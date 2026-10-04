from pydantic import BaseModel, Field

from app.models.fasilitas import Fasilitas

GOOGLE_MAPS_SEARCH_URL = "https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"
DISTANCE_PRECISION = 2
WASTE_PRECISION = 2


class FasilitasResponse(BaseModel):
    id: str
    name: str
    address: str
    province: str
    regency: str
    managed_by: str
    scope: str
    latitude: float
    longitude: float
    waste_received: float | None
    waste_managed: float | None
    year: int
    distance_km: float
    google_maps_url: str

    @classmethod
    def from_fasilitas(cls, facility: Fasilitas, distance_km: float) -> "FasilitasResponse":
        return cls(
            id=facility.id,
            name=facility.name,
            address=facility.address,
            province=facility.province,
            regency=facility.regency,
            managed_by=facility.managed_by,
            scope=facility.scope,
            latitude=facility.latitude,
            longitude=facility.longitude,
            waste_received=cls._round(facility.waste_received),
            waste_managed=cls._round(facility.waste_managed),
            year=facility.year,
            distance_km=round(distance_km, DISTANCE_PRECISION),
            google_maps_url=GOOGLE_MAPS_SEARCH_URL.format(
                latitude=facility.latitude,
                longitude=facility.longitude,
            ),
        )

    @staticmethod
    def _round(value: float | None) -> float | None:
        return round(value, WASTE_PRECISION) if value is not None else None


class FasilitasNearbyResponse(BaseModel):
    data: list[FasilitasResponse] = Field(default_factory=list)
    total: int
    count: int
    radius_km: float