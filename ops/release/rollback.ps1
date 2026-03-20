param(
    [string]$ComposeFile = "compose.release.yaml"
)

$ErrorActionPreference = 'Stop'

docker compose -f $ComposeFile down --remove-orphans
Write-Host "Release stack stopped."
