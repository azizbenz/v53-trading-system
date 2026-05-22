from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from local_replay_runtime.strategy_ladder_engine_synthetic_viability import (
    run_synthetic_engine_viability_harness,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the synthetic A/B/C/D engine viability harness."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write the JSON report.",
    )
    args = parser.parse_args()

    report = run_synthetic_engine_viability_harness()
    payload = report.to_dict()
    rendered = json.dumps(payload, indent=2)
    if args.output is not None:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0 if report.overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
