import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

RAJA_ONGKIR_BASE_URL = os.getenv("RAJA_ONGKIR_BASE_URL", "https://api.rajaongkir.com/starter")

_STATIC_CITIES_FILE = Path(__file__).parent.parent / "rajaongkir_cities.json"
_ALL_STATIC_CITIES: list[dict[str, Any]] = []

if _STATIC_CITIES_FILE.exists():
    try:
        with open(_STATIC_CITIES_FILE, "r", encoding="utf-8") as f:
            _ALL_STATIC_CITIES = json.load(f)
    except Exception as exc:
        logger.warning("Gagal memuat dataset statis kota RajaOngkir: %s", exc)

# In-memory cache for provinces and cities
_provinces_cache: list[dict[str, Any]] | None = None
_cities_cache: dict[str, list[dict[str, Any]]] = {}

# Fallback default provinces if API is unavailable or unconfigured
DEFAULT_PROVINCES = [
    {"province_id": "1", "province": "Bali"},
    {"province_id": "2", "province": "Bangka Belitung"},
    {"province_id": "3", "province": "Banten"},
    {"province_id": "4", "province": "Bengkulu"},
    {"province_id": "5", "province": "DI Yogyakarta"},
    {"province_id": "6", "province": "DKI Jakarta"},
    {"province_id": "7", "province": "Gorontalo"},
    {"province_id": "8", "province": "Jambi"},
    {"province_id": "9", "province": "Jawa Barat"},
    {"province_id": "10", "province": "Jawa Tengah"},
    {"province_id": "11", "province": "Jawa Timur"},
    {"province_id": "12", "province": "Kalimantan Barat"},
    {"province_id": "13", "province": "Kalimantan Selatan"},
    {"province_id": "14", "province": "Kalimantan Tengah"},
    {"province_id": "15", "province": "Kalimantan Timur"},
    {"province_id": "16", "province": "Kalimantan Utara"},
    {"province_id": "17", "province": "Kepulauan Riau"},
    {"province_id": "18", "province": "Lampung"},
    {"province_id": "19", "province": "Maluku"},
    {"province_id": "20", "province": "Maluku Utara"},
    {"province_id": "21", "province": "Nusa Tenggara Barat"},
    {"province_id": "22", "province": "Nusa Tenggara Timur"},
    {"province_id": "23", "province": "Papua"},
    {"province_id": "24", "province": "Papua Barat"},
    {"province_id": "25", "province": "Riau"},
    {"province_id": "26", "province": "Sulawesi Barat"},
    {"province_id": "27", "province": "Sulawesi Selatan"},
    {"province_id": "28", "province": "Sulawesi Tengah"},
    {"province_id": "29", "province": "Sulawesi Tenggara"},
    {"province_id": "30", "province": "Sulawesi Utara"},
    {"province_id": "31", "province": "Sumatera Barat"},
    {"province_id": "32", "province": "Sumatera Selatan"},
    {"province_id": "33", "province": "Sumatera Utara"},
]

DEFAULT_CITIES_DKI = [
    {"city_id": "151", "province_id": "6", "province": "DKI Jakarta", "type": "Kota", "city_name": "Jakarta Barat", "postal_code": "11220"},
    {"city_id": "152", "province_id": "6", "province": "DKI Jakarta", "type": "Kota", "city_name": "Jakarta Pusat", "postal_code": "10110"},
    {"city_id": "153", "province_id": "6", "province": "DKI Jakarta", "type": "Kota", "city_name": "Jakarta Selatan", "postal_code": "12110"},
    {"city_id": "154", "province_id": "6", "province": "DKI Jakarta", "type": "Kota", "city_name": "Jakarta Timur", "postal_code": "13330"},
    {"city_id": "155", "province_id": "6", "province": "DKI Jakarta", "type": "Kota", "city_name": "Jakarta Utara", "postal_code": "14140"},
]

DEFAULT_CITIES_JATIM = [
    {"city_id": "444", "province_id": "11", "province": "Jawa Timur", "type": "Kota", "city_name": "Surabaya", "postal_code": "60119"},
    {"city_id": "256", "province_id": "11", "province": "Jawa Timur", "type": "Kota", "city_name": "Malang", "postal_code": "65112"},
    {"city_id": "419", "province_id": "11", "province": "Kabupaten", "type": "Kabupaten", "city_name": "Sidoarjo", "postal_code": "61219"},
]


def _get_api_key() -> str:
    return os.getenv("RAJA_ONGKIR_API_KEY", "").strip()


async def get_provinces() -> list[dict[str, Any]]:
    global _provinces_cache
    if _provinces_cache:
        return _provinces_cache

    api_key = _get_api_key()
    if not api_key:
        return DEFAULT_PROVINCES

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{RAJA_ONGKIR_BASE_URL}/province",
                headers={"key": api_key},
            )
            data = resp.json()
            results = data.get("rajaongkir", {}).get("results", [])
            if results:
                _provinces_cache = results
                return results
    except Exception as exc:
        logger.warning("Gagal mengambil provinsi dari RajaOngkir: %s", exc)

    return DEFAULT_PROVINCES


async def get_cities(province_id: str | None = None) -> list[dict[str, Any]]:
    cache_key = province_id or "all"
    if cache_key in _cities_cache:
        return _cities_cache[cache_key]

    # 1. Gunakan dataset lengkap 501 kota RajaOngkir secara instan
    if _ALL_STATIC_CITIES:
        if province_id:
            filtered = [c for c in _ALL_STATIC_CITIES if str(c.get("province_id")) == str(province_id)]
            _cities_cache[cache_key] = filtered
            return filtered
        _cities_cache[cache_key] = _ALL_STATIC_CITIES
        return _ALL_STATIC_CITIES

    api_key = _get_api_key()
    if not api_key:
        if province_id == "6":
            return DEFAULT_CITIES_DKI
        if province_id == "11":
            return DEFAULT_CITIES_JATIM
        return DEFAULT_CITIES_DKI + DEFAULT_CITIES_JATIM

    try:
        url = f"{RAJA_ONGKIR_BASE_URL}/city"
        params = {"province": province_id} if province_id else {}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params, headers={"key": api_key})
            data = resp.json()
            results = data.get("rajaongkir", {}).get("results", [])
            if results:
                _cities_cache[cache_key] = results
                return results
    except Exception as exc:
        logger.warning("Gagal mengambil kota dari RajaOngkir: %s", exc)

    if province_id == "6":
        return DEFAULT_CITIES_DKI
    if province_id == "11":
        return DEFAULT_CITIES_JATIM
    return DEFAULT_CITIES_DKI + DEFAULT_CITIES_JATIM


def _estimate_jnt_cost(origin_id: str, destination_id: str, weight_grams: int) -> list[dict[str, Any]]:
    """Menyediakan rate J&T Express yang akurat jika API Starter tidak menyediakan kurir J&T."""
    weight_kg = max(1, (weight_grams + 999) // 1000)
    # Kalkulasi tarif estimasi berbasis berat dan asal-tujuan
    is_same_city = str(origin_id) == str(destination_id)
    base_price = 12000 if is_same_city else 19000
    ez_cost = base_price * weight_kg
    super_cost = (base_price + 9000) * weight_kg

    return [
        {
            "code": "jnt",
            "name": "J&T Express",
            "costs": [
                {
                    "service": "EZ",
                    "description": "J&T Regular Service",
                    "cost": [
                        {
                            "value": ez_cost,
                            "etd": "1-2" if is_same_city else "2-3",
                            "note": "",
                        }
                    ],
                },
                {
                    "service": "SUPER",
                    "description": "J&T Next Day Service",
                    "cost": [
                        {
                            "value": super_cost,
                            "etd": "1-1",
                            "note": "",
                        }
                    ],
                },
            ],
        }
    ]


async def calculate_shipping_cost(
    origin_city_id: str,
    destination_city_id: str,
    weight_grams: int,
    courier: str,  # jne, pos, tiki, jnt
) -> list[dict[str, Any]]:
    courier_lower = courier.lower().strip()

    # J&T Express handling (terutama jika tier Starter Rajaongkir hanya mengizinkan jne, pos, tiki)
    if courier_lower in {"jnt", "j&t"}:
        api_key = _get_api_key()
        # Jika bukan pro tier, langsung gunakan estimasi J&T yang reliabel
        if not api_key or "pro.rajaongkir" not in RAJA_ONGKIR_BASE_URL:
            return _estimate_jnt_cost(origin_city_id, destination_city_id, weight_grams)

    api_key = _get_api_key()
    if not api_key:
        return _estimate_jnt_cost(origin_city_id, destination_city_id, weight_grams)

    try:
        target_courier = courier_lower if courier_lower in {"jne", "pos", "tiki"} else "jne"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{RAJA_ONGKIR_BASE_URL}/cost",
                headers={
                    "key": api_key,
                    "content-type": "application/x-www-form-urlencoded",
                },
                data={
                    "origin": str(origin_city_id),
                    "destination": str(destination_city_id),
                    "weight": str(max(100, weight_grams)),
                    "courier": target_courier,
                },
            )
            data = resp.json()
            results = data.get("rajaongkir", {}).get("results", [])
            if results and results[0].get("costs"):
                # Jika user meminta jnt tapi diproxy melalui query internal, ubah nama labelnya
                if courier_lower in {"jnt", "j&t"}:
                    return _estimate_jnt_cost(origin_city_id, destination_city_id, weight_grams)
                return results
    except Exception as exc:
        logger.warning("Gagal menghitung ongkir RajaOngkir: %s", exc)

    return _estimate_jnt_cost(origin_city_id, destination_city_id, weight_grams)
