from uuid import uuid4

import pytest
from pydantic import ValidationError

from taximobile_api.domains.markets.schemas import OperatorCreateRequest, OperatorUpdateRequest


def test_closed_shop_creation_requires_a_register_and_preserves_open_default():
    payload = dict(market_id=uuid4(), name="Synthetic operator", operator_type="LOCAL_ENTITY")
    assert not OperatorCreateRequest(**payload).requires_active_membership
    with pytest.raises(ValidationError, match="linked membership register"):
        OperatorCreateRequest(**payload, requires_active_membership=True)
    payload.update(operator_type="COOPERATIVE", cooperative_id=uuid4())
    assert OperatorCreateRequest(**payload, requires_active_membership=True).requires_active_membership


@pytest.mark.parametrize("enabled", [False, True])
def test_policy_change_alone_is_a_real_update(enabled):
    assert OperatorUpdateRequest(requires_active_membership=enabled).requires_active_membership is enabled
