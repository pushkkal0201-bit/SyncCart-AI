# API and Realtime Reference

The canonical interactive API reference is available at `/docs` while the Core API is running.

## Health

```text
GET /live
GET /ready
```

## Products

```text
GET  /api/v1/products
POST /api/v1/products
GET  /api/v1/products/barcode/{barcode}
GET  /api/v1/products/{sku}
```

## Sessions / digital cart

```text
POST /api/v1/sessions
GET  /api/v1/sessions
GET  /api/v1/sessions/{session_id}
GET  /api/v1/sessions/{session_id}/events
GET  /api/v1/sessions/{session_id}/cart
POST /api/v1/sessions/{session_id}/scan
POST /api/v1/sessions/{session_id}/remove
```

Customer mutations use the configured customer-session token header and idempotency header where required.

## Customer actions / checkout

```text
POST /api/v1/sessions/{session_id}/nudges/{nudge_id}/action
POST /api/v1/sessions/{session_id}/checkout
```

## Reconciliation

```text
GET /api/v1/sessions/{session_id}/reconciliation
GET /api/v1/sessions/{session_id}/nudges
```

## Simulator

Protected by the simulator API key:

```text
POST /api/v1/simulator/pickup
POST /api/v1/simulator/return
POST /api/v1/simulator/sweep
```

The simulator is a demo/development adapter and should be disabled outside approved non-production use.

## Store operations

Protected by the store-operations key:

```text
GET  /api/v1/store/overview
GET  /api/v1/store/sessions
GET  /api/v1/store/sessions/{session_id}
GET  /api/v1/store/reviews
POST /api/v1/store/reviews/{discrepancy_id}/resolve
```

## Monitoring

Protected by the monitoring key:

```text
GET  /api/v1/admin/overview
GET  /api/v1/admin/events
GET  /api/v1/admin/sessions/{session_id}/reconciliation
POST /api/v1/admin/telemetry/camera
POST /api/v1/admin/telemetry/vision
POST /api/v1/admin/telemetry/reset
```

## Vision ingestion

Protected by the Vision API key:

```text
GET  /api/v1/vision/active-session
POST /api/v1/vision/events
POST /api/v1/vision/telemetry/camera
POST /api/v1/vision/telemetry/model
```

The active-session endpoint intentionally refuses ambiguous multi-session attribution in the controlled live watched-zone profile.

## WebSockets

```text
WS /ws/customer/{session_id}
WS /ws/store?key=<STORE_OPS_API_KEY>
WS /ws/admin?key=<MONITORING_API_KEY>
```

## Vision service

Default port: `8100`.

```text
GET  /
GET  /health/live
GET  /health/ready
GET  /metrics
GET  /control/status
POST /control/arm
POST /control/disarm
GET  /snapshot.jpg
GET  /preview.mjpeg
```

Arm/disarm requires the configured Vision control key.
