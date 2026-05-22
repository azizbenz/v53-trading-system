from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from local_replay_runtime.strategy_ladder_replay_builder_surface_audit import (
    render_replay_builder_surface_audit,
    run_replay_builder_surface_audit,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a builder-surface audit on real replay windows for selected engines."
    )
    parser.add_argument("--workflow-root", required=True, help="Workflow root directory.")
    parser.add_argument(
        "--engines",
        default="engine_c,engine_d",
        help="Comma-separated engine ids to audit.",
    )
    parser.add_argument("--output", default="", help="Optional JSON output path.")
    args = parser.parse_args()

    engine_ids = tuple(
        value.strip().lower() for value in args.engines.split(",") if value.strip()
    ) or ("engine_c", "engine_d")
    report = run_replay_builder_surface_audit(
        Path(args.workflow_root),
        engine_ids=engine_ids,
    )
    rendered = render_replay_builder_surface_audit(report)
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
