# Source Completeness Audit

The final IIT Bombay hackathon repository was built from the previously polished full-source snapshot and then upgraded with production CCTV/NVR support documentation, generic camera-source tooling, camera credential redaction, product specifications, and deployment guidance.

## Preservation audit

A path-level comparison was performed against the previous polished source bundle for source/document/config file types (`.py`, `.ts`, `.tsx`, `.css`, `.html`, `.toml`, `.yaml`, `.yml`, `.json`, `.ps1`, `.md`), excluding generated runtime/cache directories.

```text
Comparable files in previous polished repo: 222
Comparable files in final polished repo:    232
Previous files missing from final repo:       0
New source/docs/config files added:           10
```

## New additions

- production CCTV/NVR deployment documentation;
- Phone 1 vs production CCTV mapping;
- camera-source runtime contract;
- vendor-neutral camera-source examples;
- generic camera probe command;
- camera credential redaction tests;
- customer product/technical specification;
- retailer product/technical specification;
- feature/punchline brief;
- retail deployment checklist.

## Current repository inventory

At packaging time after cache cleanup:

```text
Python files:        120
TypeScript/TSX:       18
Markdown documents:   61
Python test files:     18
Total tracked-source-style files/folders package files: 250
```

## Automated verification

```text
pytest -q
59 passed
```

## Intentionally excluded artifacts

The following are not source-code omissions and are deliberately excluded from the GitHub bundle:

- Python virtual environments;
- `node_modules`;
- `.env` secrets and real camera credentials;
- local SQLite/test databases;
- raw camera captures;
- annotated datasets;
- YOLO training runs;
- trained weight binaries;
- transient caches.

The code required to recreate the supported camera, dataset, training, evaluation, and commissioning workflows remains in the repository.
