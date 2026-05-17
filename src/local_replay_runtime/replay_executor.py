"""Governed session executor for LOCAL_REPLAY artifact generation."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from interface_contracts.capital_profile_contracts import CapitalBucketProfile
from local_replay_runtime.artifact_exporter import (
    ReplayArtifactExportRequest,
    ReplayArtifactExportResult,
    export_local_replay_artifact,
)
from local_replay_runtime.promotion_artifact_builder import (
    ReplayPromotionArtifactBundle,
    build_replay_promotion_artifact_bundle,
)
from local_replay_runtime.replay_dtr_exporter import export_replay_dtr_records
from local_replay_runtime.replay_metrics_collector import (
    ReplayBookDepthAvailability,
    ReplayCostParityEvidence,
    ReplayFeeProvenance,
    ReplayFillRealismEvidence,
    ReplayImpactProvenance,
    ReplayMetricsSummary,
    build_replay_metrics_summary,
)
from local_replay_runtime.replay_run_manifest import ReplayRunManifest
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


class ReplayExecutionInput(BaseModel, frozen=True):
    """Typed local replay session inputs used to produce a governed artifact."""

    run_manifest: ReplayRunManifest
    total_opportunities: int = Field(..., ge=1)
    dtr_records: tuple[DTRRecord, ...] = ()
    initial_capital: float | None = Field(default=None, gt=0.0)
    fee_provenance: ReplayFeeProvenance = Field(default_factory=ReplayFeeProvenance)
    impact_provenance: ReplayImpactProvenance = Field(default_factory=ReplayImpactProvenance)
    capital_bucket_profiles: tuple[CapitalBucketProfile, ...] = ()
    feature_bridge_payload: dict
    parity_diagnostics_payload: dict
    review_notes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_session(self) -> "ReplayExecutionInput":
        if self.run_manifest.record_count < len(self.dtr_records):
            raise ValueError(
                "ReplayExecutionInput run_manifest.record_count must cover exported DTR records"
            )
        return self


class ReplayExecutionResult(BaseModel, frozen=True):
    """Stable result of the governed local replay session executor."""

    export_result: ReplayArtifactExportResult
    metrics_summary: ReplayMetricsSummary
    promotion_artifacts: ReplayPromotionArtifactBundle = Field(
        default_factory=ReplayPromotionArtifactBundle
    )


def _review_markdown(
    execution_input: ReplayExecutionInput,
    metrics_summary: ReplayMetricsSummary,
) -> str:
    notes = execution_input.review_notes or ("No additional review note.",)
    lines = [
        "# Governed Local Replay Review",
        "",
        "## Run",
        f"- run_id: {execution_input.run_manifest.run_id}",
        f"- strategy_id: {execution_input.run_manifest.strategy_id}",
        f"- strategy_version: {execution_input.run_manifest.strategy_version}",
        f"- lineage_version: {execution_input.run_manifest.lineage_version}",
        f"- profile_scope: {execution_input.run_manifest.profile_scope.value}",
        f"- runtime_mode: {execution_input.run_manifest.runtime_mode.value}",
        f"- performance_mode: {execution_input.run_manifest.performance_mode}",
        "",
        "## Coverage",
        f"- total_opportunities: {execution_input.total_opportunities}",
        f"- total_records: {metrics_summary.total_records}",
        f"- dtr_coverage: {metrics_summary.dtr_coverage:.3f}",
        "",
        "## Replay Metrics",
        f"- expected_ce_net: {metrics_summary.ce_net:.6f}",
        "- ce_net_semantics: expected_ce_over_all_replay_dtr_records_not_realized_pnl",
        f"- expected_cost_mean: {metrics_summary.expected_cost_mean:.6f}",
        f"- replay_expected_cost_model_mean: {metrics_summary.replay_expected_cost_model_mean:.6f}",
        f"- fee_source_status: {metrics_summary.fee_source_status}",
        f"- fee_model_name: {metrics_summary.fee_model_name or 'n/a'}",
        f"- fee_rate_maker_bps: {metrics_summary.fee_rate_maker_bps if metrics_summary.fee_rate_maker_bps is not None else 'n/a'}",
        f"- fee_rate_taker_bps: {metrics_summary.fee_rate_taker_bps if metrics_summary.fee_rate_taker_bps is not None else 'n/a'}",
        f"- fee_currency: {metrics_summary.fee_currency or 'n/a'}",
        f"- fee_amount: {metrics_summary.fee_amount if metrics_summary.fee_amount is not None else 'n/a'}",
        f"- fee_bps: {metrics_summary.fee_bps if metrics_summary.fee_bps is not None else 'n/a'}",
        f"- fee_provenance_ref: {metrics_summary.fee_provenance_ref or 'n/a'}",
        f"- fee_input_hash: {metrics_summary.fee_input_hash or 'n/a'}",
        f"- fee_policy_version: {metrics_summary.fee_policy_version or 'n/a'}",
        f"- impact_source_status: {metrics_summary.impact_source_status}",
        f"- impact_model_name: {metrics_summary.impact_model_name or 'n/a'}",
        f"- impact_bps: {metrics_summary.impact_bps if metrics_summary.impact_bps is not None else 'n/a'}",
        f"- impact_notional: {metrics_summary.impact_notional if metrics_summary.impact_notional is not None else 'n/a'}",
        f"- impact_depth_ref: {metrics_summary.impact_depth_ref or 'n/a'}",
        f"- impact_depth_level: {metrics_summary.impact_depth_level if metrics_summary.impact_depth_level is not None else 'n/a'}",
        f"- impact_provenance_ref: {metrics_summary.impact_provenance_ref or 'n/a'}",
        f"- impact_input_hash: {metrics_summary.impact_input_hash or 'n/a'}",
        f"- impact_policy_version: {metrics_summary.impact_policy_version or 'n/a'}",
        f"- book_depth_source_status: {metrics_summary.book_depth_source_status}",
        f"- book_depth_levels: {metrics_summary.book_depth_levels if metrics_summary.book_depth_levels is not None else 'n/a'}",
        f"- book_depth_snapshot_count: {metrics_summary.book_depth_snapshot_count if metrics_summary.book_depth_snapshot_count is not None else 'n/a'}",
        f"- book_depth_event_count: {metrics_summary.book_depth_event_count if metrics_summary.book_depth_event_count is not None else 'n/a'}",
        f"- book_depth_missing_count: {metrics_summary.book_depth_missing_count if metrics_summary.book_depth_missing_count is not None else 'n/a'}",
        f"- impact_depth_readiness_status: {metrics_summary.impact_depth_readiness_status}",
        f"- shadow_extension_required: {metrics_summary.shadow_extension_required}",
        f"- shadow_extension_reason: {metrics_summary.shadow_extension_reason or 'n/a'}",
        f"- minimum_shadow_days_required: {metrics_summary.minimum_shadow_days_required if metrics_summary.minimum_shadow_days_required is not None else 'n/a'}",
        f"- shadow_extension_status: {metrics_summary.shadow_extension_status}",
        f"- cost_model_completeness_status: {metrics_summary.cost_model_completeness_status}",
        f"- cost_readiness_reason_codes: {', '.join(metrics_summary.cost_readiness_reason_codes) if metrics_summary.cost_readiness_reason_codes else 'n/a'}",
        f"- realized_cost_mean: {metrics_summary.realized_cost_mean:.6f}",
        f"- gross_return_total: {metrics_summary.gross_return_total:.6f}",
        f"- executed_only_net_return: {metrics_summary.executed_only_net_return if metrics_summary.executed_only_net_return is not None else 'n/a'}",
        f"- executed_only_net_return_status: {metrics_summary.executed_only_net_return_status}",
        "- executed_only_net_return_semantics: executed_and_reduced_records_only_realized_net_after_cost",
        f"- missing_realized_cost_count: {metrics_summary.missing_realized_cost_count}",
        f"- exec_rate_total: {(metrics_summary.executed_count / metrics_summary.total_records) if metrics_summary.total_records else 0.0:.6f}",
        "- exec_rate_semantics: executed_count / total_records",
        f"- non_execution_rate: {metrics_summary.non_execution_rate:.6f}",
        f"- selected_execution_rate: {metrics_summary.selected_execution_rate if metrics_summary.selected_execution_rate is not None else 'n/a'}",
        f"- drawdown_proxy: {metrics_summary.drawdown_proxy:.6f}",
        "- drawdown_proxy_semantics: gross_return_proxy_not_net_equity_max_drawdown",
        f"- initial_capital: {metrics_summary.initial_capital if metrics_summary.initial_capital is not None else 'n/a'}",
        f"- true_net_equity_max_drawdown: {metrics_summary.true_net_equity_max_drawdown if metrics_summary.true_net_equity_max_drawdown is not None else 'n/a'}",
        f"- true_net_equity_drawdown_status: {metrics_summary.true_net_equity_drawdown_status}",
        "- true_net_equity_drawdown_semantics: ordered_executed_and_reduced_realized_net_pnl_only",
        f"- fill_realism_status: {metrics_summary.fill_realism_status}",
        f"- fill_source_status: {metrics_summary.fill_source_status}",
        f"- fill_model_name: {metrics_summary.fill_model_name or 'n/a'}",
        f"- fill_model_version: {metrics_summary.fill_model_version or 'n/a'}",
        f"- fill_ratio_source: {metrics_summary.fill_ratio_source}",
        f"- fill_ratio_expected: {metrics_summary.fill_ratio_expected if metrics_summary.fill_ratio_expected is not None else 'n/a'}",
        f"- fill_ratio_observed: {metrics_summary.fill_ratio_observed if metrics_summary.fill_ratio_observed is not None else 'n/a'}",
        f"- partial_fill_rate_expected: {metrics_summary.partial_fill_rate_expected if metrics_summary.partial_fill_rate_expected is not None else 'n/a'}",
        f"- partial_fill_rate_observed: {metrics_summary.partial_fill_rate_observed if metrics_summary.partial_fill_rate_observed is not None else 'n/a'}",
        f"- no_fill_rate_expected: {metrics_summary.no_fill_rate_expected if metrics_summary.no_fill_rate_expected is not None else 'n/a'}",
        f"- no_fill_rate_observed: {metrics_summary.no_fill_rate_observed if metrics_summary.no_fill_rate_observed is not None else 'n/a'}",
        f"- synthetic_fill_flag: {metrics_summary.synthetic_fill_flag}",
        f"- measured_fill_flag: {metrics_summary.measured_fill_flag}",
        f"- realized_slippage_status: {metrics_summary.realized_slippage_status}",
        f"- cost_parity_status: {metrics_summary.cost_parity_status}",
        f"- replay_live_cost_parity_status: {metrics_summary.replay_live_cost_parity_status}",
        f"- parity_sample_count: {metrics_summary.parity_sample_count}",
        f"- cost_drift_bps: {metrics_summary.cost_drift_bps if metrics_summary.cost_drift_bps is not None else 'n/a'}",
        f"- cost_drift_status: {metrics_summary.cost_drift_status}",
        "",
        "## Parity",
        f"- status: {execution_input.parity_diagnostics_payload.get('parity_status', 'unknown')}",
        f"- decision_match_rate: {execution_input.parity_diagnostics_payload.get('decision_match_rate', 'n/a')}",
        "",
        "## Notes",
        *[f"- {note}" for note in notes],
    ]
    if metrics_summary.capital_bucket_profiles:
        lines.extend(
            [
                "",
                "## Capital Profiles",
                *[
                    (
                        f"- bucket={profile.capital_bucket} / promotion_status={profile.promotion_status} / "
                        f"allowed_pairs={','.join(profile.allowed_pairs) if profile.allowed_pairs else 'n/a'} / "
                        f"blocked_pairs={','.join(profile.blocked_pair_symbols) if profile.blocked_pair_symbols else 'n/a'} / "
                        f"max_active_pairs={profile.max_active_pairs if profile.max_active_pairs is not None else 'n/a'} / "
                        f"min_notional_block_rate={profile.min_notional_block_rate if profile.min_notional_block_rate is not None else 'n/a'} / "
                        f"fragmentation_rate={profile.capital_fragmentation_rate if profile.capital_fragmentation_rate is not None else 'n/a'}"
                    )
                    for profile in metrics_summary.capital_bucket_profiles
                ],
            ]
        )
    return "\n".join(lines) + "\n"


def execute_local_replay_export(
    output_dir: Path,
    execution_input: ReplayExecutionInput,
) -> ReplayExecutionResult:
    """Build a governed LOCAL_REPLAY artifact directly from a typed replay session."""

    metrics_summary = build_replay_metrics_summary(
        execution_input.dtr_records,
        total_opportunities=execution_input.total_opportunities,
        initial_capital=execution_input.initial_capital,
        fee_provenance=execution_input.fee_provenance,
        impact_provenance=execution_input.impact_provenance,
        book_depth_availability=ReplayBookDepthAvailability.model_validate(
            execution_input.parity_diagnostics_payload
        ),
        fill_realism=ReplayFillRealismEvidence.model_validate(
            execution_input.parity_diagnostics_payload
        ),
        cost_parity=ReplayCostParityEvidence.model_validate(
            execution_input.parity_diagnostics_payload
        ),
        capital_bucket_profiles=execution_input.capital_bucket_profiles,
    )
    promotion_artifacts = build_replay_promotion_artifact_bundle(
        run_manifest=execution_input.run_manifest,
        metrics_summary=metrics_summary,
        dtr_records=execution_input.dtr_records,
        input_data_hash=execution_input.run_manifest.artifact_hash,
    )
    replay_metrics_payload = metrics_summary.model_dump(mode="json")
    replay_metrics_payload.update(
        {
            "engine_promotion_artifacts": [
                artifact.model_dump(mode="json")
                for artifact in promotion_artifacts.engine_promotion_artifacts
            ],
            "pair_promotion_artifacts": [
                artifact.model_dump(mode="json")
                for artifact in promotion_artifacts.pair_promotion_artifacts
            ],
            "strategy_promotion_artifacts": [
                artifact.model_dump(mode="json")
                for artifact in promotion_artifacts.strategy_promotion_artifacts
            ],
            "sample_size_survival_artifacts": [
                artifact.model_dump(mode="json")
                for artifact in promotion_artifacts.sample_size_survival_artifacts
            ],
        }
    )
    export_result = export_local_replay_artifact(
        output_dir,
        ReplayArtifactExportRequest(
            run_manifest=execution_input.run_manifest,
            review_export_markdown=_review_markdown(execution_input, metrics_summary),
            feature_bridge_payload=execution_input.feature_bridge_payload,
            parity_diagnostics_payload=execution_input.parity_diagnostics_payload,
            replay_metrics_payload=replay_metrics_payload,
            replay_dtr_records=export_replay_dtr_records(execution_input.dtr_records),
            capital_profile_payloads={
                str(profile.capital_bucket): profile.model_dump(mode="json")
                for profile in metrics_summary.capital_bucket_profiles
            },
            engine_promotion_payloads={
                artifact.engine_id: artifact.model_dump(mode="json")
                for artifact in promotion_artifacts.engine_promotion_artifacts
            },
            pair_promotion_payloads={
                artifact.pair: artifact.model_dump(mode="json")
                for artifact in promotion_artifacts.pair_promotion_artifacts
            },
            strategy_promotion_payloads={
                str(artifact.strategy_id): artifact.model_dump(mode="json")
                for artifact in promotion_artifacts.strategy_promotion_artifacts
                if artifact.strategy_id is not None
            },
            sample_size_survival_payloads={
                f"{artifact.scope}:{artifact.id}": artifact.model_dump(mode="json")
                for artifact in promotion_artifacts.sample_size_survival_artifacts
            },
        ),
    )
    return ReplayExecutionResult(
        export_result=export_result,
        metrics_summary=metrics_summary,
        promotion_artifacts=promotion_artifacts,
    )


__all__ = [
    "ReplayExecutionInput",
    "ReplayExecutionResult",
    "execute_local_replay_export",
]
