[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$TargetDatabase,

    [Parameter()]
    [ValidateRange(1024, 65535)]
    [int]$DatabasePort = 5432
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_portable-common.ps1")

$layout = Get-TaxiMobileWorkspaceLayout
$environment = Import-TaxiMobileEnvironment -Path $layout.EnvironmentFile
$sourceDatabase = Get-RequiredLocalValue -Values $environment -Name "POSTGRES_DB"
$databaseUser = Get-RequiredLocalValue -Values $environment -Name "POSTGRES_USER"
$databasePassword = Get-RequiredLocalValue -Values $environment -Name "POSTGRES_PASSWORD"
Assert-SafeDatabaseIdentifier -Value $sourceDatabase -Name "POSTGRES_DB"
Assert-SafeDatabaseIdentifier -Value $databaseUser -Name "POSTGRES_USER"
Assert-SafeLocalSecret -Value $databasePassword -Name "POSTGRES_PASSWORD"

if ($TargetDatabase -notmatch '^taximobile_restore_[A-Za-z0-9_]{1,40}$') {
    throw "TargetDatabase must be a dedicated taximobile_restore_ verification database."
}
Assert-SafeDatabaseIdentifier -Value $TargetDatabase -Name "TargetDatabase"
if ($TargetDatabase -eq $sourceDatabase -or $TargetDatabase -eq "taximobile_ci") {
    throw "Restore verification refuses application and integration-test databases."
}

$python = Join-Path $layout.BackendRoot ".venv\Scripts\python.exe"
$psql = Join-Path $layout.PostgreSqlRoot "bin\psql.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf) -or -not (Test-Path -LiteralPath $psql -PathType Leaf)) {
    throw "Workspace-local Python and portable PostgreSQL must be installed before restore verification."
}

function Invoke-ScalarQuery {
    param(
        [Parameter(Mandatory)] [string]$Database,
        [Parameter(Mandatory)] [string]$Sql
    )
    $result = & $psql --host=127.0.0.1 --port=$DatabasePort --username=$databaseUser --dbname=$Database `
        --no-password --tuples-only --no-align --set=ON_ERROR_STOP=1 --command=$Sql
    if ($LASTEXITCODE -ne 0) {
        throw "Restore verification query failed for the explicitly selected database."
    }
    return ($result | Out-String).Trim()
}

$startedForVerification = Start-PortablePostgres -Layout $layout -Port $DatabasePort -WaitSeconds 30
$previousPgPassword = $env:PGPASSWORD
$previousDatabaseUrl = $env:TAXIMOBILE_DATABASE_URL
try {
    $env:PGPASSWORD = $databasePassword
    Push-Location $layout.BackendRoot
    try {
        $headOutput = & $python -m alembic heads
        if ($LASTEXITCODE -ne 0) {
            throw "The source migration head could not be determined."
        }
        $headMatches = [regex]::Matches(($headOutput | Out-String), '(?m)^\s*([^\s]+)\s+\(head\)\s*$')
        if ($headMatches.Count -ne 1) {
            throw "Restore verification requires exactly one source migration head."
        }
        $expectedHead = $headMatches[0].Groups[1].Value
    } finally {
        Pop-Location
    }

    $restoredHead = Invoke-ScalarQuery -Database $TargetDatabase -Sql "SELECT version_num FROM alembic_version;"
    if ($restoredHead -ne $expectedHead) {
        throw "Restored migration head '$restoredHead' does not match source head '$expectedHead'."
    }
    $postgisVersion = Invoke-ScalarQuery -Database $TargetDatabase -Sql "SELECT postgis_version();"
    if (-not $postgisVersion) {
        throw "The restored database does not report a PostGIS version."
    }

    $aggregateSql = @"
SELECT json_build_object(
  'users', (SELECT count(*) FROM users),
  'rides', (SELECT count(*) FROM rides),
  'payments', (SELECT count(*) FROM payments),
  'driver_credentials', (SELECT count(*) FROM driver_credentials),
  'cooperatives', (SELECT count(*) FROM cooperatives),
  'memberships', (SELECT count(*) FROM cooperative_memberships)
)::text;
"@
    $sourceAggregates = Invoke-ScalarQuery -Database $sourceDatabase -Sql $aggregateSql
    $restoredAggregates = Invoke-ScalarQuery -Database $TargetDatabase -Sql $aggregateSql
    if ($sourceAggregates -ne $restoredAggregates) {
        throw "Restored aggregate counts do not match the backup source."
    }

    $env:TAXIMOBILE_DATABASE_URL = Get-LocalDatabaseUrl -User $databaseUser -Password $databasePassword `
        -Database $TargetDatabase -Port $DatabasePort
    Push-Location $layout.BackendRoot
    try {
        Invoke-CheckedNativeCommand -FilePath $python -Arguments @(
            "-m", "alembic", "upgrade", "head"
        ) -FailureMessage "The restored database did not accept a no-op migration to head."
    } finally {
        Pop-Location
    }
    $verifiedHead = Invoke-ScalarQuery -Database $TargetDatabase -Sql "SELECT version_num FROM alembic_version;"
    if ($verifiedHead -ne $expectedHead) {
        throw "The restored database changed away from the expected migration head."
    }

    Write-Output "Portable restore verified at migration head $expectedHead with PostGIS $postgisVersion."
    Write-Output "Aggregate counts matched for users, rides, payments, driver credentials, cooperatives, and memberships."
} finally {
    $env:PGPASSWORD = $previousPgPassword
    $env:TAXIMOBILE_DATABASE_URL = $previousDatabaseUrl
    if ($startedForVerification) {
        Stop-PortablePostgres -Layout $layout | Out-Null
    }
}
