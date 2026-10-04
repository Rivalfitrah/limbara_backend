from threading import Lock

from app.models.fasilitas import Fasilitas
from app.repositories.fasilitas_repository import FasilitasRepository
from app.utils.geo import haversine_km

DEFAULT_RADIUS_KM = 5.0
DEFAULT_LIMIT = 100


class FasilitasDataUnavailableError(RuntimeError):
    pass


class FasilitasService:
    def __init__(self, repository: FasilitasRepository | None = None) -> None:
        self._repository = repository or FasilitasRepository()
        self._facilities: list[Fasilitas] = []
        self._lock = Lock()
        self._is_loaded = False
        self._error_message: str | None = None

    @property
    def excel_path(self) -> str:
        return str(self._repository.excel_path)

    @property
    def total_facilities(self) -> int:
        self.load()
        return len(self._facilities)

    def load(self) -> int:
        with self._lock:
            if self._is_loaded:
                return len(self._facilities)
            try:
                self._facilities = self._repository.load()
                self._error_message = None
            except Exception as error:
                self._facilities = []
                self._error_message = str(error)
            self._is_loaded = True
            return len(self._facilities)

    def get_nearby(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = DEFAULT_RADIUS_KM,
        limit: int = DEFAULT_LIMIT,
    ) -> tuple[list[tuple[Fasilitas, float]], int]:
        self.load()
        if self._error_message is not None:
            raise FasilitasDataUnavailableError(self._error_message)

        matches = [
            (facility, distance)
            for facility in self._facilities
            if (distance := haversine_km(latitude, longitude, facility.latitude, facility.longitude)) <= radius_km
        ]
        matches.sort(key=lambda item: item[1])
        return matches[:limit], len(matches)


fasilitas_service = FasilitasService()