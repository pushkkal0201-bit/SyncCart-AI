# ADR-002: Event-driven domain history

## Status
Accepted.

## Decision
Important business changes generate immutable events.

## Why
Reconciliation, auditability, debugging, and judge-facing explainability all require a trustworthy timeline. Mutable cart rows remain current projections; events preserve history.
