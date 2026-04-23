"""
Rate limiting tests.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_login_rate_limit_triggered(client: AsyncClient):
    """After 5 failed login attempts from same IP, 429 must be returned."""
    await client.post("/api/auth/register", json={"username": "victim", "password": "StrongPass1"})
    for _ in range(5):
        await client.post("/api/auth/login", json={"username": "victim", "password": "WrongPassword1"})

    r = await client.post("/api/auth/login", json={"username": "victim", "password": "WrongPassword1"})
    assert r.status_code == 429
    assert r.json()["ok"] is False


async def test_register_rate_limit_triggered(client: AsyncClient):
    """After 3 register attempts from same IP, 429 must be returned."""
    for i in range(3):
        await client.post("/api/auth/register", json={"username": f"user{i}", "password": "StrongPass1"})

    r = await client.post("/api/auth/register", json={"username": "user4", "password": "StrongPass1"})
    assert r.status_code == 429
    assert r.json()["ok"] is False


async def test_login_rate_limit_resets_after_window(client: AsyncClient):
    """
    Exhaust rate limit, then simulate window expiry by directly updating
    window_start in the DB, and verify requests are allowed again.
    """
    import time
    from app.services.database import get_connection

    await client.post("/api/auth/register", json={"username": "victim", "password": "StrongPass1"})
    for _ in range(5):
        await client.post("/api/auth/login", json={"username": "victim", "password": "WrongPassword1"})

    # Move the window_start back by 61 seconds so the window has expired
    conn = get_connection()
    conn.execute(
        "UPDATE auth_rate_limits SET window_start = ? WHERE bucket_key LIKE 'login:%'",
        (int(time.time()) - 61,),
    )
    conn.commit()

    r = await client.post("/api/auth/login", json={"username": "victim", "password": "WrongPassword1"})
    # Should be 401 (bad password), NOT 429
    assert r.status_code == 401


async def test_rate_limit_error_envelope_format(client: AsyncClient):
    """Rate limit response must conform to the error envelope."""
    for _ in range(5):
        await client.post("/api/auth/login", json={"username": "nobody", "password": "WrongPassword1"})

    r = await client.post("/api/auth/login", json={"username": "nobody", "password": "WrongPassword1"})
    assert r.status_code == 429
    body = r.json()
    assert body["ok"] is False
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]
