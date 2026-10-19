# SyncCart AI — IIT Bombay Hackathon Submission

## Team Synergy

### Punchline

> **See the shelf. Trust the cart. Keep checkout moving.**

### Technical line

> **Camera observes what was taken. Phone records what was scanned. AI reconciles both.**

## Submission summary

SyncCart AI is a privacy-preserving Vision AI system for Scan-and-Go retail. It creates a **Physical Cart** from shelf-camera events and a **Digital Cart** from shopper scans, then reconciles them in real time.

The release is complete for the controlled hackathon scope: one watched shelf, one active shopper session, three configured SKUs, Phone 1 or CCTV-compatible camera input, customer Scan-and-Go, retailer exception management, monitoring, reconciliation, live physical events, and checkout decisioning.

## Current demo SKUs

```text
0 copy
1 olive_oil
2 bottle
```

## Camera strategy

The hackathon uses Phone 1 as a portable HTTP/MJPEG camera source. The production-oriented camera adapter also accepts CCTV/IP-camera/NVR RTSP streams without changing the business-event pipeline.

## Live detector strategy

The submission ships two detector profiles:

- **Fixed-zone reference detector** — complete training-free path for the calibrated shelf demo.
- **YOLO adapter** — optional custom-model profile for flexible SKU appearance detection.

`DETECTOR_MODE=AUTO` makes the release self-contained: it uses YOLO when optional weights are present and otherwise activates the fixed-zone detector.

## Main differentiators

1. Physical and digital carts are maintained independently.
2. The system detects transaction disagreement rather than criminal intent.
3. Mismatches follow `VERIFY → NUDGE → REVIEW` instead of immediate escalation.
4. Existing CCTV/NVR infrastructure can be reused.
5. Vision is isolated behind a normalized event contract.
6. Customer, retailer, and AI operations experiences are separate applications.
7. Camera, detector, reconciliation, and review decisions remain explainable.
8. No facial-recognition dependency exists in the transaction path.

## Architecture

```text
CCTV / NVR / PHONE 1
         │
         ▼
   EDGE VISION SERVICE
 OpenCV + Detector + Planogram
         │
 VISION_PICKUP / RETURN
         ▼
     SYNCCART CORE
         │
   ┌─────┼──────────────┐
   ▼     ▼              ▼
CUSTOMER RETAILER   AI MONITORING
  APP      APP         CENTER
   │
   ▼
DIGITAL CART ↔ RECONCILIATION ↔ PHYSICAL CART
```

## Included code

- FastAPI Core API
- SQLAlchemy domain and migrations
- digital cart and idempotency
- physical cart and Vision gateway
- reconciliation worker and discrepancy state machine
- customer nudge actions
- Customer React PWA
- Retailer Operations React app
- AI Monitoring React app
- generic CCTV/RTSP/MJPEG/webcam/video camera adapter
- fixed-zone reference detector
- YOLO adapter
- planogram calibration
- dataset capture and quality checks
- YOLO dataset preparation and validation
- model training/evaluation/benchmark/registration tools
- safe Vision commissioning
- simulator and E2E runner
- automated Python and frontend verification

## Judge demo

1. Start a customer session.
2. Remove `olive_oil` from the calibrated shelf.
3. Vision publishes `VISION_PICKUP`.
4. Physical Cart becomes `olive_oil = 1`.
5. Leave the item unscanned long enough for verification/nudge.
6. Scan the item in Customer App.
7. Digital Cart becomes `olive_oil = 1`.
8. Reconciliation resolves the discrepancy.
9. Retailer Operations shows no unresolved review.
10. AI Monitoring shows the evidence trail and runtime health.

## Privacy statement

SyncCart uses SKU, quantity, zone, timestamp, confidence, and transaction state. It does not require facial recognition, demographic profiling, emotion recognition, or criminal-intent classification.

## Verification

```powershell
python scripts\verify_submission.py --run-tests
npm run typecheck
npm run build
```

## Repository navigation

- `README.md` — product + technical overview
- `QUICKSTART.md` — launch instructions
- `ARCHITECTURE.md` — architecture summary
- `docs/phase-implementation.md` — code mapping for every engineering phase
- `docs/demo-guide.md` — judge demo flow
- `docs/vision/` — CCTV, camera, commissioning, data/model documentation
- `docs/product/` — customer and retailer application documentation
