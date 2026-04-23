# Tender Automation Project Starter

Backend-first scaffold created in this order:

1. Backend API (`/backend`) with upload + extraction endpoint.
2. Frontend client (`/frontend`) that uploads files and renders JSON output.

## Structure

- `backend/`: FastAPI app, schemas, parser service, API routes.
- `frontend/`: Upload form + result viewer.

## Current status

- Backend endpoint: `POST /api/tenders/process`
- Frontend connected to backend endpoint.
- Reviewer auth and per-user session history are enabled.
- Save as draft/final is implemented.
- Deployed container serves frontend at `/demo/` and API docs at `/docs`.

## Online deployment

- Dockerfile: `tender-automation/Dockerfile`
- Render blueprint: `render.yaml` (repo root)
- On deployment, open demo at `/demo/`

## Operations checklist

- Production environment checklist: `tender-automation/PRODUCTION_ENV_CHECKLIST.md`
