# SyncCart AI Quick Start

## Windows

```powershell
py -3.13 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
pip install -e ".\services\vision"
npm install
Copy-Item .env.example .env
python scripts\seed_demo_catalog.py
powershell -ExecutionPolicy Bypass -File scripts\run_synccart_stack_windows.ps1
```

## Camera

For Phone 1:

```env
CAMERA_ID=PHONE-1-SHELF-CAM
CAMERA_SOURCE=https://PHONE-IP:8080/video
CAMERA_SOURCE_NAME=Phone 1 Shelf Camera
CAMERA_STREAM_MODE=MJPEG
DETECTOR_MODE=AUTO
```

For CCTV/NVR:

```env
CAMERA_ID=STORE-01-AISLE-04-CAM-01
CAMERA_SOURCE=rtsp://USER:PASSWORD@CAMERA_IP:554/STREAM_PATH
CAMERA_SOURCE_NAME=Aisle 4 Shelf Camera
CAMERA_STREAM_MODE=RTSP
CAMERA_BACKEND=FFMPEG
DETECTOR_MODE=AUTO
```

Probe any camera source:

```powershell
python scripts\probe_camera_source.py --source "YOUR_CAMERA_SOURCE"
```

Calibrate the shelf:

```powershell
python scripts\calibrate_planogram.py --source "YOUR_CAMERA_SOURCE" --display-width 900 --display-height 550
```

## URLs

- Core API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- Customer: `http://127.0.0.1:5173`
- Retailer: `http://127.0.0.1:5174`
- Monitoring: `http://127.0.0.1:5175`
- Vision: `http://127.0.0.1:8100`
- Vision preview: `http://127.0.0.1:8100/preview.mjpeg`
