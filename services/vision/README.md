# SyncCart Vision Worker

The Vision Worker is SyncCart's retail-edge service. It consumes CCTV/IP-camera/NVR, HTTP/MJPEG, webcam, or recorded-video streams and converts stable shelf observations into `VISION_PICKUP` / `VISION_RETURN` events.

Phone 1 is the hackathon camera profile; a retail installation uses fixed CCTV or an NVR/VMS stream through the same adapter.

## Supported sources

- RTSP / RTSPS CCTV streams;
- NVR/VMS RTSP channels;
- HTTP/MJPEG, including Phone 1 IP Webcam;
- webcam indexes;
- recorded video files.

## Detector profiles

### AUTO — default

`DETECTOR_MODE=AUTO` selects the optional YOLO profile when a weight file is present and otherwise activates the built-in fixed-zone reference detector.

### Fixed-zone reference detector

Designed for the calibrated hackathon shelf. It learns the occupied appearance of each configured SKU zone and reports presence/absence changes through the same planogram + stabilizer path used by YOLO.

### YOLO

For custom appearance-based SKU detection:

```powershell
pip install -e ".\services\vision[yolo]"
```

Then provide:

```text
models/weights/synccart-sku-v001.pt
```

## Configure CCTV

```dotenv
CAMERA_ID=STORE-042-AISLE-04-CAM-01
CAMERA_SOURCE_NAME=Aisle 4 Shelf Camera
CAMERA_STREAM_MODE=RTSP
CAMERA_BACKEND=FFMPEG
CAMERA_BUFFER_SIZE=1
CAMERA_SOURCE=rtsp://USER:PASSWORD@CAMERA_IP:554/STREAM_PATH
DETECTOR_MODE=AUTO
```

Keep camera credentials in `.env` or deployment secrets. Diagnostics redact URL credentials.

## Configure Phone 1

```dotenv
CAMERA_ID=PHONE-1-SHELF-CAM
CAMERA_SOURCE_NAME=Phone 1 IP Webcam
CAMERA_STREAM_MODE=HTTP_MJPEG
CAMERA_BACKEND=AUTO
CAMERA_SOURCE=http://PHONE_IP:8080/video
DETECTOR_MODE=AUTO
```

## Probe

```powershell
python scripts\probe_camera_source.py --source "<CAMERA_STREAM>"
```

## Start

```powershell
.\scripts\run_vision_windows.ps1
```

Open:

```text
http://127.0.0.1:8100/health/ready
http://127.0.0.1:8100/metrics
http://127.0.0.1:8100/snapshot.jpg
http://127.0.0.1:8100/preview.mjpeg
```

## Safe event emission

The worker defaults to `VISION_EVENTS_ARMED=false`. Arming resets the count stabilizer and requires a fresh shelf baseline before physical events are published.

## Optional custom-model lifecycle

```powershell
python scripts\capture_vision_dataset.py --source "<CAMERA_STREAM>" --session session-01 --scenario full-shelf
python ml\dataops\prepare_yolo_dataset.py --source runtime\annotated-pool --output ml\datasets\demo_sku --clean
python ml\dataops\validate_yolo_dataset.py --data ml\datasets\demo_sku\dataset.yaml --fail-on-invalid
python ml\training\train_yolo.py --device cpu
```

See `docs/vision/` for CCTV deployment, camera contracts, data workflow, and commissioning.
