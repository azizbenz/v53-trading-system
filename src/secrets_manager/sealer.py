"""Seal plaintext secrets into a typed encrypted envelope."""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from secrets_manager._dpapi import DpapiError, protect_bytes
from secrets_manager.loader import SecretManagerLoadError, SealedSecretEnvelope, _read_key_entropy


def generate_master_key(path: Path | str, *, force: bool = False) -> Path:
    """Create a random master-key file used as additional DPAPI entropy."""

    target = Path(path).expanduser()
    if target.exists() and not force:
        raise SecretManagerLoadError(f"Master key file {target} already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    secret_text = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")
    atomic_write_text(target, f"{secret_text}\n")
    return target


def seal_bytes(
    data: bytes,
    *,
    key_path: Path | str,
    source_name: str = "",
) -> SealedSecretEnvelope:
    """Seal bytes into a typed DPAPI envelope."""

    entropy = _read_key_entropy(key_path)
    try:
        ciphertext = protect_bytes(data, entropy=entropy, description=source_name)
    except DpapiError as exc:
        raise SecretManagerLoadError(f"Could not seal secret payload: {exc}") from exc
    return SealedSecretEnvelope(
        source_name=source_name,
        created_at=datetime.now(timezone.utc),
        ciphertext_b64=base64.b64encode(ciphertext).decode("ascii"),
    )


def seal_mapping(
    payload: Mapping[str, Any],
    *,
    key_path: Path | str,
    source_name: str = "",
) -> SealedSecretEnvelope:
    """Seal a YAML mapping into a typed envelope."""

    return seal_bytes(
        yaml.safe_dump(dict(payload), sort_keys=True).encode("utf-8"),
        key_path=key_path,
        source_name=source_name,
    )


def seal_file(
    path: Path | str,
    *,
    key_path: Path | str,
    output_path: Path | str | None = None,
    remove_source: bool = False,
) -> Path:
    """Seal a plaintext file and write the encrypted envelope to disk."""

    source = Path(path)
    if not source.exists():
        raise SecretManagerLoadError(f"Plaintext secret file {source} does not exist")
    if not source.is_file():
        raise SecretManagerLoadError(f"Plaintext secret path {source} must be a file")
    target = Path(output_path) if output_path is not None else Path(f"{source}.sealed.json")
    envelope = seal_bytes(
        source.read_bytes(),
        key_path=key_path,
        source_name=source.name,
    )
    atomic_write_json(target, envelope.model_dump(mode="json"), indent=2)
    if remove_source:
        source.unlink()
    return target


__all__ = [
    "generate_master_key",
    "seal_bytes",
    "seal_file",
    "seal_mapping",
]
