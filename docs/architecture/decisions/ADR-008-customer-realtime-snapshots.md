# ADR-008: WebSocket snapshot stream for the Phase 4 customer app

## Status
Accepted for the v1 local release.

## Decision
The customer PWA connects to `/ws/customer/{session_id}` using its temporary session token. The backend sends a reconciliation snapshot whenever the serialized state changes and emits heartbeat messages periodically.

## Why snapshots first
For one controlled shopper session this is reliable, easy to reason about, and keeps the client stateless. The backend remains authoritative for cart and discrepancy state.

## Production evolution
At pilot scale, replace per-socket state polling with event-driven fan-out using Redis Streams/PubSub or a store event bus. The public WebSocket message schema can remain stable.

## Security note
The v1 local release passes the temporary token as a WebSocket query parameter because browser WebSocket APIs cannot set arbitrary headers. Internet-facing enterprise deployments can use a short-lived socket ticket or secure cookie at the same authorization boundary.
