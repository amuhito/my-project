$ErrorActionPreference = "Stop"

$backendScript = Join-Path $PSScriptRoot "start-backend.ps1"
$frontendScript = Join-Path $PSScriptRoot "start-frontend.ps1"

Start-Process powershell -ArgumentList @(
    "-ExecutionPolicy",
    "Bypass",
    "-NoExit",
    "-File",
    $backendScript
)

Start-Process powershell -ArgumentList @(
    "-ExecutionPolicy",
    "Bypass",
    "-NoExit",
    "-File",
    $frontendScript
)
