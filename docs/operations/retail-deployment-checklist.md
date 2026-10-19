# Retail Deployment Checklist

## Camera

- [ ] final shelf and camera geometry approved
- [ ] production CCTV/NVR stream available
- [ ] fixed camera ID assigned
- [ ] stream credentials stored outside Git
- [ ] edge node can reach camera VLAN
- [ ] camera probe passes
- [ ] frozen-frame recovery tested

## Vision

- [ ] planogram calibrated after final camera mounting
- [ ] model evaluated on the actual camera view
- [ ] per-class failure cases reviewed
- [ ] Vision starts disarmed
- [ ] fresh baseline reaches `READY`
- [ ] pickup and return events validated

## Core

- [ ] DB migrations applied
- [ ] catalog mapped to model SKUs
- [ ] Vision API key configured
- [ ] idempotency and event logging enabled
- [ ] WebSocket and REST paths reachable

## Customer app

- [ ] HTTPS available for browser camera/barcode features
- [ ] anonymous session creation works
- [ ] barcode catalog lookup works
- [ ] nudge actions tested
- [ ] checkout reconciliation tested

## Retailer app

- [ ] store authentication configured
- [ ] review queue tested
- [ ] false-Vision resolution tested
- [ ] audit trail reviewed

## Privacy / governance

- [ ] no facial recognition enabled
- [ ] raw video retention follows retailer CCTV policy
- [ ] access logs and credentials scoped
- [ ] user-facing notices reviewed by retailer governance team
