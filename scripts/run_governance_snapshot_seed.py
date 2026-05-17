#!/usr/bin/env python3
"""Phase 2.1 — Synthesise governance snapshots for the cockpit.

This script bridges a known gap in V5.3: the ``RefusalJournal`` and
``MlModelRiskRegistry`` modules exist in ``src/`` but are not instantiated by
the Shadow service runtime. The cockpit therefore could only show
``not_yet_persisted`` placeholders.

This helper reads the artefacts that *are* emitted by the runtime
(``auto_exports/<date>/replay_dtr.jsonl`` for refusals,
``local_lab_tail_risk_review.json`` for tail-risk gates) and aggregates them
into two governance snapshots that the cockpit adapters can display:

- ``service_dir/refusal_journal.snapshot.json``
- ``service_dir/model_risk_register.snapshot.json``

The snapshots are *honest*: when no refusals exist, the file is empty with a
clear ``source_status="ok"`` and ``top_motifs=[]``. The cockpit then displays
"0 refusals so far" instead of an alarming placeholder.

Strict doctrine: this script does NOT modify ``src/``. It only reads
artefacts and writes JSON — the live wiring of the journal/registry into the
Shadow service main loop is a separate, larger refactor for a future phase.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from interface_contracts.atomic_io import atomic_write_json  # noqa: E402


_logger = logging.getLogger(__name__)


def _iter_dtr_rows(path: Path) -> Iterable[dict]:
    if not path.is_file():
        return
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    yield payload
    except OSError as exc:
        _logger.warning("Cannot read DTR rows %s: %s", path, exc)


def _latest_export_dir(auto_exports_root: Path) -> Path | None:
    if not auto_exports_root.is_dir():
        return None
    days = sorted(
        (d for d in auto_exports_root.iterdir() if d.is_dir()),
        key=lambda d: d.name,
        reverse=True,
    )
    return days[0] if days else None


def _find_latest_tail_risk_review(build_root: Path) -> Path | None:
    if not build_root.is_dir():
        return None
    candidates: list[Path] = []
    for entry in build_root.iterdir():
        if not entry.is_dir() or not entry.name.startswith("local_lab_analysis"):
            continue
        candidate = entry / "local_lab_tail_risk_review.json"
        if candidate.is_file():
            candidates.append(candidate)
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def synthesise_refusal_journal(
    *,
    auto_exports_root: Path,
    build_root: Path,
) -> dict[str, object]:
    """Aggregate refusal-like signals from runtime artefacts."""

    motif_counter: Counter[str] = Counter()
    last_observed: dict[str, str] = {}
    total_records = 0
    refusal_records = 0

    latest = _latest_export_dir(auto_exports_root)
    dtr_path = latest / "replay_dtr.jsonl" if latest else None
    if dtr_path is not None:
        for row in _iter_dtr_rows(dtr_path):
            total_records += 1
            decision = str(row.get("decision_state", ""))
            hard_blocked = bool(row.get("hard_blocked", False))
            reasons = list(row.get("hard_block_reasons") or ())
            cause_chain = list(row.get("cause_chain") or ())
            primary = str(row.get("primary_reason", ""))
            ts_raw = row.get("timestamp")
            try:
                ts = datetime.fromtimestamp(float(ts_raw), tz=UTC).isoformat() if ts_raw else ""
            except (TypeError, ValueError):
                ts = ""
            if hard_blocked or decision != "executed" or reasons or primary:
                refusal_records += 1
                for r in reasons or [primary] or ["unspecified_refusal"]:
                    if not r:
                        continue
                    motif_counter[r] += 1
                    last_observed[r] = ts
                for c in cause_chain:
                    if isinstance(c, str) and c:
                        motif_counter[f"cause:{c}"] += 1
                        last_observed[f"cause:{c}"] = ts

    # Tail-risk breakers as Taleb refusal proxy.
    tail_breaker_total = 0
    tail_breaker_blocked = 0
    tail_caution_motifs: list[tuple[str, str]] = []
    tail_path = _find_latest_tail_risk_review(build_root)
    if tail_path is not None:
        try:
            payload = json.loads(tail_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        if isinstance(payload, dict):
            breakers = payload.get("breakers") or ()
            tail_breaker_total = len(breakers)
            for b in breakers:
                if not isinstance(b, dict):
                    continue
                if b.get("review_status") == "blocked":
                    tail_breaker_blocked += 1
                for flag in b.get("caution_flags") or ():
                    motif_counter[f"tail_risk:{flag}"] += 1
                    last_observed[f"tail_risk:{flag}"] = datetime.now(tz=UTC).isoformat()

    top_motifs = [
        {
            "motif": motif,
            "count": count,
            "last_observed_at": last_observed.get(motif, ""),
        }
        for motif, count in motif_counter.most_common(20)
    ]

    tail_risk_meter = (
        tail_breaker_blocked / tail_breaker_total if tail_breaker_total > 0 else 0.0
    )

    return {
        "snapshot_at": datetime.now(tz=UTC).isoformat(),
        "source": "scripts/run_governance_snapshot_seed.py",
        "total_records_inspected": total_records,
        "refusal_record_count": refusal_records,
        "top_motifs": top_motifs,
        "tail_risk_meter": tail_risk_meter,
        "quadruple_filter": {
            "bayes_evidence": False,
            "out_of_sample_validation": False,
            "tail_risk_audit": tail_breaker_total > 0 and tail_breaker_blocked == 0,
            "regime_stationarity": False,
        },
        "anti_survivorship": False,
        "info_note": (
            "Synthesised from replay_dtr.jsonl + local_lab_tail_risk_review.json. "
            "Live wiring of src/meta_minimal/refusal_journal/refusal_journal.py "
            "into the Shadow main loop is a separate refactor."
        ),
    }


def synthesise_model_risk_register(*, build_root: Path) -> dict[str, object]:
    """Honest empty registry until artefacts get registered through governed upload."""

    return {
        "snapshot_at": datetime.now(tz=UTC).isoformat(),
        "source": "scripts/run_governance_snapshot_seed.py",
        "active_ml": None,
        "active_regime_detector": None,
        "shadow_ml_challenger": None,
        "shadow_regime_detector_challenger": None,
        "promotion_eligible": False,
        "info_note": (
            "No ML or regime detector artefact registered yet. Phase 3 upload UI "
            "(POST /artefact/upload) will populate this registry through the "
            "governed command queue."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Seed cockpit governance snapshots.")
    parser.add_argument(
        "--service-dir",
        type=Path,
        default=REPO_ROOT / "build" / "build11_live_websocket_campaign" / "service",
    )
    parser.add_argument(
        "--auto-exports-root",
        type=Path,
        default=REPO_ROOT / "build" / "build11_live_websocket_campaign" / "auto_exports",
    )
    parser.add_argument("--build-root", type=Path, default=REPO_ROOT / "build")
    args = parser.parse_args(argv)

    service_dir = args.service_dir.expanduser().resolve()
    service_dir.mkdir(parents=True, exist_ok=True)

    refusal_payload = synthesise_refusal_journal(
        auto_exports_root=args.auto_exports_root.expanduser().resolve(),
        build_root=args.build_root.expanduser().resolve(),
    )
    model_risk_payload = synthesise_model_risk_register(
        build_root=args.build_root.expanduser().resolve(),
    )

    refusal_path = service_dir / "refusal_journal.snapshot.json"
    model_risk_path = service_dir / "model_risk_register.snapshot.json"
    atomic_write_json(refusal_path, refusal_payload, indent=2)
    atomic_write_json(model_risk_path, model_risk_payload, indent=2)

    sys.stdout.write(
        f"Refusal journal      → {refusal_path}\n"
        f"  records inspected  : {refusal_payload['total_records_inspected']}\n"
        f"  refusal records    : {refusal_payload['refusal_record_count']}\n"
        f"  top motifs         : {len(refusal_payload['top_motifs'])}\n"
        f"  tail risk meter    : {refusal_payload['tail_risk_meter']:.2%}\n"
        f"Model risk register  → {model_risk_path}\n"
        f"  active ML          : {model_risk_payload['active_ml']}\n"
        f"  promotion eligible : {model_risk_payload['promotion_eligible']}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
