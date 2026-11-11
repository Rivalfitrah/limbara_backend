import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.marketplace_image import validate_cloudinary_image_url


class ShopCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    waste_focus: str | None = Field(default=None, max_length=255)
    province: str = Field(min_length=2, max_length=100)
    city: str = Field(min_length=2, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    address: str = Field(min_length=5, max_length=500)
    postal_code: str | None = Field(default=None, max_length=10)
    phone_number: str = Field(min_length=8, max_length=25)
    email: str | None = Field(default=None, max_length=255)
    courier_options: list[str] | None = None
    logo_url: str = Field(min_length=5, max_length=512)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        clean = " ".join(value.split())
        if len(clean) < 3:
            raise ValueError("Nama toko minimal 3 karakter.")
        return clean

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        cleaned = re.sub(r"[^\d+]", "", value.strip())
        if len(cleaned) < 8:
            raise ValueError("Nomor telepon tidak valid.")
        return cleaned

    @field_validator("logo_url")
    @classmethod
    def validate_logo_url(cls, value: str) -> str:
        return validate_cloudinary_image_url(value)


class ShopUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    waste_focus: str | None = Field(default=None, max_length=255)
    province: str | None = Field(default=None, min_length=2, max_length=100)
    city: str | None = Field(default=None, min_length=2, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, min_length=5, max_length=500)
    postal_code: str | None = Field(default=None, max_length=10)
    phone_number: str | None = Field(default=None, min_length=8, max_length=25)
    email: str | None = Field(default=None, max_length=255)
    courier_options: list[str] | None = None
    logo_url: str | None = Field(default=None, min_length=5, max_length=512)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        clean = " ".join(value.split())
        if len(clean) < 3:
            raise ValueError("Nama toko minimal 3 karakter.")
        return clean

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = re.sub(r"[^\d+]", "", value.strip())
        if len(cleaned) < 8:
            raise ValueError("Nomor telepon tidak valid.")
        return cleaned

    @field_validator("logo_url")
    @classmethod
    def validate_logo_url(cls, value: str | None) -> str | None:
        return validate_cloudinary_image_url(value) if value is not None else None

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        required_fields = {"name", "province", "city", "address", "phone_number"}
        for field_name in required_fields & self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} tidak boleh kosong.")
        return self


class ShopResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    slug: str
    description: str | None
    waste_focus: str | None
    province: str
    city: str
    district: str | None
    address: str
    postal_code: str | None
    phone_number: str
    email: str | None
    courier_options: list[str] | None
    logo_url: str | None
    banner_url: str | None
    is_verified: bool
    created_at: datetime
    updated_at: datetime
