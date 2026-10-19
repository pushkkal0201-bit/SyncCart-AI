# Phase 6 — Real Camera Dataset Collection

Phase 6 converts the Vision subsystem from *software-ready* to *data-ready*. No accuracy numbers are claimed until a held-out test set is evaluated.

## 1. Fix the final camera geometry

Do not collect most of the dataset handheld. The training distribution should resemble deployment: fixed camera, final shelf height, representative lighting, and the same approximate distance used during the demo.

## 2. Probe the camera before collecting data

```powershell
python scripts\probe_camera_source.py `
  --source "http://PHONE-IP:PORT/video"
```

This writes `runtime/camera_probe.json` with measured read FPS, resolution, brightness, blur, and a simple frozen-frame warning signal.

## 3. Capture multiple independent sessions

Do not capture all 300–500 images in one continuous burst. That produces near-identical frames and overly optimistic validation.

Recommended minimum plan:

| Capture session | Purpose | Suggested accepted frames |
|---|---|---:|
| 01 | normal full / partial shelf | 50–70 |
| 02 | different lighting | 40–60 |
| 03 | product rotation / displacement | 40–60 |
| 04 | hand occlusion | 40–60 |
| 05 | partially empty shelves | 40–60 |
| 06 | mixed distance / minor camera exposure change | 40–60 |
| 07 | difficult but realistic cases | 40–60 |

Example:

```powershell
python scripts\capture_vision_dataset.py `
  --source "http://PHONE-IP:PORT/video" `
  --session session-01 `
  --scenario full-shelf `
  --auto `
  --every 20 `
  --max-saved 60
```

Controls:

- `SPACE`: save only if quality and duplicate checks pass
- `F`: force-save a frame intentionally
- `A`: toggle automatic capture
- `Q` / `Esc`: stop

Each capture session contains original images plus JSONL metadata with brightness, blur, scenario, timestamp, source, and perceptual hash.

## 4. Annotation

Annotate the three live-demo object classes exactly as:

```text
0 copy
1 olive_oil
2 bottle
```

Export YOLO detection labels. Put the annotated pool into:

```text
runtime/annotated-pool/
├── images/
└── labels/
```

The label filename must match the image stem.

## 5. Prepare leakage-resistant splits

The capture script names files as:

```text
session-01__full-shelf__00001.jpg
```

`prepare_yolo_dataset.py` keeps the same capture session in one split, reducing frame leakage between train, validation, and test sets.

```powershell
python ml\dataops\prepare_yolo_dataset.py `
  --source runtime\annotated-pool `
  --output ml\datasets\demo_sku `
  --clean
```

Default split is 70% train / 15% validation / 15% test by capture-session group.

## 6. Validate before training

```powershell
python ml\dataops\validate_yolo_dataset.py `
  --data ml\datasets\demo_sku\dataset.yaml `
  --fail-on-invalid
```

The validator checks missing labels, malformed class IDs, out-of-range boxes, class balance, exact perceptual duplicates, and cross-split duplicates.
