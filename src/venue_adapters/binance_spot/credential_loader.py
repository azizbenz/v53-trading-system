"""Stub credential loader for Binance Spot before sealed-secrets land in T2."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Mapping

import yaml
from pydantic import ValidationError

from interface_contracts.binance_contracts import BinanceCredentials
from secrets_manager import SecretManagerLoadError, load as load_sealed_mapping


class BinanceCredentialLoadError(RuntimeError):
    """Raised when Binance credentials cannot be loaded safely."""


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
    """Load credentials from environment variables.

    The sealed-secrets manager will replace this stub in T2. Until then, the
    loader stays explicit and opt-in.
    """

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

    This is only a development stub. T2 will replace the plaintext path with a
    sealed loader.
    """

    credential_path = Path(path)
    if not credential_path.exists():
        raise BinanceCredentialLoadError(f"Binance credential file {credential_path} does not exist")
    if not credential_path.is_file():
        raise BinanceCredentialLoadError(f"Binance credential path {credential_path} must be a file")

    try:
        if credential_path.name.endswith(".sealed.json"):
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


__all__ = [
    "BinanceCredentialLoadError",
    "load_binance_credentials",
    "load_binance_credentials_from_env",
    "load_binance_credentials_from_file",
    "load_testnet_credentials",
]
