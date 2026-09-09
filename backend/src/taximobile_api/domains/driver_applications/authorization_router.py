"""Scoped and replay-safe human decisions over existing city authorizations."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.operations_dependencies import (
    OperationsSessionIdentity, require_recent_operations_mfa, require_operations_permission,
)
from taximobile_api.domains.administration.permissions import OperationsPrincipal
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.idempotency.service import (
    IdempotencyKeyReuse, IdempotentReplay, InvalidIdempotencyKey, begin_command, finish_command,
)
from fastapi import HTTPException

from .authorization_lifecycle import AuthorizationDecisionRequest, decide_authorization
from .operations_router import (
    REVIEW_APPLICATIONS, operations_application_detail, scoped_application_or_404,
)
from .schemas import OperationsDriverApplicationDetailResponse
from .service import RecruitmentConflict


router = APIRouter(prefix="/operations", tags=["operations-driver-authorizations"])


@router.post(
    "/driver-applications/{application_id}/authorization/decisions",
    response_model=OperationsDriverApplicationDetailResponse,
)
async def decide_driver_city_authorization(
    application_id: UUID,
    payload: AuthorizationDecisionRequest,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(require_operations_permission(REVIEW_APPLICATIONS)),
    session: AsyncSession = Depends(database_session),
) -> OperationsDriverApplicationDetailResponse | JSONResponse:
    try:
        async with session.begin():
            # Scope is checked even for an idempotent replay: removed city
            # access must not expose a cached applicant response.
            await scoped_application_or_404(session, principal, application_id)
            command = await begin_command(
                session, user_id=principal.user_id,
                operation=f"operations-driver-authorization:{application_id}",
                key=idempotency_key, payload=payload.model_dump(mode="json"),
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            application = await decide_authorization(
                session, application_id=application_id,
                reviewer_user_id=principal.user_id, payload=payload,
            )
            result = await operations_application_detail(
                session, application,
                document_upload_available=request.app.state.driver_document_store.available,
            )
            await finish_command(session, command, status_code=200, payload=result.model_dump(mode="json"))
        return result
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except (IdempotencyKeyReuse, RecruitmentConflict) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
