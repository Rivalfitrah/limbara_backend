from typing import Any

from pydantic import BaseModel, HttpUrl


class ScanHistoryCreate(BaseModel):
    image_url: HttpUrl
    detected_objects: list[str]
    danger_level: str | None = None
    is_recyclable: bool | None = None
    insight_summary: str | None = None
    full_insight_data: dict[str, Any] | None = None
