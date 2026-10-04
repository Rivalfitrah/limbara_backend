import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel


class ScanHistory(SQLModel, table=True):
    __tablename__ = "scan_histories"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    image_url: str
    detected_objects: list[str] = Field(sa_column=Column(JSON, nullable=False))
    danger_level: str | None = None
    is_recyclable: bool | None = None
    insight_summary: str | None = None
    full_insight_data: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False))
