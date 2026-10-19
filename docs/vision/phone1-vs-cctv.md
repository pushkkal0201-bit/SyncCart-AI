# Phone 1 Hackathon Camera vs Retail CCTV

SyncCart deliberately separates the **camera hardware** from the **Vision logic**.

| Area | Hackathon camera profile | Real retail deployment |
|---|---|---|
| Camera | Android Phone 1 running IP Webcam | Existing fixed CCTV / IP camera / NVR channel |
| Stream | HTTP/MJPEG | Usually RTSP; HTTP/MJPEG also supported |
| Network | Same Wi-Fi / hotspot | Store camera/IoT VLAN |
| Camera ID | `PHONE-1-SHELF-CAM` | Stable store/aisle/camera identifier |
| Credentials | Local hackathon network | Dedicated read-only secret-managed account |
| Position | Manually fixed for demo | Permanently mounted and surveyed |
| Inference | Laptop / edge PC | Retail edge server / mini PC / GPU node |
| Video retention | Not required by SyncCart core | Controlled by retailer CCTV policy |
| Core event contract | Same | Same |

## Why Phone 1 is valid for the hackathon camera profile

Phone 1 is not the product architecture. It is a low-cost **camera emulator** that lets the team validate:

- live network stream ingestion;
- reconnect and frozen-frame handling;
- shelf-zone calibration;
- real image collection;
- inference and count stabilization;
- `VISION_PICKUP` / `VISION_RETURN` event publishing.

When replaced by CCTV, the downstream pipeline remains:

```text
camera stream -> OpenCV -> detector -> planogram -> stabilized counts -> events -> reconciliation
```

This lets the hackathon demonstrate real hardware integration without pretending that phones would be permanently mounted across a retail chain.
