import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class ProductReview(SQLModel, table=True):
    __tablename__ = "product_reviews"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(
        foreign_key="orders.id",
        index=True,
        nullable=False,
    )
    product_id: uuid.UUID = Field(
        foreign_key="products.id",
        index=True,
        nullable=False,
    )
    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        index=True,
        nullable=False,
    )
    user_name: str = Field(sa_column=Column(String(100), nullable=False))
    user_avatar: str | None = Field(default=None, sa_column=Column(String(512), nullable=True))
    rating: int = Field(sa_column=Column(Integer, nullable=False))
    comment: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    __table_args__ = (
        UniqueConstraint("order_id", "product_id", name="uq_order_product_review"),
    )
