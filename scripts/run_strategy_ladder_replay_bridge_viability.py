from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from local_replay_runtime.strategy_ladder_replay_bridge_viability import (
    render_replay_bridge_viability_report,
    run_replay_bridge_viability_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a replay-bridge viability diagnostic on one workflow."
    )
    parser.add_argument("--workflow-root", required=True, help="Workflow root directory.")
    parser.add_argument("--output", default="", help="Optional JSON output path.")
    args = parser.parse_args()

    report = run_replay_bridge_viability_report(Path(args.workflow_root))
    rendered = render_replay_bridge_viability_report(report)
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
