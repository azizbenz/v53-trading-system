"""Load sealed secret envelopes without leaking plaintext outside memory."""

from __future__ import annotations

import base64
import json
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Mapping

import yaml
from pydantic import BaseModel, Field, ValidationError

from interface_contracts.atomic_io import atomic_write_bytes
from secrets_manager._dpapi import DpapiError, unprotect_bytes


class SecretBackend(StrEnum):
    """Backends supported by the bounded sealed-secret slice."""

    WINDOWS_DPAPI_USER = "windows_dpapi_user"


class SealedSecretEnvelope(BaseModel, frozen=True):
    """Typed sealed-secret envelope written to disk."""

    schema_version: str = Field(default="v53.sealed_secret.v1", min_length=1)
    backend: SecretBackend = SecretBackend.WINDOWS_DPAPI_USER
    source_name: str = ""
    created_at: datetime
    ciphertext_b64: str = Field(..., min_length=1)


class SecretManagerLoadError(RuntimeError):
    """Raised when a sealed secret cannot be loaded safely."""


def _read_key_entropy(key_path: Path | str) -> bytes:
    candidate = Path(key_path).expanduser()
    if not candidate.exists():
        raise SecretManagerLoadError(f"Master key file {candidate} does not exist")
    if not candidate.is_file():
        raise SecretManagerLoadError(f"Master key path {candidate} must be a file")
    entropy = candidate.read_bytes().strip()
    if not entropy:
        raise SecretManagerLoadError(f"Master key file {candidate} must not be empty")
    return entropy


def load_envelope(path: Path | str) -> SealedSecretEnvelope:
    """Load and validate a sealed secret envelope from disk."""

    candidate = Path(path)
    if not candidate.exists():
        raise SecretManagerLoadError(f"Sealed secret {candidate} does not exist")
    if not candidate.is_file():
        raise SecretManagerLoadError(f"Sealed secret path {candidate} must be a file")
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SecretManagerLoadError(f"Sealed secret {candidate} could not be parsed: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise SecretManagerLoadError(f"Sealed secret {candidate} must deserialize to a mapping")
    try:
        return SealedSecretEnvelope.model_validate(payload)
    except ValidationError as exc:
        raise SecretManagerLoadError(f"Sealed secret {candidate} failed validation: {exc}") from exc


def load_secret_bytes(path: Path | str, *, key_path: Path | str) -> bytes:
    """Decrypt a sealed secret envelope into bytes in memory."""

    envelope = load_envelope(path)
    entropy = _read_key_entropy(key_path)
    try:
        ciphertext = base64.b64decode(envelope.ciphertext_b64.encode("ascii"), validate=True)
    except Exception as exc:
        raise SecretManagerLoadError(f"Sealed secret {path} has invalid ciphertext encoding: {exc}") from exc
    try:
        return unprotect_bytes(ciphertext, entropy=entropy)
    except DpapiError as exc:
        raise SecretManagerLoadError(f"Sealed secret {path} could not be unsealed: {exc}") from exc


def load_secret_text(path: Path | str, *, key_path: Path | str, encoding: str = "utf-8") -> str:
    """Decrypt a sealed secret envelope into text."""

    try:
        return load_secret_bytes(path, key_path=key_path).decode(encoding)
    except UnicodeDecodeError as exc:
        raise SecretManagerLoadError(f"Sealed secret {path} is not valid {encoding}: {exc}") from exc


def load(path: Path | str, *, key_path: Path | str) -> dict[str, Any]:
    """Load a sealed YAML/JSON mapping from disk."""

    text = load_secret_text(path, key_path=key_path)
    try:
        payload = yaml.safe_load(text)
    except Exception as exc:
        raise SecretManagerLoadError(f"Sealed secret {path} could not be parsed as YAML/JSON: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise SecretManagerLoadError(f"Sealed secret {path} must contain a mapping payload")
    return dict(payload)


def write_unsealed_text(
    path: Path | str,
    *,
    text: str,
    force: bool = False,
) -> Path:
    """Write unsealed plaintext only when explicitly requested by the operator."""

    target = Path(path)
    if target.exists() and not force:
        raise SecretManagerLoadError(f"Refusing to overwrite existing plaintext file {target}")
    atomic_write_bytes(target, text.encode("utf-8"))
    return target


__all__ = [
    "SecretBackend",
    "SecretManagerLoadError",
    "SealedSecretEnvelope",
    "load",
    "load_envelope",
    "load_secret_bytes",
    "load_secret_text",
    "write_unsealed_text",
]
