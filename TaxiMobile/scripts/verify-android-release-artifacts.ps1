[CmdletBinding()]
param(
    [Parameter()]
    [ValidateRange(1, 2147483647)]
    [int]$ExpectedVersionCode = 1,

    [Parameter()]
    [ValidatePattern('^[0-9]+(\.[0-9]+){1,3}([+-][A-Za-z0-9.-]+)?$')]
    [string]$ExpectedVersionName = "1.0.0",

    [Parameter()]
    [string]$ManifestPath
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$variants = @(
    @{ Role = "passenger"; Variant = "passengerRelease"; ApplicationId = "ma.taximobile.passenger" },
    @{ Role = "driver"; Variant = "driverRelease"; ApplicationId = "ma.taximobile.driver" }
)
$seenFiles = @()
$artifacts = @()
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
    $artifacts += [ordered]@{
        role = $variant.Role
        variant = $variant.Variant
        application_id = $variant.ApplicationId
        version_code = $element.versionCode
        version_name = $element.versionName
        path = [IO.Path]::GetRelativePath($projectRoot, $apk.FullName).Replace('\', '/')
        bytes = $apk.Length
        sha256 = (Get-FileHash -LiteralPath $apk.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}
if ($seenFiles[0] -eq $seenFiles[1]) {
    throw "Passenger and driver release outputs must be distinct artifacts."
}

if (-not [string]::IsNullOrWhiteSpace($ManifestPath)) {
    $resolvedManifestPath = if ([IO.Path]::IsPathRooted($ManifestPath)) {
        [IO.Path]::GetFullPath($ManifestPath)
    } else {
        [IO.Path]::GetFullPath((Join-Path (Get-Location).Path $ManifestPath))
    }
    if (Test-Path -LiteralPath $resolvedManifestPath) {
        throw "Refusing to overwrite existing Android verification manifest: $resolvedManifestPath"
    }
    $manifestDirectory = Split-Path -Parent $resolvedManifestPath
    if (-not (Test-Path -LiteralPath $manifestDirectory -PathType Container)) {
        New-Item -ItemType Directory -Path $manifestDirectory -Force | Out-Null
    }
    $manifest = [ordered]@{
        schema_version = 1
        generated_at = [DateTimeOffset]::UtcNow.ToString('o')
        evidence_level = 'ANDROID_VERIFICATION_ARTIFACTS'
        deployment_accepted = $false
        distribution_eligible = $false
        expected_version_code = $ExpectedVersionCode
        expected_version_name = $ExpectedVersionName
        limitations = @(
            'SIGNING_NOT_ACCEPTED'
            'PUSH_CRASH_PROVIDER_NOT_ACCEPTED'
            'PHYSICAL_DEVICE_NOT_ACCEPTED'
        )
        artifacts = $artifacts
    }
    $json = ($manifest | ConvertTo-Json -Depth 6) + "`n"
    [IO.File]::WriteAllText(
        $resolvedManifestPath,
        $json,
        [Text.UTF8Encoding]::new($false)
    )
    Write-Output "Wrote non-distributable Android verification manifest to $resolvedManifestPath."
}

Write-Output "Verified distinct passenger and driver release APK identities, versions, and files."
