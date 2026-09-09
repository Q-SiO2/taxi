"""Public recruiting catalog and applicant-owned city application API."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from taximobile_api.domains.administration.service import audit
from taximobile_api.domains.auth.dependencies import CurrentPrincipal, authenticated_principal
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.driver_applications.models import (
    DriverCityApplication,
    DriverRequirementVersion,
    RequirementVersionStatus,
)
from taximobile_api.domains.driver_applications.documents import (
    attach_clean_document,
    preflight_document_change,
    remove_document,
)
from taximobile_api.domains.driver_applications.presenters import (
    city_application_response,
    city_application_summary_response,
    recruiting_city_response,
    requirement_item_response,
)
from taximobile_api.domains.driver_applications.schemas import (
    CityApplicationCreateRequest,
    CityApplicationListResponse,
    CityApplicationResponse,
    CityApplicationUpdateRequest,
    PublicRequirementVersionResponse,
    RecruitingCityListResponse,
)
from taximobile_api.domains.driver_applications.service import (
    ApplicationIncomplete,
    ApplicationReferenceInvalid,
    RecruitmentConflict,
    RecruitmentNotFound,
    active_requirement_for_city,
    create_city_application,
    owned_application,
    requirement_items,
    submit_city_application,
    update_city_application,
    withdraw_city_application,
)
from taximobile_api.domains.drivers.models import DriverProfile
from taximobile_api.domains.markets.models import City, CityLifecycleStatus
from taximobile_api.integrations.driver_documents import (
    DriverDocumentError,
    DriverDocumentRejected,
)


router = APIRouter(tags=["driver-city-applications"])


def document_store_available(request: Request) -> bool:
    return bool(request.app.state.driver_document_store.available)


def recruitment_http_error(error: Exception) -> HTTPException:
    if isinstance(error, RecruitmentNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, ApplicationIncomplete):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The application does not satisfy every required item.",
        )
    if isinstance(error, ApplicationReferenceInvalid):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        )
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@router.get(
    "/drivers/recruiting-cities",
    response_model=RecruitingCityListResponse,
)
async def list_recruiting_cities(
    session: AsyncSession = Depends(database_session),
) -> RecruitingCityListResponse:
    now = datetime.now(UTC)
    rows = (
        await session.execute(
            select(City, DriverRequirementVersion)
            .join(DriverRequirementVersion, DriverRequirementVersion.city_id == City.id)
            .where(
                City.lifecycle_status.in_(
                    {
                        CityLifecycleStatus.CONFIGURING,
                        CityLifecycleStatus.PILOT,
                        CityLifecycleStatus.ACTIVE,
                    }
                ),
                DriverRequirementVersion.status == RequirementVersionStatus.ACTIVE,
                DriverRequirementVersion.effective_from <= now,
                or_(
                    DriverRequirementVersion.effective_until.is_(None),
                    DriverRequirementVersion.effective_until > now,
                ),
            )
            .order_by(City.code, City.id)
        )
    ).all()
    return RecruitingCityListResponse(
        items=[recruiting_city_response(city, version) for city, version in rows]
    )


@router.get(
    "/drivers/recruiting-cities/{city_id}/requirements",
    response_model=PublicRequirementVersionResponse,
)
async def get_recruiting_city_requirements(
    city_id: UUID,
    request: Request,
    session: AsyncSession = Depends(database_session),
) -> PublicRequirementVersionResponse:
    try:
        city, version = await active_requirement_for_city(session, city_id)
    except RecruitmentNotFound as error:
        raise recruitment_http_error(error) from error
    items = await requirement_items(session, version.id)
    city_response = recruiting_city_response(city, version)
    return PublicRequirementVersionResponse(
        city=city_response,
        requirement_version_id=version.id,
        requirement_version=version.version,
        effective_from=version.effective_from,
        effective_until=version.effective_until,
        document_upload_available=document_store_available(request),
        items=[requirement_item_response(item) for item in items],
    )


@router.post(
    "/drivers/me/city-applications",
    response_model=CityApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_my_city_application(
    payload: CityApplicationCreateRequest,
    request: Request,
    response: Response,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> CityApplicationResponse:
    try:
        async with session.begin():
            application, created = await create_city_application(
                session,
                user_id=principal.user_id,
                city_id=payload.city_id,
                display_name=payload.display_name,
            )
            city = await session.get(City, application.city_id)
            assert city is not None
            if created:
                await audit(
                    session,
                    actor_user_id=principal.user_id,
                    action="DRIVER_CITY_APPLICATION_CREATED",
                    resource_type="driver_city_application",
                    resource_id=application.id,
                    market_id=city.market_id,
                    city_id=city.id,
                    changes={
                        "status": application.status.value,
                        "requirement_version_id": str(application.requirement_version_id),
                    },
                )
            result = await city_application_response(
                session,
                application,
                document_upload_available=document_store_available(request),
            )
        if not created:
            response.status_code = status.HTTP_200_OK
        return result
    except (RecruitmentNotFound, RecruitmentConflict, ApplicationReferenceInvalid) as error:
        raise recruitment_http_error(error) from error


async def applicant_driver_id(session: AsyncSession, user_id: UUID) -> UUID | None:
    return await session.scalar(
        select(DriverProfile.id).where(DriverProfile.user_id == user_id)
    )


@router.get(
    "/drivers/me/city-applications",
    response_model=CityApplicationListResponse,
)
async def list_my_city_applications(
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> CityApplicationListResponse:
    driver_id = await applicant_driver_id(session, principal.user_id)
    if driver_id is None:
        return CityApplicationListResponse(items=[])
    applications = list(
        await session.scalars(
            select(DriverCityApplication)
            .where(DriverCityApplication.driver_id == driver_id)
            .order_by(DriverCityApplication.created_at.desc(), DriverCityApplication.id)
        )
    )
    return CityApplicationListResponse(
        items=[
            await city_application_summary_response(session, application)
            for application in applications
        ]
    )


async def my_application_or_404(
    session: AsyncSession,
    *,
    user_id: UUID,
    application_id: UUID,
    lock: bool = False,
) -> DriverCityApplication:
    driver_id = await applicant_driver_id(session, user_id)
    if driver_id is None:
        raise RecruitmentNotFound("Driver city application not found.")
    return await owned_application(session, application_id, driver_id, lock=lock)


@router.get(
    "/drivers/me/city-applications/{application_id}",
    response_model=CityApplicationResponse,
)
async def get_my_city_application(
    application_id: UUID,
    request: Request,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> CityApplicationResponse:
    try:
        application = await my_application_or_404(
            session,
            user_id=principal.user_id,
            application_id=application_id,
        )
    except RecruitmentNotFound as error:
        raise recruitment_http_error(error) from error
    return await city_application_response(
        session,
        application,
        document_upload_available=document_store_available(request),
    )


@router.patch(
    "/drivers/me/city-applications/{application_id}",
    response_model=CityApplicationResponse,
)
async def update_my_city_application(
    application_id: UUID,
    payload: CityApplicationUpdateRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> CityApplicationResponse:
    try:
        async with session.begin():
            application = await my_application_or_404(
                session,
                user_id=principal.user_id,
                application_id=application_id,
                lock=True,
            )
            application = await update_city_application(session, application, payload)
            result = await city_application_response(
                session,
                application,
                document_upload_available=document_store_available(request),
            )
        return result
    except (
        RecruitmentNotFound,
        RecruitmentConflict,
        ApplicationReferenceInvalid,
    ) as error:
        raise recruitment_http_error(error) from error


@router.post(
    "/drivers/me/city-applications/{application_id}/submit",
    response_model=CityApplicationResponse,
)
async def submit_my_city_application(
    application_id: UUID,
    request: Request,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> CityApplicationResponse:
    if not await request.app.state.rate_limiter.allow(
        f"city-application-submit:{principal.user_id}",
        limit=request.app.state.settings.verification_submission_rate_limit_per_hour,
        window_seconds=3600,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many application submissions. Try again later.",
        )
    try:
        async with session.begin():
            application = await my_application_or_404(
                session,
                user_id=principal.user_id,
                application_id=application_id,
                lock=True,
            )
            previous_status = application.status
            application = await submit_city_application(session, application)
            if application.status != previous_status:
                city = await session.get(City, application.city_id)
                assert city is not None
                await audit(
                    session,
                    actor_user_id=principal.user_id,
                    action="DRIVER_CITY_APPLICATION_SUBMITTED",
                    resource_type="driver_city_application",
                    resource_id=application.id,
                    market_id=city.market_id,
                    city_id=city.id,
                    changes={
                        "previous_status": previous_status.value,
                        "current_status": application.status.value,
                        "submission_revision": application.submission_revision,
                    },
                )
            result = await city_application_response(
                session,
                application,
                document_upload_available=document_store_available(request),
            )
        return result
    except (
        RecruitmentNotFound,
        RecruitmentConflict,
        ApplicationReferenceInvalid,
        ApplicationIncomplete,
    ) as error:
        raise recruitment_http_error(error) from error


@router.post(
    "/drivers/me/city-applications/{application_id}/withdraw",
    response_model=CityApplicationResponse,
)
async def withdraw_my_city_application(
    application_id: UUID,
    request: Request,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> CityApplicationResponse:
    try:
        async with session.begin():
            application = await my_application_or_404(
                session,
                user_id=principal.user_id,
                application_id=application_id,
                lock=True,
            )
            previous_status = application.status
            application = await withdraw_city_application(session, application)
            if application.status != previous_status:
                city = await session.get(City, application.city_id)
                assert city is not None
                await audit(
                    session,
                    actor_user_id=principal.user_id,
                    action="DRIVER_CITY_APPLICATION_WITHDRAWN",
                    resource_type="driver_city_application",
                    resource_id=application.id,
                    market_id=city.market_id,
                    city_id=city.id,
                    changes={
                        "previous_status": previous_status.value,
                        "current_status": application.status.value,
                    },
                )
            result = await city_application_response(
                session,
                application,
                document_upload_available=document_store_available(request),
            )
        return result
    except (RecruitmentNotFound, RecruitmentConflict) as error:
        raise recruitment_http_error(error) from error


async def require_owned_document_application(
    session: AsyncSession,
    *,
    principal: CurrentPrincipal,
    application_id: UUID,
) -> None:
    try:
        await my_application_or_404(
            session,
            user_id=principal.user_id,
            application_id=application_id,
        )
    except RecruitmentNotFound as error:
        raise recruitment_http_error(error) from error


async def read_bounded_upload(upload: UploadFile, maximum_bytes: int) -> bytes:
    content = bytearray()
    while len(content) <= maximum_bytes:
        chunk = await upload.read(min(64 * 1024, maximum_bytes + 1 - len(content)))
        if not chunk:
            break
        content.extend(chunk)
    if len(content) > maximum_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"The document exceeds the {maximum_bytes}-byte limit.",
        )
    return bytes(content)


@router.post(
    "/drivers/me/city-applications/{application_id}/documents",
    status_code=status.HTTP_201_CREATED,
    response_model=CityApplicationResponse,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": [
                            "requirement_item_id",
                            "expected_application_version",
                            "file",
                        ],
                        "properties": {
                            "requirement_item_id": {"type": "string", "format": "uuid"},
                            "expected_application_version": {
                                "type": "integer",
                                "minimum": 1,
                            },
                            "file": {"type": "string", "format": "binary"},
                        },
                    }
                }
            },
        }
    },
)
async def upload_city_application_document(
    application_id: UUID,
    request: Request,
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> CityApplicationResponse:
    try:
        async with session.begin():
            await my_application_or_404(
                session,
                user_id=principal.user_id,
                application_id=application_id,
            )
    except RecruitmentNotFound as error:
        raise recruitment_http_error(error) from error
    if not document_store_available(request):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Protected document upload is not configured for this deployment.",
        )

    try:
        form = await request.form(
            max_files=1,
            max_fields=2,
            max_part_size=request.app.state.driver_document_store.max_bytes,
        )
        if len(form.multi_items()) != 3 or set(form) != {
            "requirement_item_id",
            "expected_application_version",
            "file",
        }:
            raise ValueError
        requirement_item_id = UUID(str(form["requirement_item_id"]))
        expected_application_version = int(str(form["expected_application_version"]))
        file = form["file"]
        if expected_application_version < 1 or not isinstance(file, UploadFile):
            raise ValueError
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=422,
            detail="A requirement item, positive application version, and one file are required.",
        ) from error

    try:
        async with session.begin():
            application = await my_application_or_404(
                session,
                user_id=principal.user_id,
                application_id=application_id,
                lock=True,
            )
            await preflight_document_change(
                session,
                application,
                requirement_item_id=requirement_item_id,
                expected_version=expected_application_version,
            )
    except (RecruitmentNotFound, RecruitmentConflict, ApplicationReferenceInvalid) as error:
        await file.close()
        raise recruitment_http_error(error) from error

    if not await request.app.state.rate_limiter.allow(
        f"driver-document-upload:{principal.user_id}",
        limit=request.app.state.settings.driver_document_upload_rate_limit_per_hour,
        window_seconds=3600,
    ):
        await file.close()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many document uploads. Try again later.",
        )

    store = request.app.state.driver_document_store
    try:
        content = await read_bounded_upload(file, store.max_bytes)
        stored = await store.store(content, declared_media_type=file.content_type)
    except DriverDocumentRejected as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except DriverDocumentError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    finally:
        await file.close()

    replaced_key: str | None = None
    try:
        async with session.begin():
            application = await my_application_or_404(
                session,
                user_id=principal.user_id,
                application_id=application_id,
                lock=True,
            )
            document, replaced_key = await attach_clean_document(
                session,
                application,
                requirement_item_id=requirement_item_id,
                expected_version=expected_application_version,
                stored=stored,
                retention_days=request.app.state.settings.driver_document_retention_days,
            )
            city = await session.get(City, application.city_id)
            assert city is not None
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="DRIVER_APPLICATION_DOCUMENT_UPLOADED",
                resource_type="driver_application_document",
                resource_id=document.id,
                market_id=city.market_id,
                city_id=city.id,
                changes={
                    "application_id": str(application.id),
                    "requirement_item_id": str(requirement_item_id),
                    "media_type": document.media_type,
                    "byte_size": document.byte_size,
                    "scan_status": document.malware_scan_status.value,
                },
            )
            result = await city_application_response(
                session,
                application,
                document_upload_available=True,
            )
    except (RecruitmentNotFound, RecruitmentConflict, ApplicationReferenceInvalid) as error:
        try:
            await store.delete(stored.opaque_storage_key)
        except DriverDocumentError:
            pass
        raise recruitment_http_error(error) from error
    except Exception:
        try:
            await store.delete(stored.opaque_storage_key)
        except DriverDocumentError:
            pass
        raise

    if replaced_key is not None:
        try:
            await store.delete(replaced_key)
        except DriverDocumentError:
            # The retention worker retries objects whose database row is soft-deleted.
            pass
    return result


@router.delete(
    "/drivers/me/city-applications/{application_id}/documents/{document_id}",
    response_model=CityApplicationResponse,
)
async def delete_city_application_document(
    application_id: UUID,
    document_id: UUID,
    request: Request,
    expected_application_version: int = Query(ge=1),
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> CityApplicationResponse:
    if not document_store_available(request):
        await require_owned_document_application(
            session,
            principal=principal,
            application_id=application_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Protected document storage is not configured for this deployment.",
        )
    try:
        async with session.begin():
            application = await my_application_or_404(
                session,
                user_id=principal.user_id,
                application_id=application_id,
                lock=True,
            )
            document = await remove_document(
                session,
                application,
                document_id=document_id,
                expected_version=expected_application_version,
            )
            city = await session.get(City, application.city_id)
            assert city is not None
            await audit(
                session,
                actor_user_id=principal.user_id,
                action="DRIVER_APPLICATION_DOCUMENT_DELETED",
                resource_type="driver_application_document",
                resource_id=document.id,
                market_id=city.market_id,
                city_id=city.id,
                changes={
                    "application_id": str(application.id),
                    "requirement_item_id": str(document.requirement_item_id),
                },
            )
            result = await city_application_response(
                session,
                application,
                document_upload_available=True,
            )
    except (RecruitmentNotFound, RecruitmentConflict, ApplicationReferenceInvalid) as error:
        raise recruitment_http_error(error) from error

    try:
        await request.app.state.driver_document_store.delete(document.opaque_storage_key)
    except DriverDocumentError:
        # The row remains soft-deleted so the retention worker can retry cleanup.
        pass
    return result
