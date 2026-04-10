#!/usr/bin/env python3
"""Standalone deterministic launcher for HC-4 AAOIFI pair-screening audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _configure_stdio() -> None:
    stdout = getattr(sys, "stdout", None)
    if stdout is not None and hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8", errors="replace")
    stderr = getattr(sys, "stderr", None)
    if stderr is not None and hasattr(stderr, "reconfigure"):
        stderr.reconfigure(encoding="utf-8", errors="replace")


def run_sharia_pair_screening_audit(
    provider: object,
    *,
    traded_pairs: tuple[str, ...],
    policy: object,
    output_path: Path,
    alerts_output_path: Path | None = None,
    correlation_id: str | None = None,
) -> int:
    from uuid import uuid4

    from sharia_compliance import (
        audit_traded_pairs_against_screening,
        build_pair_screening_audit_alerts,
    )

    report = audit_traded_pairs_against_screening(
        traded_pairs=traded_pairs,
        provider=provider,
        policy=policy,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    alerts = build_pair_screening_audit_alerts(
        report,
        correlation_id=correlation_id or f"sharia_pair_screening_{uuid4().hex}",
    )
    if alerts_output_path is not None:
        alerts_output_path.parent.mkdir(parents=True, exist_ok=True)
        alerts_output_path.write_text(
            json.dumps([alert.model_dump(mode="json") for alert in alerts], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    return 0 if report.clean else 2


def _load_pairs(args: argparse.Namespace) -> tuple[str, ...]:
    values: list[str] = [pair.strip().upper() for pair in args.pair if pair.strip()]
    if args.pairs_file:
        payload = Path(args.pairs_file).read_text(encoding="utf-8")
        if args.pairs_file.lower().endswith(".json"):
            parsed = json.loads(payload)
            if not isinstance(parsed, list):
                raise ValueError("pairs-file JSON must deserialize to a list")
            values.extend(str(item).strip().upper() for item in parsed if str(item).strip())
        else:
            values.extend(line.strip().upper() for line in payload.splitlines() if line.strip())
    return tuple(dict.fromkeys(values))


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    parser = argparse.ArgumentParser(description="Run deterministic AAOIFI pair-screening audit")
    parser.add_argument("--registry", required=True)
    parser.add_argument("--policy", default="config/sharia/policy_v1.yml")
    parser.add_argument("--pair", action="append", default=[])
    parser.add_argument("--pairs-file")
    parser.add_argument("--output", default="build/sharia_pair_screening/latest_report.json")
    parser.add_argument("--alerts-output", default="build/sharia_pair_screening/latest_alerts.json")
    args = parser.parse_args(argv)

    from sharia_compliance import FilePairScreeningProvider, load_sharia_policy

    provider = FilePairScreeningProvider(args.registry)
    policy = load_sharia_policy(args.policy)
    traded_pairs = _load_pairs(args)
    if not traded_pairs:
        raise ValueError("at least one traded pair must be provided")
    return run_sharia_pair_screening_audit(
        provider,
        traded_pairs=traded_pairs,
        policy=policy,
        output_path=Path(args.output),
        alerts_output_path=Path(args.alerts_output),
    )


if __name__ == "__main__":
    raise SystemExit(main())
