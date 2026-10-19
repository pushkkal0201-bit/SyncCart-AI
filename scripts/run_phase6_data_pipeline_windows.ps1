param(
    [string]$Source = "0"
)

$ErrorActionPreference = "Stop"
Write-Host "[1/3] Probing camera source $Source" -ForegroundColor Cyan
python scripts\probe_camera_source.py --source $Source

Write-Host "[2/3] Dataset validator" -ForegroundColor Cyan
python ml\dataops\validate_yolo_dataset.py --data ml\datasets\demo_sku\dataset.yaml

Write-Host "[3/3] Next action" -ForegroundColor Cyan
Write-Host "Capture real camera data (CCTV/NVR or Phone 1 hackathon camera), annotate it, then prepare splits and train."
Write-Host "See docs\vision\data-collection.md and docs\vision\training-evaluation.md"
