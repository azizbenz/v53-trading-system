import os
from pathlib import Path
import shutil

import pytest

from secrets_manager.cli import main as secrets_cli_main
from secrets_manager.loader import SecretManagerLoadError, load
from secrets_manager.sealer import generate_master_key, seal_file


pytestmark = pytest.mark.skipif(os.name != "nt", reason="requires Windows DPAPI")


def test_seal_and_load_round_trip_removes_plaintext_when_requested():
    build_root = Path("build/test_secrets_manager_roundtrip")
    shutil.rmtree(build_root, ignore_errors=True)
    build_root.mkdir(parents=True, exist_ok=True)
    try:
        key_path = build_root / "master.key"
        source_path = build_root / "api.yml"
        source_path.write_text(
            "api_key: demo-key\nsecret_key: demo-secret\nlabel: testnet\n",
            encoding="utf-8",
        )
        generate_master_key(key_path)
        sealed_path = seal_file(source_path, key_path=key_path, remove_source=True)

        payload = load(sealed_path, key_path=key_path)

        assert not source_path.exists()
        assert payload["api_key"] == "demo-key"
        assert payload["secret_key"] == "demo-secret"
    finally:
        shutil.rmtree(build_root, ignore_errors=True)


def test_load_rejects_wrong_master_key():
    build_root = Path("build/test_secrets_manager_wrong_key")
    shutil.rmtree(build_root, ignore_errors=True)
    build_root.mkdir(parents=True, exist_ok=True)
    try:
        source_path = build_root / "api.yml"
        source_path.write_text("api_key: demo\nsecret_key: secret\n", encoding="utf-8")
        good_key = generate_master_key(build_root / "good.key")
        bad_key = generate_master_key(build_root / "bad.key")
        sealed_path = seal_file(source_path, key_path=good_key)

        with pytest.raises(SecretManagerLoadError):
            load(sealed_path, key_path=bad_key)
    finally:
        shutil.rmtree(build_root, ignore_errors=True)


def test_cli_gen_key_seal_and_unseal_round_trip():
    build_root = Path("build/test_secrets_manager_cli")
    shutil.rmtree(build_root, ignore_errors=True)
    build_root.mkdir(parents=True, exist_ok=True)
    try:
        key_path = build_root / "master.key"
        source_path = build_root / "api.yml"
        sealed_path = build_root / "api.yml.sealed.json"
        unsealed_path = build_root / "api.unsealed.yml"
        source_text = "api_key: cli-key\nsecret_key: cli-secret\nlabel: cli\n"
        source_path.write_text(source_text, encoding="utf-8")

        assert secrets_cli_main(["gen-key", str(key_path)]) == 0
        assert secrets_cli_main(
            [
                "seal",
                str(source_path),
                "--key-path",
                str(key_path),
                "--output",
                str(sealed_path),
                "--delete-source",
            ]
        ) == 0
        assert not source_path.exists()
        assert secrets_cli_main(
            [
                "unseal",
                str(sealed_path),
                "--key-path",
                str(key_path),
                "--output",
                str(unsealed_path),
            ]
        ) == 0
        assert unsealed_path.read_text(encoding="utf-8") == source_text
    finally:
        shutil.rmtree(build_root, ignore_errors=True)
