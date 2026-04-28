"""
Unit tests for the R2 storage service (tender_automation/backend/app/services/r2_storage.py).

All AWS / boto3 calls are fully mocked so no real network or credentials are needed.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

import app.services.r2_storage as r2


# ── helpers ──────────────────────────────────────────────────────────────────

R2_ENV = {
    "R2_ACCOUNT_ID": "test-account",
    "R2_ACCESS_KEY_ID": "test-key",
    "R2_SECRET_ACCESS_KEY": "test-secret",
    "R2_BUCKET_NAME": "test-bucket",
}


# ── _is_configured ────────────────────────────────────────────────────────────

def test_is_configured_returns_false_when_vars_missing(monkeypatch):
    for key in R2_ENV:
        monkeypatch.delenv(key, raising=False)
    assert r2._is_configured() is False


def test_is_configured_returns_true_when_all_vars_present(monkeypatch):
    for key, val in R2_ENV.items():
        monkeypatch.setenv(key, val)
    assert r2._is_configured() is True


def test_is_configured_returns_false_when_one_var_missing(monkeypatch):
    for key, val in R2_ENV.items():
        monkeypatch.setenv(key, val)
    monkeypatch.delenv("R2_BUCKET_NAME")
    assert r2._is_configured() is False


# ── make_key ──────────────────────────────────────────────────────────────────

def test_make_key_builds_correct_path():
    key = r2.make_key("abc-123", "document.pdf")
    assert key == "tenders/abc-123/document.pdf"


def test_make_key_sanitises_path_traversal():
    key = r2.make_key("abc-123", "../../etc/passwd")
    assert ".." not in key
    assert key.startswith("tenders/abc-123/")


def test_make_key_sanitises_backslash(monkeypatch):
    key = r2.make_key("abc-123", "dir\\file.pdf")
    assert "\\" not in key


# ── upload_file ───────────────────────────────────────────────────────────────

def test_upload_file_returns_false_when_not_configured(monkeypatch, tmp_path):
    for key in R2_ENV:
        monkeypatch.delenv(key, raising=False)
    local = tmp_path / "test.pdf"
    local.write_bytes(b"%PDF-1.4")
    assert r2.upload_file(str(local), "tenders/x/test.pdf") is False


def test_upload_file_returns_true_on_success(monkeypatch, tmp_path):
    for key, val in R2_ENV.items():
        monkeypatch.setenv(key, val)

    local = tmp_path / "test.pdf"
    local.write_bytes(b"%PDF-1.4")

    mock_client = MagicMock()
    mock_client.upload_file.return_value = None

    with patch.object(r2, "_get_client", return_value=mock_client):
        result = r2.upload_file(str(local), "tenders/x/test.pdf")

    assert result is True
    mock_client.upload_file.assert_called_once_with(
        str(local), "test-bucket", "tenders/x/test.pdf"
    )


def test_upload_file_returns_false_on_boto3_exception(monkeypatch, tmp_path):
    for key, val in R2_ENV.items():
        monkeypatch.setenv(key, val)

    local = tmp_path / "test.pdf"
    local.write_bytes(b"%PDF-1.4")

    mock_client = MagicMock()
    mock_client.upload_file.side_effect = Exception("network error")

    with patch.object(r2, "_get_client", return_value=mock_client):
        result = r2.upload_file(str(local), "tenders/x/test.pdf")

    assert result is False


# ── get_presigned_url ─────────────────────────────────────────────────────────

def test_get_presigned_url_returns_none_when_not_configured(monkeypatch):
    for key in R2_ENV:
        monkeypatch.delenv(key, raising=False)
    assert r2.get_presigned_url("tenders/x/test.pdf") is None


def test_get_presigned_url_returns_url_on_success(monkeypatch):
    for key, val in R2_ENV.items():
        monkeypatch.setenv(key, val)

    expected_url = "https://test-account.r2.cloudflarestorage.com/tenders/x/test.pdf?sig=abc"
    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = expected_url

    with patch.object(r2, "_get_client", return_value=mock_client):
        url = r2.get_presigned_url("tenders/x/test.pdf", expires_in=300)

    assert url == expected_url
    mock_client.generate_presigned_url.assert_called_once_with(
        "get_object",
        Params={"Bucket": "test-bucket", "Key": "tenders/x/test.pdf"},
        ExpiresIn=300,
    )


def test_get_presigned_url_returns_none_on_boto3_exception(monkeypatch):
    for key, val in R2_ENV.items():
        monkeypatch.setenv(key, val)

    mock_client = MagicMock()
    mock_client.generate_presigned_url.side_effect = Exception("signing error")

    with patch.object(r2, "_get_client", return_value=mock_client):
        url = r2.get_presigned_url("tenders/x/test.pdf")

    assert url is None
