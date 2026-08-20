[CmdletBinding()]
param(
    [Parameter()]
    [ValidateRange(1024, 65535)]
    [int]$Port = 5432
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_portable-common.ps1")

$layout = Get-TaxiMobileWorkspaceLayout
$downloadRoot = Join-Path $layout.WorkspaceRoot ".tools\portable-postgis-downloads"
$postgresArchive = Join-Path $downloadRoot "postgresql-16.14-1-windows-x64-binaries.zip"
$postgisArchive = Join-Path $downloadRoot "postgis-bundle-pg16-3.5.3x64.zip"
$postgresUrl = "https://get.enterprisedb.com/postgresql/postgresql-16.14-1-windows-x64-binaries.zip"
$postgisUrl = "https://download-cache.osgeo.org/postgis/windows/pg16/archive/postgis-bundle-pg16-3.5.3x64.zip"
$postgresSha256 = "98AF1417BA6A8DC30543E560E5407833A3B9E7CC7ED20E73B2006F3AA2F04663"
$postgisSha256 = "DB5C96627D24160CCA9BD4378407A4041149D02DF9B88FAEDA2CE1736B3A736D"
$postgisFolderName = "postgis-bundle-pg16-3.5.3x64"

function Get-VerifiedArchive {
    param(
        [Parameter(Mandatory)]
        [string]$Url,

        [Parameter(Mandatory)]
        [string]$Destination,

        [Parameter(Mandatory)]
        [string]$ExpectedSha256
    )

    if (Test-Path -LiteralPath $Destination -PathType Leaf) {
        $actualHash = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash
        if ($actualHash -eq $ExpectedSha256) {
            Write-Output "Using verified archive: $Destination"
            return
        }
        throw "The existing archive has an unexpected checksum and was not overwritten: $Destination"
    }

    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
    $temporaryPath = "$Destination.download"
    if (Test-Path -LiteralPath $temporaryPath) {
        throw "An incomplete download already exists. Remove it after confirming its path, then retry: $temporaryPath"
    }

    try {
        $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
        if ($null -ne $curl) {
            Invoke-CheckedNativeCommand -FilePath $curl.Source -Arguments @(
                "--fail", "--location", "--retry", "3", "--output", $temporaryPath, $Url
            ) -FailureMessage "The required archive could not be downloaded."
        } else {
            Invoke-WebRequest -Uri $Url -OutFile $temporaryPath -UseBasicParsing
        }

        $actualHash = (Get-FileHash -LiteralPath $temporaryPath -Algorithm SHA256).Hash
        if ($actualHash -ne $ExpectedSha256) {
            throw "The downloaded archive checksum did not match the pinned value."
        }
        Move-Item -LiteralPath $temporaryPath -Destination $Destination
    } catch {
        if (Test-Path -LiteralPath $temporaryPath) {
            Remove-Item -LiteralPath $temporaryPath -Force
        }
        throw
    }
}

if (-not (Test-Path -LiteralPath $layout.EnvironmentFile -PathType Leaf)) {
    & (Join-Path $PSScriptRoot "new-local-env.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "The local environment file could not be generated."
    }
}

$environment = Import-TaxiMobileEnvironment -Path $layout.EnvironmentFile
$databaseName = Get-RequiredLocalValue -Values $environment -Name "POSTGRES_DB"
$databaseUser = Get-RequiredLocalValue -Values $environment -Name "POSTGRES_USER"
$databasePassword = Get-RequiredLocalValue -Values $environment -Name "POSTGRES_PASSWORD"
Assert-SafeDatabaseIdentifier -Value $databaseName -Name "POSTGRES_DB"
Assert-SafeDatabaseIdentifier -Value $databaseUser -Name "POSTGRES_USER"
Assert-SafeLocalSecret -Value $databasePassword -Name "POSTGRES_PASSWORD"

Get-VerifiedArchive -Url $postgresUrl -Destination $postgresArchive -ExpectedSha256 $postgresSha256
Get-VerifiedArchive -Url $postgisUrl -Destination $postgisArchive -ExpectedSha256 $postgisSha256

New-Item -ItemType Directory -Force -Path $layout.RuntimeRoot | Out-Null
$postgresExecutable = Join-Path $layout.PostgreSqlRoot "bin\postgres.exe"
if (-not (Test-Path -LiteralPath $postgresExecutable -PathType Leaf)) {
    Invoke-CheckedNativeCommand -FilePath "tar.exe" -Arguments @(
        "-xf", $postgresArchive, "-C", $layout.RuntimeRoot
    ) -FailureMessage "The PostgreSQL archive could not be extracted."
}

$postgisControl = Join-Path $layout.PostgreSqlRoot "share\extension\postgis.control"
if (-not (Test-Path -LiteralPath $postgisControl -PathType Leaf)) {
    $postgisStage = Join-Path $layout.RuntimeRoot "postgis-stage"
    if (-not (Test-Path -LiteralPath $postgisStage)) {
        New-Item -ItemType Directory -Path $postgisStage | Out-Null
    }
    Invoke-CheckedNativeCommand -FilePath "tar.exe" -Arguments @(
        "-xf", $postgisArchive, "-C", $postgisStage
    ) -FailureMessage "The PostGIS archive could not be extracted."
    $postgisSource = Join-Path $postgisStage $postgisFolderName
    if (-not (Test-Path -LiteralPath (Join-Path $postgisSource "README.txt") -PathType Leaf)) {
        throw "The PostGIS archive did not have its expected directory structure."
    }
    Copy-Item -Path (Join-Path $postgisSource "*") -Destination $layout.PostgreSqlRoot -Recurse -Force
}

if (-not (Test-Path -LiteralPath $postgisControl -PathType Leaf)) {
    throw "PostGIS was not installed into the portable PostgreSQL tree."
}

$completedPostgisStage = Join-Path $layout.RuntimeRoot "postgis-stage"
if (Test-Path -LiteralPath $completedPostgisStage -PathType Container) {
    $resolvedStage = (Resolve-Path -LiteralPath $completedPostgisStage).Path
    $expectedStage = [IO.Path]::GetFullPath($completedPostgisStage)
    if ($resolvedStage -ne $expectedStage -or
        -not $resolvedStage.StartsWith($layout.RuntimeRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove an unexpected PostGIS staging path: $resolvedStage"
    }
    Remove-Item -LiteralPath $resolvedStage -Recurse -Force
}

$pgVersion = Join-Path $layout.DataRoot "PG_VERSION"
if (-not (Test-Path -LiteralPath $pgVersion -PathType Leaf)) {
    if (Test-Path -LiteralPath $layout.DataRoot) {
        if ((Get-ChildItem -LiteralPath $layout.DataRoot -Force | Measure-Object).Count -ne 0) {
            throw "The portable data directory exists but is neither initialized nor empty: $($layout.DataRoot)"
        }
    } else {
        New-Item -ItemType Directory -Path $layout.DataRoot | Out-Null
    }

    $passwordFile = Join-Path $layout.RuntimeRoot "initdb-password.tmp"
    try {
        [IO.File]::WriteAllText(
            $passwordFile,
            $databasePassword + [Environment]::NewLine,
            [Text.UTF8Encoding]::new($false)
        )
        Invoke-CheckedNativeCommand -FilePath (Join-Path $layout.PostgreSqlRoot "bin\initdb.exe") -Arguments @(
            "--pgdata=$($layout.DataRoot)", "--username=postgres", "--encoding=UTF8", "--locale=C",
            "--auth-local=trust", "--auth-host=scram-sha-256", "--pwfile=$passwordFile"
        ) -FailureMessage "The portable PostgreSQL cluster could not be initialized."
    } finally {
        if (Test-Path -LiteralPath $passwordFile) {
            Remove-Item -LiteralPath $passwordFile -Force
        }
    }

    Add-Content -LiteralPath (Join-Path $layout.DataRoot "postgresql.conf") -Value @"

# TaxiMobile workspace-local runtime. The launcher also repeats these values.
listen_addresses = '127.0.0.1'
port = $Port
password_encryption = 'scram-sha-256'
"@
}

$startedForSetup = Start-PortablePostgres -Layout $layout -Port $Port
$previousPgPassword = $env:PGPASSWORD
try {
    $env:PGPASSWORD = $databasePassword
    $psql = Join-Path $layout.PostgreSqlRoot "bin\psql.exe"
    $bootstrapSql = @"
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', '$databaseUser', '$databasePassword')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$databaseUser') \gexec
SELECT format('ALTER ROLE %I LOGIN PASSWORD %L', '$databaseUser', '$databasePassword') \gexec
SELECT format('CREATE DATABASE %I OWNER %I', '$databaseName', '$databaseUser')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$databaseName') \gexec
SELECT format('CREATE DATABASE %I OWNER %I', 'taximobile_ci', '$databaseUser')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'taximobile_ci') \gexec
"@
    $bootstrapSql | & $psql --host=127.0.0.1 --port=$Port --username=postgres --dbname=postgres --no-password --set=ON_ERROR_STOP=1 --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "The application roles and databases could not be created."
    }

    foreach ($targetDatabase in @($databaseName, "taximobile_ci")) {
        "CREATE EXTENSION IF NOT EXISTS postgis;" | & $psql --host=127.0.0.1 --port=$Port --username=postgres --dbname=$targetDatabase --no-password --set=ON_ERROR_STOP=1 --quiet
        if ($LASTEXITCODE -ne 0) {
            throw "PostGIS could not be enabled in $targetDatabase."
        }
    }
} finally {
    $env:PGPASSWORD = $previousPgPassword
    if ($startedForSetup) {
        Stop-PortablePostgres -Layout $layout | Out-Null
    }
}

Write-Output "Portable PostgreSQL 16.14 and PostGIS 3.5.3 are ready under $($layout.RuntimeRoot)."
Write-Output "No system software or global configuration was changed."
