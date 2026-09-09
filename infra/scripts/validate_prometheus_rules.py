"""Validate the committed TaxiMobile alert-rule contract without network access."""

from pathlib import Path

import yaml


RULES_PATH = Path(__file__).resolve().parents[1] / "deploy" / "prometheus-alerts.yaml"
REQUIRED_ALERTS = {
    "TaxiMobileUnhandledErrors",
    "TaxiMobileHighServerErrorRate",
    "TaxiMobileHighP95Latency",
    "TaxiMobileLegacyAdminRouteServed",
    "TaxiMobileSecurityIncidentMetricsUnavailable",
    "TaxiMobileHighSeveritySecurityIncidentOpen",
    "TaxiMobileCriticalSecurityContainmentOverdue",
    "TaxiMobileSecurityContainmentOverdue",
    "TaxiMobileSecurityPostmortemOverdue",
    "TaxiMobileOutboxMetricsUnavailable",
    "TaxiMobileDatabaseMetricsUnavailable",
    "TaxiMobileDatabaseConnectionUtilizationHigh",
    "TaxiMobileDatabaseLockWaiters",
    "TaxiMobileDatabaseDeadlocks",
    "TaxiMobileDatabasePoolMetricsUnavailable",
    "TaxiMobileDatabasePoolOverflow",
    "TaxiMobileDatabasePoolCheckoutWaitHigh",
    "TaxiMobileDatabasePoolCheckoutTimeouts",
    "TaxiMobileOutboxDeadLetters",
    "TaxiMobileOutboxDeliveryStalled",
    "TaxiMobileWorkerErrors",
    "TaxiMobileWorkerMetricsMissing",
    "TaxiMobileWorkerStalled",
    "TaxiMobileScrapeTargetDown",
    "TaxiMobileLogCollectorDroppedLines",
    "TaxiMobileLogDeliveryFailures",
}
REQUIRED_WORKERS = {
    "matching",
    "outbox",
    "credentials",
    "scheduling",
    "analytics",
    "case_alerts",
    "case_retention",
    "driver_document_retention",
}
EXPECTED_OPERATIONAL_EXPRESSIONS = {
    "TaxiMobileLegacyAdminRouteServed": (
        "sum(increase(taximobile_legacy_admin_http_requests_total"
        '{outcome="served"}[5m])) > 0'
    ),
    "TaxiMobileSecurityIncidentMetricsUnavailable": (
        "absent(taximobile_security_incident_metrics_available) or "
        "min(taximobile_security_incident_metrics_available) < 1"
    ),
    "TaxiMobileHighSeveritySecurityIncidentOpen": (
        "max by (incident_severity) (taximobile_security_incidents_open"
        '{incident_severity=~"SEV1|SEV2"}) > 0'
    ),
    "TaxiMobileCriticalSecurityContainmentOverdue": (
        "max by (incident_severity) (taximobile_security_incidents_containment_overdue"
        '{incident_severity=~"SEV1|SEV2"}) > 0'
    ),
    "TaxiMobileSecurityContainmentOverdue": (
        "max by (incident_severity) (taximobile_security_incidents_containment_overdue"
        '{incident_severity=~"SEV3|SEV4"}) > 0'
    ),
    "TaxiMobileSecurityPostmortemOverdue": (
        "max by (incident_severity) "
        "(taximobile_security_incidents_postmortem_overdue) > 0"
    ),
    "TaxiMobileDatabaseMetricsUnavailable": (
        "absent(taximobile_database_metrics_available) or "
        "min(taximobile_database_metrics_available) < 1"
    ),
    "TaxiMobileDatabaseConnectionUtilizationHigh": (
        "max(taximobile_database_connection_utilization_ratio) > 0.8"
    ),
    "TaxiMobileDatabaseLockWaiters": (
        "max(taximobile_database_waiting_locks) > 0"
    ),
    "TaxiMobileDatabaseDeadlocks": (
        "max(increase(taximobile_database_deadlocks_total[5m])) > 0"
    ),
    "TaxiMobileDatabasePoolMetricsUnavailable": (
        "absent(taximobile_database_pool_metrics_available) or "
        "min(taximobile_database_pool_metrics_available) < 1"
    ),
    "TaxiMobileDatabasePoolOverflow": (
        "max(taximobile_database_pool_overflow) > 0"
    ),
    "TaxiMobileDatabasePoolCheckoutWaitHigh": (
        "((histogram_quantile(0.95, sum by (le) "
        "(rate(taximobile_database_pool_checkout_wait_seconds_bucket[5m]))) "
        "and on() (sum(rate(taximobile_database_pool_checkout_wait_seconds_count[5m])) > 0)) "
        "or vector(0)) > 0.1"
    ),
    "TaxiMobileDatabasePoolCheckoutTimeouts": (
        "sum(increase(taximobile_database_pool_checkout_timeouts_total[5m])) > 0"
    ),
    "TaxiMobileOutboxDeliveryStalled": (
        "max(taximobile_outbox_owner_oldest_pending_age_seconds) > 300"
    ),
    "TaxiMobileScrapeTargetDown": (
        'min by (job) (up{job=~"taximobile-(api|worker|loki|alloy)"}) < 1'
    ),
    "TaxiMobileLogCollectorDroppedLines": (
        'sum(increase(loki_process_dropped_lines_total{component_id="loki.process.taximobile"}'
        "[5m])) > 0"
    ),
    "TaxiMobileLogDeliveryFailures": (
        'sum(increase(loki_write_dropped_entries_total{component_id="loki.write.taximobile"}'
        "[5m])) > 0 or sum(increase(loki_write_batch_retries_total"
        '{component_id="loki.write.taximobile"}[5m])) > 3'
    ),
}


def validate_rules(path: Path = RULES_PATH) -> None:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("groups"), list):
        raise ValueError("Prometheus rules must contain a groups list.")

    alerts: set[str] = set()
    for group in document["groups"]:
        if not isinstance(group, dict) or not isinstance(group.get("rules"), list):
            raise ValueError("Every Prometheus group must contain a rules list.")
        for rule in group["rules"]:
            if not isinstance(rule, dict):
                raise ValueError("Every Prometheus rule must be an object.")
            alert = rule.get("alert")
            expression = rule.get("expr")
            duration = rule.get("for")
            labels = rule.get("labels")
            annotations = rule.get("annotations")
            if not isinstance(alert, str) or not alert.startswith("TaxiMobile"):
                raise ValueError("Every alert must have a TaxiMobile-prefixed name.")
            if alert in alerts:
                raise ValueError(f"Duplicate alert name: {alert}")
            if not isinstance(expression, str) or not expression.strip():
                raise ValueError(f"{alert} must contain a PromQL expression.")
            if alert == "TaxiMobileWorkerMetricsMissing":
                missing_workers = {
                    worker
                    for worker in REQUIRED_WORKERS
                    if f'worker="{worker}"' not in expression
                }
                if missing_workers:
                    raise ValueError(
                        "TaxiMobileWorkerMetricsMissing must cover every fixed worker; "
                        f"missing={sorted(missing_workers)}"
                    )
            expected_expression = EXPECTED_OPERATIONAL_EXPRESSIONS.get(alert)
            if (
                expected_expression is not None
                and " ".join(expression.split()) != expected_expression
            ):
                raise ValueError(f"{alert} must preserve its reviewed bounded expression.")
            if alert == "TaxiMobileOutboxDeadLetters":
                if (
                    "taximobile_outbox_owner_dead_letter_events" not in expression
                    or "by (owner)" not in expression
                ):
                    raise ValueError(
                        "TaxiMobileOutboxDeadLetters must preserve the fixed operational owner."
                    )
                forbidden_dimensions = {
                    "topic",
                    "resource_id",
                    "user_id",
                    "authorization_id",
                    "payload",
                }
                present_dimensions = {
                    dimension
                    for dimension in forbidden_dimensions
                    if dimension in expression
                }
                if present_dimensions:
                    raise ValueError(
                        "TaxiMobileOutboxDeadLetters contains a forbidden dynamic dimension; "
                        f"present={sorted(present_dimensions)}"
                    )
            if not isinstance(duration, str) or not duration:
                raise ValueError(f"{alert} must use a non-empty hold duration.")
            if not isinstance(labels, dict) or labels.get("severity") not in {"warning", "critical"}:
                raise ValueError(f"{alert} must declare a reviewed severity.")
            if not isinstance(annotations, dict) or not {
                "summary",
                "description",
            }.issubset(annotations):
                raise ValueError(f"{alert} must provide safe summary and description annotations.")
            if alert == "TaxiMobileOutboxDeadLetters":
                annotation_text = " ".join(str(value) for value in annotations.values())
                if "$labels.owner" not in annotation_text:
                    raise ValueError(
                        "TaxiMobileOutboxDeadLetters annotations must identify the owner."
                    )
            alerts.add(alert)

    missing = REQUIRED_ALERTS - alerts
    unexpected = alerts - REQUIRED_ALERTS
    if missing or unexpected:
        raise ValueError(
            f"Alert contract mismatch; missing={sorted(missing)}, unexpected={sorted(unexpected)}"
        )


if __name__ == "__main__":
    validate_rules()
    print(f"Validated {len(REQUIRED_ALERTS)} TaxiMobile Prometheus alert rules.")
