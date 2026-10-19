# SyncCart SKU Detector v001

## Role

This model card defines the optional YOLO detector profile for the three-SKU SyncCart shelf contract.

The v1.0 repository does not require this binary profile to run the end-to-end demo because `DETECTOR_MODE=AUTO` falls back to the built-in fixed-zone reference detector when a YOLO weight file is not supplied.

## Classes

- `copy`
- `olive_oil`
- `bottle`

## Expected artifact

```text
models/weights/synccart-sku-v001.pt
```

## Runtime contract

The YOLO adapter converts model detections to the same normalized planogram observations and `VISION_PICKUP` / `VISION_RETURN` events used by the fixed-zone detector.

## Privacy boundary

The detector operates on products and shelf zones. It does not require face recognition, demographic inference, emotion recognition, or criminal-intent classification.

## Registration workflow

```text
Capture → Annotate → Prepare → Validate → Train → Evaluate → Benchmark → Register
```

Tooling is provided under `ml/` and `scripts/`.
