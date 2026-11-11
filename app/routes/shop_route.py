from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlmodel import Session

from app.database import get_session
from app.schemas.shop import ShopCreateRequest, ShopResponse, ShopUpdateRequest
from app.services.auth_service import get_current_user, require_trusted_origin
from app.services.shop_service import (
    create_shop_for_user,
    get_shop_by_slug,
    get_shop_by_user_id,
    update_shop_for_user,
)
from app.services.marketplace_image_service import MAX_IMAGE_BYTES, upload_marketplace_image

router = APIRouter()


@router.get("/me", response_model=ShopResponse | None)
def get_my_shop(request: Request, session: Session = Depends(get_session)):
    user = get_current_user(request, session)
    return get_shop_by_user_id(session, user.id)


@router.post("", response_model=ShopResponse, status_code=status.HTTP_201_CREATED)
def create_shop(
    payload: ShopCreateRequest,
    request: Request,
    session: Session = Depends(get_session),
):
    require_trusted_origin(request)
    user = get_current_user(request, session)
    return create_shop_for_user(session, user, payload)


@router.post("/images")
async def upload_shop_image(
    request: Request,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    require_trusted_origin(request)
    get_current_user(request, session)
    file_bytes = await file.read(MAX_IMAGE_BYTES + 1)
    url = upload_marketplace_image(
        file_bytes,
        file.content_type,
        folder="limbara/shops",
    )
    return {"image_url": url}


@router.patch("/me", response_model=ShopResponse)
def update_my_shop(
    payload: ShopUpdateRequest,
    request: Request,
    session: Session = Depends(get_session),
):
    require_trusted_origin(request)
    user = get_current_user(request, session)
    return update_shop_for_user(session, user, payload)


@router.get("/{slug}", response_model=ShopResponse)
def get_shop_detail(slug: str, session: Session = Depends(get_session)):
    shop = get_shop_by_slug(session, slug)
    if shop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Toko tidak ditemukan.",
        )
    return shop
