[CmdletBinding()]
param(
    [switch]$IncludeMonitoring
)

$ErrorActionPreference = "Stop"

$required = @(
    "TAXIMOBILE_API_IMAGE",
    "TAXIMOBILE_CLAMAV_IMAGE",
    "TAXIMOBILE_DATABASE_URL",
    "TAXIMOBILE_JWT_SECRET",
    "TAXIMOBILE_OPERATIONS_MFA_ENCRYPTION_KEY",
    "TAXIMOBILE_MONITORING_TOKEN",
    "TAXIMOBILE_ALLOWED_HOSTS",
    "TAXIMOBILE_ROUTING_PROVIDER",
    "TAXIMOBILE_ROUTING_BASE_URL",
    "TAXIMOBILE_FIREBASE_PROJECT_ID",
    "TAXIMOBILE_CASE_PAGER_URL",
    "TAXIMOBILE_CASE_PAGER_TOKEN",
    "TAXIMOBILE_TRUSTED_PROXY_CIDRS"
)
if ($IncludeMonitoring) {
    $required += @(
        "TAXIMOBILE_PROMETHEUS_IMAGE",
        "TAXIMOBILE_ALERTMANAGER_IMAGE",
        "TAXIMOBILE_GRAFANA_IMAGE",
        "TAXIMOBILE_LOKI_IMAGE",
        "TAXIMOBILE_ALLOY_IMAGE",
        "TAXIMOBILE_MONITORING_TOKEN_FILE",
        "TAXIMOBILE_GRAFANA_ADMIN_PASSWORD_FILE",
        "TAXIMOBILE_PLATFORM_ALERT_WEBHOOK_URL_FILE",
        "TAXIMOBILE_DISPATCH_ALERT_WEBHOOK_URL_FILE",
        "TAXIMOBILE_SCHEDULING_ALERT_WEBHOOK_URL_FILE",
        "TAXIMOBILE_DRIVER_COMPLIANCE_ALERT_WEBHOOK_URL_FILE"
    )
}
foreach ($name in $required) {
    if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($name))) {
        throw "$name must be supplied through the deployment configuration or secret boundary."
    }
}

foreach ($imageName in @("TAXIMOBILE_API_IMAGE", "TAXIMOBILE_CLAMAV_IMAGE")) {
    $image = [Environment]::GetEnvironmentVariable($imageName)
    if ($image -notmatch '@sha256:[0-9a-fA-F]{64}$') {
        throw "$imageName must end with a full immutable @sha256 digest."
    }
}
if ($IncludeMonitoring) {
    foreach ($imageName in @(
        "TAXIMOBILE_PROMETHEUS_IMAGE",
        "TAXIMOBILE_ALERTMANAGER_IMAGE",
        "TAXIMOBILE_GRAFANA_IMAGE",
        "TAXIMOBILE_LOKI_IMAGE",
        "TAXIMOBILE_ALLOY_IMAGE"
    )) {
        $image = [Environment]::GetEnvironmentVariable($imageName)
        if ($image -notmatch '@sha256:[0-9a-fA-F]{64}$') {
            throw "$imageName must end with a full immutable @sha256 digest."
        }
    }
}

$databaseUrl = [Environment]::GetEnvironmentVariable("TAXIMOBILE_DATABASE_URL")
if ($databaseUrl -notmatch '^postgresql\+asyncpg://') {
    throw "TAXIMOBILE_DATABASE_URL must use the postgresql+asyncpg scheme."
}
if ($databaseUrl -match '@(localhost|127\.|\[::1\])') {
    throw "Production PostgreSQL/PostGIS must not use a loopback host."
}

$jwtSecret = [Environment]::GetEnvironmentVariable("TAXIMOBILE_JWT_SECRET")
$operationsMfaKey = [Environment]::GetEnvironmentVariable("TAXIMOBILE_OPERATIONS_MFA_ENCRYPTION_KEY")
$monitoringToken = [Environment]::GetEnvironmentVariable("TAXIMOBILE_MONITORING_TOKEN")
$casePagerToken = [Environment]::GetEnvironmentVariable("TAXIMOBILE_CASE_PAGER_TOKEN")
if ($jwtSecret.Length -lt 32 -or $monitoringToken.Length -lt 32 -or $casePagerToken.Length -lt 32) {
    throw "JWT, monitoring, and case-pager secrets must each contain at least 32 characters."
}
if (
    $jwtSecret -eq $monitoringToken -or
    $jwtSecret -eq $casePagerToken -or
    $monitoringToken -eq $casePagerToken
) {
    throw "JWT, monitoring, and case-pager credentials must be independent secrets."
}
try {
    $normalizedMfaKey = $operationsMfaKey.Replace("-", "+").Replace("_", "/")
    $normalizedMfaKey += "=" * ((4 - ($normalizedMfaKey.Length % 4)) % 4)
    $decodedMfaKey = [Convert]::FromBase64String($normalizedMfaKey)
} catch {
    throw "TAXIMOBILE_OPERATIONS_MFA_ENCRYPTION_KEY must be base64url."
}
if ($decodedMfaKey.Length -ne 32) {
    throw "TAXIMOBILE_OPERATIONS_MFA_ENCRYPTION_KEY must decode to exactly 32 bytes."
}
if ($operationsMfaKey -in @($jwtSecret, $monitoringToken, $casePagerToken)) {
    throw "The operations MFA encryption key must be independent from other deployment secrets."
}

if ($IncludeMonitoring) {
    $monitoringTokenPath = [Environment]::GetEnvironmentVariable(
        "TAXIMOBILE_MONITORING_TOKEN_FILE"
    )
    if (-not (Test-Path -LiteralPath $monitoringTokenPath -PathType Leaf)) {
        throw "TAXIMOBILE_MONITORING_TOKEN_FILE must identify a readable secret file."
    }
    $monitoringFileValue = (Get-Content -LiteralPath $monitoringTokenPath -Raw).Trim()
    if ($monitoringFileValue -ne $monitoringToken) {
        throw "The monitoring token environment value and secret file must match exactly."
    }

    $grafanaPasswordPath = [Environment]::GetEnvironmentVariable(
        "TAXIMOBILE_GRAFANA_ADMIN_PASSWORD_FILE"
    )
    if (-not (Test-Path -LiteralPath $grafanaPasswordPath -PathType Leaf)) {
        throw "TAXIMOBILE_GRAFANA_ADMIN_PASSWORD_FILE must identify a readable secret file."
    }
    $grafanaAdminPassword = (Get-Content -LiteralPath $grafanaPasswordPath -Raw).Trim()
    if (
        $grafanaAdminPassword.Length -lt 20 -or
        $grafanaAdminPassword -notmatch '[A-Z]' -or
        $grafanaAdminPassword -notmatch '[a-z]' -or
        $grafanaAdminPassword -notmatch '[0-9]' -or
        $grafanaAdminPassword -notmatch '[^A-Za-z0-9]' -or
        $grafanaAdminPassword -match '[\r\n\p{C}]' -or
        $grafanaAdminPassword -match '["\\]'
    ) {
        throw "The Grafana administrator password must contain at least 20 printable characters with upper, lower, numeric, and special characters, without quotes or backslashes."
    }
    if (
        $grafanaAdminPassword -in @(
            $jwtSecret,
            $monitoringToken,
            $casePagerToken,
            $operationsMfaKey
        )
    ) {
        throw "The Grafana administrator password must be independent from other deployment secrets."
    }

    $webhookFileVariables = @(
        "TAXIMOBILE_PLATFORM_ALERT_WEBHOOK_URL_FILE",
        "TAXIMOBILE_DISPATCH_ALERT_WEBHOOK_URL_FILE",
        "TAXIMOBILE_SCHEDULING_ALERT_WEBHOOK_URL_FILE",
        "TAXIMOBILE_DRIVER_COMPLIANCE_ALERT_WEBHOOK_URL_FILE"
    )
    foreach ($fileVariable in $webhookFileVariables) {
        $webhookPath = [Environment]::GetEnvironmentVariable($fileVariable)
        if (-not (Test-Path -LiteralPath $webhookPath -PathType Leaf)) {
            throw "$fileVariable must identify a readable secret file."
        }
        $webhookValue = (Get-Content -LiteralPath $webhookPath -Raw).Trim()
        $webhookUri = $null
        if (
            -not [Uri]::TryCreate($webhookValue, [UriKind]::Absolute, [ref]$webhookUri) -or
            $webhookUri.Scheme -ne "https" -or
            [string]::IsNullOrWhiteSpace($webhookUri.Host) -or
            -not [string]::IsNullOrWhiteSpace($webhookUri.UserInfo) -or
            -not [string]::IsNullOrWhiteSpace($webhookUri.Query) -or
            -not [string]::IsNullOrWhiteSpace($webhookUri.Fragment)
        ) {
            throw "$fileVariable must contain one absolute HTTPS URL without credentials, query, or fragment."
        }
    }
}

$casePagerUrlValue = [Environment]::GetEnvironmentVariable("TAXIMOBILE_CASE_PAGER_URL")
$casePagerUrl = $null
if (
    -not [Uri]::TryCreate($casePagerUrlValue, [UriKind]::Absolute, [ref]$casePagerUrl) -or
    $casePagerUrl.Scheme -ne "https" -or
    [string]::IsNullOrWhiteSpace($casePagerUrl.Host) -or
    -not [string]::IsNullOrWhiteSpace($casePagerUrl.UserInfo) -or
    -not [string]::IsNullOrWhiteSpace($casePagerUrl.Query) -or
    -not [string]::IsNullOrWhiteSpace($casePagerUrl.Fragment)
) {
    throw "Production case paging requires an absolute HTTPS URL without credentials, query, or fragment."
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

$manualTransferValue = [Environment]::GetEnvironmentVariable("TAXIMOBILE_MANUAL_TRANSFER_ENABLED")
if ([string]::IsNullOrWhiteSpace($manualTransferValue)) {
    $manualTransferValue = "false"
}
if ($manualTransferValue -notin @("true", "false", "1", "0")) {
    throw "TAXIMOBILE_MANUAL_TRANSFER_ENABLED must be true, false, 1, or 0."
}
if ($manualTransferValue -in @("true", "1")) {
    $transferRecipient = [Environment]::GetEnvironmentVariable("TAXIMOBILE_TRANSFER_RECIPIENT_NAME")
    $transferBankAccount = [Environment]::GetEnvironmentVariable("TAXIMOBILE_TRANSFER_BANK_ACCOUNT")
    $transferWalletId = [Environment]::GetEnvironmentVariable("TAXIMOBILE_TRANSFER_WALLET_ID")
    if ([string]::IsNullOrWhiteSpace($transferRecipient)) {
        throw "Enabled manual transfer requires TAXIMOBILE_TRANSFER_RECIPIENT_NAME."
    }
    if (
        [string]::IsNullOrWhiteSpace($transferBankAccount) -and
        [string]::IsNullOrWhiteSpace($transferWalletId)
    ) {
        throw "Enabled manual transfer requires a bank account or M-Wallet destination."
    }
    foreach ($transferValue in @($transferRecipient, $transferBankAccount, $transferWalletId)) {
        if (
            -not [string]::IsNullOrWhiteSpace($transferValue) -and
            ($transferValue.Trim().Length -gt 120 -or $transferValue -match '\p{C}')
        ) {
            throw "Manual-transfer display values must contain at most 120 printable characters."
        }
    }
}
$trustedProxies = [Environment]::GetEnvironmentVariable("TAXIMOBILE_TRUSTED_PROXY_CIDRS")
if ($trustedProxies.Split(",").Trim() | Where-Object { $_ -in @("*", "0.0.0.0/0", "::/0") }) {
    throw "Trusted proxy CIDRs must not authorize every network address."
}

Write-Output "TaxiMobile production deployment inputs passed non-secret validation."
