from __future__ import annotations

import json
from datetime import datetime, timezone

from app.schemas import TenderRecord, TenderReviewSaveRequest
from app.services.database import get_connection


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_processed_record(record: TenderRecord, user_id: int) -> TenderRecord:
    payload = json.dumps(record.model_dump())
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO tenders (tender_id, user_id, payload_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                record.tender_id,
                user_id,
                payload,
                record.created_at,
                record.updated_at,
            ),
        )
        conn.commit()
    return record


def get_record(tender_id: str, user_id: int) -> TenderRecord | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT payload_json FROM tenders WHERE tender_id = ? AND user_id = ?",
            (tender_id, user_id),
        ).fetchone()
        if row is None:
            return None
        payload = json.loads(row["payload_json"])
        return TenderRecord(**payload)


def list_records(user_id: int, limit: int = 30) -> list[TenderRecord]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT payload_json FROM tenders WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    records: list[TenderRecord] = []
    for row in rows:
        records.append(TenderRecord(**json.loads(row["payload_json"])))
    return records


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
    )
