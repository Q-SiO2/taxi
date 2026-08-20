[CmdletBinding()]
param(
    [Parameter()]
    [switch]$ConfirmLocalDemoData,

    [Parameter()]
    [ValidateRange(1024, 65535)]
    [int]$DatabasePort = 5432
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_portable-common.ps1")

if (-not $ConfirmLocalDemoData) {
    throw "This command adds synthetic records to the local development database. Re-run with -ConfirmLocalDemoData after review."
}

$layout = Get-TaxiMobileWorkspaceLayout
$environment = Import-TaxiMobileEnvironment -Path $layout.EnvironmentFile -SetProcessEnvironment
$databaseName = Get-RequiredLocalValue -Values $environment -Name "POSTGRES_DB"
$databaseUser = Get-RequiredLocalValue -Values $environment -Name "POSTGRES_USER"
$databasePassword = Get-RequiredLocalValue -Values $environment -Name "POSTGRES_PASSWORD"
$python = Join-Path $layout.BackendRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "The workspace-local backend Python environment is missing."
}

$env:TAXIMOBILE_ENV = "development"
$env:TAXIMOBILE_DATABASE_URL = Get-LocalDatabaseUrl -User $databaseUser -Password $databasePassword -Database $databaseName -Port $DatabasePort
$env:TAXIMOBILE_ROUTING_PROVIDER = "valhalla"
$env:TAXIMOBILE_ROUTING_BASE_URL = "http://127.0.0.1:8002"
$env:TAXIMOBILE_ALLOWED_HOSTS = "localhost,127.0.0.1"

Push-Location $layout.BackendRoot
try {
    Invoke-CheckedNativeCommand -FilePath $python -Arguments @(
        "-m", "taximobile_api.operations.ux_demo_seed",
        "--confirm", "CONFIRM_LOCAL_UX_DEMO_DATA"
    ) -FailureMessage "Local UX demo data creation failed."
} finally {
    Pop-Location
}
