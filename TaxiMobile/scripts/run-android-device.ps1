[CmdletBinding()]
param(
    [Parameter()]
    [ValidateSet("passenger", "driver")]
    [string]$Role = "passenger",

    [Parameter()]
    [ValidateRange(1, 65535)]
    [int]$ApiPort = 8000,

    [Parameter()]
    [string]$MapStyleUrl = "https://tiles.openfreemap.org/styles/positron",

    [Parameter()]
    [ValidateRange(10, 300)]
    [int]$DeviceReconnectTimeoutSeconds = 120,

    [Parameter()]
    [switch]$RegistrationSmoke,

    [Parameter()]
    [switch]$ConfirmClearAppData,

    [Parameter()]
    [string]$EvidencePath
)

$ErrorActionPreference = "Stop"

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Executable,

        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )

    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE`: $Executable $($Arguments -join ' ')"
    }
}

$mobileRoot = Split-Path -Parent $PSScriptRoot
$workspaceRoot = Split-Path -Parent $mobileRoot
$androidSdkRoot = Join-Path $workspaceRoot ".tools\android-sdk"
$adb = Join-Path $androidSdkRoot "platform-tools\adb.exe"
$gradle = Join-Path $mobileRoot "gradlew.bat"

if (-not (Test-Path -LiteralPath $adb -PathType Leaf)) {
    throw "Workspace Android platform tools are missing. Expected: $adb"
}
if (-not (Test-Path -LiteralPath $gradle -PathType Leaf)) {
    throw "Gradle wrapper is missing. Expected: $gradle"
}

$workspaceJdkRoot = Join-Path $workspaceRoot ".tools\jdk21"
$jdkHome = Get-ChildItem -LiteralPath $workspaceJdkRoot -Directory -ErrorAction SilentlyContinue |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "bin\java.exe") } |
    Select-Object -First 1 -ExpandProperty FullName
if (-not $jdkHome) {
    throw "Workspace JDK 21 is missing under $workspaceJdkRoot."
}

$readyUrl = "http://127.0.0.1:$ApiPort/ready"
try {
    $ready = Invoke-RestMethod -Uri $readyUrl -TimeoutSec 5
} catch {
    throw "TaxiMobile API is not ready at $readyUrl. Start the local backend before launching the phone app."
}
if ($ready.status -ne "ready") {
    throw "TaxiMobile API or PostGIS is not ready at $readyUrl."
}
if ($RegistrationSmoke -and -not $ConfirmClearAppData) {
    throw "RegistrationSmoke clears the selected debug app's local data. Re-run with ConfirmClearAppData after review."
}
if ($EvidencePath -and -not $RegistrationSmoke) {
    throw "EvidencePath requires RegistrationSmoke because launch alone is not acceptance evidence."
}
if ($EvidencePath) {
    $resolvedEvidencePath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($EvidencePath)
    if (Test-Path -LiteralPath $resolvedEvidencePath) {
        throw "Android acceptance refuses to overwrite existing evidence: $resolvedEvidencePath"
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resolvedEvidencePath) | Out-Null
}

$deviceLines = & $adb devices
if ($LASTEXITCODE -ne 0) {
    throw "ADB could not enumerate devices."
}
$connectedDevices = @(
    $deviceLines |
        Select-Object -Skip 1 |
        Where-Object { $_ -match "^\S+\s+device(?:\s|$)" } |
        ForEach-Object { ($_ -split "\s+")[0] }
)
if ($connectedDevices.Count -ne 1) {
    throw "Connect exactly one authorized Android device. Found $($connectedDevices.Count)."
}

Invoke-CheckedCommand $adb reverse "tcp:$ApiPort" "tcp:$ApiPort"
$reverseRules = & $adb reverse --list
if ($LASTEXITCODE -ne 0 -or -not ($reverseRules -match "tcp:$ApiPort\s+tcp:$ApiPort")) {
    throw "ADB reverse was not established for API port $ApiPort."
}

$env:JAVA_HOME = $jdkHome
$env:ANDROID_HOME = $androidSdkRoot
$env:ANDROID_SDK_ROOT = $androidSdkRoot
$env:GRADLE_USER_HOME = Join-Path $workspaceRoot ".tools\gradle-home"

$taskRole = (Get-Culture).TextInfo.ToTitleCase($Role)
$buildTask = ":androidApp:assemble${taskRole}Debug"
$apiBaseUrl = "http://127.0.0.1:$ApiPort"

Push-Location $mobileRoot
try {
    Invoke-CheckedCommand $gradle `
        "--no-daemon" `
        "--console=plain" `
        "-PtaximobileDebugApiBaseUrl=$apiBaseUrl" `
        "-PtaximobileDebugMapStyleUrl=$MapStyleUrl" `
        $buildTask
} finally {
    Pop-Location
}

# A phone can briefly reset its USB/ADB transport during a long debug build.
# Preserve the originally authorized serial, wait for only that device, and
# restore the reverse rule before installation. Never switch to another device.
$reconnectDeadline = (Get-Date).AddSeconds($DeviceReconnectTimeoutSeconds)
do {
    $currentDeviceLines = & $adb devices
    if ($LASTEXITCODE -ne 0) {
        throw "ADB could not re-check the selected device after the build."
    }
    $currentDevices = @(
        $currentDeviceLines |
            Select-Object -Skip 1 |
            Where-Object { $_ -match "^\S+\s+device(?:\s|$)" } |
            ForEach-Object { ($_ -split "\s+")[0] }
    )
    if ($currentDevices.Count -eq 1 -and $currentDevices[0] -eq $connectedDevices[0]) {
        break
    }
    if ($currentDevices.Count -gt 0 -and $currentDevices[0] -ne $connectedDevices[0]) {
        throw "The originally selected Android device was replaced during the build. Refusing to install on another device."
    }
    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $reconnectDeadline)

if ($currentDevices.Count -ne 1 -or $currentDevices[0] -ne $connectedDevices[0]) {
    throw "Android device $($connectedDevices[0]) did not reconnect within $DeviceReconnectTimeoutSeconds seconds. The APK was built but not installed."
}

Invoke-CheckedCommand $adb reverse "tcp:$ApiPort" "tcp:$ApiPort"

$apk = Join-Path $mobileRoot "androidApp\build\outputs\apk\$Role\debug\androidApp-$Role-debug.apk"
if (-not (Test-Path -LiteralPath $apk -PathType Leaf)) {
    throw "The expected APK was not produced: $apk"
}

Invoke-CheckedCommand $adb install -r $apk

$packageName = "ma.taximobile.$Role"
$activityName = "org.example.taximobile.MainActivity"
if ($RegistrationSmoke) {
    Invoke-CheckedCommand $adb shell pm clear $packageName
}
Invoke-CheckedCommand $adb shell am start -n "$packageName/$activityName"

Write-Host "TaxiMobile $Role is running on $($connectedDevices[0])."
Write-Host "API tunnel: device 127.0.0.1:$ApiPort -> development machine 127.0.0.1:$ApiPort"

if ($RegistrationSmoke) {
    $workspacePython = Join-Path $workspaceRoot ".tools\python312\python.exe"
    if (-not (Test-Path -LiteralPath $workspacePython -PathType Leaf)) {
        throw "The workspace Python runtime is required for Android acceptance: $workspacePython"
    }
    $smokeScript = Join-Path $PSScriptRoot "android_registration_smoke.py"
    $smokeArguments = @($smokeScript, "--adb", $adb, "--role", $Role)
    if ($EvidencePath) {
        $smokeArguments += @("--output", $resolvedEvidencePath)
    }
    Invoke-CheckedCommand $workspacePython @smokeArguments
}
