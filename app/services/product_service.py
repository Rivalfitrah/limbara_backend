import re
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import Session, col, func, select

from app.models.product import Product
from app.models.shop import Shop
from app.models.user import User
from app.schemas.product import (
    DashboardSummary,
    MarketplaceProductPage,
    MarketplaceProductResponse,
    MarketplaceShopSummary,
    ProductCreate,
    ProductUpdate,
)
from app.services.marketplace_image_service import upload_marketplace_image
from app.services.shop_service import get_shop_by_user_id


def slugify(text: str) -> str:
    cleaned = text.strip().lower()
    cleaned = re.sub(r"[^\w\s-]", "", cleaned)
    slug = re.sub(r"[\s_-]+", "-", cleaned).strip("-")
    return slug or "produk"


def generate_unique_product_slug(session: Session, name: str) -> str:
    base_slug = slugify(name)
    slug = base_slug
    counter = 1

    while session.exec(select(Product).where(Product.slug == slug)).first() is not None:
        counter += 1
        slug = f"{base_slug}-{counter}"

    return slug


def upload_product_image_to_cloudinary(
    file_bytes: bytes,
    content_type: str | None,
) -> str:
    return upload_marketplace_image(
        file_bytes,
        content_type,
        folder="limbara/products",
    )


def get_user_shop_or_404(session: Session, user: User) -> Shop:
    shop = get_shop_by_user_id(session, user.id)
    if shop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anda belum memiliki toko terdaftar. Silakan buat toko terlebih dahulu.",
        )
    return shop


def list_shop_products(
    session: Session,
    shop_id: uuid.UUID,
    search: str | None = None,
    is_active: bool | None = None,
) -> list[Product]:
    query = select(Product).where(Product.shop_id == shop_id)

    if search:
        search_term = f"%{search.strip().lower()}%"
        query = query.where(col(Product.name).ilike(search_term))

    if is_active is not None:
        query = query.where(Product.is_active == is_active)

    query = query.order_by(col(Product.created_at).desc())
    return session.exec(query).all()


def create_product_for_shop(
    session: Session,
    shop: Shop,
    payload: ProductCreate,
) -> Product:
    slug = generate_unique_product_slug(session, payload.name)
    now = datetime.now(timezone.utc)

    product = Product(
        shop_id=shop.id,
        name=payload.name,
        slug=slug,
        category=payload.category,
        waste_material=payload.waste_material,
        price=payload.price,
        previous_price=payload.previous_price,
        stock=payload.stock,
        image_url=payload.image_url,
        images=payload.images or [payload.image_url],
        short_description=payload.short_description,
        description=payload.description,
        weight_grams=payload.weight_grams,
        dimensions=payload.dimensions,
        production_time=payload.production_time,
        impact=payload.impact,
        is_active=payload.is_active,
        sold_count=0,
        created_at=now,
        updated_at=now,
    )

    session.add(product)
    session.commit()
    session.refresh(product)
    return product


def get_product_by_id_and_shop(
    session: Session,
    product_id: uuid.UUID,
    shop_id: uuid.UUID,
) -> Product:
    product = session.get(Product, product_id)
    if product is None or product.shop_id != shop_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produk tidak ditemukan di toko Anda.",
        )
    return product


def update_product_for_shop(
    session: Session,
    product_id: uuid.UUID,
    shop_id: uuid.UUID,
    payload: ProductUpdate,
) -> Product:
    product = get_product_by_id_and_shop(session, product_id, shop_id)

    update_data = payload.model_dump(exclude_unset=True)

    if "images" in update_data:
        update_data["image_url"] = update_data["images"][0]
    elif "image_url" in update_data:
        current_images = list(product.images or [product.image_url])
        update_data["images"] = [update_data["image_url"], *current_images[1:]]

    if "name" in update_data and update_data["name"] and update_data["name"] != product.name:
        product.slug = generate_unique_product_slug(session, update_data["name"])

    for key, value in update_data.items():
        setattr(product, key, value)

    product.updated_at = datetime.now(timezone.utc)
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


def toggle_product_active_for_shop(
    session: Session,
    product_id: uuid.UUID,
    shop_id: uuid.UUID,
    is_active: bool,
) -> Product:
    product = get_product_by_id_and_shop(session, product_id, shop_id)
    product.is_active = is_active
    product.updated_at = datetime.now(timezone.utc)
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


def delete_product_for_shop(
    session: Session,
    product_id: uuid.UUID,
    shop_id: uuid.UUID,
) -> None:
    product = get_product_by_id_and_shop(session, product_id, shop_id)
    session.delete(product)
    session.commit()


def get_dashboard_summary(session: Session, shop: Shop) -> DashboardSummary:
    total_products = session.exec(
        select(func.count()).select_from(Product).where(Product.shop_id == shop.id)
    ).one()

    active_products = session.exec(
        select(func.count()).select_from(Product).where(
            Product.shop_id == shop.id,
            Product.is_active == True,
        )
    ).one()

    inactive_products = total_products - active_products

    total_stock_res = session.exec(
        select(func.sum(Product.stock)).where(Product.shop_id == shop.id)
    ).one()
    total_stock = total_stock_res or 0

    total_sold_res = session.exec(
        select(func.sum(Product.sold_count)).where(Product.shop_id == shop.id)
    ).one()
    total_sold = total_sold_res or 0

    return DashboardSummary(
        total_products=total_products,
        active_products=active_products,
        inactive_products=inactive_products,
        total_stock=total_stock,
        total_sold=total_sold,
        shop_name=shop.name,
        shop_slug=shop.slug,
        waste_focus=shop.waste_focus,
        city=shop.city,
    )


def _marketplace_product_response(
    session: Session,
    product: Product,
    shop: Shop,
) -> MarketplaceProductResponse:
    total_products = session.exec(
        select(func.count()).select_from(Product).where(
            Product.shop_id == shop.id,
            Product.is_active == True,
        )
    ).one()
    shop_summary = MarketplaceShopSummary(
        id=shop.id,
        slug=shop.slug,
        name=shop.name,
        city=shop.city,
        province=shop.province,
        logo_url=shop.logo_url,
        is_verified=shop.is_verified,
        total_products=total_products,
        created_at=shop.created_at,
    )
    return MarketplaceProductResponse(
        **Product.model_validate(product).model_dump(),
        shop=shop_summary,
    )


def list_marketplace_products(
    session: Session,
    page: int,
    page_size: int,
    search: str | None = None,
    category: str | None = None,
) -> MarketplaceProductPage:
    filters = [Product.is_active == True]
    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(col(Product.name).ilike(term))
    if category and category.strip():
        filters.append(Product.category == category.strip())

    total = session.exec(
        select(func.count()).select_from(Product).where(*filters)
    ).one()
    rows = session.exec(
        select(Product, Shop)
        .join(Shop, Product.shop_id == Shop.id)
        .where(*filters)
        .order_by(col(Product.created_at).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    items = [
        _marketplace_product_response(session, product, shop)
        for product, shop in rows
    ]
    total_pages = (total + page_size - 1) // page_size if total else 0
    return MarketplaceProductPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def get_marketplace_product_by_slug(
    session: Session,
    slug: str,
) -> MarketplaceProductResponse:
    row = session.exec(
        select(Product, Shop)
        .join(Shop, Product.shop_id == Shop.id)
        .where(Product.slug == slug, Product.is_active == True)
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produk tidak ditemukan.",
        )
    product, shop = row
    return _marketplace_product_response(session, product, shop)
