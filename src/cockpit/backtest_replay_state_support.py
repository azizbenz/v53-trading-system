"""Reader helpers for the /backtest/replay drill-down NEW cards (Patch A).

Two operator surfaces that are specific to the replay sub-page and read straight
from a pinned run's artifacts (kept out of the large strategy_ladder_summary
enrichment so the wiring stays isolated and low-risk):

  - prod-safety contract  : ``a2_gold_prod_safety_contract.json`` (A2 gold phase)
  - loss analysis ledger  : ``loss_analysis_ledger.jsonl`` (B2 detailed replay)

Both readers are defensive: any missing file / parse error yields a snapshot
with ``is_available=False`` so the template renders an explicit "not available"
state instead of raising.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProdSafetyContractCardSnapshot:
    is_available: bool = False
    schema_version: str = ""
    prod_safety_status: str = "PROD_SAFETY_NOT_PROVEN"
    prod_safe: bool = False
    allowed_usage: tuple[str, ...] = ()
    blocked_usage: tuple[str, ...] = ()
    source_path: str = ""


@dataclass(frozen=True)
class LossLedgerRow:
    trade_id: str = ""
    pair: str = ""
    engine_id: str = ""
    capital_bucket: int = 0
    loss_bps: float = 0.0
    loss_classification: str = ""
    primary_cause: str = ""
    secondary_causes: tuple[str, ...] = ()


@dataclass(frozen=True)
class LossAnalysisLedgerCardSnapshot:
    is_available: bool = False
    total_loss_count: int = 0
    top_rows: tuple[LossLedgerRow, ...] = ()
    source_path: str = ""


def _first_existing(*candidates: Path) -> Path | None:
    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def read_prod_safety_contract(a2_root: Path | None) -> ProdSafetyContractCardSnapshot:
    """Read ``a2_gold_prod_safety_contract.json`` from the A2 gold phase root."""
    if a2_root is None:
        return ProdSafetyContractCardSnapshot()
    path = _first_existing(
        a2_root / "a2_gold_prod_safety_contract.json",
        a2_root / "reports" / "a2_gold_prod_safety_contract.json",
    )
    if path is None:
        return ProdSafetyContractCardSnapshot()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ProdSafetyContractCardSnapshot()
    if not isinstance(payload, dict):
        return ProdSafetyContractCardSnapshot()

    def _str_tuple(value: object) -> tuple[str, ...]:
        if isinstance(value, (list, tuple)):
            return tuple(str(item) for item in value if str(item).strip())
        return ()

    return ProdSafetyContractCardSnapshot(
        is_available=True,
        schema_version=str(payload.get("schema_version") or ""),
        prod_safety_status=str(payload.get("prod_safety_status") or "PROD_SAFETY_NOT_PROVEN"),
        prod_safe=bool(payload.get("prod_safe")),
        allowed_usage=_str_tuple(payload.get("allowed_usage")),
        blocked_usage=_str_tuple(payload.get("blocked_usage")),
        source_path=str(path),
    )


def read_loss_analysis_ledger(
    b2_root: Path | None,
    *,
    top_n: int = 10,
) -> LossAnalysisLedgerCardSnapshot:
    """Read ``loss_analysis_ledger.jsonl`` from the B2 phase root (globbed).

    Rows are sorted by ``loss_bps`` descending and the worst ``top_n`` returned.
    """
    if b2_root is None:
        return LossAnalysisLedgerCardSnapshot()
    # IMPORTANT: bounded search only. The B2 phase root can be a very large tree
    # on the runs drive; an unbounded recursive `**` glob would walk the whole
    # tree and stall every replay page load. The ledger lives at the run dir,
    # which is at most a few known levels deep
    # (e.g. <b2_root>/backtest_strategy_ladder/<workflow>/loss_analysis_ledger.jsonl).
    path = _first_existing(b2_root / "loss_analysis_ledger.jsonl")
    if path is None:
        for pattern in (
            "*/loss_analysis_ledger.jsonl",
            "*/*/loss_analysis_ledger.jsonl",
            "*/*/*/loss_analysis_ledger.jsonl",
        ):
            try:
                matches = sorted(b2_root.glob(pattern))
            except OSError:
                matches = []
            if matches:
                path = matches[0]
                break
    if path is None:
        return LossAnalysisLedgerCardSnapshot()
    rows: list[LossLedgerRow] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return LossAnalysisLedgerCardSnapshot()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict):
            continue
        secondary = record.get("secondary_causes")
        rows.append(
            LossLedgerRow(
                trade_id=str(record.get("trade_id") or ""),
                pair=str(record.get("pair") or ""),
                engine_id=str(record.get("engine_id") or ""),
                capital_bucket=int(record.get("capital_bucket") or 0),
                loss_bps=float(record.get("loss_bps") or 0.0),
                loss_classification=str(record.get("loss_classification") or ""),
                primary_cause=str(record.get("primary_cause") or ""),
                secondary_causes=tuple(
                    str(item) for item in secondary
                    if isinstance(secondary, (list, tuple)) and str(item).strip()
                ),
            )
        )
    rows.sort(key=lambda r: r.loss_bps, reverse=True)
    return LossAnalysisLedgerCardSnapshot(
        is_available=True,
        total_loss_count=len(rows),
        top_rows=tuple(rows[: max(0, top_n)]),
        source_path=str(path),
    )
