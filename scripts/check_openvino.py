"""Comprueba si OpenVINO ve la GPU integrada Intel (UHD 630)."""

from openvino import Core


def main() -> int:
    core = Core()
    devices = core.available_devices
    print("Dispositivos OpenVINO:", ", ".join(devices) or "ninguno")

    gpu_devices = [device for device in devices if device.startswith("GPU")]
    if not gpu_devices:
        print("No se detectó GPU Intel. Actualiza el controlador Intel UHD/OpenCL.")
        return 1

    for device in gpu_devices:
        try:
            name = core.get_property(device, "FULL_DEVICE_NAME")
        except Exception:
            name = "nombre no disponible"
        print(f"✓ {device}: {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
