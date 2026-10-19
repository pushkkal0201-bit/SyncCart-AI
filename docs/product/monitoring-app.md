# AI Monitoring Center — Product and Technical Specification

## Purpose

The AI Monitoring Center is the engineering and system-operations surface for SyncCart. It keeps camera, detector, event, and reconciliation diagnostics separate from the retailer's day-to-day exception workflow.

## Main features

- Core API and database health;
- camera status, source, resolution, FPS, and frame latency;
- detector name, version, device, inference latency, and confidence;
- class-count distribution;
- recent domain event stream;
- per-session reconciliation inspection;
- Vision preview and snapshot endpoints;
- frozen-camera state;
- runtime telemetry reset;
- distinct monitoring access boundary.

## Camera visibility

The monitoring surface works with any configured camera source accepted by the Vision service: CCTV/NVR RTSP, HTTP/MJPEG, webcam, recorded video, or the Phone 1 hackathon stream.

## API integration

```text
GET  /api/v1/admin/overview
GET  /api/v1/admin/events
GET  /api/v1/admin/sessions/{session_id}/reconciliation
POST /api/v1/admin/telemetry/camera
POST /api/v1/admin/telemetry/vision
POST /api/v1/admin/telemetry/reset
WS   /ws/admin?key=<MONITOR_KEY>
```

## Source map

```text
apps/monitoring-web/src/App.tsx
services/api/app/api/v1/monitoring.py
services/api/app/services/monitoring.py
services/api/app/services/monitoring_telemetry.py
services/api/app/api/ws/monitoring.py
```
