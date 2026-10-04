from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.schemas.fasilitas import FasilitasNearbyResponse, FasilitasResponse
from app.services.fasilitas_service import DEFAULT_LIMIT, DEFAULT_RADIUS_KM, FasilitasDataUnavailableError, fasilitas_service

router = APIRouter()
MAX_RADIUS_KM = 100.0
MAX_LIMIT = 300


@router.get("/nearby", response_model=FasilitasNearbyResponse)
def get_nearby_fasilitas(
    lat: Annotated[float, Query(ge=-90, le=90, description="Latitude lokasi pengguna")],
    lng: Annotated[float, Query(ge=-180, le=180, description="Longitude lokasi pengguna")],
    radius_km: Annotated[float, Query(gt=0, le=MAX_RADIUS_KM)] = DEFAULT_RADIUS_KM,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
) -> FasilitasNearbyResponse:
    try:
        matches, total = fasilitas_service.get_nearby(lat, lng, radius_km, limit)
    except FasilitasDataUnavailableError as error:
        raise HTTPException(status_code=503, detail=f"Data fasilitas belum tersedia: {error}")

    data = [FasilitasResponse.from_fasilitas(facility, distance) for facility, distance in matches]
    return FasilitasNearbyResponse(
        data=data,
        total=total,
        count=len(data),
        radius_km=radius_km,
    )