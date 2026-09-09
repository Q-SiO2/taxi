from uuid import uuid4

import pytest
from pydantic import ValidationError

from taximobile_api.domains.administration.models import AdministrativeRoleTemplate
from taximobile_api.domains.administration.operations_schemas import (
    OperationsAccountSecurityActionRequest,
)
from taximobile_api.domains.administration.permissions import (
    GrantAuthorization,
    OperationsPermission,
    OperationsPrincipal,
    ROLE_PERMISSIONS,
)
from taximobile_api.domains.markets.schemas import MultiPolygonGeometry


def authorization(role, *, market_id=None, operator_id=None, city_id=None, cities=(), operators=()):
    return GrantAuthorization(
        grant_id=uuid4(),
        role_template=role,
        permissions=ROLE_PERMISSIONS[role],
        market_id=market_id,
        operator_id=operator_id,
        city_id=city_id,
        covered_operator_ids=frozenset(operators),
        covered_city_ids=frozenset(cities),
    )


def test_permissions_remain_bound_to_each_grant_scope() -> None:
    user_id = uuid4()
    market_id = uuid4()
    city_a = uuid4()
    city_b = uuid4()
    principal = OperationsPrincipal(
        user_id=user_id,
        session_id=uuid4(),
        grants=(
            authorization(
                AdministrativeRoleTemplate.CITY_MANAGER,
                market_id=market_id,
                city_id=city_a,
                cities=(city_a,),
            ),
            authorization(
                AdministrativeRoleTemplate.ANALYST,
                market_id=market_id,
                city_id=city_b,
                cities=(city_b,),
            ),
        ),
    )

    assert principal.allows(OperationsPermission.MANAGE_CITY_LIFECYCLE, city_id=city_a)
    assert not principal.allows(OperationsPermission.MANAGE_CITY_LIFECYCLE, city_id=city_b)
    assert not principal.allows(OperationsPermission.MANAGE_CITY_LIFECYCLE, market_id=market_id)
    assert principal.city_ids_for(OperationsPermission.VIEW_CONTROL_PLANE) == {city_a, city_b}


def test_only_market_scoped_grant_authorizes_market_level_command() -> None:
    market_id = uuid4()
    platform = OperationsPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        grants=(
            authorization(
                AdministrativeRoleTemplate.PLATFORM_ADMIN,
                market_id=market_id,
            ),
        ),
    )

    assert platform.allows(OperationsPermission.MANAGE_CITY_LIFECYCLE, market_id=market_id)
    assert platform.allows(OperationsPermission.MANAGE_ACCOUNT_SECURITY, market_id=market_id)

    for role in AdministrativeRoleTemplate:
        if role != AdministrativeRoleTemplate.PLATFORM_ADMIN:
            assert OperationsPermission.MANAGE_ACCOUNT_SECURITY not in ROLE_PERMISSIONS[role]


def test_account_security_case_reference_is_controlled_and_normalized() -> None:
    request = OperationsAccountSecurityActionRequest(
        reason_code="ACCOUNT_COMPROMISE",
        case_reference="  sec-case-2026  ",
    )

    assert request.case_reference == "SEC-CASE-2026"

    with pytest.raises(ValidationError):
        OperationsAccountSecurityActionRequest(
            reason_code="ACCOUNT_COMPROMISE",
            case_reference="customer called about a lost phone",
        )


def test_service_area_geometry_is_closed_bounded_and_serializable() -> None:
    geometry = MultiPolygonGeometry(
        coordinates=[
            [
                [
                    [-7.0, 33.8],
                    [-6.7, 33.8],
                    [-6.7, 34.1],
                    [-7.0, 34.1],
                    [-7.0, 33.8],
                ]
            ]
        ]
    )

    assert geometry.to_wkt().startswith("MULTIPOLYGON(((-7.0 33.8")
