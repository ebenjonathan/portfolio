# Backend (FastAPI)

## Run

1. Create/activate a Python environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy environment file:

```bash
copy .env.example .env
```

4. Add your `OPENAI_API_KEY` in `.env`.

5. Start API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## OCR host dependencies

PDF OCR fallback requires:

- Tesseract OCR installed and available on PATH.
- Poppler installed and available on PATH.

Without these, the API still works for text-based PDFs and TXT files and falls back gracefully.

## Endpoints

- `GET /health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me` (Bearer token)
- `POST /api/tenders/process` (multipart form)
  - `organization` (text)
  - `tender_file` (PDF or TXT only, max 5 MB)
- `GET /api/tenders/history?limit=40` (Bearer token)
- `GET /api/tenders/{tender_id}`
- `POST /api/tenders/{tender_id}/save`

Processed and reviewed records are persisted in sqlite at `backend/storage/app.db`.

## Reviewer sessions

- Register reviewer account once.
- Login to receive Bearer token.
- All history and saved records are scoped per user.

## Online deployment (Render)

From repository root, use `render.yaml`.

- Docker build context: `tender-automation/`
- App serves API and static demo at `/demo/`
