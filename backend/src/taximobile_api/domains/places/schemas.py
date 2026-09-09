from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PlaceCoordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class PlaceAttributionResponse(BaseModel):
    text: str
    url: str


class PlaceResultResponse(BaseModel):
    id: str
    primary_text: str
    secondary_text: str | None
    coordinate: PlaceCoordinate
    kind: Literal["ADDRESS", "STREET", "LOCALITY", "POI", "OTHER"]
    pickup_serviceable: bool


class PlaceSearchResponse(BaseModel):
    city_id: UUID
    query: str
    items: list[PlaceResultResponse]
    attribution: PlaceAttributionResponse


class ReversePlaceResponse(BaseModel):
    city_id: UUID
    item: PlaceResultResponse | None
    attribution: PlaceAttributionResponse
