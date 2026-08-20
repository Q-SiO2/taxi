[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$required = @(
    "TAXIMOBILE_API_IMAGE",
    "TAXIMOBILE_DATABASE_URL",
    "TAXIMOBILE_JWT_SECRET",
    "TAXIMOBILE_MONITORING_TOKEN",
    "TAXIMOBILE_ALLOWED_HOSTS",
    "TAXIMOBILE_ROUTING_PROVIDER",
    "TAXIMOBILE_ROUTING_BASE_URL",
    "TAXIMOBILE_FIREBASE_PROJECT_ID",
    "TAXIMOBILE_TRUSTED_PROXY_CIDRS"
)
foreach ($name in $required) {
    if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($name))) {
        throw "$name must be supplied through the deployment configuration or secret boundary."
    }
}

$image = [Environment]::GetEnvironmentVariable("TAXIMOBILE_API_IMAGE")
if ($image -notmatch '@sha256:[0-9a-fA-F]{64}$') {
    throw "TAXIMOBILE_API_IMAGE must end with a full immutable @sha256 digest."
}

$databaseUrl = [Environment]::GetEnvironmentVariable("TAXIMOBILE_DATABASE_URL")
if ($databaseUrl -notmatch '^postgresql\+asyncpg://') {
    throw "TAXIMOBILE_DATABASE_URL must use the postgresql+asyncpg scheme."
}
if ($databaseUrl -match '@(localhost|127\.|\[::1\])') {
    throw "Production PostgreSQL/PostGIS must not use a loopback host."
}

$jwtSecret = [Environment]::GetEnvironmentVariable("TAXIMOBILE_JWT_SECRET")
$monitoringToken = [Environment]::GetEnvironmentVariable("TAXIMOBILE_MONITORING_TOKEN")
if ($jwtSecret.Length -lt 32 -or $monitoringToken.Length -lt 32) {
    throw "JWT and monitoring secrets must each contain at least 32 characters."
}
if ($jwtSecret -eq $monitoringToken) {
    throw "JWT and monitoring credentials must be independent secrets."
}

$allowedHosts = [Environment]::GetEnvironmentVariable("TAXIMOBILE_ALLOWED_HOSTS")
$allowedHostValues = @(
    $allowedHosts.Split(",") |
        ForEach-Object { $_.Trim() } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
)
$exactHostPattern = '^(?=.{1,253}$)[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*$'
$invalidAllowedHosts = @(
    $allowedHostValues |
        Where-Object { $_.Contains("*") -or $_ -notmatch $exactHostPattern }
)
if ($allowedHostValues.Count -eq 0 -or $invalidAllowedHosts.Count -gt 0) {
    throw "Production host allowlists must contain only exact DNS or IPv4 host names without wildcards, schemes, ports, or paths."
}
$corsOrigins = [Environment]::GetEnvironmentVariable("TAXIMOBILE_CORS_ORIGINS")
if (-not [string]::IsNullOrWhiteSpace($corsOrigins)) {
    foreach ($originValue in $corsOrigins.Split(",")) {
        $origin = $originValue.Trim()
        $parsedOrigin = $null
        if (
            [string]::IsNullOrWhiteSpace($origin) -or
            $origin.Contains("*") -or
            $origin.EndsWith("/") -or
            -not [Uri]::TryCreate($origin, [UriKind]::Absolute, [ref]$parsedOrigin) -or
            $parsedOrigin.Scheme -ne "https" -or
            [string]::IsNullOrWhiteSpace($parsedOrigin.Host) -or
            $parsedOrigin.Host -notmatch $exactHostPattern -or
            -not [string]::IsNullOrWhiteSpace($parsedOrigin.UserInfo) -or
            $parsedOrigin.AbsolutePath -ne "/" -or
            -not [string]::IsNullOrWhiteSpace($parsedOrigin.Query) -or
            -not [string]::IsNullOrWhiteSpace($parsedOrigin.Fragment)
        ) {
            throw "Production browser-origin allowlists must contain only exact HTTPS origins without wildcards, credentials, paths, queries, or fragments."
        }
    }
}

$routingProvider = [Environment]::GetEnvironmentVariable("TAXIMOBILE_ROUTING_PROVIDER")
if ($routingProvider -notin @("valhalla", "graphhopper")) {
    throw "TAXIMOBILE_ROUTING_PROVIDER must be exactly valhalla or graphhopper."
}

$firebaseProject = [Environment]::GetEnvironmentVariable("TAXIMOBILE_FIREBASE_PROJECT_ID")
if ($firebaseProject -match '[/\\\s]') {
    throw "TAXIMOBILE_FIREBASE_PROJECT_ID must be a project ID, not a path or URL."
}
$trustedProxies = [Environment]::GetEnvironmentVariable("TAXIMOBILE_TRUSTED_PROXY_CIDRS")
if ($trustedProxies.Split(",").Trim() | Where-Object { $_ -in @("*", "0.0.0.0/0", "::/0") }) {
    throw "Trusted proxy CIDRs must not authorize every network address."
}

Write-Output "TaxiMobile production deployment inputs passed non-secret validation."
