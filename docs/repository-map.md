# Repository Map

## `apps/`

### `customer-web/`
React/Vite Scan-and-Go customer experience.

### `retailer-web/`
Store colleague operations surface: session overview, cart comparison, review queue, resolution.

### `monitoring-web/`
Engineering/AI operations surface: health, telemetry, events, reconciliation inspection.

## `packages/`

Shared frontend building blocks:

- `api-client/` — REST client
- `realtime-client/` — WebSocket client
- `shared-types/` — common TypeScript types
- `design-system/` — reusable UI components and tokens

## `services/api/`

Transactional core:

- `app/api/` — HTTP and WebSocket routes
- `app/services/` — business logic
- `app/repositories/` — persistence access
- `app/models/` — SQLAlchemy models
- `app/schemas/` — Pydantic API contracts
- `app/core/` — settings, logging, middleware, exceptions
- `migrations/` — Alembic schema history
- `tests/` — backend/integration tests

## `services/vision/`

Edge Vision runtime:

- `camera.py` — OpenCV camera adapter
- `detector.py` — YOLO adapter
- `planogram.py` — zone config and mapping
- `stabilizer.py` — stable count transition logic
- `freeze.py` — frozen-frame detection
- `runtime.py` — runtime telemetry / preview state
- `worker.py` — end-to-end camera/inference/event loop
- `main.py` — Vision HTTP control/health/preview API
- `tests/` — pure logic / control tests

## `scripts/`

Operational tooling:

- `probe_camera_source.py` — generic CCTV/NVR/Phone camera probe
- `probe_phone_camera.py` — Phone 1 compatibility helper
- `calibrate_planogram.py`
- `capture_vision_dataset.py`
- `seed_demo_catalog.py`
- `commission_synccart.py`
- `e2e_demo_runner.py`
- Windows launchers
- `verify_submission.py`

## `ml/`

Model lifecycle:

- `dataops/prepare_yolo_dataset.py`
- `dataops/validate_yolo_dataset.py`
- `training/train_yolo.py`
- `evaluation/evaluate_model.py`
- `evaluation/benchmark_model.py`
- `evaluation/register_model.py`

## `config/`

`vision_planogram.yaml` maps detector classes to business SKUs and calibrated shelf zones.

## `models/`

Model registry contract and local weight destination. Weight files are excluded from Git.

## `docs/`

Architecture decisions, privacy/security, Vision operations, impact, demo guide, technical deep dive, roadmap, and API reference.

## Sourcebooks

`PHASE*_SOURCEBOOK.md` files preserve detailed development snapshots and rationale from the staged build process.

## Production camera / product additions

- `scripts/probe_camera_source.py` — generic CCTV/NVR/Phone/webcam source probe.
- `config/camera_sources.example.yaml` — vendor-neutral source examples.
- `docs/vision/cctv-production-deployment.md` — real-world CCTV integration and security.
- `docs/vision/phone1-vs-cctv.md` — Phone 1-to-CCTV deployment mapping.
- `docs/vision/camera-source-contract.md` — camera configuration/runtime contract.
- `docs/product/main-features.md` — product feature pillars and punchline.
- `docs/product/customer-app.md` — customer product/technical specification.
- `docs/product/retailer-app.md` — retailer product/technical specification.
- `docs/operations/retail-deployment-checklist.md` — pilot deployment checklist.
