"""Validate the committed TaxiMobile alert-rule contract without network access."""

from pathlib import Path

import yaml


RULES_PATH = Path(__file__).resolve().parents[1] / "deploy" / "prometheus-alerts.yaml"
REQUIRED_ALERTS = {
    "TaxiMobileUnhandledErrors",
    "TaxiMobileHighServerErrorRate",
    "TaxiMobileHighP95Latency",
    "TaxiMobileOutboxMetricsUnavailable",
    "TaxiMobileOutboxDeadLetters",
    "TaxiMobileOutboxDeliveryStalled",
    "TaxiMobileWorkerErrors",
    "TaxiMobileWorkerMetricsMissing",
    "TaxiMobileWorkerStalled",
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
            if not isinstance(duration, str) or not duration:
                raise ValueError(f"{alert} must use a non-empty hold duration.")
            if not isinstance(labels, dict) or labels.get("severity") not in {"warning", "critical"}:
                raise ValueError(f"{alert} must declare a reviewed severity.")
            if not isinstance(annotations, dict) or not {
                "summary",
                "description",
            }.issubset(annotations):
                raise ValueError(f"{alert} must provide safe summary and description annotations.")
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
