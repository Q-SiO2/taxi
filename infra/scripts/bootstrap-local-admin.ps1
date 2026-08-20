[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateLength(3, 320)]
    [string]$Email
)

$ErrorActionPreference = "Stop"

$infraRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$composeFile = Join-Path $infraRoot "compose.yaml"
$environmentFile = Join-Path $infraRoot ".env"

if (-not (Test-Path -LiteralPath $environmentFile)) {
    throw "Create infra/.env with .\scripts\new-local-env.ps1 before bootstrapping an administrator."
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is required for the documented local administrator bootstrap."
}

& docker compose --env-file $environmentFile -f $composeFile exec api `
    python -m taximobile_api.cli.bootstrap_admin `
    --email $Email `
    --confirm-initial-admin

if ($LASTEXITCODE -ne 0) {
    throw "The initial administrator was not created. Review the safe command error above."
}
