import re
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.shop import Shop
from app.models.user import User
from app.schemas.shop import ShopCreateRequest, ShopUpdateRequest


def slugify(text: str) -> str:
    cleaned = text.strip().lower()
    cleaned = re.sub(r"[^\w\s-]", "", cleaned)
    slug = re.sub(r"[\s_-]+", "-", cleaned).strip("-")
    return slug or "toko"


def generate_unique_slug(session: Session, name: str) -> str:
    base_slug = slugify(name)
    slug = base_slug
    counter = 1

    while session.exec(select(Shop).where(Shop.slug == slug)).first() is not None:
        counter += 1
        slug = f"{base_slug}-{counter}"

    return slug


def get_shop_by_user_id(session: Session, user_id: uuid.UUID) -> Shop | None:
    return session.exec(select(Shop).where(Shop.user_id == user_id)).first()


def get_shop_by_slug(session: Session, slug: str) -> Shop | None:
    return session.exec(select(Shop).where(Shop.slug == slug)).first()


def create_shop_for_user(session: Session, user: User, payload: ShopCreateRequest) -> Shop:
    existing_shop = get_shop_by_user_id(session, user.id)
    if existing_shop is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Akun Anda sudah memiliki toko yang terdaftar.",
        )

    slug = generate_unique_slug(session, payload.name)
    now = datetime.now(timezone.utc)

    shop = Shop(
        user_id=user.id,
        name=payload.name,
        slug=slug,
        description=payload.description,
        waste_focus=payload.waste_focus,
        province=payload.province,
        city=payload.city,
        district=payload.district,
        address=payload.address,
        postal_code=payload.postal_code,
        phone_number=payload.phone_number,
        email=payload.email or user.email,
        courier_options=payload.courier_options or [],
        logo_url=payload.logo_url,
        created_at=now,
        updated_at=now,
    )

    session.add(shop)
    session.commit()
    session.refresh(shop)
    return shop


def update_shop_for_user(
    session: Session,
    user: User,
    payload: ShopUpdateRequest,
) -> Shop:
    shop = get_shop_by_user_id(session, user.id)
    if shop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Toko tidak ditemukan.",
        )

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(shop, key, value)

    shop.updated_at = datetime.now(timezone.utc)
    session.add(shop)
    session.commit()
    session.refresh(shop)
    return shop
