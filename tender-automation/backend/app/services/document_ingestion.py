from __future__ import annotations

from pypdf import PdfReader


def _extract_pdf_text(file_path: str) -> str:
    reader = PdfReader(file_path)
    pages_text: list[str] = []
    for page in reader.pages:
        pages_text.append((page.extract_text() or "").strip())
    return "\n".join([item for item in pages_text if item])


def _extract_text_file(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
        return fh.read()


def _ocr_pdf(file_path: str) -> str:
    from pdf2image import convert_from_path
    import pytesseract

    pages = convert_from_path(file_path, dpi=220)

    ocr_chunks: list[str] = []
    for image in pages:
        ocr_chunks.append(pytesseract.image_to_string(image))
    return "\n".join([item.strip() for item in ocr_chunks if item and item.strip()])


def ingest_document(filename: str, file_path: str) -> tuple[str, bool, list[str]]:
    ext = filename.lower().split(".")[-1]
    notes: list[str] = []
    ocr_used = False

    if ext == "pdf":
        extracted = _extract_pdf_text(file_path)
        if len(extracted.strip()) < 250:
            try:
                extracted = _ocr_pdf(file_path)
                ocr_used = True
                notes.append("OCR fallback executed for low-text PDF.")
            except Exception as exc:
                notes.append(
                    "OCR fallback failed. Install Tesseract OCR and Poppler binaries on host."
                )
                notes.append(f"OCR error: {exc}")
    elif ext in {"txt"}:
        extracted = _extract_text_file(file_path)
    else:
        raise ValueError("Unsupported file type. Upload PDF or TXT.")

    if not extracted.strip():
        raise ValueError("Could not extract readable text from uploaded file.")

    return extracted, ocr_used, notes
