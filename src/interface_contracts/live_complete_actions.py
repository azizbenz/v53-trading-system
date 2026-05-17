"""Shared typed Build-17 action contracts."""

from __future__ import annotations

from enum import StrEnum


class LiveCompleteAllowedAction(StrEnum):
    """Allowed Build-17 operator actions serialized as stable string values."""

    SET_HALTED = "set_halted"
    ROLLBACK_TO_LIGHT = "rollback_to_light"
    SUSPEND_PAIR = "suspend_pair"
    REQUEST_PAIR_RESUME = "request_pair_resume"
    SUSPEND_ENGINE = "suspend_engine"
    REQUEST_ENGINE_RESUME = "request_engine_resume"
    REQUEST_UPLOAD_ML_ARTIFACT = "request_upload_ml_artifact"
    REQUEST_UPLOAD_REGIME_DETECTOR_ARTIFACT = "request_upload_regime_detector_artifact"
    REQUEST_UPLOAD_SHADOW_ML_CHALLENGER_ARTIFACT = (
        "request_upload_shadow_ml_challenger_artifact"
    )
    REQUEST_UPLOAD_SHADOW_REGIME_DETECTOR_CHALLENGER_ARTIFACT = (
        "request_upload_shadow_regime_detector_challenger_artifact"
    )
    REQUEST_CLEAR_SHADOW_ML_CHALLENGER_ARTIFACT = (
        "request_clear_shadow_ml_challenger_artifact"
    )
    REQUEST_CLEAR_SHADOW_REGIME_DETECTOR_CHALLENGER_ARTIFACT = (
        "request_clear_shadow_regime_detector_challenger_artifact"
    )
    REQUEST_EXPORT_ACTIVE_ML_ARTIFACT = "request_export_active_ml_artifact"
    REQUEST_EXPORT_ACTIVE_REGIME_DETECTOR_ARTIFACT = (
        "request_export_active_regime_detector_artifact"
    )
    REQUEST_EXPORT_SHADOW_ML_ARTIFACT_COMPARISON_EVIDENCE = (
        "request_export_shadow_ml_artifact_comparison_evidence"
    )
    REQUEST_EXPORT_SHADOW_REGIME_DETECTOR_ARTIFACT_COMPARISON_EVIDENCE = (
        "request_export_shadow_regime_detector_artifact_comparison_evidence"
    )
    REQUEST_EXPORT_SHADOW_CHALLENGER_VERDICT_BUNDLE = (
        "request_export_shadow_challenger_verdict_bundle"
    )
    REQUEST_EXPORT_REGIME_DETECTOR_SHADOW_AUDIT_BUNDLE = (
        "request_export_regime_detector_shadow_audit_bundle"
    )
    REQUEST_UPLOAD_BINANCE_CREDENTIALS_BUNDLE = (
        "request_upload_binance_credentials_bundle"
    )
    REQUEST_ACTIVATE_BINANCE_CREDENTIALS_PROFILE = (
        "request_activate_binance_credentials_profile"
    )
    REQUEST_EXPORT_BINANCE_CREDENTIAL_INVENTORY = (
        "request_export_binance_credential_inventory"
    )
    REQUEST_DEACTIVATE_BINANCE_CREDENTIALS_PROFILE = (
        "request_deactivate_binance_credentials_profile"
    )
    VIEW_COMPLETE_GATES = "view_complete_gates"


class LiveCompleteForbiddenAction(StrEnum):
    """Forbidden Build-17 operator actions serialized as stable string values."""

    PROFILE_CUSTOM = "profile_custom"
    ACTIVATE_UNVALIDATED_ENGINE = "activate_unvalidated_engine"
    MODIFY_RISK_CAPS = "modify_risk_caps"
    INJECT_UNVERSIONED_CONFIG = "inject_unversioned_config"
    BYPASS_HARD_BLOCKER = "bypass_hard_blocker"


__all__ = [
    "LiveCompleteAllowedAction",
    "LiveCompleteForbiddenAction",
]
