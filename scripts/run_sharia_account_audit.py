#!/usr/bin/env python3
"""Standalone weekly launcher for the bounded halal account-feature audit."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from uuid import uuid4
from pathlib import Path


def _configure_stdio() -> None:
    stdout = getattr(sys, "stdout", None)
    if stdout is not None and hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8", errors="replace")
    stderr = getattr(sys, "stderr", None)
    if stderr is not None and hasattr(stderr, "reconfigure"):
        stderr.reconfigure(encoding="utf-8", errors="replace")


async def run_sharia_account_audit(
    provider: object,
    *,
    output_path: Path,
    alerts_output_path: Path | None = None,
    correlation_id: str | None = None,
) -> int:
    from sharia_compliance import build_account_feature_audit_alerts

    report = await provider.run_audit()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    alerts = build_account_feature_audit_alerts(
        report,
        correlation_id=correlation_id or f"sharia_audit_{uuid4().hex}",
    )
    if alerts_output_path is not None:
        alerts_output_path.parent.mkdir(parents=True, exist_ok=True)
        alerts_output_path.write_text(
            json.dumps([alert.model_dump(mode="json") for alert in alerts], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    return 0 if report.clean else 2


async def _run_from_cli(args: argparse.Namespace) -> int:
    from sharia_compliance import AccountFeaturesAuditConfig
    from venue_adapters.binance_spot import (
        BinanceAccountFeatureAuditProvider,
        BinanceRestClient,
        load_binance_adapter_config,
        load_binance_credentials_from_env,
        load_binance_credentials_from_file,
    )

    adapter_config = load_binance_adapter_config(args.config)
    credentials = (
        load_binance_credentials_from_file(args.credentials_file, key_path=args.key_path)
        if args.credentials_file
        else load_binance_credentials_from_env()
    )
    audit_config = AccountFeaturesAuditConfig(
        calibration_root=adapter_config.calibration_root,
        calibration_version=adapter_config.calibration_version,
    )
    async with BinanceRestClient(
        credentials=credentials,
        base_url=adapter_config.rest_base_url,
        timeout_s=adapter_config.timeout_s,
    ) as client:
        provider = BinanceAccountFeatureAuditProvider(
            client,
            recv_window_ms=adapter_config.recv_window_ms,
            audit_config=audit_config,
        )
        return await run_sharia_account_audit(
            provider,
            output_path=Path(args.output),
            alerts_output_path=Path(args.alerts_output),
        )


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    parser = argparse.ArgumentParser(description="Run the bounded weekly sharia account audit")
    parser.add_argument("--config", default="config/binance_adapter.yml")
    parser.add_argument("--credentials-file")
    parser.add_argument("--key-path")
    parser.add_argument("--output", default="build/sharia_account_audit/latest_report.json")
    parser.add_argument("--alerts-output", default="build/sharia_account_audit/latest_alerts.json")
    args = parser.parse_args(argv)
    return asyncio.run(_run_from_cli(args))


if __name__ == "__main__":
    raise SystemExit(main())
