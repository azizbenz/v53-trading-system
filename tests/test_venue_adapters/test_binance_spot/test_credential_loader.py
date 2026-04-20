import json
from pathlib import Path
import shutil
import os

import pytest

from secrets_manager.sealer import generate_master_key, seal_file
from venue_adapters.binance_spot.credential_loader import (
    BinanceCredentialLoadError,
    load_binance_credentials,
    load_binance_credentials_from_env,
    load_binance_credentials_from_file,
    load_testnet_credentials,
)


def test_load_binance_credentials_validates_mapping_without_leaking_secret_repr() -> None:
    credentials = load_binance_credentials(
        {
            "api_key": "api-key-value",
            "secret_key": "secret-key-value",
            "label": "testnet",
        }
    )

    assert credentials.label == "testnet"
    assert "api-key-value" not in repr(credentials)
    assert "secret-key-value" not in repr(credentials)


def test_load_binance_credentials_from_env_requires_both_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("V53_BINANCE_API_KEY", "api-only")
    monkeypatch.delenv("V53_BINANCE_SECRET_KEY", raising=False)

    with pytest.raises(BinanceCredentialLoadError):
        load_binance_credentials_from_env()


def test_load_testnet_credentials_reads_dedicated_testnet_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BINANCE_TESTNET_API_KEY", "testnet-api")
    monkeypatch.setenv("BINANCE_TESTNET_SECRET", "testnet-secret")
    monkeypatch.setenv("BINANCE_TESTNET_LABEL", "binance-spot-testnet")

    credentials = load_testnet_credentials()

    assert credentials.label == "binance-spot-testnet"


def test_load_binance_credentials_from_file_supports_json(repo_tmp_path: Path) -> None:
    build_root = repo_tmp_path / "test_venue_adapters_binance_credentials"
    shutil.rmtree(build_root, ignore_errors=True)
    build_root.mkdir(parents=True, exist_ok=True)
    try:
        credential_path = build_root / "binance_credentials.json"
        credential_path.write_text(
            json.dumps(
                {
                    "api_key": "api-key-value",
                    "secret_key": "secret-key-value",
                    "label": "testnet",
                }
            ),
            encoding="utf-8",
        )

        credentials = load_binance_credentials_from_file(credential_path)

        assert credentials.label == "testnet"
    finally:
        shutil.rmtree(build_root, ignore_errors=True)


@pytest.mark.skipif(os.name != "nt", reason="requires Windows DPAPI")
def test_load_binance_credentials_from_sealed_file(repo_tmp_path: Path) -> None:
    build_root = repo_tmp_path / "test_venue_adapters_binance_credentials_sealed"
    shutil.rmtree(build_root, ignore_errors=True)
    build_root.mkdir(parents=True, exist_ok=True)
    try:
        key_path = generate_master_key(build_root / "master.key")
        credential_path = build_root / "binance_credentials.yml"
        credential_path.write_text(
            "api_key: api-key-value\nsecret_key: secret-key-value\nlabel: testnet\n",
            encoding="utf-8",
        )
        sealed_path = seal_file(credential_path, key_path=key_path, remove_source=True)

        credentials = load_binance_credentials_from_file(sealed_path, key_path=key_path)

        assert credentials.label == "testnet"
    finally:
        shutil.rmtree(build_root, ignore_errors=True)
