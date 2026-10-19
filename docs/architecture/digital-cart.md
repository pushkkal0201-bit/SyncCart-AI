# Phase 2 — Digital Cart Architecture

## Goal

Phase 2 proves the customer transaction side before Vision AI is connected.

The implemented flow is:

```text
Phone 2 / API client
      |
      | barcode + X-Session-Token
      v
POST /api/v1/sessions/{id}/scan
      |
      +--> product barcode lookup
      +--> duplicate-scan suppression
      +--> idempotency check
      +--> immutable PRODUCT_SCANNED event
      +--> DIGITAL cart projection update
      v
GET /api/v1/sessions/{id}/cart
```

## Customer session token

`POST /api/v1/sessions` now issues a high-entropy temporary customer token.
Only a SHA-256 hash is stored in the database. The raw token is returned once to the caller.

Customer cart endpoints require:

```http
X-Session-Token: <token>
```

The token is intentionally separate from store-operator authentication.

## Idempotency

Cart mutations support:

```http
Idempotency-Key: <client-generated-key>
```

The server stores a request fingerprint and the serialized mutation response. Replaying the same key with the same payload returns the original result without mutating the cart again. Reusing the key with a different payload returns `IDEMPOTENCY_CONFLICT`.

## Duplicate barcode suppression

A phone camera can emit the same barcode several times in a very short interval. A configurable duplicate window prevents these repeated reads from incrementing the cart repeatedly.

Configuration:

```env
DUPLICATE_SCAN_WINDOW_MS=1500
```

This is distinct from idempotency:

- idempotency protects retried API writes;
- duplicate suppression protects repeated scanner detections.

## Cart projection

The `cart_items` table continues to support both `DIGITAL` and `PHYSICAL` projections.
Phase 2 mutates only the digital projection.

Phase 3 will ingest simulated physical events into the physical projection and reconcile the two.
