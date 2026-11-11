import hashlib
import hmac
import logging
import os


logger = logging.getLogger("limbara.auth")


def _subject_hash(identifier: str | None) -> str:
    if not identifier:
        return "anonymous"
    secret = os.getenv("JWT_SECRET_KEY", "")
    if len(secret) < 32:
        return "unavailable"
    key = hmac.new(secret.encode(), b"auth-audit-v1", hashlib.sha256).digest()
    return hmac.new(key, identifier.casefold().strip().encode(), hashlib.sha256).hexdigest()


def log_auth_event(action: str, outcome: str, identifier: str | None = None) -> None:
    logger.info(
        "auth_event action=%s outcome=%s subject=%s",
        action,
        outcome,
        _subject_hash(identifier),
    )

