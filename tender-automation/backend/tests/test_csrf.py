"""
CSRF protection enforcement tests.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def _register_and_login(client: AsyncClient) -> tuple[str, str]:
    """Returns (session_token, csrf_token)."""
    await client.post("/api/auth/register", json={"username": "alice", "password": "StrongPass1"})
    login = await client.post("/api/auth/login", json={"username": "alice", "password": "StrongPass1"})
    data = login.json()
    return data["token"], data["csrf_token"]


# ──────────────────────────────────────────────────────────────────────── #
# Logout CSRF                                                               #
# ──────────────────────────────────────────────────────────────────────── #

async def test_logout_without_csrf_header_is_rejected(client: AsyncClient):
    token, csrf = await _register_and_login(client)
    r = await client.post(
        "/api/auth/logout",
        cookies={"session_token": token, "csrf_token": csrf},
        # intentionally NO X-CSRF-Token header
    )
    assert r.status_code == 403
    assert r.json()["ok"] is False


async def test_logout_with_wrong_csrf_token_is_rejected(client: AsyncClient):
    token, csrf = await _register_and_login(client)
    r = await client.post(
        "/api/auth/logout",
        headers={"X-CSRF-Token": "totallywrongtoken"},
        cookies={"session_token": token, "csrf_token": csrf},
    )
    assert r.status_code == 403


async def test_logout_with_correct_csrf_succeeds(client: AsyncClient):
    token, csrf = await _register_and_login(client)
    r = await client.post(
        "/api/auth/logout",
        headers={"X-CSRF-Token": csrf},
        cookies={"session_token": token, "csrf_token": csrf},
    )
    assert r.status_code == 200


# ──────────────────────────────────────────────────────────────────────── #
# Tender save CSRF (cookie-based auth, mutating endpoint)                  #
# ──────────────────────────────────────────────────────────────────────── #

async def test_save_review_without_csrf_is_rejected(client: AsyncClient):
    token, csrf = await _register_and_login(client)
    r = await client.post(
        "/api/tenders/fake-tender-id/save",
        json={
            "extracted": {
                "company_details": [],
                "payment_terms": [],
                "compliance_requirements": [],
                "service_scope": [],
                "submission_formats": [],
                "notes": [],
            },
            "needs_human_review": [],
            "final_output": "ok",
        },
        cookies={"session_token": token, "csrf_token": csrf},
        # NO X-CSRF-Token header
    )
    assert r.status_code == 403


async def test_save_review_with_csrf_passes_auth_layer(client: AsyncClient):
    """With correct CSRF, auth passes — 404 because tender doesn't exist is acceptable."""
    token, csrf = await _register_and_login(client)
    r = await client.post(
        "/api/tenders/nonexistent/save",
        json={
            "extracted": {
                "company_details": [],
                "payment_terms": [],
                "compliance_requirements": [],
                "service_scope": [],
                "submission_formats": [],
                "notes": [],
            },
            "needs_human_review": [],
            "final_output": "ok",
        },
        headers={"X-CSRF-Token": csrf},
        cookies={"session_token": token, "csrf_token": csrf},
    )
    # 404 means auth/CSRF passed, tender just wasn't found
    assert r.status_code == 404


# ──────────────────────────────────────────────────────────────────────── #
# Bearer token does NOT require CSRF (not cookie-based)                    #
# ──────────────────────────────────────────────────────────────────────── #

async def test_bearer_token_does_not_require_csrf(client: AsyncClient):
    token, _csrf = await _register_and_login(client)
    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


# ──────────────────────────────────────────────────────────────────────── #
# GET requests via cookie do NOT require CSRF                              #
# ──────────────────────────────────────────────────────────────────────── #

async def test_get_history_via_cookie_no_csrf_required(client: AsyncClient):
    token, _csrf = await _register_and_login(client)
    r = await client.get(
        "/api/tenders/history",
        cookies={"session_token": token},
    )
    assert r.status_code == 200
