# Phase Implementation Map

SyncCart AI v1.0 integrates the complete hackathon engineering sequence into one repository.

## Phase 0 — Architecture and repository foundation

**Purpose:** establish boundaries before features.

**Implemented in:**

- `docs/architecture/`
- `docs/privacy.md`
- `docs/security.md`
- `.env.example`
- `pyproject.toml`
- `package.json`
- `.github/workflows/`

## Phase 1 — Core API foundation

**Purpose:** durable session/event platform.

**Implemented in:**

- `services/api/app/main.py`
- `services/api/app/core/`
- `services/api/app/db/`
- `services/api/app/models/`
- `services/api/migrations/`
- health endpoints and request middleware

## Phase 2 — Digital cart

**Purpose:** customer scans become an idempotent digital cart projection.

**Implemented in:**

- `services/api/app/services/cart.py`
- `services/api/app/services/products.py`
- `services/api/app/services/sessions.py`
- `services/api/app/repositories/idempotency.py`
- product/session/cart APIs

## Phase 3 — Physical cart and reconciliation

**Purpose:** reconcile shelf events with digital scans.

**Implemented in:**

- `physical_cart.py`
- `reconciliation.py`
- `reconciliation_worker.py`
- discrepancy/event match models and repositories
- customer actions / nudge lifecycle

## Phase 4A/B — Customer application

**Purpose:** Scan-and-Go, nudges, checkout, exit state.

**Implemented in:**

- `apps/customer-web/`
- `packages/api-client/`
- `packages/realtime-client/`
- customer WebSocket endpoint

## Phase 4C — Retailer Operations

**Purpose:** targeted exception management.

**Implemented in:**

- `apps/retailer-web/`
- `services/api/app/services/store_operations.py`
- `services/api/app/api/v1/store_ops.py`
- `/ws/store`

## Phase 4D — AI Monitoring Center

**Purpose:** camera, detector, event, and reconciliation observability.

**Implemented in:**

- `apps/monitoring-web/`
- monitoring telemetry service and APIs
- `/ws/admin`

## Phase 5 — Vision service

**Purpose:** turn a camera stream into normalized physical events.

**Implemented in:**

- `services/vision/synccart_vision/camera.py`
- `detector.py`
- `planogram.py`
- `stabilizer.py`
- `freeze.py`
- `worker.py`
- Core Vision gateway

## Phase 6 — DataOps and model lifecycle

**Purpose:** reproducible capture, dataset preparation, training, evaluation, benchmarking, and registration.

**Implemented in:**

- `scripts/capture_vision_dataset.py`
- `scripts/calibrate_planogram.py`
- `ml/dataops/`
- `ml/training/`
- `ml/evaluation/`
- `models/registry/`

## Phase 7 — Live commissioning and safety controls

**Purpose:** prevent uncontrolled physical-event publication.

**Implemented in:**

- Vision arm/disarm endpoints
- fresh baseline learning
- event cooldown
- frozen-camera detection
- `scripts/commission_synccart.py`
- `scripts/e2e_demo_runner.py`
- live runtime telemetry

## Release 1.0 — CCTV-first complete demo profile

**Purpose:** make the repository runnable as a complete controlled shelf demonstration without requiring committed model binaries.

**Implemented in:**

- RTSP/NVR/HTTP/webcam camera adapter
- camera-source credential redaction
- `FixedZoneReferenceDetector`
- `DETECTOR_MODE=AUTO`
- optional YOLO detector profile
- generic camera probe
- current `copy`, `olive_oil`, `bottle` planogram

The release keeps the transaction engine independent from detector choice: both detector profiles emit the same physical event contract.
