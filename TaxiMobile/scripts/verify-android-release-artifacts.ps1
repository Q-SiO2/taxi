[CmdletBinding()]
param(
    [Parameter()]
    [ValidateRange(1, 2147483647)]
    [int]$ExpectedVersionCode = 1,

    [Parameter()]
    [ValidatePattern('^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))?$')]
    [string]$ExpectedVersionName = "1.0.0",

    [Parameter()]
    [string]$ManifestPath,
    [string]$Aapt2Path,
    [string]$ReleaseBuildLogPath,
    [string]$ExpectedPassengerCertificateSha256,
    [string]$ExpectedDriverCertificateSha256,
    [string]$ApkSignerJarPath
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$signatureInputsRequested = @("ExpectedPassengerCertificateSha256", "ExpectedDriverCertificateSha256", "ApkSignerJarPath") |
    Where-Object { $PSBoundParameters.ContainsKey($_) }
if ($signatureInputsRequested -and (
    [string]::IsNullOrWhiteSpace($ExpectedPassengerCertificateSha256) -or
    [string]::IsNullOrWhiteSpace($ExpectedDriverCertificateSha256)
)) {
    throw "Signature inspection requires nonempty expected certificate fingerprints for both roles."
}

$pythonCommand = Get-Command python -ErrorAction Stop
$arguments = @(
    (Join-Path $PSScriptRoot "generate_android_verification_manifest.py"),
    "--project-dir", $projectRoot,
    "--expected-version-code", $ExpectedVersionCode.ToString(),
    "--expected-version-name", $ExpectedVersionName
)
if (-not [string]::IsNullOrWhiteSpace($ManifestPath)) {
    $arguments += @("--output", $ManifestPath)
}
if (-not [string]::IsNullOrWhiteSpace($Aapt2Path)) {
    $arguments += @("--aapt2", $Aapt2Path)
}
if (-not [string]::IsNullOrWhiteSpace($ReleaseBuildLogPath)) {
    $arguments += @("--build-log", $ReleaseBuildLogPath)
}
foreach ($pair in @(
    @("--expected-passenger-certificate-sha256", $ExpectedPassengerCertificateSha256),
    @("--expected-driver-certificate-sha256", $ExpectedDriverCertificateSha256),
    @("--apksigner-jar", $ApkSignerJarPath)
)) {
    if (-not [string]::IsNullOrWhiteSpace($pair[1])) {
        $arguments += @($pair[0], $pair[1])
    }
}
& $pythonCommand.Source @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Android artifact verification failed; no accepted distribution manifest was produced."
}
