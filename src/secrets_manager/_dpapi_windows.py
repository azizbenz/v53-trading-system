"""Windows DPAPI backend used by the sealed-secrets slice."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes


CRYPTPROTECT_UI_FORBIDDEN = 0x01


class DpapiError(RuntimeError):
    """Raised when the Windows DPAPI backend cannot protect or unprotect data."""


if os.name == "nt":

    class _DataBlob(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
        ]


    _crypt32 = ctypes.windll.crypt32
    _kernel32 = ctypes.windll.kernel32
    _crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(_DataBlob),
        wintypes.LPCWSTR,
        ctypes.POINTER(_DataBlob),
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    _crypt32.CryptProtectData.restype = wintypes.BOOL
    _crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(_DataBlob),
        ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(_DataBlob),
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    _crypt32.CryptUnprotectData.restype = wintypes.BOOL
    _kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
    _kernel32.LocalFree.restype = wintypes.HLOCAL


def _build_blob(data: bytes) -> tuple[_DataBlob, ctypes.Array[ctypes.c_char]]:  # type: ignore[name-defined]
    buffer = ctypes.create_string_buffer(data)
    blob = _DataBlob(  # type: ignore[name-defined]
        cbData=len(data),
        pbData=ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)),
    )
    return blob, buffer


def _blob_to_bytes(blob: _DataBlob) -> bytes:  # type: ignore[name-defined]
    return ctypes.string_at(blob.pbData, blob.cbData)


def _require_windows() -> None:
    if os.name != "nt":
        raise DpapiError("Windows DPAPI backend is only available on Windows")


def protect_bytes(data: bytes, *, entropy: bytes, description: str = "") -> bytes:
    """Protect bytes with the current Windows user context and additional entropy."""

    _require_windows()
    if not entropy:
        raise DpapiError("DPAPI additional entropy must not be empty")
    input_blob, input_buffer = _build_blob(data)
    entropy_blob, entropy_buffer = _build_blob(entropy)
    output_blob = _DataBlob()  # type: ignore[name-defined]
    if not _crypt32.CryptProtectData(  # type: ignore[name-defined]
        ctypes.byref(input_blob),
        description,
        ctypes.byref(entropy_blob),
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output_blob),
    ):
        raise DpapiError(f"CryptProtectData failed with error code {ctypes.GetLastError()}")
    try:
        return _blob_to_bytes(output_blob)
    finally:
        if output_blob.pbData:
            _kernel32.LocalFree(output_blob.pbData)  # type: ignore[arg-type,name-defined]
        del input_buffer
        del entropy_buffer


def unprotect_bytes(data: bytes, *, entropy: bytes) -> bytes:
    """Unprotect bytes with the current Windows user context and additional entropy."""

    _require_windows()
    if not entropy:
        raise DpapiError("DPAPI additional entropy must not be empty")
    input_blob, input_buffer = _build_blob(data)
    entropy_blob, entropy_buffer = _build_blob(entropy)
    output_blob = _DataBlob()  # type: ignore[name-defined]
    description_ptr = wintypes.LPWSTR()
    if not _crypt32.CryptUnprotectData(  # type: ignore[name-defined]
        ctypes.byref(input_blob),
        ctypes.byref(description_ptr),
        ctypes.byref(entropy_blob),
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output_blob),
    ):
        raise DpapiError(f"CryptUnprotectData failed with error code {ctypes.GetLastError()}")
    try:
        return _blob_to_bytes(output_blob)
    finally:
        if output_blob.pbData:
            _kernel32.LocalFree(output_blob.pbData)  # type: ignore[arg-type,name-defined]
        if description_ptr:
            _kernel32.LocalFree(description_ptr)  # type: ignore[arg-type,name-defined]
        del input_buffer
        del entropy_buffer


__all__ = ["DpapiError", "protect_bytes", "unprotect_bytes"]
