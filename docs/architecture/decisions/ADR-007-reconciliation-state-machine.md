# ADR-007: Reconciliation state machine before Vision integration

## Status

Accepted.

## Context

SyncCart must distinguish internal verification, customer correction, and colleague review. A binary `match / mismatch` flag cannot represent this safely.

## Decision

Use explicit session-facing states:

- `CLEAR`
- `VERIFY`
- `NUDGE`
- `REVIEW`
- `RESOLVED`

Discrepancies independently use:

- `VERIFYING`
- `NUDGE_SENT`
- `REVIEW_REQUIRED`
- `RESOLVED`

Grace periods and review escalation are configuration-driven.

## Consequences

The workflow is explainable and testable. Phase 4 can subscribe to `NUDGE_SENT` without inventing UI-side business rules, and the Vision service publishes the same normalized events.
