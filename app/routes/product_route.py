import uuid
from fastapi import (
    APIRouter,
    Depends,
    File,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlmodel import Session

from app.database import get_session
from app.schemas.product import (
    DashboardSummary,
    MarketplaceProductPage,
    MarketplaceProductResponse,
    ProductCreate,
    ProductResponse,
    ProductToggleActive,
    ProductUpdate,
)
from app.services.auth_service import get_current_user, require_trusted_origin
from app.services.product_service import (
    create_product_for_shop,
    delete_product_for_shop,
    get_dashboard_summary,
    get_marketplace_product_by_slug,
    get_product_by_id_and_shop,
    get_user_shop_or_404,
    list_shop_products,
    list_marketplace_products,
    toggle_product_active_for_shop,
    update_product_for_shop,
    upload_product_image_to_cloudinary,
)
from app.services.marketplace_image_service import MAX_IMAGE_BYTES

router = APIRouter()


@router.post("/shops/me/products/upload")
async def upload_product_image(
    request: Request,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    require_trusted_origin(request)
    user = get_current_user(request, session)
    get_user_shop_or_404(session, user)

    file_bytes = await file.read(MAX_IMAGE_BYTES + 1)
    url = upload_product_image_to_cloudinary(file_bytes, file.content_type)
    return {"image_url": url}


@router.get("/products", response_model=MarketplaceProductPage)
def get_marketplace_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=48),
    search: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, max_length=50),
    session: Session = Depends(get_session),
):
    return list_marketplace_products(
        session,
        page=page,
        page_size=page_size,
        search=search,
        category=category,
    )


@router.get("/products/{slug}", response_model=MarketplaceProductResponse)
def get_marketplace_product(slug: str, session: Session = Depends(get_session)):
    return get_marketplace_product_by_slug(session, slug)


@router.get("/shops/me/dashboard", response_model=DashboardSummary)
def get_my_shop_dashboard(
    request: Request,
    session: Session = Depends(get_session),
):
    user = get_current_user(request, session)
    shop = get_user_shop_or_404(session, user)
    return get_dashboard_summary(session, shop)


@router.get("/shops/me/products", response_model=list[ProductResponse])
def get_my_products(
    request: Request,
    search: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    session: Session = Depends(get_session),
):
    user = get_current_user(request, session)
    shop = get_user_shop_or_404(session, user)
    return list_shop_products(session, shop.id, search=search, is_active=is_active)


@router.post(
    "/shops/me/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    payload: ProductCreate,
    request: Request,
    session: Session = Depends(get_session),
):
    require_trusted_origin(request)
    user = get_current_user(request, session)
    shop = get_user_shop_or_404(session, user)
    return create_product_for_shop(session, shop, payload)


@router.get("/shops/me/products/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_session),
):
    user = get_current_user(request, session)
    shop = get_user_shop_or_404(session, user)
    return get_product_by_id_and_shop(session, product_id, shop.id)


@router.put("/shops/me/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    request: Request,
    session: Session = Depends(get_session),
):
    require_trusted_origin(request)
    user = get_current_user(request, session)
    shop = get_user_shop_or_404(session, user)
    return update_product_for_shop(session, product_id, shop.id, payload)


@router.patch("/shops/me/products/{product_id}/toggle-active", response_model=ProductResponse)
def toggle_product_active(
    product_id: uuid.UUID,
    payload: ProductToggleActive,
    request: Request,
    session: Session = Depends(get_session),
):
    require_trusted_origin(request)
    user = get_current_user(request, session)
    shop = get_user_shop_or_404(session, user)
    return toggle_product_active_for_shop(session, product_id, shop.id, payload.is_active)


@router.delete("/shops/me/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_session),
) -> None:
    require_trusted_origin(request)
    user = get_current_user(request, session)
    shop = get_user_shop_or_404(session, user)
    delete_product_for_shop(session, product_id, shop.id)
