# Impact, Innovation, and Benefits

## Innovation thesis

SyncCart AI treats Scan-and-Go loss prevention as a **state-reconciliation problem**.

Two independent systems describe the same shopping session:

```text
Physical reality: what the shelf camera says moved
Digital reality:  what the customer phone says was scanned
```

The platform creates value by reconciling those realities rather than attempting to classify customer intent.

## Innovation pillars

### Dual-source truth

Vision does not merely decorate the checkout flow; it independently produces a physical-cart projection.

### Privacy-preserving intervention

The system can operate without facial recognition or demographic inference because the primary object of reasoning is SKU quantity.

### Graduated friction

A temporary disagreement is not immediately escalated. The platform uses grace windows, matching, neutral nudges, and targeted review.

### Explainability by construction

Every intervention is tied to product/event evidence rather than an opaque shopper-risk label.

### Operational separation

Customer, retailer, and AI operations receive different interfaces because their jobs and information needs are different.


### Existing CCTV reuse

The production architecture consumes standard CCTV/NVR streams instead of requiring a dedicated phone or custom smart-cart camera. Phone 1 is strictly the hackathon camera emulator. This lowers the hardware barrier for a controlled pilot because the retailer can evaluate SyncCart against its existing camera estate where geometry and image quality are suitable.

### Edge-first deployment practicality

A store edge node can consume camera streams inside the camera VLAN, run SKU inference locally, and publish normalized events to the Core API. This reduces dependency on continuous cloud-video upload and keeps the transaction platform focused on event metadata.

### Vision safety controls

Live event emission can be disarmed while inference remains active. A new arm cycle requires a fresh stable baseline, which reduces accidental event emission during camera setup or shelf reset.

## Stakeholder benefits

### Shopper

- preserves the Scan-and-Go experience when carts already match;
- receives private, product-specific corrective prompts;
- avoids identity-based suspicion as a core product mechanism.

### Retail associate

- sees a targeted review queue;
- receives SKU-level evidence and reason codes;
- avoids manually reviewing every session.

### Retail manager

- can observe discrepancy lifecycle and resolution patterns;
- can separate operational issues from model/camera issues;
- gains a path to pilot measurement rather than anecdotal loss-prevention decisions.

### Engineering / AI operations

- independent monitoring surface;
- camera and inference health;
- event traceability;
- frozen-stream detection;
- explicit degraded states;
- model registration contract.

## Where SyncCart can be applied

The architecture is relevant to controlled environments where products are visually observable and digital declaration exists, including:

- Scan-and-Go retail;
- smart shelves;
- micro-markets;
- unattended retail pilots;
- controlled store-in-store experiences.

Actual deployment suitability depends on camera geometry, SKU visual separability, shopper density, store policy, and model performance.

## When SyncCart intervenes

1. physical/digital state diverges;
2. reconciliation waits for expected temporal correction;
3. persistent physical-ahead-of-digital state can produce a private nudge;
4. unresolved discrepancy can enter colleague review;
5. checkout performs a final consistency decision.

## Pilot KPIs

The system should be evaluated on measured operational and model metrics, including:

- discrepancy events per 100 sessions;
- auto-resolved match rate;
- nudge resolution rate;
- colleague review rate;
- false-review rate;
- mean discrepancy resolution time;
- checkout clear-to-exit rate;
- per-class precision / recall / mAP;
- event-level pickup/return precision and recall;
- inference latency;
- camera availability;
- frozen-stream recovery count.

No unmeasured KPI is represented as achieved performance in this repository.
