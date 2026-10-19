$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Error "Root virtual environment not found. Create it with: py -3.12 -m venv .venv"
}

. .\.venv\Scripts\Activate.ps1

Write-Host "Starting SyncCart Vision Worker on http://0.0.0.0:8100" -ForegroundColor Cyan
Write-Host "Camera source: $env:CAMERA_SOURCE_NAME ($env:CAMERA_STREAM_MODE)" -ForegroundColor DarkGray

uvicorn synccart_vision.main:app `
    --app-dir services/vision `
    --host 0.0.0.0 `
    --port 8100
