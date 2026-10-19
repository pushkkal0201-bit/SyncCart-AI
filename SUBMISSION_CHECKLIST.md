# IIT Bombay Hackathon Submission Checklist

Before sharing the GitHub URL:

- [ ] Repository visibility matches the hackathon requirement.
- [ ] `README.md` renders correctly, including Mermaid diagrams.
- [ ] `git status` is clean.
- [ ] `.env`, `.venv`, `node_modules`, local databases, captures, and model binaries are not committed.
- [ ] `python scripts/verify_submission.py --run-tests` passes locally.
- [ ] GitHub contains `apps/`, `services/`, `packages/`, `ml/`, `scripts/`, `config/`, `docs/`, and tests.
- [ ] Current SKU contract is `copy`, `olive_oil`, `bottle`.
- [ ] README explains CCTV/NVR as the retail camera architecture and Phone 1 as the hackathon camera profile.
- [ ] `docs/vision/cctv-production-deployment.md` renders correctly.
- [ ] No real RTSP usernames/passwords are committed.
- [ ] Customer, Retailer Operations, and AI Monitoring apps are visible in repository navigation.
- [ ] The fixed-zone detector is selected through `DETECTOR_MODE=AUTO` or `ZONE_OCCUPANCY` for the calibrated shelf demo.
- [ ] The repository URL opens for judges without additional access requests when public access is required.

Recommended final commit message:

```text
SyncCart AI v1.0 — IIT Bombay hackathon submission
```
