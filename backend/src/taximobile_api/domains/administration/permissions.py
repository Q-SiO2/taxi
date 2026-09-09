"""Named operations permissions and scope-aware authorization snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from taximobile_api.domains.administration.models import AdministrativeRoleTemplate


class OperationsPermission(StrEnum):
    VIEW_CONTROL_PLANE = "view_control_plane"
    MANAGE_CITY_LIFECYCLE = "manage_city_lifecycle"
    MANAGE_OPERATORS = "manage_operators"
    MANAGE_OPERATOR_ASSIGNMENTS = "manage_operator_assignments"
    MANAGE_CITY_CONFIGURATION = "manage_city_configuration"
    MANAGE_SERVICE_AREAS = "manage_service_areas"
    MANAGE_SCOPED_STAFF_GRANTS = "manage_scoped_staff_grants"
    VIEW_SCOPED_AUDIT = "view_scoped_audit"
    REVIEW_DRIVER_APPLICATIONS = "review_driver_applications"
    MANAGE_DRIVER_REQUIREMENTS = "manage_driver_requirements"
    MANAGE_CITY_TARIFFS = "manage_city_tariffs"
    MANAGE_OPERATOR_FEE_POLICIES = "manage_operator_fee_policies"
    MANAGE_FIXED_ROUTES = "manage_fixed_routes"
    MANAGE_SCHEDULING_POLICY = "manage_scheduling_policy"
    MANAGE_PAYMENT_CAPABILITIES = "manage_payment_capabilities"
    RECONCILE_PAYMENTS = "reconcile_payments"
    MANAGE_SUPPORT_CASES = "manage_support_cases"
    MANAGE_SAFETY_CASES = "manage_safety_cases"
    MANAGE_CASE_RETENTION = "manage_case_retention"
    MANAGE_ACCOUNT_SECURITY = "manage_account_security"
    MANAGE_SECURITY_INCIDENTS = "manage_security_incidents"
    VIEW_SCOPED_OPERATIONAL_AGGREGATES = "view_scoped_operational_aggregates"


FOUNDATION_ADMIN_PERMISSIONS = frozenset(
    {
        OperationsPermission.VIEW_CONTROL_PLANE,
        OperationsPermission.MANAGE_CITY_LIFECYCLE,
        OperationsPermission.MANAGE_OPERATORS,
        OperationsPermission.MANAGE_OPERATOR_ASSIGNMENTS,
        OperationsPermission.MANAGE_CITY_CONFIGURATION,
        OperationsPermission.MANAGE_SERVICE_AREAS,
        OperationsPermission.MANAGE_SCOPED_STAFF_GRANTS,
        OperationsPermission.VIEW_SCOPED_AUDIT,
        OperationsPermission.MANAGE_DRIVER_REQUIREMENTS,
    }
)


ROLE_PERMISSIONS: dict[AdministrativeRoleTemplate, frozenset[OperationsPermission]] = {
    AdministrativeRoleTemplate.PLATFORM_ADMIN: frozenset(OperationsPermission),
    AdministrativeRoleTemplate.OPERATOR_ADMIN: frozenset(
        {
            OperationsPermission.VIEW_CONTROL_PLANE,
            OperationsPermission.MANAGE_CITY_CONFIGURATION,
            OperationsPermission.VIEW_SCOPED_AUDIT,
            OperationsPermission.VIEW_SCOPED_OPERATIONAL_AGGREGATES,
            OperationsPermission.MANAGE_FIXED_ROUTES,
            OperationsPermission.MANAGE_PAYMENT_CAPABILITIES,
        }
    ),
    AdministrativeRoleTemplate.CITY_MANAGER: (
        FOUNDATION_ADMIN_PERMISSIONS
        | {
            OperationsPermission.MANAGE_FIXED_ROUTES,
            OperationsPermission.MANAGE_PAYMENT_CAPABILITIES,
        }
    )
    - {
        OperationsPermission.MANAGE_OPERATORS,
        OperationsPermission.MANAGE_OPERATOR_ASSIGNMENTS,
        OperationsPermission.MANAGE_SCOPED_STAFF_GRANTS,
    },
    AdministrativeRoleTemplate.DRIVER_REVIEWER: frozenset(
        {
            OperationsPermission.VIEW_CONTROL_PLANE,
            OperationsPermission.REVIEW_DRIVER_APPLICATIONS,
        }
    ),
    AdministrativeRoleTemplate.PRICING_MANAGER: frozenset(
        {
            OperationsPermission.VIEW_CONTROL_PLANE,
            OperationsPermission.MANAGE_CITY_TARIFFS,
            OperationsPermission.MANAGE_OPERATOR_FEE_POLICIES,
            OperationsPermission.MANAGE_SCHEDULING_POLICY,
        }
    ),
    AdministrativeRoleTemplate.PAYMENT_RECONCILER: frozenset(
        {
            OperationsPermission.VIEW_CONTROL_PLANE,
            OperationsPermission.RECONCILE_PAYMENTS,
        }
    ),
    AdministrativeRoleTemplate.SUPPORT_AGENT: frozenset(
        {
            OperationsPermission.VIEW_CONTROL_PLANE,
            OperationsPermission.MANAGE_SUPPORT_CASES,
        }
    ),
    AdministrativeRoleTemplate.SAFETY_RESPONDER: frozenset(
        {
            OperationsPermission.VIEW_CONTROL_PLANE,
            OperationsPermission.MANAGE_SAFETY_CASES,
        }
    ),
    AdministrativeRoleTemplate.ANALYST: frozenset(
        {
            OperationsPermission.VIEW_CONTROL_PLANE,
            OperationsPermission.VIEW_SCOPED_OPERATIONAL_AGGREGATES,
        }
    ),
}


@dataclass(frozen=True, slots=True)
class GrantAuthorization:
    """One grant expanded with only the resource IDs its scope covers."""

    grant_id: UUID
    role_template: AdministrativeRoleTemplate
    permissions: frozenset[OperationsPermission]
    market_id: UUID | None
    operator_id: UUID | None
    city_id: UUID | None
    covered_operator_ids: frozenset[UUID]
    covered_city_ids: frozenset[UUID]

    def allows(
        self,
        permission: OperationsPermission,
        *,
        market_id: UUID | None = None,
        operator_id: UUID | None = None,
        city_id: UUID | None = None,
    ) -> bool:
        if permission not in self.permissions:
            return False
        if city_id is not None:
            return city_id in self.covered_city_ids
        if operator_id is not None:
            return operator_id in self.covered_operator_ids
        if market_id is not None:
            # Market-wide authority exists only on a market-scoped grant.  A
            # child grant knows its parent market for presentation/filtering but
            # must not thereby create cities or mutate sibling resources.
            return (
                self.operator_id is None
                and self.city_id is None
                and self.market_id == market_id
            )
        return True


@dataclass(frozen=True, slots=True)
class OperationsPrincipal:
    user_id: UUID
    session_id: UUID
    grants: tuple[GrantAuthorization, ...]

    def allows(
        self,
        permission: OperationsPermission,
        *,
        market_id: UUID | None = None,
        operator_id: UUID | None = None,
        city_id: UUID | None = None,
    ) -> bool:
        return any(
            grant.allows(
                permission,
                market_id=market_id,
                operator_id=operator_id,
                city_id=city_id,
            )
            for grant in self.grants
        )

    def market_ids_for(self, permission: OperationsPermission) -> frozenset[UUID]:
        return frozenset(
            grant.market_id
            for grant in self.grants
            if permission in grant.permissions and grant.market_id is not None
        )

    def operator_ids_for(self, permission: OperationsPermission) -> frozenset[UUID]:
        return frozenset(
            operator_id
            for grant in self.grants
            if permission in grant.permissions
            for operator_id in grant.covered_operator_ids
        )

    def city_ids_for(self, permission: OperationsPermission) -> frozenset[UUID]:
        return frozenset(
            city_id
            for grant in self.grants
            if permission in grant.permissions
            for city_id in grant.covered_city_ids
        )
