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

$webApiContractValidator = Join-Path $PSScriptRoot "validate_web_api_contract.py"
Invoke-CheckedNativeCommand -FilePath $python -Arguments @(
    $webApiContractValidator
) -FailureMessage "The web/backend API contract gate failed."

$startedForTests = Start-PortablePostgres -Layout $layout -Port $DatabasePort -WaitSeconds 30
$psql = Join-Path $layout.PostgreSqlRoot "bin\psql.exe"
$dropdb = Join-Path $layout.PostgreSqlRoot "bin\dropdb.exe"
$createdb = Join-Path $layout.PostgreSqlRoot "bin\createdb.exe"
$previousPgPassword = $env:PGPASSWORD
$temporaryCreateDatabaseGranted = $false
try {
    # The integration fixture clones this exact migrated template once per test.
    # Recreate only the explicitly named CI database so migration-seeded baseline
    # rows are pristine and no test can inherit a prior run's accounts/sessions.
    $env:PGPASSWORD = $databasePassword
    Invoke-CheckedNativeCommand -FilePath $psql -Arguments @(
        "--host=127.0.0.1", "--port=$DatabasePort", "--username=postgres",
        "--dbname=postgres", "--no-password", "--set=ON_ERROR_STOP=1", "--quiet",
        "--command=SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'taximobile_ci' AND pid <> pg_backend_pid();"
    ) -FailureMessage "Could not close prior isolated CI database connections."
    Invoke-CheckedNativeCommand -FilePath $dropdb -Arguments @(
        "--host=127.0.0.1", "--port=$DatabasePort", "--username=postgres",
        "--no-password", "--if-exists", "--force", "taximobile_ci"
    ) -FailureMessage "Could not reset the isolated taximobile_ci database."
    Invoke-CheckedNativeCommand -FilePath $createdb -Arguments @(
        "--host=127.0.0.1", "--port=$DatabasePort", "--username=postgres",
        "--no-password", "--owner=$databaseUser", "taximobile_ci"
    ) -FailureMessage "Could not recreate the isolated taximobile_ci database."
    Invoke-CheckedNativeCommand -FilePath $psql -Arguments @(
        "--host=127.0.0.1", "--port=$DatabasePort", "--username=postgres",
        "--dbname=taximobile_ci", "--no-password", "--set=ON_ERROR_STOP=1", "--quiet",
        "--command=CREATE EXTENSION IF NOT EXISTS postgis;"
    ) -FailureMessage "Could not enable PostGIS in the isolated CI database."
    Invoke-CheckedNativeCommand -FilePath $psql -Arguments @(
        "--host=127.0.0.1", "--port=$DatabasePort", "--username=postgres",
        "--dbname=postgres", "--no-password", "--set=ON_ERROR_STOP=1", "--quiet",
        "--command=ALTER ROLE `"$databaseUser`" CREATEDB;"
    ) -FailureMessage "Could not grant temporary integration clone authority."
    $temporaryCreateDatabaseGranted = $true

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
    if ($temporaryCreateDatabaseGranted) {
        Invoke-CheckedNativeCommand -FilePath $psql -Arguments @(
            "--host=127.0.0.1", "--port=$DatabasePort", "--username=postgres",
            "--dbname=postgres", "--no-password", "--set=ON_ERROR_STOP=1", "--quiet",
            "--command=ALTER ROLE `"$databaseUser`" NOCREATEDB;"
        ) -FailureMessage "Could not revoke temporary integration clone authority."
    }
    $env:PGPASSWORD = $previousPgPassword
    if ($startedForTests) {
        Stop-PortablePostgres -Layout $layout | Out-Null
    }
}

Write-Output "Backend unit, API, and migrated PostGIS integration tests passed."
