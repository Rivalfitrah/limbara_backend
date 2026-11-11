import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session, select

from app.database import get_session
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.review import ProductReview
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewEligibilityResponse, ReviewResponse
from app.services.auth_service import get_current_user

router = APIRouter()


@router.get("/products/{product_id}/reviews", response_model=list[ReviewResponse])
def get_product_reviews(
    product_id: uuid.UUID,
    session: Session = Depends(get_session),
):
    reviews = session.exec(
        select(ProductReview)
        .where(ProductReview.product_id == product_id)
        .order_by(ProductReview.created_at.desc())
    ).all()
    return reviews


@router.get("/products/{product_id}/review-eligibility", response_model=ReviewEligibilityResponse)
def check_review_eligibility(
    product_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_session),
):
    try:
        user: User = get_current_user(request, session)
    except HTTPException:
        return ReviewEligibilityResponse(
            can_review=False,
            message="Silakan login terlebih dahulu untuk memberikan ulasan.",
        )

    # Cari pesanan berstatus SELESAI milik pembeli yang memuat produk ini
    completed_orders = session.exec(
        select(Order).where(Order.buyer_id == user.id, Order.status == "SELESAI")
    ).all()

    for order in completed_orders:
        has_item = session.exec(
            select(OrderItem).where(
                OrderItem.order_id == order.id,
                OrderItem.product_id == product_id,
            )
        ).first()

        if has_item:
            # Periksa apakah sudah pernah diulas
            existing_review = session.exec(
                select(ProductReview).where(
                    ProductReview.order_id == order.id,
                    ProductReview.product_id == product_id,
                )
            ).first()

            if not existing_review:
                return ReviewEligibilityResponse(
                    can_review=True,
                    order_id=order.id,
                    message="Anda dapat memberikan ulasan untuk produk ini.",
                )

    return ReviewEligibilityResponse(
        can_review=False,
        message="Ulasan hanya dapat diberikan setelah Anda membeli produk ini dan menyelesaikan pesanan.",
    )


@router.post("/products/{product_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_product_review(
    product_id: uuid.UUID,
    payload: ReviewCreate,
    request: Request,
    session: Session = Depends(get_session),
):
    user: User = get_current_user(request, session)

    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produk tidak ditemukan.")

    # 1. Validasi pesanan
    order = session.get(Order, payload.order_id)
    if not order or order.buyer_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pesanan tidak valid.")

    if order.status != "SELESAI":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ulasan hanya dapat diberikan setelah pesanan berstatus 'SELESAI'.",
        )

    # 2. Validasi barang ada di pesanan tersebut
    item = session.exec(
        select(OrderItem).where(
            OrderItem.order_id == order.id,
            OrderItem.product_id == product_id,
        )
    ).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Produk ini tidak terdapat dalam pesanan yang Anda pilih.",
        )

    # 3. Validasi belum pernah diulas
    existing = session.exec(
        select(ProductReview).where(
            ProductReview.order_id == order.id,
            ProductReview.product_id == product_id,
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Anda telah memberikan ulasan untuk produk ini pada pesanan tersebut.",
        )

    review = ProductReview(
        order_id=order.id,
        product_id=product.id,
        user_id=user.id,
        user_name=user.name or "Pengguna Limbara",
        user_avatar=user.avatar_url,
        rating=payload.rating,
        comment=payload.comment.strip(),
        created_at=datetime.now(timezone.utc),
    )
    session.add(review)
    session.commit()
    session.refresh(review)

    return review
