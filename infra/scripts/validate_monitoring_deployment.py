"""Validate the self-hosted production monitoring contract without secrets or network access."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml


DEPLOY_DIR = Path(__file__).resolve().parents[1] / "deploy"
PROMETHEUS_PATH = DEPLOY_DIR / "prometheus.yaml"
ALERTMANAGER_PATH = DEPLOY_DIR / "alertmanager.yaml"
OVERLAY_PATH = DEPLOY_DIR / "compose.monitoring.yaml"
GRAFANA_DATASOURCE_PATH = (
    DEPLOY_DIR / "grafana" / "provisioning" / "datasources" / "prometheus.yaml"
)
GRAFANA_LOKI_DATASOURCE_PATH = (
    DEPLOY_DIR / "grafana" / "provisioning" / "datasources" / "loki.yaml"
)
GRAFANA_PROVIDER_PATH = (
    DEPLOY_DIR / "grafana" / "provisioning" / "dashboards" / "taximobile.yaml"
)
GRAFANA_DASHBOARD_PATH = (
    DEPLOY_DIR / "grafana" / "dashboards" / "taximobile-operations.json"
)
GRAFANA_LOG_DASHBOARD_PATH = (
    DEPLOY_DIR / "grafana" / "dashboards" / "taximobile-logs.json"
)
LOKI_PATH = DEPLOY_DIR / "loki.yaml"
ALLOY_PATH = DEPLOY_DIR / "alloy" / "config.alloy"
MONITORING_TOKEN_PATH = "/run/secrets/taximobile_monitoring_token"
GRAFANA_ADMIN_PASSWORD_PATH = "/run/secrets/taximobile_grafana_admin_password"
GRAFANA_DATASOURCE_UID = "taximobile-prometheus"
GRAFANA_LOKI_DATASOURCE_UID = "taximobile-loki"
OWNER_RECEIVERS = {
    "dispatch_operations": "dispatch-operations",
    "scheduling_operations": "scheduling-operations",
    "driver_compliance": "driver-compliance",
    "unclassified": "platform-duty",
}
RECEIVER_SECRET_PATHS = {
    "platform-duty": "/run/secrets/taximobile_platform_alert_webhook_url",
    "dispatch-operations": "/run/secrets/taximobile_dispatch_alert_webhook_url",
    "scheduling-operations": "/run/secrets/taximobile_scheduling_alert_webhook_url",
    "driver-compliance": "/run/secrets/taximobile_driver_compliance_alert_webhook_url",
}
FORBIDDEN_ALERT_LABELS = {
    "user_id",
    "driver_id",
    "passenger_id",
    "device_id",
    "ride_id",
    "resource_id",
    "authorization_id",
    "payload",
    "topic",
}
DASHBOARD_METRICS = {
    "up",
    "taximobile_http_requests_total",
    "taximobile_http_request_duration_seconds_bucket",
    "taximobile_unhandled_errors_total",
    "taximobile_legacy_admin_http_requests_total",
    "taximobile_worker_iterations_total",
    "taximobile_worker_items_processed_total",
    "taximobile_worker_last_success_unixtime",
    "taximobile_outbox_metrics_available",
    "taximobile_outbox_owner_pending_events",
    "taximobile_outbox_owner_dead_letter_events",
    "taximobile_outbox_owner_oldest_pending_age_seconds",
    "taximobile_database_metrics_available",
    "taximobile_database_connection_utilization_ratio",
    "taximobile_database_waiting_locks",
    "taximobile_database_deadlocks_total",
    "taximobile_database_pool_metrics_available",
    "taximobile_database_pool_checked_out",
    "taximobile_database_pool_overflow",
    "taximobile_database_pool_checkout_wait_seconds_bucket",
    "taximobile_database_pool_checkout_wait_seconds_count",
    "taximobile_database_pool_checkout_timeouts_total",
    "taximobile_security_incident_metrics_available",
    "taximobile_security_incidents_open",
    "taximobile_security_incidents_containment_overdue",
    "taximobile_security_incidents_postmortem_pending",
    "taximobile_security_incidents_postmortem_overdue",
}
DASHBOARD_LABELS = {
    "job",
    "status_class",
    "route",
    "le",
    "worker",
    "outcome",
    "owner",
    "error_type",
    "incident_severity",
}
EXPECTED_DASHBOARD_TITLES = {
    "Core scrape health",
    "HTTP 5xx ratio",
    "HTTP p95 latency",
    "Outbox visibility",
    "HTTP request rate by status class",
    "HTTP p95 latency by normalized route",
    "Worker time since success",
    "Worker errors",
    "Worker processing rate",
    "Pending outbox events by owner",
    "Oldest pending event by owner",
    "Dead letters by owner",
    "Unhandled server errors",
    "Legacy administration requests",
    "Database metrics visibility",
    "Database connection utilization",
    "Database waiting locks",
    "Database deadlocks",
    "Database pool visibility",
    "Database pool checked out",
    "Database pool overflow",
    "Database pool checkout p95",
    "Database pool checkout timeouts",
    "Security incident visibility",
    "Open security incidents",
    "Security incident deadlines",
}
EXPECTED_LOG_DASHBOARD_QUERIES = {
    'sum by (service) (count_over_time({service=~"api|worker"}[5m]))',
    'sum by (service) (count_over_time({service=~"api|worker"} | json | level=~"ERROR|CRITICAL" [5m]))',
    '{service=~"api|worker"} | json',
}


def _mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a mapping.")
    return value


def _sequence(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list.")
    return value


def _load(path: Path) -> dict[str, Any]:
    return _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), path.name)


def _load_json(path: Path) -> dict[str, Any]:
    return _mapping(json.loads(path.read_text(encoding="utf-8")), path.name)


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_prometheus(document: dict[str, Any]) -> None:
    if document.get("rule_files") != ["/etc/prometheus/rules/taximobile-alerts.yaml"]:
        raise ValueError("Prometheus must load only the reviewed TaxiMobile rule file.")

    alerting = _mapping(document.get("alerting"), "prometheus.alerting")
    managers = _sequence(alerting.get("alertmanagers"), "prometheus.alertmanagers")
    expected_manager = [{"static_configs": [{"targets": ["taximobile-alertmanager:9093"]}]}]
    if managers != expected_manager:
        raise ValueError("Prometheus must send alerts only to the internal Alertmanager target.")

    relabel_rules = _sequence(
        alerting.get("alert_relabel_configs"), "prometheus.alerting.alert_relabel_configs"
    )
    if len(relabel_rules) != 1:
        raise ValueError("Prometheus must have one defensive private-label removal rule.")
    relabel = _mapping(relabel_rules[0], "prometheus.alert_relabel_configs[0]")
    if relabel.get("action") != "labeldrop":
        raise ValueError("Prometheus must drop private alert labels before Alertmanager.")
    removed_labels = set(str(relabel.get("regex", "")).split("|"))
    if removed_labels != FORBIDDEN_ALERT_LABELS:
        raise ValueError("Prometheus private alert-label removal vocabulary changed.")

    scrape_configs = _sequence(document.get("scrape_configs"), "prometheus.scrape_configs")
    expected_application_targets = {
        "taximobile-api": ("taximobile-api-metrics:8000", "api"),
        "taximobile-worker": ("taximobile-worker-metrics:8001", "worker"),
    }
    expected_observability_targets = {
        "taximobile-loki": ("loki:3100", "log_store"),
        "taximobile-alloy": ("alloy:12345", "log_collector"),
    }
    expected_targets = expected_application_targets | expected_observability_targets
    if {config.get("job_name") for config in scrape_configs if isinstance(config, dict)} != set(
        expected_targets
    ):
        raise ValueError("Prometheus must scrape exactly the API and worker jobs.")
    for raw_config in scrape_configs:
        config = _mapping(raw_config, "prometheus.scrape_config")
        job_name = config["job_name"]
        target, process_role = expected_targets[job_name]
        if job_name in expected_application_targets:
            if config.get("metrics_path") != "/internal/metrics":
                raise ValueError(f"{job_name} must use the authenticated internal metrics path.")
            authorization = _mapping(config.get("authorization"), f"{job_name}.authorization")
            if authorization != {"type": "Bearer", "credentials_file": MONITORING_TOKEN_PATH}:
                raise ValueError(f"{job_name} must read its bearer credential from the Docker secret.")
        else:
            if config.get("metrics_path") != "/metrics" or "authorization" in config:
                raise ValueError(
                    f"{job_name} must expose only its internal component metrics path."
                )
        static_configs = _sequence(config.get("static_configs"), f"{job_name}.static_configs")
        expected_static = [{"targets": [target], "labels": {"process_role": process_role}}]
        if static_configs != expected_static:
            raise ValueError(f"{job_name} target or bounded labels changed.")


def validate_alertmanager(document: dict[str, Any]) -> None:
    route = _mapping(document.get("route"), "alertmanager.route")
    if route.get("receiver") != "platform-duty" or route.get("group_by") != [
        "alertname",
        "owner",
    ]:
        raise ValueError("Alertmanager root routing must retain alert name and owner.")
    child_routes = _sequence(route.get("routes"), "alertmanager.route.routes")
    actual_routes: dict[str, str] = {}
    for raw_route in child_routes:
        child = _mapping(raw_route, "alertmanager.route.routes[]")
        matchers = _sequence(child.get("matchers"), "alertmanager.route.matchers")
        if len(matchers) != 1 or not isinstance(matchers[0], str):
            raise ValueError("Each owner route must have one exact matcher.")
        matcher = matchers[0].replace(" ", "")
        prefix = 'owner="'
        if not matcher.startswith(prefix) or not matcher.endswith('"'):
            raise ValueError("Each owner route must match one exact owner value.")
        owner = matcher[len(prefix) : -1]
        if owner in actual_routes:
            raise ValueError(f"Duplicate Alertmanager owner route: {owner}")
        actual_routes[owner] = str(child.get("receiver"))
    if actual_routes != OWNER_RECEIVERS:
        raise ValueError("Alertmanager owner-to-receiver routing changed or is incomplete.")

    receivers = _sequence(document.get("receivers"), "alertmanager.receivers")
    actual_receivers: dict[str, str] = {}
    for raw_receiver in receivers:
        receiver = _mapping(raw_receiver, "alertmanager.receivers[]")
        name = str(receiver.get("name"))
        webhooks = _sequence(receiver.get("webhook_configs"), f"{name}.webhook_configs")
        if len(webhooks) != 1:
            raise ValueError(f"{name} must have exactly one bounded webhook receiver.")
        webhook = _mapping(webhooks[0], f"{name}.webhook_configs[0]")
        if webhook.get("send_resolved") is not True or webhook.get("max_alerts") != 20:
            raise ValueError(f"{name} must send resolutions and bound webhook batches.")
        if "url" in webhook or not isinstance(webhook.get("url_file"), str):
            raise ValueError(f"{name} webhook URL must come only from a secret file.")
        actual_receivers[name] = webhook["url_file"]
    if actual_receivers != RECEIVER_SECRET_PATHS:
        raise ValueError("Alertmanager receiver secret files changed or are incomplete.")


def validate_loki(document: dict[str, Any]) -> None:
    if set(document) != {
        "auth_enabled",
        "server",
        "common",
        "ingester",
        "schema_config",
        "storage_config",
        "limits_config",
        "compactor",
        "analytics",
    }:
        raise ValueError("Loki configuration surface changed unexpectedly.")
    if document.get("auth_enabled") is not False:
        raise ValueError("Loki must rely only on the isolated monitoring network.")
    if document.get("server") != {
        "http_listen_port": 3100,
        "grpc_listen_port": 9096,
        "log_level": "info",
    }:
        raise ValueError("Loki listener or log-level configuration changed.")
    common = _mapping(document.get("common"), "loki.common")
    if common != {
        "instance_addr": "127.0.0.1",
        "path_prefix": "/loki",
        "storage": {
            "filesystem": {
                "chunks_directory": "/loki/chunks",
                "rules_directory": "/loki/rules",
            }
        },
        "replication_factor": 1,
        "ring": {"kvstore": {"store": "inmemory"}},
    }:
        raise ValueError("Loki must remain a single-node filesystem deployment.")
    if document.get("ingester") != {"lifecycler": {"min_ready_duration": "0s"}}:
        raise ValueError("Loki single-node readiness must not retain a cluster rollout delay.")
    schemas = _sequence(
        _mapping(document.get("schema_config"), "loki.schema_config").get("configs"),
        "loki.schema_config.configs",
    )
    if len(schemas) != 1:
        raise ValueError("Loki must use one reviewed schema epoch.")
    schema = _mapping(schemas[0], "loki.schema_config.configs[0]")
    if (
        str(schema.get("from")) != "2024-01-01"
        or schema.get("store") != "tsdb"
        or schema.get("object_store") != "filesystem"
        or schema.get("schema") != "v13"
        or schema.get("index") != {"prefix": "taximobile_index_", "period": "24h"}
    ):
        raise ValueError("Loki must use the reviewed TSDB v13 filesystem schema.")
    if document.get("storage_config") != {
        "tsdb_shipper": {
            "active_index_directory": "/loki/index",
            "cache_location": "/loki/index_cache",
        }
    }:
        raise ValueError("Loki index state must remain inside its private volume.")
    if document.get("limits_config") != {
        "retention_period": "720h",
        "max_query_lookback": "720h",
        "ingestion_rate_mb": 4,
        "ingestion_burst_size_mb": 8,
        "max_line_size": 16384,
        "max_line_size_truncate": False,
        "reject_old_samples": True,
        "reject_old_samples_max_age": "720h",
        "allow_structured_metadata": False,
        "volume_enabled": False,
    }:
        raise ValueError("Loki ingestion, query, or retention limits changed.")
    if document.get("compactor") != {
        "working_directory": "/loki/compactor",
        "compaction_interval": "10m",
        "apply_retention_interval": "10m",
        "retention_enabled": True,
        "retention_delete_delay": "2h",
        "retention_delete_worker_count": 10,
        "delete_request_store": "filesystem",
    }:
        raise ValueError("Loki compactor must enforce the reviewed retention boundary.")
    if document.get("analytics") != {"reporting_enabled": False}:
        raise ValueError("Loki analytics reporting must remain disabled.")


def validate_alloy(configuration: str) -> None:
    required_fragments = {
        '"__path__" = "/var/log/taximobile-api/events.jsonl*"',
        '"__path__" = "/var/log/taximobile-worker/events.jsonl*"',
        '"service"  = "api"',
        '"service"  = "worker"',
        'longer_than         = "16KB"',
        "drop_malformed = true",
        'values = ["service"]',
        'url = "http://loki:3100/loki/api/v1/push"',
    }
    missing = sorted(fragment for fragment in required_fragments if fragment not in configuration)
    if missing:
        raise ValueError(f"Alloy log pipeline is missing reviewed boundaries: {missing}")
    if configuration.count("loki.source.file") != 2:
        raise ValueError("Alloy must tail exactly the API and worker file sources.")
    if configuration.count('loki.write "') != 1:
        raise ValueError("Alloy must write only to the internal Loki endpoint.")
    if any(
        forbidden in configuration
        for forbidden in (
            "docker.sock",
            "/var/lib/docker",
            "loki.source.docker",
            "loki.source.api",
            "basic_auth",
            "bearer_token",
            "stage.labels",
            "stage.structured_metadata",
            "import.http",
            "import.git",
        )
    ):
        raise ValueError("Alloy must not gain Docker, remote-config, or dynamic-label authority.")
    labels = set(re.findall(r'"([a-z_][a-z0-9_]*)"\s*=\s*"(?:api|worker)"', configuration))
    if labels != {"service"}:
        raise ValueError("Alloy may index only the fixed service label.")


def validate_grafana(
    datasource_document: dict[str, Any],
    loki_datasource_document: dict[str, Any],
    provider_document: dict[str, Any],
    dashboard_document: dict[str, Any],
    log_dashboard_document: dict[str, Any],
) -> None:
    expected_datasource = {
        "apiVersion": 1,
        "prune": True,
        "datasources": [
            {
                "name": "TaxiMobile Prometheus",
                "type": "prometheus",
                "uid": GRAFANA_DATASOURCE_UID,
                "orgId": 1,
                "access": "proxy",
                "url": "http://prometheus:9090",
                "isDefault": True,
                "editable": False,
                "version": 1,
                "jsonData": {
                    "httpMethod": "POST",
                    "prometheusType": "Prometheus",
                    "timeInterval": "15s",
                    "manageAlerts": False,
                },
            }
        ],
    }
    if datasource_document != expected_datasource:
        raise ValueError(
            "Grafana must use only the immutable internal TaxiMobile Prometheus datasource."
        )

    expected_loki_datasource = {
        "apiVersion": 1,
        "prune": True,
        "datasources": [
            {
                "name": "TaxiMobile Loki",
                "type": "loki",
                "uid": GRAFANA_LOKI_DATASOURCE_UID,
                "orgId": 1,
                "access": "proxy",
                "url": "http://loki:3100",
                "isDefault": False,
                "editable": False,
                "version": 1,
                "jsonData": {"maxLines": 1000, "timeout": 30},
            }
        ],
    }
    if loki_datasource_document != expected_loki_datasource:
        raise ValueError("Grafana must use only the immutable internal TaxiMobile Loki datasource.")

    expected_provider = {
        "apiVersion": 1,
        "providers": [
            {
                "name": "taximobile-operations",
                "orgId": 1,
                "folder": "TaxiMobile Operations",
                "folderUid": "taximobile-operations",
                "type": "file",
                "disableDeletion": True,
                "allowUiUpdates": False,
                "updateIntervalSeconds": 30,
                "options": {
                    "path": "/etc/grafana/dashboards",
                    "foldersFromFilesStructure": False,
                },
            }
        ],
    }
    if provider_document != expected_provider:
        raise ValueError("Grafana dashboard provisioning must remain immutable and file-backed.")

    if (
        dashboard_document.get("uid") != "taximobile-operations"
        or dashboard_document.get("title") != "TaxiMobile Operations"
        or dashboard_document.get("editable") is not False
        or dashboard_document.get("refresh") != "30s"
    ):
        raise ValueError("The TaxiMobile operations dashboard identity or immutable settings changed.")
    if dashboard_document.get("links") != [] or _mapping(
        dashboard_document.get("templating"), "grafana.dashboard.templating"
    ).get("list") != []:
        raise ValueError("The operations dashboard must not contain external links or variables.")

    panels = _sequence(dashboard_document.get("panels"), "grafana.dashboard.panels")
    titles: set[str] = set()
    panel_ids: set[int] = set()
    metrics: set[str] = set()
    labels: set[str] = set()
    for raw_panel in panels:
        panel = _mapping(raw_panel, "grafana.dashboard.panels[]")
        title = panel.get("title")
        panel_id = panel.get("id")
        if not isinstance(title, str) or not isinstance(panel_id, int):
            raise ValueError("Every Grafana panel must have a stable title and integer ID.")
        if title in titles or panel_id in panel_ids:
            raise ValueError("Grafana panel titles and IDs must be unique.")
        titles.add(title)
        panel_ids.add(panel_id)
        if panel.get("datasource") != {
            "type": "prometheus",
            "uid": GRAFANA_DATASOURCE_UID,
        }:
            raise ValueError(f"Grafana panel {title!r} must use the provisioned datasource UID.")
        targets = _sequence(panel.get("targets"), f"grafana.panel[{title}].targets")
        if not targets:
            raise ValueError(f"Grafana panel {title!r} must have at least one reviewed query.")
        for raw_target in targets:
            target = _mapping(raw_target, f"grafana.panel[{title}].targets[]")
            expression = target.get("expr")
            legend = target.get("legendFormat", "")
            if not isinstance(expression, str) or not expression.strip():
                raise ValueError(f"Grafana panel {title!r} has an empty Prometheus query.")
            if not isinstance(legend, str):
                raise ValueError(f"Grafana panel {title!r} has a non-string legend.")
            metrics.update(re.findall(r"\b(?:taximobile_[a-z0-9_]+|up)\b", expression))
            for selector in re.findall(r"\{([^{}]*)\}", expression):
                labels.update(
                    re.findall(r"\b([a-z_][a-z0-9_]*)\s*(?:!?=~?)", selector)
                )
            for grouping in re.findall(r"\b(?:by|without)\s*\(([^()]*)\)", expression):
                labels.update(
                    label.strip() for label in grouping.split(",") if label.strip()
                )
            labels.update(re.findall(r"\{\{([a-z_][a-z0-9_]*)\}\}", legend))
            sensitive = FORBIDDEN_ALERT_LABELS.intersection(
                set(re.findall(r"\b[a-z_][a-z0-9_]*\b", f"{expression} {legend}"))
            )
            if sensitive:
                raise ValueError(
                    f"Grafana panel {title!r} references forbidden private labels: "
                    f"{sorted(sensitive)}"
                )
        if title == "Core scrape health" and {
            target.get("expr") for target in targets if isinstance(target, dict)
        } != {'min(up{job=~"taximobile-(api|worker|loki|alloy)"})'}:
            raise ValueError(
                "Core scrape health must include API, worker, Loki, and Alloy."
            )

    if titles != EXPECTED_DASHBOARD_TITLES:
        raise ValueError("The required TaxiMobile operational panel set changed or is incomplete.")
    if metrics != DASHBOARD_METRICS:
        raise ValueError("Grafana dashboard metric vocabulary changed or is incomplete.")
    unknown_labels = labels - DASHBOARD_LABELS
    if unknown_labels:
        raise ValueError(f"Grafana dashboard uses unreviewed labels: {sorted(unknown_labels)}")

    if (
        log_dashboard_document.get("uid") != "taximobile-logs"
        or log_dashboard_document.get("title") != "TaxiMobile Logs"
        or log_dashboard_document.get("editable") is not False
        or log_dashboard_document.get("refresh") != "30s"
        or log_dashboard_document.get("links") != []
        or _mapping(
            log_dashboard_document.get("templating"), "grafana.logs.templating"
        ).get("list")
        != []
    ):
        raise ValueError("The TaxiMobile log dashboard identity or immutable settings changed.")
    log_panels = _sequence(log_dashboard_document.get("panels"), "grafana.logs.panels")
    if {panel.get("title") for panel in log_panels if isinstance(panel, dict)} != {
        "Structured log volume by service",
        "Error logs by service",
        "Recent structured events",
    }:
        raise ValueError("The required TaxiMobile log panel set changed or is incomplete.")
    log_queries: set[str] = set()
    for raw_panel in log_panels:
        panel = _mapping(raw_panel, "grafana.logs.panels[]")
        if panel.get("datasource") != {
            "type": "loki",
            "uid": GRAFANA_LOKI_DATASOURCE_UID,
        }:
            raise ValueError("Every log panel must use the internal Loki datasource UID.")
        for raw_target in _sequence(panel.get("targets"), "grafana.logs.targets"):
            target = _mapping(raw_target, "grafana.logs.targets[]")
            expression = target.get("expr")
            if not isinstance(expression, str):
                raise ValueError("Every log panel must contain one reviewed LogQL query.")
            log_queries.add(expression)
            selectors = re.findall(r"\{([^{}]+)\}", expression)
            if any(
                not re.fullmatch(r'service=~"api\|worker"', selector)
                for selector in selectors
            ):
                raise ValueError("LogQL selectors may use only the fixed service vocabulary.")
    if log_queries != EXPECTED_LOG_DASHBOARD_QUERIES:
        raise ValueError("Grafana log-dashboard query vocabulary changed or is incomplete.")


def _require_hardening(
    name: str,
    service: dict[str, Any],
    image_variable: str,
    expected_user: str = "65534:65534",
) -> None:
    image = service.get("image")
    if not isinstance(image, str) or f"${{{image_variable}:?" not in image:
        raise ValueError(f"{name} must require its immutable image input.")
    if service.get("pull_policy") != "always" or service.get("read_only") is not True:
        raise ValueError(f"{name} must pull and use a read-only root filesystem.")
    if service.get("user") != expected_user:
        raise ValueError(f"{name} must run as the fixed unprivileged user.")
    if "ALL" not in _sequence(service.get("cap_drop"), f"{name}.cap_drop"):
        raise ValueError(f"{name} must drop all capabilities.")
    if "no-new-privileges:true" not in _sequence(
        service.get("security_opt"), f"{name}.security_opt"
    ):
        raise ValueError(f"{name} must disable privilege escalation.")
    ports = _sequence(service.get("ports"), f"{name}.ports")
    if len(ports) != 1 or not str(ports[0]).startswith("127.0.0.1:"):
        raise ValueError(f"{name} operator port must bind only to loopback.")


def validate_overlay(document: dict[str, Any]) -> None:
    services = _mapping(document.get("services"), "monitoring.services")
    if set(services) != {
        "api",
        "worker",
        "prometheus",
        "alertmanager",
        "grafana",
        "loki",
        "alloy",
    }:
        raise ValueError("Monitoring overlay services changed unexpectedly.")
    prometheus = _mapping(services["prometheus"], "monitoring.prometheus")
    alertmanager = _mapping(services["alertmanager"], "monitoring.alertmanager")
    grafana = _mapping(services["grafana"], "monitoring.grafana")
    loki = _mapping(services["loki"], "monitoring.loki")
    alloy = _mapping(services["alloy"], "monitoring.alloy")
    _require_hardening("prometheus", prometheus, "TAXIMOBILE_PROMETHEUS_IMAGE")
    _require_hardening("alertmanager", alertmanager, "TAXIMOBILE_ALERTMANAGER_IMAGE")
    _require_hardening(
        "grafana", grafana, "TAXIMOBILE_GRAFANA_IMAGE", expected_user="472:472"
    )
    _require_hardening("loki", loki, "TAXIMOBILE_LOKI_IMAGE", expected_user="10001:10001")
    _require_hardening("alloy", alloy, "TAXIMOBILE_ALLOY_IMAGE", expected_user="473:473")
    if prometheus.get("networks") != ["taximobile_monitoring"]:
        raise ValueError("Prometheus must use only the internal monitoring network.")
    if grafana.get("networks") != ["taximobile_monitoring"]:
        raise ValueError("Grafana must use only the internal monitoring network.")
    if loki.get("networks") != ["taximobile_monitoring"]:
        raise ValueError("Loki must use only the internal monitoring network.")
    if alloy.get("networks") != ["taximobile_monitoring"]:
        raise ValueError("Alloy must use only the internal monitoring network.")
    alert_networks = _mapping(alertmanager.get("networks"), "alertmanager.networks")
    if set(alert_networks) != {"taximobile_monitoring", "taximobile_alert_egress"}:
        raise ValueError(
            "Alertmanager must use only the monitoring and dedicated alert-egress networks."
        )
    if alert_networks["taximobile_alert_egress"] != {}:
        raise ValueError("Alertmanager alert egress must not add aliases or network privileges.")
    networks = _mapping(document.get("networks"), "monitoring.networks")
    if networks != {
        "taximobile_monitoring": {"internal": True},
        "taximobile_alert_egress": {},
    }:
        raise ValueError(
            "Scrape traffic must be internal and only Alertmanager may have dedicated egress."
        )

    api_network = _mapping(
        _mapping(services["api"], "monitoring.api").get("networks"), "monitoring.api.networks"
    )
    worker_network = _mapping(
        _mapping(services["worker"], "monitoring.worker").get("networks"),
        "monitoring.worker.networks",
    )
    expected_aliases = {
        "api": (api_network, "taximobile-api-metrics"),
        "worker": (worker_network, "taximobile-worker-metrics"),
    }
    for name, (network, alias) in expected_aliases.items():
        if "default" not in network:
            raise ValueError(f"{name} must retain its application dependency network.")
        monitoring = _mapping(network.get("taximobile_monitoring"), f"{name}.monitoring")
        if monitoring.get("aliases") != [alias]:
            raise ValueError(f"{name} must expose only its fixed internal metrics alias.")

    grafana_environment = _mapping(grafana.get("environment"), "grafana.environment")
    expected_grafana_environment = {
        "GF_SECURITY_ADMIN_USER": "taximobile-admin",
        "GF_SECURITY_ADMIN_PASSWORD__FILE": GRAFANA_ADMIN_PASSWORD_PATH,
        "GF_AUTH_ANONYMOUS_ENABLED": "false",
        "GF_USERS_ALLOW_SIGN_UP": "false",
        "GF_AUTH_BASIC_PASSWORD_POLICY": "true",
        "GF_ANALYTICS_REPORTING_ENABLED": "false",
        "GF_ANALYTICS_CHECK_FOR_UPDATES": "false",
        "GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES": "false",
        "GF_UNIFIED_ALERTING_ENABLED": "false",
        "GF_ALERTING_ENABLED": "false",
        "GF_LOG_MODE": "console",
        "GF_LOG_LEVEL": "info",
    }
    if grafana_environment != expected_grafana_environment:
        raise ValueError("Grafana authentication, telemetry, or alerting boundary changed.")
    expected_grafana_volumes = {
        "./grafana/provisioning/datasources:/etc/grafana/provisioning/datasources:ro",
        "./grafana/provisioning/dashboards:/etc/grafana/provisioning/dashboards:ro",
        "./grafana/dashboards:/etc/grafana/dashboards:ro",
        "taximobile_grafana_data:/var/lib/grafana",
    }
    if set(_sequence(grafana.get("volumes"), "grafana.volumes")) != expected_grafana_volumes:
        raise ValueError("Grafana must mount only reviewed provisioning and persistent state.")
    if grafana.get("secrets") != ["taximobile_grafana_admin_password"]:
        raise ValueError("Grafana administrator credentials must come only from its Docker secret.")
    if grafana.get("depends_on") != {
        "prometheus": {"condition": "service_healthy"},
        "loki": {"condition": "service_healthy"},
    }:
        raise ValueError("Grafana must wait for its internal Prometheus and Loki datasources.")

    if loki.get("volumes") != [
        "./loki.yaml:/etc/loki/taximobile.yaml:ro",
        "taximobile_loki_data:/loki",
    ]:
        raise ValueError("Loki must mount only reviewed configuration and private state.")
    if loki.get("command") != ["-config.file=/etc/loki/taximobile.yaml"] or _mapping(
        loki.get("healthcheck"), "loki.healthcheck"
    ).get("test") != [
        "CMD",
        "/usr/bin/loki",
        "-config.file=/etc/loki/taximobile.yaml",
        "-verify-config=true",
    ]:
        raise ValueError("Loki must use its native configuration verification healthcheck.")
    if alloy.get("group_add") != ["2000"]:
        raise ValueError("Alloy must receive only the read-only TaxiMobile log group.")
    if alloy.get("volumes") != [
        "./alloy/config.alloy:/etc/alloy/config.alloy:ro",
        "taximobile_api_logs:/var/log/taximobile-api:ro",
        "taximobile_worker_logs:/var/log/taximobile-worker:ro",
        "taximobile_alloy_data:/var/lib/alloy/data",
    ]:
        raise ValueError("Alloy must mount only config, read-only role logs, and position state.")
    if alloy.get("command") != [
        "run",
        "/etc/alloy/config.alloy",
        "--storage.path=/var/lib/alloy/data",
        "--server.http.listen-addr=0.0.0.0:12345",
        "--server.http.enable-pprof=false",
        "--server.http.disable-support-bundle",
        "--disable-reporting",
    ] or _mapping(alloy.get("healthcheck"), "alloy.healthcheck").get("test") != [
        "CMD",
        "/bin/alloy",
        "validate",
        "/etc/alloy/config.alloy",
    ]:
        raise ValueError("Alloy must use its native configuration verification healthcheck.")
    if alloy.get("depends_on") != {"loki": {"condition": "service_healthy"}}:
        raise ValueError("Alloy must wait for the internal Loki store.")

    secrets = _mapping(document.get("secrets"), "monitoring.secrets")
    expected_secret_names = {
        "taximobile_monitoring_token",
        "taximobile_platform_alert_webhook_url",
        "taximobile_dispatch_alert_webhook_url",
        "taximobile_scheduling_alert_webhook_url",
        "taximobile_driver_compliance_alert_webhook_url",
        "taximobile_grafana_admin_password",
    }
    if set(secrets) != expected_secret_names:
        raise ValueError("Monitoring secret-file inputs changed or are incomplete.")
    if secrets["taximobile_grafana_admin_password"] != {
        "file": "${TAXIMOBILE_GRAFANA_ADMIN_PASSWORD_FILE:?Set the Grafana administrator password secret file path}"
    }:
        raise ValueError("Grafana administrator secret source changed.")

    volumes = _mapping(document.get("volumes"), "monitoring.volumes")
    if set(volumes) != {
        "taximobile_prometheus_data",
        "taximobile_alertmanager_data",
        "taximobile_grafana_data",
        "taximobile_loki_data",
        "taximobile_alloy_data",
    }:
        raise ValueError("Monitoring persistent volumes changed or are incomplete.")


def validate_monitoring_deployment() -> None:
    validate_prometheus(_load(PROMETHEUS_PATH))
    validate_alertmanager(_load(ALERTMANAGER_PATH))
    validate_loki(_load(LOKI_PATH))
    validate_alloy(_load_text(ALLOY_PATH))
    validate_grafana(
        _load(GRAFANA_DATASOURCE_PATH),
        _load(GRAFANA_LOKI_DATASOURCE_PATH),
        _load(GRAFANA_PROVIDER_PATH),
        _load_json(GRAFANA_DASHBOARD_PATH),
        _load_json(GRAFANA_LOG_DASHBOARD_PATH),
    )
    validate_overlay(_load(OVERLAY_PATH))


if __name__ == "__main__":
    validate_monitoring_deployment()
    print(
        "Validated TaxiMobile Prometheus, Alertmanager, Loki, Alloy, Grafana dashboards, "
        "and monitoring Compose contracts."
    )
