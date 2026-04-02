"""Minimal governed Build-13 Live-Light gate and execution-intent builder.

HARD STATEMENT §0.6: 30j shadow prerequisite enforced before Live-Light.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from interface_contracts import PromotionState, ProfileId, ReviewState, RuntimeMode
from monitoring import TechnicalDashboardPayload
from protocols.contracts import (
    LiveLightDecision,
    LiveLightExecutionIntent,
    LiveLightInput,
    LiveLightRunSummary,
    MicroLiveRunSummary,
)
from protocols.enums import (
    LiveLightRunState,
    LiveLightVerdict,
    MicroLiveRunState,
    MicroLiveVerdict,
)
from protocols.errors import LiveLightInputError

_BUILD14_CONTRACTS_MODULE = "complete_enablers.contracts"
_BUILD14_SIGNAL_CLASS = "Build14InfluenceSignal"
_BUILD14_REPORT_CLASS = "Build14InfluenceReport"


def _format_operator_safing_reason(request) -> str:
    target_mode = (
        f" -> {request.target_runtime_mode.value}"
        if request.target_runtime_mode is not None
        else ""
    )
    return (
        "operator safing request: "
        f"{request.action.value} ({request.source_runtime_mode.value}{target_mode}) "
        f"reason={request.reason}"
    )


def _normalized_value(value: object, default: str) -> str:
    if value is None:
        return default
    enum_value = getattr(value, "value", value)
    return str(enum_value)


def _is_typed_build14_contract(value: object, *, class_name: str) -> bool:
    return (
        value.__class__.__module__ == _BUILD14_CONTRACTS_MODULE
        and value.__class__.__name__ == class_name
    )


def _revalidate_typed_build14_contract(value: object) -> object:
    model_dump = getattr(value, "model_dump", None)
    model_validate = getattr(value.__class__, "model_validate", None)
    if not callable(model_dump) or not callable(model_validate):
        raise TypeError("Build-14 influence must expose Pydantic model_dump/model_validate")
    return model_validate(model_dump())


def _resolve_validated_build14_signal(
    build14_influence: object | None,
    *,
    expected_correlation_id: str,
) -> tuple[object | None, tuple[str, ...]]:
    if build14_influence is None:
        return None, ()

    if _is_typed_build14_contract(build14_influence, class_name=_BUILD14_SIGNAL_CLASS):
        contract_kind = "signal"
    elif _is_typed_build14_contract(build14_influence, class_name=_BUILD14_REPORT_CLASS):
        contract_kind = "report"
    else:
        return None, (
            "Build-14 influence must be a typed Build14InfluenceSignal or Build14InfluenceReport",
        )

    try:
        validated_contract = _revalidate_typed_build14_contract(build14_influence)
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        detail = str(first_error.get("msg", "")).strip()
        if not detail:
            detail = "Build-14 influence failed typed contract validation"
        return None, (f"Build-14 influence failed typed contract validation: {detail}",)
    except (TypeError, ValueError) as exc:
        detail = str(exc).strip() or "Build-14 influence failed typed contract validation"
        return None, (f"Build-14 influence failed typed contract validation: {detail}",)

    if contract_kind == "report":
        report_correlation_id = str(getattr(validated_contract, "correlation_id", "")).strip()
        if not report_correlation_id:
            return None, ("Build-14 influence report must expose a concrete correlation_id",)
        if report_correlation_id != expected_correlation_id:
            return None, (
                "Build-14 influence correlation_id must match the current Live-Light run",
            )
        signal = getattr(validated_contract, "signal", None)
        if signal is None or not _is_typed_build14_contract(
            signal,
            class_name=_BUILD14_SIGNAL_CLASS,
        ):
            return None, (
                "Build-14 influence report must carry a typed Build14InfluenceSignal",
            )
    else:
        signal = validated_contract

    signal_correlation_id = str(getattr(signal, "correlation_id", "")).strip()
    if not signal_correlation_id:
        return None, ("Build-14 influence must expose a concrete correlation_id",)
    if signal_correlation_id != expected_correlation_id:
        return None, (
            "Build-14 influence correlation_id must match the current Live-Light run",
        )

    return signal, ()


def _build14_reason_codes(signal: object | None) -> tuple[str, ...]:
    if signal is None:
        return ()
    raw_value = getattr(signal, "reason_codes", ())
    if raw_value is None:
        return ()
    return tuple(str(item) for item in raw_value)


def _validate_micro_live_source_payload_scope(payload: TechnicalDashboardPayload) -> None:
    if payload.profile != ProfileId.LIGHT:
        raise LiveLightInputError(
            "Build-13 Live-Light source payload must stay on profile=LIGHT"
        )
    if payload.runtime_mode != RuntimeMode.MICRO_LIVE:
        raise LiveLightInputError(
            "Build-13 Live-Light source payload must originate from runtime_mode=MICRO_LIVE"
        )


def _validate_micro_live_consistency(
    micro_live_summary: MicroLiveRunSummary,
    micro_live_payload: TechnicalDashboardPayload,
) -> None:
    replay_import = micro_live_payload.replay_import
    projection = micro_live_payload.micro_live
    normalized_status = replay_import.validation_status.strip().casefold()

    if micro_live_summary.correlation_id != micro_live_payload.correlation_id:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching correlation_id between Micro-live summary and payload"
        )
    if projection.run_state not in {"", "not_run"} and projection.run_state != micro_live_summary.run_state.value:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live run_state between summary and payload"
        )
    if projection.verdict not in {"", "not_run"} and projection.verdict != micro_live_summary.decision.verdict.value:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live verdict between summary and payload"
        )
    if projection.allowed_to_probe != micro_live_summary.decision.allowed_to_probe:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live allowed_to_probe between summary and payload"
        )
    if projection.shadow_run_id and projection.shadow_run_id != micro_live_summary.shadow_run_id:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching shadow_run_id between Micro-live summary and payload"
        )
    if projection.import_artifact_id not in {"", "none"} and projection.import_artifact_id != micro_live_summary.import_artifact_id:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live/import artifact_id"
        )
    if projection.import_lineage_version not in {"", "n/a"} and projection.import_lineage_version != micro_live_summary.import_lineage_version:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live/import lineage_version"
        )
    if normalized_status != "accepted":
        raise LiveLightInputError(
            "Build-13 Live-Light requires an accepted replay import_validation_status"
        )
    if replay_import.rejection_reasons:
        raise LiveLightInputError(
            "Build-13 Live-Light requires empty replay import_rejection_reasons"
        )
    if not replay_import.artifact_id or replay_import.artifact_id == "none":
        raise LiveLightInputError(
            "Build-13 Live-Light requires a concrete replay import_artifact_id"
        )
    if not replay_import.lineage_version or replay_import.lineage_version == "n/a":
        raise LiveLightInputError(
            "Build-13 Live-Light requires a concrete replay lineage_version"
        )
    if micro_live_summary.import_artifact_id != replay_import.artifact_id:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live/import artifact_id"
        )
    if micro_live_summary.import_lineage_version != replay_import.lineage_version:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live/import lineage_version"
        )


def _validate_live_light_surface(
    micro_live_summary: MicroLiveRunSummary,
    *,
    live_pairs: tuple[str, ...],
    active_engines: tuple[str, ...],
) -> None:
    planned_pairs = set(micro_live_summary.execution_plan.planned_pairs)
    planned_engines = set(micro_live_summary.execution_plan.planned_engines)

    if not set(live_pairs).issubset(planned_pairs):
        raise LiveLightInputError(
            "Build-13 Live-Light live_pairs must stay within the governed Micro-live planned_pairs"
        )
    if not set(active_engines).issubset(planned_engines):
        raise LiveLightInputError(
            "Build-13 Live-Light active_engines must stay within the governed Micro-live planned_engines"
        )


def _build14_guardrail_reasons(
    signal: object,
) -> tuple[str, ...]:
    reasons: list[str] = []
    influence_mode = _normalized_value(getattr(signal, "influence_mode", None), "read_only")
    action = _normalized_value(getattr(signal, "action", None), "observe")
    reason_codes = _build14_reason_codes(signal)
    confidence_penalty_weight = float(getattr(signal, "confidence_penalty_weight", 0.0))
    recommended_budget_factor = float(getattr(signal, "recommended_budget_factor", 1.0))
    requires_manual_review = bool(getattr(signal, "requires_manual_review", False))
    stability_confirmed = bool(getattr(signal, "stability_confirmed", True))
    non_regression_required = bool(getattr(signal, "non_regression_required", True))
    families = tuple(getattr(signal, "families", ()) or ())

    if (
        bool(getattr(signal, "can_override_engines", False))
        or bool(getattr(signal, "can_bypass_risk", False))
        or bool(getattr(signal, "can_bypass_portfolio", False))
    ):
        reasons.append(
            "Build-14 influence must never bypass engines, risk, or portfolio"
        )
    if bool(getattr(signal, "can_trade_autonomously", False)):
        reasons.append("Build-14 influence must never trade autonomously")
    if not non_regression_required:
        reasons.append("Build-14 influence must keep non_regression_required=True")

    if influence_mode == "shadow_enabled":
        reasons.append(
            "Shadow-enabled Build-14 outputs require explicit post-Shadow live translation before Live-Light"
        )
        return tuple(reasons)

    if influence_mode == "read_only":
        if action != "observe":
            reasons.append("read-only Build-14 influence must keep action=observe")
        if confidence_penalty_weight != 0.0:
            reasons.append("read-only Build-14 influence must keep zero confidence penalty")
        if recommended_budget_factor != 1.0:
            reasons.append("read-only Build-14 influence must keep budget factor at 1.0")
        if requires_manual_review:
            reasons.append("read-only Build-14 influence must not require manual review")
        return tuple(reasons)

    if not stability_confirmed:
        reasons.append("limited Build-14 influence requires stability_confirmed=True")
    if not families:
        reasons.append("limited Build-14 influence must reference at least one signal family")
    if action == "observe":
        reasons.append("limited Build-14 influence must not keep action=observe")
    if action == "downgrade_confidence":
        if confidence_penalty_weight <= 0.0:
            reasons.append("Build-14 confidence downgrade requires a positive penalty")
        if not 0.0 < recommended_budget_factor < 1.0:
            reasons.append("Build-14 confidence downgrade requires a bounded budget factor")
        if requires_manual_review:
            reasons.append("Build-14 confidence downgrade must stay automated and bounded")
    if action in {"review_only", "soft_veto"}:
        if not requires_manual_review:
            reasons.append("Build-14 review_only and soft_veto must require manual review")
        if recommended_budget_factor != 0.0:
            reasons.append("Build-14 review_only and soft_veto must zero the budget factor")
    if action != "observe" and not reason_codes:
        reasons.append("limited Build-14 influence must expose reason_codes")

    return tuple(reasons)


def build_live_light_input_from_micro_live(
    micro_live_summary: MicroLiveRunSummary,
    micro_live_payload: TechnicalDashboardPayload,
    *,
    live_pairs: tuple[str, ...],
    requested_total_notional_usdt: float,
    requested_pair_notional_usdt: float,
    max_total_notional_usdt: float,
    max_pair_notional_usdt: float,
    execution_order_limit: int = 3,
    active_engines: tuple[str, ...] | None = None,
    shadow_days_completed: int | None = None,
    shadow_required_days: int | None = None,
    component_verdicts_rendered: bool | None = None,
    shadow_report_ready: bool | None = None,
    micro_live_stable_days: int,
    micro_live_required_days: int = 7,
    build14_live_eligible: bool = False,
    observability_ready: bool = False,
    halt_ready: bool = False,
    operator_safing_request=None,
    execution_ready: bool = False,
    broker_ready: bool = False,
    exchange_ready: bool = False,
    onboarding_accepted: bool = False,
    onboarding_review_state: ReviewState = ReviewState.PENDING,
    onboarding_reasons: tuple[str, ...] = (),
) -> LiveLightInput:
    """Build a governed Build-13 input from Build-12 Micro-live outputs."""

    _validate_micro_live_source_payload_scope(micro_live_payload)
    _validate_micro_live_consistency(micro_live_summary, micro_live_payload)
    resolved_active_engines = active_engines or micro_live_summary.execution_plan.planned_engines
    shadow_projection = micro_live_payload.shadow
    resolved_shadow_days_completed = (
        shadow_projection.shadow_days_completed
        if shadow_days_completed is None
        else shadow_days_completed
    )
    resolved_shadow_required_days = (
        shadow_projection.shadow_required_days
        if shadow_required_days is None
        else shadow_required_days
    )
    resolved_shadow_report_ready = (
        shadow_projection.shadow_report_ready
        if shadow_report_ready is None
        else shadow_report_ready
    )
    resolved_component_verdicts_rendered = (
        (
            shadow_projection.shadow_validated_component_count
            + shadow_projection.dormant_component_count
        )
        > 0
        if component_verdicts_rendered is None
        else component_verdicts_rendered
    )
    _validate_live_light_surface(
        micro_live_summary,
        live_pairs=live_pairs,
        active_engines=resolved_active_engines,
    )
    return LiveLightInput(
        correlation_id=micro_live_summary.correlation_id,
        profile=micro_live_payload.profile,
        runtime_mode=RuntimeMode.LIVE,
        micro_live_run_id=micro_live_summary.run_id,
        shadow_run_id=micro_live_summary.shadow_run_id,
        micro_live_verdict=micro_live_summary.decision.verdict,
        micro_live_run_state=micro_live_summary.run_state,
        micro_live_blocking_reasons=micro_live_summary.decision.blocking_reasons,
        shadow_days_completed=resolved_shadow_days_completed,
        shadow_required_days=resolved_shadow_required_days,
        component_verdicts_rendered=resolved_component_verdicts_rendered,
        shadow_report_ready=resolved_shadow_report_ready,
        micro_live_stable_days=micro_live_stable_days,
        micro_live_required_days=micro_live_required_days,
        build14_live_eligible=build14_live_eligible,
        micro_live_import_artifact_id=micro_live_summary.import_artifact_id,
        micro_live_import_lineage_version=micro_live_summary.import_lineage_version,
        import_artifact_id=micro_live_payload.replay_import.artifact_id,
        import_lineage_version=micro_live_payload.replay_import.lineage_version,
        import_validation_status=micro_live_payload.replay_import.validation_status,
        import_rejection_reasons=micro_live_payload.replay_import.rejection_reasons,
        onboarding_accepted=onboarding_accepted,
        onboarding_review_state=onboarding_review_state,
        onboarding_reasons=onboarding_reasons,
        review_export_ready=micro_live_payload.shadow.review_export_ready,
        observability_ready=observability_ready,
        halt_ready=halt_ready,
        operator_safing_request=operator_safing_request,
        execution_ready=execution_ready,
        broker_ready=broker_ready,
        exchange_ready=exchange_ready,
        active_engines=resolved_active_engines,
        live_pairs=live_pairs,
        requested_total_notional_usdt=requested_total_notional_usdt,
        requested_pair_notional_usdt=requested_pair_notional_usdt,
        max_total_notional_usdt=max_total_notional_usdt,
        max_pair_notional_usdt=max_pair_notional_usdt,
        execution_order_limit=execution_order_limit,
    )


def run_live_light_gate(
    live_light_input: LiveLightInput,
    *,
    run_id: str | None = None,
    build14_influence: object | None = None,
    shadow_state_dir: Path | None = None,
) -> LiveLightRunSummary:
    """Run the minimal Build-13 gate without opening Complete or full live execution.

    HARD STATEMENT §0.6: if shadow_state_dir is provided, verifies 30 consecutive
    shadow days before allowing Live-Light promotion.
    """

    hard_blocking_reasons: list[str] = []

    # HARD STATEMENT §0.6: 30j shadow prerequisite
    if shadow_state_dir is not None:
        from protocols.shadow_runtime import check_shadow_30j_gate
        gate_passed, report = check_shadow_30j_gate(shadow_state_dir, profile="light")
        if not gate_passed:
            days = report.get("consecutive_days", 0)
            hard_blocking_reasons.append(
                f"HARD STATEMENT: Light shadow requires 30 consecutive days, "
                f"currently at {days}/30"
            )
    micro_live_needs_review = False
    build14_requires_review = False
    normalized_import_status = live_light_input.import_validation_status.strip().casefold()
    build14_signal, build14_validation_reasons = _resolve_validated_build14_signal(
        build14_influence,
        expected_correlation_id=live_light_input.correlation_id,
    )
    build14_influence_mode = _normalized_value(
        getattr(build14_signal, "influence_mode", None),
        "read_only",
    )
    build14_action = _normalized_value(
        getattr(build14_signal, "action", None),
        "observe",
    )
    build14_severity = _normalized_value(
        getattr(build14_signal, "severity", None),
        "nominal",
    )
    build14_summary = str(getattr(build14_signal, "summary", "")) if build14_signal is not None else ""
    build14_reason_codes = _build14_reason_codes(build14_signal)
    confidence_penalty_weight = 0.0
    recommended_budget_factor = 1.0
    build14_reason_lines: tuple[str, ...] = ()

    hard_blocking_reasons.extend(build14_validation_reasons)

    if build14_signal is not None and not live_light_input.build14_live_eligible:
        hard_blocking_reasons.append(
            "Build-14 live influence requires explicit post-Shadow live eligibility"
        )

    if live_light_input.micro_live_run_state != MicroLiveRunState.READY_TO_PROBE:
        hard_blocking_reasons.append(
            "Build-12 Micro-live run must be ready_to_probe before Live-Light"
        )
    if live_light_input.micro_live_verdict == MicroLiveVerdict.BLOCKED:
        hard_blocking_reasons.append(
            "Build-12 Micro-live is blocked and cannot open Live-Light"
        )
    elif live_light_input.micro_live_verdict == MicroLiveVerdict.DRY_RUN_ONLY:
        micro_live_needs_review = True

    if live_light_input.micro_live_blocking_reasons:
        hard_blocking_reasons.extend(
            f"micro-live gate: {reason}"
            for reason in live_light_input.micro_live_blocking_reasons
        )

    if normalized_import_status != "accepted":
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires an accepted import_validation_status"
        )
    if live_light_input.import_rejection_reasons:
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires empty import_rejection_reasons"
        )
    if (
        live_light_input.micro_live_import_artifact_id
        != live_light_input.import_artifact_id
    ):
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires matching Micro-live/import artifact_id"
        )
    if (
        live_light_input.micro_live_import_lineage_version
        != live_light_input.import_lineage_version
    ):
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires matching Micro-live/import lineage_version"
        )

    if not live_light_input.onboarding_accepted:
        hard_blocking_reasons.append(
            "strategy onboarding must be accepted before Live-Light"
        )
    elif live_light_input.onboarding_review_state not in {
        ReviewState.PENDING,
        ReviewState.APPROVED,
    }:
        hard_blocking_reasons.append(
            "accepted onboarding must keep a pending or approved review_state"
        )
    if live_light_input.onboarding_reasons and live_light_input.onboarding_accepted:
        hard_blocking_reasons.append(
            "accepted onboarding must not carry rejection reasons"
        )
    if live_light_input.onboarding_review_state in {
        ReviewState.NEEDS_REVISION,
        ReviewState.REJECTED,
    }:
        hard_blocking_reasons.append(
            f"onboarding review_state={live_light_input.onboarding_review_state.value} is not eligible for Live-Light"
        )
    hard_blocking_reasons.extend(
        f"onboarding gate: {reason}" for reason in live_light_input.onboarding_reasons
    )

    if not live_light_input.review_export_ready:
        hard_blocking_reasons.append(
            "Build-11/9X review export must be ready before Live-Light execution"
        )
    if not live_light_input.observability_ready:
        hard_blocking_reasons.append(
            "Build-10 observability must be ready before Live-Light execution"
        )
    if not live_light_input.halt_ready:
        hard_blocking_reasons.append(
            "operator halt guard must be ready before Live-Light execution"
        )
    if live_light_input.operator_safing_request is not None:
        hard_blocking_reasons.append(
            _format_operator_safing_reason(live_light_input.operator_safing_request)
        )
    if not live_light_input.execution_ready:
        hard_blocking_reasons.append(
            "execution readiness must be confirmed before Live-Light execution"
        )
    if not live_light_input.broker_ready:
        hard_blocking_reasons.append(
            "broker readiness must be confirmed before Live-Light execution"
        )
    if not live_light_input.exchange_ready:
        hard_blocking_reasons.append(
            "exchange readiness must be confirmed before Live-Light execution"
        )

    if build14_signal is not None:
        hard_blocking_reasons.extend(_build14_guardrail_reasons(build14_signal))
        build14_reason_lines = tuple(
            f"build14 gate: {reason}" for reason in build14_reason_codes
        )
        if build14_action == "downgrade_confidence":
            confidence_penalty_weight = float(
                getattr(build14_signal, "confidence_penalty_weight", 0.0)
            )
            recommended_budget_factor = float(
                getattr(build14_signal, "recommended_budget_factor", 1.0)
            )
        elif build14_action in {"review_only", "soft_veto"}:
            build14_requires_review = True
            confidence_penalty_weight = float(
                getattr(build14_signal, "confidence_penalty_weight", 0.0)
            )
            recommended_budget_factor = float(
                getattr(build14_signal, "recommended_budget_factor", 1.0)
            )

    if hard_blocking_reasons:
        combined_reasons = tuple(hard_blocking_reasons) + build14_reason_lines
        decision = LiveLightDecision(
            allowed_to_execute_small=False,
            verdict=LiveLightVerdict.BLOCKED,
            normalized_promotion_state=PromotionState.MICRO_LIVE_CANDIDATE,
            review_state=ReviewState.NEEDS_REVISION,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            blocking_reasons=combined_reasons,
            manual_review_required=True,
        )
        execution_intent = LiveLightExecutionIntent(
            intent_id=run_id or f"{live_light_input.correlation_id}:live_light_intent",
            import_artifact_id=live_light_input.import_artifact_id,
            import_lineage_version=live_light_input.import_lineage_version,
            planned_engines=(),
            planned_pairs=(),
            requested_total_notional_usdt=live_light_input.requested_total_notional_usdt,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            execution_order_limit=0,
            dry_run_only=False,
            halt_guard_required=True,
            broker_ready_required=True,
            exchange_ready_required=True,
        )
        run_state = LiveLightRunState.BLOCKED
    elif micro_live_needs_review or build14_requires_review:
        review_reasons = []
        if micro_live_needs_review:
            review_reasons.append(
                "Build-12 Micro-live verdict must be allowed_to_probe before Live-Light can execute small size"
            )
        if build14_signal is not None and build14_requires_review:
            review_reasons.append(build14_summary)
            review_reasons.extend(build14_reason_lines)
        decision = LiveLightDecision(
            allowed_to_execute_small=False,
            verdict=LiveLightVerdict.DRY_RUN_ONLY,
            normalized_promotion_state=PromotionState.MICRO_LIVE_CANDIDATE,
            review_state=ReviewState.NEEDS_REVISION,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            blocking_reasons=tuple(review_reasons),
            manual_review_required=True,
        )
        execution_intent = LiveLightExecutionIntent(
            intent_id=run_id or f"{live_light_input.correlation_id}:live_light_intent",
            import_artifact_id=live_light_input.import_artifact_id,
            import_lineage_version=live_light_input.import_lineage_version,
            planned_engines=live_light_input.active_engines,
            planned_pairs=live_light_input.live_pairs,
            requested_total_notional_usdt=live_light_input.requested_total_notional_usdt,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            execution_order_limit=live_light_input.execution_order_limit,
            dry_run_only=True,
            halt_guard_required=True,
            broker_ready_required=True,
            exchange_ready_required=True,
        )
        run_state = LiveLightRunState.PREPARED
    else:
        approved_total = round(
            live_light_input.requested_total_notional_usdt * recommended_budget_factor,
            8,
        )
        approved_pair = round(
            live_light_input.requested_pair_notional_usdt * recommended_budget_factor,
            8,
        )
        decision = LiveLightDecision(
            allowed_to_execute_small=True,
            verdict=LiveLightVerdict.ALLOWED_TO_EXECUTE_SMALL,
            normalized_promotion_state=PromotionState.LIVE_CANDIDATE,
            review_state=ReviewState.PENDING,
            approved_total_notional_usdt=approved_total,
            approved_pair_notional_usdt=approved_pair,
            blocking_reasons=(),
            manual_review_required=False,
        )
        execution_intent = LiveLightExecutionIntent(
            intent_id=run_id or f"{live_light_input.correlation_id}:live_light_intent",
            import_artifact_id=live_light_input.import_artifact_id,
            import_lineage_version=live_light_input.import_lineage_version,
            planned_engines=live_light_input.active_engines,
            planned_pairs=live_light_input.live_pairs,
            requested_total_notional_usdt=live_light_input.requested_total_notional_usdt,
            approved_total_notional_usdt=approved_total,
            approved_pair_notional_usdt=approved_pair,
            execution_order_limit=live_light_input.execution_order_limit,
            dry_run_only=False,
            halt_guard_required=True,
            broker_ready_required=True,
            exchange_ready_required=True,
        )
        run_state = LiveLightRunState.READY_TO_EXECUTE_SMALL

    return LiveLightRunSummary(
        run_id=run_id or f"{live_light_input.correlation_id}:live_light_run",
        correlation_id=live_light_input.correlation_id,
        run_state=run_state,
        micro_live_run_id=live_light_input.micro_live_run_id,
        shadow_run_id=live_light_input.shadow_run_id,
        micro_live_verdict=live_light_input.micro_live_verdict,
        decision=decision,
        execution_intent=execution_intent,
        import_artifact_id=live_light_input.import_artifact_id,
        import_lineage_version=live_light_input.import_lineage_version,
        observability_ready=live_light_input.observability_ready,
        halt_ready=live_light_input.halt_ready,
        operator_safing_request=live_light_input.operator_safing_request,
        execution_ready=live_light_input.execution_ready,
        broker_ready=live_light_input.broker_ready,
        exchange_ready=live_light_input.exchange_ready,
        onboarding_ready=live_light_input.onboarding_accepted,
        build14_influence_mode=build14_influence_mode,
        build14_action=build14_action,
        build14_severity=build14_severity,
        build14_summary=build14_summary,
        build14_reason_codes=build14_reason_codes,
        build14_confidence_penalty_weight=confidence_penalty_weight,
        build14_recommended_budget_factor=recommended_budget_factor,
        build14_live_eligible=live_light_input.build14_live_eligible,
    )


__all__ = [
    "build_live_light_input_from_micro_live",
    "run_live_light_gate",
]
