"""Governed expected-edge feature ablation and promotion verdict helpers."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.expected_edge_feature_promotion_registry import (
    ExpectedEdgeFeatureVerdict,
    FeaturePromotionEntry,
    FeaturePromotionRegistry,
    load_feature_promotion_registry,
    save_feature_promotion_registry,
)


class FeaturePromotionThresholds(BaseModel, frozen=True):
    schema_version: str = Field(
        default="expected_edge.feature_promotion_thresholds.v1",
        min_length=1,
    )
    psr_promote_threshold: float = Field(..., ge=0.0)
    psr_demote_threshold: float = Field(..., ge=0.0)
    sharpe_promote_threshold: float = Field(..., ge=0.0)
    sharpe_demote_threshold: float = Field(..., ge=0.0)
    break_even_promote_bps: float = Field(..., ge=0.0)
    break_even_demote_bps: float = Field(..., ge=0.0)
    shap_top_n: int = Field(..., ge=1)
    calibration_status: str = Field(default="TO_CALIBRATE", min_length=1)


class FeatureAblationMetrics(BaseModel, frozen=True):
    psr: float
    sharpe: float
    break_even_bps: float
    trade_count: int = Field(..., ge=0)


class FeatureAblationRequest(BaseModel, frozen=True):
    schema_version: str = Field(
        default="expected_edge.feature_ablation_request.v1",
        min_length=1,
    )
    pair: str = Field(..., min_length=1)
    timeframe: str = Field(..., min_length=1)
    feature_name: str = Field(..., min_length=1)
    shap_rank: int | None = Field(default=None, ge=1)
    baseline_metrics: FeatureAblationMetrics
    ablated_metrics: FeatureAblationMetrics
    talab_quadruple_pass: bool = False
    min_btl: int = Field(default=252, ge=1)
    thresholds: FeaturePromotionThresholds
    output_dir: Path


class FeatureAblationReport(BaseModel, frozen=True):
    schema_version: str = Field(
        default="expected_edge.feature_ablation_report.v1",
        min_length=1,
    )
    pair: str = Field(..., min_length=1)
    timeframe: str = Field(..., min_length=1)
    feature_name: str = Field(..., min_length=1)
    shap_rank: int | None = Field(default=None, ge=1)
    baseline_metrics: FeatureAblationMetrics
    ablated_metrics: FeatureAblationMetrics
    delta_psr: float
    delta_sharpe: float
    delta_break_even_bps: float
    talab_quadruple_pass: bool = False
    min_btl_required: int = Field(..., ge=1)
    min_btl_satisfied: bool = False
    verdict: ExpectedEdgeFeatureVerdict = ExpectedEdgeFeatureVerdict.INSUFFICIENT_EVIDENCE
    evidence_artifact_ref: str = ""
    evidence_class: str = Field(default="SHAP_AND_ABLATION_PNL", min_length=1)
    blockers: tuple[str, ...] = ()


def compute_feature_promotion_verdict(
    *,
    shap_rank: int | None,
    delta_psr: float,
    delta_sharpe: float,
    delta_break_even_bps: float,
    min_btl_satisfied: bool,
    talab_quadruple_pass: bool,
    thresholds: FeaturePromotionThresholds,
) -> ExpectedEdgeFeatureVerdict:
    if not min_btl_satisfied:
        return ExpectedEdgeFeatureVerdict.INSUFFICIENT_EVIDENCE
    if (
        delta_psr < (-1.0 * thresholds.psr_demote_threshold)
        or delta_sharpe < (-1.0 * thresholds.sharpe_demote_threshold)
        or delta_break_even_bps < (-1.0 * thresholds.break_even_demote_bps)
        or not talab_quadruple_pass
    ):
        return ExpectedEdgeFeatureVerdict.DEMOTED
    if (
        shap_rank is not None
        and shap_rank <= thresholds.shap_top_n
        and delta_psr > thresholds.psr_promote_threshold
        and delta_sharpe > thresholds.sharpe_promote_threshold
        and delta_break_even_bps > thresholds.break_even_promote_bps
        and talab_quadruple_pass
    ):
        return ExpectedEdgeFeatureVerdict.PROMOTED
    return ExpectedEdgeFeatureVerdict.NEUTRAL


def _sanitized_feature_name(feature_name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", feature_name.strip()).strip("._") or "feature"


def _evidence_path(request: FeatureAblationRequest) -> Path:
    return request.output_dir / (
        f"feature_ablation_{request.pair.upper()}_{request.timeframe}_"
        f"{_sanitized_feature_name(request.feature_name)}.json"
    )


def run_feature_ablation(request: FeatureAblationRequest) -> FeatureAblationReport:
    delta_psr = request.baseline_metrics.psr - request.ablated_metrics.psr
    delta_sharpe = request.baseline_metrics.sharpe - request.ablated_metrics.sharpe
    delta_break_even_bps = (
        request.ablated_metrics.break_even_bps - request.baseline_metrics.break_even_bps
    )
    min_btl_satisfied = (
        min(request.baseline_metrics.trade_count, request.ablated_metrics.trade_count)
        >= request.min_btl
    )
    verdict = compute_feature_promotion_verdict(
        shap_rank=request.shap_rank,
        delta_psr=delta_psr,
        delta_sharpe=delta_sharpe,
        delta_break_even_bps=delta_break_even_bps,
        min_btl_satisfied=min_btl_satisfied,
        talab_quadruple_pass=request.talab_quadruple_pass,
        thresholds=request.thresholds,
    )
    evidence_path = _evidence_path(request)
    report = FeatureAblationReport(
        pair=request.pair,
        timeframe=request.timeframe,
        feature_name=request.feature_name,
        shap_rank=request.shap_rank,
        baseline_metrics=request.baseline_metrics,
        ablated_metrics=request.ablated_metrics,
        delta_psr=delta_psr,
        delta_sharpe=delta_sharpe,
        delta_break_even_bps=delta_break_even_bps,
        talab_quadruple_pass=request.talab_quadruple_pass,
        min_btl_required=request.min_btl,
        min_btl_satisfied=min_btl_satisfied,
        verdict=verdict,
        evidence_artifact_ref=str(evidence_path.resolve()),
        blockers=(),
    )
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(evidence_path, report.model_dump(mode="json"), indent=2)
    return report


def apply_feature_promotion_to_registry(
    report: FeatureAblationReport,
    registry_path: Path,
    *,
    pair: str,
    timeframe: str,
) -> FeaturePromotionRegistry:
    registry = load_feature_promotion_registry(registry_path)
    updated = registry.upsert(
        FeaturePromotionEntry(
            pair=pair,
            timeframe=timeframe,
            feature_name=report.feature_name,
            verdict=report.verdict,
            shap_rank=report.shap_rank,
            ablation_delta_psr=report.delta_psr,
            ablation_delta_sharpe=report.delta_sharpe,
            ablation_delta_break_even_bps=report.delta_break_even_bps,
            talab_quadruple_pass=report.talab_quadruple_pass,
            min_btl_required=report.min_btl_required,
            min_btl_satisfied=report.min_btl_satisfied,
            ablation_min_btl_satisfied=report.min_btl_satisfied,
            evidence_artifact_ref=report.evidence_artifact_ref,
        )
    )
    save_feature_promotion_registry(registry_path, updated)
    return updated


__all__ = [
    "FeatureAblationMetrics",
    "FeatureAblationReport",
    "FeatureAblationRequest",
    "FeaturePromotionThresholds",
    "apply_feature_promotion_to_registry",
    "compute_feature_promotion_verdict",
    "run_feature_ablation",
]
