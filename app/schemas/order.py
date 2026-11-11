import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class CheckoutItemPayload(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(default=1, ge=1)


class CheckoutRequest(BaseModel):
    items: list[CheckoutItemPayload] = Field(min_length=1)
    recipient_name: str = Field(min_length=2, max_length=120)
    recipient_phone: str = Field(min_length=8, max_length=30)
    shipping_address: str = Field(min_length=5)
    shipping_province: str = Field(min_length=2, max_length=100)
    shipping_city: str = Field(min_length=2, max_length=100)
    shipping_postal_code: str | None = None
    courier: str = Field(default="jnt")
    courier_service: str = Field(default="EZ")
    shipping_cost: int = Field(ge=0)
    notes: str | None = None


class OrderItemResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    product_image: str | None = None
    price: int
    quantity: int
    subtotal: int


class OrderResponse(BaseModel):
    id: uuid.UUID
    order_number: str
    status: str
    total_product_amount: int
    shipping_cost: int
    total_amount: int
    courier: str
    courier_service: str
    recipient_name: str
    recipient_phone: str
    shipping_address: str
    shipping_city: str
    shipping_province: str
    shipping_postal_code: str | None
    notes: str | None
    snap_token: str | None
    snap_redirect_url: str | None
    payment_type: str | None
    tracking_number: str | None = None
    paid_at: datetime | None = None
    shipped_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    items: list[OrderItemResponse] = []


class ShipOrderRequest(BaseModel):
    tracking_number: str = Field(min_length=3, max_length=100)


class ShippingCostRequest(BaseModel):
    origin_city_id: str = "151"  # Default Jakarta Barat
    destination_city_id: str
    weight_grams: int = 1000
    courier: str = "jnt"  # jnt, jne, pos, tiki
