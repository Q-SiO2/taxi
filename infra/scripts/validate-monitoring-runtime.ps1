[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

& (Join-Path $PSScriptRoot "validate-production-inputs.ps1") -IncludeMonitoring

$deployDirectory = (Resolve-Path (Join-Path $PSScriptRoot "..\deploy")).Path
$prometheusConfig = Join-Path $deployDirectory "prometheus.yaml"
$alertmanagerConfig = Join-Path $deployDirectory "alertmanager.yaml"
$alertRules = Join-Path $deployDirectory "prometheus-alerts.yaml"
$lokiConfig = Join-Path $deployDirectory "loki.yaml"
$alloyConfig = Join-Path $deployDirectory "alloy\config.alloy"
$grafanaDatasourceDirectory = Join-Path $deployDirectory "grafana\provisioning\datasources"
$grafanaProviderDirectory = Join-Path $deployDirectory "grafana\provisioning\dashboards"
$grafanaDashboardDirectory = Join-Path $deployDirectory "grafana\dashboards"
$monitoringTokenFile = (
    Resolve-Path -LiteralPath $env:TAXIMOBILE_MONITORING_TOKEN_FILE
).Path
$platformWebhookFile = (
    Resolve-Path -LiteralPath $env:TAXIMOBILE_PLATFORM_ALERT_WEBHOOK_URL_FILE
).Path
$dispatchWebhookFile = (
    Resolve-Path -LiteralPath $env:TAXIMOBILE_DISPATCH_ALERT_WEBHOOK_URL_FILE
).Path
$schedulingWebhookFile = (
    Resolve-Path -LiteralPath $env:TAXIMOBILE_SCHEDULING_ALERT_WEBHOOK_URL_FILE
).Path
$complianceWebhookFile = (
    Resolve-Path -LiteralPath $env:TAXIMOBILE_DRIVER_COMPLIANCE_ALERT_WEBHOOK_URL_FILE
).Path
$grafanaAdminPasswordFile = (
    Resolve-Path -LiteralPath $env:TAXIMOBILE_GRAFANA_ADMIN_PASSWORD_FILE
).Path

& docker compose `
    -f (Join-Path $deployDirectory "compose.production.yaml") `
    -f (Join-Path $deployDirectory "compose.monitoring.yaml") `
    config --quiet
if ($LASTEXITCODE -ne 0) {
    throw "The merged production monitoring Compose model is invalid."
}

& docker run --rm --entrypoint /bin/promtool `
    --volume "${prometheusConfig}:/etc/prometheus/prometheus.yaml:ro" `
    --volume "${alertRules}:/etc/prometheus/rules/taximobile-alerts.yaml:ro" `
    --volume "${monitoringTokenFile}:/run/secrets/taximobile_monitoring_token:ro" `
    $env:TAXIMOBILE_PROMETHEUS_IMAGE `
    check config /etc/prometheus/prometheus.yaml
if ($LASTEXITCODE -ne 0) {
    throw "Prometheus rejected the production configuration or alert rules."
}

& docker run --rm --entrypoint /bin/amtool `
    --volume "${alertmanagerConfig}:/etc/alertmanager/alertmanager.yaml:ro" `
    --volume "${platformWebhookFile}:/run/secrets/taximobile_platform_alert_webhook_url:ro" `
    --volume "${dispatchWebhookFile}:/run/secrets/taximobile_dispatch_alert_webhook_url:ro" `
    --volume "${schedulingWebhookFile}:/run/secrets/taximobile_scheduling_alert_webhook_url:ro" `
    --volume "${complianceWebhookFile}:/run/secrets/taximobile_driver_compliance_alert_webhook_url:ro" `
    $env:TAXIMOBILE_ALERTMANAGER_IMAGE `
    check-config /etc/alertmanager/alertmanager.yaml
if ($LASTEXITCODE -ne 0) {
    throw "Alertmanager rejected the production routing configuration."
}

& docker run --rm --entrypoint /usr/bin/loki `
    --volume "${lokiConfig}:/etc/loki/taximobile.yaml:ro" `
    $env:TAXIMOBILE_LOKI_IMAGE `
    "-config.file=/etc/loki/taximobile.yaml" `
    "-verify-config=true"
if ($LASTEXITCODE -ne 0) {
    throw "Loki rejected the production storage, ingestion, or retention configuration."
}

& docker run --rm --entrypoint /bin/alloy `
    --volume "${alloyConfig}:/etc/alloy/config.alloy:ro" `
    $env:TAXIMOBILE_ALLOY_IMAGE `
    validate /etc/alloy/config.alloy
if ($LASTEXITCODE -ne 0) {
    throw "Alloy rejected the production file-log collection pipeline."
}

$smokeId = [Guid]::NewGuid().ToString("N")
$grafanaContainer = "taximobile-grafana-validation-$smokeId"
$grafanaVolume = "taximobile-grafana-validation-$smokeId"
try {
    & docker volume create $grafanaVolume *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the disposable Grafana validation volume."
    }

    & docker run --detach `
        --name $grafanaContainer `
        --user "472:472" `
        --read-only `
        --tmpfs "/tmp:size=64m,mode=1777" `
        --tmpfs "/var/log/grafana:size=32m,mode=0750,uid=472,gid=472" `
        --cap-drop ALL `
        --security-opt "no-new-privileges:true" `
        --network none `
        --mount "type=volume,source=$grafanaVolume,target=/var/lib/grafana" `
        --volume "${grafanaDatasourceDirectory}:/etc/grafana/provisioning/datasources:ro" `
        --volume "${grafanaProviderDirectory}:/etc/grafana/provisioning/dashboards:ro" `
        --volume "${grafanaDashboardDirectory}:/etc/grafana/dashboards:ro" `
        --volume "${grafanaAdminPasswordFile}:/run/secrets/taximobile_grafana_admin_password:ro" `
        --env "GF_SECURITY_ADMIN_USER=taximobile-admin" `
        --env "GF_SECURITY_ADMIN_PASSWORD__FILE=/run/secrets/taximobile_grafana_admin_password" `
        --env "GF_AUTH_ANONYMOUS_ENABLED=false" `
        --env "GF_USERS_ALLOW_SIGN_UP=false" `
        --env "GF_AUTH_BASIC_PASSWORD_POLICY=true" `
        --env "GF_ANALYTICS_REPORTING_ENABLED=false" `
        --env "GF_ANALYTICS_CHECK_FOR_UPDATES=false" `
        --env "GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES=false" `
        --env "GF_UNIFIED_ALERTING_ENABLED=false" `
        --env "GF_ALERTING_ENABLED=false" `
        --env "GF_LOG_MODE=console" `
        --env "GF_LOG_LEVEL=info" `
        $env:TAXIMOBILE_GRAFANA_IMAGE *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "The hardened Grafana validation container did not start."
    }

    $grafanaReady = $false
    for ($attempt = 1; $attempt -le 30; $attempt += 1) {
        & docker exec $grafanaContainer /usr/bin/wget --spider -q `
            http://127.0.0.1:3000/api/health *> $null
        if ($LASTEXITCODE -eq 0) {
            $grafanaReady = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $grafanaReady) {
        & docker logs $grafanaContainer
        throw "Grafana did not become ready with the committed provisioning files."
    }

    $grafanaLogs = (& docker logs $grafanaContainer 2>&1) -join "`n"
    if ($grafanaLogs -match '(?i)failed to provision|provisioning.*error|failed to save dashboard') {
        Write-Output $grafanaLogs
        throw "Grafana reported a datasource or dashboard provisioning failure."
    }

    $grafanaDashboardJson = (
        & docker exec $grafanaContainer /bin/sh -c `
            'password="$(cat /run/secrets/taximobile_grafana_admin_password)"; printf "user = \"taximobile-admin:%s\"\n" "$password" | /usr/bin/curl --silent --show-error --fail --config - http://127.0.0.1:3000/api/dashboards/uid/taximobile-operations' `
            2>&1
    ) -join "`n"
    if ($LASTEXITCODE -ne 0) {
        throw "Grafana rejected authenticated access to the provisioned dashboard."
    }
    try {
        $grafanaDashboard = $grafanaDashboardJson | ConvertFrom-Json -Depth 100
    } catch {
        throw "Grafana returned an invalid dashboard API response."
    }
    if (
        $grafanaDashboard.dashboard.uid -ne "taximobile-operations" -or
        @($grafanaDashboard.dashboard.panels).Count -ne 13
    ) {
        throw "Grafana did not provision the reviewed 13-panel operations dashboard."
    }

    $grafanaLogDashboardJson = (
        & docker exec $grafanaContainer /bin/sh -c `
            'password="$(cat /run/secrets/taximobile_grafana_admin_password)"; printf "user = \"taximobile-admin:%s\"\n" "$password" | /usr/bin/curl --silent --show-error --fail --config - http://127.0.0.1:3000/api/dashboards/uid/taximobile-logs' `
            2>&1
    ) -join "`n"
    if ($LASTEXITCODE -ne 0) {
        throw "Grafana rejected authenticated access to the provisioned log dashboard."
    }
    try {
        $grafanaLogDashboard = $grafanaLogDashboardJson | ConvertFrom-Json -Depth 100
    } catch {
        throw "Grafana returned an invalid log-dashboard API response."
    }
    if (
        $grafanaLogDashboard.dashboard.uid -ne "taximobile-logs" -or
        @($grafanaLogDashboard.dashboard.panels).Count -ne 3
    ) {
        throw "Grafana did not provision the reviewed three-panel log dashboard."
    }
} finally {
    & docker rm --force $grafanaContainer *> $null
    & docker volume rm $grafanaVolume *> $null
}

$pipelineId = [Guid]::NewGuid().ToString("N")
$pipelineNetwork = "taximobile-log-validation-$pipelineId"
$lokiContainer = "taximobile-loki-validation-$pipelineId"
$alloyContainer = "taximobile-alloy-validation-$pipelineId"
$apiLogVolume = "taximobile-api-log-validation-$pipelineId"
$workerLogVolume = "taximobile-worker-log-validation-$pipelineId"
$lokiVolume = "taximobile-loki-validation-$pipelineId"
$alloyVolume = "taximobile-alloy-validation-$pipelineId"
try {
    & docker network create --internal $pipelineNetwork *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the disposable internal log-pipeline network."
    }
    foreach ($volume in @(
        $apiLogVolume,
        $workerLogVolume,
        $lokiVolume,
        $alloyVolume
    )) {
        & docker volume create $volume *> $null
        if ($LASTEXITCODE -ne 0) {
            throw "Could not create disposable log-pipeline state."
        }
    }

    foreach ($volume in @($apiLogVolume, $workerLogVolume)) {
        & docker run --rm `
            --mount "type=volume,source=$volume,target=/var/log/taximobile" `
            --entrypoint /bin/true `
            $env:TAXIMOBILE_API_IMAGE
        if ($LASTEXITCODE -ne 0) {
            throw "The application image could not initialize its UID/GID 2000 log volume."
        }
    }

    & docker run --detach `
        --name $lokiContainer `
        --entrypoint /usr/bin/loki `
        --user "10001:10001" `
        --read-only `
        --tmpfs "/tmp:size=64m,mode=1777" `
        --cap-drop ALL `
        --security-opt "no-new-privileges:true" `
        --network $pipelineNetwork `
        --network-alias loki `
        --mount "type=volume,source=$lokiVolume,target=/loki" `
        --volume "${lokiConfig}:/etc/loki/taximobile.yaml:ro" `
        $env:TAXIMOBILE_LOKI_IMAGE `
        "-config.file=/etc/loki/taximobile.yaml" *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "The hardened Loki validation container did not start."
    }

    $lokiReady = $false
    for ($attempt = 1; $attempt -le 30; $attempt += 1) {
        & docker run --rm `
            --network $pipelineNetwork `
            --entrypoint python `
            $env:TAXIMOBILE_API_IMAGE `
            -c 'import urllib.request; urllib.request.urlopen("http://loki:3100/ready", timeout=3).read()' `
            *> $null
        if ($LASTEXITCODE -eq 0) {
            $lokiReady = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $lokiReady) {
        & docker logs $lokiContainer
        throw "Loki did not satisfy its real HTTP readiness contract."
    }

    & docker run --detach `
        --name $alloyContainer `
        --entrypoint /bin/alloy `
        --user "473:473" `
        --group-add "2000" `
        --read-only `
        --tmpfs "/tmp:size=64m,mode=1777" `
        --cap-drop ALL `
        --security-opt "no-new-privileges:true" `
        --network $pipelineNetwork `
        --network-alias alloy `
        --mount "type=volume,source=$apiLogVolume,target=/var/log/taximobile-api,readonly" `
        --mount "type=volume,source=$workerLogVolume,target=/var/log/taximobile-worker,readonly" `
        --mount "type=volume,source=$alloyVolume,target=/var/lib/alloy/data" `
        --volume "${alloyConfig}:/etc/alloy/config.alloy:ro" `
        $env:TAXIMOBILE_ALLOY_IMAGE `
        run /etc/alloy/config.alloy `
        "--storage.path=/var/lib/alloy/data" `
        "--server.http.listen-addr=0.0.0.0:12345" `
        "--server.http.enable-pprof=false" `
        "--server.http.disable-support-bundle" `
        "--disable-reporting" *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "The hardened Alloy validation container did not start."
    }

    $alloyReady = $false
    for ($attempt = 1; $attempt -le 30; $attempt += 1) {
        & docker run --rm `
            --network $pipelineNetwork `
            --entrypoint python `
            $env:TAXIMOBILE_API_IMAGE `
            -c 'import urllib.request; urllib.request.urlopen("http://alloy:12345/-/ready", timeout=3).read()' `
            *> $null
        if ($LASTEXITCODE -eq 0) {
            $alloyReady = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $alloyReady) {
        & docker logs $alloyContainer
        throw "Alloy did not satisfy its real HTTP readiness contract."
    }

    & docker run --rm `
        --mount "type=volume,source=$apiLogVolume,target=/var/log/taximobile" `
        --entrypoint python `
        $env:TAXIMOBILE_API_IMAGE `
        -c 'from pathlib import Path; from taximobile_api.core.logging import configure_logging; p=Path("/var/log/taximobile/events.jsonl"); logger=configure_logging("INFO", log_file=p); logger.info("pipeline-api-safe-event"); [h.flush() for h in logger.handlers]; f=p.open("a", encoding="utf-8"); f.write("not-json\n"); f.write("{\"timestamp\":\"2026-09-06T08:00:00+00:00\",\"level\":\"INFO\",\"message\":\"" + "x"*17000 + "\"}\n"); f.close()' `
        *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "The API image could not write its structured validation fixture."
    }
    & docker run --rm `
        --mount "type=volume,source=$workerLogVolume,target=/var/log/taximobile" `
        --entrypoint python `
        $env:TAXIMOBILE_API_IMAGE `
        -c 'from pathlib import Path; from taximobile_api.core.logging import configure_logging; logger=configure_logging("INFO", log_file=Path("/var/log/taximobile/events.jsonl")); logger.error("pipeline-worker-safe-event", extra={"worker":"outbox"}); [h.flush() for h in logger.handlers]' `
        *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "The worker image could not write its structured validation fixture."
    }

    $ingestionVerified = $false
    for ($attempt = 1; $attempt -le 40; $attempt += 1) {
        $queryEvidence = (
            & docker run --rm `
                --network $pipelineNetwork `
                --entrypoint python `
                $env:TAXIMOBILE_API_IMAGE `
                -c 'import json,time,urllib.parse,urllib.request; now=time.time_ns(); q=urllib.parse.urlencode({"query":"{service=~\"api|worker\"}","start":str(now-3600_000_000_000),"end":str(now),"limit":"100"}); data=json.load(urllib.request.urlopen("http://loki:3100/loki/api/v1/query_range?"+q, timeout=5)); values=[line for stream in data["data"]["result"] for _,line in stream["values"]]; assert any("pipeline-api-safe-event" in line for line in values); assert any("pipeline-worker-safe-event" in line for line in values); assert all("not-json" not in line and len(line)<16384 for line in values); print(json.dumps({"streams":len(data["data"]["result"]),"events":len(values)}))' `
                2>$null
        ) -join "`n"
        if ($LASTEXITCODE -eq 0) {
            $ingestionVerified = $true
            Write-Output "Validated bounded Loki ingestion: $queryEvidence"
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $ingestionVerified) {
        & docker logs $alloyContainer
        & docker logs $lokiContainer
        throw "Role logs were not queryable or malformed/oversize lines leaked into Loki."
    }
} finally {
    & docker rm --force $alloyContainer $lokiContainer *> $null
    foreach ($volume in @(
        $apiLogVolume,
        $workerLogVolume,
        $lokiVolume,
        $alloyVolume
    )) {
        & docker volume rm $volume *> $null
    }
    & docker network rm $pipelineNetwork *> $null
}

Write-Output "TaxiMobile production monitoring inputs, Compose, rules, routing, dashboards, and bounded structured-log ingestion passed validation."
