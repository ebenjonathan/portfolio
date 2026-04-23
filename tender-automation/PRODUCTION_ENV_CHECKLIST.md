# Production Environment Checklist

Use this checklist before and after deploying the Tender Automation demo.

## 1. Required Environment Variables

Set these in your hosting provider (for example Render).

### Required

- OPENAI_API_KEY
  - Purpose: Enables structured extraction with OpenAI.
  - Example: `sk-...`

### Recommended

- OPENAI_MODEL
  - Purpose: Selects extraction model.
  - Default in code: `gpt-4.1-mini`
  - Suggested values: `gpt-4.1-mini` (cost/performance), `gpt-4.1` (higher quality)

- CORS_ORIGINS
  - Purpose: Allowed browser origins for frontend requests.
  - Format: comma-separated list.
  - Example:
    - `https://your-demo-service.onrender.com,https://www.mupinilabs.com`

### Optional App Metadata

- APP_NAME
  - Purpose: Human-readable service name.
  - Example: `AI Tender Automation API`

- APP_HOST
  - Purpose: Host bind value (usually not needed if container cmd already sets host).
  - Example: `0.0.0.0`

- APP_PORT
  - Purpose: Port bind value (usually set by platform).
  - Example: `8000`

## 2. OCR Runtime Dependencies (Server)

OCR fallback for image-based PDFs requires system binaries.

### Must be installed in runtime image

- Tesseract OCR
  - Binary expected on PATH: `tesseract`

- Poppler tools
  - Required by `pdf2image` to render PDF pages.
  - Binary expected on PATH: `pdftoppm` and related tools.

### Python packages already in requirements

- pytesseract
- pdf2image
- Pillow
- pypdf

### Verify dependencies inside deployed container

Run a one-off shell (if platform allows) and verify:

```bash
tesseract --version
pdftoppm -h
```

If these fail, OCR fallback will not run for scanned PDFs.

## 3. Pre-Deploy Configuration Check

- Render blueprint exists: `render.yaml` (create at repo root if deploying to Render)
- Docker build file exists: `tender-automation/Dockerfile`
- Static demo mount is configured in backend at `/demo/`
- Auth endpoints are enabled:
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `GET /api/auth/me`

## 4. Post-Deploy Smoke Test URLs

Replace `<BASE_URL>` with your deployed service URL.

### Public pages

- Demo page (mounted by backend):
  - `<BASE_URL>/demo/`
- API docs:
  - `<BASE_URL>/docs`
- Health:
  - `<BASE_URL>/health`

### Portfolio integration links (if portfolio points to deployed demo)

- Project page:
  - `https://www.mupinilabs.com/projects/tender-automation-demo.html`
- Embedded demo target from that page should load:
  - `<BASE_URL>/demo/`

### API auth flow checks

1. Register reviewer:

```http
POST <BASE_URL>/api/auth/register
Content-Type: application/json

{
  "username": "reviewer1",
  "password": "StrongPass123"
}
```

2. Login reviewer:

```http
POST <BASE_URL>/api/auth/login
Content-Type: application/json

{
  "username": "reviewer1",
  "password": "StrongPass123"
}
```

Expected: response includes `token`.

3. Validate token:

```http
GET <BASE_URL>/api/auth/me
Authorization: Bearer <TOKEN>
```

Expected: reviewer profile JSON.

### Tender workflow checks

4. Process file:

- Use frontend (`/demo/`) or multipart request to:
  - `POST <BASE_URL>/api/tenders/process`
- Include:
  - `organization`
  - `tender_file` (PDF/DOCX)

Expected:
- `tender_id`
- extracted sections
- `needs_human_review`
- `final_output`

5. Save draft and final:

- `POST <BASE_URL>/api/tenders/{tender_id}/save`
- Use Bearer token.
- Test both statuses:
  - `draft`
  - `final`

6. Check per-user history:

- `GET <BASE_URL>/api/tenders/history?limit=40`
- Use Bearer token.

Expected:
- Only records for logged-in reviewer.

## 5. Functional Acceptance Criteria

Deployment is acceptable when all are true:

- `/health` returns `{"status":"ok"}`.
- `/demo/` loads without blank page.
- Register/login works and returns valid token.
- Authenticated processing succeeds for PDF and DOCX.
- Draft/final save works and status updates correctly.
- History endpoint returns user-scoped records.
- OCR fallback works on scanned PDF (or known limitation documented).

## 6. Common Production Issues

- 401 Unauthorized on frontend calls
  - Cause: missing/expired token.
  - Fix: login again and ensure `Authorization: Bearer <token>` is sent.

- CORS errors in browser
  - Cause: origin missing in `CORS_ORIGINS`.
  - Fix: add exact frontend origin and redeploy.

- OCR not triggering for scanned PDFs
  - Cause: Tesseract/Poppler missing in runtime.
  - Fix: verify container packages and PATH binaries.

- OpenAI extraction fallback messages in notes
  - Cause: missing/invalid `OPENAI_API_KEY`.
  - Fix: set valid key and restart service.

## 7. Security and Operations Notes

- Do not commit real `OPENAI_API_KEY` values.
- Rotate API keys periodically.
- Avoid using free-form shared accounts for reviewers; create unique usernames per reviewer.
- Backup `backend/storage/app.db` if long-term history retention is needed.
