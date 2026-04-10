$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$appRoot = Join-Path $projectRoot "delivery-kanban-poc"
$frontendDir = Join-Path $appRoot "frontend"
$envFile = Join-Path $frontendDir ".env"
$envExampleFile = Join-Path $frontendDir ".env.example"

Set-Location $frontendDir

if (-not (Test-Path $envFile) -and (Test-Path $envExampleFile)) {
    Copy-Item $envExampleFile $envFile
}

if (-not (Test-Path "node_modules")) {
    npm.cmd install
}

npm.cmd run dev
