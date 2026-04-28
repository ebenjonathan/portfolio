# Production Deployment Checklist

## Architecture
```
Browser
  ├─► Cloudflare Pages  (portfolio + tender frontend, static)
  │       └─► API calls ──► Render  (FastAPI + Tesseract + Poppler, Docker)
  │                             ├─► Neon PostgreSQL (users, sessions, tenders)
  │                             └─► Cloudflare R2   (uploaded PDFs/TXTs, optional)
```

---

## 1. Neon PostgreSQL

1. Create a free account at https://neon.tech
2. Create a project → copy the **Connection string** (looks like `postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require`)
3. Keep it, you'll paste it as `DATABASE_URL` in Render

---

## 2. Cloudflare R2 (optional)

1. Cloudflare dashboard → R2 → Create bucket (e.g. `tender-uploads`)
2. Manage R2 API tokens → Create token with **Object Read & Write** on that bucket
3. Note: Account ID, Access Key ID, Secret Access Key, Bucket Name
4. If you skip R2, uploads still work, files are processed in-memory then discarded

---

## 3. Render (FastAPI backend)

1. New → Web Service → connect your GitHub repo
2. **Root directory**: `tender-automation`
3. **Runtime**: Docker
4. **Dockerfile path**: `./Dockerfile`
5. Set env vars in the Render dashboard (never commit secrets):
   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | Neon connection string |
   | `OPENAI_API_KEY` | Your OpenAI key |
   | `SESSION_COOKIE_SECURE` | `true` |
   | `SESSION_COOKIE_SAMESITE` | `none` |
   | `CORS_ORIGINS` | `https://your-portfolio.pages.dev` (set after Pages deploy) |
   | `R2_ACCOUNT_ID` | Cloudflare account ID (optional) |
   | `R2_ACCESS_KEY_ID` | R2 access key (optional) |
   | `R2_SECRET_ACCESS_KEY` | R2 secret key (optional) |
   | `R2_BUCKET_NAME` | `tender-uploads` (optional) |
6. Health check path: `/health`
7. Deploy → copy your Render URL (e.g. `https://tender-api.onrender.com`)

---

## 4. Frontend config

Edit `tender-automation/frontend/config.js`:
```js
window.PUBLIC_API_URL = "https://tender-api.onrender.com";
```
Commit and push.

---

## 5. Cloudflare Pages (portfolio + frontend)

1. Cloudflare dashboard → Pages → Create project → Connect Git
2. Settings:
   | Field | Value |
   |---|---|
   | Framework preset | None |
   | Root directory | `/` (repo root) |
   | Build command | `npm run build` |
  | Build output directory | `dist` |
   | Deploy command | *(leave empty)* |
3. Deploy → your site is live

If you want to deploy manually with Wrangler, use `npx wrangler pages deploy dist`.
Do not use `npx wrangler deploy` for this repo because `functions/` contains Cloudflare Pages Functions, not a Worker entrypoint.

---

## 6. Post-deploy

- Update `CORS_ORIGINS` in Render with your live Pages URL
- Test full flow: register → login → upload tender → process → save
- Verify `/health` returns `{"status": "ok"}` on the Render URL

---

## Free tier limits summary

| Service | Limit |
|---|---|
| Cloudflare Pages | Unlimited requests, 500 builds/month |
| Render (free) | 750 hrs/month, **spins down after 15 min idle** |
| Neon (free) | 0.5 GB storage, 1 project |
| R2 (free) | 10 GB storage, 1M writes/month |

> Render free tier cold starts take ~30s. Upgrade to **Starter ($7/mo)** to keep the service warm for demos.


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
