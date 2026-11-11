import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Column, DateTime, String, Text
from sqlmodel import Field, SQLModel


class Shop(SQLModel, table=True):
    __tablename__ = "shops"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        unique=True,
        index=True,
        nullable=False,
    )
    name: str = Field(sa_column=Column(String(100), nullable=False, index=True))
    slug: str = Field(sa_column=Column(String(120), unique=True, index=True, nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    waste_focus: str | None = Field(default=None, sa_column=Column(String(255), nullable=True))
    province: str = Field(sa_column=Column(String(100), nullable=False))
    city: str = Field(sa_column=Column(String(100), nullable=False))
    district: str | None = Field(default=None, sa_column=Column(String(100), nullable=True))
    address: str = Field(sa_column=Column(Text, nullable=False))
    postal_code: str | None = Field(default=None, sa_column=Column(String(10), nullable=True))
    phone_number: str = Field(sa_column=Column(String(25), nullable=False))
    email: str | None = Field(default=None, sa_column=Column(String(255), nullable=True))
    courier_options: list[str] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    logo_url: str | None = Field(default=None, sa_column=Column(String(512), nullable=True))
    banner_url: str | None = Field(default=None, sa_column=Column(String(512), nullable=True))
    is_verified: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            onupdate=lambda: datetime.now(timezone.utc),
        ),
    )
