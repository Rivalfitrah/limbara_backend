import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Text
from sqlmodel import Field, SQLModel


class Order(SQLModel, table=True):
    __tablename__ = "orders"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_number: str = Field(sa_column=Column(String(50), unique=True, index=True, nullable=False))
    buyer_id: uuid.UUID = Field(
        foreign_key="users.id",
        index=True,
        nullable=False,
    )
    shop_id: uuid.UUID = Field(
        foreign_key="shops.id",
        index=True,
        nullable=False,
    )
    status: str = Field(
        default="PENDING",
        sa_column=Column(String(30), default="PENDING", index=True, nullable=False),
    )
    total_product_amount: int = Field(default=0, nullable=False)
    shipping_cost: int = Field(default=0, nullable=False)
    total_amount: int = Field(default=0, nullable=False)
    courier: str = Field(sa_column=Column(String(50), nullable=False))
    courier_service: str = Field(sa_column=Column(String(50), nullable=False))
    recipient_name: str = Field(sa_column=Column(String(120), nullable=False))
    recipient_phone: str = Field(sa_column=Column(String(30), nullable=False))
    shipping_address: str = Field(sa_column=Column(Text, nullable=False))
    shipping_province: str = Field(sa_column=Column(String(100), nullable=False))
    shipping_city: str = Field(sa_column=Column(String(100), nullable=False))
    shipping_postal_code: str | None = Field(default=None, sa_column=Column(String(20), nullable=True))
    notes: str | None = Field(default=None, sa_column=Column(String(255), nullable=True))
    snap_token: str | None = Field(default=None, sa_column=Column(String(255), nullable=True))
    snap_redirect_url: str | None = Field(default=None, sa_column=Column(String(512), nullable=True))
    midtrans_transaction_id: str | None = Field(default=None, sa_column=Column(String(100), nullable=True))
    payment_type: str | None = Field(default=None, sa_column=Column(String(50), nullable=True))
    paid_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    tracking_number: str | None = Field(default=None, sa_column=Column(String(100), nullable=True))
    shipped_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    completed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
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


class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"

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
    product_name: str = Field(sa_column=Column(String(120), nullable=False))
    product_image: str | None = Field(default=None, sa_column=Column(String(512), nullable=True))
    price: int = Field(nullable=False)
    quantity: int = Field(default=1, nullable=False)
    subtotal: int = Field(nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
