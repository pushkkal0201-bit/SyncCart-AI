param(
    [switch]$SkipVision
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path ".").Path

if (-not (Test-Path "$Root\.venv\Scripts\Activate.ps1")) {
    Write-Error "Missing .venv. Create it with: py -3.12 -m venv .venv"
}
if (-not (Test-Path "$Root\.env")) {
    Write-Error "Missing .env. Create it with: Copy-Item .env.example .env"
}
if (-not (Test-Path "$Root\node_modules")) {
    Write-Warning "node_modules is missing. Run npm install before starting the three frontend apps."
}

function Start-SyncCartWindow {
    param(
        [string]$Title,
        [string]$Command
    )
    $escapedRoot = $Root.Replace("'", "''")
    $full = "Set-Location '$escapedRoot'; `$Host.UI.RawUI.WindowTitle='$Title'; Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass; . .\.venv\Scripts\Activate.ps1; $Command"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $full
}

Start-SyncCartWindow "SyncCart Core API :8000" "uvicorn app.main:app --app-dir services/api --host 0.0.0.0 --port 8000 --reload"
Start-Sleep -Milliseconds 700
Start-SyncCartWindow "SyncCart Customer :5173" "npm run dev:customer"
Start-SyncCartWindow "SyncCart Retailer :5174" "npm run dev:retailer"
Start-SyncCartWindow "SyncCart Monitoring :5175" "npm run dev:monitoring"

if (-not $SkipVision) {
    Start-SyncCartWindow "SyncCart Vision :8100" "uvicorn synccart_vision.main:app --app-dir services/vision --host 0.0.0.0 --port 8100"
}

Write-Host "SyncCart windows launched." -ForegroundColor Green
Write-Host "Core API:     http://127.0.0.1:8000/docs"
Write-Host "Customer:     http://127.0.0.1:5173"
Write-Host "Retailer:     http://127.0.0.1:5174"
Write-Host "Monitoring:   http://127.0.0.1:5175"
if (-not $SkipVision) {
    Write-Host "Vision:       http://127.0.0.1:8100/health/ready"
    Write-Host "Vision feed:  http://127.0.0.1:8100/preview.mjpeg"
}
