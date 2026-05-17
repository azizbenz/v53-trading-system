"""Fetch public Bybit spot metadata into a local historical metadata cache."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from local_replay_runtime.bybit_historical_metadata import (  # noqa: E402
    fetch_bybit_spot_metadata_cache,
)


def _csv_tuple(raw_value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in (raw_value or "").split(",") if part.strip())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch public Bybit spot metadata into a local cache."
    )
    parser.add_argument(
        "--pairs",
        required=True,
        help="Comma-separated symbol list, for example BTCUSDT,BNBUSDT.",
    )
    parser.add_argument(
        "--output-root",
        required=True,
        help="Local metadata cache root, for example K:\\v5.3 backtest\\metadata\\bybit\\spot",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    payload = fetch_bybit_spot_metadata_cache(
        pairs=_csv_tuple(args.pairs),
        output_root=Path(args.output_root).resolve(),
    )
    print(json.dumps(payload, indent=2))
    fetch_status = str(payload.get("fetch_status") or "")
    if fetch_status == "BYBIT_PUBLIC_METADATA_FETCH_READY":
        return 0
    if fetch_status == "BYBIT_PUBLIC_METADATA_FETCH_PARTIAL":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
