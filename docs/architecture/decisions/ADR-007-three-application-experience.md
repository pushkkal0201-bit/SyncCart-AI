# ADR-007: Three application experiences on one SyncCart Core

## Status
Accepted for Phase 4 onward.

## Decision
SyncCart will expose three separate frontend experiences backed by the same domain services and database:

1. Customer Scan-and-Go PWA.
2. Retailer Operations application.
3. Monitoring / AI Operations application.

Shared packages provide types, API clients, realtime clients, and design primitives. Business logic remains server-side.

## Rationale
The three users have materially different jobs. A customer needs a minimal scan/cart/nudge/checkout flow; store colleagues need operational exceptions; engineers need camera, model, event, and system telemetry. Combining them creates unnecessary permissions, cognitive load, and accidental data exposure.

## Consequences
Frontend authorization and API boundaries will become role-aware in later phases. Phase 4A establishes shared packages; Phase 4B implements the customer application first.
