"""City-scoped legal holds and immutable retention evidence."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.operations_dependencies import (
    OperationsSessionIdentity,
    require_operations_permission,
    require_recent_operations_mfa,
)
from taximobile_api.domains.administration.permissions import OperationsPermission, OperationsPrincipal
from taximobile_api.domains.administration.service import audit
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.case_retention.models import (
    CaseLegalHold,
    CaseRetentionAction,
    CaseRetentionActionCode,
    LegalHoldReasonCode,
    LegalHoldReleaseReasonCode,
    LegalHoldStatus,
)
from taximobile_api.domains.case_retention.schemas import (
    CaseKind,
    CaseRetentionActionListResponse,
    CaseRetentionActionResponse,
    LegalHoldCreateRequest,
    LegalHoldListResponse,
    LegalHoldReleaseRequest,
    LegalHoldResponse,
)
from taximobile_api.domains.idempotency.service import (
    IdempotencyKeyReuse,
    IdempotentReplay,
    InvalidIdempotencyKey,
    begin_command,
    finish_command,
)
from taximobile_api.domains.safety.models import SafetyReport
from taximobile_api.domains.support.models import SupportTicket


router = APIRouter(prefix="/operations/case-retention", tags=["operations-case-retention"])
PERMISSION = OperationsPermission.MANAGE_CASE_RETENTION


def _case_identity(record: CaseLegalHold | CaseRetentionAction) -> tuple[CaseKind, UUID]:
    if record.support_ticket_id is not None:
        return CaseKind.SUPPORT, record.support_ticket_id
    assert record.safety_report_id is not None
    return CaseKind.SAFETY, record.safety_report_id


def hold_response(hold: CaseLegalHold) -> LegalHoldResponse:
    case_kind, case_id = _case_identity(hold)
    return LegalHoldResponse(
        id=hold.id,
        city_id=hold.city_id,
        case_kind=case_kind,
        case_id=case_id,
        status=LegalHoldStatus(hold.status),
        reason_code=LegalHoldReasonCode(hold.reason_code),
        authority_reference=hold.authority_reference,
        placed_by_user_id=hold.placed_by_user_id,
        placed_at=hold.placed_at,
        review_due_at=hold.review_due_at,
        released_by_user_id=hold.released_by_user_id,
        released_at=hold.released_at,
        release_reason_code=(
            LegalHoldReleaseReasonCode(hold.release_reason_code)
            if hold.release_reason_code is not None
            else None
        ),
    )


def action_response(action: CaseRetentionAction) -> CaseRetentionActionResponse:
    case_kind, case_id = _case_identity(action)
    return CaseRetentionActionResponse(
        id=action.id,
        city_id=action.city_id,
        case_kind=case_kind,
        case_id=case_id,
        action=CaseRetentionActionCode(action.action),
        retention_policy_version=action.retention_policy_version,
        retention_due_at=action.retention_due_at,
        executed_at=action.executed_at,
        erased_note_count=action.erased_note_count,
    )


def _authorized_cities(principal: OperationsPrincipal) -> frozenset[UUID]:
    city_ids = principal.city_ids_for(PERMISSION)
    if not city_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Case-retention authority is required.")
    return city_ids


async def _locked_case(
    session: AsyncSession,
    principal: OperationsPrincipal,
    case_kind: CaseKind,
    case_id: UUID,
) -> SupportTicket | SafetyReport:
    city_ids = _authorized_cities(principal)
    model = SupportTicket if case_kind == CaseKind.SUPPORT else SafetyReport
    case = await session.scalar(
        select(model).where(model.id == case_id, model.city_id.in_(city_ids)).with_for_update()
    )
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    if case.retention_processed_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Case retention has already been processed.")
    return case


@router.get("/holds", response_model=LegalHoldListResponse)
async def list_legal_holds(
    city_id: UUID | None = Query(default=None),
    hold_status: LegalHoldStatus | None = Query(default=None, alias="status"),
    case_kind: CaseKind | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> LegalHoldListResponse:
    city_ids = _authorized_cities(principal)
    if city_id is not None and city_id not in city_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City not found.")
    filters = [CaseLegalHold.city_id.in_(city_ids)]
    if city_id is not None:
        filters.append(CaseLegalHold.city_id == city_id)
    if hold_status is not None:
        filters.append(CaseLegalHold.status == hold_status.value)
    if case_kind == CaseKind.SUPPORT:
        filters.append(CaseLegalHold.support_ticket_id.is_not(None))
    elif case_kind == CaseKind.SAFETY:
        filters.append(CaseLegalHold.safety_report_id.is_not(None))
    holds = list(await session.scalars(select(CaseLegalHold).where(*filters).order_by(CaseLegalHold.status.asc(), CaseLegalHold.review_due_at.asc(), CaseLegalHold.id.asc()).offset((page - 1) * limit).limit(limit)))
    total = await session.scalar(select(func.count()).select_from(CaseLegalHold).where(*filters))
    return LegalHoldListResponse(items=[hold_response(item) for item in holds], page=page, limit=limit, total=total or 0)


@router.post("/holds", response_model=LegalHoldResponse, status_code=status.HTTP_201_CREATED)
async def place_legal_hold(
    payload: LegalHoldCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> LegalHoldResponse:
    now = datetime.now(UTC)
    review_due_at = payload.review_due_at.astimezone(UTC) if payload.review_due_at.tzinfo else None
    if review_due_at is None or review_due_at <= now or review_due_at > now + timedelta(days=366):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="review_due_at must be timezone-aware and within the next 366 days.")
    try:
        async with session.begin():
            case = await _locked_case(session, principal, payload.case_kind, payload.case_id)
            command = await begin_command(session, user_id=principal.user_id, operation="operations.case_retention.hold.place", key=idempotency_key, payload=payload.model_dump(mode="json"))
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            case_filter = (
                CaseLegalHold.support_ticket_id == payload.case_id
                if payload.case_kind == CaseKind.SUPPORT
                else CaseLegalHold.safety_report_id == payload.case_id
            )
            if await session.scalar(select(CaseLegalHold.id).where(case_filter, CaseLegalHold.status == LegalHoldStatus.ACTIVE.value)) is not None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The case already has an active legal hold.")
            hold = CaseLegalHold(
                city_id=case.city_id,
                support_ticket_id=payload.case_id if payload.case_kind == CaseKind.SUPPORT else None,
                safety_report_id=payload.case_id if payload.case_kind == CaseKind.SAFETY else None,
                status=LegalHoldStatus.ACTIVE.value,
                reason_code=payload.reason_code.value,
                authority_reference=payload.authority_reference,
                placed_by_user_id=principal.user_id,
                placed_at=now,
                review_due_at=review_due_at,
                created_at=now,
                updated_at=now,
            )
            session.add(hold)
            await session.flush()
            await audit(session, actor_user_id=principal.user_id, action="CASE_LEGAL_HOLD_PLACED", resource_type="case_legal_hold", resource_id=hold.id, city_id=hold.city_id, changes={"case_kind": payload.case_kind.value, "reason_code": payload.reason_code.value, "authority_reference_recorded": True, "review_due_at": review_due_at.isoformat()})
            response = hold_response(hold)
            await finish_command(session, command, status_code=status.HTTP_201_CREATED, payload=response.model_dump(mode="json"))
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except IntegrityError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The case already has an active legal hold.") from error
    return response


@router.post("/holds/{hold_id}/release", response_model=LegalHoldResponse)
async def release_legal_hold(
    hold_id: UUID,
    payload: LegalHoldReleaseRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _recent_mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> LegalHoldResponse:
    try:
        async with session.begin():
            hold = await session.scalar(select(CaseLegalHold).where(CaseLegalHold.id == hold_id, CaseLegalHold.city_id.in_(_authorized_cities(principal))).with_for_update())
            if hold is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Legal hold not found.")
            command = await begin_command(session, user_id=principal.user_id, operation="operations.case_retention.hold.release", key=idempotency_key, payload={"hold_id": str(hold_id), **payload.model_dump(mode="json")})
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            if hold.status != LegalHoldStatus.ACTIVE.value:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only an active legal hold can be released.")
            now = datetime.now(UTC)
            hold.status = LegalHoldStatus.RELEASED.value
            hold.released_by_user_id = principal.user_id
            hold.released_at = now
            hold.release_reason_code = payload.reason_code.value
            hold.updated_at = now
            case_kind, _ = _case_identity(hold)
            await audit(session, actor_user_id=principal.user_id, action="CASE_LEGAL_HOLD_RELEASED", resource_type="case_legal_hold", resource_id=hold.id, city_id=hold.city_id, changes={"case_kind": case_kind.value, "release_reason_code": payload.reason_code.value})
            response = hold_response(hold)
            await finish_command(session, command, status_code=status.HTTP_200_OK, payload=response.model_dump(mode="json"))
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return response


@router.get("/actions", response_model=CaseRetentionActionListResponse)
async def list_retention_actions(
    city_id: UUID | None = Query(default=None),
    case_kind: CaseKind | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(require_operations_permission(PERMISSION)),
    session: AsyncSession = Depends(database_session),
) -> CaseRetentionActionListResponse:
    city_ids = _authorized_cities(principal)
    if city_id is not None and city_id not in city_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City not found.")
    filters = [CaseRetentionAction.city_id.in_(city_ids)]
    if city_id is not None:
        filters.append(CaseRetentionAction.city_id == city_id)
    if case_kind == CaseKind.SUPPORT:
        filters.append(CaseRetentionAction.support_ticket_id.is_not(None))
    elif case_kind == CaseKind.SAFETY:
        filters.append(CaseRetentionAction.safety_report_id.is_not(None))
    actions = list(await session.scalars(select(CaseRetentionAction).where(*filters).order_by(CaseRetentionAction.executed_at.desc(), CaseRetentionAction.id.desc()).offset((page - 1) * limit).limit(limit)))
    total = await session.scalar(select(func.count()).select_from(CaseRetentionAction).where(*filters))
    return CaseRetentionActionListResponse(items=[action_response(item) for item in actions], page=page, limit=limit, total=total or 0)
