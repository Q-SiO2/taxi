from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RouteCoordinate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class RouteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    origin: RouteCoordinate
    destination: RouteCoordinate
    language: Literal["ar", "en", "fr"] = "en"


class RouteManeuverResponse(BaseModel):
    instruction: str
    distance_meters: int
    duration_seconds: int
    begin_shape_index: int
    end_shape_index: int


class RouteResponse(BaseModel):
    distance_meters: int
    duration_seconds: int
    geometry: list[RouteCoordinate]
    maneuvers: list[RouteManeuverResponse]
