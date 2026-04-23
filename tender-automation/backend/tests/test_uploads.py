"""
File upload validation tests (size, type, malicious filenames, empty files).
These tests stub out the document ingestion and OpenAI extraction so no
filesystem writes or network calls happen.
"""
from __future__ import annotations

import io
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


# ──────────────────────────────────────────────────────────────────────── #
# Helpers                                                                   #
# ──────────────────────────────────────────────────────────────────────── #

FAKE_SUMMARY = {
    "company_details": ["Acme Corp"],
    "payment_terms": ["Net 30"],
    "compliance_requirements": ["ISO 9001"],
    "service_scope": ["Consulting"],
    "submission_formats": ["PDF"],
    "notes": [],
}

FAKE_TENDER_SUMMARY_OBJ = MagicMock(
    company_details=["Acme Corp"],
    payment_terms=["Net 30"],
    compliance_requirements=["ISO 9001"],
    service_scope=["Consulting"],
    submission_formats=["PDF"],
    notes=[],
    model_dump=lambda: FAKE_SUMMARY,
)


def _make_upload_request(
    client: AsyncClient,
    token: str,
    csrf: str,
    filename: str = "tender.txt",
    content: bytes = b"This is a valid tender document content with enough text.",
    org: str = "TestOrg",
):
    return client.post(
        "/api/tenders/process",
        data={"organization": org},
        files={"tender_file": (filename, io.BytesIO(content), "text/plain")},
        headers={"X-CSRF-Token": csrf},
        cookies={"session_token": token, "csrf_token": csrf},
    )


async def _register_and_login(client: AsyncClient) -> tuple[str, str]:
    await client.post("/api/auth/register", json={"username": "alice", "password": "StrongPass1"})
    login = await client.post("/api/auth/login", json={"username": "alice", "password": "StrongPass1"})
    data = login.json()
    return data["token"], data["csrf_token"]


# ──────────────────────────────────────────────────────────────────────── #
# File type validation                                                      #
# ──────────────────────────────────────────────────────────────────────── #

async def test_unsupported_file_type_rejected(client: AsyncClient):
    token, csrf = await _register_and_login(client)
    r = await _make_upload_request(client, token, csrf, filename="malware.exe", content=b"MZ\x00\x01")
    assert r.status_code == 400
    assert "Unsupported" in r.json()["error"]["message"]


async def test_docx_file_type_rejected(client: AsyncClient):
    token, csrf = await _register_and_login(client)
    r = await _make_upload_request(client, token, csrf, filename="document.docx", content=b"PK\x03\x04")
    assert r.status_code == 400


async def test_no_extension_rejected(client: AsyncClient):
    token, csrf = await _register_and_login(client)
    r = await _make_upload_request(client, token, csrf, filename="noextension", content=b"some content")
    assert r.status_code == 400


# ──────────────────────────────────────────────────────────────────────── #
# File size limits                                                          #
# ──────────────────────────────────────────────────────────────────────── #

async def test_file_exceeding_5mb_rejected(client: AsyncClient):
    token, csrf = await _register_and_login(client)
    oversized = b"A" * (5 * 1024 * 1024 + 1)
    r = await _make_upload_request(client, token, csrf, filename="big.txt", content=oversized)
    assert r.status_code == 413
    assert "too large" in r.json()["error"]["message"].lower()


async def test_empty_file_rejected(client: AsyncClient):
    token, csrf = await _register_and_login(client)
    r = await _make_upload_request(client, token, csrf, filename="empty.txt", content=b"")
    assert r.status_code == 400


# ──────────────────────────────────────────────────────────────────────── #
# Valid TXT upload (stubbed ingestion + extraction)                        #
# ──────────────────────────────────────────────────────────────────────── #

async def test_valid_txt_upload_returns_200(client: AsyncClient):
    from app.schemas import TenderSummary

    token, csrf = await _register_and_login(client)
    fake_summary = TenderSummary(**FAKE_SUMMARY)

    with (
        patch(
            "app.routes.tenders.ingest_document",
            return_value=("Full tender text content here " * 20, False, []),
        ),
        patch(
            "app.routes.tenders.extract_with_openai",
            return_value=(fake_summary, [], "Final output text", []),
        ),
    ):
        r = await _make_upload_request(
            client, token, csrf, filename="tender.txt", content=b"Valid tender content"
        )

    assert r.status_code == 200
    body = r.json()
    assert "tender_id" in body
    assert body["organization"] == "TestOrg"
    assert "extracted" in body


# ──────────────────────────────────────────────────────────────────────── #
# Missing organization field                                               #
# ──────────────────────────────────────────────────────────────────────── #

async def test_blank_organization_rejected(client: AsyncClient):
    token, csrf = await _register_and_login(client)
    r = await client.post(
        "/api/tenders/process",
        data={"organization": "   "},
        files={"tender_file": ("t.txt", io.BytesIO(b"content"), "text/plain")},
        headers={"X-CSRF-Token": csrf},
        cookies={"session_token": token, "csrf_token": csrf},
    )
    assert r.status_code == 400


# ──────────────────────────────────────────────────────────────────────── #
# Auth required                                                             #
# ──────────────────────────────────────────────────────────────────────── #

async def test_upload_requires_auth(client: AsyncClient):
    r = await client.post(
        "/api/tenders/process",
        data={"organization": "Org"},
        files={"tender_file": ("t.txt", io.BytesIO(b"content"), "text/plain")},
    )
    assert r.status_code == 401


# ──────────────────────────────────────────────────────────────────────── #
# Malicious filename (path traversal attempt)                              #
# ──────────────────────────────────────────────────────────────────────── #

async def test_path_traversal_filename_rejected(client: AsyncClient):
    """../../etc/passwd-style filename has no valid extension → rejected."""
    token, csrf = await _register_and_login(client)
    r = await _make_upload_request(
        client, token, csrf,
        filename="../../etc/passwd",
        content=b"root:x:0:0",
    )
    assert r.status_code == 400
