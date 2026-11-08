from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlmodel import Session

from app.database import get_session
from app.schemas.auth import AuthenticatedUser, LoginRequest, RegisterRequest
from app.services.auth_service import (
    build_google_authorization_url,
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
    upsert_google_user,
)

router = APIRouter()


@router.post("/register", response_model=AuthenticatedUser, status_code=201)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    require_trusted_origin(request)
    user = register_manual_user(session, payload)
    token = create_user_session(session, user, request.headers.get("user-agent"))
    set_session_cookie(response, token)
    return user


@router.post("/login", response_model=AuthenticatedUser)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    require_trusted_origin(request)
    user = authenticate_manual_user(session, payload)
    token = create_user_session(session, user, request.headers.get("user-agent"))
    set_session_cookie(response, token)
    return user


@router.get("/google/login")
def google_login(return_to: str | None = Query(default=None)):
    destination = return_to or get_frontend_url()
    if not is_allowed_return_url(destination):
        destination = get_frontend_url()
    return RedirectResponse(build_google_authorization_url(destination))


@router.get("/google/callback")
async def google_callback(code: str, state: str, session: Session = Depends(get_session)):
    destination = read_state(state)
    profile = await fetch_google_profile(code)
    user = upsert_google_user(session, profile)
    response = RedirectResponse(destination)
    token = create_user_session(session, user)
    set_session_cookie(response, token)
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
    clear_auth_cookies(response)


@router.post("/logout-all", status_code=204)
def logout_all(request: Request, response: Response, session: Session = Depends(get_session)) -> None:
    require_trusted_origin(request)
    user = get_current_user(request, session)
    revoke_all_user_sessions(session, user)
    clear_auth_cookies(response)
