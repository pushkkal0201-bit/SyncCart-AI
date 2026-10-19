# SyncCart AI

### IIT Bombay Hackathon Submission · Team Synergy · Release v1.0

## **See the shelf. Trust the cart. Keep checkout moving.**

> **Camera observes what was taken. Phone records what was scanned. AI reconciles both.**

[![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.13-3776AB?logo=python&logoColor=white)](#technology-stack)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128%2B-009688?logo=fastapi&logoColor=white)](#technology-stack)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=111)](#technology-stack)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)](#technology-stack)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.10%2B-5C3EE8?logo=opencv&logoColor=white)](#vision-layer)
[![CCTV](https://img.shields.io/badge/Camera-RTSP%20%7C%20MJPEG%20%7C%20Webcam-111827)](#camera-integration)
[![Privacy](https://img.shields.io/badge/Privacy-No%20Face%20Recognition-7D3C98)](#privacy-and-responsible-ai)

---

## Executive Summary

**SyncCart AI** is a privacy-preserving Vision AI platform for frictionless **Scan-and-Go retail**. It solves a simple but expensive operational gap:

```text
What physically left the shelf  !=  What was digitally scanned
```

SyncCart maintains two independent transaction views:

- **Physical Cart** — generated from shelf-camera events such as pickup and return.
- **Digital Cart** — generated from customer barcode scans on the Scan-and-Go app.

The **Shelf-to-Scan Reconciliation Engine** continuously compares both views. Matching events disappear into the background. A temporary mismatch enters verification, then a private product-specific nudge, and only persistent unresolved disagreement reaches a retailer review queue.

### Core principle

> **Do not classify people as suspicious. Detect disagreement between two versions of the transaction.**

The repository contains the complete hackathon submission scope: Core API, Customer App, Retailer Operations App, AI Monitoring Center, CCTV/Phone camera ingestion, physical event generation, digital cart, reconciliation, nudges, review workflow, dataset and model tooling, simulator, commissioning controls, documentation, and automated verification.

---

# 1. What, Why, Who, Where, When, How

| Question | SyncCart AI |
|---|---|
| **What?** | A Vision AI + event-reconciliation system that compares shelf reality with the shopper's digital cart. |
| **Why?** | Scan-and-Go is fast, but missed scans create a trust gap. SyncCart protects convenience without turning the store into a surveillance-first experience. |
| **Who?** | Shoppers, store colleagues, retail managers, and AI/engineering operations teams. |
| **Where?** | Real retail: fixed CCTV/IP cameras or NVR/VMS streams connected to an edge node. Hackathon demo: Phone 1 acts as the shelf-camera source. |
| **When?** | On pickup, return, scan, cart removal, grace-window expiry, review, and checkout. |
| **How?** | Camera stream → shelf observation → physical event → digital scan → temporal reconciliation → match / nudge / review. |

---

# 2. Problem

Scan-and-Go removes queue friction but creates three competing requirements:

1. **Customer convenience** — shopping should remain fast and private.
2. **Revenue protection** — physical items must reconcile with the digital cart.
3. **Operational efficiency** — colleagues should review only specific unresolved discrepancies.

Traditional approaches often over-index on one side: more manual checks reduce convenience, while less verification increases uncertainty. SyncCart inserts a software reconciliation layer between shelf activity and checkout.

---

# 3. Main Feature: Shelf-to-Scan Reconciliation

```text
             PHYSICAL REALITY
            CCTV / shelf camera
                    │
                    ▼
             Physical Cart
                    │
                    │
                    ▼
              RECONCILIATION
                    ▲
                    │
                    │
              Digital Cart
                    ▲
                    │
          Customer Scan-and-Go
              DIGITAL REALITY
```

A pickup and a scan for the same SKU inside the configured match window produce a confirmed match. A pickup without a corresponding scan moves through controlled escalation:

```text
MATCHED
   │
   └─ mismatch detected
          ↓
       VERIFY
          ↓
       NUDGE
          ↓
       REVIEW
```

The platform therefore intervenes on **item-level evidence**, not on identity or demographic inference.

---

# 4. Key Innovation

## 4.1 Dual-reality transaction model

SyncCart never treats a single sensor as absolute truth. It maintains independent physical and digital projections and reconciles them through events.

## 4.2 Discrepancy detection instead of intent classification

The system asks:

> “Does the physical cart agree with the digital cart?”

It does **not** ask:

> “Does this person look suspicious?”

## 4.3 Existing CCTV reuse

Real deployments can connect to fixed IP cameras or NVR/VMS channels over RTSP. This reduces dependency on specialized smart-cart hardware.

## 4.4 Graduated intervention

SyncCart uses:

```text
VERIFY → PRIVATE NUDGE → TARGETED REVIEW
```

rather than sending every mismatch directly to staff.

## 4.5 Safe Vision boundary

Vision is treated as an uncertain sensor. Camera output becomes a normalized event only after temporal stabilization, confidence checks, baseline learning, cooldown handling, and explicit arming.

## 4.6 Two live detector profiles

The release supports two complementary physical-observation strategies:

- **Fixed-zone reference detector** — training-free, optimized for the calibrated three-SKU demo shelf.
- **YOLO detector adapter** — optional custom-model path for appearance-based SKU detection across more flexible layouts.

`DETECTOR_MODE=AUTO` prefers YOLO when weights are supplied and otherwise uses the built-in fixed-zone reference detector, so the release remains fully runnable without committing large binary weights.

---

# 5. Real-World Camera Architecture

## Production deployment

```mermaid
flowchart LR
    CCTV[Fixed CCTV / IP Camera] -->|RTSP| EDGE[SyncCart Edge Vision]
    NVR[NVR / VMS Channel] -->|RTSP| EDGE
    EDGE --> CV[OpenCV Camera Adapter]
    CV --> DET[Detector]
    DET --> PLAN[Planogram / Shelf Zones]
    PLAN --> STAB[Temporal Stabilizer]
    STAB --> CORE[SyncCart Core API]
```

## Hackathon deployment

Phone 1 is used as a portable camera source because it provides the same network-stream contract without requiring access to a retail CCTV installation.

```mermaid
flowchart LR
    PHONE[Phone 1 + IP Webcam] -->|HTTP / MJPEG| EDGE[SyncCart Edge Vision]
    EDGE --> CORE[Same Vision + Reconciliation Pipeline]
```

The downstream code path is unchanged.

| Layer | Hackathon demo | Retail installation |
|---|---|---|
| Camera | Phone 1 | CCTV / IP camera / NVR |
| Stream | HTTP/MJPEG | RTSP preferred; HTTP/MJPEG supported |
| Compute | Laptop | Edge PC / mini server / GPU node |
| Identity | `PHONE-1-SHELF-CAM` | Store/aisle/camera ID |
| Event contract | `VISION_PICKUP`, `VISION_RETURN` | Same |

---

# 6. Full System Architecture

```mermaid
flowchart TB
    subgraph Edge[Retail Edge]
        CAM[CCTV / NVR / Phone 1]
        VISION[Vision Service\nOpenCV + Detector + Planogram]
        CAM --> VISION
    end

    subgraph Core[SyncCart Core]
        API[FastAPI Core API]
        EVENTS[Immutable Domain Events]
        PHYS[Physical Cart Projection]
        DIGI[Digital Cart Projection]
        REC[Reconciliation Engine]
        DISC[Discrepancy Lifecycle]
        NUDGE[Nudge / Review Workflow]
        DB[(SQLite local / PostgreSQL-ready)]

        API --> EVENTS
        EVENTS --> PHYS
        EVENTS --> DIGI
        PHYS --> REC
        DIGI --> REC
        REC --> DISC
        DISC --> NUDGE
        API --> DB
    end

    subgraph Apps[Role-specific Applications]
        CUSTOMER[Customer Scan-and-Go App]
        RETAILER[Retailer Operations App]
        MONITOR[AI Monitoring Center]
    end

    VISION -->|VISION_PICKUP / VISION_RETURN| API
    CUSTOMER -->|PRODUCT_SCANNED / DIGITAL_ITEM_REMOVED| API
    API <-->|REST + WebSocket| CUSTOMER
    API <-->|REST + WebSocket| RETAILER
    API <-->|REST + WebSocket| MONITOR
```

### Architectural rule

The camera never owns transaction truth. It produces frames. The Vision service converts frames into evidence. The Core API owns durable cart state, idempotency, matching, discrepancy state, review, and checkout decisions.

---

# 7. End-to-End Event Flow

```mermaid
sequenceDiagram
    participant Shelf
    participant Camera
    participant Vision
    participant Core
    participant Customer
    participant Reconcile
    participant Retailer

    Shelf->>Camera: Product quantity changes
    Camera->>Vision: Video frames
    Vision->>Vision: Detect + stabilize
    Vision->>Core: VISION_PICKUP(SKU)
    Core->>Reconcile: Physical Cart +1

    alt Customer scans inside match window
        Customer->>Core: PRODUCT_SCANNED(SKU)
        Core->>Reconcile: Digital Cart +1
        Reconcile->>Core: MATCH_CONFIRMED
    else Scan not observed
        Reconcile->>Core: VERIFY
        Reconcile->>Customer: Product-specific nudge
        alt Customer scans or returns item
            Customer->>Core: corrective action
            Vision->>Core: VISION_RETURN if returned
            Reconcile->>Core: RESOLVED
        else Mismatch remains
            Reconcile->>Retailer: REVIEW_REQUIRED
        end
    end
```

---

# 8. Customer App

The Customer App is the shopper-facing Scan-and-Go experience on Phone 2.

### Features

- anonymous session creation;
- barcode-based product lookup;
- digital cart projection;
- duplicate-scan suppression;
- item removal;
- real-time cart/reconciliation snapshots;
- private discrepancy nudges;
- `SCAN NOW`, `I RETURNED IT`, and `GET HELP` actions;
- checkout reconciliation;
- clear-to-exit state.

### Customer journey

```text
Start session
    ↓
Scan product
    ↓
Digital cart
    ↓
Continue shopping
    ↓
Mismatch? ── No ──→ Continue / Checkout
    │
   Yes
    ↓
Private nudge
    ↓
Scan now / Returned it / Get help
    ↓
Reconciliation
    ↓
Clear to exit or targeted review
```

### Source

```text
apps/customer-web/
packages/api-client/
packages/realtime-client/
packages/shared-types/
packages/design-system/
```

---

# 9. Retailer Operations App

The Retailer App is an **exception-management surface**, not a second customer cart editor.

### Features

- store overview metrics;
- active shopping sessions;
- physical vs digital cart comparison;
- open discrepancy queue;
- reason codes and evidence;
- Vision confidence visibility;
- event timeline;
- colleague resolution workflow;
- audited review resolution.

### Integrity rule

Retailer review actions do not fabricate a `PRODUCT_SCANNED` event. Customer scans originate from the Customer App; physical corrections remain on the physical/review side of the domain model.

### Source

```text
apps/retailer-web/
services/api/app/services/store_operations.py
services/api/app/api/v1/store_ops.py
services/api/app/api/ws/store.py
```

---

# 10. AI Monitoring Center

The Monitoring App separates engineering observability from store operations.

### Features

- API/database/reconciliation health;
- camera source and FPS;
- stream latency and resolution;
- detector name/version/device;
- inference latency/confidence;
- detection distribution;
- domain event stream;
- reconciliation inspector;
- Vision preview;
- runtime reset controls;
- camera freeze/offline indicators.

### Source

```text
apps/monitoring-web/
services/api/app/services/monitoring.py
services/api/app/api/v1/monitoring.py
services/api/app/api/ws/monitoring.py
```

---

# 11. Vision Layer

The Vision service accepts a generic camera source and exposes the same event contract regardless of camera vendor.

## Camera sources

- RTSP / RTSPS CCTV;
- NVR/VMS channel;
- HTTP/MJPEG;
- USB/webcam index;
- recorded video file.

## Detector modes

### `AUTO` — default

```text
YOLO weights available? → YOLO
otherwise               → fixed-zone reference detector
```

### `ZONE_OCCUPANCY`

Uses the calibrated planogram and learns the initial occupied appearance of each SKU zone. It is optimized for the controlled demo where one product occupies one configured zone.

### `YOLO`

Uses an Ultralytics-compatible custom weight file and class-to-SKU mapping.

## Physical-event pipeline

```text
Camera frame
   ↓
Detector
   ↓
SKU/zone observation
   ↓
Count stabilizer
   ↓
Baseline + cooldown + arm controls
   ↓
VISION_PICKUP / VISION_RETURN
   ↓
Core API
```

---

# 12. Current Demo SKU Contract

```text
0 copy
1 olive_oil
2 bottle
```

Planogram configuration:

```text
config/vision_planogram.yaml
```

The fixed-zone detector maps each calibrated region directly to its SKU, while the YOLO adapter can map model classes through `class_to_sku`.

---

# 13. Reconciliation State Machine

```mermaid
stateDiagram-v2
    [*] --> Synced
    Synced --> Verifying: physical != digital
    Verifying --> Synced: matching event arrives
    Verifying --> NudgeSent: mismatch persists
    NudgeSent --> Resolved: scan / return / colleague resolution
    NudgeSent --> ReviewRequired: escalation window expires
    ReviewRequired --> Resolved: colleague resolves
    Resolved --> Synced
```

The reconciliation layer is intentionally deterministic and event-based so Vision uncertainty does not silently mutate business state.

---

# 14. Domain Events

Representative events include:

```text
SESSION_STARTED
PRODUCT_SCANNED
DIGITAL_ITEM_REMOVED
VISION_PICKUP
VISION_RETURN
MATCH_CONFIRMED
DISCREPANCY_OPENED
NUDGE_SENT
CUSTOMER_ACTION_RECORDED
REVIEW_REQUIRED
REVIEW_RESOLVED
CHECKOUT_REQUESTED
CHECKOUT_APPROVED
SESSION_ENDED
```

All major writes support idempotency or duplicate suppression at the appropriate boundary.

---

# 15. Privacy and Responsible AI

SyncCart is deliberately designed around transaction state rather than identity.

### Not used

- facial recognition;
- demographic profiling;
- emotion recognition;
- criminal-intent classification;
- persistent biometric identity.

### Used

- SKU;
- quantity;
- shelf zone;
- timestamp;
- detector confidence;
- physical/digital cart state;
- temporary session identifiers.

### Design posture

```text
Edge-first video processing
        ↓
Minimal event metadata
        ↓
Transaction reconciliation
        ↓
Targeted intervention only when needed
```

---

# 16. Security Boundaries

SyncCart separates customer, retailer, simulator, Vision, and monitoring access paths.

| Boundary | Mechanism in local release |
|---|---|
| Customer | Temporary session token |
| Retailer Operations | Store operations key |
| Monitoring | Monitoring key |
| Vision ingestion | Vision key |
| Vision arm/disarm | Separate control key |
| Simulator | Separate simulator key |

Secrets are loaded from `.env`, which is excluded from Git. Camera credentials are redacted in diagnostics.

---

# 17. Technology Stack

| Layer | Technology |
|---|---|
| Core API | Python, FastAPI |
| Persistence | SQLAlchemy 2.x, Alembic |
| Local DB | SQLite |
| Deployment DB contract | PostgreSQL-ready SQLAlchemy models |
| Vision | OpenCV, NumPy |
| Trainable detector | Ultralytics YOLO / PyTorch adapter |
| Frontend | React 18, TypeScript, Vite |
| Realtime | WebSockets + REST fallback |
| DataOps | Python, YOLO dataset tooling |
| Verification | Pytest, TypeScript compiler, GitHub Actions |
| Camera | RTSP, HTTP/MJPEG, webcam, recorded video |

---

# 18. Repository Structure

```text
SyncCart-AI/
├── apps/
│   ├── customer-web/          # Phone 2 Scan-and-Go experience
│   ├── retailer-web/          # Store exception management
│   └── monitoring-web/        # AI/engineering operations
│
├── packages/
│   ├── api-client/
│   ├── design-system/
│   ├── realtime-client/
│   └── shared-types/
│
├── services/
│   ├── api/                   # Core FastAPI application
│   └── vision/                # CCTV / edge Vision worker
│
├── ml/
│   ├── dataops/               # prepare + validate datasets
│   ├── training/              # YOLO training entrypoint
│   └── evaluation/            # evaluate + benchmark + register
│
├── scripts/
│   ├── probe_camera_source.py
│   ├── calibrate_planogram.py
│   ├── capture_vision_dataset.py
│   ├── commission_synccart.py
│   ├── e2e_demo_runner.py
│   ├── run_synccart_stack_windows.ps1
│   └── verify_submission.py
│
├── config/
│   ├── vision_planogram.yaml
│   └── camera_sources.example.yaml
│
├── docs/
│   ├── architecture/
│   ├── product/
│   ├── vision/
│   ├── operations/
│   └── phase-implementation.md
│
├── models/
│   ├── registry/
│   └── weights/
│
├── .github/workflows/
├── .env.example
├── pyproject.toml
├── package.json
├── ARCHITECTURE.md
├── QUICKSTART.md
└── README.md
```

---

# 19. Phase Implementation Map

All engineering phases are integrated into release v1.0.

| Phase | Capability | Primary implementation |
|---|---|---|
| **0** | Repository, ADRs, config, privacy/security | `docs/`, `.env.example`, project configs |
| **1** | FastAPI foundation, DB, logging, health | `services/api/app/`, Alembic |
| **2** | Digital cart, scans, idempotency | cart/session/product services + tests |
| **3** | Physical cart, matching, discrepancies, nudges | reconciliation + physical-cart services |
| **4A/B** | Customer Scan-and-Go PWA | `apps/customer-web/` |
| **4C** | Retailer Operations App | `apps/retailer-web/`, store APIs |
| **4D** | AI Monitoring Center | `apps/monitoring-web/`, monitoring APIs |
| **5** | Camera + Vision service | `services/vision/`, Vision gateway |
| **6** | Dataset/DataOps/model lifecycle | `ml/`, capture/calibration scripts |
| **7** | Safe live commissioning + E2E | control endpoints, commissioning, E2E runner |
| **Release 1.0** | CCTV-first profile + training-free fixed-zone detector | camera adapter + `FixedZoneReferenceDetector` |

Detailed map: [`docs/phase-implementation.md`](docs/phase-implementation.md)

---

# 20. Quick Start — Windows

## Requirements

- Python 3.12 or 3.13
- Node.js 18+
- Git
- Camera source: CCTV/RTSP, IP Webcam, webcam, or recorded video

## Install

```powershell
py -3.13 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
pip install -e ".\services\vision"
npm install
Copy-Item .env.example .env
```

YOLO support is optional:

```powershell
pip install -e ".\services\vision[yolo]"
```

## Seed demo catalog

```powershell
python scripts\seed_demo_catalog.py
```

## Launch stack

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_synccart_stack_windows.ps1
```

Services:

```text
Core API       http://127.0.0.1:8000
Swagger        http://127.0.0.1:8000/docs
Customer       http://127.0.0.1:5173
Retailer       http://127.0.0.1:5174
Monitoring     http://127.0.0.1:5175
Vision         http://127.0.0.1:8100
Vision preview http://127.0.0.1:8100/preview.mjpeg
```

---

# 21. Camera Integration

## CCTV / NVR

Example `.env`:

```env
CAMERA_ID=STORE-01-AISLE-04-CAM-01
CAMERA_SOURCE_NAME=Aisle 4 Shelf Camera
CAMERA_SOURCE=rtsp://USER:PASSWORD@CAMERA_IP:554/STREAM_PATH
CAMERA_STREAM_MODE=RTSP
CAMERA_BACKEND=FFMPEG
CAMERA_BUFFER_SIZE=1
DETECTOR_MODE=AUTO
```

Probe:

```powershell
python scripts\probe_camera_source.py --source "rtsp://USER:PASSWORD@CAMERA_IP:554/STREAM_PATH"
```

## Phone 1 hackathon camera

```env
CAMERA_ID=PHONE-1-SHELF-CAM
CAMERA_SOURCE_NAME=Phone 1 Shelf Camera
CAMERA_SOURCE=https://PHONE-IP:8080/video
CAMERA_STREAM_MODE=MJPEG
DETECTOR_MODE=AUTO
```

Probe:

```powershell
python scripts\probe_camera_source.py --source "https://PHONE-IP:8080/video"
```

---

# 22. Shelf Calibration

```powershell
python scripts\calibrate_planogram.py `
  --source "https://PHONE-IP:8080/video" `
  --display-width 900 `
  --display-height 550
```

The current planogram maps three calibrated zones to:

```text
copy
olive_oil
bottle
```

For the fixed-zone detector, start the Vision service with one product present in each configured zone so the initial occupied reference can be learned.

---

# 23. Model and Data Pipeline

The repository supports a complete custom-model lifecycle without storing private datasets or large binary weights in Git.

```text
Capture
   ↓
Annotate
   ↓
Prepare YOLO dataset
   ↓
Validate
   ↓
Train
   ↓
Evaluate / Benchmark
   ↓
Register
   ↓
Run with DETECTOR_MODE=YOLO or AUTO
```

Commands:

```powershell
python ml\dataops\prepare_yolo_dataset.py --source runtime\annotated-pool --output ml\datasets\demo_sku --clean
python ml\dataops\validate_yolo_dataset.py --data ml\datasets\demo_sku\dataset.yaml --fail-on-invalid
python ml\training\train_yolo.py --device cpu --epochs 80 --batch 8
python ml\evaluation\evaluate_model.py --weights PATH\TO\best.pt --split test --device cpu
python ml\evaluation\benchmark_model.py --weights PATH\TO\best.pt --device cpu
python ml\evaluation\register_model.py --weights PATH\TO\best.pt --metrics PATH\TO\metrics.json
```

The default hackathon release does not depend on a committed model binary because the fixed-zone detector provides a complete live shelf-event path.

---

# 24. Core API Surface

Representative endpoints:

### Sessions / customer

```text
POST /api/v1/sessions
GET  /api/v1/sessions/{session_id}
GET  /api/v1/sessions/{session_id}/cart
POST /api/v1/sessions/{session_id}/scan
POST /api/v1/sessions/{session_id}/cart/items/{sku}/remove
POST /api/v1/sessions/{session_id}/checkout
```

### Products

```text
GET /api/v1/products
GET /api/v1/products/barcode/{barcode}
```

### Reconciliation / customer actions

```text
GET  /api/v1/sessions/{session_id}/reconciliation
POST /api/v1/sessions/{session_id}/nudges/{nudge_id}/action
```

### Retailer Operations

```text
GET  /api/v1/store/overview
GET  /api/v1/store/sessions
GET  /api/v1/store/sessions/{session_id}
GET  /api/v1/store/reviews
POST /api/v1/store/reviews/{discrepancy_id}/resolve
```

### Monitoring

```text
GET  /api/v1/admin/overview
GET  /api/v1/admin/events
GET  /api/v1/admin/sessions/{session_id}/reconciliation
POST /api/v1/admin/telemetry/camera
POST /api/v1/admin/telemetry/vision
POST /api/v1/admin/telemetry/reset
```

### Vision service

```text
GET  /health/ready
GET  /metrics
GET  /snapshot.jpg
GET  /preview.mjpeg
GET  /control/status
POST /control/arm
POST /control/disarm
```

### WebSockets

```text
/ws/customer/{session_id}
/ws/store
/ws/admin
```

Full reference: [`docs/api-reference.md`](docs/api-reference.md)

---

# 25. Demo Story for Judges

A two-minute judge flow:

1. Start a customer session on Phone 2.
2. Show that Phone 1 represents the shelf camera in the hackathon setup and that the same adapter accepts real CCTV/NVR RTSP.
3. Remove `olive_oil` from the calibrated shelf zone.
4. Vision stabilizes the count change and publishes `VISION_PICKUP`.
5. Physical Cart becomes `olive_oil = 1`.
6. Do not scan immediately.
7. SyncCart verifies the mismatch and sends a private nudge.
8. Scan `olive_oil` on Phone 2.
9. Digital Cart becomes `olive_oil = 1`.
10. Reconciliation resolves the discrepancy.
11. Retailer Operations shows no unresolved review.
12. AI Monitoring shows the camera, detector, domain event, and reconciliation trail.

### Judge takeaway

> **SyncCart converts existing camera infrastructure into transaction evidence, then uses reconciliation rather than identity profiling to protect Scan-and-Go.**

---

# 26. Business Impact

## Shopper

- shorter checkout flow;
- fewer blanket bag checks;
- private self-correction for ordinary missed scans;
- no facial-recognition dependency.

## Retailer

- item-level discrepancy evidence;
- fewer broad manual interventions;
- reusable CCTV infrastructure;
- auditable event trail;
- targeted colleague workflow.

## Store colleague

- review specific SKU disagreements instead of entire baskets;
- clear reason codes;
- physical vs digital cart side-by-side.

## Engineering / AI operations

- camera health and freeze detection;
- detector telemetry;
- event inspection;
- model-independent camera contract;
- safe arm/disarm and baseline controls.

---

# 27. Deployment Profiles

SyncCart separates the transaction engine from camera hardware, so the same core can be deployed at different scales.

### Hackathon profile

```text
Phone 1 camera
1 calibrated shelf
1 active shopper in watched zone
fixed-zone detector or YOLO
SQLite
3 web applications
```

### Retail edge profile

```text
CCTV / NVR RTSP
edge inference node
PostgreSQL
store identity integration
multiple Vision workers
central operational monitoring
```

The normalized event boundary keeps cart/reconciliation logic unchanged as the camera estate grows.

---

# 28. Verification

Run the complete Python verification suite:

```powershell
python scripts\verify_submission.py --run-tests
```

Run frontend type checks:

```powershell
npm run typecheck
```

Build all three web applications:

```powershell
npm run build
```

GitHub Actions configuration is included in `.github/workflows/`.

---

# 29. Documentation

### Start here

- [`QUICKSTART.md`](QUICKSTART.md)
- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`docs/phase-implementation.md`](docs/phase-implementation.md)
- [`docs/demo-guide.md`](docs/demo-guide.md)

### Product

- [`docs/product/main-features.md`](docs/product/main-features.md)
- [`docs/product/customer-app.md`](docs/product/customer-app.md)
- [`docs/product/retailer-app.md`](docs/product/retailer-app.md)

### Architecture

- [`docs/architecture/system-overview.md`](docs/architecture/system-overview.md)
- [`docs/architecture/event-flow.md`](docs/architecture/event-flow.md)
- [`docs/architecture/reconciliation.md`](docs/architecture/reconciliation.md)

### Vision / CCTV

- [`docs/vision/cctv-production-deployment.md`](docs/vision/cctv-production-deployment.md)
- [`docs/vision/camera-source-contract.md`](docs/vision/camera-source-contract.md)
- [`docs/vision/architecture.md`](docs/vision/architecture.md)
- [`docs/vision/phone1-setup.md`](docs/vision/phone1-setup.md)
- [`docs/vision/live-commissioning.md`](docs/vision/live-commissioning.md)

### Governance

- [`docs/privacy.md`](docs/privacy.md)
- [`docs/security.md`](docs/security.md)
- [`docs/impact-and-innovation.md`](docs/impact-and-innovation.md)

---

# 30. Release Scope

**SyncCart AI v1.0 is the complete IIT Bombay hackathon submission build for a controlled, fixed-planogram, single-shopper shelf-reconciliation demonstration.**

It includes both the portable Phone 1 camera profile used for judging and the CCTV/NVR camera contract used by the real-world architecture. The release intentionally separates camera ingestion, Vision evidence, transaction state, reconciliation, store operations, and engineering monitoring so each layer can scale independently.

---

## Team

**Team Synergy**  
**Project:** SyncCart AI

### Final punchline

> ## **See the shelf. Trust the cart. Keep checkout moving.**
