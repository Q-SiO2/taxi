"""Authenticated, minimized place search and reverse-geocoding API."""

from hashlib import sha256
import re
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.auth.dependencies import CurrentPrincipal, authenticated_principal
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.places.schemas import (
    PlaceAttributionResponse,
    PlaceCoordinate,
    PlaceResultResponse,
    PlaceSearchResponse,
    ReversePlaceResponse,
)
from taximobile_api.domains.places.service import (
    PlaceCityUnavailable,
    active_place_city_context,
    pickup_serviceability,
)
from taximobile_api.integrations.geocoding import (
    GeoCoordinate,
    GeocodingProvider,
    GeocodingUnavailable,
    PlaceAttribution,
    PlaceCandidate,
)


router = APIRouter(tags=["places"])
_WHITESPACE = re.compile(r"\s+")


@router.get("/places/search", response_model=PlaceSearchResponse)
async def search_places(
    request: Request,
    city_id: UUID,
    query: str = Query(min_length=2, max_length=120),
    language: Literal["ar", "en", "fr"] = "en",
    limit: int = Query(default=8, ge=1, le=10),
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> PlaceSearchResponse:
    normalized_query = _normalized_query(query)
    await _rate_limit(
        request,
        principal,
        bucket="place-search",
        limit=request.app.state.settings.place_search_rate_limit_per_minute,
    )
    try:
        city = await active_place_city_context(session, city_id)
    except PlaceCityUnavailable as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    provider: GeocodingProvider = request.app.state.geocoding_provider
    try:
        result = await provider.search(
            normalized_query,
            language=language,
            limit=limit,
            viewbox=city.viewbox,
        )
    except GeocodingUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Place search is temporarily unavailable. Select a point on the map instead.",
        ) from error
    serviceable = await pickup_serviceability(
        session,
        city,
        [candidate.coordinate for candidate in result.candidates],
    )
    return PlaceSearchResponse(
        city_id=city.city_id,
        query=normalized_query,
        items=[
            _response(candidate, is_serviceable)
            for candidate, is_serviceable in zip(result.candidates, serviceable, strict=True)
        ],
        attribution=_attribution(result.attribution),
    )


@router.get("/places/reverse", response_model=ReversePlaceResponse)
async def reverse_place(
    request: Request,
    city_id: UUID,
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    language: Literal["ar", "en", "fr"] = "en",
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> ReversePlaceResponse:
    await _rate_limit(
        request,
        principal,
        bucket="place-reverse",
        limit=request.app.state.settings.place_reverse_rate_limit_per_minute,
    )
    try:
        city = await active_place_city_context(session, city_id)
    except PlaceCityUnavailable as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    coordinate = GeoCoordinate(latitude, longitude)
    serviceable = (await pickup_serviceability(session, city, [coordinate]))[0]
    provider: GeocodingProvider = request.app.state.geocoding_provider
    try:
        result = await provider.reverse(coordinate, language=language)
    except GeocodingUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Address lookup is temporarily unavailable. The selected coordinate is still usable.",
        ) from error
    return ReversePlaceResponse(
        city_id=city.city_id,
        item=(
            _response(result.candidate, serviceable, coordinate_override=coordinate)
            if result.candidate is not None
            else None
        ),
        attribution=_attribution(result.attribution),
    )


async def _rate_limit(
    request: Request,
    principal: CurrentPrincipal,
    *,
    bucket: str,
    limit: int,
) -> None:
    if not await request.app.state.rate_limiter.allow(
        f"{bucket}:{principal.user_id}",
        limit=limit,
        window_seconds=60,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many place requests. Wait before trying again.",
        )


def _normalized_query(query: str) -> str:
    value = _WHITESPACE.sub(" ", query).strip()
    if len(value) < 2 or any(ord(character) < 32 for character in value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Place query must contain at least two visible characters.",
        )
    return value


def _response(
    candidate: PlaceCandidate,
    serviceable: bool,
    *,
    coordinate_override: GeoCoordinate | None = None,
) -> PlaceResultResponse:
    coordinate = coordinate_override or candidate.coordinate
    opaque_id = sha256(
        (
            f"{candidate.provider_reference}|{coordinate.latitude:.7f}|"
            f"{coordinate.longitude:.7f}"
        ).encode("utf-8")
    ).hexdigest()[:24]
    return PlaceResultResponse(
        id=opaque_id,
        primary_text=candidate.primary_text,
        secondary_text=candidate.secondary_text,
        coordinate=PlaceCoordinate(
            latitude=coordinate.latitude,
            longitude=coordinate.longitude,
        ),
        kind=candidate.kind,
        pickup_serviceable=serviceable,
    )


def _attribution(value: PlaceAttribution) -> PlaceAttributionResponse:
    return PlaceAttributionResponse(text=value.text, url=value.url)
