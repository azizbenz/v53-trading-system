"""POSIX keyring-backed secret protection shim."""

from __future__ import annotations

import base64
import hashlib
import uuid

try:
    import keyring
    from keyring.errors import KeyringError
except ImportError:  # pragma: no cover - exercised via monkeypatched fallback tests.

    class KeyringError(RuntimeError):
        """Fallback error type when keyring is unavailable."""

    class _MissingKeyring:
        def set_password(self, _service: str, _token: str, _payload: str) -> None:
            raise KeyringError("keyring is not installed")

        def get_password(self, _service: str, _token: str) -> str | None:
            raise KeyringError("keyring is not installed")

    keyring = _MissingKeyring()


_SERVICE_NAME = "v53-trading-system.secrets"
_TOKEN_PREFIX = "v53-keyring"


class DpapiError(RuntimeError):
    """Raised when the POSIX keyring backend cannot protect or unprotect data."""


def protect_bytes(data: bytes, *, entropy: bytes, description: str = "") -> bytes:
    """Store the payload in the user keyring and return an opaque token."""

    del description
    if not entropy:
        raise DpapiError("POSIX keyring entropy must not be empty")
    entropy_digest = hashlib.sha256(entropy).hexdigest()
    token = f"{_TOKEN_PREFIX}:{entropy_digest}:{uuid.uuid4().hex}"
    payload = base64.b64encode(data).decode("ascii")
    try:
        keyring.set_password(_SERVICE_NAME, token, payload)
    except KeyringError as exc:
        raise DpapiError(f"POSIX keyring set_password failed: {exc}") from exc
    return token.encode("utf-8")


def unprotect_bytes(data: bytes, *, entropy: bytes) -> bytes:
    """Resolve an opaque token back to plaintext bytes from the user keyring."""

    if not entropy:
        raise DpapiError("POSIX keyring entropy must not be empty")
    try:
        token = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DpapiError(f"POSIX keyring token is not valid UTF-8: {exc}") from exc
    parts = token.split(":")
    if len(parts) != 3 or parts[0] != _TOKEN_PREFIX:
        raise DpapiError("POSIX keyring token has an invalid format")
    entropy_digest = hashlib.sha256(entropy).hexdigest()
    if parts[1] != entropy_digest:
        raise DpapiError("POSIX keyring token does not match the provided entropy")
    try:
        payload = keyring.get_password(_SERVICE_NAME, token)
    except KeyringError as exc:
        raise DpapiError(f"POSIX keyring get_password failed: {exc}") from exc
    if payload is None:
        raise DpapiError("POSIX keyring token is unknown")
    try:
        return base64.b64decode(payload.encode("ascii"), validate=True)
    except (UnicodeEncodeError, ValueError) as exc:
        raise DpapiError(f"POSIX keyring payload is invalid: {exc}") from exc


__all__ = ["DpapiError", "protect_bytes", "unprotect_bytes"]
