"""
Shared pytest fixtures for the Tender Automation test suite.
Uses an in-memory SQLite database so tests are fully isolated and need
no filesystem or network access.
"""
from __future__ import annotations

import os
import sys
import sqlite3
from pathlib import Path

# Make sure backend/  is on sys.path so `from app.xxx import …` works
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# --------------------------------------------------------------------------- #
# Patch database BEFORE any app code is imported so init_db() and every
# get_connection() call hit the same in-memory database, not a real file.
# --------------------------------------------------------------------------- #
import unittest.mock as mock

_IN_MEMORY_CONN: sqlite3.Connection | None = None


def _get_in_memory_connection() -> sqlite3.Connection:
    global _IN_MEMORY_CONN
    if _IN_MEMORY_CONN is None:
        _IN_MEMORY_CONN = sqlite3.connect(":memory:", check_same_thread=False)
        _IN_MEMORY_CONN.row_factory = sqlite3.Row
    return _IN_MEMORY_CONN


# Patch before app imports
mock.patch("app.services.database.get_connection", side_effect=_get_in_memory_connection).start()

# Now safe to import app
from app.main import app  # noqa: E402
from app.services.database import init_db  # noqa: E402

# Run schema creation against the in-memory DB
init_db()

import pytest  # noqa: E402
from httpx import AsyncClient, ASGITransport  # noqa: E402


@pytest.fixture(autouse=True)
def reset_db():
    """Wipe all rows between tests to guarantee isolation."""
    conn = _get_in_memory_connection()
    yield
    conn.execute("DELETE FROM sessions")
    conn.execute("DELETE FROM users")
    conn.execute("DELETE FROM tenders")
    conn.execute("DELETE FROM auth_rate_limits")
    conn.execute("DELETE FROM auth_failed_attempts")
    conn.commit()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ------------------------------------------------------------------ #
# Helper: register + login → return (token, csrf_token, cookies dict) #
# ------------------------------------------------------------------ #
@pytest.fixture
async def auth_client(client: AsyncClient):
    """Returns an AsyncClient pre-loaded with a valid session."""
    await client.post("/api/auth/register", json={"username": "testuser", "password": "Password1!"})
    resp = await client.post("/api/auth/login", json={"username": "testuser", "password": "Password1!"})
    assert resp.status_code == 200
    data = resp.json()
    csrf = data["csrf_token"]

    # Attach CSRF header to the client for subsequent mutating requests
    client.headers.update({"X-CSRF-Token": csrf})
    yield client
