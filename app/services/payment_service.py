import base64
import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.order import Order, OrderItem

logger = logging.getLogger(__name__)


def _is_production() -> bool:
    return os.getenv("MIDTRANS_IS_PRODUCTION", "false").lower() == "true"


def get_snap_url() -> str:
    if _is_production():
        return "https://app.midtrans.com/snap/v1/transactions"
    return "https://app.sandbox.midtrans.com/snap/v1/transactions"


def get_midtrans_server_key() -> str:
    key = os.getenv("MIDTRANS_SERVER_KEY", "").strip()
    return key


def get_midtrans_signature_key() -> str:
    # Mengutamakan MIDTRANS_SIGNATURE_KEY jika ada, jika tidak fallback ke server key
    key = os.getenv("MIDTRANS_SIGNATURE_KEY", "").strip()
    return key or get_midtrans_server_key()


async def create_snap_transaction(
    order: Order,
    items: list[OrderItem],
    buyer_email: str,
) -> dict[str, str]:
    server_key = get_midtrans_server_key()
    if not server_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pembayaran Midtrans belum dikonfigurasi (MIDTRANS_SERVER_KEY belum diatur).",
        )

    # Encode Server Key ke Base64 untuk HTTP Basic Auth
    auth_header = base64.b64encode(f"{server_key}:".encode("utf-8")).decode("utf-8")

    # Item details
    item_details = []
    for it in items:
        item_details.append(
            {
                "id": str(it.product_id)[:50],
                "price": int(it.price),
                "quantity": int(it.quantity),
                "name": it.product_name[:50],
            }
        )

    if order.shipping_cost > 0:
        item_details.append(
            {
                "id": "SHIPPING-FEE",
                "price": int(order.shipping_cost),
                "quantity": 1,
                "name": f"Ongkir {order.courier.upper()} {order.courier_service}"[:50],
            }
        )

    payload = {
        "transaction_details": {
            "order_id": order.order_number,
            "gross_amount": int(order.total_amount),
        },
        "item_details": item_details,
        "customer_details": {
            "first_name": order.recipient_name,
            "email": buyer_email,
            "phone": order.recipient_phone,
            "shipping_address": {
                "first_name": order.recipient_name,
                "phone": order.recipient_phone,
                "address": order.shipping_address,
                "city": order.shipping_city,
                "postal_code": order.shipping_postal_code or "",
            },
        },
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                get_snap_url(),
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Basic {auth_header}",
                },
            )
            if resp.is_error:
                logger.error("Midtrans Snap error %s: %s", resp.status_code, resp.text)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Midtrans menolak transaksi: {resp.text}",
                )

            data = resp.json()
            return {
                "token": data.get("token", ""),
                "redirect_url": data.get("redirect_url", ""),
            }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Gagal memanggil Midtrans Snap: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gagal menghubungi server pembayaran Midtrans. Silakan coba sesaat lagi.",
        ) from exc


def verify_midtrans_signature(notification_data: dict[str, Any]) -> bool:
    order_id = notification_data.get("order_id", "")
    status_code = notification_data.get("status_code", "")
    gross_amount = notification_data.get("gross_amount", "")
    received_signature = notification_data.get("signature_key", "")

    # Cek signature dengan server_key maupun signature_key
    keys_to_test = [get_midtrans_signature_key(), get_midtrans_server_key()]
    for key in keys_to_test:
        if not key:
            continue
        raw_str = f"{order_id}{status_code}{gross_amount}{key}"
        calculated_signature = hashlib.sha512(raw_str.encode("utf-8")).hexdigest()
        if calculated_signature.lower() == received_signature.lower():
            return True

    return False


def process_midtrans_notification(session: Session, payload: dict[str, Any]) -> Order:
    if not verify_midtrans_signature(payload):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signature Midtrans tidak valid.",
        )

    order_number = payload.get("order_id")
    order = session.exec(select(Order).where(Order.order_number == order_number)).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pesanan tidak ditemukan.")

    transaction_status = payload.get("transaction_status", "")
    fraud_status = payload.get("fraud_status", "")
    payment_type = payload.get("payment_type")
    transaction_id = payload.get("transaction_id")

    order.payment_type = payment_type or order.payment_type
    order.midtrans_transaction_id = transaction_id or order.midtrans_transaction_id

    now = datetime.now(timezone.utc)
    if transaction_status in {"capture", "settlement"}:
        if fraud_status == "challenge":
            order.status = "CHALLENGE"
        else:
            order.status = "DIPROSES"
            order.paid_at = now
    elif transaction_status in {"deny", "cancel"}:
        order.status = "CANCELLED"
    elif transaction_status in {"expire"}:
        order.status = "EXPIRED"
    elif transaction_status in {"pending"}:
        order.status = "PENDING"

    order.updated_at = now
    session.add(order)
    session.commit()
    session.refresh(order)
    return order
