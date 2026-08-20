[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$ApiBaseUrl,

    [Parameter(Mandatory)]
    [string]$WorkerBaseUrl,

    [Parameter(Mandatory)]
    [switch]$ConfirmAuthorizedTarget
)

$ErrorActionPreference = "Stop"

try {
    $target = [Uri]$ApiBaseUrl
} catch {
    throw "ApiBaseUrl must be an absolute HTTP or HTTPS URL."
}
if (-not $target.IsAbsoluteUri -or $target.Scheme -notin @("http", "https")) {
    throw "ApiBaseUrl must be an absolute HTTP or HTTPS URL."
}
if ($target.AbsolutePath -ne "/" -or $target.Query -or $target.Fragment) {
    throw "ApiBaseUrl must contain only the scheme and host (plus an optional port)."
}
if (-not $ConfirmAuthorizedTarget) {
    throw "Refusing network verification without -ConfirmAuthorizedTarget."
}

$isLoopback = $target.Host -eq "localhost"
$parsedAddress = $null
if ([System.Net.IPAddress]::TryParse($target.Host, [ref]$parsedAddress)) {
    $isLoopback = [System.Net.IPAddress]::IsLoopback($parsedAddress)
}
if (-not $isLoopback -and $target.Scheme -ne "https") {
    throw "Non-local deployment verification requires HTTPS."
}

try {
    $workerTarget = [Uri]$WorkerBaseUrl
} catch {
    throw "WorkerBaseUrl must be an absolute HTTP or HTTPS URL."
}
if (-not $workerTarget.IsAbsoluteUri -or $workerTarget.Scheme -notin @("http", "https")) {
    throw "WorkerBaseUrl must be an absolute HTTP or HTTPS URL."
}
if ($workerTarget.AbsolutePath -ne "/" -or $workerTarget.Query -or $workerTarget.Fragment) {
    throw "WorkerBaseUrl must contain only the scheme and host (plus an optional port)."
}
$workerIsLoopback = $workerTarget.Host -eq "localhost"
$parsedWorkerAddress = $null
if ([System.Net.IPAddress]::TryParse($workerTarget.Host, [ref]$parsedWorkerAddress)) {
    $workerIsLoopback = [System.Net.IPAddress]::IsLoopback($parsedWorkerAddress)
}
if (-not $workerIsLoopback -and $workerTarget.Scheme -ne "https") {
    throw "Non-local worker verification requires HTTPS."
}

$monitoringToken = $env:TAXIMOBILE_MONITORING_TOKEN
if ([string]::IsNullOrWhiteSpace($monitoringToken) -or $monitoringToken.Length -lt 32) {
    throw "Load the deployment's 32+ character TAXIMOBILE_MONITORING_TOKEN through the secret boundary."
}

$base = $target.AbsoluteUri.TrimEnd("/")
$workerBase = $workerTarget.AbsoluteUri.TrimEnd("/")
$health = Invoke-RestMethod -Uri "$base/health" -TimeoutSec 10 -MaximumRedirection 0
if ($health.status -ne "ok") {
    throw "The health endpoint did not report ok."
}
$ready = Invoke-RestMethod -Uri "$base/ready" -TimeoutSec 10 -MaximumRedirection 0
if ($ready.status -ne "ready") {
    throw "The readiness endpoint did not report ready."
}
$metadata = Invoke-RestMethod -Uri "$base/api/v1/meta" -TimeoutSec 10 -MaximumRedirection 0
if ($metadata.service -ne "taximobile-api" -or $metadata.version -ne "v1") {
    throw "The API metadata does not identify the expected TaxiMobile v1 service."
}
$workerHealth = Invoke-RestMethod -Uri "$workerBase/health" -TimeoutSec 10 -MaximumRedirection 0
if ($workerHealth.status -ne "ok" -or $workerHealth.service -ne "taximobile-worker") {
    throw "The worker health endpoint did not identify a healthy TaxiMobile worker."
}
$workerReady = Invoke-RestMethod -Uri "$workerBase/ready" -TimeoutSec 10 -MaximumRedirection 0
if ($workerReady.status -ne "ready" -or $workerReady.service -ne "taximobile-worker") {
    throw "The worker readiness endpoint did not report ready."
}
$metrics = Invoke-RestMethod `
    -Uri "$base/internal/metrics" `
    -Headers @{ Authorization = "Bearer $monitoringToken" } `
    -TimeoutSec 10 `
    -MaximumRedirection 0
if ($metrics -notmatch "taximobile_http_requests_total" -or $metrics -notmatch "taximobile_http_request_duration_seconds") {
    throw "The authenticated metrics endpoint did not expose the expected bounded metrics."
}
if ($metrics -notmatch '(?m)^taximobile_outbox_metrics_available 1$') {
    throw "The deployment could not read aggregate outbox metrics from its database."
}
foreach ($requiredOutboxMetric in @(
    "taximobile_outbox_pending_events",
    "taximobile_outbox_dead_letter_events",
    "taximobile_outbox_locked_events",
    "taximobile_outbox_oldest_pending_age_seconds"
)) {
    if ($metrics -notmatch "(?m)^$requiredOutboxMetric [0-9]+(?:\.[0-9]+)?$") {
        throw "The authenticated metrics endpoint did not expose $requiredOutboxMetric."
    }
}
$workerMetrics = Invoke-RestMethod `
    -Uri "$workerBase/internal/metrics" `
    -Headers @{ Authorization = "Bearer $monitoringToken" } `
    -TimeoutSec 10 `
    -MaximumRedirection 0
if ($workerMetrics -notmatch '(?m)^taximobile_outbox_metrics_available 1$') {
    throw "The worker could not read aggregate outbox metrics from its database."
}
foreach ($worker in @("matching", "outbox", "credentials")) {
    if ($workerMetrics -notmatch "(?m)^taximobile_worker_iterations_total\{worker=`"$worker`",outcome=`"success`"\} [1-9][0-9]*$") {
        throw "The authenticated metrics endpoint did not expose the $worker worker success counter."
    }
    if ($workerMetrics -notmatch "(?m)^taximobile_worker_iterations_total\{worker=`"$worker`",outcome=`"error`"\} [0-9]+$") {
        throw "The authenticated metrics endpoint did not expose the $worker worker error counter."
    }
    if ($workerMetrics -notmatch "(?m)^taximobile_worker_last_success_unixtime\{worker=`"$worker`"\} (?!0(?:\.0+)?$)[0-9]+(?:\.[0-9]+)?$") {
        throw "The authenticated metrics endpoint did not expose the $worker worker heartbeat."
    }
}

Write-Output "TaxiMobile deployment verification passed for the authorized target."
Write-Output "API/worker health, database readiness, API identity, HTTP/outbox metrics, and worker telemetry are available."
