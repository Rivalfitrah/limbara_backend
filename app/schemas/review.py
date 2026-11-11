import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    order_id: uuid.UUID
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=3, max_length=1000)


class ReviewResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    product_id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    user_avatar: str | None = None
    rating: int
    comment: str
    created_at: datetime


class ReviewEligibilityResponse(BaseModel):
    can_review: bool
    order_id: uuid.UUID | None = None
    message: str
