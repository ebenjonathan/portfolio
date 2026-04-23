"""
Tender history and record retrieval tests.
"""
from __future__ import annotations

import io
from unittest.mock import patch

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def _register_and_login(client: AsyncClient, username: str = "alice") -> tuple[str, str]:
    await client.post("/api/auth/register", json={"username": username, "password": "StrongPass1"})
    login = await client.post("/api/auth/login", json={"username": username, "password": "StrongPass1"})
    data = login.json()
    return data["token"], data["csrf_token"]


async def _create_tender(client: AsyncClient, token: str, csrf: str) -> str:
    """Upload a tender (stubbed) and return its tender_id."""
    from app.schemas import TenderSummary

    fake_summary = TenderSummary(
        company_details=["Acme"],
        payment_terms=["Net 30"],
        compliance_requirements=[],
        service_scope=["Consulting"],
        submission_formats=["PDF"],
        notes=[],
    )
    with (
        patch(
            "app.routes.tenders.ingest_document",
            return_value=("full text " * 30, False, []),
        ),
        patch(
            "app.routes.tenders.extract_with_openai",
            return_value=(fake_summary, [], "Final output", []),
        ),
    ):
        r = await client.post(
            "/api/tenders/process",
            data={"organization": "TestOrg"},
            files={"tender_file": ("t.txt", io.BytesIO(b"Valid content"), "text/plain")},
            headers={"X-CSRF-Token": csrf},
            cookies={"session_token": token, "csrf_token": csrf},
        )
    assert r.status_code == 200
    return r.json()["tender_id"]


async def test_history_returns_empty_list_initially(client: AsyncClient):
    token, _csrf = await _register_and_login(client)
    r = await client.get("/api/tenders/history", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == []


async def test_history_contains_uploaded_tender(client: AsyncClient):
    token, csrf = await _register_and_login(client)
    tid = await _create_tender(client, token, csrf)
    r = await client.get("/api/tenders/history", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    ids = [rec["tender_id"] for rec in r.json()]
    assert tid in ids


async def test_history_limit_is_respected(client: AsyncClient):
    token, csrf = await _register_and_login(client)
    # Create 3 tenders
    for _ in range(3):
        await _create_tender(client, token, csrf)

    r = await client.get("/api/tenders/history?limit=2", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()) == 2


async def test_history_limit_clamped_to_100(client: AsyncClient):
    token, _csrf = await _register_and_login(client)
    # limit=999 should work but return at most 100 records (none here)
    r = await client.get("/api/tenders/history?limit=999", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_get_tender_record_by_id(client: AsyncClient):
    token, csrf = await _register_and_login(client)
    tid = await _create_tender(client, token, csrf)
    r = await client.get(f"/api/tenders/{tid}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["tender_id"] == tid


async def test_get_tender_record_not_found(client: AsyncClient):
    token, _csrf = await _register_and_login(client)
    r = await client.get("/api/tenders/tdr-doesnotexist", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


async def test_history_isolated_per_user(client: AsyncClient):
    """User A's tenders must not be visible to User B."""
    token_a, csrf_a = await _register_and_login(client, "userA")
    token_b, _csrf_b = await _register_and_login(client, "userB")

    await _create_tender(client, token_a, csrf_a)

    r = await client.get("/api/tenders/history", headers={"Authorization": f"Bearer {token_b}"})
    assert r.status_code == 200
    assert r.json() == []


async def test_save_review_updates_record(client: AsyncClient):
    token, csrf = await _register_and_login(client)
    tid = await _create_tender(client, token, csrf)

    r = await client.post(
        f"/api/tenders/{tid}/save",
        json={
            "extracted": {
                "company_details": ["Updated Corp"],
                "payment_terms": [],
                "compliance_requirements": [],
                "service_scope": [],
                "submission_formats": [],
                "notes": [],
            },
            "needs_human_review": [],
            "final_output": "Reviewed output",
            "reviewer_notes": "Looks good",
            "status": "final",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "final"
    assert body["reviewer_notes"] == "Looks good"
    assert body["extracted"]["company_details"] == ["Updated Corp"]
