# Camera Source Contract

## Goal

Provide a vendor-neutral boundary between retail camera infrastructure and SyncCart Vision.

## Runtime configuration

| Variable | Purpose |
|---|---|
| `CAMERA_ID` | Stable non-secret identifier used in events and telemetry |
| `CAMERA_SOURCE` | Webcam index, RTSP URL, HTTP/MJPEG URL, or video path |
| `CAMERA_SOURCE_NAME` | Human-readable operational label |
| `CAMERA_STREAM_MODE` | `AUTO`, `RTSP`, `HTTP_MJPEG`, `WEBCAM`, etc. |
| `CAMERA_BACKEND` | OpenCV backend hint: `AUTO`, `FFMPEG`, `DSHOW`, `MSMF` |
| `CAMERA_BUFFER_SIZE` | Low-latency buffer hint where supported |
| `CAMERA_RECONNECT_DELAY_MS` | Delay before reconnect attempts |
| `FROZEN_FRAME_LIMIT` | Consecutive repeated-frame threshold |

## Source classification

The runtime classifies sources for telemetry as:

- `RTSP_CCTV`
- `HTTP_MJPEG`
- `WEBCAM`
- `VIDEO_FILE`

## Security contract

Camera credentials may exist inside `CAMERA_SOURCE` at runtime, but diagnostics use a redacted source representation. Operators should still use `.env`, OS secrets, containers, or a secret manager rather than embedding credentials in source code.

## Business boundary

A camera source never owns cart truth. It only produces frames. The Vision service converts frames into normalized physical events, and the Core API owns transaction state, reconciliation, discrepancy lifecycle and review.
