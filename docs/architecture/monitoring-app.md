# SyncCart AI Monitoring / AI Operations Center

Phase 4D creates a third application for engineering observability. It is intentionally separate from the customer and retailer surfaces.

## Responsibility boundary

The monitoring application may observe:

- API / database / reconciliation health;
- camera runtime telemetry;
- Vision runtime telemetry;
- immutable domain events;
- reconciliation evidence;
- system counters and runtime notices.

It must not become the place where store colleagues make customer-facing review decisions. That remains the Retailer Operations App.

## Runtime telemetry contract

Camera and Vision runtime measurements are ephemeral and process-local in Phase 4D. They are not written into the transactional database.

This is deliberate: FPS, frame latency, detector latency, and class counts are operational signals rather than shopping records. Phase 6 may replace the in-process adapter with Redis, Prometheus, or another telemetry backend while retaining the same API contract.

## Honest pre-Vision behavior

Before a production CCTV/NVR source or the Phone 1 hackathon camera and the Vision worker are connected, camera and Vision states are returned as `NOT_CONFIGURED`.

The interface must never invent FPS, latency, model accuracy, or detection counts merely to make the dashboard look alive.

## Access boundary

Phase 4D uses `X-Monitor-Key` as the local monitoring access boundary. Enterprise deployments can bind this boundary to administrator/workforce identity, MFA, and RBAC.

## Realtime

`WS /ws/admin?key=...` emits `monitoring.snapshot` messages whenever the snapshot changes and heartbeat messages on the configured interval.
