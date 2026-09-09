from datetime import UTC, datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from taximobile_api.domains.auth.dependencies import CurrentPrincipal, authenticated_principal
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.drivers.models import AvailabilityStatus, DriverCredential, DriverLocation, DriverVerification, Vehicle, VehicleStatus, VehicleVerificationStatus
from taximobile_api.domains.drivers.schemas import (
    ActiveVehicleRequest,
    AvailabilityResponse,
    DriverApplicationRequest,
    DriverCredentialListResponse,
    DriverCredentialResponse,
    DriverProfileResponse,
    DriverRideListResponse,
    DriverRideResponse,
    LocationUpdateRequest,
    LocationUpdateResponse,
    OnlineAvailabilityRequest,
    VehicleCreateRequest,
    VehicleListResponse,
    VehicleResponse,
    VehicleUpdateRequest,
    VerificationResponse,
)
from taximobile_api.domains.driver_applications.service import (
    RecruitmentConflict,
    location_is_inside_active_service_area,
    select_active_authorization,
)
from taximobile_api.domains.fixed_routes.service import fixed_route_ride_summary
from taximobile_api.domains.markets.models import ServiceType
from taximobile_api.domains.drivers.service import (
    DriverApplicationExists,
    DriverMissing,
    VehicleConflict,
    VehicleNotEligible,
    VehicleOperationUnavailable,
    active_vehicle_eligibility_failure,
    can_change_vehicle,
    LocationRejected,
    apply_to_drive,
    driver_for_user,
    invalid_driver_credentials,
    invalidate_open_application_vehicle_evidence,
    online_eligibility_failure,
    record_location,
    register_vehicle,
    submit_verification,
    VerificationSubmissionUnavailable,
)
from taximobile_api.domains.rides.models import Ride, RideStatus


router = APIRouter(tags=["drivers"])


def profile_response(profile) -> DriverProfileResponse:
    return DriverProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        display_name=profile.display_name,
        verification_status=profile.verification_status.value,
        account_status=profile.account_status.value,
        availability_status=profile.availability_status.value,
    )


def vehicle_response(vehicle: Vehicle) -> VehicleResponse:
    return VehicleResponse(
        id=vehicle.id,
        make=vehicle.make,
        model=vehicle.model,
        color=vehicle.color,
        status=vehicle.status.value,
        verification_status=vehicle.verification_status.value,
    )


def credential_response(credential: DriverCredential) -> DriverCredentialResponse:
    return DriverCredentialResponse(
        id=credential.id,
        type=credential.credential_type,
        status=credential.verification_status.value,
        issued_at=credential.issued_at,
        expires_at=credential.expires_at,
    )


@router.post("/drivers/apply", response_model=DriverProfileResponse, status_code=status.HTTP_201_CREATED)
async def apply(
    payload: DriverApplicationRequest,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> DriverProfileResponse:
    try:
        async with session.begin():
            profile = await apply_to_drive(session, principal.user_id, payload)
    except DriverApplicationExists as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return profile_response(profile)


@router.get("/drivers/me", response_model=DriverProfileResponse)
async def get_driver(
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> DriverProfileResponse:
    try:
        return profile_response(await driver_for_user(session, principal.user_id))
    except DriverMissing as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/drivers/me/verification", response_model=VerificationResponse)
async def get_verification(
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> VerificationResponse:
    try:
        profile = await driver_for_user(session, principal.user_id)
    except DriverMissing as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    verification = await session.scalar(
        select(DriverVerification)
        .where(DriverVerification.driver_id == profile.id)
        .order_by(DriverVerification.created_at.desc())
    )
    return VerificationResponse(
        status=verification.status.value if verification else "NOT_STARTED",
        submitted_at=verification.submitted_at if verification else None,
    )


@router.post("/drivers/me/verification", response_model=VerificationResponse)
async def submit_driver_verification(
    request: Request,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> VerificationResponse:
    if not await request.app.state.rate_limiter.allow(
        f"verification:{principal.user_id}",
        limit=request.app.state.settings.verification_submission_rate_limit_per_hour,
        window_seconds=3600,
    ):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many verification submissions. Try again later.")
    try:
        async with session.begin():
            profile = await driver_for_user(session, principal.user_id)
            verification = await submit_verification(session, profile)
    except DriverMissing as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except VerificationSubmissionUnavailable as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return VerificationResponse(status=verification.status.value, submitted_at=verification.submitted_at)


@router.get("/drivers/me/credentials", response_model=DriverCredentialListResponse)
async def get_credentials(
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> DriverCredentialListResponse:
    try:
        profile = await driver_for_user(session, principal.user_id)
    except DriverMissing as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    credentials = list(
        await session.scalars(
            select(DriverCredential)
            .where(DriverCredential.driver_id == profile.id)
            .order_by(DriverCredential.credential_type, DriverCredential.created_at, DriverCredential.id)
        )
    )
    return DriverCredentialListResponse(credentials=[credential_response(item) for item in credentials])


@router.get("/drivers/me/vehicles", response_model=VehicleListResponse)
async def get_vehicles(
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> VehicleListResponse:
    try:
        profile = await driver_for_user(session, principal.user_id)
    except DriverMissing as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    vehicles = list(await session.scalars(select(Vehicle).where(Vehicle.driver_id == profile.id)))
    return VehicleListResponse(vehicles=[vehicle_response(vehicle) for vehicle in vehicles])


@router.post("/drivers/me/vehicles", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    payload: VehicleCreateRequest,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> VehicleResponse:
    try:
        async with session.begin():
            profile = await driver_for_user(session, principal.user_id)
            vehicle = await register_vehicle(session, profile, payload)
    except DriverMissing as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except VehicleConflict as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return vehicle_response(vehicle)


async def owner_vehicle(session: AsyncSession, profile, vehicle_id: UUID) -> Vehicle:
    vehicle = await session.get(Vehicle, vehicle_id)
    if vehicle is None or vehicle.driver_id != profile.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found.")
    return vehicle


@router.patch("/drivers/me/vehicles/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(
    vehicle_id: UUID,
    payload: VehicleUpdateRequest,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> VehicleResponse:
    try:
        async with session.begin():
            profile = await driver_for_user(session, principal.user_id, lock=True)
            reason = can_change_vehicle(profile)
            if reason:
                raise VehicleOperationUnavailable(reason)
            vehicle = await owner_vehicle(session, profile, vehicle_id)
            changes = payload.model_dump(exclude_unset=True)
            registration_number = changes.get("registration_number")
            if registration_number is not None:
                duplicate = await session.scalar(
                    select(Vehicle.id).where(
                        Vehicle.registration_number == registration_number,
                        Vehicle.id != vehicle.id,
                    )
                )
                if duplicate is not None:
                    raise VehicleConflict("A vehicle with that registration number already exists.")
            taxi_identifier = changes.get("taxi_identifier")
            if taxi_identifier is not None:
                duplicate = await session.scalar(
                    select(Vehicle.id).where(
                        Vehicle.taxi_identifier == taxi_identifier,
                        Vehicle.id != vehicle.id,
                    )
                )
                if duplicate is not None:
                    raise VehicleConflict("A vehicle with that taxi identifier already exists.")
            for field, value in changes.items():
                setattr(vehicle, field, value)
            # Client edits cannot retain dispatch eligibility without review.
            vehicle.verification_status = VehicleVerificationStatus.PENDING
            await invalidate_open_application_vehicle_evidence(session, vehicle.id)
    except DriverMissing as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except VehicleOperationUnavailable as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except VehicleConflict as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return vehicle_response(vehicle)


@router.delete("/drivers/me/vehicles/{vehicle_id}", response_model=VehicleResponse)
async def deactivate_vehicle(
    vehicle_id: UUID,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> VehicleResponse:
    try:
        async with session.begin():
            profile = await driver_for_user(session, principal.user_id, lock=True)
            reason = can_change_vehicle(profile)
            if reason:
                raise VehicleOperationUnavailable(reason)
            vehicle = await owner_vehicle(session, profile, vehicle_id)
            vehicle.status = VehicleStatus.INACTIVE
            await invalidate_open_application_vehicle_evidence(session, vehicle.id)
            if profile.active_vehicle_id == vehicle.id:
                profile.active_vehicle_id = None
    except DriverMissing as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except VehicleOperationUnavailable as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return vehicle_response(vehicle)


@router.post("/drivers/me/active-vehicle", response_model=AvailabilityResponse)
async def select_active_vehicle(
    payload: ActiveVehicleRequest,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> AvailabilityResponse:
    try:
        async with session.begin():
            profile = await driver_for_user(session, principal.user_id, lock=True)
            vehicle = await session.get(Vehicle, payload.vehicle_id)
            change_failure = can_change_vehicle(profile)
            if change_failure:
                raise VehicleNotEligible(change_failure)
            reason = active_vehicle_eligibility_failure(profile, vehicle)
            if reason == "Vehicle not found.":
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found.")
            if reason:
                raise VehicleNotEligible(reason)
            profile.active_vehicle_id = vehicle.id
    except DriverMissing as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except VehicleNotEligible as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return AvailabilityResponse(
        status=profile.availability_status.value,
        vehicle_id=profile.active_vehicle_id,
        city_id=profile.online_city_id,
        service_type=profile.online_service_type.value if profile.online_service_type else None,
    )


@router.post("/drivers/me/availability/online", response_model=AvailabilityResponse)
async def go_online(
    request: Request,
    payload: OnlineAvailabilityRequest | None = None,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> AvailabilityResponse:
    try:
        async with session.begin():
            profile = await driver_for_user(session, principal.user_id, lock=True)
            vehicle = await session.get(Vehicle, profile.active_vehicle_id) if profile.active_vehicle_id else None
            latest_location = await session.scalar(
                select(DriverLocation)
                .where(DriverLocation.driver_id == profile.id)
                .order_by(DriverLocation.observed_at.desc())
                .limit(1)
            )
            if await session.scalar(select(invalid_driver_credentials(profile.id, datetime.now(UTC)))):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A professional credential is unverified or expired.",
                )
            reason = online_eligibility_failure(
                profile,
                vehicle,
                latest_location_at=(
                    latest_location.observed_at if latest_location is not None else None
                ),
                location_freshness_seconds=request.app.state.settings.matching_location_freshness_seconds,
            )
            if reason:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=reason)
            requested_service = (
                payload.service_type
                if payload is not None
                else profile.online_service_type or ServiceType.ON_DEMAND
            )
            selected = await select_active_authorization(
                session,
                profile=profile,
                requested_city_id=(
                    payload.city_id if payload is not None else profile.online_city_id
                ),
                requested_service_type=requested_service,
            )
            assert latest_location is not None
            if not await location_is_inside_active_service_area(
                session,
                city=selected.city,
                location_id=latest_location.id,
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Current location is outside the active city service area.",
                )
            if profile.availability_status != AvailabilityStatus.AVAILABLE or profile.available_since is None:
                profile.available_since = datetime.now(UTC)
            profile.availability_status = AvailabilityStatus.AVAILABLE
            profile.online_city_id = selected.city.id
            profile.online_service_type = selected.service_type
    except DriverMissing as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except RecruitmentConflict as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return AvailabilityResponse(
        status=profile.availability_status.value,
        vehicle_id=profile.active_vehicle_id,
        city_id=profile.online_city_id,
        service_type=profile.online_service_type.value if profile.online_service_type else None,
    )


@router.get("/drivers/me/availability", response_model=AvailabilityResponse)
async def availability(
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> AvailabilityResponse:
    try:
        profile = await driver_for_user(session, principal.user_id)
    except DriverMissing as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return AvailabilityResponse(
        status=profile.availability_status.value,
        vehicle_id=profile.active_vehicle_id,
        city_id=profile.online_city_id,
        service_type=profile.online_service_type.value if profile.online_service_type else None,
    )


@router.post("/drivers/me/availability/offline", response_model=AvailabilityResponse)
async def go_offline(
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> AvailabilityResponse:
    try:
        async with session.begin():
            profile = await driver_for_user(session, principal.user_id, lock=True)
            if profile.availability_status in {AvailabilityStatus.EN_ROUTE, AvailabilityStatus.AT_PICKUP, AvailabilityStatus.ON_RIDE}:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An active ride must be handled first.")
            profile.availability_status = AvailabilityStatus.OFFLINE
            profile.available_since = None
            profile.online_city_id = None
            profile.online_service_type = None
    except DriverMissing as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return AvailabilityResponse(
        status=profile.availability_status.value,
        vehicle_id=profile.active_vehicle_id,
        city_id=profile.online_city_id,
        service_type=profile.online_service_type.value if profile.online_service_type else None,
    )


@router.post("/drivers/me/location", response_model=LocationUpdateResponse)
async def update_location(
    payload: LocationUpdateRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> LocationUpdateResponse:
    if not await request.app.state.rate_limiter.allow(
        f"location:{principal.user_id}",
        limit=request.app.state.settings.location_update_rate_limit_per_minute,
        window_seconds=60,
    ):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many location updates. Try again shortly.")
    try:
        async with session.begin():
            profile = await driver_for_user(session, principal.user_id, lock=True)
            location = await record_location(session, profile, payload)
    except DriverMissing as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except LocationRejected as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return LocationUpdateResponse(server_time=location.recorded_at)


@router.get("/drivers/me/rides", response_model=DriverRideListResponse)
async def driver_ride_history(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    ride_status: RideStatus | None = Query(default=None, alias="status"),
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> DriverRideListResponse:
    try:
        profile = await driver_for_user(session, principal.user_id)
    except DriverMissing as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    filters = [Ride.driver_id == profile.id]
    if ride_status is not None:
        filters.append(Ride.status == ride_status)
    statement = select(Ride).where(*filters).order_by(Ride.created_at.desc())
    rides = list(await session.scalars(statement.offset((page - 1) * limit).limit(limit)))
    total = await session.scalar(select(func.count()).select_from(Ride).where(*filters))
    items = []
    for ride in rides:
        items.append(
            DriverRideResponse(
                id=ride.id,
                status=ride.status.value,
                completed_at=ride.completed_at,
                service_type=ride.service_type.value,
                fixed_route=(
                    await fixed_route_ride_summary(session, ride.fixed_route_direction_id)
                    if ride.fixed_route_direction_id is not None
                    else None
                ),
            )
        )
    return DriverRideListResponse(
        items=items,
        page=page,
        limit=limit,
        total=total or 0,
    )
