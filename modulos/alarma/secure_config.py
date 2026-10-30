import base64
import ctypes
from ctypes import wintypes


_PREFIX = "dpapi:"


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def _crypt(data, protect):
    if not hasattr(ctypes, "windll"):
        raise OSError("Windows DPAPI solo está disponible en Windows.")

    source_buffer = ctypes.create_string_buffer(data)
    source = _DataBlob(
        len(data),
        ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_byte)),
    )
    destination = _DataBlob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    operation = (
        crypt32.CryptProtectData
        if protect
        else crypt32.CryptUnprotectData
    )
    operation.argtypes = [
        ctypes.POINTER(_DataBlob),
        wintypes.LPCWSTR,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    operation.restype = wintypes.BOOL

    if not operation(
        ctypes.byref(source),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(destination),
    ):
        raise ctypes.WinError(ctypes.get_last_error())

    try:
        return ctypes.string_at(destination.pbData, destination.cbData)
    finally:
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p
        kernel32.LocalFree(destination.pbData)


def protect_secret(secret):
    if not secret or secret.startswith(_PREFIX):
        return secret
    encrypted = _crypt(secret.encode("utf-8"), protect=True)
    return _PREFIX + base64.b64encode(encrypted).decode("ascii")


def unprotect_secret(secret):
    if not secret or not secret.startswith(_PREFIX):
        return secret
    encrypted = base64.b64decode(secret[len(_PREFIX):], validate=True)
    return _crypt(encrypted, protect=False).decode("utf-8")


def transform_notification_secrets(config, transform):
    transformed = dict(config)
    for section, key in (("telegram", "token"), ("gmail", "app_password")):
        values = dict(transformed.get(section, {}))
        if values.get(key):
            values[key] = transform(values[key])
        profiles = {}
        for profile_name, profile in values.get("profiles", {}).items():
            profile_values = dict(profile)
            if profile_values.get(key):
                profile_values[key] = transform(profile_values[key])
            profiles[profile_name] = profile_values
        if "profiles" in values:
            values["profiles"] = profiles
        transformed[section] = values
    return transformed


def protect_notification_secrets(config):
    return transform_notification_secrets(config, protect_secret)


def unprotect_notification_secrets(config):
    return transform_notification_secrets(config, unprotect_secret)
