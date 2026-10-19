# Optional model weights

Large trained binaries are intentionally excluded from Git repository history.

The complete v1.0 demo runs with the built-in fixed-zone reference detector. To switch to the optional custom YOLO profile, place an Ultralytics-compatible weight file at:

```text
models/weights/synccart-sku-v001.pt
```

Then use:

```env
DETECTOR_MODE=YOLO
```

or keep:

```env
DETECTOR_MODE=AUTO
```

`AUTO` selects YOLO when the weight file is available and otherwise uses the fixed-zone reference detector.
