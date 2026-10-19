# Retailer Operations App — Phase 4C

The Retailer Operations App is a distinct operational surface for store colleagues. It intentionally excludes engineering-only metrics such as GPU utilization and raw model diagnostics.

## Responsibilities

- current store-level status and active session counts;
- live shopping-session list;
- physical-vs-digital cart comparison;
- explainable discrepancy evidence;
- exception-only review queue;
- immutable event timeline;
- targeted operator resolution;
- live operational WebSocket snapshots;
- lightweight operational analytics.

## Access boundary

Phase 4C uses `X-Store-Key` as the local store-operations boundary. The browser stores this key in `sessionStorage`, not persistent local storage. Enterprise identity can be attached to the same authorization boundary without changing store workflows.

Deployment integration options:

1. employee identity provider;
2. short-lived access tokens;
3. role-based access control;
4. store/region scoping;
5. audited privileged actions.

## Review safety model

The operator application never creates a fake `PRODUCT_SCANNED` event.

When a colleague confirms a false Vision detection or a physical return, SyncCart corrects the **physical cart projection** and writes a `REVIEW_RESOLVED` operator event. If a customer must actually scan an item, that scan still has to arrive through the customer transaction path.

## Realtime channel

`/ws/store?key=<store-key>` sends `store.snapshot` payloads. The retailer client also periodically refreshes over REST so temporary WebSocket failure does not make the operational screen stale indefinitely.


## Product specification

For the complete store-colleague journey, operational features, resolution integrity, and production access model, see [`docs/product/retailer-app.md`](../product/retailer-app.md).
