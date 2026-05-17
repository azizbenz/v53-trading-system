#!/usr/bin/env python3
"""Run the V5.3 cockpit source discovery audit."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cockpit.source_discovery_support import (  # noqa: E402
    build_argument_parser,
    run_discovery,
    summarize_artifacts,
    write_discovery_outputs,
)


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    artifacts = run_discovery(
        repo_root=args.repo_root.expanduser().resolve(),
        runtime_root=args.runtime_root.expanduser().resolve(),
    )
    if args.stdout_only:
        sys.stdout.write(summarize_artifacts(artifacts) + "\n")
        return 0
    paths = write_discovery_outputs(
        artifacts=artifacts,
        output_dir=args.output_dir.expanduser().resolve(),
        emit_json=bool(args.emit_json),
    )
    sys.stdout.write(
        "Generated cockpit discovery artifacts:\n"
        + "\n".join(f"- {name}: {path}" for name, path in paths.items())
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
