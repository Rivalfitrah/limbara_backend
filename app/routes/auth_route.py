from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlmodel import Session

from app.database import get_session
from app.schemas.auth import AuthenticatedUser
from app.services.auth_service import (
    COOKIE_NAME,
    build_google_authorization_url,
    cookie_options,
    create_access_token,
    fetch_google_profile,
    get_current_user,
    get_frontend_url,
    is_allowed_return_url,
    read_state,
    upsert_google_user,
)

router = APIRouter()


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
    response.set_cookie(COOKIE_NAME, create_access_token(user), **cookie_options())
    return response


@router.get("/me", response_model=AuthenticatedUser)
def current_user(request: Request, session: Session = Depends(get_session)):
    return get_current_user(request, session)


@router.post("/logout", status_code=204)
def logout() -> Response:
    response = Response(status_code=204)
    response.delete_cookie(COOKIE_NAME, path="/")
    return response
