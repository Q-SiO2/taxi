[CmdletBinding()]
param([Parameter(Mandatory)] [string]$DemoId)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_union-demo-common.ps1")
$layout = Get-TaxiMobileWorkspaceLayout
$root = Resolve-UnionDemoRoot -Layout $layout -DemoId $DemoId
$lock = [IO.File]::Open((Join-Path $root "launch.lock"), [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
try {
    $state = Read-UnionDemoState -Layout $layout -DemoId $DemoId
    $process = Get-UnionDemoApiProcess -Layout $layout -State $state
    if ($null -ne $process) {
        $children = @(Get-UnionDemoApiChildProcesses -Layout $layout -State $state -RootProcess $process)
        foreach ($child in $children) {
            Stop-Process -Id $child.Id -ErrorAction Stop
            if (-not $child.WaitForExit(10000)) { throw "Owned demo API child has not exited; state was preserved." }
        }
        $process.Refresh()
        if (-not $process.HasExited) { Stop-Process -Id $process.Id -ErrorAction Stop }
        if (-not $process.WaitForExit(10000)) { throw "Demo API launcher has not exited; its state was preserved." }
    }
    $state.api = $null
    $state.phase = "STOPPED"
    $state | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $root "state.json") -Encoding UTF8
    Write-Output "Stopped only this demo API. PostgreSQL, all databases, login files and logs were preserved."
} finally { $lock.Dispose() }
