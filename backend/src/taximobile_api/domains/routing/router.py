from fastapi import APIRouter, Depends, HTTPException, Request, status

from taximobile_api.domains.auth.dependencies import CurrentPrincipal, authenticated_principal
from taximobile_api.domains.routing.schemas import (
    RouteCoordinate,
    RouteManeuverResponse,
    RouteRequest,
    RouteResponse,
)
from taximobile_api.integrations.routing.models import RouteCoordinate as ProviderCoordinate
from taximobile_api.integrations.routing.provider import RoutingProvider, RoutingUnavailable


router = APIRouter(tags=["routing"])


@router.post("/routing/route", response_model=RouteResponse)
async def calculate_route(
    payload: RouteRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(authenticated_principal),
) -> RouteResponse:
    if not await request.app.state.rate_limiter.allow(
        f"routing:{principal.user_id}",
        limit=request.app.state.settings.routing_rate_limit_per_minute,
        window_seconds=60,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many routing requests. Try again shortly.",
        )
    provider: RoutingProvider = request.app.state.routing_provider
    try:
        route = await provider.route(
            ProviderCoordinate(payload.origin.latitude, payload.origin.longitude),
            ProviderCoordinate(payload.destination.latitude, payload.destination.longitude),
            payload.language,
        )
    except RoutingUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Routing is temporarily unavailable.",
        ) from error
    return RouteResponse(
        distance_meters=route.distance_meters,
        duration_seconds=route.duration_seconds,
        geometry=[RouteCoordinate(latitude=item.latitude, longitude=item.longitude) for item in route.geometry],
        maneuvers=[
            RouteManeuverResponse(
                instruction=item.instruction,
                distance_meters=item.distance_meters,
                duration_seconds=item.duration_seconds,
                begin_shape_index=item.begin_shape_index,
                end_shape_index=item.end_shape_index,
            )
            for item in route.maneuvers
        ],
    )
