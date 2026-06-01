"""Tests for the /backtest/replay NEW card readers (Patch A 2026-05-31)."""

from __future__ import annotations

import json
from pathlib import Path

from cockpit.backtest_replay_state_support import (
    read_loss_analysis_ledger,
    read_prod_safety_contract,
)


def test_prod_safety_contract_reads_contract(tmp_path: Path) -> None:
    a2_root = tmp_path / "phase_a2_data_factory"
    a2_root.mkdir()
    (a2_root / "a2_gold_prod_safety_contract.json").write_text(
        json.dumps(
            {
                "schema_version": "strategy_ladder.a2_gold_prod_safety_contract.v2",
                "prod_safety_status": "PROD_SAFE_BLOCKED_BY_BOOK_NOT_FRESH",
                "prod_safe": False,
                "allowed_usage": ["RESEARCH_ONLY"],
                "blocked_usage": ["LIVE_PROMOTION", "MICRO_LIVE"],
            }
        ),
        encoding="utf-8",
    )

    snap = read_prod_safety_contract(a2_root)

    assert snap.is_available is True
    assert snap.prod_safe is False
    assert snap.prod_safety_status == "PROD_SAFE_BLOCKED_BY_BOOK_NOT_FRESH"
    assert snap.allowed_usage == ("RESEARCH_ONLY",)
    assert snap.blocked_usage == ("LIVE_PROMOTION", "MICRO_LIVE")


def test_prod_safety_contract_fail_soft_when_missing(tmp_path: Path) -> None:
    assert read_prod_safety_contract(None).is_available is False
    assert read_prod_safety_contract(tmp_path).is_available is False


def test_loss_ledger_reads_top_n_sorted_desc(tmp_path: Path) -> None:
    b2_root = tmp_path / "phase_b2_detailed_replay"
    nested = b2_root / "backtest_strategy_ladder" / "wf-1"
    nested.mkdir(parents=True)
    rows = [
        {"trade_id": "c1-400", "pair": "BTCUSDT", "engine_id": "engine_a", "loss_bps": 12.0,
         "loss_classification": "LIQUIDITY_FRAGILITY", "primary_cause": "SPREAD", "secondary_causes": ["SLIPPAGE"]},
        {"trade_id": "c2-400", "pair": "BTCUSDT", "engine_id": "engine_c", "loss_bps": 88.5,
         "loss_classification": "ADVERSE_SELECTION", "primary_cause": "ADVERSE", "secondary_causes": []},
        {"trade_id": "c3-400", "pair": "ETHUSDT", "engine_id": "engine_a", "loss_bps": 41.0,
         "loss_classification": "COST", "primary_cause": "FEE", "secondary_causes": ["SPREAD", "SLIPPAGE"]},
    ]
    (nested / "loss_analysis_ledger.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
    )

    snap = read_loss_analysis_ledger(b2_root, top_n=2)

    assert snap.is_available is True
    assert snap.total_loss_count == 3
    assert len(snap.top_rows) == 2
    # sorted by loss_bps desc -> worst first
    assert snap.top_rows[0].trade_id == "c2-400"
    assert snap.top_rows[0].loss_bps == 88.5
    assert snap.top_rows[1].trade_id == "c3-400"
    assert snap.top_rows[1].secondary_causes == ("SPREAD", "SLIPPAGE")


def test_loss_ledger_fail_soft_when_missing(tmp_path: Path) -> None:
    assert read_loss_analysis_ledger(None).is_available is False
    assert read_loss_analysis_ledger(tmp_path).is_available is False
