[CmdletBinding()]
param(
    [Parameter()]
    [ValidateRange(1024, 65535)]
    [int]$DatabasePort = 5432,

    [Parameter()]
    [string]$JUnitPath,

    [Parameter()]
    [string]$DatabaseMetadataPath,

    [Parameter()]
    [string]$BackupRestorePath,

    [Parameter()]
    [string]$EvidencePath
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_portable-common.ps1")

$evidencePathCount = @($JUnitPath, $DatabaseMetadataPath, $BackupRestorePath, $EvidencePath).Where({ -not [string]::IsNullOrWhiteSpace($_) }).Count
if ($evidencePathCount -ne 0 -and $evidencePathCount -ne 4) {
    throw "JUnitPath, DatabaseMetadataPath, BackupRestorePath, and EvidencePath must be supplied together."
}
$writeEvidence = $evidencePathCount -eq 4

function Resolve-NewT3EvidencePath {
    param([Parameter(Mandatory)] [string]$Path)
    $resolved = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
    if (Test-Path -LiteralPath $resolved) {
        throw "T3 evidence refuses to overwrite an existing path: $resolved"
    }
    $parent = Split-Path -Parent $resolved
    if (-not $parent) {
        throw "T3 evidence output requires a parent directory."
    }
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    return $resolved
}

if ($writeEvidence) {
    $resolvedJUnitPath = Resolve-NewT3EvidencePath -Path $JUnitPath
    $resolvedDatabaseMetadataPath = Resolve-NewT3EvidencePath -Path $DatabaseMetadataPath
    $resolvedBackupRestorePath = Resolve-NewT3EvidencePath -Path $BackupRestorePath
    $resolvedEvidencePath = Resolve-NewT3EvidencePath -Path $EvidencePath
    if (@($resolvedJUnitPath, $resolvedDatabaseMetadataPath, $resolvedBackupRestorePath, $resolvedEvidencePath) | Group-Object | Where-Object Count -gt 1) {
        throw "Each T3 evidence output path must be distinct."
    }
}

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
$pgDump = Join-Path $layout.PostgreSqlRoot "bin\pg_dump.exe"
$pgRestore = Join-Path $layout.PostgreSqlRoot "bin\pg_restore.exe"
$previousPgPassword = $env:PGPASSWORD
$temporaryCreateDatabaseGranted = $false
try {
    # The integration fixture clones this exact migrated template once per test.
    # Recreate only the explicitly named CI database so migration-seeded baseline
    # rows are pristine and no test can inherit a prior run's accounts/sessions.
    $env:PGPASSWORD = $databasePassword
    $staleCloneOutput = & $psql --host=127.0.0.1 --port=$DatabasePort --username=postgres `
        --dbname=postgres --no-password --tuples-only --no-align --set=ON_ERROR_STOP=1 `
        --command="SELECT datname FROM pg_database WHERE datname LIKE 'taximobile_ci_test_%' ORDER BY datname;"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not inventory stale disposable integration clone databases."
    }
    $staleCloneDatabases = @($staleCloneOutput | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    foreach ($staleCloneDatabase in $staleCloneDatabases) {
        if ($staleCloneDatabase -notmatch '^taximobile_ci_test_[a-f0-9]{32}$') {
            throw "Refusing unexpected database name in the disposable integration namespace."
        }
        Invoke-CheckedNativeCommand -FilePath $psql -Arguments @(
            "--host=127.0.0.1", "--port=$DatabasePort", "--username=postgres",
            "--dbname=postgres", "--no-password", "--set=ON_ERROR_STOP=1", "--quiet",
            "--command=ALTER DATABASE `"$staleCloneDatabase`" WITH ALLOW_CONNECTIONS false;"
        ) -FailureMessage "Could not close a stale disposable integration clone."
        Invoke-CheckedNativeCommand -FilePath $dropdb -Arguments @(
            "--host=127.0.0.1", "--port=$DatabasePort", "--username=postgres",
            "--no-password", "--force", $staleCloneDatabase
        ) -FailureMessage "Could not remove a stale disposable integration clone."
    }
    $staleCloneCount = $staleCloneDatabases.Count
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
        $pytestArguments = @("-m", "pytest")
        if ($writeEvidence) {
            $pytestArguments += "--junitxml=$resolvedJUnitPath"
        }
        Invoke-CheckedNativeCommand -FilePath $python -Arguments $pytestArguments `
            -FailureMessage "The backend test suite failed."
    } finally {
        Pop-Location
    }

    # Integration tests need CREATEDB to clone the migrated template. Revoke it
    # before collecting post-run metadata so the evidence proves authority did
    # not leak beyond the suite.
    if ($temporaryCreateDatabaseGranted) {
        Invoke-CheckedNativeCommand -FilePath $psql -Arguments @(
            "--host=127.0.0.1", "--port=$DatabasePort", "--username=postgres",
            "--dbname=postgres", "--no-password", "--set=ON_ERROR_STOP=1", "--quiet",
            "--command=ALTER ROLE `"$databaseUser`" NOCREATEDB;"
        ) -FailureMessage "Could not revoke temporary integration clone authority."
        $temporaryCreateDatabaseGranted = $false
    }

    if ($writeEvidence) {
        $databaseMetadataCollector = Join-Path $PSScriptRoot "collect_t3_database_metadata.py"
        Invoke-CheckedNativeCommand -FilePath $python -Arguments @(
            $databaseMetadataCollector,
            "--authority-mode", "TEMPORARY_CREATEDB_REVOKED",
            "--database-lifecycle", "RECREATED_BEFORE_MIGRATION",
            "--preexisting-clone-count", $staleCloneCount,
            "--output", $resolvedDatabaseMetadataPath
        ) -FailureMessage "T3 post-run database metadata collection failed."

        $backupRestoreRunner = Join-Path $PSScriptRoot "run_t3_backup_restore_rehearsal.py"
        Invoke-CheckedNativeCommand -FilePath $python -Arguments @(
            $backupRestoreRunner,
            "--maintenance-user", "postgres",
            "--pg-dump", $pgDump,
            "--pg-restore", $pgRestore,
            "--createdb", $createdb,
            "--dropdb", $dropdb,
            "--psql", $psql,
            "--output", $resolvedBackupRestorePath
        ) -FailureMessage "T3 local backup/restore rehearsal failed."

        $systemEvidenceGenerator = Join-Path $PSScriptRoot "generate_t3_system_report.py"
        Invoke-CheckedNativeCommand -FilePath $python -Arguments @(
            $systemEvidenceGenerator,
            "--junit", $resolvedJUnitPath,
            "--database-metadata", $resolvedDatabaseMetadataPath,
            "--backup-restore", $resolvedBackupRestorePath,
            "--output", $resolvedEvidencePath
        ) -FailureMessage "T3 system evidence generation failed."
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
if ($writeEvidence) {
    Write-Output "Complete bounded T3 evidence written to $resolvedEvidencePath. Formal phase acceptance remains open."
}
