# Technical Deep Dive

## 1. Domain model

The platform treats activity as immutable domain events that feed projections and reconciliation. Representative events include:

- `PRODUCT_SCANNED`
- `DIGITAL_ITEM_REMOVED`
- `VISION_PICKUP`
- `VISION_RETURN`
- `MATCH_CONFIRMED`
- `DISCREPANCY_OPENED`
- `MATCH_EXPIRED`
- nudge / review / resolution events

The digital and physical carts are projections of these actions rather than ad-hoc UI state.

## 2. Digital cart

Customer mutations are protected by:

- temporary session tokens;
- token hashing at rest;
- duplicate-scan suppression;
- idempotency keys;
- server-side product lookup and quantity updates.

## 3. Physical cart

The core accepts normalized Vision events through a protected endpoint. The payload is validated for:

- session attribution;
- event kind;
- SKU;
- quantity;
- confidence;
- source metadata;
- idempotency.

Low-confidence or invalid events can be rejected before affecting the physical-cart projection.

## 4. Temporal matching

A compatible physical and digital event can be paired when:

- they refer to the same session;
- they refer to the same SKU;
- quantity matches;
- the opposite event type is compatible;
- the candidate has not already been matched;
- timestamps fall inside the configured match window.

The match confidence combines Vision confidence with temporal proximity. The coefficients are release heuristics used for explainable event matching and are not represented as calibrated probability estimates.

## 5. Discrepancy lifecycle

When physical and digital quantities diverge, SyncCart opens a discrepancy in `VERIFYING` state. A configured grace window allows expected user actions to arrive before intervention.

If physical quantity remains ahead of digital quantity, the system can create a neutral nudge. If unresolved after the escalation window, the item can enter `REVIEW_REQUIRED`.

## 6. Reconciliation worker

A background worker periodically advances time-dependent discrepancy states. Long-running reconciliation work is intentionally kept outside request handlers.

## 7. Vision runtime

The edge worker performs:

1. camera open / reconnect;
2. frame read;
3. frozen-frame monitoring;
4. YOLO inference when weights are available;
5. mapping detections to configured shelf zones;
6. per-zone count calculation;
7. count stabilization across consecutive frames;
8. pickup/return transition generation;
9. safe event suppression / publication;
10. camera and model telemetry publication;
11. annotated preview generation.

## 8. Missing-model behavior

If custom weights are unavailable, the service can remain alive and report camera state while Vision is `DEGRADED`. It does not fabricate product events.

## 9. Planogram

`config/vision_planogram.yaml` maps detector class names to business SKUs and normalized shelf rectangles. Calibration writes normalized coordinates so the configuration remains resolution-independent for the fixed camera view.

## 10. Camera freeze detection

The service tracks repeated frames. If a configured number of nearly identical frames indicates a frozen stream, the worker marks the condition and can reconnect rather than publishing events from stale imagery.

## 11. Live safety controls

Arm/disarm is separate from inference. Arming:

- increments a control generation;
- resets the stabilizer;
- clears event cooldown state;
- starts a fresh baseline-learning phase;
- permits event publication only after baseline readiness.

## 12. Realtime interfaces

Customer, store, and monitoring WebSockets expose role-specific snapshots. REST endpoints remain available for initial load and recovery.

## 13. DataOps

The repository includes tools for:

- camera probing;
- controlled capture;
- blur / brightness / duplicate checks;
- planogram calibration;
- YOLO dataset preparation;
- grouped train/val/test splitting by capture session;
- label validation;
- training;
- evaluation;
- benchmark;
- model registration.

Grouped splitting reduces leakage from near-consecutive frames captured in the same session.

## 14. Current controlled model contract

Classes:

```text
copy
olive_oil
bottle
```

The custom weights file is intentionally not committed until a measured model is trained and promoted.
