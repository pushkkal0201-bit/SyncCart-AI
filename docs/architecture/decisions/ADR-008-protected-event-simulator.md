# ADR-008: Protected physical-event simulator as the Phase 3 input adapter

## Status

Accepted.

## Context

The complete cart-reconciliation product loop must be proven before introducing model training, phone streaming, lighting variance, and shelf-count noise.

## Decision

Provide simulator endpoints that create the same normalized `VISION_PICKUP` and `VISION_RETURN` events the Vision worker emits.

Simulator endpoints:

- are disabled by configuration when not required;
- require `X-Simulator-Key`;
- support `Idempotency-Key`;
- apply the same confidence gate and physical-cart service used by Vision integration.

## Consequences

Backend behavior can be tested deterministically. Phase 6/7 will replace only the input adapter, not the reconciliation domain.
