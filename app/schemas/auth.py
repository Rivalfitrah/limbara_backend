import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _normalize_and_validate_email(value: str) -> str:
    email = value.strip().lower()
    local_part, separator, domain = email.partition("@")
    if not separator or not local_part or "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise ValueError("Format email tidak valid.")
    return email


class RegisterRequest(BaseModel):
    email: str
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalize_and_validate_email(value)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Nama minimal 2 karakter.")
        return normalized


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalize_and_validate_email(value)


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    avatar_url: str | None
