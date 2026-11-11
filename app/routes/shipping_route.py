from typing import Any

from fastapi import APIRouter, Query

from app.schemas.order import ShippingCostRequest
from app.services.shipping_service import (
    calculate_shipping_cost,
    get_cities,
    get_provinces,
)

router = APIRouter()


@router.get("/provinces")
async def list_provinces() -> list[dict[str, Any]]:
    return await get_provinces()


@router.get("/cities")
async def list_cities(province_id: str | None = Query(default=None)) -> list[dict[str, Any]]:
    return await get_cities(province_id)


@router.post("/cost")
async def calculate_cost(payload: ShippingCostRequest) -> list[dict[str, Any]]:
    return await calculate_shipping_cost(
        origin_city_id=payload.origin_city_id,
        destination_city_id=payload.destination_city_id,
        weight_grams=payload.weight_grams,
        courier=payload.courier,
    )
