# ADR-004: Shelf-count change before hand-action recognition

## Status
Accepted.

## Decision
The release Vision profile will infer pickup/return events from stable per-SKU shelf-count changes.

## Why
It is easier to validate with two phones and a laptop, requires less data, and directly produces the physical-cart event that reconciliation needs.
