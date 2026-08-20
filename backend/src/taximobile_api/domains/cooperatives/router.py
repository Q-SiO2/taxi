from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taximobile_api.domains.auth.dependencies import CurrentPrincipal, authenticated_principal
from taximobile_api.domains.auth.router import database_session
from taximobile_api.domains.cooperatives.models import (
    Cooperative,
    CooperativeMembership,
    CooperativeMembershipStatus,
)
from taximobile_api.domains.cooperatives.schemas import CooperativeMembershipResponse


router = APIRouter(prefix="/cooperative", tags=["cooperative"])


@router.get("/membership", response_model=CooperativeMembershipResponse)
async def current_membership(
    principal: CurrentPrincipal = Depends(authenticated_principal),
    session: AsyncSession = Depends(database_session),
) -> CooperativeMembershipResponse:
    rows = (
        await session.execute(
            select(CooperativeMembership, Cooperative)
            .join(Cooperative, Cooperative.id == CooperativeMembership.cooperative_id)
            .where(
                CooperativeMembership.user_id == principal.user_id,
                CooperativeMembership.membership_status != CooperativeMembershipStatus.ENDED,
            )
            .order_by(CooperativeMembership.updated_at.desc(), CooperativeMembership.id)
            .limit(2)
        )
    ).all()
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Current cooperative membership not found.")
    if len(rows) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Multiple current cooperative memberships require administrative resolution.",
        )
    membership, cooperative = rows[0]
    return CooperativeMembershipResponse(
        cooperative_id=cooperative.id,
        cooperative_name=cooperative.name,
        status=membership.membership_status.value,
        joined_at=membership.joined_at,
        membership_number=membership.membership_number,
    )
