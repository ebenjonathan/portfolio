from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import text

from app.schemas import TenderRecord, TenderReviewSaveRequest
from app.services.database import get_connection


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_processed_record(record: TenderRecord, user_id: int) -> TenderRecord:
    payload = json.dumps(record.model_dump())
    with get_connection() as conn:
        conn.execute(
            text(
                "INSERT INTO tenders (tender_id, user_id, payload_json, created_at, updated_at)"
                " VALUES (:tender_id, :user_id, :payload_json, :created_at, :updated_at)"
                " ON CONFLICT (tender_id) DO UPDATE SET"
                "   payload_json = EXCLUDED.payload_json,"
                "   updated_at = EXCLUDED.updated_at"
            ),
            {
                "tender_id": record.tender_id,
                "user_id": user_id,
                "payload_json": payload,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            },
        )
        conn.commit()
    return record


def get_record(tender_id: str, user_id: int) -> TenderRecord | None:
    with get_connection() as conn:
        row = conn.execute(
            text(
                "SELECT payload_json FROM tenders"
                " WHERE tender_id = :tender_id AND user_id = :user_id"
            ),
            {"tender_id": tender_id, "user_id": user_id},
        ).mappings().fetchone()
        if row is None:
            return None
        payload = json.loads(row["payload_json"])
        return TenderRecord(**payload)


def list_records(user_id: int, limit: int = 30) -> list[TenderRecord]:
    with get_connection() as conn:
        rows = conn.execute(
            text(
                "SELECT payload_json FROM tenders"
                " WHERE user_id = :user_id"
                " ORDER BY updated_at DESC"
                " LIMIT :limit"
            ),
            {"user_id": user_id, "limit": limit},
        ).mappings().fetchall()
    return [TenderRecord(**json.loads(row["payload_json"])) for row in rows]


def save_review(tender_id: str, review: TenderReviewSaveRequest, user_id: int) -> TenderRecord | None:
    existing = get_record(tender_id, user_id)
    if existing is None:
        return None

    updated = TenderRecord(
        tender_id=existing.tender_id,
        organization=existing.organization,
        source_filename=existing.source_filename,
        ocr_used=existing.ocr_used,
        extracted=review.extracted,
        needs_human_review=review.needs_human_review,
        final_output=review.final_output,
        reviewer_notes=review.reviewer_notes,
        status=review.status,
        created_at=existing.created_at,
        updated_at=_now_iso(),
    )
    return save_processed_record(updated, user_id)


def build_record(
    tender_id: str,
    organization: str,
    source_filename: str,
    ocr_used: bool,
    extracted,
    needs_human_review: list[str],
    final_output: str,
    r2_key: str = "",
) -> TenderRecord:
    now = _now_iso()
    return TenderRecord(
        tender_id=tender_id,
        organization=organization,
        source_filename=source_filename,
        ocr_used=ocr_used,
        extracted=extracted,
        needs_human_review=needs_human_review,
        final_output=final_output,
        reviewer_notes="",
        status="processed",
        created_at=now,
        updated_at=now,
        r2_key=r2_key,
    )
