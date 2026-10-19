# Deployment Scale Profiles

This document describes supported architecture profiles rather than repository completion status.

## Hackathon profile

- Phone 1 or webcam / RTSP source;
- one calibrated shelf;
- one eligible active shopper in the watched zone;
- fixed-zone reference detector or YOLO detector;
- SQLite;
- three web applications;
- local API-key boundaries.

## Retail edge profile

- fixed CCTV / NVR RTSP;
- edge Vision workers;
- PostgreSQL;
- store identity adapter;
- multiple camera workers;
- centralized monitoring;
- governed camera credentials.

## Enterprise scale profile

The same domain contracts support store-fleet orchestration, centralized observability, multi-camera topology, identity-provider integration, and retailer-specific deployment governance without changing the physical/digital cart reconciliation model.
