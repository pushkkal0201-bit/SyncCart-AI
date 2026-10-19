# Reconciliation Engine

## Purpose

The reconciliation engine is the core product logic. It does not classify shoppers. It compares two independent cart projections and explains disagreement.

## Inputs

Physical events:

- `VISION_PICKUP`
- `VISION_RETURN`

Digital events:

- `PRODUCT_SCANNED`
- `DIGITAL_ITEM_REMOVED`

## Event matching

A new physical or digital event attempts to match the latest unmatched opposite-side event when all of the following hold:

1. same shopping session;
2. same SKU;
3. same event quantity;
4. compatible event direction;
5. event timestamps fall within `EVENT_MATCH_WINDOW_MS`;
6. neither event has already been matched.

Compatible pairs are:

- `VISION_PICKUP` ↔ `PRODUCT_SCANNED`
- `VISION_RETURN` ↔ `DIGITAL_ITEM_REMOVED`

A successful pairing creates an `event_matches` row and immutable `MATCH_CONFIRMED` event.

## Cart-level reconciliation

Matching individual events is useful evidence, but cart truth is ultimately calculated from the projections:

```text
difference = physical_quantity - digital_quantity
```

Interpretation:

- `difference == 0`: aligned;
- `difference > 0`: physically present quantity exceeds scanned quantity;
- `difference < 0`: digital quantity exceeds currently observed physical quantity.

## Grace window

A mismatch does not immediately create customer-facing intervention.

```text
DISCREPANCY_OPENED
        |
        v
    VERIFYING
        |
        | SCAN_GRACE_PERIOD_MS
        v
```

If physical quantity remains ahead, SyncCart creates a neutral soft nudge.

If digital quantity remains ahead, the system escalates to review rather than blaming the customer because this condition can indicate delayed/failed vision.

## Risk score

Phase 3 uses an explicit heuristic, not a trained theft model.

The score combines:

- quantity gap;
- time unmatched;
- latest physical-event confidence;
- whether intervention has already occurred.

The heuristic is deliberately configuration-driven and is **not** presented as scientifically calibrated production risk.

## Explainability

The API returns human-readable reasons such as:

```text
SOAP-001: physical=1, digital=0, difference=1, status=NUDGE_SENT
SOAP-001: vision confidence=0.95
```

The dashboard phase will render the same evidence rather than a mystery red score.

## Failure-safe behavior

Low-confidence physical events are rejected before cart mutation using `MIN_VISION_CONFIDENCE`.

The Vision worker can therefore degrade gracefully without silently corrupting cart state.
