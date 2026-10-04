from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Fasilitas:
    id: str
    name: str
    address: str
    province: str
    regency: str
    village: str | None
    district: str | None
    latitude: float
    longitude: float
    managed_by: str
    scope: str
    waste_received: float | None
    waste_managed: float | None
    year: int