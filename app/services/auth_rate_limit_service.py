import hashlib
import hmac
import math
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.auth_rate_limit import AuthRateLimit
from app.services.auth_service import get_jwt_secret
from app.services.auth_audit_service import log_auth_event


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def hash_rate_limit_identifier(action: str, identifier: str) -> str:
    derived_key = hmac.new(
        get_jwt_secret().encode(),
        b"auth-rate-limit-v1",
        hashlib.sha256,
    ).digest()
    return hmac.new(
        derived_key,
        f"{action}:{identifier.casefold().strip()}".encode(),
        hashlib.sha256,
    ).hexdigest()


def client_identifier(request: Request) -> str:
    return request.client.host if request.client else "unknown-client"


def consume_rate_limit(
    session: Session,
    *,
    action: str,
    identifier: str,
    limit: int,
    window: timedelta,
    _retried: bool = False,
) -> None:
    now = datetime.now(timezone.utc)
    identifier_hash = hash_rate_limit_identifier(action, identifier)
    bucket = session.exec(
        select(AuthRateLimit).where(
            AuthRateLimit.action == action,
            AuthRateLimit.identifier_hash == identifier_hash,
        )
    ).first()

    if bucket is None:
        bucket = AuthRateLimit(
            action=action,
            identifier_hash=identifier_hash,
            attempts=1,
            window_started_at=now,
        )
    else:
        blocked_until = _aware(bucket.blocked_until) if bucket.blocked_until else None
        if blocked_until and blocked_until > now:
            log_auth_event(action, "rate_limited", identifier_hash)
            retry_after = max(1, math.ceil((blocked_until - now).total_seconds()))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Terlalu banyak percobaan. Silakan coba lagi nanti.",
                headers={"Retry-After": str(retry_after)},
            )
        if now - _aware(bucket.window_started_at) >= window:
            bucket.window_started_at = now
            bucket.attempts = 1
            bucket.blocked_until = None
        else:
            bucket.attempts += 1

    if bucket.attempts > limit:
        bucket.blocked_until = now + window

    session.add(bucket)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        if _retried:
            raise
        return consume_rate_limit(
            session,
            action=action,
            identifier=identifier,
            limit=limit,
            window=window,
            _retried=True,
        )

    if bucket.blocked_until:
        log_auth_event(action, "rate_limited", identifier_hash)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Terlalu banyak percobaan. Silakan coba lagi nanti.",
            headers={"Retry-After": str(math.ceil(window.total_seconds()))},
        )


def reset_rate_limit(session: Session, *, action: str, identifier: str) -> None:
    identifier_hash = hash_rate_limit_identifier(action, identifier)
    bucket = session.exec(
        select(AuthRateLimit).where(
            AuthRateLimit.action == action,
            AuthRateLimit.identifier_hash == identifier_hash,
        )
    ).first()
    if bucket is not None:
        session.delete(bucket)
        session.commit()

