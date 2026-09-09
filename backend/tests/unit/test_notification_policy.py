import ast
from pathlib import Path
import re

import pytest

from taximobile_api.core.notification_policy import (
    DeliveryChannel,
    DeliveryFallback,
    DeliveryUrgency,
    LIVE_EVENT_TYPES,
    OUTBOX_NOTIFICATION_POLICIES,
    DEAD_LETTER_OWNERS,
    PUSH_EVENT_TYPES,
    UnsupportedOutboxTopic,
    notification_policy_for_hint,
    notification_policy_for_topic,
)


EXPECTED_TOPICS = {
    "ride.offer.created",
    "ride.accepted",
    "ride.cancelled",
    "ride.matching.failed",
    "ride.coordination.message",
    "scheduled.offer.created",
    "scheduled.driver.committed",
    "scheduled.dispatch.started",
    "scheduled.fallback.matching",
    "scheduled.unfulfilled",
    "driver.credential.expiring",
    "driver.credential.expired",
    "driver.city_authorization.changed",
}


def test_every_outbox_delivery_topic_has_one_complete_closed_policy() -> None:
    assert set(OUTBOX_NOTIFICATION_POLICIES) == EXPECTED_TOPICS
    assert len({policy.hint_type for policy in OUTBOX_NOTIFICATION_POLICIES.values()}) == len(
        EXPECTED_TOPICS
    )
    for topic, policy in OUTBOX_NOTIFICATION_POLICIES.items():
        assert policy.topic == topic
        assert policy.max_delivery_age_seconds > 0
        assert policy.dead_letter_owner in DEAD_LETTER_OWNERS
        assert notification_policy_for_hint(policy.hint_type) is policy


def test_live_and_push_allowlists_are_derived_from_the_same_policy() -> None:
    assert "RIDE_COORDINATION_MESSAGE" in LIVE_EVENT_TYPES
    assert "RIDE_COORDINATION_MESSAGE" in PUSH_EVENT_TYPES
    assert "DRIVER_CREDENTIAL_EXPIRING" not in LIVE_EVENT_TYPES
    assert "DRIVER_CREDENTIAL_EXPIRING" in PUSH_EVENT_TYPES
    assert all(
        DeliveryChannel.LIVE in policy.channels
        for policy in OUTBOX_NOTIFICATION_POLICIES.values()
        if policy.hint_type in LIVE_EVENT_TYPES
    )


def test_ride_and_compliance_delivery_policy_have_distinct_urgency_and_fallback() -> None:
    ride = notification_policy_for_topic("ride.accepted")
    credential = notification_policy_for_topic("driver.credential.expiring")

    assert ride.urgency == DeliveryUrgency.IMMEDIATE
    assert ride.fallback == DeliveryFallback.AUTHORIZED_RIDE_RELOAD
    assert not ride.quiet_hours_allowed
    assert credential.urgency == DeliveryUrgency.INFORMATIONAL
    assert credential.fallback == DeliveryFallback.PERSISTENT_NOTIFICATION_INBOX
    assert credential.quiet_hours_allowed
    authorization = notification_policy_for_topic("driver.city_authorization.changed")
    assert authorization.urgency == DeliveryUrgency.IMMEDIATE
    assert authorization.fallback == DeliveryFallback.PERSISTENT_NOTIFICATION_INBOX
    assert not authorization.quiet_hours_allowed


def test_unclassified_topic_fails_closed_for_bounded_dead_letter_processing() -> None:
    with pytest.raises(UnsupportedOutboxTopic):
        notification_policy_for_topic("future.unreviewed.topic")


def test_every_literal_producer_topic_has_a_delivery_policy() -> None:
    source = Path(__file__).resolve().parents[2] / "src" / "taximobile_api"
    topics = set()
    for path in source.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "enqueue":
                for keyword in node.keywords:
                    if keyword.arg == "topic" and isinstance(keyword.value, ast.Constant):
                        topics.add(keyword.value.value)
    assert topics <= set(OUTBOX_NOTIFICATION_POLICIES)
    assert "scheduled.offer.created" in topics


def test_mobile_push_allowlist_matches_the_backend_policy_exactly() -> None:
    root = Path(__file__).resolve().parents[3]
    relay = root / "TaxiMobile/shared/src/commonMain/kotlin/org/example/taximobile/feature/notifications/PushRefreshHintRelay.kt"
    content = relay.read_text(encoding="utf-8")
    block = re.search(r"ALLOWED_EVENT_TYPES\s*=\s*setOf\((.*?)\)", content, re.S)
    assert block is not None
    mobile_types = set(re.findall(r'"([A-Z_]+)"', block.group(1)))
    assert mobile_types == PUSH_EVENT_TYPES
