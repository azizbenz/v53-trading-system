"""Support field resolvers for Shadow VPS service monitoring payload construction."""

from __future__ import annotations

from typing import TypeVar

from interface_contracts.shadow_vps_service_contracts import (
    ShadowVpsCampaignSummary,
    ShadowVpsRuntimeEvidenceBundle,
    ShadowVpsServiceState,
)


T = TypeVar("T")


def _prefer_value(primary: T | None, secondary: T | None, default: T) -> T:
    if primary is not None:
        return primary
    if secondary is not None:
        return secondary
    return default


def _prefer_text(
    primary: str | None,
    secondary: str | None,
    default: str,
    *,
    disallowed: tuple[str, ...] = (),
) -> str:
    for value in (primary, secondary):
        if value and value not in disallowed:
            return value
    return default


def _prefer_optional_text(primary: str | None, secondary: str | None) -> str:
    for value in (primary, secondary):
        if value:
            return value
    return ""


def _resolve_bootstrap_identity_fields(
    state: ShadowVpsServiceState,
    campaign_summary: ShadowVpsCampaignSummary | None,
    runtime_evidence_bundle: ShadowVpsRuntimeEvidenceBundle | None,
) -> dict[str, object]:
    return {
        "execution_runtime_bootstrap_ref": _prefer_optional_text(
            campaign_summary.execution_runtime_bootstrap_ref if campaign_summary is not None else None,
            _prefer_optional_text(
                (
                    runtime_evidence_bundle.execution_runtime_bootstrap_ref
                    if runtime_evidence_bundle is not None
                    else None
                ),
                state.last_execution_runtime_bootstrap_ref,
            ),
        ),
        "execution_runtime_bootstrap_status": _prefer_text(
            campaign_summary.execution_runtime_bootstrap_status if campaign_summary is not None else None,
            (
                runtime_evidence_bundle.execution_runtime_bootstrap_status
                if runtime_evidence_bundle is not None
                else state.last_execution_runtime_bootstrap_status
            ),
            "not_configured",
            disallowed=("not_configured",),
        ),
        "execution_runtime_bootstrap_source": _prefer_text(
            campaign_summary.execution_runtime_bootstrap_source if campaign_summary is not None else None,
            (
                runtime_evidence_bundle.execution_runtime_bootstrap_source
                if runtime_evidence_bundle is not None
                else state.last_execution_runtime_bootstrap_source
            ),
            "not_configured",
        ),
        "execution_runtime_gatekeeper_audit_ref": _prefer_optional_text(
            (
                campaign_summary.execution_runtime_gatekeeper_audit_ref
                if campaign_summary is not None
                else None
            ),
            _prefer_optional_text(
                (
                    runtime_evidence_bundle.execution_runtime_gatekeeper_audit_ref
                    if runtime_evidence_bundle is not None
                    else None
                ),
                state.last_execution_runtime_gatekeeper_audit_ref,
            ),
        ),
        "execution_runtime_gatekeeper_audit_source": _prefer_text(
            (
                campaign_summary.execution_runtime_gatekeeper_audit_source
                if campaign_summary is not None
                else None
            ),
            (
                runtime_evidence_bundle.execution_runtime_gatekeeper_audit_source
                if runtime_evidence_bundle is not None
                else state.last_execution_runtime_gatekeeper_audit_source
            ),
            "not_configured",
        ),
    }


def _resolve_bootstrap_reconciliation_fields(
    campaign_summary: ShadowVpsCampaignSummary | None,
    runtime_evidence_bundle: ShadowVpsRuntimeEvidenceBundle | None,
) -> dict[str, object]:
    return {
        "execution_runtime_bootstrap_user_data_stream_enabled": _prefer_value(
            (
                campaign_summary.execution_runtime_bootstrap_user_data_stream_enabled
                if campaign_summary is not None
                else None
            ),
            (
                runtime_evidence_bundle.execution_runtime_bootstrap_user_data_stream_enabled
                if runtime_evidence_bundle is not None
                else None
            ),
            False,
        ),
        "execution_runtime_bootstrap_reconciliation_boot_executed": _prefer_value(
            (
                campaign_summary.execution_runtime_bootstrap_reconciliation_boot_executed
                if campaign_summary is not None
                else None
            ),
            (
                runtime_evidence_bundle.execution_runtime_bootstrap_reconciliation_boot_executed
                if runtime_evidence_bundle is not None
                else None
            ),
            False,
        ),
        "execution_runtime_bootstrap_reconciliation_boot_trading_blocked": _prefer_value(
            (
                campaign_summary.execution_runtime_bootstrap_reconciliation_boot_trading_blocked
                if campaign_summary is not None
                else None
            ),
            (
                runtime_evidence_bundle.execution_runtime_bootstrap_reconciliation_boot_trading_blocked
                if runtime_evidence_bundle is not None
                else None
            ),
            False,
        ),
        "execution_runtime_bootstrap_reconciliation_boot_circuit_breaker_tripped": _prefer_value(
            (
                campaign_summary.execution_runtime_bootstrap_reconciliation_boot_circuit_breaker_tripped
                if campaign_summary is not None
                else None
            ),
            (
                runtime_evidence_bundle.execution_runtime_bootstrap_reconciliation_boot_circuit_breaker_tripped
                if runtime_evidence_bundle is not None
                else None
            ),
            False,
        ),
        "execution_runtime_bootstrap_reconciliation_boot_detail": _prefer_text(
            (
                campaign_summary.execution_runtime_bootstrap_reconciliation_boot_detail
                if campaign_summary is not None
                else None
            ),
            (
                runtime_evidence_bundle.execution_runtime_bootstrap_reconciliation_boot_detail
                if runtime_evidence_bundle is not None
                else None
            ),
            "",
        ),
        "execution_runtime_bootstrap_reconciliation_boot_recovery_action": _prefer_text(
            (
                campaign_summary.execution_runtime_bootstrap_reconciliation_boot_recovery_action
                if campaign_summary is not None
                else None
            ),
            (
                runtime_evidence_bundle.execution_runtime_bootstrap_reconciliation_boot_recovery_action
                if runtime_evidence_bundle is not None
                else None
            ),
            "",
        ),
        "execution_runtime_bootstrap_reconciliation_boot_divergence_count": _prefer_value(
            (
                campaign_summary.execution_runtime_bootstrap_reconciliation_boot_divergence_count
                if campaign_summary is not None
                else None
            ),
            (
                runtime_evidence_bundle.execution_runtime_bootstrap_reconciliation_boot_divergence_count
                if runtime_evidence_bundle is not None
                else None
            ),
            0,
        ),
    }


def _resolve_bootstrap_runtime_state_fields(
    state: ShadowVpsServiceState,
) -> dict[str, object]:
    return {
        "execution_runtime_bootstrap_remote_state_snapshot_captured": (
            state.last_execution_runtime_bootstrap_remote_state_snapshot_captured
        ),
        "execution_runtime_bootstrap_remote_open_order_count": (
            state.last_execution_runtime_bootstrap_remote_open_order_count
        ),
        "execution_runtime_bootstrap_remote_position_asset_count": (
            state.last_execution_runtime_bootstrap_remote_position_asset_count
        ),
        "execution_runtime_bootstrap_remote_open_orders_present": (
            state.last_execution_runtime_bootstrap_remote_open_orders_present
        ),
        "execution_runtime_bootstrap_remote_positions_present": (
            state.last_execution_runtime_bootstrap_remote_positions_present
        ),
        "vps_recovery_readiness_report_ref": state.last_vps_recovery_readiness_report_ref,
        "vps_recovery_status": state.last_vps_recovery_status,
        "vps_recovery_eligible_to_trade": state.last_vps_recovery_eligible_to_trade,
        "vps_warmup_summary_ref": state.last_vps_warmup_summary_ref,
        "vps_warmup_final_state": state.last_vps_warmup_final_state,
        "vps_warmup_eligible_to_trade": state.last_vps_warmup_eligible_to_trade,
        "active_ml_artifact_hash": (
            ""
            if state.active_ml_artifact is None
            else state.active_ml_artifact.artifact_hash
        ),
        "active_ml_artifact_id": (
            ""
            if state.active_ml_artifact is None
            else state.active_ml_artifact.artifact_id
        ),
        "active_regime_detector_artifact_hash": (
            ""
            if state.active_regime_detector_artifact is None
            else state.active_regime_detector_artifact.artifact_hash
        ),
        "active_regime_detector_artifact_id": (
            ""
            if state.active_regime_detector_artifact is None
            else state.active_regime_detector_artifact.artifact_id
        ),
        "active_regime_detector_shadow_audit_bundle_ref": (
            state.active_regime_detector_shadow_audit_bundle_ref
        ),
        "dashboard_control_halted": state.dashboard_control_halted,
        "dashboard_control_target_profile": state.dashboard_control_target_profile,
        "dashboard_control_target_deployment_state": (
            state.dashboard_control_target_deployment_state
        ),
        "dashboard_control_suspended_pair_count": len(
            state.dashboard_control_suspended_pairs
        ),
        "dashboard_control_suspended_engine_count": len(
            state.dashboard_control_suspended_engines
        ),
        "dashboard_control_suspended_pairs": state.dashboard_control_suspended_pairs,
        "dashboard_control_suspended_engines": state.dashboard_control_suspended_engines,
        "dashboard_control_last_request_id": state.dashboard_control_last_request_id,
        "dashboard_control_last_command_kind": state.dashboard_control_last_command_kind,
        "dashboard_control_last_result_status": state.dashboard_control_last_result_status,
    }


def resolve_bootstrap_fields(
    state: ShadowVpsServiceState,
    campaign_summary: ShadowVpsCampaignSummary | None,
    runtime_evidence_bundle: ShadowVpsRuntimeEvidenceBundle | None,
) -> dict[str, object]:
    """Resolve execution-runtime bootstrap and gatekeeper evidence fields."""

    resolved_fields = _resolve_bootstrap_identity_fields(
        state,
        campaign_summary,
        runtime_evidence_bundle,
    )
    resolved_fields.update(
        _resolve_bootstrap_reconciliation_fields(
            campaign_summary,
            runtime_evidence_bundle,
        )
    )
    resolved_fields.update(_resolve_bootstrap_runtime_state_fields(state))
    return resolved_fields


def _resolve_projection_source_fields(
    campaign_summary: ShadowVpsCampaignSummary | None,
    runtime_evidence_bundle: ShadowVpsRuntimeEvidenceBundle | None,
) -> dict[str, object]:
    return {
        "execution_runtime_projection_status": _prefer_text(
            campaign_summary.execution_runtime_projection_status if campaign_summary is not None else None,
            (
                runtime_evidence_bundle.execution_runtime_projection_status
                if runtime_evidence_bundle is not None
                else None
            ),
            "not_configured",
        ),
        "execution_runtime_projection_source_detail": _prefer_text(
            campaign_summary.execution_runtime_projection_source if campaign_summary is not None else None,
            (
                runtime_evidence_bundle.execution_runtime_projection_source
                if runtime_evidence_bundle is not None
                else None
            ),
            "not_configured",
        ),
        "regime_lite_assessment_source": _prefer_text(
            campaign_summary.regime_lite_assessment_source if campaign_summary is not None else None,
            runtime_evidence_bundle.regime_lite_assessment_source if runtime_evidence_bundle is not None else None,
            "not_configured",
        ),
        "regime_lite_safing_recommendation_source": _prefer_text(
            (
                campaign_summary.regime_lite_safing_recommendation_source
                if campaign_summary is not None
                else None
            ),
            (
                runtime_evidence_bundle.regime_lite_safing_recommendation_source
                if runtime_evidence_bundle is not None
                else None
            ),
            "not_configured",
        ),
        "info_stress_assessment_source": _prefer_text(
            campaign_summary.info_stress_assessment_source if campaign_summary is not None else None,
            runtime_evidence_bundle.info_stress_assessment_source if runtime_evidence_bundle is not None else None,
            "not_configured",
        ),
    }


def _resolve_projection_consumer_fields(
    campaign_summary: ShadowVpsCampaignSummary | None,
    runtime_evidence_bundle: ShadowVpsRuntimeEvidenceBundle | None,
) -> dict[str, object]:
    return {
        "execution_runtime_projection_ready": _prefer_value(
            campaign_summary.execution_runtime_projection_ready if campaign_summary is not None else None,
            (
                runtime_evidence_bundle.execution_runtime_projection_ready
                if runtime_evidence_bundle is not None
                else None
            ),
            False,
        ),
        "execution_runtime_projection_consumer_count": _prefer_value(
            (
                campaign_summary.execution_runtime_projection_consumer_count
                if campaign_summary is not None
                else None
            ),
            (
                runtime_evidence_bundle.execution_runtime_projection_consumer_count
                if runtime_evidence_bundle is not None
                else None
            ),
            0,
        ),
        "execution_runtime_projection_ready_consumer_count": _prefer_value(
            (
                campaign_summary.execution_runtime_projection_ready_consumer_count
                if campaign_summary is not None
                else None
            ),
            (
                runtime_evidence_bundle.execution_runtime_projection_ready_consumer_count
                if runtime_evidence_bundle is not None
                else None
            ),
            0,
        ),
        "execution_runtime_projection_partial_consumer_count": _prefer_value(
            (
                campaign_summary.execution_runtime_projection_partial_consumer_count
                if campaign_summary is not None
                else None
            ),
            (
                runtime_evidence_bundle.execution_runtime_projection_partial_consumer_count
                if runtime_evidence_bundle is not None
                else None
            ),
            0,
        ),
        "execution_runtime_projection_blocked_consumer_count": _prefer_value(
            (
                campaign_summary.execution_runtime_projection_blocked_consumer_count
                if campaign_summary is not None
                else None
            ),
            (
                runtime_evidence_bundle.execution_runtime_projection_blocked_consumer_count
                if runtime_evidence_bundle is not None
                else None
            ),
            0,
        ),
    }


def _resolve_projection_bridge_fields(
    campaign_summary: ShadowVpsCampaignSummary | None,
    runtime_evidence_bundle: ShadowVpsRuntimeEvidenceBundle | None,
) -> dict[str, object]:
    return {
        "execution_runtime_projection_bridge_status": _prefer_text(
            (
                campaign_summary.execution_runtime_projection_bridge_status
                if campaign_summary is not None
                else None
            ),
            (
                runtime_evidence_bundle.execution_runtime_projection_bridge_status
                if runtime_evidence_bundle is not None
                else None
            ),
            "planned",
        ),
        "execution_runtime_projection_bridge_loaded": _prefer_value(
            (
                campaign_summary.execution_runtime_projection_bridge_loaded
                if campaign_summary is not None
                else None
            ),
            (
                runtime_evidence_bundle.execution_runtime_projection_bridge_loaded
                if runtime_evidence_bundle is not None
                else None
            ),
            False,
        ),
        "execution_runtime_projection_rate_limit_model_loaded": _prefer_value(
            (
                campaign_summary.execution_runtime_projection_rate_limit_model_loaded
                if campaign_summary is not None
                else None
            ),
            (
                runtime_evidence_bundle.execution_runtime_projection_rate_limit_model_loaded
                if runtime_evidence_bundle is not None
                else None
            ),
            False,
        ),
        "execution_runtime_projection_spread_guard_model_loaded": _prefer_value(
            (
                campaign_summary.execution_runtime_projection_spread_guard_model_loaded
                if campaign_summary is not None
                else None
            ),
            (
                runtime_evidence_bundle.execution_runtime_projection_spread_guard_model_loaded
                if runtime_evidence_bundle is not None
                else None
            ),
            False,
        ),
        "execution_runtime_projection_slippage_model_loaded": _prefer_value(
            (
                campaign_summary.execution_runtime_projection_slippage_model_loaded
                if campaign_summary is not None
                else None
            ),
            (
                runtime_evidence_bundle.execution_runtime_projection_slippage_model_loaded
                if runtime_evidence_bundle is not None
                else None
            ),
            False,
        ),
    }


def resolve_projection_fields(
    campaign_summary: ShadowVpsCampaignSummary | None,
    runtime_evidence_bundle: ShadowVpsRuntimeEvidenceBundle | None,
) -> dict[str, object]:
    """Resolve execution-runtime projection and governed source fields."""

    resolved_fields = _resolve_projection_source_fields(
        campaign_summary,
        runtime_evidence_bundle,
    )
    resolved_fields.update(
        _resolve_projection_consumer_fields(
            campaign_summary,
            runtime_evidence_bundle,
        )
    )
    resolved_fields.update(
        _resolve_projection_bridge_fields(
            campaign_summary,
            runtime_evidence_bundle,
        )
    )
    return resolved_fields
