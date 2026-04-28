# Frontend (Vanilla)

This is a demo client that walks through a 3-stage tender review workflow:

- Extracted
- Needs Review
- Final Output

It is labeled as demo-only for stakeholder preview.

## Run

1. Ensure backend is running at your configured API base URL.
2. Serve this folder with any static server.

Example with Python:

```bash
python -m http.server 5500
```

3. Open:

- your static server URL (for example, your Pages preview URL)

4. In the UI, keep API Base URL set to your backend server URL.

## Runtime config

The frontend reads API base URL from `window.APP_CONFIG.API_BASE_URL` in `config.js`.
Set the placeholder before deploy:

`window.APP_CONFIG = { API_BASE_URL: "https://your-api.example.com" }`

## Save behavior

- `Save Draft` posts to `POST /api/tenders/{tender_id}/save` with status `draft`.
- `Save Final` posts to `POST /api/tenders/{tender_id}/save` with status `final`.

## Next frontend steps

- Add multi-step review UI (Extracted / Needs Review / Final Output).
- Add authentication and per-organization workspace.
- Add human validation workflow for extracted sections.
