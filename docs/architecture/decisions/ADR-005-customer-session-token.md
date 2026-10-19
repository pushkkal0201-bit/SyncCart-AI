# ADR-005 — Temporary customer session token

## Status

Accepted in Phase 2.

## Context

Phone 2 needs to mutate and read one anonymous shopping session without exposing a permanent customer identity.

## Decision

At session creation, SyncCart generates a high-entropy temporary customer token. Only its SHA-256 digest is stored. Customer cart operations require the raw token through `X-Session-Token`.

## Consequences

- cart access is scoped to the anonymous shopping session;
- the database does not contain the reusable raw customer token;
- store-staff authentication remains a separate concern for a later phase;
- sessions created before this ADR must be recreated before using customer cart APIs.
