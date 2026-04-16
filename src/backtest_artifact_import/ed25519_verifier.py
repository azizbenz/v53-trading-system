"""Minimal pure-Python Ed25519 verification for governed artifact intake.

This module is intentionally bounded:
- verify only
- raw 32-byte public keys encoded as base64
- raw 64-byte signatures encoded as base64
- message is passed as bytes by the caller
"""

from __future__ import annotations

import base64
import binascii
import hashlib

_P = 2**255 - 19
_L = 2**252 + 27742317777372353535851937790883648493
_D = (-121665 * pow(121666, _P - 2, _P)) % _P
_I = pow(2, (_P - 1) // 4, _P)


def _modp_inv(value: int) -> int:
    return pow(value, _P - 2, _P)


def _recover_x(y: int, sign: int) -> int:
    xx = (y * y - 1) * _modp_inv((_D * y * y + 1) % _P) % _P
    x = pow(xx, (_P + 3) // 8, _P)
    if (x * x - xx) % _P != 0:
        x = (x * _I) % _P
    if (x * x - xx) % _P != 0:
        raise ValueError("invalid Edwards25519 point")
    if x & 1 != sign:
        x = _P - x
    return x


def _is_on_curve(point: tuple[int, int]) -> bool:
    x, y = point
    return (-x * x + y * y - 1 - _D * x * x * y * y) % _P == 0


def _point_add(p1: tuple[int, int], p2: tuple[int, int]) -> tuple[int, int]:
    x1, y1 = p1
    x2, y2 = p2
    x_denom = _modp_inv((1 + _D * x1 * x2 * y1 * y2) % _P)
    y_denom = _modp_inv((1 - _D * x1 * x2 * y1 * y2) % _P)
    x3 = ((x1 * y2 + x2 * y1) * x_denom) % _P
    y3 = ((y1 * y2 + x1 * x2) * y_denom) % _P
    return (x3, y3)


def _point_mul(point: tuple[int, int], scalar: int) -> tuple[int, int]:
    result = (0, 1)
    addend = point
    remaining = scalar
    while remaining > 0:
        if remaining & 1:
            result = _point_add(result, addend)
        addend = _point_add(addend, addend)
        remaining >>= 1
    return result


def _decode_point(encoded: bytes) -> tuple[int, int]:
    if len(encoded) != 32:
        raise ValueError("Ed25519 public keys and encoded points must be 32 bytes")
    y = int.from_bytes(encoded, "little") & ((1 << 255) - 1)
    sign = encoded[31] >> 7
    if y >= _P:
        raise ValueError("invalid Edwards25519 y-coordinate")
    point = (_recover_x(y, sign), y)
    if not _is_on_curve(point):
        raise ValueError("decoded point is not on curve")
    return point


def _decode_signature(encoded: bytes) -> tuple[bytes, int]:
    if len(encoded) != 64:
        raise ValueError("Ed25519 signatures must be 64 bytes")
    r_enc = encoded[:32]
    s = int.from_bytes(encoded[32:], "little")
    if s >= _L:
        raise ValueError("Ed25519 signature scalar is out of range")
    return r_enc, s


def _decode_base64_bytes(value: str, *, expected_len: int) -> bytes:
    decoded = base64.b64decode(value, validate=True)
    if len(decoded) != expected_len:
        raise ValueError(f"expected {expected_len} decoded bytes, got {len(decoded)}")
    return decoded


_BASE_Y = (4 * _modp_inv(5)) % _P
_BASE_POINT = (_recover_x(_BASE_Y, 0), _BASE_Y)


def verify_ed25519_signature_base64(
    *,
    public_key_b64: str,
    signature_b64: str,
    message: bytes,
) -> bool:
    """Verify a base64-encoded raw Ed25519 signature against a message."""

    try:
        public_key = _decode_base64_bytes(public_key_b64, expected_len=32)
        signature = _decode_base64_bytes(signature_b64, expected_len=64)
        public_point = _decode_point(public_key)
        encoded_r, scalar_s = _decode_signature(signature)
        r_point = _decode_point(encoded_r)
        challenge = int.from_bytes(
            hashlib.sha512(encoded_r + public_key + message).digest(),
            "little",
        ) % _L
        left = _point_mul(_BASE_POINT, scalar_s)
        right = _point_add(r_point, _point_mul(public_point, challenge))
        return _point_mul(left, 8) == _point_mul(right, 8)
    except (binascii.Error, TypeError, ValueError):
        return False


__all__ = ["verify_ed25519_signature_base64"]
