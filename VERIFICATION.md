# Verification — SyncCart AI v1.0

This file records repository checks executed for the IIT Bombay hackathon submission build.

## Automated verification

| Check | Result |
|---|---|
| Python test suite | **60 passed** |
| Python syntax / import compilation | **PASS** |
| Submission static verifier | **PASS** |
| Current Vision class contract | `copy`, `olive_oil`, `bottle` |
| Calibration CLI display resize | **PRESENT** |
| Vision control endpoints | **PRESENT** |
| Frozen-frame handling | **PRESENT** |
| CCTV/NVR RTSP path | **SUPPORTED** |
| HTTP/MJPEG / Phone 1 path | **SUPPORTED** |
| Fixed-zone reference detector | **PRESENT** |
| Optional YOLO adapter | **PRESENT** |
| Camera credential redaction | **PRESENT** |
| Raw capture folders in source bundle | **EXCLUDED** |
| `.env` secrets in source bundle | **EXCLUDED** |
| `.venv` / `node_modules` | **EXCLUDED** |

## Re-run locally

```powershell
python scripts\verify_submission.py --run-tests
```

Frontend verification commands:

```powershell
npm install
npm run typecheck
npm run build
```
