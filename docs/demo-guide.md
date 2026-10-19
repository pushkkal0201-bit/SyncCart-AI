# Judge Demo Guide

## Goal

Demonstrate the core thesis in under five minutes:

> physical pickup + mobile scan = match; physical pickup without scan = private discrepancy workflow.

## Pre-demo checklist

- Core API on port 8000.
- Customer App on 5173.
- Retailer App on 5174.
- Monitoring App on 5175.
- Vision service on 8100.
- Camera stream reachable from the edge laptop/server.
- Camera fixed after planogram calibration.
- Current products visible: `copy`, `olive_oil`, `bottle`.
- One eligible active shopper session in the watched zone.
- `DETECTOR_MODE=AUTO` or an explicitly selected detector profile.
- Vision event emission disarmed until the demo baseline is ready.

## Recommended story

### 1. Establish the two realities

Show Customer App and Retailer App. Explain that the customer phone owns the digital declaration while the camera independently observes shelf-state changes.

### 2. Matched flow

- remove `olive_oil`;
- Vision publishes pickup;
- scan olive oil on Phone 2;
- show physical and digital quantities align;
- show `MATCH_CONFIRMED` / synced state.

### 3. Missed-scan flow

- remove `bottle`;
- do not scan it;
- show physical cart ahead of digital cart;
- show `VERIFYING`;
- after the grace window show a private nudge;
- resolve by scanning or returning the product;
- show discrepancy resolution.

### 4. Operational evidence

Show Retailer Operations:

- cart comparison;
- discrepancy reason;
- review queue if escalation is demonstrated.

### 5. Technical evidence

Show AI Monitoring:

- core health;
- camera/Vision telemetry;
- detector runtime;
- event stream;
- reconciliation inspection.

## Safe live sequence

```text
DISARMED
  ↓
camera + detector stable
  ↓
POST /control/arm
  ↓
fresh baseline
  ↓
BASELINE READY
  ↓
perform controlled pickup
  ↓
perform matching scan
  ↓
verify final resolution
  ↓
POST /control/disarm
```

## Deterministic demo profile

The protected simulator is included as a deterministic event-source profile that exercises the exact same Core reconciliation path as Vision. It is useful for presenting the transaction engine independently from camera-network conditions.

## Camera framing for judges

State clearly: **Phone 1 is the hackathon camera source. A retail deployment consumes fixed CCTV/NVR RTSP through the same Vision adapter.**

Punchline: **See the shelf. Trust the cart. Keep checkout moving.**
