[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_portable-common.ps1")

$layout = Get-TaxiMobileWorkspaceLayout
$version = "3.12.10"
$archiveName = "python-$version-embed-amd64.zip"
$archiveUrl = "https://www.python.org/ftp/python/$version/$archiveName"
# Published in Python.org's Sigstore bundle for this exact archive.
$archiveSha256 = "4ACBED6DD1C744B0376E3B1CF57CE906F9DC9E95E68824584C8099A63025A3C3"
$downloadRoot = Join-Path $layout.WorkspaceRoot ".tools\python312-downloads"
$archivePath = Join-Path $downloadRoot $archiveName
$runtimeRoot = Join-Path $layout.WorkspaceRoot ".tools\python312"
$python = Join-Path $runtimeRoot "python.exe"
$pathConfiguration = Join-Path $runtimeRoot "python312._pth"
$sitePackages = Join-Path $runtimeRoot "Lib\site-packages"
$requirements = Join-Path $layout.BackendRoot "requirements.lock"
$installerPython = Join-Path $layout.BackendRoot ".venv\Scripts\python.exe"
$markerPath = Join-Path $runtimeRoot ".taximobile-runtime.json"

if (-not (Test-Path -LiteralPath $requirements -PathType Leaf)) {
    throw "The pinned backend requirements file is missing: $requirements"
}
if (-not (Test-Path -LiteralPath $installerPython -PathType Leaf)) {
    throw "Create backend/.venv first; its pip installs target-specific pinned wheels into the portable runtime."
}

New-Item -ItemType Directory -Force -Path $downloadRoot | Out-Null
if (Test-Path -LiteralPath $archivePath -PathType Leaf) {
    $actualHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash
    if ($actualHash -ne $archiveSha256) {
        throw "The existing Python archive has an unexpected checksum and was not overwritten: $archivePath"
    }
} else {
    $temporaryPath = "$archivePath.download"
    if (Test-Path -LiteralPath $temporaryPath) {
        throw "An incomplete Python download already exists. Remove it after confirming its path, then retry: $temporaryPath"
    }
    try {
        $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
        if ($null -ne $curl) {
            Invoke-CheckedNativeCommand -FilePath $curl.Source -Arguments @(
                "--fail", "--location", "--retry", "3", "--output", $temporaryPath, $archiveUrl
            ) -FailureMessage "The Python archive could not be downloaded."
        } else {
            Invoke-WebRequest -Uri $archiveUrl -OutFile $temporaryPath -UseBasicParsing
        }
        if ((Get-FileHash -LiteralPath $temporaryPath -Algorithm SHA256).Hash -ne $archiveSha256) {
            throw "The downloaded Python archive checksum did not match the pinned value."
        }
        Move-Item -LiteralPath $temporaryPath -Destination $archivePath
    } catch {
        if (Test-Path -LiteralPath $temporaryPath) {
            Remove-Item -LiteralPath $temporaryPath -Force
        }
        throw
    }
}

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
    Invoke-CheckedNativeCommand -FilePath "tar.exe" -Arguments @(
        "-xf", $archivePath, "-C", $runtimeRoot
    ) -FailureMessage "The portable Python archive could not be extracted."
}

$runtimeVersion = (& $python --version 2>&1).ToString().Trim()
if ($LASTEXITCODE -ne 0 -or $runtimeVersion -ne "Python $version") {
    throw "The extracted runtime did not identify itself as Python $version."
}

$pathContents = @"
python312.zip
.
Lib\site-packages
..\..\backend\src

# Enable standard site initialization for the workspace-local wheel directory.
import site
"@
[IO.File]::WriteAllText($pathConfiguration, $pathContents, [Text.UTF8Encoding]::new($false))

$requirementsSha256 = (Get-FileHash -LiteralPath $requirements -Algorithm SHA256).Hash
$marker = $null
if (Test-Path -LiteralPath $markerPath -PathType Leaf) {
    try {
        $marker = Get-Content -LiteralPath $markerPath -Raw | ConvertFrom-Json
    } catch {
        $marker = $null
    }
}
$requiresInstall = $null -eq $marker -or
    $marker.pythonVersion -ne $version -or
    $marker.archiveSha256 -ne $archiveSha256 -or
    $marker.requirementsSha256 -ne $requirementsSha256

if ($requiresInstall) {
    $resolvedPython = (Resolve-Path -LiteralPath $python).Path
    $activeRuntimeProcesses = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
        try { $_.Path -eq $resolvedPython } catch { $false }
    })
    if ($activeRuntimeProcesses.Count -gt 0) {
        throw "Portable Python is currently running. Stop the portable stack before installing or updating its pinned wheels."
    }
    if (Test-Path -LiteralPath $sitePackages -PathType Container) {
        $resolvedSitePackages = (Resolve-Path -LiteralPath $sitePackages).Path
        $expectedSitePackages = [IO.Path]::GetFullPath($sitePackages)
        if ($resolvedSitePackages -ne $expectedSitePackages -or
            -not $resolvedSitePackages.StartsWith($runtimeRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to replace an unexpected package directory: $resolvedSitePackages"
        }
        Remove-Item -LiteralPath $resolvedSitePackages -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $sitePackages | Out-Null

    Invoke-CheckedNativeCommand -FilePath $installerPython -Arguments @(
        "-m", "pip", "install", "--disable-pip-version-check", "--no-input", "--require-hashes",
        "--requirement", $requirements, "--target", $sitePackages,
        "--platform", "win_amd64", "--python-version", "3.12",
        "--implementation", "cp", "--abi", "cp312", "--only-binary=:all:", "--no-deps"
    ) -FailureMessage "Pinned Python 3.12 runtime wheels could not be installed."

    @{
        pythonVersion = $version
        archiveSha256 = $archiveSha256
        requirementsSha256 = $requirementsSha256
    } | ConvertTo-Json | Set-Content -LiteralPath $markerPath -Encoding UTF8
}

Invoke-CheckedNativeCommand -FilePath $python -Arguments @(
    "-c", "import alembic, asyncpg, fastapi, httptools, sqlalchemy, taximobile_api, uvicorn"
) -FailureMessage "The portable Python runtime could not import TaxiMobile's pinned runtime dependencies."

Write-Output "Portable Python $version is ready under $runtimeRoot."
Write-Output "It is a loopback development/test runtime, not a production deployment artifact."
