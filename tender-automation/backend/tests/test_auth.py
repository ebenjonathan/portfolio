"""
Authentication flow tests: register, login, logout, /me, session expiry.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


# ──────────────────────────────────────────────────────────────────────── #
# Registration                                                              #
# ──────────────────────────────────────────────────────────────────────── #

async def test_register_success(client: AsyncClient):
    r = await client.post("/api/auth/register", json={"username": "alice", "password": "StrongPass1"})
    assert r.status_code == 201
    assert r.json()["message"] == "Account created"


async def test_register_duplicate_username(client: AsyncClient):
    await client.post("/api/auth/register", json={"username": "alice", "password": "StrongPass1"})
    r = await client.post("/api/auth/register", json={"username": "alice", "password": "AnotherPass1"})
    assert r.status_code == 409
    assert r.json()["ok"] is False


async def test_register_username_too_short(client: AsyncClient):
    r = await client.post("/api/auth/register", json={"username": "ab", "password": "StrongPass1"})
    assert r.status_code == 400
    assert r.json()["ok"] is False


async def test_register_password_too_short(client: AsyncClient):
    r = await client.post("/api/auth/register", json={"username": "validname", "password": "abc"})
    assert r.status_code == 400
    assert r.json()["ok"] is False


async def test_register_username_is_lowercased(client: AsyncClient):
    """Usernames are stored lowercase; second reg with different casing must 409."""
    await client.post("/api/auth/register", json={"username": "Bob", "password": "StrongPass1"})
    r = await client.post("/api/auth/register", json={"username": "BOB", "password": "StrongPass1"})
    assert r.status_code == 409


# ──────────────────────────────────────────────────────────────────────── #
# Login                                                                     #
# ──────────────────────────────────────────────────────────────────────── #

async def test_login_valid_credentials(client: AsyncClient):
    await client.post("/api/auth/register", json={"username": "alice", "password": "StrongPass1"})
    r = await client.post("/api/auth/login", json={"username": "alice", "password": "StrongPass1"})
    assert r.status_code == 200
    body = r.json()
    assert "token" in body
    assert body["username"] == "alice"
    assert "csrf_token" in body
    # session_token cookie must be httponly
    assert "session_token" in r.cookies


async def test_login_invalid_password(client: AsyncClient):
    await client.post("/api/auth/register", json={"username": "alice", "password": "StrongPass1"})
    r = await client.post("/api/auth/login", json={"username": "alice", "password": "WrongPass!"})
    assert r.status_code == 401
    assert r.json()["ok"] is False


async def test_login_nonexistent_user(client: AsyncClient):
    r = await client.post("/api/auth/login", json={"username": "ghost", "password": "whatever1"})
    assert r.status_code == 401
    assert r.json()["ok"] is False


async def test_login_case_insensitive_username(client: AsyncClient):
    await client.post("/api/auth/register", json={"username": "alice", "password": "StrongPass1"})
    r = await client.post("/api/auth/login", json={"username": "ALICE", "password": "StrongPass1"})
    assert r.status_code == 200


# ──────────────────────────────────────────────────────────────────────── #
# /me (session validation)                                                  #
# ──────────────────────────────────────────────────────────────────────── #

async def test_me_with_bearer_token(client: AsyncClient):
    await client.post("/api/auth/register", json={"username": "alice", "password": "StrongPass1"})
    login = await client.post("/api/auth/login", json={"username": "alice", "password": "StrongPass1"})
    token = login.json()["token"]
    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == "alice"


async def test_me_without_token(client: AsyncClient):
    r = await client.get("/api/auth/me")
    assert r.status_code == 401
    assert r.json()["ok"] is False


async def test_me_invalid_token(client: AsyncClient):
    r = await client.get("/api/auth/me", headers={"Authorization": "Bearer totallyinvalidtoken"})
    assert r.status_code == 401
    assert r.json()["ok"] is False


# ──────────────────────────────────────────────────────────────────────── #
# Session expiry                                                            #
# ──────────────────────────────────────────────────────────────────────── #

async def test_expired_session_returns_401(client: AsyncClient):
    """Manually insert an already-expired session and verify rejection."""
    from datetime import datetime, timedelta, timezone
    from app.services.database import get_connection

    await client.post("/api/auth/register", json={"username": "alice", "password": "StrongPass1"})

    expired_token = "expired_test_token_abc123"
    now = datetime.now(timezone.utc)
    past = now - timedelta(hours=1)
    conn = get_connection()
    user_row = conn.execute("SELECT id FROM users WHERE username='alice'").fetchone()
    conn.execute(
        "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (expired_token, user_row["id"], past.isoformat(), past.isoformat()),
    )
    conn.commit()

    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert r.status_code == 401


# ──────────────────────────────────────────────────────────────────────── #
# Logout                                                                    #
# ──────────────────────────────────────────────────────────────────────── #

async def test_logout_clears_session(client: AsyncClient):
    await client.post("/api/auth/register", json={"username": "alice", "password": "StrongPass1"})
    login = await client.post("/api/auth/login", json={"username": "alice", "password": "StrongPass1"})
    token = login.json()["token"]
    csrf = login.json()["csrf_token"]

    # logout via cookie + CSRF header
    logout_r = await client.post(
        "/api/auth/logout",
        headers={"X-CSRF-Token": csrf},
        cookies={"session_token": token, "csrf_token": csrf},
    )
    assert logout_r.status_code == 200

    # Token must now be invalid
    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
