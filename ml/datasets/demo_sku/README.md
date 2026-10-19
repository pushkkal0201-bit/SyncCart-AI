# SyncCart demo SKU dataset

This directory is intentionally empty of training images. Capture and annotate your own demo products rather than pretending a generic model knows your exact packaging.

Expected YOLO structure:

```text
ml/datasets/demo_sku/
├── dataset.yaml
├── images/
│   ├── train/
│   └── val/
└── labels/
    ├── train/
    └── val/
```

Use class names exactly as defined in `dataset.yaml`, because `config/vision_planogram.yaml` maps those model classes to SyncCart SKUs.
