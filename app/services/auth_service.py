import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import HTTPException, Request, status
from jose import JWTError, jwt
from sqlmodel import Session, select

from app.models import User

ALGORITHM = "HS256"
COOKIE_NAME = "limbara_access_token"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def get_frontend_url() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")


def get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret or len(secret) < 32:
        raise RuntimeError("JWT_SECRET_KEY harus diatur dengan minimal 32 karakter.")
    return secret


def is_allowed_return_url(url: str) -> bool:
    expected = urlparse(get_frontend_url())
    candidate = urlparse(url)
    return candidate.scheme == expected.scheme and candidate.netloc == expected.netloc


def create_state(return_to: str) -> str:
    payload = {
        "return_to": return_to,
        "nonce": secrets.token_urlsafe(24),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=ALGORITHM)


def read_state(state: str) -> str:
    try:
        payload = jwt.decode(state, get_jwt_secret(), algorithms=[ALGORITHM])
        return_to = payload["return_to"]
    except (JWTError, KeyError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="State OAuth tidak valid.") from error

    if not is_allowed_return_url(return_to):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tujuan redirect tidak valid.")
    return return_to


def build_google_authorization_url(return_to: str) -> str:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    if not client_id or not redirect_uri:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google OAuth belum dikonfigurasi.")

    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": create_state(return_to),
            "access_type": "offline",
            "prompt": "select_account",
        }
    )
    return f"{GOOGLE_AUTH_URL}?{query}"


async def fetch_google_profile(code: str) -> dict:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    if not client_id or not client_secret or not redirect_uri:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google OAuth belum dikonfigurasi.")

    async with httpx.AsyncClient(timeout=15) as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_response.is_error:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kode otorisasi Google tidak valid.")

        access_token = token_response.json().get("access_token")
        profile_response = await client.get(GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})

    if profile_response.is_error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Profil Google tidak dapat diverifikasi.")

    profile = profile_response.json()
    if not profile.get("sub") or not profile.get("email") or not profile.get("email_verified"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email Google harus terverifikasi.")
    return profile


def upsert_google_user(session: Session, profile: dict) -> User:
    user = session.exec(select(User).where(User.google_id == profile["sub"])).first()
    if user is None:
        user = User(
            google_id=profile["sub"],
            email=profile["email"],
            name=profile.get("name") or profile["email"].split("@")[0],
            avatar_url=profile.get("picture"),
        )
        session.add(user)
    else:
        user.email = profile["email"]
        user.name = profile.get("name") or user.name
        user.avatar_url = profile.get("picture") or user.avatar_url
        session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_access_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=ALGORITHM)


def get_current_user(request: Request, session: Session) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        authorization = request.headers.get("Authorization", "")
        if authorization.startswith("Bearer "):
            token = authorization.removeprefix("Bearer ")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autentikasi diperlukan.")

    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[ALGORITHM])
        user_id = payload["sub"]
    except (JWTError, KeyError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesi tidak valid atau sudah berakhir.") from error

    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Pengguna tidak ditemukan.")
    return user


def cookie_options() -> dict:
    secure = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    return {"httponly": True, "secure": secure, "samesite": "none" if secure else "lax", "max_age": 60 * 60 * 24 * 7, "path": "/"}
