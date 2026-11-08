import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, String, UniqueConstraint
from sqlmodel import Field, SQLModel


class AuthAccount(SQLModel, table=True):
    __tablename__ = "auth_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_auth_accounts_user_provider"),
        UniqueConstraint("provider", "provider_subject", name="uq_auth_accounts_provider_subject"),
        CheckConstraint(
            "(provider = 'LOCAL' AND password_hash IS NOT NULL) OR "
            "(provider = 'GOOGLE' AND provider_subject IS NOT NULL AND password_hash IS NULL)",
            name="ck_auth_accounts_credentials",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    provider: str = Field(sa_column=Column(String(20), nullable=False))
    provider_subject: str | None = Field(default=None, sa_column=Column(String(255), nullable=True))
    password_hash: str | None = Field(default=None, sa_column=Column(String(255), nullable=True))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
