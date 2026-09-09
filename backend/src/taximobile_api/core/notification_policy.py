"""Closed delivery policy for every transactional-outbox notification topic.

The persistent database record remains authoritative.  This registry controls
only non-authoritative live/push refresh hints and deliberately contains no user,
ride, message, or provider data.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DeliveryChannel(StrEnum):
    LIVE = "LIVE"
    PUSH = "PUSH"


class DeliveryUrgency(StrEnum):
    IMMEDIATE = "IMMEDIATE"
    INFORMATIONAL = "INFORMATIONAL"


class DeliveryFallback(StrEnum):
    AUTHORIZED_RIDE_RELOAD = "AUTHORIZED_RIDE_RELOAD"
    PERSISTENT_NOTIFICATION_INBOX = "PERSISTENT_NOTIFICATION_INBOX"


DEAD_LETTER_OWNERS = frozenset(
    {
        "dispatch_operations",
        "scheduling_operations",
        "driver_compliance",
    }
)


@dataclass(frozen=True, slots=True)
class NotificationDeliveryPolicy:
    topic: str
    hint_type: str
    channels: frozenset[DeliveryChannel]
    urgency: DeliveryUrgency
    max_delivery_age_seconds: int
    fallback: DeliveryFallback
    quiet_hours_allowed: bool
    dead_letter_owner: str

    def __post_init__(self) -> None:
        if self.max_delivery_age_seconds <= 0:
            raise ValueError("Notification delivery age must be positive.")
        if not self.channels:
            raise ValueError("Notification delivery must have at least one channel.")
        if self.dead_letter_owner not in DEAD_LETTER_OWNERS:
            raise ValueError("Notification delivery owner must use the closed operational vocabulary.")


_RIDE_CHANNELS = frozenset({DeliveryChannel.LIVE, DeliveryChannel.PUSH})
_PUSH_ONLY = frozenset({DeliveryChannel.PUSH})


OUTBOX_NOTIFICATION_POLICIES: dict[str, NotificationDeliveryPolicy] = {
    policy.topic: policy
    for policy in (
        NotificationDeliveryPolicy(
            topic="ride.offer.created",
            hint_type="RIDE_OFFER_AVAILABLE",
            channels=_RIDE_CHANNELS,
            urgency=DeliveryUrgency.IMMEDIATE,
            max_delivery_age_seconds=300,
            fallback=DeliveryFallback.AUTHORIZED_RIDE_RELOAD,
            quiet_hours_allowed=False,
            dead_letter_owner="dispatch_operations",
        ),
        NotificationDeliveryPolicy(
            topic="ride.accepted",
            hint_type="DRIVER_ASSIGNED",
            channels=_RIDE_CHANNELS,
            urgency=DeliveryUrgency.IMMEDIATE,
            max_delivery_age_seconds=900,
            fallback=DeliveryFallback.AUTHORIZED_RIDE_RELOAD,
            quiet_hours_allowed=False,
            dead_letter_owner="dispatch_operations",
        ),
        NotificationDeliveryPolicy(
            topic="ride.cancelled",
            hint_type="RIDE_CANCELLED",
            channels=_RIDE_CHANNELS,
            urgency=DeliveryUrgency.IMMEDIATE,
            max_delivery_age_seconds=7_200,
            fallback=DeliveryFallback.AUTHORIZED_RIDE_RELOAD,
            quiet_hours_allowed=False,
            dead_letter_owner="dispatch_operations",
        ),
        NotificationDeliveryPolicy(
            topic="ride.matching.failed",
            hint_type="RIDE_UNMATCHED",
            channels=_RIDE_CHANNELS,
            urgency=DeliveryUrgency.IMMEDIATE,
            max_delivery_age_seconds=900,
            fallback=DeliveryFallback.AUTHORIZED_RIDE_RELOAD,
            quiet_hours_allowed=False,
            dead_letter_owner="dispatch_operations",
        ),
        NotificationDeliveryPolicy(
            topic="ride.coordination.message",
            hint_type="RIDE_COORDINATION_MESSAGE",
            channels=_RIDE_CHANNELS,
            urgency=DeliveryUrgency.IMMEDIATE,
            max_delivery_age_seconds=300,
            fallback=DeliveryFallback.AUTHORIZED_RIDE_RELOAD,
            quiet_hours_allowed=False,
            dead_letter_owner="dispatch_operations",
        ),
        NotificationDeliveryPolicy(
            topic="scheduled.offer.created",
            hint_type="SCHEDULED_OFFER",
            channels=_PUSH_ONLY,
            urgency=DeliveryUrgency.IMMEDIATE,
            max_delivery_age_seconds=7_200,
            fallback=DeliveryFallback.PERSISTENT_NOTIFICATION_INBOX,
            quiet_hours_allowed=False,
            dead_letter_owner="scheduling_operations",
        ),
        NotificationDeliveryPolicy(
            topic="scheduled.driver.committed",
            hint_type="SCHEDULED_DRIVER_COMMITTED",
            channels=_PUSH_ONLY,
            urgency=DeliveryUrgency.INFORMATIONAL,
            max_delivery_age_seconds=604_800,
            fallback=DeliveryFallback.PERSISTENT_NOTIFICATION_INBOX,
            quiet_hours_allowed=True,
            dead_letter_owner="scheduling_operations",
        ),
        NotificationDeliveryPolicy(
            topic="scheduled.dispatch.started",
            hint_type="SCHEDULED_DISPATCH_STARTED",
            channels=_PUSH_ONLY,
            urgency=DeliveryUrgency.IMMEDIATE,
            max_delivery_age_seconds=7_200,
            fallback=DeliveryFallback.PERSISTENT_NOTIFICATION_INBOX,
            quiet_hours_allowed=False,
            dead_letter_owner="scheduling_operations",
        ),
        NotificationDeliveryPolicy(
            topic="scheduled.fallback.matching",
            hint_type="SCHEDULED_FALLBACK_MATCHING",
            channels=_PUSH_ONLY,
            urgency=DeliveryUrgency.IMMEDIATE,
            max_delivery_age_seconds=7_200,
            fallback=DeliveryFallback.PERSISTENT_NOTIFICATION_INBOX,
            quiet_hours_allowed=False,
            dead_letter_owner="scheduling_operations",
        ),
        NotificationDeliveryPolicy(
            topic="scheduled.unfulfilled",
            hint_type="SCHEDULED_UNFULFILLED",
            channels=_PUSH_ONLY,
            urgency=DeliveryUrgency.IMMEDIATE,
            max_delivery_age_seconds=86_400,
            fallback=DeliveryFallback.PERSISTENT_NOTIFICATION_INBOX,
            quiet_hours_allowed=False,
            dead_letter_owner="scheduling_operations",
        ),
        NotificationDeliveryPolicy(
            topic="driver.city_authorization.changed",
            hint_type="DRIVER_CITY_AUTHORIZATION_CHANGED",
            channels=_PUSH_ONLY,
            urgency=DeliveryUrgency.IMMEDIATE,
            max_delivery_age_seconds=604_800,
            fallback=DeliveryFallback.PERSISTENT_NOTIFICATION_INBOX,
            quiet_hours_allowed=False,
            dead_letter_owner="driver_compliance",
        ),
        NotificationDeliveryPolicy(
            topic="driver.credential.expiring",
            hint_type="DRIVER_CREDENTIAL_EXPIRING",
            channels=_PUSH_ONLY,
            urgency=DeliveryUrgency.INFORMATIONAL,
            max_delivery_age_seconds=604_800,
            fallback=DeliveryFallback.PERSISTENT_NOTIFICATION_INBOX,
            quiet_hours_allowed=True,
            dead_letter_owner="driver_compliance",
        ),
        NotificationDeliveryPolicy(
            topic="driver.credential.expired",
            hint_type="DRIVER_CREDENTIAL_EXPIRED",
            channels=_PUSH_ONLY,
            urgency=DeliveryUrgency.INFORMATIONAL,
            max_delivery_age_seconds=604_800,
            fallback=DeliveryFallback.PERSISTENT_NOTIFICATION_INBOX,
            quiet_hours_allowed=True,
            dead_letter_owner="driver_compliance",
        ),
    )
}


class UnsupportedOutboxTopic(ValueError):
    """Unknown topics must dead-letter visibly instead of disappearing as success."""


def notification_policy_for_topic(topic: str) -> NotificationDeliveryPolicy:
    try:
        return OUTBOX_NOTIFICATION_POLICIES[topic]
    except KeyError as error:
        raise UnsupportedOutboxTopic(
            "Outbox topic has no approved notification delivery policy."
        ) from error


LIVE_EVENT_TYPES = frozenset(
    policy.hint_type
    for policy in OUTBOX_NOTIFICATION_POLICIES.values()
    if DeliveryChannel.LIVE in policy.channels
)


PUSH_EVENT_TYPES = frozenset(
    policy.hint_type
    for policy in OUTBOX_NOTIFICATION_POLICIES.values()
    if DeliveryChannel.PUSH in policy.channels
)


def notification_policy_for_hint(hint_type: str) -> NotificationDeliveryPolicy:
    matches = [
        policy
        for policy in OUTBOX_NOTIFICATION_POLICIES.values()
        if policy.hint_type == hint_type
    ]
    if len(matches) != 1:
        raise ValueError("Notification hint has no unique approved delivery policy.")
    return matches[0]
