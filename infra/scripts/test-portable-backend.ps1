[CmdletBinding()]
param(
    [Parameter()]
    [ValidateRange(1024, 65535)]
    [int]$DatabasePort = 5432
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_portable-common.ps1")

$layout = Get-TaxiMobileWorkspaceLayout
$environment = Import-TaxiMobileEnvironment -Path $layout.EnvironmentFile -SetProcessEnvironment
$databaseUser = Get-RequiredLocalValue -Values $environment -Name "POSTGRES_USER"
$databasePassword = Get-RequiredLocalValue -Values $environment -Name "POSTGRES_PASSWORD"
$python = Join-Path $layout.BackendRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "The workspace-local backend Python environment is missing."
}

$credentialValidator = Join-Path $PSScriptRoot "validate_source_credentials.py"
Invoke-CheckedNativeCommand -FilePath $python -Arguments @(
    $credentialValidator
) -FailureMessage "The source credential hygiene gate failed."

$apiContractValidator = Join-Path $PSScriptRoot "validate_mobile_api_contract.py"
Invoke-CheckedNativeCommand -FilePath $python -Arguments @(
    $apiContractValidator
) -FailureMessage "The mobile/backend API contract gate failed."

$startedForTests = Start-PortablePostgres -Layout $layout -Port $DatabasePort -WaitSeconds 30
try {
    $env:TAXIMOBILE_ENV = "test"
    $env:TAXIMOBILE_RUN_INTEGRATION = "1"
    $env:TAXIMOBILE_DATABASE_URL = Get-LocalDatabaseUrl -User $databaseUser -Password $databasePassword -Database "taximobile_ci" -Port $DatabasePort
    $env:TAXIMOBILE_ROUTING_PROVIDER = "valhalla"
    $env:TAXIMOBILE_ROUTING_BASE_URL = "http://127.0.0.1:8002"
    $env:TAXIMOBILE_ALLOWED_HOSTS = "localhost,127.0.0.1,testserver"

    Push-Location $layout.BackendRoot
    try {
        Invoke-CheckedNativeCommand -FilePath $python -Arguments @(
            "-m", "alembic", "upgrade", "head"
        ) -FailureMessage "Integration database migrations failed."
        Invoke-CheckedNativeCommand -FilePath $python -Arguments @(
            "-m", "pytest"
        ) -FailureMessage "The backend test suite failed."
    } finally {
        Pop-Location
    }
} finally {
    if ($startedForTests) {
        Stop-PortablePostgres -Layout $layout | Out-Null
    }
}

Write-Output "Backend unit, API, and migrated PostGIS integration tests passed."
