"""Credential loaders for Binance Spot with runtime-safe policy seams."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Mapping

import yaml
from pydantic import ValidationError

from interface_contracts import RuntimeMode
from interface_contracts.binance_contracts import BinanceCredentials
from secrets_manager import SecretManagerLoadError, load as load_sealed_mapping


class BinanceCredentialLoadError(RuntimeError):
    """Raised when Binance credentials cannot be loaded safely."""


def _is_sealed_credential_path(path: Path) -> bool:
    return path.name.endswith(".sealed.json")


def load_binance_credentials(payload: Mapping[str, object]) -> BinanceCredentials:
    """Validate credentials from a mapping without logging secret content."""

    if not isinstance(payload, Mapping):
        raise BinanceCredentialLoadError("Binance credentials payload must be a mapping")
    try:
        return BinanceCredentials(
            api_key=str(payload["api_key"]),
            secret_key=str(payload["secret_key"]),
            label=str(payload.get("label", "")),
        )
    except KeyError as exc:
        raise BinanceCredentialLoadError(
            f"Binance credentials payload is missing required key {exc.args[0]!r}"
        ) from exc
    except ValidationError as exc:
        raise BinanceCredentialLoadError(f"Binance credentials payload is invalid: {exc}") from exc


def load_binance_credentials_from_env(prefix: str = "V53_BINANCE_") -> BinanceCredentials:
    """Load credentials from environment variables for local/dev seams."""

    api_key = os.getenv(f"{prefix}API_KEY", "")
    secret_key = os.getenv(f"{prefix}SECRET_KEY", "")
    label = os.getenv(f"{prefix}LABEL", "")
    return load_binance_credentials(
        {
            "api_key": api_key,
            "secret_key": secret_key,
            "label": label,
        }
    )


def load_testnet_credentials() -> BinanceCredentials:
    """Load Binance Spot testnet credentials from the dedicated environment seam."""

    return load_binance_credentials(
        {
            "api_key": os.getenv("BINANCE_TESTNET_API_KEY", ""),
            "secret_key": os.getenv("BINANCE_TESTNET_SECRET", ""),
            "label": os.getenv("BINANCE_TESTNET_LABEL", "testnet"),
        }
    )


def load_binance_credentials_from_file(
    path: Path | str,
    *,
    key_path: Path | str | None = None,
) -> BinanceCredentials:
    """Load credentials from a local file.

    Plaintext files remain supported here for tests/local development only.
    Runtime code must use :func:`load_binance_credentials_for_runtime`.
    """

    credential_path = Path(path)
    if not credential_path.exists():
        raise BinanceCredentialLoadError(f"Binance credential file {credential_path} does not exist")
    if not credential_path.is_file():
        raise BinanceCredentialLoadError(f"Binance credential path {credential_path} must be a file")

    try:
        if _is_sealed_credential_path(credential_path):
            if key_path is None:
                raise BinanceCredentialLoadError(
                    f"Sealed Binance credential file {credential_path} requires key_path"
                )
            payload = load_sealed_mapping(credential_path, key_path=key_path)
        else:
            suffix = credential_path.suffix.lower()
            text = credential_path.read_text(encoding="utf-8")
            if suffix in {".yml", ".yaml"}:
                payload = yaml.safe_load(text)
            elif suffix == ".json":
                payload = json.loads(text)
            else:
                raise BinanceCredentialLoadError(
                    f"Binance credential file {credential_path} has unsupported suffix {credential_path.suffix!r}"
                )
    except SecretManagerLoadError as exc:
        raise BinanceCredentialLoadError(str(exc)) from exc
    except BinanceCredentialLoadError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise BinanceCredentialLoadError(
            f"Binance credential file {credential_path} could not be parsed: {exc}"
        ) from exc

    if not isinstance(payload, Mapping):
        raise BinanceCredentialLoadError(
            f"Binance credential file {credential_path} must deserialize to a mapping"
        )
    return load_binance_credentials(payload)


def load_binance_credentials_for_runtime(
    path: Path | str,
    *,
    runtime_mode: RuntimeMode,
    key_path: Path | str | None = None,
    allow_plaintext_local_replay: bool = False,
) -> BinanceCredentials:
    """Load Binance credentials with VPS/LIVE fail-closed plaintext policy."""

    credential_path = Path(path)
    if not _is_sealed_credential_path(credential_path):
        if runtime_mode != RuntimeMode.LOCAL_REPLAY or not allow_plaintext_local_replay:
            raise BinanceCredentialLoadError(
                "Plaintext Binance credential files are forbidden for runtime loading"
            )
    return load_binance_credentials_from_file(credential_path, key_path=key_path)


def load_binance_credentials_from_env_for_runtime(
    *,
    runtime_mode: RuntimeMode,
    prefix: str = "V53_BINANCE_",
    allow_env_local_replay: bool = False,
) -> BinanceCredentials:
    """Load env credentials only for explicit LOCAL_REPLAY development seams."""

    if runtime_mode != RuntimeMode.LOCAL_REPLAY or not allow_env_local_replay:
        raise BinanceCredentialLoadError(
            "Environment Binance credentials are forbidden for runtime loading"
        )
    return load_binance_credentials_from_env(prefix=prefix)


__all__ = [
    "BinanceCredentialLoadError",
    "load_binance_credentials",
    "load_binance_credentials_from_env",
    "load_binance_credentials_from_env_for_runtime",
    "load_binance_credentials_from_file",
    "load_binance_credentials_for_runtime",
    "load_testnet_credentials",
]
