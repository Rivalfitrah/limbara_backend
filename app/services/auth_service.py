import asyncio
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
from google.auth import exceptions as google_auth_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models import AuthAccount, OAuthLoginState, User, UserSession
from app.schemas.auth import LoginRequest, RegisterRequest

ALGORITHM = "HS256"
LEGACY_COOKIE_NAME = "limbara_access_token"
OAUTH_STATE_COOKIE_NAME = "limbara_oauth_state"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

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

    user = User(
        email=payload.email,
        name=payload.name,
        email_verified_at=None,
        last_login_at=None,
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
    session.exec(select(User).where(User.id == user.id).with_for_update()).one()
    active_sessions = session.exec(
        select(UserSession)
        .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        .order_by(UserSession.created_at, UserSession.id)
    ).all()
    for oldest_session in active_sessions[: max(0, len(active_sessions) - 2)]:
        oldest_session.revoked_at = now
        session.add(oldest_session)
    session.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=now + timedelta(hours=24),
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
    if now - last_seen_at > timedelta(hours=2):
        stored_session.revoked_at = now
        session.add(stored_session)
        session.commit()
        return None
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


def hash_oauth_state(state: str) -> str:
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


def create_state(session: Session, return_to: str) -> tuple[str, str]:
    nonce = secrets.token_urlsafe(24)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    payload = {
        "return_to": return_to,
        "nonce": nonce,
        "exp": expires_at,
    }
    state = jwt.encode(payload, get_jwt_secret(), algorithm=ALGORITHM)
    session.add(OAuthLoginState(state_hash=hash_oauth_state(state), expires_at=expires_at))
    session.commit()
    return state, nonce


def read_state(session: Session, state: str, correlation_state: str | None) -> tuple[str, str]:
    if not correlation_state or not secrets.compare_digest(state, correlation_state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="State OAuth tidak valid.")
    try:
        payload = jwt.decode(state, get_jwt_secret(), algorithms=[ALGORITHM])
        return_to = payload["return_to"]
        nonce = payload["nonce"]
    except (JWTError, KeyError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="State OAuth tidak valid.") from error

    if not is_allowed_return_url(return_to):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tujuan redirect tidak valid.")
    stored_state = session.exec(
        select(OAuthLoginState).where(OAuthLoginState.state_hash == hash_oauth_state(state))
    ).first()
    now = datetime.now(timezone.utc)
    if stored_state is None or stored_state.used_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="State OAuth tidak valid.")
    expires_at = stored_state.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="State OAuth telah kedaluwarsa.")
    stored_state.used_at = now
    session.add(stored_state)
    session.commit()
    return return_to, nonce


def build_google_authorization_url(session: Session, return_to: str) -> tuple[str, str]:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    if not client_id or not redirect_uri:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google OAuth belum dikonfigurasi.")

    state, nonce = create_state(session, return_to)
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "access_type": "offline",
            "prompt": "select_account",
        }
    )
    return f"{GOOGLE_AUTH_URL}?{query}", state


async def fetch_google_profile(code: str, expected_nonce: str) -> dict:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    if not client_id or not client_secret or not redirect_uri:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google OAuth belum dikonfigurasi.")

    token_data = None
    for attempt in range(3):
        try:
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
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Kode otorisasi Google tidak valid atau telah kedaluwarsa.",
                    )
                token_data = token_response.json()
                break
        except HTTPException:
            raise
        except httpx.RequestError as exc:
            if attempt == 2:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Gagal terhubung ke server autentikasi Google. Silakan periksa koneksi internet Anda.",
                ) from exc
            await asyncio.sleep(0.5 * (attempt + 1))

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gagal menerima respon token dari Google.",
        )

    id_token = token_data.get("id_token")
    if not isinstance(id_token, str) or not id_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token identitas Google tidak valid.")

    try:
        claims = await asyncio.to_thread(
            google_id_token.verify_oauth2_token,
            id_token,
            google_requests.Request(),
            client_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token identitas Google tidak valid.") from error
    except google_auth_exceptions.GoogleAuthError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Verifikasi Google tidak tersedia.") from error

    email_verified_claim = claims.get("email_verified", False)
    email_verified = email_verified_claim is True or str(email_verified_claim).lower() == "true"
    profile = {
        "sub": str(claims.get("sub")) if claims.get("sub") else None,
        "email": str(claims.get("email")) if claims.get("email") else None,
        "email_verified": email_verified,
        "name": claims.get("name"),
        "picture": claims.get("picture"),
    }

    if not secrets.compare_digest(str(claims.get("nonce", "")), expected_nonce):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nonce OAuth tidak valid.")

    if not profile.get("sub") or not profile.get("email") or not profile.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email Google harus terverifikasi.",
        )

    return profile


def set_oauth_state_cookie(response: Response, state: str) -> None:
    options = cookie_options()
    response.set_cookie(
        OAUTH_STATE_COOKIE_NAME,
        state,
        httponly=True,
        secure=options["secure"],
        samesite="lax",
        max_age=600,
        path="/api/auth/google",
    )


def clear_oauth_state_cookie(response: Response) -> None:
    response.delete_cookie(
        OAUTH_STATE_COOKIE_NAME,
        path="/api/auth/google",
        secure=cookie_options()["secure"],
        samesite="lax",
    )


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


def get_current_user(request: Request, session: Session) -> User:
    token = request.cookies.get(get_session_cookie_name())
    user = get_user_from_session_token(session, token) if token else None
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
        "max_age": 60 * 60 * 24,
        "path": "/",
    }
