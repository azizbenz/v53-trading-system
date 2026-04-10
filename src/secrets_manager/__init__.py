"""Bounded sealed-secrets helpers for local/runtime credential loading."""

from secrets_manager.cli import build_parser, main
from secrets_manager.loader import (
    SecretBackend,
    SecretManagerLoadError,
    SealedSecretEnvelope,
    load,
    load_envelope,
    load_secret_bytes,
    load_secret_text,
    write_unsealed_text,
)
from secrets_manager.sealer import generate_master_key, seal_bytes, seal_file, seal_mapping

__all__ = [
    "SecretBackend",
    "SecretManagerLoadError",
    "SealedSecretEnvelope",
    "build_parser",
    "generate_master_key",
    "load",
    "load_envelope",
    "load_secret_bytes",
    "load_secret_text",
    "main",
    "seal_bytes",
    "seal_file",
    "seal_mapping",
    "write_unsealed_text",
]
