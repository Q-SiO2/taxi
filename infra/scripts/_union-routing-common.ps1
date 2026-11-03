# Native GraphHopper is an optional local rehearsal path, not a production service.
. (Join-Path $PSScriptRoot "_union-demo-common.ps1")

function Resolve-UnionRoutingFile {
    param([string]$Root, [string]$Path)
    $resolved = [IO.Path]::GetFullPath($Path)
    $boundary = [IO.Path]::GetFullPath($Root).TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
    if (-not $resolved.StartsWith($boundary, [StringComparison]::OrdinalIgnoreCase) -or
        $resolved.Contains('"') -or -not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
        throw "Routing inputs must be existing files inside this demo's routing directory."
    }
    $cursor = $resolved
    while ($cursor -ne $Root) {
        if ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Routing input paths must not contain links."
        }
        $cursor = Split-Path -Parent $cursor
    }
    return $resolved
}

function ConvertTo-UnionRoutingConfig {
    param([string]$Source)
    # Keep the same reviewed engine/car profile as Docker. Only socket bindings
    # differ on the native host; never expose the container's wildcard listener.
    foreach ($replacement in @(
        @('port: 8989', 'port: 8002'),
        @('port: 8990', 'port: 8003'),
        @('bind_host: 0.0.0.0', 'bind_host: 127.0.0.1')
    )) {
        if ([regex]::Matches($Source, [regex]::Escape($replacement[0])).Count -ne 1) {
            throw "Reviewed routing socket configuration changed; inspect it before native launch."
        }
        $Source = $Source.Replace($replacement[0], $replacement[1])
    }
    return $Source
}

function Get-UnionRoutingProcess {
    param($State)
    $process = Get-Process -Id ([int]$State.pid) -ErrorAction SilentlyContinue
    if ($null -eq $process) { return $null }
    if ($process.Path -ne $State.executable -or
        $process.StartTime.ToUniversalTime().Ticks -ne [long]$State.startTimeUtcTicks) {
        throw "Routing process ownership changed; it was not adopted or stopped."
    }
    $command = Get-CimInstance Win32_Process -Filter "ProcessId = $($process.Id)"
    if (-not $command.CommandLine.Contains('"' + $State.jar + '"') -or
        -not $command.CommandLine.Contains('"' + $State.config + '"') -or
        -not $command.CommandLine.Contains('"-Ddw.graphhopper.graph.location=' + $State.graph + '"')) {
        throw "Routing command does not match its recorded graph and configuration."
    }
    return $process
}
