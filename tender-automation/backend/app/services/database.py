from __future__ import annotations

import logging
import os
import time

from sqlalchemy import Column, ForeignKey, Index, Integer, MetaData, String, Table, create_engine, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

metadata = MetaData()

users_table = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String, nullable=False, unique=True),
    Column("password_hash", String, nullable=False),
    Column("created_at", String, nullable=False),
)

sessions_table = Table(
    "sessions",
    metadata,
    Column("token", String, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("created_at", String, nullable=False),
    Column("expires_at", String, nullable=False),
    Index("idx_sessions_user_id", "user_id"),
)

tenders_table = Table(
    "tenders",
    metadata,
    Column("tender_id", String, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("payload_json", String, nullable=False),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
    Index("idx_tenders_user_updated", "user_id", "updated_at"),
)

auth_rate_limits_table = Table(
    "auth_rate_limits",
    metadata,
    Column("bucket_key", String, primary_key=True),
    Column("count", Integer, nullable=False),
    Column("window_start", Integer, nullable=False),
)

auth_failed_attempts_table = Table(
    "auth_failed_attempts",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("action", String, nullable=False),
    Column("username", String, nullable=False),
    Column("ip_address", String, nullable=False),
    Column("reason", String, nullable=False),
    Column("created_at", String, nullable=False),
)

# Module-level engine, can be overridden by tests before first use.
_engine: Engine | None = None


def _build_engine() -> Engine:
    database_url = os.getenv("DATABASE_URL", "sqlite:///./storage/app.db")

    # Neon and most PaaS providers emit postgres:// which SQLAlchemy requires as postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    is_sqlite = database_url.startswith("sqlite")
    kwargs: dict = {}

    if is_sqlite:
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_size"] = 5
        kwargs["max_overflow"] = 10
        kwargs["pool_pre_ping"] = True
        kwargs["pool_recycle"] = 300

    return create_engine(database_url, **kwargs)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def get_connection():
    """Return a SQLAlchemy Connection (use as context manager: ``with get_connection() as conn``)."""
    return get_engine().connect()


def init_db(retries: int = 3) -> None:
    """Create tables if they don't exist. Retries on transient failures (e.g. cold DB wake)."""
    engine = get_engine()
    for attempt in range(retries):
        try:
            metadata.create_all(engine)
            logger.info("Database schema initialised successfully")
            return
        except Exception as exc:
            if attempt < retries - 1:
                wait = 2 ** attempt
                logger.warning(
                    "DB init attempt %d/%d failed (%s). Retrying in %ds…",
                    attempt + 1,
                    retries,
                    exc,
                    wait,
                )
                time.sleep(wait)
            else:
                logger.error("DB init failed after %d attempts: %s", retries, exc)
                raise
