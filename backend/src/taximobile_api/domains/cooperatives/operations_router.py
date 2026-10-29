"""Scoped, MFA-protected maintenance of an operator's existing driver register."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.administration.operations_dependencies import (
    OperationsSessionIdentity, require_operations_permission, require_recent_operations_mfa,
)
from taximobile_api.domains.administration.permissions import OperationsPermission, OperationsPrincipal
from taximobile_api.domains.administration.service import audit
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.cooperatives.models import Cooperative, CooperativeMembership
from taximobile_api.domains.cooperatives.operations_schemas import (
    OperatorMembershipCreateRequest, OperatorMembershipListResponse,
    OperatorMembershipResponse, OperatorMembershipUpdateRequest,
)
from taximobile_api.domains.driver_applications.models import DriverCityApplication
from taximobile_api.domains.drivers.models import DriverProfile
from taximobile_api.domains.idempotency.service import (
    IdempotentReplay, IdempotencyKeyReuse, InvalidIdempotencyKey, begin_command, finish_command,
)
from taximobile_api.domains.markets.models import Operator, OperatorCityAssignment

router = APIRouter(prefix="/operations/operators", tags=["operations-memberships"])
MANAGE = OperationsPermission.MANAGE_OPERATORS


async def scoped_register(session, principal, operator_id, *, lock=False):
    statement = select(Operator).where(
        Operator.id == operator_id, Operator.id.in_(principal.operator_ids_for(MANAGE)),
    )
    if lock:
        # The parent remains stable while a member changes. This matches the
        # admission lock order without exclusively locking all operator work.
        statement = statement.with_for_update(read=True)
    operator = await session.scalar(statement.execution_options(populate_existing=True))
    if operator is None:
        raise HTTPException(status_code=404, detail="Operator not found.")
    if operator.cooperative_id is None:
        raise HTTPException(status_code=409, detail="This operator has no linked membership register.")
    return operator


async def response(session, member):
    driver_id = await session.scalar(select(DriverProfile.id).where(DriverProfile.user_id == member.user_id))
    return member_response(member, driver_id)


def member_response(member, driver_id):
    return OperatorMembershipResponse(
        id=member.id, cooperative_id=member.cooperative_id, driver_id=driver_id,
        status=member.membership_status.value, membership_number=member.membership_number,
        joined_at=member.joined_at, ended_at=member.ended_at, updated_at=member.updated_at,
    )


def audit_state(member):
    return {
        "status": member.membership_status.value,
        "joined_at": member.joined_at.isoformat() if member.joined_at else None,
        "ended_at": member.ended_at.isoformat() if member.ended_at else None,
    }


@router.get("/{operator_id}/memberships", response_model=OperatorMembershipListResponse)
async def list_memberships(
    operator_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE)),
    session: AsyncSession = Depends(database_session),
):
    operator = await scoped_register(session, principal, operator_id)
    organization = await session.get(Cooperative, operator.cooperative_id)
    total = await session.scalar(select(func.count(CooperativeMembership.id)).where(
        CooperativeMembership.cooperative_id == operator.cooperative_id,
    ))
    rows = (await session.execute(
        select(CooperativeMembership, DriverProfile.id)
        .outerjoin(DriverProfile, DriverProfile.user_id == CooperativeMembership.user_id)
        .where(CooperativeMembership.cooperative_id == operator.cooperative_id)
        .order_by(CooperativeMembership.created_at.desc(), CooperativeMembership.id)
        .offset((page - 1) * limit).limit(limit)
    )).all()
    return OperatorMembershipListResponse(
        operator_id=operator.id, cooperative_id=operator.cooperative_id,
        cooperative_status=organization.status.value,
        items=[member_response(member, driver_id) for member, driver_id in rows],
        page=page, limit=limit, total=total,
    )


@router.post("/{operator_id}/memberships", response_model=OperatorMembershipResponse, status_code=201)
async def create_membership(
    operator_id: UUID,
    payload: OperatorMembershipCreateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE)),
    session: AsyncSession = Depends(database_session),
):
    try:
        async with session.begin():
            operator = await scoped_register(session, principal, operator_id, lock=True)
            command = await begin_command(
                session, user_id=principal.user_id,
                operation=f"op-member-add:{operator.id.hex}:{operator.cooperative_id.hex}",
                key=idempotency_key, payload=payload.model_dump(mode="json"),
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            associated_application = exists(select(DriverCityApplication.id).join(
                OperatorCityAssignment, OperatorCityAssignment.city_id == DriverCityApplication.city_id,
            ).where(
                DriverCityApplication.driver_id == DriverProfile.id,
                OperatorCityAssignment.operator_id == operator.id,
            ))
            driver = await session.scalar(select(DriverProfile).where(
                DriverProfile.id == payload.driver_id, associated_application,
            ))
            if driver is None:
                raise HTTPException(status_code=404, detail="Driver not found in this operator's city applications.")
            member = CooperativeMembership(
                cooperative_id=operator.cooperative_id, user_id=driver.user_id,
                membership_status=payload.status, membership_number=payload.membership_number,
                joined_at=payload.joined_at, ended_at=payload.ended_at,
            )
            session.add(member)
            await session.flush()
            await audit(session, actor_user_id=principal.user_id,
                action="OPERATOR_MEMBERSHIP_CREATED", resource_type="cooperative_membership",
                resource_id=member.id, market_id=operator.market_id, operator_id=operator.id,
                changes={"current": audit_state(member), "reason": payload.reason})
            result = member_response(member, driver.id)
            await finish_command(session, command, status_code=201, payload=result.model_dump(mode="json"))
        return result
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail="The driver or membership number already exists in this register.") from error


@router.patch("/{operator_id}/memberships/{membership_id}", response_model=OperatorMembershipResponse)
async def update_membership(
    operator_id: UUID,
    membership_id: UUID,
    payload: OperatorMembershipUpdateRequest,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    _mfa: OperationsSessionIdentity = Depends(require_recent_operations_mfa),
    principal: OperationsPrincipal = Depends(require_operations_permission(MANAGE)),
    session: AsyncSession = Depends(database_session),
):
    try:
        async with session.begin():
            operator = await scoped_register(session, principal, operator_id, lock=True)
            member_query = select(CooperativeMembership).where(
                CooperativeMembership.id == membership_id,
                CooperativeMembership.cooperative_id == operator.cooperative_id,
            )
            if await session.scalar(member_query) is None:
                raise HTTPException(status_code=404, detail="Membership not found.")
            command = await begin_command(
                session, user_id=principal.user_id,
                operation=f"op-member-edit:{operator.id.hex}:{operator.cooperative_id.hex}:{membership_id.hex}",
                key=idempotency_key, payload=payload.model_dump(mode="json"),
            )
            if isinstance(command, IdempotentReplay):
                return JSONResponse(status_code=command.status_code, content=command.payload)
            member = await session.scalar(member_query.with_for_update().execution_options(populate_existing=True))
            if member is None:
                raise HTTPException(status_code=404, detail="Membership not found.")
            if member.updated_at != payload.expected_updated_at:
                raise HTTPException(status_code=409, detail="Membership changed. Refresh before editing.")
            previous = audit_state(member)
            number_changed = member.membership_number != payload.membership_number
            member.membership_status = payload.status
            member.membership_number = payload.membership_number
            member.joined_at = payload.joined_at
            member.ended_at = payload.ended_at
            member.updated_at = datetime.now(UTC)
            await session.flush()
            await audit(session, actor_user_id=principal.user_id,
                action="OPERATOR_MEMBERSHIP_UPDATED", resource_type="cooperative_membership",
                resource_id=member.id, market_id=operator.market_id, operator_id=operator.id,
                changes={"previous": previous, "current": audit_state(member),
                         "membership_number_changed": number_changed, "reason": payload.reason})
            result = await response(session, member)
            await finish_command(session, command, status_code=200, payload=result.model_dump(mode="json"))
        return result
    except InvalidIdempotencyKey as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except IdempotencyKeyReuse as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail="That membership number already exists in this register.") from error
