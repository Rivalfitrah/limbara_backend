import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.marketplace_image import MAX_PRODUCT_IMAGES, validate_cloudinary_image_url


class ProductCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    category: str = Field(min_length=2, max_length=50)
    waste_material: str = Field(min_length=2, max_length=100)
    price: int = Field(ge=500)
    previous_price: int | None = Field(default=None, ge=500)
    stock: int = Field(default=0, ge=0)
    image_url: str = Field(min_length=5, max_length=512)
    images: list[str] | None = Field(default=None, max_length=MAX_PRODUCT_IMAGES)
    short_description: str | None = Field(default=None, max_length=255)
    description: str | None = None
    weight_grams: int = Field(default=200, ge=1)
    dimensions: str | None = Field(default=None, max_length=50)
    production_time: str | None = Field(default=None, max_length=50)
    impact: str | None = Field(default=None, max_length=255)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        clean = " ".join(value.split())
        if len(clean) < 3:
            raise ValueError("Nama produk minimal 3 karakter.")
        return clean

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: str) -> str:
        return validate_cloudinary_image_url(value)

    @field_validator("images")
    @classmethod
    def validate_images(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        if not value:
            raise ValueError("Produk minimal memiliki satu gambar.")
        return [validate_cloudinary_image_url(url) for url in value]

    @model_validator(mode="after")
    def synchronize_primary_image(self):
        self.images = self.images or [self.image_url]
        self.image_url = self.images[0]
        return self


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=120)
    category: str | None = Field(default=None, min_length=2, max_length=50)
    waste_material: str | None = Field(default=None, min_length=2, max_length=100)
    price: int | None = Field(default=None, ge=500)
    previous_price: int | None = Field(default=None, ge=500)
    stock: int | None = Field(default=None, ge=0)
    image_url: str | None = Field(default=None, min_length=5, max_length=512)
    images: list[str] | None = Field(default=None, max_length=MAX_PRODUCT_IMAGES)
    short_description: str | None = Field(default=None, max_length=255)
    description: str | None = None
    weight_grams: int | None = Field(default=None, ge=1)
    dimensions: str | None = Field(default=None, max_length=50)
    production_time: str | None = Field(default=None, max_length=50)
    impact: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: str | None) -> str | None:
        return validate_cloudinary_image_url(value) if value is not None else None

    @field_validator("images")
    @classmethod
    def validate_images(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        if not value:
            raise ValueError("Produk minimal memiliki satu gambar.")
        return [validate_cloudinary_image_url(url) for url in value]


class ProductToggleActive(BaseModel):
    is_active: bool


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    shop_id: uuid.UUID
    name: str
    slug: str
    category: str
    waste_material: str
    price: int
    previous_price: int | None
    stock: int
    image_url: str
    images: list[str] | None
    short_description: str | None
    description: str | None
    weight_grams: int
    dimensions: str | None
    production_time: str | None
    impact: str | None
    is_active: bool
    sold_count: int
    created_at: datetime
    updated_at: datetime


class DashboardSummary(BaseModel):
    total_products: int
    active_products: int
    inactive_products: int
    total_stock: int
    total_sold: int
    shop_name: str
    shop_slug: str
    waste_focus: str | None
    city: str


class MarketplaceShopSummary(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    city: str
    province: str
    logo_url: str | None
    is_verified: bool
    total_products: int
    created_at: datetime


class MarketplaceProductResponse(ProductResponse):
    shop: MarketplaceShopSummary


class MarketplaceProductPage(BaseModel):
    items: list[MarketplaceProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
