$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$appRoot = Join-Path $projectRoot "delivery-kanban-poc"
$backendDir = Join-Path $appRoot "backend"
$pythonExe = Join-Path $backendDir ".venv\Scripts\python.exe"

Set-Location $backendDir

if (-not (Test-Path $pythonExe)) {
    python -m venv .venv
}

& $pythonExe -m pip install -r requirements.txt
& $pythonExe -m uvicorn app.main:app --reload
