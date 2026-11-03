# Local rehearsal helpers. Never accept an arbitrary database or runtime path.
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_portable-common.ps1")

function Resolve-UnionDemoRoot {
    param([hashtable]$Layout, [string]$DemoId)
    if ($DemoId -cnotmatch '^[a-f0-9]{32}$') {
        throw "DemoId must be the exact 32-character ID printed by the demo launcher."
    }
    $root = [IO.Path]::GetFullPath((Join-Path $Layout.WorkspaceRoot ".tools\union-demo\$DemoId"))
    $boundary = [IO.Path]::GetFullPath($Layout.WorkspaceRoot) + [IO.Path]::DirectorySeparatorChar
    if (-not $root.StartsWith($boundary, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Demo runtime is outside this workspace."
    }
    $cursor = $root
    while ($cursor -ne $Layout.WorkspaceRoot) {
        if (Test-Path -LiteralPath $cursor) {
            $item = Get-Item -LiteralPath $cursor -Force
            if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
                throw "Demo runtime ancestors must be real directories, not links."
            }
        }
        $cursor = Split-Path -Parent $cursor
    }
    return $root
}

function Protect-UnionDemoRoot {
    param([string]$Root)
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent().User
    $directory = [IO.DirectoryInfo]::new($Root)
    # Read/write the discretionary ACL only, not SACL/owner sections that may
    # require SeSecurityPrivilege. No elevation or audit-policy change is needed.
    $acl = [IO.FileSystemAclExtensions]::GetAccessControl(
        $directory, [Security.AccessControl.AccessControlSections]::Access
    )
    $acl.SetAccessRuleProtection($true, $false)
    # Only the current Windows account can read child login/configuration files.
    foreach ($rule in $acl.GetAccessRules($true, $false, [Security.Principal.SecurityIdentifier])) {
        $acl.RemoveAccessRuleSpecific($rule)
    }
    $rule = [Security.AccessControl.FileSystemAccessRule]::new(
        $identity, "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow"
    )
    $acl.AddAccessRule($rule)
    [IO.FileSystemAclExtensions]::SetAccessControl($directory, $acl)
    $confirmed = Get-Acl -LiteralPath $Root
    if (-not $confirmed.AreAccessRulesProtected) { throw "Demo directory ACL was not protected." }
    foreach ($entry in $confirmed.Access) {
        if ($entry.AccessControlType -eq "Allow" -and
            $entry.IdentityReference.Translate([Security.Principal.SecurityIdentifier]) -ne $identity) {
            throw "Demo directory has an unexpected reader."
        }
    }
}

function Read-UnionDemoState {
    param([hashtable]$Layout, [string]$DemoId)
    $root = Resolve-UnionDemoRoot -Layout $Layout -DemoId $DemoId
    $statePath = Join-Path $root "state.json"
    if (-not (Test-Path -LiteralPath $statePath -PathType Leaf)) {
        throw "No recorded demo exists for this ID. Nothing was created or reset."
    }
    if ((Get-Item -LiteralPath $statePath).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "Demo state must not be a link."
    }
    $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    if ($state.schema -ne 1 -or $state.demoId -ne $DemoId -or
        $state.database -ne "taximobile_union_demo_$DemoId" -or
        $state.apiPort -lt 1024 -or $state.apiPort -gt 65535 -or
        $state.databasePort -lt 1024 -or $state.databasePort -gt 65535 -or
        $state.jwtSecret -cnotmatch '^[a-f0-9]{64}$') {
        throw "Demo state is not a valid isolated local rehearsal record."
    }
    return $state
}

function Get-UnionDemoApiProcess {
    param([hashtable]$Layout, $State)
    if ($null -eq $State.api) { return $null }
    $process = Get-Process -Id ([int]$State.api.pid) -ErrorAction SilentlyContinue
    if ($null -eq $process) { return $null }
    $expected = (Resolve-Path -LiteralPath (Join-Path $Layout.BackendRoot ".venv\Scripts\python.exe")).Path
    if ($State.api.executable -ne $expected -or $process.Path -ne $expected -or
        $process.StartTime.ToUniversalTime().Ticks -ne [long]$State.api.startTimeUtcTicks) {
        throw "Saved demo API identity does not match the live process. It was not stopped or replaced."
    }
    return $process
}

function Resolve-UnionDemoRoutingProvider {
    param($State, [string]$Requested, [bool]$HasLiveApi)
    # Schema-1 records predating selectable routing used Valhalla exclusively.
    $recorded = "valhalla"
    if ($State.PSObject.Properties.Name -contains "routingProvider") {
        $recorded = [string]$State.routingProvider
    }
    if ($recorded -notin @("valhalla", "graphhopper")) { throw "Invalid recorded routing provider." }
    if ([string]::IsNullOrEmpty($Requested)) { return $recorded }
    if ($Requested -notin @("valhalla", "graphhopper")) { throw "Invalid requested routing provider." }
    if ($Requested -ne $recorded -and $HasLiveApi) {
        throw "Stop this exact demo API before explicitly changing its routing provider; no live retarget was performed."
    }
    return $Requested
}

function Get-UnionDemoApiChildProcesses {
    param([hashtable]$Layout, $State, $RootProcess)
    if ($null -eq $RootProcess) { return @() }
    # On Windows the venv executable is a launcher; CPython's actual listener
    # can be its direct child. Bind that child to the known parent's lifetime,
    # the venv's actual base interpreter and this exact loopback uvicorn command.
    $venvPython = Join-Path $Layout.BackendRoot ".venv\Scripts\python.exe"
    $basePython = & $venvPython -I -c "import sys; print(sys._base_executable)"
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $basePython -PathType Leaf)) {
        throw "Could not establish the venv's base interpreter identity."
    }
    $basePython = (Resolve-Path -LiteralPath $basePython).Path
    $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $($RootProcess.Id)")
    foreach ($child in $children) {
        if ($child.ExecutablePath -ne $basePython) { continue }
        $candidate = Get-Process -Id ([int]$child.ProcessId) -ErrorAction SilentlyContinue
        if ($null -eq $candidate) { continue }
        if ($candidate.StartTime.ToUniversalTime().Ticks -lt $RootProcess.StartTime.ToUniversalTime().Ticks -or
            $child.CommandLine -notmatch '(^|\s)-m\s+uvicorn\s+taximobile_api\.main:app(\s|$)' -or
            $child.CommandLine -notmatch '(^|\s)--host\s+127\.0\.0\.1(\s|$)' -or
            $child.CommandLine -notmatch "(^|\s)--port\s+$($State.apiPort)(\s|$)") {
            throw "A Python child does not match this demo API command; it was not adopted or stopped."
        }
        $candidate
    }
}
