@echo off
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\activate.bat" (
  echo [SyncCart] Missing .venv. Create it first with: py -3.13 -m venv .venv
  exit /b 1
)

if not exist ".env" (
  echo [SyncCart] Missing .env. Copy .env.example to .env and set camera / API keys.
  exit /b 1
)

if not exist "node_modules" (
  echo [SyncCart] node_modules missing. Run: npm install
  exit /b 1
)

start "SyncCart Core API :8000" cmd /k "cd /d %CD% && call .venv\Scripts\activate.bat && uvicorn app.main:app --app-dir services/api --host 0.0.0.0 --port 8000"
timeout /t 1 /nobreak >nul
start "SyncCart Customer :5173" cmd /k "cd /d %CD% && npm run dev:customer"
start "SyncCart Retailer :5174" cmd /k "cd /d %CD% && npm run dev:retailer"
start "SyncCart Monitoring :5175" cmd /k "cd /d %CD% && npm run dev:monitoring"
start "SyncCart Vision :8100" cmd /k "cd /d %CD% && call .venv\Scripts\activate.bat && uvicorn synccart_vision.main:app --app-dir services/vision --host 0.0.0.0 --port 8100"

echo.
echo SyncCart v1.0 launch windows opened.
echo Core API:     http://127.0.0.1:8000/docs
echo Customer:     http://127.0.0.1:5173
echo Retailer:     http://127.0.0.1:5174
echo Monitoring:   http://127.0.0.1:5175
echo Vision:       http://127.0.0.1:8100/health/ready
echo Vision feed:  http://127.0.0.1:8100/preview.mjpeg
endlocal
