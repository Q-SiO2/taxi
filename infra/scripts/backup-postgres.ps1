[CmdletBinding()]
param(
    [Parameter()]
    [string]$OutputDirectory,

    [Parameter()]
    [switch]$Portable
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_portable-common.ps1")

$layout = Get-TaxiMobileWorkspaceLayout
$infraRoot = $layout.InfraRoot
$OutputDirectory = if ($OutputDirectory) { $OutputDirectory } else { Join-Path $infraRoot "backups" }
$composeFile = Join-Path $infraRoot "compose.yaml"
$environmentFile = Join-Path $infraRoot ".env"
if (-not (Test-Path -LiteralPath $environmentFile)) {
    throw "Generate infra/.env with scripts/new-local-env.ps1 before creating a backup."
}

$environment = Import-TaxiMobileEnvironment -Path $environmentFile
$databaseName = Get-RequiredLocalValue -Values $environment -Name "POSTGRES_DB"
$databaseUser = Get-RequiredLocalValue -Values $environment -Name "POSTGRES_USER"
$databasePassword = Get-RequiredLocalValue -Values $environment -Name "POSTGRES_PASSWORD"
$databasePort = if ($environment.ContainsKey("POSTGRES_PORT")) { [int]$environment["POSTGRES_PORT"] } else { 5432 }
Assert-SafeDatabaseIdentifier -Value $databaseName -Name "POSTGRES_DB"
Assert-SafeDatabaseIdentifier -Value $databaseUser -Name "POSTGRES_USER"
Assert-SafeLocalSecret -Value $databasePassword -Name "POSTGRES_PASSWORD"

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$resolvedOutput = (Resolve-Path -LiteralPath $OutputDirectory).Path
if (-not $resolvedOutput.StartsWith($layout.WorkspaceRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Local TaxiMobile backups must remain inside the workspace."
}
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupPath = Join-Path $resolvedOutput "taximobile-$timestamp.sql"
if (Test-Path -LiteralPath $backupPath) {
    throw "A backup with the same timestamp already exists: $backupPath"
}

$startedForBackup = $false
try {
    if ($Portable) {
        $pgDump = Join-Path $layout.PostgreSqlRoot "bin\pg_dump.exe"
        if (-not (Test-Path -LiteralPath $pgDump -PathType Leaf)) {
            throw "Run scripts/setup-portable-postgis.ps1 before creating a portable backup."
        }
        $startedForBackup = Start-PortablePostgres -Layout $layout -Port $databasePort
        $previousPgPassword = $env:PGPASSWORD
        try {
            $env:PGPASSWORD = $databasePassword
            & $pgDump --host=127.0.0.1 --port=$databasePort --username=$databaseUser --dbname=$databaseName `
                --no-password --no-privileges --no-comments --encoding=UTF8 --file=$backupPath
            $dumpExitCode = $LASTEXITCODE
        } finally {
            $env:PGPASSWORD = $previousPgPassword
        }
    } else {
        # Plain SQL intentionally avoids Windows binary-pipeline corruption.
        $writer = [IO.StreamWriter]::new($backupPath, $false, [Text.UTF8Encoding]::new($false))
        try {
            & docker compose --env-file $environmentFile -f $composeFile exec -T postgres `
                pg_dump --username=$databaseUser --dbname=$databaseName --no-owner --no-privileges --no-comments | ForEach-Object {
                    $writer.WriteLine($_)
                }
            $dumpExitCode = $LASTEXITCODE
        } finally {
            $writer.Dispose()
        }
    }
} finally {
    if ($startedForBackup) {
        Stop-PortablePostgres -Layout $layout | Out-Null
    }
}
if ($dumpExitCode -ne 0) {
    Remove-Item -LiteralPath $backupPath -ErrorAction SilentlyContinue
    throw "PostgreSQL backup failed."
}
if ((Get-Item -LiteralPath $backupPath).Length -eq 0) {
    Remove-Item -LiteralPath $backupPath
    throw "PostgreSQL backup produced an empty file."
}

Write-Output "Backup created: $backupPath"
