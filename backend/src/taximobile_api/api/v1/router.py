"""The stable v1 router; domain routers are added here as their contracts exist."""

from typing import Annotated

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from taximobile_api.core.client_compatibility import (
    CLIENT_BUILD_HEADER,
    CLIENT_SURFACE_HEADER,
    CLIENT_VERSION_HEADER,
    ClientCompatibilityPolicy,
    ClientCompatibilityStatus,
    ClientIdentityError,
    ClientSurface,
    parse_client_identity,
)
from taximobile_api.core.errors import error_response

from taximobile_api.domains.auth.router import router as auth_router
from taximobile_api.domains.administration.router import router as administration_router
from taximobile_api.domains.drivers.router import router as drivers_router
from taximobile_api.domains.rides.router import router as rides_router
from taximobile_api.domains.ride_communications.router import (
    router as ride_communications_router,
)
from taximobile_api.domains.rides.offers_router import router as offers_router
from taximobile_api.domains.payments.router import router as payments_router
from taximobile_api.domains.payments.admin_router import router as payment_administration_router
from taximobile_api.domains.payments.operations_configuration_router import (
    router as payment_configuration_operations_router,
)
from taximobile_api.domains.payments.operations_reconciliation_router import (
    router as payment_reconciliation_operations_router,
)
from taximobile_api.domains.support.router import router as support_router
from taximobile_api.domains.support.admin_router import router as support_administration_router
from taximobile_api.domains.support.operations_router import router as support_operations_router
from taximobile_api.domains.safety.router import router as safety_router
from taximobile_api.domains.safety.admin_router import router as safety_administration_router
from taximobile_api.domains.safety.operations_router import router as safety_operations_router
from taximobile_api.domains.notifications.router import router as notifications_router
from taximobile_api.domains.routing.router import router as routing_router
from taximobile_api.domains.places.router import router as places_router
from taximobile_api.domains.cooperatives.router import router as cooperatives_router
from taximobile_api.domains.administration.operations_auth_router import (
    router as operations_auth_router,
)
from taximobile_api.domains.administration.operations_router import (
    router as operations_administration_router,
)
from taximobile_api.domains.markets.operations_router import router as markets_operations_router
from taximobile_api.domains.markets.configuration_router import (
    router as markets_configuration_router,
)
from taximobile_api.domains.driver_applications.router import (
    router as driver_applications_router,
)
from taximobile_api.domains.driver_applications.operations_router import (
    router as driver_applications_operations_router,
)
from taximobile_api.domains.driver_applications.authorization_router import (
    router as driver_authorizations_operations_router,
)
from taximobile_api.domains.pricing.operations_router import (
    router as pricing_operations_router,
)
from taximobile_api.domains.fixed_routes.router import router as fixed_routes_router
from taximobile_api.domains.fixed_routes.operations_router import (
    router as fixed_routes_operations_router,
)
from taximobile_api.domains.scheduled_bookings.router import (
    router as scheduled_bookings_router,
)
from taximobile_api.domains.scheduled_bookings.operations_router import (
    router as scheduled_bookings_operations_router,
)
from taximobile_api.domains.analytics.router import router as analytics_operations_router
from taximobile_api.domains.case_alerts.router import router as case_alerts_router
from taximobile_api.domains.case_retention.router import router as case_retention_router
from taximobile_api.domains.security_incidents.router import (
    router as security_incidents_router,
)


class ApiMetadata(BaseModel):
    service: str
    version: str


async def metadata() -> ApiMetadata:
    return ApiMetadata(service="taximobile-api", version="v1")


class ClientCompatibilityResponse(BaseModel):
    status: ClientCompatibilityStatus
    surface: ClientSurface
    minimum_version: str
    recommended_version: str
    policy_revision: str
    api_version: str


async def client_compatibility(
    request: Request,
    surface: Annotated[str, Header(alias=CLIENT_SURFACE_HEADER)],
    version: Annotated[str, Header(alias=CLIENT_VERSION_HEADER)],
    build: Annotated[str, Header(alias=CLIENT_BUILD_HEADER)],
) -> ClientCompatibilityResponse | JSONResponse:
    """Assess a closed build identity without authenticating or accepting a command."""
    try:
        identity = parse_client_identity(
            {
                CLIENT_SURFACE_HEADER.lower(): surface,
                CLIENT_VERSION_HEADER.lower(): version,
                CLIENT_BUILD_HEADER.lower(): build,
            }
        )
    except ClientIdentityError:
        return error_response(
            status_code=400,
            code="CLIENT_IDENTITY_INVALID",
            message="The TaxiMobile client identity is invalid.",
        )
    policy: ClientCompatibilityPolicy = request.app.state.client_compatibility_policy
    result = policy.assess(identity)
    return ClientCompatibilityResponse(
        status=result.status,
        surface=result.surface,
        minimum_version=result.minimum_version,
        recommended_version=result.recommended_version,
        policy_revision=result.policy_revision,
        api_version=result.api_version,
    )


def create_v1_router(*, legacy_admin_api_enabled: bool) -> APIRouter:
    """Build the v1 surface, mounting transitional global authority only locally."""
    router = APIRouter()
    router.include_router(auth_router)
    if legacy_admin_api_enabled:
        router.include_router(administration_router)
    router.include_router(drivers_router)
    router.include_router(driver_applications_router)
    router.include_router(rides_router)
    router.include_router(ride_communications_router)
    router.include_router(offers_router)
    router.include_router(payments_router)
    if legacy_admin_api_enabled:
        router.include_router(payment_administration_router)
    router.include_router(payment_configuration_operations_router)
    router.include_router(payment_reconciliation_operations_router)
    router.include_router(support_router)
    if legacy_admin_api_enabled:
        router.include_router(support_administration_router)
    router.include_router(support_operations_router)
    router.include_router(safety_router)
    if legacy_admin_api_enabled:
        router.include_router(safety_administration_router)
    router.include_router(safety_operations_router)
    router.include_router(notifications_router)
    router.include_router(routing_router)
    router.include_router(places_router)
    router.include_router(cooperatives_router)
    router.include_router(operations_auth_router)
    router.include_router(markets_operations_router)
    router.include_router(markets_configuration_router)
    router.include_router(operations_administration_router)
    router.include_router(driver_applications_operations_router)
    router.include_router(driver_authorizations_operations_router)
    router.include_router(pricing_operations_router)
    router.include_router(fixed_routes_router)
    router.include_router(fixed_routes_operations_router)
    router.include_router(scheduled_bookings_router)
    router.include_router(scheduled_bookings_operations_router)
    router.include_router(analytics_operations_router)
    router.include_router(case_alerts_router)
    router.include_router(case_retention_router)
    router.include_router(security_incidents_router)
    router.add_api_route(
        "/client-compatibility",
        client_compatibility,
        methods=["GET"],
        response_model=ClientCompatibilityResponse,
        responses={400: {"description": "Malformed client build identity"}},
        tags=["system"],
    )
    router.add_api_route(
        "/meta",
        metadata,
        methods=["GET"],
        response_model=ApiMetadata,
        tags=["system"],
    )
    return router
