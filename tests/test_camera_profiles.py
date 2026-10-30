import pytest
import time

from camera import CamaraRTSP


def make_camera(high_resolution_url="rtsp://camera/main"):
    camera = CamaraRTSP.__new__(CamaraRTSP)
    camera.url = "rtsp://camera/sub"
    camera.high_resolution_url = high_resolution_url
    camera.current_url = camera.url
    camera.frame = object()
    camera.active_profile = "mosaic"
    camera.requested_profile = "mosaic"
    camera.display_size = (384, 216)
    camera.connect_calls = 0
    camera.connect = lambda: setattr(camera, "connect_calls", camera.connect_calls + 1)
    return camera


def test_single_profile_switches_to_mainstream_and_requested_resolution():
    camera = make_camera()

    camera.set_stream_profile("single", (1280, 720))
    assert camera.current_url == "rtsp://camera/sub"
    camera._apply_requested_profile()

    assert camera.current_url == "rtsp://camera/main"
    assert camera.display_size == (1280, 720)
    assert camera.frame is None
    assert camera.connect_calls == 1


def test_mosaic_profile_returns_to_substream():
    camera = make_camera()
    camera.set_stream_profile("single", (1920, 1080))
    camera._apply_requested_profile()

    camera.set_stream_profile("mosaic", (384, 216))
    camera._apply_requested_profile()

    assert camera.current_url == "rtsp://camera/sub"
    assert camera.display_size == (384, 216)
    assert camera.connect_calls == 2


def test_single_profile_without_mainstream_keeps_current_stream():
    camera = make_camera(high_resolution_url="")
    camera.set_stream_profile("single", (1280, 720))
    camera._apply_requested_profile()

    assert camera.current_url == "rtsp://camera/sub"
    assert camera.display_size == (1280, 720)
    assert camera.connect_calls == 0


def test_invalid_camera_profile_is_rejected():
    camera = make_camera()

    with pytest.raises(ValueError):
        camera.set_stream_profile("high", (1280, 720))


def test_camera_constructor_does_not_wait_for_stream_connection(monkeypatch):
    import threading

    connection_started = threading.Event()
    allow_connection = threading.Event()

    def blocked_connect(camera):
        connection_started.set()
        allow_connection.wait(timeout=2)

    monkeypatch.setattr(CamaraRTSP, "connect", blocked_connect)
    started_at = time.monotonic()
    camera = CamaraRTSP("rtsp://slow-camera/stream", "Lenta")
    try:
        assert time.monotonic() - started_at < 0.5
        assert connection_started.wait(timeout=0.2)
        assert camera.thread.is_alive()
    finally:
        camera.stop()
        allow_connection.set()
        camera.thread.join(timeout=1)
