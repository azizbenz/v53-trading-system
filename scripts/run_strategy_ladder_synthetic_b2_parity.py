from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from local_replay_runtime.strategy_ladder_synthetic_b2_parity import (  # noqa: E402
    render_synthetic_b2_parity_report,
    run_synthetic_b2_parity_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run direct-vs-B2 synthetic parity diagnostics for engines A/B/C/D."
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=REPO_ROOT / "docs" / "diagnostics" / "strategy_ladder_synthetic_b2_parity.json",
        help="Where to write the parity report JSON.",
    )
    parser.add_argument(
        "--asset-root",
        type=Path,
        default=None,
        help="Optional directory for generated synthetic raw assets.",
    )
    args = parser.parse_args()

    report = run_synthetic_b2_parity_report(asset_root=args.asset_root)
    payload = render_synthetic_b2_parity_report(report)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
