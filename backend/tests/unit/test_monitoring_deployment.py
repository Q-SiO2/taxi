"""Mutation tests for the self-hosted production monitoring boundary."""

import json
from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[3]
VALIDATOR_PATH = ROOT / "infra" / "scripts" / "validate_monitoring_deployment.py"


def _validator():
    spec = spec_from_file_location("taximobile_monitoring_validator", VALIDATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _document(filename: str) -> dict:
    path = ROOT / "infra" / "deploy" / filename
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _grafana_document(*parts: str) -> dict:
    path = ROOT / "infra" / "deploy" / "grafana" / Path(*parts)
    if path.suffix == ".json":
        document = json.loads(path.read_text(encoding="utf-8"))
    else:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def test_committed_monitoring_deployment_contract_is_valid() -> None:
    _validator().validate_monitoring_deployment()


def test_every_scrape_uses_the_monitoring_token_secret() -> None:
    document = deepcopy(_document("prometheus.yaml"))
    document["scrape_configs"][0]["authorization"] = {
        "type": "Bearer",
        "credentials": "inline-secret",
    }

    with pytest.raises(ValueError, match="Docker secret"):
        _validator().validate_prometheus(document)


def test_prometheus_cannot_drop_log_pipeline_scrapes() -> None:
    document = deepcopy(_document("prometheus.yaml"))
    document["scrape_configs"] = [
        config
        for config in document["scrape_configs"]
        if config["job_name"] != "taximobile-alloy"
    ]

    with pytest.raises(ValueError, match="scrape exactly"):
        _validator().validate_prometheus(document)


def test_private_alert_label_defense_cannot_be_removed() -> None:
    document = deepcopy(_document("prometheus.yaml"))
    document["alerting"]["alert_relabel_configs"][0]["regex"] = "user_id|ride_id"

    with pytest.raises(ValueError, match="removal vocabulary changed"):
        _validator().validate_prometheus(document)


def test_every_fixed_owner_has_the_reviewed_receiver() -> None:
    document = deepcopy(_document("alertmanager.yaml"))
    document["route"]["routes"][2]["receiver"] = "platform-duty"

    with pytest.raises(ValueError, match="owner-to-receiver routing"):
        _validator().validate_alertmanager(document)


def test_alert_webhook_url_cannot_be_inlined() -> None:
    document = deepcopy(_document("alertmanager.yaml"))
    webhook = document["receivers"][0]["webhook_configs"][0]
    del webhook["url_file"]
    webhook["url"] = "https://private.invalid/example"

    with pytest.raises(ValueError, match="secret file"):
        _validator().validate_alertmanager(document)


def test_loki_retention_cannot_be_disabled_or_shortened() -> None:
    document = deepcopy(_document("loki.yaml"))
    document["compactor"]["retention_enabled"] = False
    with pytest.raises(ValueError, match="enforce the reviewed retention boundary"):
        _validator().validate_loki(document)

    document = deepcopy(_document("loki.yaml"))
    document["limits_config"]["retention_period"] = "24h"
    with pytest.raises(ValueError, match="retention limits changed"):
        _validator().validate_loki(document)


def test_loki_single_node_readiness_cannot_regain_cluster_delay() -> None:
    document = deepcopy(_document("loki.yaml"))
    document["ingester"]["lifecycler"]["min_ready_duration"] = "15s"

    with pytest.raises(ValueError, match="single-node readiness"):
        _validator().validate_loki(document)


def test_alloy_cannot_gain_host_or_docker_authority() -> None:
    configuration = (
        (ROOT / "infra" / "deploy" / "alloy" / "config.alloy")
        .read_text(encoding="utf-8")
        + '\n// forbidden mount hint: /var/run/docker.sock\n'
    )

    with pytest.raises(ValueError, match="must not gain Docker"):
        _validator().validate_alloy(configuration)


def test_alloy_cannot_promote_event_fields_to_index_labels() -> None:
    configuration = (
        (ROOT / "infra" / "deploy" / "alloy" / "config.alloy")
        .read_text(encoding="utf-8")
        + '\nloki.process "forbidden" { stage.labels { values = { ride_id = "" } } }\n'
    )

    with pytest.raises(ValueError, match="dynamic-label authority"):
        _validator().validate_alloy(configuration)


def test_scrape_network_cannot_be_made_externally_routable() -> None:
    document = deepcopy(_document("compose.monitoring.yaml"))
    document["networks"]["taximobile_monitoring"]["internal"] = False

    with pytest.raises(ValueError, match="Scrape traffic must be internal"):
        _validator().validate_overlay(document)


def test_prometheus_cannot_join_the_alert_delivery_egress_network() -> None:
    document = deepcopy(_document("compose.monitoring.yaml"))
    document["services"]["prometheus"]["networks"].append("taximobile_alert_egress")

    with pytest.raises(ValueError, match="Prometheus must use only"):
        _validator().validate_overlay(document)


def test_monitoring_operator_ports_cannot_bind_publicly() -> None:
    document = deepcopy(_document("compose.monitoring.yaml"))
    document["services"]["prometheus"]["ports"] = ["0.0.0.0:9090:9090"]

    with pytest.raises(ValueError, match="only to loopback"):
        _validator().validate_overlay(document)


def test_grafana_datasource_cannot_leave_the_internal_collector() -> None:
    datasource = deepcopy(
        _grafana_document("provisioning", "datasources", "prometheus.yaml")
    )
    datasource["datasources"][0]["url"] = "https://metrics.example.test"

    with pytest.raises(ValueError, match="internal TaxiMobile Prometheus"):
        _validator().validate_grafana(
            datasource,
            _grafana_document("provisioning", "datasources", "loki.yaml"),
            _grafana_document("provisioning", "dashboards", "taximobile.yaml"),
            _grafana_document("dashboards", "taximobile-operations.json"),
            _grafana_document("dashboards", "taximobile-logs.json"),
        )


def test_grafana_loki_datasource_cannot_leave_the_internal_store() -> None:
    loki_datasource = deepcopy(
        _grafana_document("provisioning", "datasources", "loki.yaml")
    )
    loki_datasource["datasources"][0]["url"] = "https://logs.example.test"

    with pytest.raises(ValueError, match="internal TaxiMobile Loki"):
        _validator().validate_grafana(
            _grafana_document("provisioning", "datasources", "prometheus.yaml"),
            loki_datasource,
            _grafana_document("provisioning", "dashboards", "taximobile.yaml"),
            _grafana_document("dashboards", "taximobile-operations.json"),
            _grafana_document("dashboards", "taximobile-logs.json"),
        )


def test_grafana_dashboard_rejects_private_identifier_labels() -> None:
    dashboard = deepcopy(
        _grafana_document("dashboards", "taximobile-operations.json")
    )
    dashboard["panels"][0]["targets"][0]["expr"] = (
        'min(up{job="taximobile-api",ride_id="synthetic"})'
    )

    with pytest.raises(ValueError, match="forbidden private labels"):
        _validator().validate_grafana(
            _grafana_document("provisioning", "datasources", "prometheus.yaml"),
            _grafana_document("provisioning", "datasources", "loki.yaml"),
            _grafana_document("provisioning", "dashboards", "taximobile.yaml"),
            dashboard,
            _grafana_document("dashboards", "taximobile-logs.json"),
        )


def test_grafana_dashboard_rejects_unreviewed_metrics() -> None:
    dashboard = deepcopy(
        _grafana_document("dashboards", "taximobile-operations.json")
    )
    panel = next(
        panel
        for panel in dashboard["panels"]
        if panel["title"] == "Unhandled server errors"
    )
    panel["targets"][0]["expr"] = "sum(taximobile_unbounded_business_value)"

    with pytest.raises(ValueError, match="metric vocabulary"):
        _validator().validate_grafana(
            _grafana_document("provisioning", "datasources", "prometheus.yaml"),
            _grafana_document("provisioning", "datasources", "loki.yaml"),
            _grafana_document("provisioning", "dashboards", "taximobile.yaml"),
            dashboard,
            _grafana_document("dashboards", "taximobile-logs.json"),
        )


def test_grafana_core_health_cannot_drop_log_pipeline_targets() -> None:
    dashboard = deepcopy(
        _grafana_document("dashboards", "taximobile-operations.json")
    )
    dashboard["panels"][0]["targets"][0]["expr"] = (
        'min(up{job=~"taximobile-api|taximobile-worker"})'
    )

    with pytest.raises(ValueError, match="must include API, worker, Loki, and Alloy"):
        _validator().validate_grafana(
            _grafana_document("provisioning", "datasources", "prometheus.yaml"),
            _grafana_document("provisioning", "datasources", "loki.yaml"),
            _grafana_document("provisioning", "dashboards", "taximobile.yaml"),
            dashboard,
            _grafana_document("dashboards", "taximobile-logs.json"),
        )


def test_grafana_dashboard_cannot_drop_a_required_panel() -> None:
    dashboard = deepcopy(
        _grafana_document("dashboards", "taximobile-operations.json")
    )
    dashboard["panels"].pop()

    with pytest.raises(ValueError, match="panel set"):
        _validator().validate_grafana(
            _grafana_document("provisioning", "datasources", "prometheus.yaml"),
            _grafana_document("provisioning", "datasources", "loki.yaml"),
            _grafana_document("provisioning", "dashboards", "taximobile.yaml"),
            dashboard,
            _grafana_document("dashboards", "taximobile-logs.json"),
        )


def test_grafana_log_dashboard_cannot_query_private_labels() -> None:
    dashboard = deepcopy(_grafana_document("dashboards", "taximobile-logs.json"))
    dashboard["panels"][0]["targets"][0]["expr"] = (
        'sum(count_over_time({ride_id="synthetic"}[5m]))'
    )

    with pytest.raises(ValueError, match="fixed service vocabulary"):
        _validator().validate_grafana(
            _grafana_document("provisioning", "datasources", "prometheus.yaml"),
            _grafana_document("provisioning", "datasources", "loki.yaml"),
            _grafana_document("provisioning", "dashboards", "taximobile.yaml"),
            _grafana_document("dashboards", "taximobile-operations.json"),
            dashboard,
        )


def test_grafana_cannot_join_alert_delivery_egress() -> None:
    document = deepcopy(_document("compose.monitoring.yaml"))
    document["services"]["grafana"]["networks"].append("taximobile_alert_egress")

    with pytest.raises(ValueError, match="Grafana must use only"):
        _validator().validate_overlay(document)


def test_grafana_cannot_enable_anonymous_access() -> None:
    document = deepcopy(_document("compose.monitoring.yaml"))
    document["services"]["grafana"]["environment"][
        "GF_AUTH_ANONYMOUS_ENABLED"
    ] = "true"

    with pytest.raises(ValueError, match="authentication"):
        _validator().validate_overlay(document)


@pytest.mark.parametrize("service_name", ["loki", "alloy"])
def test_log_pipeline_operator_ports_cannot_bind_publicly(service_name: str) -> None:
    document = deepcopy(_document("compose.monitoring.yaml"))
    container_port = 3100 if service_name == "loki" else 12345
    document["services"][service_name]["ports"] = [
        f"0.0.0.0:{container_port}:{container_port}"
    ]

    with pytest.raises(ValueError, match="only to loopback"):
        _validator().validate_overlay(document)


@pytest.mark.parametrize("service_name", ["loki", "alloy"])
def test_log_pipeline_cannot_gain_alert_egress(service_name: str) -> None:
    document = deepcopy(_document("compose.monitoring.yaml"))
    document["services"][service_name]["networks"].append(
        "taximobile_alert_egress"
    )

    with pytest.raises(ValueError, match=f"{service_name.capitalize()} must use only"):
        _validator().validate_overlay(document)


def test_alloy_log_mounts_must_stay_read_only_and_group_bounded() -> None:
    document = deepcopy(_document("compose.monitoring.yaml"))
    document["services"]["alloy"]["volumes"][1] = (
        "taximobile_api_logs:/var/log/taximobile-api:rw"
    )
    with pytest.raises(ValueError, match="read-only role logs"):
        _validator().validate_overlay(document)

    document = deepcopy(_document("compose.monitoring.yaml"))
    document["services"]["alloy"]["group_add"] = ["0"]
    with pytest.raises(ValueError, match="read-only TaxiMobile log group"):
        _validator().validate_overlay(document)


@pytest.mark.parametrize("service_name", ["loki", "alloy"])
def test_log_pipeline_native_healthchecks_cannot_drift(service_name: str) -> None:
    document = deepcopy(_document("compose.monitoring.yaml"))
    document["services"][service_name]["healthcheck"]["test"] = [
        "CMD",
        "/bin/false",
    ]

    with pytest.raises(ValueError, match="native configuration verification"):
        _validator().validate_overlay(document)
