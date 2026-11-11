from urllib.parse import quote
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlmodel import Session

from app.database import get_session
from app.schemas.auth import AuthenticatedUser, LoginRequest, RegisterRequest, RegistrationResponse
from app.services.auth_service import (
    build_google_authorization_url,
    clear_oauth_state_cookie,
    clear_auth_cookies,
    create_user_session,
    authenticate_manual_user,
    fetch_google_profile,
    get_current_user,
    get_frontend_url,
    get_session_cookie_name,
    is_allowed_return_url,
    read_state,
    register_manual_user,
    require_trusted_origin,
    revoke_all_user_sessions,
    revoke_session_token,
    set_session_cookie,
    set_oauth_state_cookie,
    OAUTH_STATE_COOKIE_NAME,
    upsert_google_user,
)
from app.services.auth_rate_limit_service import client_identifier, consume_rate_limit, reset_rate_limit
from app.services.auth_audit_service import log_auth_event

router = APIRouter()


@router.post("/register", response_model=RegistrationResponse, status_code=201)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    require_trusted_origin(request)
    consume_rate_limit(
        session,
        action="register_ip",
        identifier=client_identifier(request),
        limit=5,
        window=timedelta(hours=1),
    )
    register_manual_user(session, payload)
    clear_auth_cookies(response)
    log_auth_event("register", "succeeded", payload.email)
    return RegistrationResponse(message="Akun berhasil dibuat. Silakan masuk.")


@router.post("/login", response_model=AuthenticatedUser)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    require_trusted_origin(request)
    consume_rate_limit(
        session,
        action="login_account",
        identifier=payload.email,
        limit=5,
        window=timedelta(minutes=15),
    )
    consume_rate_limit(
        session,
        action="login_ip",
        identifier=client_identifier(request),
        limit=20,
        window=timedelta(minutes=15),
    )
    try:
        user = authenticate_manual_user(session, payload)
    except HTTPException:
        log_auth_event("login", "failed", payload.email)
        raise
    reset_rate_limit(session, action="login_account", identifier=payload.email)
    token = create_user_session(session, user, request.headers.get("user-agent"))
    set_session_cookie(response, token)
    log_auth_event("login", "succeeded", payload.email)
    return user


@router.get("/google/login")
def google_login(
    request: Request,
    return_to: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    consume_rate_limit(
        session,
        action="google_ip",
        identifier=client_identifier(request),
        limit=20,
        window=timedelta(minutes=15),
    )
    destination = return_to or get_frontend_url()
    if not is_allowed_return_url(destination):
        destination = get_frontend_url()
    authorization_url, state = build_google_authorization_url(session, destination)
    response = RedirectResponse(authorization_url)
    set_oauth_state_cookie(response, state)
    return response


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    request: Request,
    session: Session = Depends(get_session),
):
    frontend_url = get_frontend_url()
    login_url = f"{frontend_url}/login"
    try:
        destination, nonce = read_state(
            session,
            state,
            request.cookies.get(OAUTH_STATE_COOKIE_NAME),
        )
    except HTTPException as exc:
        response = RedirectResponse(f"{login_url}?auth_error={quote(exc.detail)}")
        clear_oauth_state_cookie(response)
        return response

    try:
        profile = await fetch_google_profile(code, nonce)
        user = upsert_google_user(session, profile)
        response = RedirectResponse(destination)
        token = create_user_session(session, user)
        set_session_cookie(response, token)
        clear_oauth_state_cookie(response)
        log_auth_event("google_login", "succeeded", user.id.hex)
        return response
    except HTTPException as exc:
        response = RedirectResponse(f"{login_url}?auth_error={quote(exc.detail)}")
        clear_oauth_state_cookie(response)
        return response
    except Exception:
        response = RedirectResponse(f"{login_url}?auth_error={quote('Terjadi kesalahan saat memproses login Google.')}")
        clear_oauth_state_cookie(response)
        return response


@router.get("/me", response_model=AuthenticatedUser)
def current_user(request: Request, session: Session = Depends(get_session)):
    return get_current_user(request, session)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, session: Session = Depends(get_session)) -> None:
    require_trusted_origin(request)
    token = request.cookies.get(get_session_cookie_name())
    if token:
        revoke_session_token(session, token)
    log_auth_event("logout", "succeeded")
    clear_auth_cookies(response)


@router.post("/logout-all", status_code=204)
def logout_all(request: Request, response: Response, session: Session = Depends(get_session)) -> None:
    require_trusted_origin(request)
    user = get_current_user(request, session)
    revoke_all_user_sessions(session, user)
    log_auth_event("logout_all", "succeeded", user.id.hex)
    clear_auth_cookies(response)
