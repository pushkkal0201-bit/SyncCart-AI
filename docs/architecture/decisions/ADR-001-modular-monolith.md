# ADR-001: Modular monolith first

## Status
Accepted.

## Decision
Use one FastAPI deployment with explicit modules and repository/service boundaries for the v1 release.

## Why
It preserves industrial boundaries without paying the networking, deployment, and debugging tax of premature microservices. Vision remains a separate worker because long-running inference has different runtime characteristics.
