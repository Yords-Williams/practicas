import modulos.robo.inference as inference


def test_theft_detector_uses_cpu_when_cuda_is_unavailable(monkeypatch):
    monkeypatch.setattr(inference.torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(inference, "YOLO", lambda _model_path: object())

    detector = inference.TheftDetectionSystem()

    assert detector.device == "cpu"


def test_theft_detector_uses_cuda_device_zero_when_available(monkeypatch):
    monkeypatch.setattr(inference.torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(
        inference.torch.cuda,
        "get_device_name",
        lambda _device_index: "Test GPU",
    )
    monkeypatch.setattr(inference, "YOLO", lambda _model_path: object())

    detector = inference.TheftDetectionSystem()

    assert detector.device == 0
