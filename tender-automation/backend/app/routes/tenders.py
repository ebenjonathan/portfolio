import uuid
import asyncio
import os
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.schemas import TenderProcessingResponse, TenderRecord, TenderReviewSaveRequest
from app.services.auth_service import get_current_user
from app.services.document_ingestion import ingest_document
from app.services.openai_extractor import extract_with_openai
from app.services.result_store import (
    build_record,
    get_record,
    list_records,
    save_processed_record,
    save_review,
)

router = APIRouter()

MAX_UPLOAD_SIZE = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {"pdf", "txt"}
EXTRACTION_TIMEOUT_SECONDS = int(os.getenv("EXTRACTION_TIMEOUT_SECONDS", "60"))


@router.post("/process", response_model=TenderProcessingResponse)
async def process_tender(
    organization: str = Form(...),
    tender_file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> TenderProcessingResponse:
    if not organization.strip():
        raise HTTPException(status_code=400, detail="organization is required")

    if tender_file.filename is None:
        raise HTTPException(status_code=400, detail="file name is required")

    ext = tender_file.filename.rsplit(".", 1)[-1].lower() if "." in tender_file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload PDF or TXT.")

    total_bytes = 0
    tmp_path = ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp_path = tmp.name
        while True:
            chunk = await tender_file.read(1024 * 1024)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_UPLOAD_SIZE:
                raise HTTPException(status_code=413, detail="File too large. Max size is 5MB.")
            tmp.write(chunk)

    if total_bytes == 0:
        raise HTTPException(status_code=400, detail="uploaded file is empty")

    try:
        extracted_text, ocr_used, ingest_notes = await asyncio.wait_for(
            asyncio.to_thread(ingest_document, tender_file.filename, tmp_path),
            timeout=EXTRACTION_TIMEOUT_SECONDS,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Document extraction timed out") from exc
    finally:
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass

    tender_id = f"tdr-{uuid.uuid4().hex[:10]}"

    try:
        extracted, needs_human_review, final_output, _notes = await asyncio.wait_for(
            asyncio.to_thread(
                extract_with_openai,
                document_text=extracted_text,
                organization=organization.strip(),
                ingest_notes=ingest_notes,
            ),
            timeout=EXTRACTION_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Extraction pipeline timed out") from exc

    record = build_record(
        tender_id=tender_id,
        organization=organization.strip(),
        source_filename=tender_file.filename,
        ocr_used=ocr_used,
        extracted=extracted,
        needs_human_review=needs_human_review,
        final_output=final_output,
    )
    save_processed_record(record, current_user["id"])

    return TenderProcessingResponse(
        tender_id=tender_id,
        organization=organization.strip(),
        source_filename=tender_file.filename,
        ocr_used=ocr_used,
        extracted=extracted,
        needs_human_review=needs_human_review,
        final_output=final_output,
    )


@router.get("/history", response_model=list[TenderRecord])
def get_tender_history(
    limit: int = 30,
    current_user: dict = Depends(get_current_user),
) -> list[TenderRecord]:
    bounded_limit = max(1, min(limit, 100))
    return list_records(current_user["id"], bounded_limit)


@router.get("/{tender_id}", response_model=TenderRecord)
def get_tender_record(
    tender_id: str,
    current_user: dict = Depends(get_current_user),
) -> TenderRecord:
    record = get_record(tender_id, current_user["id"])
    if record is None:
        raise HTTPException(status_code=404, detail="Tender record not found")
    return record


@router.post("/{tender_id}/save", response_model=TenderRecord)
def save_tender_review(
    tender_id: str,
    payload: TenderReviewSaveRequest,
    current_user: dict = Depends(get_current_user),
) -> TenderRecord:
    updated = save_review(tender_id, payload, current_user["id"])
    if updated is None:
        raise HTTPException(status_code=404, detail="Tender record not found")
    return updated
