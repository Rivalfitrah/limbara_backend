import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, UniqueConstraint
from sqlmodel import Field, SQLModel


class AuthRateLimit(SQLModel, table=True):
    __tablename__ = "auth_rate_limits"
    __table_args__ = (
        UniqueConstraint("action", "identifier_hash", name="uq_auth_rate_limit_action_identifier"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    action: str = Field(sa_column=Column(String(32), nullable=False, index=True))
    identifier_hash: str = Field(sa_column=Column(String(64), nullable=False, index=True))
    attempts: int = Field(default=0, nullable=False)
    window_started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    blocked_until: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True, index=True),
    )

