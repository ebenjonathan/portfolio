"""
Shared pytest fixtures for the Tender Automation test suite.

Uses an in-memory SQLite database via SQLAlchemy StaticPool so every
engine.connect() call shares the same underlying connection, tests are
fully isolated and need no filesystem or network access.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Make sure backend/ is on sys.path so `from app.xxx import …` works
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ── Point the app at an in-memory SQLite DB before any app code is imported ──
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ.setdefault("SESSION_COOKIE_SECURE", "false")

# Override the module-level engine with a StaticPool engine so all
# connections in the same test process share one SQLite connection.
import app.services.database as _db_module  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

_test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_db_module._engine = _test_engine

# Now safe to import app
from app.main import app  # noqa: E402
from app.services.database import init_db  # noqa: E402

init_db()

import pytest  # noqa: E402
from httpx import AsyncClient, ASGITransport  # noqa: E402


@pytest.fixture(autouse=True)
def reset_db():
    """Wipe all rows between tests to guarantee isolation."""
    yield
    with _test_engine.connect() as conn:
        conn.execute(text("DELETE FROM sessions"))
        conn.execute(text("DELETE FROM users"))
        conn.execute(text("DELETE FROM tenders"))
        conn.execute(text("DELETE FROM auth_rate_limits"))
        conn.execute(text("DELETE FROM auth_failed_attempts"))
        conn.commit()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ─────────────────────────────────────────────────────── #
# Helper: register + login → pre-authenticated client     #
# ─────────────────────────────────────────────────────── #
@pytest.fixture
async def auth_client(client: AsyncClient):
    """Returns an AsyncClient pre-loaded with a valid session."""
    await client.post("/api/auth/register", json={"username": "testuser", "password": "Password1!"})
    resp = await client.post("/api/auth/login", json={"username": "testuser", "password": "Password1!"})
    assert resp.status_code == 200
    data = resp.json()
    csrf = data["csrf_token"]
    client.headers.update({"X-CSRF-Token": csrf})
    yield client
