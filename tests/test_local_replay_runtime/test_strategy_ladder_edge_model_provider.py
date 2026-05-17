"""Tests pour strategy_ladder_edge_model_provider (Audit 2026-05-07 MVP)."""

from __future__ import annotations

import base64
from datetime import UTC, date, datetime, timedelta
import hashlib
import json
from pathlib import Path

import pytest

from interface_contracts import MlModelArtifact
from local_replay_runtime.ml_governance_sidecars import (
    ML_ANTI_LEAKAGE_PROOF_FILENAME,
    build_ml_anti_leakage_proof_artifact,
)
from local_replay_runtime.strategy_ladder_edge_model_provider import (
    EdgeEstimate,
    estimate_forward_return_edge_bps,
    load_governed_expected_edge_model_artifact,
)
from local_replay_runtime.strategy_ladder_economic_provenance import (
    expected_edge_backtest_truth_status,
    is_expected_edge_backtest_truth,
)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, separators=(",", ":")) for row in rows) + "\n",
        encoding="utf-8",
    )


def _feature_hash(feature_names: tuple[str, ...]) -> str:
    return hashlib.sha256(
        json.dumps(list(feature_names), sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _build_expected_edge_artifact() -> MlModelArtifact:
    feature_names = ("edge_score",)
    now = datetime(2026, 5, 9, tzinfo=UTC)
    return MlModelArtifact.create(
        feature_names=feature_names,
        feature_hash=_feature_hash(feature_names),
        pair_universe=("BTCUSDT",),
        train_window={
            "start_at": datetime(2025, 1, 1, tzinfo=UTC),
            "end_at": datetime(2025, 3, 1, tzinfo=UTC),
        },
        validation_window={
            "start_at": datetime(2025, 3, 2, tzinfo=UTC),
            "end_at": datetime(2025, 4, 1, tzinfo=UTC),
        },
        oos_sharpe=1.1,
        backtest_sharpe=1.0,
        training_seed=7,
        created_at=now,
        calibration_version="v1",
        dataset_hash="d" * 64,
        model_bytes_b64=base64.b64encode(b"fixture-model").decode("ascii"),
        training_metrics={
            "strategy_ladder_target_policy": "strategy_ladder_forward_return_label",
            "strategy_ladder_label_source": "strategy_ladder_forward_return_label",
            "strategy_ladder_label_hash": "e" * 64,
            "strategy_ladder_target_horizon_minutes": 5,
            "strategy_ladder_purge_window_minutes": 30,
            "strategy_ladder_embargo_window_minutes": 30,
            "strategy_ladder_walkforward_status": "EXPECTED_EDGE_WALKFORWARD_DECLARED",
            "strategy_ladder_split_declared": True,
            "strategy_ladder_label_fidelity": "EXPECTED_EDGE_GOVERNANCE_CANDIDATE",
        },
        stale_after=now + timedelta(days=7),
    )


def test_estimate_edge_uptrend(tmp_path: Path) -> None:
    """Sur un uptrend stable, edge_bps > 0."""
    base_ts = 1_700_000_000_000
    rows = [
        {
            "timestamp_ms": base_ts + i * 60_000,
            "open": 100.0 + i * 0.05,
            "high": 100.05 + i * 0.05,
            "low": 99.95 + i * 0.05,
            "close": 100.0 + i * 0.05,
            "volume": 10.0,
        }
        for i in range(15)
    ]
    path = tmp_path / "ohlcv.jsonl"
    _write_jsonl(path, rows)

    est = estimate_forward_return_edge_bps(
        raw_ohlcv_path=path,
        timestamp_ms=base_ts + 14 * 60_000,
        lookback_ms=15 * 60_000,
    )
    assert isinstance(est, EdgeEstimate)
    assert est.detector_status == "MEASURED"
    assert est.provenance == "PROXY_FORWARD_RETURN_MEDIAN_TO_CALIBRATE"
    assert not est.provenance.startswith("MEASURED_")
    assert not is_expected_edge_backtest_truth(est.provenance)
    assert expected_edge_backtest_truth_status(est.provenance) == "EXPECTED_EDGE_PROXY_BLOCKED"
    assert est.edge_bps > 0.0  # uptrend → positive median forward return


def test_forward_return_proxy_estimate_never_claims_measured_backtest_truth(
    tmp_path: Path,
) -> None:
    base_ts = 1_700_000_000_000
    rows = [
        {
            "timestamp_ms": base_ts + i * 60_000,
            "open": 100.0 + i * 0.05,
            "high": 100.05 + i * 0.05,
            "low": 99.95 + i * 0.05,
            "close": 100.0 + i * 0.05,
            "volume": 10.0,
        }
        for i in range(15)
    ]
    path = tmp_path / "ohlcv.jsonl"
    _write_jsonl(path, rows)

    est = estimate_forward_return_edge_bps(
        raw_ohlcv_path=path,
        timestamp_ms=base_ts + 14 * 60_000,
        lookback_ms=15 * 60_000,
    )

    assert est.detector_status == "MEASURED"
    assert est.provenance == "PROXY_FORWARD_RETURN_MEDIAN_TO_CALIBRATE"
    assert expected_edge_backtest_truth_status(est.provenance) == "EXPECTED_EDGE_PROXY_BLOCKED"
    assert est.artifact_hash is None
    assert est.feature_hash is None
    assert est.model_status == "EXPECTED_EDGE_MODEL_NOT_USED"


def test_estimate_edge_missing_path_returns_default() -> None:
    est = estimate_forward_return_edge_bps(
        raw_ohlcv_path=None,
        timestamp_ms=1_700_000_000_000,
    )
    assert est.detector_status == "OHLCV_PATH_MISSING"
    assert est.provenance == "DEFAULT_TO_CALIBRATE"
    assert est.edge_bps == 0.0


def test_estimate_edge_insufficient_bars(tmp_path: Path) -> None:
    """Avec < min_bars (default 5), retourne INSUFFICIENT_BARS."""
    base_ts = 1_700_000_000_000
    rows = [
        {
            "timestamp_ms": base_ts + i * 60_000,
            "open": 100.0,
            "high": 100.1,
            "low": 99.9,
            "close": 100.0,
            "volume": 10.0,
        }
        for i in range(3)
    ]
    path = tmp_path / "ohlcv.jsonl"
    _write_jsonl(path, rows)
    est = estimate_forward_return_edge_bps(
        raw_ohlcv_path=path,
        timestamp_ms=base_ts + 3 * 60_000,
        min_bars=5,
    )
    assert est.detector_status.startswith("INSUFFICIENT_BARS")
    assert est.edge_bps == 0.0


def test_estimate_edge_causal_no_lookahead(tmp_path: Path) -> None:
    """Le lookback est causal : seuls les bars <= timestamp_ms sont utilises."""
    base_ts = 1_700_000_000_000
    rows = [
        {
            "timestamp_ms": base_ts + i * 60_000,
            "open": 100.0,
            "high": 100.1,
            "low": 99.9,
            "close": 100.0 + (i if i < 5 else (i - 5) * -1),  # change apres t=5
            "volume": 10.0,
        }
        for i in range(15)
    ]
    path = tmp_path / "ohlcv.jsonl"
    _write_jsonl(path, rows)
    # Causal cut au bar 4 : ne doit voir que les bars 0..4 (uptrend)
    est = estimate_forward_return_edge_bps(
        raw_ohlcv_path=path,
        timestamp_ms=base_ts + 4 * 60_000,
        lookback_ms=15 * 60_000,
    )
    assert est.n_lookback_bars_used == 5  # bars 0..4 inclus
    assert est.edge_bps > 0.0


def test_load_governed_expected_edge_model_without_artifact_stays_proxy_discovery_only() -> None:
    result = load_governed_expected_edge_model_artifact(
        None,
        expected_artifact_hash=None,
    )

    assert result.model is None
    assert result.status == "EXPECTED_EDGE_PROXY_DISCOVERY_ONLY"
    assert result.label_fidelity == "EXPECTED_EDGE_PROXY_DISCOVERY_ONLY"
    assert result.anti_leakage_status == "EXPECTED_EDGE_ANTI_LEAKAGE_MISSING"
    assert "EXPECTED_EDGE_PROXY_BLOCKED" in result.blocker_codes


def test_load_governed_expected_edge_model_without_anti_leakage_proof_is_candidate_only(
    tmp_path: Path,
) -> None:
    artifact = _build_expected_edge_artifact()
    artifact_path = tmp_path / "expected_edge_artifact.json"
    artifact_path.write_text(
        artifact.model_dump_json(indent=2),
        encoding="utf-8",
    )

    result = load_governed_expected_edge_model_artifact(
        artifact_path,
        expected_artifact_hash=artifact.artifact_hash,
        now=datetime(2026, 5, 9, tzinfo=UTC),
    )

    assert result.model is None
    assert result.status == "EXPECTED_EDGE_GOVERNANCE_CANDIDATE"
    assert result.training_artifact_ref == str(artifact_path.resolve())
    assert result.label_source == "strategy_ladder_forward_return_label"
    assert result.label_fidelity == "EXPECTED_EDGE_GOVERNANCE_CANDIDATE"
    assert result.anti_leakage_status == "EXPECTED_EDGE_ANTI_LEAKAGE_MISSING"
    assert result.walkforward_status == "EXPECTED_EDGE_WALKFORWARD_DECLARED"
    assert result.horizon_minutes == 5
    assert result.purge_window_minutes == 30
    assert result.embargo_window_minutes == 30
    assert "EXPECTED_EDGE_ANTI_LEAKAGE_PROOF_MISSING" in result.blocker_codes
    assert "EXPECTED_EDGE_PROXY_BLOCKED" in result.blocker_codes
    assert "EXPECTED_EDGE_NOT_PROMOTION_GRADE" in result.blocker_codes


def test_load_governed_expected_edge_model_with_research_only_label_fidelity_stays_blocked(
    tmp_path: Path,
) -> None:
    base_artifact = _build_expected_edge_artifact()
    payload = base_artifact.model_dump()
    payload.pop("artifact_hash", None)
    payload["training_metrics"] = {
        **base_artifact.training_metrics,
        "strategy_ladder_label_fidelity": "LABEL_STORE_RESEARCH_ONLY",
    }
    artifact = MlModelArtifact.create(**payload)
    artifact_path = tmp_path / "expected_edge_artifact.json"
    artifact_path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    proof = build_ml_anti_leakage_proof_artifact(
        artifact,
        test_start=date(2025, 4, 2),
        test_end=date(2025, 4, 30),
        created_at=datetime(2026, 5, 9, tzinfo=UTC),
    )
    (tmp_path / ML_ANTI_LEAKAGE_PROOF_FILENAME).write_text(
        proof.model_dump_json(indent=2),
        encoding="utf-8",
    )

    result = load_governed_expected_edge_model_artifact(
        artifact_path,
        expected_artifact_hash=artifact.artifact_hash,
        now=datetime(2026, 5, 9, tzinfo=UTC),
    )

    assert result.model is None
    assert result.status == "EXPECTED_EDGE_GOVERNANCE_CANDIDATE"
    assert result.anti_leakage_status == "EXPECTED_EDGE_ANTI_LEAKAGE_PROVEN"
    assert "EXPECTED_EDGE_LABEL_FIDELITY_NOT_PROMOTION_GRADE" in result.blocker_codes
    assert "EXPECTED_EDGE_PROXY_BLOCKED" in result.blocker_codes
