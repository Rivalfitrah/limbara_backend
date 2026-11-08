import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse

import httpx
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import HTTPException, Request, Response, status
from jose import JWTError, jwt
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models import AuthAccount, User, UserSession
from app.schemas.auth import LoginRequest, RegisterRequest

ALGORITHM = "HS256"
LEGACY_COOKIE_NAME = "limbara_access_token"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

password_hasher = PasswordHasher(time_cost=2, memory_cost=19_456, parallelism=1, hash_len=32, salt_len=16)


def normalize_email(value: str) -> str:
    return value.strip().lower()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


_DUMMY_PASSWORD_HASH = hash_password("limbara-dummy-password")


def require_trusted_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin:
        return

    allowed_origins = {get_frontend_url()}
    allowed_origins.update(
        item.strip().rstrip("/")
        for item in os.getenv("ALLOWED_ORIGINS", "").split(",")
        if item.strip()
    )
    if origin.rstrip("/") not in allowed_origins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin permintaan tidak diizinkan.")


def register_manual_user(session: Session, payload: RegisterRequest) -> User:
    existing_user = session.exec(select(User).where(User.email == payload.email)).first()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Akun tidak dapat dibuat dengan data tersebut.",
        )

    now = datetime.now(timezone.utc)
    user = User(
        email=payload.email,
        name=payload.name,
        email_verified_at=None,
        last_login_at=now,
    )
    session.add(user)

    try:
        session.flush()
        session.add(
            AuthAccount(
                user_id=user.id,
                provider="LOCAL",
                password_hash=hash_password(payload.password),
            )
        )
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Akun tidak dapat dibuat dengan data tersebut.",
        ) from error

    session.refresh(user)
    return user


def authenticate_manual_user(session: Session, payload: LoginRequest) -> User:
    statement = (
        select(User, AuthAccount)
        .join(AuthAccount, AuthAccount.user_id == User.id)
        .where(User.email == payload.email, AuthAccount.provider == "LOCAL")
    )
    result = session.exec(statement).first()
    password_hash = result[1].password_hash if result else _DUMMY_PASSWORD_HASH

    if result is None or password_hash is None or not verify_password(password_hash, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password tidak valid.",
        )

    user, account = result
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password tidak valid.",
        )

    if password_hasher.check_needs_rehash(account.password_hash):
        account.password_hash = hash_password(payload.password)
        session.add(account)

    user.last_login_at = datetime.now(timezone.utc)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_user_session(session: Session, user: User, user_agent: str | None = None) -> str:
    token = create_session_token()
    now = datetime.now(timezone.utc)
    session.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=now + timedelta(days=7),
            last_seen_at=now,
            user_agent=user_agent[:512] if user_agent else None,
        )
    )
    session.commit()
    return token


def get_user_from_session_token(session: Session, token: str) -> User | None:
    stored_session = session.exec(
        select(UserSession).where(UserSession.token_hash == hash_session_token(token))
    ).first()
    if stored_session is None or stored_session.revoked_at is not None:
        return None

    expires_at = stored_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if expires_at <= now:
        return None

    user = session.get(User, stored_session.user_id)
    if user is None or not user.is_active:
        return None

    last_seen_at = stored_session.last_seen_at
    if last_seen_at.tzinfo is None:
        last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)
    if now - last_seen_at >= timedelta(minutes=15):
        stored_session.last_seen_at = now
        session.add(stored_session)
        session.commit()
    return user


def revoke_session_token(session: Session, token: str) -> None:
    stored_session = session.exec(
        select(UserSession).where(UserSession.token_hash == hash_session_token(token))
    ).first()
    if stored_session is None or stored_session.revoked_at is not None:
        return
    stored_session.revoked_at = datetime.now(timezone.utc)
    session.add(stored_session)
    session.commit()


def revoke_all_user_sessions(session: Session, user: User) -> None:
    active_sessions = session.exec(
        select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
    ).all()
    now = datetime.now(timezone.utc)
    for stored_session in active_sessions:
        stored_session.revoked_at = now
        session.add(stored_session)
    session.commit()


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
    subject = profile["sub"]
    email = normalize_email(profile["email"])
    account = session.exec(
        select(AuthAccount).where(
            AuthAccount.provider == "GOOGLE",
            AuthAccount.provider_subject == subject,
        )
    ).first()
    user = session.get(User, account.user_id) if account else None

    if user is None:
        if session.exec(select(User).where(User.email == email)).first() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email telah digunakan oleh metode login lain.",
            )

        user = User(
            google_id=subject,
            email=email,
            name=profile.get("name") or email.split("@")[0],
            avatar_url=profile.get("picture"),
            email_verified_at=datetime.now(timezone.utc),
            last_login_at=datetime.now(timezone.utc),
        )
        session.add(user)
        session.flush()
        session.add(
            AuthAccount(
                user_id=user.id,
                provider="GOOGLE",
                provider_subject=subject,
            )
        )
    else:
        user.google_id = subject
        user.email = email
        user.name = profile.get("name") or user.name
        user.avatar_url = profile.get("picture") or user.avatar_url
        user.email_verified_at = user.email_verified_at or datetime.now(timezone.utc)
        user.last_login_at = datetime.now(timezone.utc)
        session.add(user)

    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Akun Google tidak dapat dihubungkan.",
        ) from error
    session.refresh(user)
    return user


def get_session_cookie_name() -> str:
    return "__Host-limbara_session" if cookie_options()["secure"] else "limbara_session"


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(get_session_cookie_name(), token, **cookie_options())


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(get_session_cookie_name(), path="/", secure=cookie_options()["secure"])
    response.delete_cookie(LEGACY_COOKIE_NAME, path="/")


def _get_legacy_jwt_user(request: Request, session: Session) -> User | None:
    token = request.cookies.get(LEGACY_COOKIE_NAME)
    if not token:
        return None

    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[ALGORITHM])
        user_id = payload["sub"]
    except (JWTError, KeyError):
        return None
    return session.get(User, user_id)


def get_current_user(request: Request, session: Session) -> User:
    token = request.cookies.get(get_session_cookie_name())
    user = get_user_from_session_token(session, token) if token else _get_legacy_jwt_user(request, session)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesi tidak valid atau sudah berakhir.")
    return user


def cookie_options() -> dict:
    secure = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    configured_samesite = os.getenv("COOKIE_SAMESITE", "none" if secure else "lax").lower()
    samesite = configured_samesite if configured_samesite in {"lax", "strict", "none"} else "lax"
    if samesite == "none" and not secure:
        samesite = "lax"
    return {
        "httponly": True,
        "secure": secure,
        "samesite": samesite,
        "max_age": 60 * 60 * 24 * 7,
        "path": "/",
    }
