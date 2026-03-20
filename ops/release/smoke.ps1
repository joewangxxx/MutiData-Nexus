param(
    [string]$ControllerBaseUrl = "http://127.0.0.1:8000",
    [string]$WebBaseUrl = "http://127.0.0.1:3000"
)

$ErrorActionPreference = 'Stop'

function Assert-Ok {
    param(
        [string]$BaseUrl,
        [string]$Path,
        [string]$ExpectedStatus
    )

    $response = Invoke-RestMethod -Method Get -Uri "$BaseUrl$Path"
    if ($response.data.status -ne $ExpectedStatus) {
        throw "Expected $Path to report '$ExpectedStatus' but got '$($response.data.status)'."
    }
}

function Assert-WebOk {
    param(
        [string]$Path,
        [string]$ExpectedStatus
    )

    $response = Invoke-RestMethod -Method Get -Uri "$WebBaseUrl$Path"
    if ($response.status -ne $ExpectedStatus) {
        throw "Expected $Path to report '$ExpectedStatus' but got '$($response.status)'."
    }
}

Assert-Ok -BaseUrl $ControllerBaseUrl -Path "/api/v1/ops/healthz" -ExpectedStatus "ok"
Assert-Ok -BaseUrl $ControllerBaseUrl -Path "/api/v1/ops/readyz" -ExpectedStatus "ok"
Assert-WebOk -Path "/healthz" -ExpectedStatus "ok"
Assert-WebOk -Path "/readyz" -ExpectedStatus "ready"

Write-Host "Release smoke checks passed."
