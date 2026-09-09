"""Stable compatibility identifiers and reviewed control-plane allowlists.

The first national migration maps every pre-city TaxiMobile record to one
explicit Casablanca compatibility scope.  These UUIDs are migration data, not
secrets and not mutable deployment configuration.  Keeping them in one module
prevents transitional API code, seed tooling, and migrations from inventing
different meanings for legacy records.
"""

from uuid import UUID


LEGACY_MARKET_ID = UUID("10000000-0000-4000-8000-000000000001")
LEGACY_OPERATOR_ID = UUID("10000000-0000-4000-8000-000000000002")
LEGACY_CITY_ID = UUID("10000000-0000-4000-8000-000000000003")
LEGACY_SERVICE_AREA_VERSION_ID = UUID("10000000-0000-4000-8000-000000000004")
LEGACY_OPERATOR_ASSIGNMENT_ID = UUID("10000000-0000-4000-8000-000000000005")
LEGACY_CONFIGURATION_VERSION_ID = UUID("10000000-0000-4000-8000-000000000006")
LEGACY_DRIVER_REQUIREMENT_VERSION_ID = UUID("10000000-0000-4000-8000-000000000007")
LEGACY_DRIVER_PROFILE_REQUIREMENT_ITEM_ID = UUID("10000000-0000-4000-8000-000000000008")
LEGACY_ZERO_OPERATOR_FEE_POLICY_ID = UUID("10000000-0000-4000-8000-000000000009")

LEGACY_MARKET_CODE = "MA"
LEGACY_CITY_CODE = "casablanca"


# These gates are deliberately staged.  Configuration and operational evidence
# is required before a bounded PILOT can begin.  The pilot then produces the
# service/fairness evidence required for public ACTIVE service.  Keeping the
# stages separate avoids the circular and unsafe alternatives of requiring
# pilot evidence before a pilot exists or treating PILOT as public activation.
# Evidence values are bounded ticket/runbook references, never documents,
# secrets, participant identifiers, or free-form operational notes.
PILOT_ENTRY_CITY_READINESS_GATES = frozenset(
    {
        "LEGAL_AND_OPERATOR_OWNERSHIP",
        "SERVICE_AREA_AND_TIMEZONE",
        "DRIVER_AND_VEHICLE_REQUIREMENTS",
        "TARIFF_AND_OPERATOR_FEE",
        "MATCHING_AND_CANCELLATION",
        "PAYMENT_AND_RECONCILIATION",
        "SUPPORT_SAFETY_AND_RETENTION",
        "LOCALIZATION_AR_FR_EN",
        "MAP_ROUTING_COVERAGE",
        "SECURITY_MONITORING_AND_ROLLBACK",
    }
)

PUBLIC_ACTIVATION_CITY_READINESS_GATES = frozenset(
    {*PILOT_ENTRY_CITY_READINESS_GATES, "PILOT_SERVICE_AND_FAIRNESS"}
)

# This evidence is recorded after launch and is intentionally not a prerequisite
# for that same launch.  It remains visible so the national operator can close
# one rollout before approving another city plan.
POST_LAUNCH_CITY_EVIDENCE_GATES = frozenset({"POST_LAUNCH_REVIEW"})

ALL_CITY_READINESS_GATES = frozenset(
    {*PUBLIC_ACTIVATION_CITY_READINESS_GATES, *POST_LAUNCH_CITY_EVIDENCE_GATES}
)

# Compatibility name used by existing API response fields.  "Required" means
# ready for public activation; stage-specific fields expose the finer contract.
REQUIRED_CITY_READINESS_GATES = PUBLIC_ACTIVATION_CITY_READINESS_GATES
