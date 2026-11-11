import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String
from sqlmodel import Field, SQLModel


class OAuthLoginState(SQLModel, table=True):
    __tablename__ = "oauth_login_states"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    state_hash: str = Field(sa_column=Column(String(64), unique=True, index=True, nullable=False))
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), index=True, nullable=False))
    used_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

