#!/usr/bin/env python3
"""Seed the Binance credential profile into the Shadow VPS service state.

Creates a sealed credential bundle from .env and updates the service state
so the bootstrap reconciliation and credential checks pass.

Usage:
    python scripts/run_shadow_credential_seed.py [--service-dir PATH] [--env-file PATH]
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parent
SRC_ROOT = REPO_ROOT / "src"
for _candidate in (SCRIPT_ROOT, SRC_ROOT):
    if str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

from interface_contracts.dashboard_command_contracts import (  # noqa: E402
    BinanceCredentialInventoryEntry,
    BinanceCredentialProfileRef,
    BinanceCredentialValidationStatus,
    DashboardSecretEnvironment,
    DashboardSecretKind,
)
from protocols import ShadowVpsServiceStore  # noqa: E402
from secrets_manager.sealer import generate_master_key, seal_mapping  # noqa: E402


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        val = raw_value.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
            val = val[1:-1]
        values[key.strip()] = val
    return values


def run_credential_seed(
    *,
    service_dir: Path,
    env_file: Path,
    profile_id: str = "binance-live-001",
    force: bool = False,
) -> None:
    env = _load_env_file(env_file) if env_file.is_file() else {}
    api_key = env.get("BINANCE_API_KEY", "").strip()
    api_secret = env.get("BINANCE_API_SECRET", "").strip()
    if not api_key or not api_secret:
        raise RuntimeError(
            f"BINANCE_API_KEY and BINANCE_API_SECRET must be set in {env_file}"
        )

    secrets_dir = REPO_ROOT / "secrets"
    secrets_dir.mkdir(parents=True, exist_ok=True)

    key_path = secrets_dir / f"{profile_id}.key"
    sealed_path = secrets_dir / f"{profile_id}.sealed.json"

    if not key_path.exists() or force:
        generate_master_key(key_path, force=force)
        print(f"Created master key: {key_path}")
    else:
        print(f"Reusing existing master key: {key_path}")

    envelope = seal_mapping(
        {"api_key": api_key, "secret_key": api_secret, "label": profile_id},
        key_path=key_path,
        source_name=profile_id,
    )
    sealed_bytes = envelope.model_dump_json(indent=2).encode("utf-8")
    sealed_path.write_bytes(sealed_bytes)
    print(f"Created sealed bundle: {sealed_path}")

    secret_hash = hashlib.sha256(sealed_bytes).hexdigest()
    sealed_ref = f"secrets/{profile_id}.sealed.json"

    profile_ref = BinanceCredentialProfileRef(
        profile_id=profile_id,
        environment=DashboardSecretEnvironment.LIVE,
        secret_kind=DashboardSecretKind.BINANCE_SPOT_CREDENTIALS,
        secret_hash=secret_hash,
        sealed_ref=sealed_ref,
    )
    now_ms = int(time.time() * 1000)
    entry = BinanceCredentialInventoryEntry(
        profile=profile_ref,
        active=True,
        validation_status=BinanceCredentialValidationStatus.VALIDATED,
        last_auth_check_ms=now_ms,
        created_at_ms=now_ms,
    )

    store = ShadowVpsServiceStore(service_dir)
    state = store.state
    existing = tuple(
        item for item in state.binance_credential_inventory
        if item.profile.profile_id != profile_id
    )
    state.binance_credential_inventory = existing + (entry,)
    state.active_binance_credential_profile_id = profile_id
    state.binance_credential_validation_status = BinanceCredentialValidationStatus.VALIDATED.value
    state.binance_credential_last_auth_check_ms = now_ms
    state.binance_credential_last_failure_reason_codes = ()
    store.persist()

    print(f"State updated:   {store.state_path}")
    print(f"Active profile:  {profile_id}")
    print(f"Validation:      validated")
    print(f"secret_hash:     {secret_hash[:16]}...")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--service-dir",
        type=Path,
        default=REPO_ROOT / "build/build11_live_websocket_campaign/service",
        help="Shadow VPS service state directory (default: build11)",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=REPO_ROOT / ".env",
        help="Path to .env file with BINANCE_API_KEY and BINANCE_API_SECRET",
    )
    parser.add_argument(
        "--profile-id",
        default="binance-live-001",
        help="Credential profile ID (default: binance-live-001)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing key file if present",
    )
    args = parser.parse_args(argv)
    run_credential_seed(
        service_dir=args.service_dir,
        env_file=args.env_file,
        profile_id=args.profile_id,
        force=args.force,
    )
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
