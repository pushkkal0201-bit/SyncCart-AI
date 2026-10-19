# ADR-010 — Separate Monitoring / AI Operations Surface

## Status
Accepted for Phase 4D.

## Context
Customer, retailer, and AI/system operators have different responsibilities and different acceptable information density. Combining them into one dashboard would expose technical controls to store staff and operational review controls to engineers unnecessarily.

## Decision
Create a third React application, `apps/monitoring-web`, backed by protected `/api/v1/admin/*` APIs and `/ws/admin` realtime snapshots.

The monitoring app owns engineering observability. The retailer app owns store exception handling. The customer app owns Scan-and-Go interaction.

## Consequences
- clearer authorization boundaries;
- less accidental disclosure of internal model/runtime details;
- independent UX optimized for each role;
- shared platform types, API client, realtime client, and design tokens still prevent duplication.
