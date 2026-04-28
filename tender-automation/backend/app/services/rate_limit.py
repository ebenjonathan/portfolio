from __future__ import annotations

import time
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import text

from app.services.database import get_connection


@dataclass
class RateLimitRule:
    name: str
    max_requests: int
    window_seconds: int


def _window_key(ip_address: str, rule: RateLimitRule) -> str:
    return f"{rule.name}:{ip_address}"


def enforce_rate_limit(ip_address: str, rule: RateLimitRule) -> None:
    now = int(time.time())
    bucket_key = _window_key(ip_address, rule)

    with get_connection() as conn:
        row = conn.execute(
            text(
                "SELECT count, window_start FROM auth_rate_limits"
                " WHERE bucket_key = :bucket_key"
            ),
            {"bucket_key": bucket_key},
        ).mappings().fetchone()

        if row is None:
            conn.execute(
                text(
                    "INSERT INTO auth_rate_limits (bucket_key, count, window_start)"
                    " VALUES (:bucket_key, :count, :window_start)"
                ),
                {"bucket_key": bucket_key, "count": 1, "window_start": now},
            )
            conn.commit()
            return

        count = int(row["count"])
        window_start = int(row["window_start"])

        if now - window_start >= rule.window_seconds:
            conn.execute(
                text(
                    "UPDATE auth_rate_limits SET count = :count, window_start = :window_start"
                    " WHERE bucket_key = :bucket_key"
                ),
                {"count": 1, "window_start": now, "bucket_key": bucket_key},
            )
            conn.commit()
            return

        if count >= rule.max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests for {rule.name}. Try again later.",
            )

        conn.execute(
            text(
                "UPDATE auth_rate_limits SET count = :count"
                " WHERE bucket_key = :bucket_key"
            ),
            {"count": count + 1, "bucket_key": bucket_key},
        )
        conn.commit()
