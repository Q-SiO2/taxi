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
    [string]$Aapt2Path
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

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
& $pythonCommand.Source @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Android artifact verification failed; no accepted distribution manifest was produced."
}
