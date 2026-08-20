[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_portable-common.ps1")

$layout = Get-TaxiMobileWorkspaceLayout
$pidFile = Join-Path $layout.RuntimeRoot "api-process.json"
if (Test-Path -LiteralPath $pidFile -PathType Leaf) {
    $metadata = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
    try {
        $process = Get-Process -Id ([int]$metadata.pid) -ErrorAction Stop
        $allowedExecutables = @(
            (Join-Path $layout.BackendRoot ".venv\Scripts\python.exe"),
            (Join-Path $layout.WorkspaceRoot ".tools\python312\python.exe")
        ) | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | ForEach-Object {
            (Resolve-Path -LiteralPath $_).Path
        }
        $expectedPython = (Resolve-Path -LiteralPath ([string]$metadata.executable)).Path
        if ($expectedPython -notin $allowedExecutables) {
            throw "The saved API executable is outside the allowed workspace runtimes. It was not stopped."
        }
        if ($process.Path -ne $expectedPython -or $process.StartTime.ToUniversalTime().Ticks -ne [long]$metadata.startTimeUtcTicks) {
            throw "The saved API process identity no longer matches its process ID. It was not stopped."
        }
        Stop-Process -Id $process.Id
        $null = $process.WaitForExit(10000)
        Write-Output "Stopped the TaxiMobile API process."
    } catch [Microsoft.PowerShell.Commands.ProcessCommandException] {
        Write-Output "The saved TaxiMobile API process is no longer running."
    }
    Remove-Item -LiteralPath $pidFile -Force
} else {
    Write-Output "The portable TaxiMobile API is not recorded as running."
}

if (Stop-PortablePostgres -Layout $layout) {
    Write-Output "Stopped portable PostgreSQL."
} else {
    Write-Output "Portable PostgreSQL is not running."
}
