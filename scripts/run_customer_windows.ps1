$ErrorActionPreference = "Stop"

Write-Host "Starting SyncCart Customer PWA on 0.0.0.0:5173" -ForegroundColor Cyan
Write-Host "Open it on Phone 2 using: http://<LAPTOP_IPV4>:5173" -ForegroundColor Yellow

npm run dev:customer
