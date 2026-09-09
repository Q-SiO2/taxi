[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$infraRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$templatePath = Join-Path $infraRoot ".env.example"
$environmentFile = Join-Path $infraRoot ".env"

if (Test-Path -LiteralPath $environmentFile) {
    throw "infra/.env already exists. This generator never overwrites an existing local environment file."
}

function New-LocalSecret {
    param(
        [Parameter(Mandatory)]
        [ValidateRange(24, 128)]
        [int]$ByteCount
    )

    $bytes = New-Object byte[] $ByteCount
    $random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $random.GetBytes($bytes)
    } finally {
        $random.Dispose()
    }

    return [Convert]::ToBase64String($bytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")
}

$postgresPassword = New-LocalSecret -ByteCount 32
$jwtSecret = New-LocalSecret -ByteCount 48
$monitoringToken = New-LocalSecret -ByteCount 32
$driverDocumentKey = New-LocalSecret -ByteCount 32
$contents = Get-Content -LiteralPath $templatePath -Raw
$contents = $contents -replace '(?m)^POSTGRES_PASSWORD=.*$', "POSTGRES_PASSWORD=$postgresPassword"
$contents = $contents -replace '(?m)^TAXIMOBILE_JWT_SECRET=.*$', "TAXIMOBILE_JWT_SECRET=$jwtSecret"
$contents = $contents -replace '(?m)^TAXIMOBILE_MONITORING_TOKEN=.*$', "TAXIMOBILE_MONITORING_TOKEN=$monitoringToken"
$contents = $contents -replace '(?m)^TAXIMOBILE_DRIVER_DOCUMENT_STORAGE_ROOT=.*$', 'TAXIMOBILE_DRIVER_DOCUMENT_STORAGE_ROOT=/var/lib/taximobile/driver-documents'
$contents = $contents -replace '(?m)^TAXIMOBILE_DRIVER_DOCUMENT_ENCRYPTION_KEY=.*$', "TAXIMOBILE_DRIVER_DOCUMENT_ENCRYPTION_KEY=$driverDocumentKey"
$contents = $contents -replace '(?m)^TAXIMOBILE_DRIVER_DOCUMENT_CLAMAV_HOST=.*$', 'TAXIMOBILE_DRIVER_DOCUMENT_CLAMAV_HOST=clamav'

[System.IO.File]::WriteAllText(
    $environmentFile,
    $contents,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Output "Created ignored local environment file: $environmentFile"
Write-Output "It contains generated development-only secrets and was not printed."
