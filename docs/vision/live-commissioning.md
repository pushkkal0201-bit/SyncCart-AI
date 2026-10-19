# Phase 7 — Live hardware commissioning

Phase 7 controls when physical camera evidence is allowed to mutate the SyncCart physical cart. Camera and detector processing can run continuously while event publication remains disarmed.

## Safety sequence

1. Start Core and Vision.
2. Keep `VISION_EVENTS_ARMED=false` during setup.
3. Verify `/preview.mjpeg`, `/metrics`, planogram, detector, and camera health.
4. Start exactly one customer shopping session for the watched zone.
5. Arm with `POST /control/arm` and `X-Vision-Control-Key`.
6. Wait until `/control/status` reports `baseline_status=READY`.
7. Perform the pickup/return flow.
8. Disarm after the run.

## Commissioning command

```powershell
python scripts\commission_synccart.py `
  --camera-source "http://PHONE-IP:PORT/video"
```

Reports are written under `runtime/`.

## Live end-to-end run

```powershell
python scripts\e2e_demo_runner.py `
  --mode live `
  --vision-control-key "YOUR-VISION-CONTROL-KEY"
```

The runner creates an anonymous session, arms Vision, waits for a stable baseline, waits for a real `VISION_PICKUP`, digitally scans the configured barcode, confirms reconciliation, and disarms Vision.

## Deterministic event-source run

```powershell
python scripts\e2e_demo_runner.py `
  --mode simulator `
  --simulator-key "YOUR-SIMULATOR-KEY"
```

This mode demonstrates the same transaction and reconciliation state machine without depending on camera-network conditions.

## Frozen-stream handling

The Vision worker fingerprints tiny grayscale frames. If the same frame repeats beyond `FROZEN_FRAME_LIMIT`, the camera is marked degraded, telemetry is published, and the source is reopened. The threshold is conservative because a shelf can remain visually static for long periods.
