"""Versioned metric definitions; changing semantics requires a new code/version."""

from dataclasses import dataclass


METRIC_DEFINITION_VERSION = "operations-analytics-v1"
MINIMUM_CELL_SIZE = 5
RETENTION_DAYS = 730
LATE_EVENT_POLICY = "RECOMPUTE_FROM_SOURCE_UNTIL_RETENTION"


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    code: str
    family: str
    title: str
    unit: str
    source: str
    purpose: str
    owner: str = "national-operations"


def _metric(
    code: str,
    family: str,
    title: str,
    *,
    unit: str = "count",
    source: str,
    purpose: str,
) -> MetricDefinition:
    return MetricDefinition(code, family, title, unit, source, purpose)


METRIC_DEFINITIONS = (
    _metric("RIDE_REQUESTED", "demand", "Ride requests", source="ride_events", purpose="Measure service demand."),
    _metric("RIDE_ACCEPTED", "fulfillment", "Accepted rides", source="ride_events", purpose="Measure requests reaching assignment."),
    _metric("DRIVER_EN_ROUTE", "fulfillment", "Drivers en route", source="ride_events", purpose="Measure assigned rides progressing toward pickup."),
    _metric("DRIVER_ARRIVED", "fulfillment", "Driver arrivals", source="ride_events", purpose="Measure pickup progression."),
    _metric("RIDE_STARTED", "fulfillment", "Started rides", source="ride_events", purpose="Measure rides reaching passenger pickup."),
    _metric("RIDE_COMPLETED", "fulfillment", "Completed rides", source="ride_events", purpose="Measure fulfilled transport."),
    _metric("RIDE_CANCELLED", "fulfillment", "Cancelled rides", source="ride_events", purpose="Measure controlled cancellation outcomes."),
    _metric("RIDE_UNMATCHED", "fulfillment", "Unmatched rides", source="ride_events", purpose="Measure requests exhausted without assignment."),
    _metric("RIDE_OFFERED", "offers", "Immediate offers", source="ride_offers", purpose="Measure dispatch attempts."),
    _metric("RIDE_OFFER_ACCEPTED", "offers", "Accepted immediate offers", source="ride_offers", purpose="Measure non-punitive offer outcomes."),
    _metric("RIDE_OFFER_DECLINED", "offers", "Declined immediate offers", source="ride_offers", purpose="Measure non-punitive offer outcomes."),
    _metric("RIDE_OFFER_EXPIRED", "offers", "Expired immediate offers", source="ride_offers", purpose="Measure offer timing reliability."),
    _metric("RIDE_OFFER_CANCELLED", "offers", "Cancelled immediate offers", source="ride_offers", purpose="Measure offers closed after another authoritative outcome."),
    _metric("MATCHING_FAIRNESS_SCORE", "fairness", "Matching fairness score", unit="average_score", source="ride_offers", purpose="Audit aggregate dispatch fairness inputs without driver-level trails."),
    _metric("DRIVER_WORK_DISTRIBUTION", "fairness", "Driver work distribution", unit="assignments_per_driver_and_gini", source="rides", purpose="Measure aggregate assignment distribution without punitive driver ranking or participant exports."),
    _metric("SCHEDULED_CREATED", "scheduling", "Scheduled requests", source="scheduled_booking_events", purpose="Measure future-booking demand."),
    _metric("SCHEDULED_OFFERING_STARTED", "scheduling", "Scheduled offering windows", source="scheduled_booking_events", purpose="Measure bookings entering advance offer distribution."),
    _metric("SCHEDULED_OFFER_CREATED", "scheduling", "Scheduled offers", source="scheduled_booking_events", purpose="Measure advance dispatch attempts."),
    _metric("SCHEDULED_OFFER_DECLINED", "scheduling", "Declined scheduled offers", source="scheduled_booking_events", purpose="Measure non-punitive scheduled-offer outcomes."),
    _metric("SCHEDULED_DRIVER_COMMITTED", "scheduling", "Scheduled commitments", source="scheduled_booking_events", purpose="Measure scheduled supply commitment."),
    _metric("SCHEDULED_HANDOFF_STARTED", "scheduling", "Scheduled dispatch handoffs", source="scheduled_booking_events", purpose="Measure bookings entering live dispatch handoff."),
    _metric("SCHEDULED_LIVE_RIDE_CREATED", "scheduling", "Scheduled handoffs", source="scheduled_booking_events", purpose="Measure bookings reaching live dispatch."),
    _metric("SCHEDULED_UNFULFILLED", "scheduling", "Unfulfilled scheduled bookings", source="scheduled_booking_events", purpose="Measure explicit scheduling failures."),
    _metric("SCHEDULED_CANCELLED", "scheduling", "Cancelled scheduled bookings", source="scheduled_booking_events", purpose="Measure scheduled cancellation outcomes."),
    _metric("DRIVER_APPLICATION_CREATED", "onboarding", "Driver applications started", source="driver_city_applications", purpose="Measure recruiting funnel entry."),
    _metric("DRIVER_APPLICATION_SUBMITTED", "onboarding", "Driver applications submitted", source="driver_city_applications", purpose="Measure recruiting funnel progression."),
    _metric("DRIVER_APPLICATION_DECIDED", "onboarding", "Driver application decisions", source="driver_application_decisions", purpose="Measure review volume and duration."),
    _metric("PAYMENT_COMPLETED", "financial", "Completed settlements", unit="money_and_count", source="payments", purpose="Reconcile settled passenger totals."),
    _metric("PAYMENT_REFUNDED", "financial", "Confirmed refunds", unit="money_and_count", source="payment_refunds", purpose="Reconcile operator-funded refunds."),
    _metric("FINANCIAL_PASSENGER_TOTAL", "financial", "Passenger total settled", unit="money_and_count", source="payments + driver_earnings", purpose="Reconcile passenger settlement totals to completed payments."),
    _metric("FINANCIAL_TRANSPORT_FARE", "financial", "Transport fare settled", unit="money_and_count", source="driver_earnings", purpose="Reconcile settled transport-fare components."),
    _metric("FINANCIAL_SCHEDULING_SURCHARGE", "financial", "Scheduling surcharge settled", unit="money_and_count", source="driver_earnings", purpose="Reconcile settled scheduling-surcharge components."),
    _metric("FINANCIAL_OPERATOR_FEE", "financial", "Operator service fee settled", unit="money_and_count", source="driver_earnings", purpose="Reconcile settled operator service fees."),
    _metric("FINANCIAL_OPERATOR_ALLOCATION", "financial", "Operator allocation settled", unit="money_and_count", source="driver_earnings", purpose="Reconcile complete settled operator allocations."),
    _metric("FINANCIAL_DRIVER_NET", "financial", "Driver net settled", unit="money_and_count", source="driver_earnings", purpose="Reconcile settled driver net amounts."),
    _metric("SUPPLY_AVAILABLE", "supply", "Available drivers", source="operational_supply_snapshots_hourly", purpose="Measure coarse city-wide supply without participant trails."),
    _metric("SUPPLY_ELIGIBLE", "supply", "Eligible drivers", source="operational_supply_snapshots_hourly", purpose="Measure coarse city-wide eligible supply without participant trails."),
    _metric("SUPPORT_TICKET_CREATED", "support", "Support cases", source="support_tickets", purpose="Plan category-level support capacity without case text."),
    _metric("SAFETY_REPORT_CREATED", "safety", "Safety reports", source="safety_reports", purpose="Plan restricted category-level safety response without report text."),
)

METRIC_DEFINITION_BY_CODE = {definition.code: definition for definition in METRIC_DEFINITIONS}
