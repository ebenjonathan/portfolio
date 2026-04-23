from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.database import get_connection

TOKEN_TTL_HOURS = 24 * 7
bearer_scheme = HTTPBearer(auto_error=False)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_password(password: str, salt: str) -> str:
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return key.hex()


def create_password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = _hash_password(password, salt)
    return f"{salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, digest = password_hash.split("$", 1)
    except ValueError:
        return False
    expected = _hash_password(password, salt)
    return secrets.compare_digest(expected, digest)


def register_user(username: str, password: str) -> bool:
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    hashed = create_password_hash(password)
    with get_connection() as conn:
        exists = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if exists:
            return False
        conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, hashed, _now_iso()),
        )
        conn.commit()
    return True


def log_failed_attempt(action: str, username: str, ip_address: str, reason: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO auth_failed_attempts (action, username, ip_address, reason, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (action, username, ip_address, reason, _now_iso()),
        )
        conn.commit()


def create_session_token(username: str, password: str) -> tuple[str, int] | None:
    with get_connection() as conn:
        user = conn.execute(
            "SELECT id, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if user is None:
            return None

        if not verify_password(password, user["password_hash"]):
            return None

        token = secrets.token_urlsafe(48)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=TOKEN_TTL_HOURS)
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, user["id"], now.isoformat(), expires.isoformat()),
        )
        conn.commit()
        return token, user["id"]


def revoke_session_token(token: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()


def get_user_from_token(token: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT u.id AS user_id, u.username, s.expires_at
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = ?
            """,
            (token,),
        ).fetchone()

        if row is None:
            return None

        if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return None

        return {"id": row["user_id"], "username": row["username"]}


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    token = None
    via_cookie = False

    if credentials is not None:
        token = credentials.credentials
    else:
        cookie_token = request.cookies.get("session_token", "")
        if cookie_token:
            token = cookie_token
            via_cookie = True

    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    if via_cookie and request.method.upper() not in {"GET", "HEAD", "OPTIONS"}:
        csrf_cookie = request.cookies.get("csrf_token", "")
        csrf_header = request.headers.get("X-CSRF-Token", "")
        if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
            raise HTTPException(status_code=403, detail="CSRF validation failed")

    user = get_user_from_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired authorization token")

    return user
