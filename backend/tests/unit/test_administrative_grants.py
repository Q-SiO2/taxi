import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
import pytest
from pydantic import ValidationError

from taximobile_api.domains.administration.models import AdministrativeRoleTemplate
from taximobile_api.domains.administration.operations_router import (
    _reject_direct_grant_mutation,
    create_administrative_grant,
)
from taximobile_api.domains.administration.operations_schemas import (
    AdministrativeGrantCreateRequest,
)
from taximobile_api.domains.administration.permissions import OperationsPrincipal


def test_grant_creation_rejects_self_grant_before_database_access() -> None:
    user_id = uuid4()
    payload = AdministrativeGrantCreateRequest(
        user_id=user_id,
        role_template=AdministrativeRoleTemplate.PLATFORM_ADMIN,
        market_id=uuid4(),
        expires_at=datetime.now(UTC) + timedelta(days=30),
        reason="Quarterly access assignment",
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            create_administrative_grant(
                payload=payload,
                http_request=object(),  # Self-grant fails before environment access.
                _recent_mfa=object(),  # Dependency already proved by routing tests.
                principal=OperationsPrincipal(user_id, uuid4(), ()),
                session=object(),  # Self-grant must fail before any database call.
            )
        )

    assert error.value.status_code == 409
    assert "different authorized administrator" in error.value.detail


@pytest.mark.parametrize(
    ("role", "scope"),
    [
        (AdministrativeRoleTemplate.PLATFORM_ADMIN, "city_id"),
        (AdministrativeRoleTemplate.OPERATOR_ADMIN, "market_id"),
        (AdministrativeRoleTemplate.DRIVER_REVIEWER, "operator_id"),
    ],
)
def test_grant_schema_rejects_role_scope_mismatch(role, scope) -> None:
    values = {
        "user_id": uuid4(),
        "role_template": role,
        scope: uuid4(),
        "reason": "Reviewed assignment",
    }
    with pytest.raises(ValidationError, match="Role template and administrative scope"):
        AdministrativeGrantCreateRequest(**values)


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_direct_grant_mutation_is_disabled_outside_local_test_scaffolding(
    environment: str,
) -> None:
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(settings=SimpleNamespace(environment=environment))
        )
    )

    with pytest.raises(HTTPException) as error:
        _reject_direct_grant_mutation(request)

    assert error.value.status_code == 409
    assert "maker-checker" in error.value.detail


def test_direct_grant_mutation_remains_available_to_test_fixtures() -> None:
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(settings=SimpleNamespace(environment="test"))
        )
    )

    assert _reject_direct_grant_mutation(request) is None
