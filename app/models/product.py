import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, String, Text
from sqlmodel import Field, SQLModel


class Product(SQLModel, table=True):
    __tablename__ = "products"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    shop_id: uuid.UUID = Field(
        foreign_key="shops.id",
        index=True,
        nullable=False,
    )
    name: str = Field(sa_column=Column(String(120), nullable=False, index=True))
    slug: str = Field(sa_column=Column(String(150), unique=True, index=True, nullable=False))
    category: str = Field(sa_column=Column(String(50), nullable=False, index=True))
    waste_material: str = Field(sa_column=Column(String(100), nullable=False))
    price: int = Field(nullable=False)
    previous_price: int | None = Field(default=None, nullable=True)
    stock: int = Field(default=0, nullable=False)
    image_url: str = Field(sa_column=Column(String(512), nullable=False))
    images: list[str] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    short_description: str | None = Field(default=None, sa_column=Column(String(255), nullable=True))
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    weight_grams: int = Field(default=200, nullable=False)
    dimensions: str | None = Field(default=None, sa_column=Column(String(50), nullable=True))
    production_time: str | None = Field(default=None, sa_column=Column(String(50), nullable=True))
    impact: str | None = Field(default=None, sa_column=Column(String(255), nullable=True))
    is_active: bool = Field(default=True, nullable=False, index=True)
    sold_count: int = Field(default=0, nullable=False)
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
