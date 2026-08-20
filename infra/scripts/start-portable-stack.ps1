[CmdletBinding()]
param(
    [Parameter()]
    [ValidateRange(1024, 65535)]
    [int]$DatabasePort = 5432,

    [Parameter()]
    [ValidateRange(1024, 65535)]
    [int]$ApiPort = 8000,

    [Parameter()]
    [ValidateRange(10, 180)]
    [int]$WaitTimeoutSeconds = 60
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_portable-common.ps1")

$layout = Get-TaxiMobileWorkspaceLayout
$postgresExecutable = Join-Path $layout.PostgreSqlRoot "bin\postgres.exe"
$pgVersion = Join-Path $layout.DataRoot "PG_VERSION"
if (-not (Test-Path -LiteralPath $postgresExecutable -PathType Leaf) -or
    -not (Test-Path -LiteralPath $pgVersion -PathType Leaf)) {
    throw "Run scripts/setup-portable-postgis.ps1 before starting the portable stack."
}

$environment = Import-TaxiMobileEnvironment -Path $layout.EnvironmentFile -SetProcessEnvironment
$databaseName = Get-RequiredLocalValue -Values $environment -Name "POSTGRES_DB"
$databaseUser = Get-RequiredLocalValue -Values $environment -Name "POSTGRES_USER"
$databasePassword = Get-RequiredLocalValue -Values $environment -Name "POSTGRES_PASSWORD"
$databaseUrl = Get-LocalDatabaseUrl -User $databaseUser -Password $databasePassword -Database $databaseName -Port $DatabasePort
$portablePython = Join-Path $layout.WorkspaceRoot ".tools\python312\python.exe"
$portablePythonMarker = Join-Path $layout.WorkspaceRoot ".tools\python312\.taximobile-runtime.json"
$virtualEnvironmentPython = Join-Path $layout.BackendRoot ".venv\Scripts\python.exe"
$python = if ((Test-Path -LiteralPath $portablePython -PathType Leaf) -and
    (Test-Path -LiteralPath $portablePythonMarker -PathType Leaf)) {
    $portablePython
} else {
    $virtualEnvironmentPython
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "No workspace-local backend Python runtime is available. Set up .tools/python312 or create backend/.venv and install backend/requirements.lock."
}

$postgresStarted = Start-PortablePostgres -Layout $layout -Port $DatabasePort -WaitSeconds $WaitTimeoutSeconds

$env:TAXIMOBILE_ENV = "development"
$env:TAXIMOBILE_DATABASE_URL = $databaseUrl
$env:TAXIMOBILE_ROUTING_PROVIDER = "valhalla"
$env:TAXIMOBILE_ROUTING_BASE_URL = "http://127.0.0.1:8002"
$env:TAXIMOBILE_ALLOWED_HOSTS = "localhost,127.0.0.1"

try {
    Push-Location $layout.BackendRoot
    try {
        Invoke-CheckedNativeCommand -FilePath $python -Arguments @(
            "-m", "alembic", "upgrade", "head"
        ) -FailureMessage "TaxiMobile database migrations failed."
    } finally {
        Pop-Location
    }

    New-Item -ItemType Directory -Force -Path $layout.LogRoot | Out-Null
    $pidFile = Join-Path $layout.RuntimeRoot "api-process.json"
    if (Test-Path -LiteralPath $pidFile -PathType Leaf) {
        try {
            $metadata = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
            $existing = Get-Process -Id ([int]$metadata.pid) -ErrorAction Stop
            $expectedPython = (Resolve-Path -LiteralPath $python).Path
            if ($existing.Path -eq $expectedPython -and $existing.StartTime.ToUniversalTime().Ticks -eq [long]$metadata.startTimeUtcTicks) {
                Write-Output "TaxiMobile API is already running with process ID $($existing.Id)."
            } else {
                throw "The saved API process identity no longer matches its process ID. Stop it manually only after inspection, then remove $pidFile."
            }
        } catch [Microsoft.PowerShell.Commands.ProcessCommandException] {
            Remove-Item -LiteralPath $pidFile -Force
        }
    }

    if (-not (Test-Path -LiteralPath $pidFile -PathType Leaf)) {
        $standardOutput = Join-Path $layout.LogRoot "api.stdout.log"
        $standardError = Join-Path $layout.LogRoot "api.stderr.log"
        $apiProcess = Start-Process -FilePath $python -ArgumentList @(
            "-m", "uvicorn", "taximobile_api.main:app", "--host", "127.0.0.1", "--port", [string]$ApiPort,
            "--no-access-log"
        ) -WorkingDirectory $layout.BackendRoot -WindowStyle Hidden -RedirectStandardOutput $standardOutput -RedirectStandardError $standardError -PassThru
        $apiProcess.Refresh()
        @{
            pid = $apiProcess.Id
            startTimeUtcTicks = $apiProcess.StartTime.ToUniversalTime().Ticks
            executable = (Resolve-Path -LiteralPath $python).Path
            port = $ApiPort
        } | ConvertTo-Json | Set-Content -LiteralPath $pidFile -Encoding UTF8
        Write-Output "Started TaxiMobile with $(& $python --version 2>&1)."
    }

    $deadline = (Get-Date).AddSeconds($WaitTimeoutSeconds)
    $healthUrl = "http://127.0.0.1:$ApiPort/health"
    $readyUrl = "http://127.0.0.1:$ApiPort/ready"
    do {
        try {
            $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 3
            $ready = Invoke-RestMethod -Uri $readyUrl -TimeoutSec 3
            if ($health.status -eq "ok" -and $ready.status -eq "ready") {
                Write-Output "TaxiMobile API and PostGIS are ready at http://127.0.0.1:$ApiPort."
                Write-Output "For a USB-connected Android phone, run: adb reverse tcp:$ApiPort tcp:$ApiPort"
                exit 0
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    } while ((Get-Date) -lt $deadline)

    throw "The API did not become ready. Inspect $($layout.LogRoot) without sharing secrets from the environment file."
} catch {
    if ($postgresStarted -and -not (Test-Path -LiteralPath (Join-Path $layout.RuntimeRoot "api-process.json") -PathType Leaf)) {
        Stop-PortablePostgres -Layout $layout | Out-Null
    }
    throw
}
