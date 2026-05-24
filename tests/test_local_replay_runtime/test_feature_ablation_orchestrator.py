from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from local_replay_runtime.expected_edge_feature_ablation_orchestrator import (
    FeatureAblationMetrics,
    FeatureAblationRequest,
    FeaturePromotionThresholds,
    apply_feature_promotion_to_registry,
    run_feature_ablation,
)
from local_replay_runtime.expected_edge_feature_promotion_registry import (
    ExpectedEdgeFeatureVerdict,
    FeaturePromotionRegistry,
    load_feature_promotion_registry,
)


def _thresholds() -> FeaturePromotionThresholds:
    return FeaturePromotionThresholds(
        psr_promote_threshold=0.02,
        psr_demote_threshold=0.02,
        sharpe_promote_threshold=0.01,
        sharpe_demote_threshold=0.01,
        break_even_promote_bps=0.5,
        break_even_demote_bps=0.5,
        shap_top_n=5,
    )


def _request(
    tmp_path: Path,
    *,
    baseline_psr: float,
    ablated_psr: float,
    baseline_sharpe: float,
    ablated_sharpe: float,
    baseline_break_even_bps: float = 10.0,
    ablated_break_even_bps: float = 12.0,
    baseline_trade_count: int = 300,
    ablated_trade_count: int = 300,
    shap_rank: int | None = 1,
    talab_quadruple_pass: bool = True,
    min_btl: int = 252,
) -> FeatureAblationRequest:
    return FeatureAblationRequest(
        pair="BTCUSDT",
        timeframe="1m",
        feature_name="vpin",
        shap_rank=shap_rank,
        baseline_metrics=FeatureAblationMetrics(
            psr=baseline_psr,
            sharpe=baseline_sharpe,
            break_even_bps=baseline_break_even_bps,
            trade_count=baseline_trade_count,
        ),
        ablated_metrics=FeatureAblationMetrics(
            psr=ablated_psr,
            sharpe=ablated_sharpe,
            break_even_bps=ablated_break_even_bps,
            trade_count=ablated_trade_count,
        ),
        talab_quadruple_pass=talab_quadruple_pass,
        min_btl=min_btl,
        thresholds=_thresholds(),
        output_dir=tmp_path,
    )


def test_ablation_promotes_when_positive_psr_delta(tmp_path: Path) -> None:
    report = run_feature_ablation(
        _request(
            tmp_path,
            baseline_psr=0.92,
            ablated_psr=0.85,
            baseline_sharpe=0.31,
            ablated_sharpe=0.27,
        )
    )
    assert report.delta_psr == pytest.approx(0.07)
    assert report.verdict == ExpectedEdgeFeatureVerdict.PROMOTED


def test_ablation_demotes_when_negative_psr_delta(tmp_path: Path) -> None:
    report = run_feature_ablation(
        _request(
            tmp_path,
            baseline_psr=0.85,
            ablated_psr=0.92,
            baseline_sharpe=0.27,
            ablated_sharpe=0.31,
            baseline_break_even_bps=12.0,
            ablated_break_even_bps=10.0,
        )
    )
    assert report.verdict == ExpectedEdgeFeatureVerdict.DEMOTED


def test_ablation_insufficient_evidence_when_min_btl_unmet(tmp_path: Path) -> None:
    report = run_feature_ablation(
        _request(
            tmp_path,
            baseline_psr=0.92,
            ablated_psr=0.85,
            baseline_sharpe=0.31,
            ablated_sharpe=0.27,
            baseline_trade_count=100,
            ablated_trade_count=100,
        )
    )
    assert report.verdict == ExpectedEdgeFeatureVerdict.INSUFFICIENT_EVIDENCE


def test_ablation_neutral_when_within_thresholds(tmp_path: Path) -> None:
    report = run_feature_ablation(
        _request(
            tmp_path,
            baseline_psr=0.90,
            ablated_psr=0.885,
            baseline_sharpe=0.30,
            ablated_sharpe=0.295,
            baseline_break_even_bps=10.0,
            ablated_break_even_bps=10.2,
            shap_rank=10,
        )
    )
    assert report.verdict == ExpectedEdgeFeatureVerdict.NEUTRAL


def test_ablation_demoted_when_talab_quadruple_fails(tmp_path: Path) -> None:
    report = run_feature_ablation(
        _request(
            tmp_path,
            baseline_psr=0.92,
            ablated_psr=0.85,
            baseline_sharpe=0.31,
            ablated_sharpe=0.27,
            talab_quadruple_pass=False,
        )
    )
    assert report.verdict == ExpectedEdgeFeatureVerdict.DEMOTED


def test_compute_verdict_no_magic_numbers() -> None:
    with pytest.raises(ValidationError):
        FeaturePromotionThresholds()


def test_report_evidence_artifact_persisted(tmp_path: Path) -> None:
    report = run_feature_ablation(
        _request(
            tmp_path,
            baseline_psr=0.92,
            ablated_psr=0.85,
            baseline_sharpe=0.31,
            ablated_sharpe=0.27,
        )
    )
    assert Path(report.evidence_artifact_ref).is_file()


def test_apply_to_registry_replaces_existing_entry(tmp_path: Path) -> None:
    registry_path = tmp_path / "feature_promotion_registry.json"
    first_report = run_feature_ablation(
        _request(
            tmp_path,
            baseline_psr=0.92,
            ablated_psr=0.85,
            baseline_sharpe=0.31,
            ablated_sharpe=0.27,
        )
    )
    apply_feature_promotion_to_registry(
        first_report,
        registry_path,
        pair="BTCUSDT",
        timeframe="1m",
    )
    second_report = run_feature_ablation(
        _request(
            tmp_path,
            baseline_psr=0.85,
            ablated_psr=0.92,
            baseline_sharpe=0.27,
            ablated_sharpe=0.31,
            baseline_break_even_bps=12.0,
            ablated_break_even_bps=10.0,
        )
    )
    updated = apply_feature_promotion_to_registry(
        second_report,
        registry_path,
        pair="BTCUSDT",
        timeframe="1m",
    )
    assert isinstance(updated, FeaturePromotionRegistry)
    loaded = load_feature_promotion_registry(registry_path)
    entries = loaded.entries_for_pair_tf("BTCUSDT", "1m")
    assert len(entries) == 1
    assert entries[0].verdict == ExpectedEdgeFeatureVerdict.DEMOTED
