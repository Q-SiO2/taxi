[CmdletBinding()]
param(
    [switch]$ConfirmSyntheticDemo,
    [Parameter(Mandatory)] [string]$DemoId,
    [Parameter(Mandatory)] [string]$JavaPath,
    [Parameter(Mandatory)] [string]$JarPath,
    [Parameter(Mandatory)] [string]$OsmPath,
    [Parameter(Mandatory)] [ValidatePattern('^[a-f0-9]{64}$')] [string]$OsmSha256
)
$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_union-routing-common.ps1")
if (-not $ConfirmSyntheticDemo) { throw "Use -ConfirmSyntheticDemo for native loopback routing." }
$layout = Get-TaxiMobileWorkspaceLayout
$demoRoot = Resolve-UnionDemoRoot -Layout $layout -DemoId $DemoId
$null = Read-UnionDemoState -Layout $layout -DemoId $DemoId
Protect-UnionDemoRoot -Root $demoRoot
$root = Join-Path $demoRoot "routing"
if (-not (Test-Path -LiteralPath $root -PathType Container) -or
    (Get-Item -LiteralPath $root -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw "Create a real routing directory inside the existing demo and download verified inputs there."
}
$jar = Resolve-UnionRoutingFile -Root $root -Path $JarPath
$osm = Resolve-UnionRoutingFile -Root $root -Path $OsmPath
$java = (Resolve-Path -LiteralPath $JavaPath).Path
if (-not (Test-Path -LiteralPath $java -PathType Leaf) -or
    [IO.Path]::GetFileName($java) -ne "java.exe" -or $java.Contains('"')) {
    throw "JavaPath must name an installed java.exe (Java 17 or later)."
}
$lock = [IO.File]::Open((Join-Path $root "routing.lock"), [IO.FileMode]::OpenOrCreate,
    [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
$priorEnvironment = @{}
try {
    # Do not let inherited JVM options expose the host or replace pinned inputs.
    foreach ($name in @("JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "_JAVA_OPTIONS")) {
        $priorEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
        [Environment]::SetEnvironmentVariable($name, $null, "Process")
    }
    $jarDigest = (Get-FileHash -LiteralPath $jar -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($jarDigest -ne "b59c024afe172ec6ec85b6327006c3138ec58c7d0bcd26253d0e42853f613def") {
        throw "GraphHopper 11.0 JAR checksum mismatch; no binary was executed."
    }
    if ((Get-FileHash -LiteralPath $osm -Algorithm SHA256).Hash.ToLowerInvariant() -ne $OsmSha256) {
        throw "OSM checksum mismatch; no graph was imported."
    }
    $version = (& $java -XshowSettings:properties -version 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0 -or $version -notmatch 'java\.specification\.version\s*=\s*(\d+)' -or
        [int]$Matches[1] -lt 17) { throw "GraphHopper 11.0 needs Java 17 or later." }
    $configText = ConvertTo-UnionRoutingConfig -Source (
        Get-Content -LiteralPath (Join-Path $layout.InfraRoot "routing\graphhopper\config.yml") -Raw
    )
    $configBytes = [Text.Encoding]::UTF8.GetBytes($configText)
    $configDigest = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($configBytes)).ToLowerInvariant()
    # Configuration identity joins engine + extract identity: changed profiles
    # cannot quietly load a graph prepared under a different configuration.
    $graph = Join-Path $root "graph-v11-$OsmSha256-$configDigest"
    $config = Join-Path $root "native-$configDigest.yml"
    if (Test-Path -LiteralPath $config) {
        $null = Resolve-UnionRoutingFile -Root $root -Path $config
        if ((Get-FileHash -LiteralPath $config -Algorithm SHA256).Hash.ToLowerInvariant() -ne $configDigest) {
            throw "Recorded native configuration was modified."
        }
    }
    $statePath = Join-Path $root "routing-state.json"
    if (Test-Path -LiteralPath $statePath) {
        $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        if ($state.schema -ne 1 -or $state.demoId -ne $DemoId) { throw "Invalid routing ownership record." }
        $live = Get-UnionRoutingProcess -State $state
        if ($null -ne $live) {
            if ($state.jar -ne $jar -or $state.executable -ne $java -or
                $state.graph -ne $graph -or $state.config -ne $config) {
                throw "A recorded routing import/server is live with different inputs. It was not retargeted."
            }
            $listeners = @(Get-NetTCPConnection -LocalPort 8002,8003 -State Listen -ErrorAction SilentlyContinue)
            if (@($listeners | Where-Object {
                $_.OwningProcess -ne $live.Id -or $_.LocalAddress -ne "127.0.0.1"
            }).Count) { throw "Routing sockets do not belong exclusively to the recorded loopback process." }
            Write-Output "The recorded GraphHopper process is still live; do not start a second import."
            Write-Output "Observe http://127.0.0.1:8002/info and this demo's routing logs. Live is not accepted."
            return
        }
    }
    $listeners = @(Get-NetTCPConnection -LocalPort 8002,8003 -State Listen -ErrorAction SilentlyContinue)
    if ($listeners.Count) { throw "Routing/admin port occupied; no existing service was stopped." }
    if (-not (Test-Path -LiteralPath $config)) { [IO.File]::WriteAllBytes($config, $configBytes) }
    if (Test-Path -LiteralPath $graph) {
        if ((Get-Item -LiteralPath $graph -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Graph cache must not be a link."
        }
    }
    $attempt = [guid]::NewGuid().ToString("N")
    $live = Start-Process -FilePath $java -ArgumentList @(
        "-Xms512m", "-Xmx3g", "-XX:ActiveProcessorCount=2",
        ('"-Ddw.graphhopper.datareader.file=' + $osm + '"'),
        ('"-Ddw.graphhopper.graph.location=' + $graph + '"'),
        "-jar", ('"' + $jar + '"'), "server", ('"' + $config + '"')
    ) -WorkingDirectory $root -WindowStyle Hidden -PassThru `
      -RedirectStandardOutput (Join-Path $root "graphhopper-$attempt.stdout.log") `
      -RedirectStandardError (Join-Path $root "graphhopper-$attempt.stderr.log")
    $state = [pscustomobject]@{
        schema = 1; demoId = $DemoId; provider = "graphhopper"; pid = $live.Id
        startTimeUtcTicks = $live.StartTime.ToUniversalTime().Ticks; executable = $java
        jar = $jar; config = $config; graph = $graph; osmSha256 = $OsmSha256
        jarSha256 = $jarDigest; configSha256 = $configDigest
    }
    $state | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statePath -Encoding UTF8
    Write-Output "Started the recorded GraphHopper import/server, bounded to 3 GiB heap and two JVM processors."
    Write-Output "This does not select or restart the demo API, or certify routing."
    Write-Output "Observe this demo's routing logs and http://127.0.0.1:8002/info, then run routing_acceptance."
} finally {
    foreach ($name in $priorEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($name, $priorEnvironment[$name], "Process")
    }
    $lock.Dispose()
}
