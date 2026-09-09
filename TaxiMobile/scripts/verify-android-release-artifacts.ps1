[CmdletBinding()]
param(
    [Parameter()]
    [ValidateRange(1, 2147483647)]
    [int]$ExpectedVersionCode = 1,

    [Parameter()]
    [ValidatePattern('^[0-9]+(\.[0-9]+){1,3}([+-][A-Za-z0-9.-]+)?$')]
    [string]$ExpectedVersionName = "1.0.0"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$variants = @(
    @{ Role = "passenger"; Variant = "passengerRelease"; ApplicationId = "ma.taximobile.passenger" },
    @{ Role = "driver"; Variant = "driverRelease"; ApplicationId = "ma.taximobile.driver" }
)
$seenFiles = @()
foreach ($variant in $variants) {
    $outputDirectory = Join-Path $projectRoot "androidApp\build\outputs\apk\$($variant.Role)\release"
    $metadataPath = Join-Path $outputDirectory "output-metadata.json"
    if (-not (Test-Path -LiteralPath $metadataPath -PathType Leaf)) {
        throw "Missing release metadata for $($variant.Role)."
    }
    $metadata = Get-Content -LiteralPath $metadataPath -Raw | ConvertFrom-Json
    if ($metadata.applicationId -ne $variant.ApplicationId -or $metadata.variantName -ne $variant.Variant) {
        throw "Unexpected package or variant identity for $($variant.Role)."
    }
    if ($metadata.elements.Count -ne 1) {
        throw "Expected exactly one universal $($variant.Role) release APK."
    }
    $element = $metadata.elements[0]
    if ($element.versionCode -ne $ExpectedVersionCode -or $element.versionName -ne $ExpectedVersionName) {
        throw "Unexpected version metadata for $($variant.Role)."
    }
    $apkPath = Join-Path $outputDirectory $element.outputFile
    $apk = Get-Item -LiteralPath $apkPath -ErrorAction Stop
    if ($apk.Length -lt 1MB) {
        throw "The $($variant.Role) release APK is unexpectedly small."
    }
    $seenFiles += $apk.FullName
}
if ($seenFiles[0] -eq $seenFiles[1]) {
    throw "Passenger and driver release outputs must be distinct artifacts."
}

Write-Output "Verified distinct passenger and driver release APK identities, versions, and files."
