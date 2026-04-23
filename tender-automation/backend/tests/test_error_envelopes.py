"""
Error envelope format tests — every non-2xx response must contain:
  { "ok": false, "error": { "code": <int>, "message": <str> } }
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


def _assert_envelope(r, expected_status: int):
    assert r.status_code == expected_status, r.text
    body = r.json()
    assert body.get("ok") is False, f"Expected ok=false, got: {body}"
    assert "error" in body, f"Missing 'error' key: {body}"
    error = body["error"]
    assert isinstance(error.get("code"), int), f"error.code must be int: {error}"
    assert isinstance(error.get("message"), str), f"error.message must be str: {error}"


async def test_envelope_401_no_token(client: AsyncClient):
    r = await client.get("/api/auth/me")
    _assert_envelope(r, 401)


async def test_envelope_401_invalid_token(client: AsyncClient):
    r = await client.get("/api/auth/me", headers={"Authorization": "Bearer badtoken"})
    _assert_envelope(r, 401)


async def test_envelope_409_duplicate_user(client: AsyncClient):
    await client.post("/api/auth/register", json={"username": "alice", "password": "StrongPass1"})
    r = await client.post("/api/auth/register", json={"username": "alice", "password": "StrongPass1"})
    _assert_envelope(r, 409)


async def test_envelope_400_short_username(client: AsyncClient):
    r = await client.post("/api/auth/register", json={"username": "ab", "password": "StrongPass1"})
    _assert_envelope(r, 400)


async def test_envelope_400_short_password(client: AsyncClient):
    r = await client.post("/api/auth/register", json={"username": "validuser", "password": "abc"})
    _assert_envelope(r, 400)


async def test_envelope_422_missing_required_field(client: AsyncClient):
    """Sending no body should trigger Pydantic validation error → 422."""
    r = await client.post("/api/auth/register", json={})
    _assert_envelope(r, 422)


async def test_envelope_401_wrong_login(client: AsyncClient):
    r = await client.post("/api/auth/login", json={"username": "ghost", "password": "wrongpass1"})
    _assert_envelope(r, 401)


async def test_envelope_403_csrf_failure(client: AsyncClient):
    await client.post("/api/auth/register", json={"username": "alice", "password": "StrongPass1"})
    login = await client.post("/api/auth/login", json={"username": "alice", "password": "StrongPass1"})
    token = login.json()["token"]
    csrf = login.json()["csrf_token"]

    r = await client.post(
        "/api/auth/logout",
        cookies={"session_token": token, "csrf_token": csrf},
        # NO X-CSRF-Token header
    )
    _assert_envelope(r, 403)


async def test_health_endpoint_returns_ok(client: AsyncClient):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_envelope_404_tender_not_found(client: AsyncClient):
    await client.post("/api/auth/register", json={"username": "alice", "password": "StrongPass1"})
    login = await client.post("/api/auth/login", json={"username": "alice", "password": "StrongPass1"})
    token = login.json()["token"]

    r = await client.get(
        "/api/tenders/nonexistent-id",
        headers={"Authorization": f"Bearer {token}"},
    )
    _assert_envelope(r, 404)
