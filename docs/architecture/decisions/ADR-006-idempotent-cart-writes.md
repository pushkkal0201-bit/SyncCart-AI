# ADR-006 — Idempotent digital-cart writes

## Status

Accepted in Phase 2.

## Context

Mobile networks, browser retries, and barcode scanners can resend the same logical action. A repeated request must not silently add the product twice.

## Decision

Cart mutation endpoints accept an optional `Idempotency-Key`. The backend stores a request fingerprint and original response under the session and operation. A matching retry returns the saved response. A mismatched retry is rejected.

A second independent protection suppresses repeated barcode detections inside a configurable short interval.

## Consequences

- safe retries are possible;
- barcode double-reads are reduced;
- persistent idempotency storage adds one small database table;
- clients should generate a new key for each new intended mutation.
