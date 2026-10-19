from synccart_vision.camera import infer_source_kind, redact_camera_source


def test_camera_source_kind_detection():
    assert infer_source_kind("0") == "WEBCAM"
    assert infer_source_kind("rtsp://10.0.0.2/live") == "RTSP_CCTV"
    assert infer_source_kind("https://10.0.0.3/video") == "HTTP_MJPEG"
    assert infer_source_kind("demo.mp4") == "VIDEO_FILE"


def test_camera_source_redacts_credentials():
    value = redact_camera_source("rtsp://admin:secret@10.0.0.2:554/live/ch1")
    assert value == "rtsp://10.0.0.2:554/live/ch1"
    assert "admin" not in value
    assert "secret" not in value
