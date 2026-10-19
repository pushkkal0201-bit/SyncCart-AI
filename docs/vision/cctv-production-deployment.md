# Production CCTV / NVR Deployment

## Production principle

The hackathon demo uses **Phone 1** as a convenient IP camera, while the retail architecture connects to **existing CCTV/IP-camera/NVR infrastructure**.

In a real store, SyncCart does not require a shopper-facing phone to act as the shelf camera. Instead, the Vision service consumes one or more fixed camera streams exposed by a CCTV camera or an NVR/VMS.

```mermaid
flowchart LR
    CCTV[Fixed Retail CCTV] -->|RTSP / HTTP-MJPEG| EDGE[SyncCart Edge Vision Node]
    NVR[NVR / VMS Channel] -->|RTSP| EDGE
    EDGE --> YOLO[SKU Detection]
    YOLO --> PLAN[Planogram Zones]
    PLAN --> STAB[Stable Count Changes]
    STAB --> EVENTS[VISION_PICKUP / VISION_RETURN]
    EVENTS --> CORE[SyncCart Core API]
```

## Supported input modes

The current OpenCV camera adapter accepts:

- RTSP / RTSPS CCTV streams;
- RTSP channels exposed by an NVR/VMS;
- HTTP / MJPEG streams;
- USB / built-in webcam indexes;
- recorded video files for reproducible tests.

The Phone 1 hackathon path uses the same adapter and therefore exercises the same downstream Vision pipeline.

## Recommended production topology

```text
Retail CCTV / NVR
      │
      │ store camera VLAN
      ▼
Edge inference PC / mini server
      │
      ├── OpenCV stream ingest
      ├── YOLO SKU detector
      ├── planogram zone mapping
      ├── frozen-stream watchdog
      └── normalized event publisher
      │
      ▼
SyncCart Core API
      │
      ├── Customer App
      ├── Retailer Operations
      └── AI Monitoring Center
```

### Why edge inference

The preferred deployment keeps continuous video inside the store network. The core platform receives normalized transaction metadata such as SKU, quantity delta, confidence, camera ID, zone ID and timestamp rather than depending on cloud storage of raw video.

## CCTV onboarding sequence

1. **Select a camera** whose field of view clearly covers the target shelf.
2. **Assign a stable camera ID** such as `STORE-042-AISLE-04-CAM-01`.
3. **Reserve a fixed IP or stable NVR channel mapping**.
4. **Enable a stream** usable by OpenCV, usually RTSP.
5. **Use a dedicated read-only camera account** where supported.
6. **Place camera credentials in deployment secrets**, never in Git.
7. **Probe the stream** using `scripts/probe_camera_source.py`.
8. **Calibrate planogram zones** against the final camera geometry.
9. **Validate SKU model performance** on footage from the actual camera.
10. **Start Vision disarmed**, learn a fresh baseline, then arm event emission.

## Example `.env` for a direct CCTV stream

```dotenv
CAMERA_ID=STORE-042-AISLE-04-CAM-01
CAMERA_SOURCE_NAME=Aisle 4 Shelf Camera
CAMERA_STREAM_MODE=RTSP
CAMERA_BACKEND=FFMPEG
CAMERA_BUFFER_SIZE=1
CAMERA_SOURCE=rtsp://USER:PASSWORD@10.10.20.31:554/STREAM_PATH
```

Do not commit real credentials. `.env` is intentionally ignored by Git.

## Example NVR channel

```dotenv
CAMERA_ID=STORE-042-NVR-CH12
CAMERA_SOURCE_NAME=Aisle 4 NVR Channel 12
CAMERA_STREAM_MODE=RTSP
CAMERA_BACKEND=FFMPEG
CAMERA_BUFFER_SIZE=1
CAMERA_SOURCE=rtsp://USER:PASSWORD@NVR_IP:554/CHANNEL_PATH
```

The exact path depends on the CCTV/NVR vendor. SyncCart is intentionally vendor-neutral: once a standard stream URL is available, the same Vision worker can consume it.

## ONVIF

ONVIF can be useful for **device discovery, capability inspection, and obtaining stream profiles**, but the current runtime consumes the final RTSP/HTTP stream URL through OpenCV. ONVIF is therefore an integration aid rather than a hard runtime dependency.

## Main stream vs substream

For a pilot, choose the lowest stream that still keeps products visually separable.

- **Main stream**: higher detail, higher compute/network cost.
- **Substream**: lower latency and bandwidth, but may lose small-SKU detail.

A production pilot should benchmark both and select based on measured detection accuracy and latency.

## Networking and security

Recommended controls:

- isolate cameras on a retail/IoT VLAN;
- allow the edge node to read only required camera streams;
- deny public internet exposure of RTSP endpoints;
- use per-camera or per-NVR read-only credentials;
- store secrets outside source control;
- prefer fixed IPs or stable DNS/NVR mappings;
- monitor stream health and reconnect events;
- log camera IDs, not credentials or full secret-bearing URLs.

The camera adapter redacts user/password credentials from diagnostic output.

## Failure behavior

The Vision service is designed to fail visibly:

- camera unavailable -> `OFFLINE` / `DEGRADED`;
- repeated frozen frames -> reconnect and degraded telemetry;
- missing model weights -> camera preview may continue, but physical events are not fabricated;
- event emission disarmed -> inference continues, events remain suppressed;
- baseline learning -> transitions remain suppressed until stable counts are established.

## Multi-camera scale-out

The current hackathon repository demonstrates one watched zone and one eligible shopper session. A production rollout can run one Vision worker per camera/zone or orchestrate multiple workers, each with a unique `CAMERA_ID`, planogram and model configuration.

The hackathon release uses one eligible active shopper per watched zone. Enterprise deployments can add a separate camera-to-session attribution service without changing the physical/digital cart event contract.
