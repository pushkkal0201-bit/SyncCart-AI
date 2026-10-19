# Phase 6 — Training, evaluation, benchmarking, and registration

## Install ML dependencies

```powershell
pip install -e ".\services\vision[yolo]"
```

## Validate dataset first

```powershell
python ml\dataops\validate_yolo_dataset.py --fail-on-invalid
```

Do not train against a broken or leaking dataset simply because the GPU is feeling underused.

## Train

```powershell
python ml\training\train_yolo.py `
  --device cpu `
  --epochs 80 `
  --batch 8
```

If the laptop has a supported NVIDIA CUDA setup, `--device 0` may be used after verifying the environment.

## Evaluate on the held-out test split

```powershell
python ml\evaluation\evaluate_model.py `
  --weights runtime\training\synccart-sku-v001\weights\best.pt `
  --split test `
  --device cpu
```

This writes measured precision, recall, mAP50, mAP50-95, and Ultralytics timing information to `runtime/evaluation/`.

## Benchmark on the actual laptop

```powershell
python ml\evaluation\benchmark_model.py `
  --weights runtime\training\synccart-sku-v001\weights\best.pt `
  --device cpu
```

Use these measured values in the final presentation instead of invented FPS numbers.

## Register only after evaluation

```powershell
python ml\evaluation\register_model.py `
  --weights runtime\training\synccart-sku-v001\weights\best.pt `
  --metrics runtime\evaluation\synccart-sku-v001.metrics.json
```

Registration copies the validated model to the runtime weight location and updates registry metadata/model card.

## Calibrate shelf zones

After the final camera geometry is fixed:

```powershell
python scripts\calibrate_planogram.py `
  --source "http://PHONE-IP:PORT/video"
```

The tool asks you to draw each shelf zone and updates normalized planogram coordinates while preserving a backup.
