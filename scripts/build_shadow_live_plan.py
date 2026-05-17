"""Emit the canonical Shadow live pair plan as JSON."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from protocols.shadow_live_plan import build_shadow_live_plan  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the canonical Shadow live pair/engine route plan."
    )
    parser.add_argument(
        "--pairs",
        nargs="*",
        default=None,
        help="Optional governed pair override. Defaults to the canonical 7-pair universe.",
    )
    args = parser.parse_args()
    plan = build_shadow_live_plan(args.pairs)
    sys.stdout.write(plan.model_dump_json(indent=2))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
