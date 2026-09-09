[CmdletBinding()]
param(
    [Parameter()]
    [ValidateRange(10, 3600)]
    [int]$WaitTimeoutSeconds = 120,

    [Parameter()]
    [ValidateSet("none", "valhalla", "graphhopper")]
    [string]$RoutingProvider = "none",

    [Parameter()]
    [switch]$RunRoutingAcceptance,

    [Parameter()]
    [switch]$WithRouting
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_portable-common.ps1")

$infraRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$composeFile = Join-Path $infraRoot "compose.yaml"
$environmentFile = Join-Path $infraRoot ".env"

if (-not (Test-Path -LiteralPath $environmentFile -PathType Leaf)) {
    throw "Create infra/.env before starting the local stack: powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\new-local-env.ps1"
}

if ($WithRouting) {
    if ($PSBoundParameters.ContainsKey("RoutingProvider") -and $RoutingProvider -ne "none") {
        throw "Use either legacy -WithRouting or -RoutingProvider, not both."
    }
    $RoutingProvider = "valhalla"
}
if ($RunRoutingAcceptance -and $RoutingProvider -eq "none") {
    throw "RunRoutingAcceptance requires -RoutingProvider valhalla or graphhopper."
}

function Assert-ImmutableHttpsDownload {
    param(
        [Parameter(Mandatory)]
        [string]$Value,

        [Parameter(Mandatory)]
        [string]$Name
    )

    try {
        $uri = [Uri]$Value
    } catch {
        throw "$Name must be an absolute HTTPS URL."
    }
    if (-not $uri.IsAbsoluteUri -or $uri.Scheme -ne "https" -or -not $uri.Host -or
        $uri.UserInfo -or $uri.Query -or $uri.Fragment) {
        throw "$Name must be an absolute HTTPS URL without credentials, a query, or a fragment."
    }
    if ($uri.AbsolutePath -match '(?i)-latest\.') {
        throw "$Name must identify a dated immutable extract, not a mutable latest URL."
    }
}

$environment = Import-TaxiMobileEnvironment -Path $environmentFile
$composePrefix = @("compose", "--env-file", $environmentFile, "-f", $composeFile)
$composeArguments = @($composePrefix)
$routingInternalUrl = $null
$routingLoopbackUrl = $null
$routingHost = $null

$documentSettings = @(
    $environment["TAXIMOBILE_DRIVER_DOCUMENT_STORAGE_ROOT"],
    $environment["TAXIMOBILE_DRIVER_DOCUMENT_ENCRYPTION_KEY"],
    $environment["TAXIMOBILE_DRIVER_DOCUMENT_CLAMAV_HOST"]
)
$configuredDocumentSettings = @($documentSettings | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
if ($configuredDocumentSettings.Count -ne 0 -and $configuredDocumentSettings.Count -ne $documentSettings.Count) {
    throw "Driver-document root, encryption key, and ClamAV host must be configured together or all left empty."
}
if ($configuredDocumentSettings.Count -eq $documentSettings.Count) {
    $composeArguments += @("--profile", "driver-documents")
}

switch ($RoutingProvider) {
    "valhalla" {
        $tileUrl = Get-RequiredLocalValue -Values $environment -Name "VALHALLA_TILE_URL"
        Assert-ImmutableHttpsDownload -Value $tileUrl -Name "VALHALLA_TILE_URL"
        [Environment]::SetEnvironmentVariable("TAXIMOBILE_ROUTING_PROVIDER", "valhalla", "Process")
        [Environment]::SetEnvironmentVariable("TAXIMOBILE_ROUTING_BASE_URL", "http://valhalla:8002", "Process")
        $composeArguments += @("--profile", "routing-valhalla")
        $routingInternalUrl = "http://valhalla:8002"
        $routingLoopbackUrl = "http://127.0.0.1:8002"
        $routingHost = "valhalla"
    }
    "graphhopper" {
        $osmUrl = Get-RequiredLocalValue -Values $environment -Name "GRAPHHOPPER_OSM_URL"
        $osmSha256 = Get-RequiredLocalValue -Values $environment -Name "GRAPHHOPPER_OSM_SHA256"
        Assert-ImmutableHttpsDownload -Value $osmUrl -Name "GRAPHHOPPER_OSM_URL"
        if ($osmSha256 -cnotmatch '^[0-9a-f]{64}$') {
            throw "GRAPHHOPPER_OSM_SHA256 must be an exact lowercase SHA-256 digest."
        }
        [Environment]::SetEnvironmentVariable("TAXIMOBILE_ROUTING_PROVIDER", "graphhopper", "Process")
        [Environment]::SetEnvironmentVariable("TAXIMOBILE_ROUTING_BASE_URL", "http://graphhopper:8989", "Process")
        $composeArguments += @("--profile", "routing-graphhopper")
        $routingInternalUrl = "http://graphhopper:8989"
        $routingLoopbackUrl = "http://127.0.0.1:8002"
        $routingHost = "graphhopper"
    }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw @"
Docker Desktop is required for TaxiMobile's documented local PostGIS stack but
is not installed or is not available on PATH. Install and start Docker Desktop,
then run this script again. The script deliberately does not install or alter
system software.
"@
}

# `docker info` distinguishes a missing/stopped engine from a compose failure.
& docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop is installed but its engine is not running. Start Docker Desktop, then retry."
}

$composeArguments += @("up", "--build", "--detach", "--wait", "--wait-timeout", $WaitTimeoutSeconds)

& docker @composeArguments
if ($LASTEXITCODE -ne 0) {
    throw "TaxiMobile's local Docker Compose stack did not become healthy. Run 'docker compose --env-file .env -f compose.yaml logs' from infra/ for details."
}

$healthUrl = "http://127.0.0.1:8000/health"
$deadline = (Get-Date).AddSeconds($WaitTimeoutSeconds)
$health = $null
do {
    try {
        $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 5
        if ($null -ne $health) {
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
} while ((Get-Date) -lt $deadline)

if ($null -eq $health) {
    throw "Docker Compose reported healthy services but the TaxiMobile API did not answer $healthUrl within $WaitTimeoutSeconds seconds."
}

if ($RoutingProvider -eq "none") {
    Write-Output "TaxiMobile API is ready at $healthUrl"
    Write-Output "Routing was not requested. Use -RoutingProvider valhalla or graphhopper to build one selected service."
    Write-Output "For a USB-connected Android device, run: adb reverse tcp:8000 tcp:8000"
    exit 0
}

$routeRequest = if ($RoutingProvider -eq "valhalla") {
    @{
        locations = @(
            @{ lat = 33.5731; lon = -7.5898 },
            @{ lat = 33.5899; lon = -7.6039 }
        )
        costing = "auto"
        directions_options = @{ units = "kilometers"; language = "en-US" }
    } | ConvertTo-Json -Depth 4 -Compress
} else {
    @{
        profile = "car"
        points = @(
            @(-7.5898, 33.5731),
            @(-7.6039, 33.5899)
        )
        locale = "en"
        instructions = $true
        points_encoded = $false
        elevation = $false
    } | ConvertTo-Json -Depth 4 -Compress
}
$routeUrl = "$routingLoopbackUrl/route"
$routeReady = $false
do {
    try {
        $route = Invoke-RestMethod -Method Post -Uri $routeUrl -ContentType "application/json" -Body $routeRequest -TimeoutSec 15
        $routeReady = if ($RoutingProvider -eq "valhalla") {
            $null -ne $route.trip.summary
        } else {
            $null -ne $route.paths -and $route.paths.Count -gt 0
        }
        if ($routeReady) {
            break
        }
    } catch {
        Start-Sleep -Seconds 5
    }
} while ((Get-Date) -lt $deadline)

if (-not $routeReady) {
    throw "$RoutingProvider did not return the fixed Casablanca readiness route within $WaitTimeoutSeconds seconds. First-time Morocco graph generation can take longer; inspect only the selected routing service logs and retry with a larger timeout."
}

if ($RunRoutingAcceptance) {
    $acceptanceArguments = @($composePrefix) + @(
        "exec", "--no-TTY", "api", "python", "-m",
        "taximobile_api.operations.routing_acceptance",
        "--provider", $RoutingProvider,
        "--base-url", $routingInternalUrl,
        "--confirm-host", $routingHost,
        "--timeout-seconds", "15"
    )
    & docker @acceptanceArguments
    if ($LASTEXITCODE -ne 0) {
        throw "$RoutingProvider readiness passed but full Morocco route/narration acceptance failed. Do not promote this graph or catalog."
    }
}

Write-Output "TaxiMobile API is ready at $healthUrl"
Write-Output "$RoutingProvider returned the fixed Casablanca readiness route."
if ($RunRoutingAcceptance) {
    Write-Output "$RoutingProvider passed the full fixed-scenario Morocco routing acceptance gate."
}
Write-Output "For a USB-connected Android device, run: adb reverse tcp:8000 tcp:8000"
