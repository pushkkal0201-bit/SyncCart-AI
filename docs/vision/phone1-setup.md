# Phone 1 Live Shelf-Camera Setup (Hackathon Camera Profile)

> **Deployment note:** retail stores use fixed CCTV/IP cameras or NVR/VMS streams. Phone 1 is the portable camera source used in the hackathon. See [`cctv-production-deployment.md`](cctv-production-deployment.md).

Phase 5 turns Phone 1 into the live shelf-camera source while the laptop runs the edge Vision service.

## Network

Keep Phone 1, Phone 2, and the laptop on the same Wi-Fi or hotspot. The Vision service itself does not require public internet once dependencies and model weights are installed.

## Camera source

Use any phone-camera application capable of exposing an MJPEG, HTTP video, or RTSP URL that OpenCV can read. A typical camera application may provide a URL resembling:

```text
http://192.168.1.23:8080/video
```

or:

```text
rtsp://192.168.1.23:8554/live
```

The exact path depends on the phone-camera application. Do not assume a URL until the app shows it.

Set the root `.env`:

```env
CAMERA_SOURCE=http://PHONE-IP:PORT/video
CAMERA_ID=PHONE-1-SHELF-CAM
CAMERA_SOURCE_NAME=Phone 1 Shelf Camera
CAMERA_STREAM_MODE=MJPEG
```

For initial laptop-only validation, `CAMERA_SOURCE=0` uses the laptop webcam.

## Fixed mounting

Phone 1 must remain fixed during a shopping session. Avoid handheld movement. Mount it so all configured shelf zones remain visible and avoid severe glare.

## Planogram calibration

Edit `config/vision_planogram.yaml`. Each rectangle is normalized to the camera image:

```text
[x1, y1, x2, y2]
```

where all coordinates range from `0.0` to `1.0`.

The controlled shelf profile assigns one SKU family to each shelf zone. This is intentional. The release intentionally binds one configured SKU to each calibrated shelf zone and blocks ambiguous shopper attribution.

## Why the worker fails safe

If the camera is offline, custom YOLO weights are missing, multiple customer sessions are simultaneously active, or the model becomes degraded, the worker does not invent physical events. Monitoring reports the degraded state and the platform falls back to human verification or simulation for development.
