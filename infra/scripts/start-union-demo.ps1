[CmdletBinding()]
param(
    [switch]$ConfirmSyntheticDemo,
    [string]$DemoId,
    [ValidateSet("valhalla", "graphhopper")] [string]$RoutingProvider,
    [ValidateRange(1024, 65535)] [int]$DatabasePort = 5432,
    [ValidateRange(1024, 65535)] [int]$ApiPort = 8000,
    [ValidateRange(10, 60)] [int]$WaitTimeoutSeconds = 45
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_union-demo-common.ps1")
if (-not $ConfirmSyntheticDemo) {
    throw "Use -ConfirmSyntheticDemo for a loopback-only synthetic rehearsal, not public service."
}
$layout = Get-TaxiMobileWorkspaceLayout
$python = Join-Path $layout.BackendRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Backend virtual environment is missing." }
$values = Import-TaxiMobileEnvironment -Path $layout.EnvironmentFile
$dbUser = Get-RequiredLocalValue -Values $values -Name POSTGRES_USER
$dbPassword = Get-RequiredLocalValue -Values $values -Name POSTGRES_PASSWORD
Assert-SafeDatabaseIdentifier -Value $dbUser -Name POSTGRES_USER
Assert-SafeLocalSecret -Value $dbPassword -Name POSTGRES_PASSWORD

$fresh = [string]::IsNullOrWhiteSpace($DemoId)
if ($fresh) { $DemoId = [guid]::NewGuid().ToString("N") }
$root = Resolve-UnionDemoRoot -Layout $layout -DemoId $DemoId
if ($fresh) {
    if (Test-Path -LiteralPath $root) { throw "New demo directory already exists; refusing reuse." }
    New-Item -ItemType Directory -Path $root | Out-Null
    Protect-UnionDemoRoot -Root $root
    $secretBytes = [byte[]]::new(32)
    [Security.Cryptography.RandomNumberGenerator]::Fill($secretBytes)
    $state = [pscustomobject]@{
        schema = 1; demoId = $DemoId; database = "taximobile_union_demo_$DemoId"
        databasePort = $DatabasePort; apiPort = $ApiPort
        jwtSecret = [Convert]::ToHexString($secretBytes).ToLowerInvariant()
        phase = "PREPARING"; api = $null
    }
} else {
    $state = Read-UnionDemoState -Layout $layout -DemoId $DemoId
    if (($PSBoundParameters.ContainsKey("DatabasePort") -and $DatabasePort -ne $state.databasePort) -or
        ($PSBoundParameters.ContainsKey("ApiPort") -and $ApiPort -ne $state.apiPort)) {
        throw "Resume uses the recorded ports; it cannot retarget an existing demo."
    }
    $DatabasePort = [int]$state.databasePort
    $ApiPort = [int]$state.apiPort
    Protect-UnionDemoRoot -Root $root
    if ($state.phase -notin @("SEEDED", "STARTED", "READY", "STOPPED")) {
        throw "This demo did not finish preparation. Inspect its private logs; it was not reseeded."
    }
}
$lockPath = Join-Path $root "launch.lock"
$lock = [IO.File]::Open($lockPath, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
$statePath = Join-Path $root "state.json"
$priorEnvironment = @{}
$variableNames = @("PGPASSWORD", "GOOGLE_APPLICATION_CREDENTIALS") + @(
    Get-ChildItem Env: | Where-Object Name -Like "TAXIMOBILE_*" | ForEach-Object Name
)
foreach ($name in $variableNames) {
    $priorEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
    [Environment]::SetEnvironmentVariable($name, $null, "Process")
}
try {
    if (-not $fresh) {
        # A concurrent launcher/stopper may have changed process ownership while
        # this invocation waited for the file lock. Never act on stale metadata.
        $state = Read-UnionDemoState -Layout $layout -DemoId $DemoId
    }
    $live = Get-UnionDemoApiProcess -Layout $layout -State $state
    $selectedRouting = Resolve-UnionDemoRoutingProvider -State $state -Requested $RoutingProvider -HasLiveApi ($null -ne $live)
    $listener = @(Get-NetTCPConnection -LocalPort $ApiPort -State Listen -ErrorAction SilentlyContinue)
    $ownedPids = @()
    if ($null -ne $live) {
        $ownedPids = @($live.Id) + @(Get-UnionDemoApiChildProcesses -Layout $layout -State $state -RootProcess $live | ForEach-Object Id)
    }
    if ($listener.Count -gt 0 -and @($listener | Where-Object {
        $_.OwningProcess -notin $ownedPids -or $_.LocalAddress -ne "127.0.0.1"
    }).Count -gt 0) {
        throw "The demo API port is occupied by another process. It was not stopped."
    }
    $null = Start-PortablePostgres -Layout $layout -Port $DatabasePort -WaitSeconds 30
    $env:PGPASSWORD = $dbPassword
    $clusterDirectory = & (Join-Path $layout.PostgreSqlRoot "bin\psql.exe") `
        --host=127.0.0.1 --port=$DatabasePort --username=postgres --no-password `
        --dbname=postgres --tuples-only --no-align --set=ON_ERROR_STOP=1 `
        --command="SELECT current_setting('data_directory');"
    if ($LASTEXITCODE -ne 0 -or @($clusterDirectory).Count -ne 1 -or
        [IO.Path]::GetFullPath(([string]$clusterDirectory).Trim()).TrimEnd('\', '/') -ne
        [IO.Path]::GetFullPath($layout.DataRoot).TrimEnd('\', '/')) {
        throw "The requested database port does not belong to this workspace's portable cluster. No demo database was created or changed."
    }
    $env:TAXIMOBILE_ENV = "development"
    $env:TAXIMOBILE_PROCESS_ROLE = "all"
    $env:TAXIMOBILE_DATABASE_URL = Get-LocalDatabaseUrl -User $dbUser -Password $dbPassword -Database $state.database -Port $DatabasePort
    $env:TAXIMOBILE_JWT_SECRET = $state.jwtSecret
    # The Android emulator reaches this loopback-bound API via its host alias.
    # Keep an exact allowlist; this does not expose the API on a LAN interface.
    $env:TAXIMOBILE_ALLOWED_HOSTS = "localhost,127.0.0.1,10.0.2.2"
    $env:TAXIMOBILE_CORS_ORIGINS = "http://127.0.0.1:8080"
    $env:TAXIMOBILE_ROUTING_PROVIDER = $selectedRouting
    $env:TAXIMOBILE_ROUTING_BASE_URL = "http://127.0.0.1:8002"
    $env:TAXIMOBILE_GEOCODING_PROVIDER = "disabled"
    $env:TAXIMOBILE_OPERATIONS_PASSWORD_LOGIN_ENABLED = "true"
    $env:TAXIMOBILE_MANUAL_TRANSFER_ENABLED = "false"
    $env:TAXIMOBILE_LOG_LEVEL = "WARNING"
    $state | Add-Member -NotePropertyName routingProvider -NotePropertyValue $selectedRouting -Force
    if ($fresh) {
        $state | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $statePath -Encoding UTF8
        Invoke-CheckedNativeCommand -FilePath (Join-Path $layout.PostgreSqlRoot "bin\createdb.exe") -Arguments @(
            "--host=127.0.0.1", "--port=$DatabasePort", "--username=postgres", "--no-password", "--owner=$dbUser", $state.database
        ) -FailureMessage "Isolated demo database creation failed; existing databases were not changed."
        Invoke-CheckedNativeCommand -FilePath (Join-Path $layout.PostgreSqlRoot "bin\psql.exe") -Arguments @(
            "--host=127.0.0.1", "--port=$DatabasePort", "--username=postgres", "--no-password",
            "--dbname=$($state.database)", "--set=ON_ERROR_STOP=1", "--quiet", "--command=CREATE EXTENSION postgis;"
        ) -FailureMessage "Demo PostGIS extension creation failed."
        Push-Location $layout.BackendRoot
        try {
            Invoke-CheckedNativeCommand -FilePath $python -Arguments @("-m", "alembic", "upgrade", "head") -FailureMessage "Demo migrations failed."
            Invoke-CheckedNativeCommand -FilePath $python -Arguments @(
                "-m", "taximobile_api.operations.ux_demo_seed", "--confirm", "CONFIRM_LOCAL_UX_DEMO_DATA",
                "--profile", "union_live", "--output", (Join-Path $root "accounts.json")
            ) -FailureMessage "Demo seed failed; no automatic retry or reset was performed."
        } finally { Pop-Location }
        $state.phase = "SEEDED"
        $state | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $statePath -Encoding UTF8
    }
    if ($null -eq $live) {
        $attempt = [guid]::NewGuid().ToString("N")
        $live = Start-Process -FilePath $python -ArgumentList @(
            "-m", "uvicorn", "taximobile_api.main:app", "--host", "127.0.0.1", "--port", [string]$ApiPort, "--no-access-log"
        ) -WorkingDirectory $layout.BackendRoot -WindowStyle Hidden -PassThru `
          -RedirectStandardOutput (Join-Path $root "api-$attempt.stdout.log") `
          -RedirectStandardError (Join-Path $root "api-$attempt.stderr.log")
        $live.Refresh()
        $state.api = [pscustomobject]@{
            pid = $live.Id; startTimeUtcTicks = $live.StartTime.ToUniversalTime().Ticks
            executable = (Resolve-Path -LiteralPath $python).Path
        }
        $state.phase = "STARTED"
        $state | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $statePath -Encoding UTF8
    }
    $deadline = (Get-Date).AddSeconds($WaitTimeoutSeconds)
    do {
        $live.Refresh()
        if ($live.HasExited) { throw "Demo API exited. Inspect this demo's private logs; no restart was attempted." }
        try {
            $ready = Invoke-RestMethod -Uri "http://127.0.0.1:$ApiPort/ready" -TimeoutSec 2
            if ($ready.status -eq "ready") {
                $state.phase = "READY"
                $state | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $statePath -Encoding UTF8
                Write-Output "Demo ID: $DemoId"
                Write-Output "API ready: http://127.0.0.1:$ApiPort"
                Write-Output "Selected routing: $selectedRouting at http://127.0.0.1:8002 (requires separate provider verification)"
                Write-Output "Private test logins: $(Join-Path $root 'accounts.json')"
                Write-Output "Resume this same demo with -DemoId $DemoId; it will not reseed."
                Write-Output "Maps, routing, OS push and mobile/browser journeys still require verification."
                return
            }
        } catch [Microsoft.PowerShell.Commands.HttpResponseException] { }
          catch [System.Net.Http.HttpRequestException] { }
          catch [System.Threading.Tasks.TaskCanceledException] { }
        Start-Sleep -Milliseconds 250
    } while ((Get-Date) -lt $deadline)
    throw "Readiness observation timed out. The recorded API may still be live; inspect/resume this exact demo ID, do not create a replacement merely for a timeout."
} finally {
    foreach ($name in @(Get-ChildItem Env: | Where-Object Name -Like "TAXIMOBILE_*" | ForEach-Object Name)) {
        [Environment]::SetEnvironmentVariable($name, $null, "Process")
    }
    foreach ($name in $priorEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($name, $priorEnvironment[$name], "Process")
    }
    $lock.Dispose()
}
