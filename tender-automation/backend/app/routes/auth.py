import os
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.schemas import (
    AuthResponse,
    MessageResponse,
    UserLoginRequest,
    UserProfileResponse,
    UserRegisterRequest,
)
from app.services.auth_service import (
    create_session_token,
    get_current_user,
    log_failed_attempt,
    register_user,
    revoke_session_token,
)
from app.services.rate_limit import RateLimitRule, enforce_rate_limit

router = APIRouter()

SESSION_COOKIE_NAME = "session_token"
CSRF_COOKIE_NAME = "csrf_token"

SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "lax")

LOGIN_RULE = RateLimitRule(name="login", max_requests=5, window_seconds=60)
REGISTER_RULE = RateLimitRule(name="register", max_requests=3, window_seconds=60)


@router.post("/register", response_model=MessageResponse, status_code=201)
def register(payload: UserRegisterRequest, request: Request) -> MessageResponse:
    ip_address = request.client.host if request.client else "0.0.0.0"
    enforce_rate_limit(ip_address, REGISTER_RULE)

    username = payload.username.strip().lower()
    if len(username) < 3:
        log_failed_attempt("register", username, ip_address, "username_too_short")
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")

    created = register_user(username, payload.password)
    if not created:
        log_failed_attempt("register", username, ip_address, "username_exists")
        raise HTTPException(status_code=409, detail="Username already exists")

    return MessageResponse(message="Account created")


@router.post("/login", response_model=AuthResponse)
def login(payload: UserLoginRequest, request: Request, response: Response) -> AuthResponse:
    ip_address = request.client.host if request.client else "0.0.0.0"
    enforce_rate_limit(ip_address, LOGIN_RULE)

    username = payload.username.strip().lower()
    session = create_session_token(username, payload.password)
    if session is None:
        log_failed_attempt("login", username, ip_address, "invalid_credentials")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token, _user_id = session
    csrf_token = secrets.token_urlsafe(24)

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
        max_age=7 * 24 * 3600,
        path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
        max_age=7 * 24 * 3600,
        path="/",
    )

    return AuthResponse(token=token, username=username, csrf_token=csrf_token)


@router.post("/logout", response_model=MessageResponse)
def logout(request: Request, response: Response) -> MessageResponse:
    token = request.cookies.get(SESSION_COOKIE_NAME, "")
    csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME, "")
    csrf_header = request.headers.get("X-CSRF-Token", "")

    if token and (not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header)):
        raise HTTPException(status_code=403, detail="CSRF validation failed")

    if token:
        revoke_session_token(token)

    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserProfileResponse)
def me(current_user: dict = Depends(get_current_user)) -> UserProfileResponse:
    return UserProfileResponse(id=current_user["id"], username=current_user["username"])
