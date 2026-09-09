"""Regression tests for the deployable Prometheus alert contract."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
VALIDATOR_PATH = ROOT / "infra" / "scripts" / "validate_prometheus_rules.py"
RULES_PATH = ROOT / "infra" / "deploy" / "prometheus-alerts.yaml"


def _validator():
    spec = spec_from_file_location("taximobile_prometheus_validator", VALIDATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _mutated_rules(tmp_path: Path, old: str, new: str) -> Path:
    content = RULES_PATH.read_text(encoding="utf-8")
    assert old in content
    path = tmp_path / "prometheus-alerts.yaml"
    path.write_text(content.replace(old, new, 1), encoding="utf-8")
    return path


def test_committed_prometheus_rules_pass_the_offline_contract() -> None:
    _validator().validate_rules(RULES_PATH)


def test_dead_letter_alert_must_preserve_operational_owner(tmp_path: Path) -> None:
    path = _mutated_rules(
        tmp_path,
        "max by (owner) (taximobile_outbox_owner_dead_letter_events) > 0",
        "max(taximobile_outbox_dead_letter_events) > 0",
    )

    with pytest.raises(ValueError, match="preserve the fixed operational owner"):
        _validator().validate_rules(path)


def test_dead_letter_alert_rejects_dynamic_private_dimensions(tmp_path: Path) -> None:
    path = _mutated_rules(
        tmp_path,
        "max by (owner) (taximobile_outbox_owner_dead_letter_events) > 0",
        'max by (owner) (taximobile_outbox_owner_dead_letter_events{user_id!=""}) > 0',
    )

    with pytest.raises(ValueError, match="forbidden dynamic dimension"):
        _validator().validate_rules(path)


def test_dead_letter_alert_annotation_names_the_response_owner(tmp_path: Path) -> None:
    path = _mutated_rules(
        tmp_path,
        "owned by {{ $labels.owner }}",
        "requiring operator attention",
    )

    with pytest.raises(ValueError, match="annotations must identify the owner"):
        _validator().validate_rules(path)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (
            "min(taximobile_database_metrics_available) < 1",
            "min(taximobile_database_metrics_available) < 0",
        ),
        (
            "max(taximobile_database_connection_utilization_ratio) > 0.8",
            "max(taximobile_database_connection_utilization_ratio) > 1",
        ),
        (
            "max(taximobile_database_waiting_locks) > 0",
            "max(taximobile_database_waiting_locks) > 100",
        ),
        (
            "max(increase(taximobile_database_deadlocks_total[5m])) > 0",
            "max(increase(taximobile_database_deadlocks_total[1h])) > 0",
        ),
        (
            "min(taximobile_database_pool_metrics_available) < 1",
            "min(taximobile_database_pool_metrics_available) < 0",
        ),
        (
            "max(taximobile_database_pool_overflow) > 0",
            "max(taximobile_database_pool_overflow) > 10",
        ),
        (
            "or vector(0)) > 0.1",
            "or vector(0)) > 1",
        ),
        (
            "sum(increase(taximobile_database_pool_checkout_timeouts_total[5m])) > 0",
            "sum(increase(taximobile_database_pool_checkout_timeouts_total[1h])) > 0",
        ),
        (
            'taximobile_legacy_admin_http_requests_total{outcome="served"}[5m]',
            'taximobile_legacy_admin_http_requests_total{outcome="blocked"}[5m]',
        ),
        (
            "min(taximobile_security_incident_metrics_available) < 1",
            "min(taximobile_security_incident_metrics_available) < 0",
        ),
        (
            'taximobile_security_incidents_open{incident_severity=~"SEV1|SEV2"}',
            'taximobile_security_incidents_open{market_id!=""}',
        ),
        (
            'taximobile_security_incidents_containment_overdue{incident_severity=~"SEV1|SEV2"}',
            'taximobile_security_incidents_containment_overdue{incident_severity="SEV4"}',
        ),
        (
            'taximobile_security_incidents_containment_overdue{incident_severity=~"SEV3|SEV4"}',
            'taximobile_security_incidents_containment_overdue{incident_severity="SEV1"}',
        ),
        (
            "(taximobile_security_incidents_postmortem_overdue) > 0",
            "(taximobile_security_incidents_postmortem_pending) > 0",
        ),
    ],
)
def test_reviewed_operational_alert_expressions_are_immutable(
    tmp_path: Path,
    old: str,
    new: str,
) -> None:
    path = _mutated_rules(tmp_path, old, new)

    with pytest.raises(ValueError, match="preserve its reviewed bounded expression"):
        _validator().validate_rules(path)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (
            'min by (job) (up{job=~"taximobile-(api|worker|loki|alloy)"}) < 1',
            'min by (job) (up{job=~"taximobile-(api|worker)"}) < 1',
        ),
        (
            'loki_process_dropped_lines_total{component_id="loki.process.taximobile"}',
            'loki_process_dropped_lines_total{ride_id!=""}',
        ),
        (
            'loki_write_dropped_entries_total{component_id="loki.write.taximobile"}',
            'loki_write_dropped_entries_total{component_id="other"}',
        ),
    ],
)
def test_log_pipeline_alert_expressions_are_immutable(
    tmp_path: Path,
    old: str,
    new: str,
) -> None:
    path = _mutated_rules(tmp_path, old, new)

    with pytest.raises(ValueError, match="preserve its reviewed bounded expression"):
        _validator().validate_rules(path)
