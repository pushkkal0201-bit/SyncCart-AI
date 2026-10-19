# ADR-009 — Separate retailer operations from customer and engineering interfaces

**Status:** Accepted

## Decision

SyncCart uses three distinct applications over one shared backend domain:

1. Customer Scan-and-Go PWA;
2. Retailer Operations App;
3. Monitoring / AI Operations App.

## Why

Store colleagues need concise, action-oriented evidence. They should not need Vision-engineering logs, model-registry controls, or infrastructure metrics. Conversely, customers must never see internal risk heuristics.

A separate Retailer App allows us to expose only operational concepts: sessions, cart differences, nudges, reviews, evidence, and resolution actions.

## Consequences

- shared domain and API remain the source of truth;
- frontends share types, network clients, realtime clients, and design tokens;
- authorization can evolve independently by audience;
- UI density and vocabulary can match the user role.
