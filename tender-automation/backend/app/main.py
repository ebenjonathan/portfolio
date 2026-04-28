import logging
import logging.config
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from app.routes.auth import router as auth_router
from app.routes.tenders import router as tenders_router
from app.services.database import init_db

load_dotenv()

# ── Structured logging ─────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "format": '{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","msg":%(message)r}',
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
            }
        },
        "root": {"level": LOG_LEVEL, "handlers": ["console"]},
    }
)

logger = logging.getLogger(__name__)

# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(title="AI Tender Automation API", version="0.1.0")
init_db()

# ── CORS ───────────────────────────────────────────────────────────────────
default_allow_origins = [
    "http://127.0.0.1:8795",
    "http://localhost:8795",
    "https://your-domain.pages.dev",
    "https://www.mupinilabs.com",
    "https://mupinilabs.com",
]

env_origins = os.getenv("CORS_ORIGINS", "")
extra_allow_origins = [item.strip() for item in env_origins.split(",") if item.strip()]
allow_origins = list(dict.fromkeys([*default_allow_origins, *extra_allow_origins]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Security headers ───────────────────────────────────────────────────────
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


# ── Error envelopes ────────────────────────────────────────────────────────
@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "ok": False,
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
            },
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "ok": False,
            "error": {
                "code": 422,
                "message": "Validation failed",
                "details": exc.errors(),
            },
        },
    )


# ── Routes ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(tenders_router, prefix="/api/tenders", tags=["tenders"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
