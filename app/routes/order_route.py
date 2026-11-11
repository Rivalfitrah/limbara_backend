import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlmodel import Session, select

from app.database import get_session
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User
from app.schemas.order import CheckoutRequest, OrderItemResponse, OrderResponse, ShipOrderRequest
from app.services.auth_service import get_current_user
from app.services.payment_service import create_snap_transaction, process_midtrans_notification
from app.services.product_service import get_user_shop_or_404

router = APIRouter()


def _format_order_response(order: Order, items: list[OrderItem]) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        total_product_amount=order.total_product_amount,
        shipping_cost=order.shipping_cost,
        total_amount=order.total_amount,
        courier=order.courier,
        courier_service=order.courier_service,
        recipient_name=order.recipient_name,
        recipient_phone=order.recipient_phone,
        shipping_address=order.shipping_address,
        shipping_city=order.shipping_city,
        shipping_province=order.shipping_province,
        shipping_postal_code=order.shipping_postal_code,
        notes=order.notes,
        snap_token=order.snap_token,
        snap_redirect_url=order.snap_redirect_url,
        payment_type=order.payment_type,
        tracking_number=order.tracking_number,
        paid_at=order.paid_at,
        shipped_at=order.shipped_at,
        completed_at=order.completed_at,
        created_at=order.created_at,
        items=[
            OrderItemResponse(
                id=it.id,
                product_id=it.product_id,
                product_name=it.product_name,
                product_image=it.product_image,
                price=it.price,
                quantity=it.quantity,
                subtotal=it.subtotal,
            )
            for it in items
        ],
    )


@router.post("/checkout", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_checkout_order(
    payload: CheckoutRequest,
    request: Request,
    session: Session = Depends(get_session),
):
    user: User = get_current_user(request, session)

    if not payload.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Keranjang belanja kosong.")

    order_items: list[OrderItem] = []
    total_product_amount = 0
    shop_id: uuid.UUID | None = None

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y%m%d%H%M")
    random_suffix = secrets.token_hex(2).upper()
    order_number = f"LMB-{date_str}-{random_suffix}"

    order_id = uuid.uuid4()

    for item_data in payload.items:
        product = session.get(Product, item_data.product_id)
        if not product or not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Produk tidak ditemukan atau sudah tidak aktif.",
            )
        if product.stock < item_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stok produk {product.name} tidak mencukupi (sisa {product.stock}).",
            )

        if shop_id is None:
            shop_id = product.shop_id

        item_subtotal = product.price * item_data.quantity
        total_product_amount += item_subtotal

        order_item = OrderItem(
            id=uuid.uuid4(),
            order_id=order_id,
            product_id=product.id,
            product_name=product.name,
            product_image=product.image_url,
            price=product.price,
            quantity=item_data.quantity,
            subtotal=item_subtotal,
            created_at=now,
        )
        order_items.append(order_item)

    if shop_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Toko produk tidak valid.")

    total_amount = total_product_amount + payload.shipping_cost

    order = Order(
        id=order_id,
        order_number=order_number,
        buyer_id=user.id,
        shop_id=shop_id,
        status="PENDING",
        total_product_amount=total_product_amount,
        shipping_cost=payload.shipping_cost,
        total_amount=total_amount,
        courier=payload.courier,
        courier_service=payload.courier_service,
        recipient_name=payload.recipient_name,
        recipient_phone=payload.recipient_phone,
        shipping_address=payload.shipping_address,
        shipping_province=payload.shipping_province,
        shipping_city=payload.shipping_city,
        shipping_postal_code=payload.shipping_postal_code,
        notes=payload.notes,
        created_at=now,
        updated_at=now,
    )

    # Dapatkan Snap Token dari Midtrans
    snap_data = await create_snap_transaction(order, order_items, user.email)
    order.snap_token = snap_data.get("token")
    order.snap_redirect_url = snap_data.get("redirect_url")

    # Kurangi stok produk
    for item_data in payload.items:
        prod = session.get(Product, item_data.product_id)
        if prod:
            prod.stock -= item_data.quantity
            prod.sold_count += item_data.quantity
            session.add(prod)

    session.add(order)
    for it in order_items:
        session.add(it)

    session.commit()
    session.refresh(order)

    return _format_order_response(order, order_items)


@router.get("/me", response_model=list[OrderResponse])
def get_my_orders(
    request: Request,
    session: Session = Depends(get_session),
):
    user: User = get_current_user(request, session)
    orders = session.exec(
        select(Order).where(Order.buyer_id == user.id).order_by(Order.created_at.desc())
    ).all()

    result = []
    for ord in orders:
        items = session.exec(select(OrderItem).where(OrderItem.order_id == ord.id)).all()
        result.append(_format_order_response(ord, items))
    return result


@router.get("/shop/me", response_model=list[OrderResponse])
def get_shop_orders_for_seller(
    request: Request,
    status_filter: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    user: User = get_current_user(request, session)
    shop = get_user_shop_or_404(session, user)

    stmt = select(Order).where(Order.shop_id == shop.id)
    if status_filter and status_filter.upper() != "ALL":
        stmt = stmt.where(Order.status == status_filter.upper())

    orders = session.exec(stmt.order_by(Order.created_at.desc())).all()
    result = []
    for ord in orders:
        items = session.exec(select(OrderItem).where(OrderItem.order_id == ord.id)).all()
        result.append(_format_order_response(ord, items))
    return result


@router.post("/shop/me/{order_id}/ship", response_model=OrderResponse)
def ship_order_by_seller(
    order_id: uuid.UUID,
    payload: ShipOrderRequest,
    request: Request,
    session: Session = Depends(get_session),
):
    user: User = get_current_user(request, session)
    shop = get_user_shop_or_404(session, user)

    order = session.get(Order, order_id)
    if not order or order.shop_id != shop.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pesanan tidak ditemukan di toko Anda.")

    if order.status not in {"DIPROSES", "PAID"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hanya pesanan berstatus 'DIPROSES' yang dapat dikirim.",
        )

    tracking_num = payload.tracking_number.strip()
    if not tracking_num:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nomor resi wajib diisi.")

    now = datetime.now(timezone.utc)
    order.tracking_number = tracking_num
    order.status = "DIKIRIM"
    order.shipped_at = now
    order.updated_at = now

    session.add(order)
    session.commit()
    session.refresh(order)

    items = session.exec(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    return _format_order_response(order, items)


@router.post("/{order_id}/mark-paid", response_model=OrderResponse)
def mark_order_paid(
    order_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_session),
):
    user: User = get_current_user(request, session)
    order = session.get(Order, order_id)
    if not order or (order.buyer_id != user.id and not user.is_superuser):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pesanan tidak ditemukan.")

    if order.status == "PENDING":
        now = datetime.now(timezone.utc)
        order.status = "DIPROSES"
        order.paid_at = now
        order.updated_at = now
        session.add(order)
        session.commit()
        session.refresh(order)

    items = session.exec(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    return _format_order_response(order, items)


@router.post("/{order_id}/complete", response_model=OrderResponse)
def complete_order_by_buyer(
    order_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_session),
):
    user: User = get_current_user(request, session)
    order = session.get(Order, order_id)
    if not order or order.buyer_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pesanan tidak ditemukan.")

    if order.status != "DIKIRIM":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hanya pesanan yang sedang dalam status 'DIKIRIM' yang dapat diselesaikan.",
        )

    now = datetime.now(timezone.utc)
    order.status = "SELESAI"
    order.completed_at = now
    order.updated_at = now
    session.add(order)
    session.commit()
    session.refresh(order)

    items = session.exec(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    return _format_order_response(order, items)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order_detail(
    order_id: uuid.UUID,
    request: Request,
    session: Session = Depends(get_session),
):
    user: User = get_current_user(request, session)
    order = session.get(Order, order_id)
    if not order or (order.buyer_id != user.id and not user.is_superuser):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pesanan tidak ditemukan.")

    items = session.exec(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    return _format_order_response(order, items)


@router.post("/payments/notification")
def midtrans_webhook(
    payload: dict[str, Any],
    session: Session = Depends(get_session),
):
    """Webhook listener untuk update status otomatis dari server Midtrans."""
    order = process_midtrans_notification(session, payload)
    return {"status": "ok", "order_id": order.order_number, "order_status": order.status}
