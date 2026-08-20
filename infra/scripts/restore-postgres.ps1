[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string]$BackupPath,

    [Parameter(Mandatory)]
    [switch]$ConfirmRestore,

    [Parameter()]
    [switch]$Portable,

    [Parameter()]
    [string]$TargetDatabase,

    [Parameter()]
    [switch]$CreatePortableTarget
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_portable-common.ps1")
if (-not $ConfirmRestore) {
    throw "Restoration requires -ConfirmRestore. It must target a clean, non-production database."
}

$layout = Get-TaxiMobileWorkspaceLayout
$infraRoot = $layout.InfraRoot
$composeFile = Join-Path $infraRoot "compose.yaml"
$environmentFile = Join-Path $infraRoot ".env"
if (-not (Test-Path -LiteralPath $environmentFile)) {
    throw "Generate infra/.env with scripts/new-local-env.ps1 before restoring a backup."
}

$environment = Import-TaxiMobileEnvironment -Path $environmentFile
$configuredDatabaseName = Get-RequiredLocalValue -Values $environment -Name "POSTGRES_DB"
$databaseUser = Get-RequiredLocalValue -Values $environment -Name "POSTGRES_USER"
$databasePassword = Get-RequiredLocalValue -Values $environment -Name "POSTGRES_PASSWORD"
$databasePort = if ($environment.ContainsKey("POSTGRES_PORT")) { [int]$environment["POSTGRES_PORT"] } else { 5432 }
Assert-SafeDatabaseIdentifier -Value $configuredDatabaseName -Name "POSTGRES_DB"
Assert-SafeDatabaseIdentifier -Value $databaseUser -Name "POSTGRES_USER"
Assert-SafeLocalSecret -Value $databasePassword -Name "POSTGRES_PASSWORD"

$resolvedBackup = (Resolve-Path -LiteralPath $BackupPath).Path
if (-not $resolvedBackup.StartsWith($layout.WorkspaceRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Local TaxiMobile restore inputs must remain inside the workspace."
}

if ($Portable) {
    if (-not $CreatePortableTarget) {
        throw "Portable restore requires -CreatePortableTarget and creates only a new verification database."
    }
    if (-not $TargetDatabase -or $TargetDatabase -notmatch '^taximobile_restore_[A-Za-z0-9_]{1,40}$') {
        throw "Portable TargetDatabase must start with taximobile_restore_ and contain only letters, digits, or underscores."
    }
    Assert-SafeDatabaseIdentifier -Value $TargetDatabase -Name "TargetDatabase"
    if ($TargetDatabase -eq $configuredDatabaseName -or $TargetDatabase -eq "taximobile_ci") {
        throw "The portable restore target cannot be an application or integration-test database."
    }

    $startedForRestore = Start-PortablePostgres -Layout $layout -Port $databasePort
    $previousPgPassword = $env:PGPASSWORD
    try {
        $env:PGPASSWORD = $databasePassword
        $psql = Join-Path $layout.PostgreSqlRoot "bin\psql.exe"
        $existingDatabase = & $psql --host=127.0.0.1 --port=$databasePort --username=postgres --dbname=postgres `
            --no-password --tuples-only --no-align --set=ON_ERROR_STOP=1 `
            --command="SELECT datname FROM pg_database WHERE datname = '$TargetDatabase';"
        if ($LASTEXITCODE -ne 0) {
            throw "The portable restore target could not be checked."
        }
        if ($existingDatabase) {
            throw "Portable restore refuses to overwrite the existing database '$TargetDatabase'."
        }

        "CREATE DATABASE $TargetDatabase OWNER $databaseUser;" | & $psql --host=127.0.0.1 --port=$databasePort `
            --username=postgres --dbname=postgres --no-password --set=ON_ERROR_STOP=1 --quiet
        if ($LASTEXITCODE -ne 0) {
            throw "The clean portable restore target could not be created."
        }
        "CREATE EXTENSION IF NOT EXISTS postgis;" | & $psql --host=127.0.0.1 --port=$databasePort `
            --username=postgres --dbname=$TargetDatabase --no-password --set=ON_ERROR_STOP=1 --quiet
        if ($LASTEXITCODE -ne 0) {
            throw "PostGIS could not be enabled in the portable restore target."
        }

        # Restore as the local cluster administrator so extension-owned seed data
        # can be loaded. The dump retains the application's object ownership.
        & $psql --host=127.0.0.1 --port=$databasePort --username=postgres --dbname=$TargetDatabase `
            --no-password --set=ON_ERROR_STOP=1 --file=$resolvedBackup
        if ($LASTEXITCODE -ne 0) {
            throw "Restore failed. The newly created target may contain a partial restore and must be reviewed."
        }
    } finally {
        $env:PGPASSWORD = $previousPgPassword
        if ($startedForRestore) {
            Stop-PortablePostgres -Layout $layout | Out-Null
        }
    }

    Write-Output "Restore completed into new verification database '$TargetDatabase'. Run migrations and application smoke tests before considering the drill complete."
    exit 0
}

$databaseName = if ($TargetDatabase) { $TargetDatabase } else { $configuredDatabaseName }
Assert-SafeDatabaseIdentifier -Value $databaseName -Name "TargetDatabase"

# The command deliberately does not drop or overwrite a database. Create a
# clean local verification database before use; psql stops on the first error.
Get-Content -LiteralPath $BackupPath -Raw | & docker compose --env-file $environmentFile -f $composeFile exec -T postgres `
    psql --username=$databaseUser --dbname=$databaseName --set=ON_ERROR_STOP=1
if ($LASTEXITCODE -ne 0) {
    throw "Restore failed. The target database may not be clean."
}

Write-Output "Restore completed into database '$databaseName'. Run migrations and application smoke tests before using it."
