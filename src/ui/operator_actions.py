"""Governed operator actions for the locked Build-10 Light UI."""

from __future__ import annotations

from interface_contracts import ProfileId
from ui.contracts import (
    OperatorActionLogEntry,
    OperatorActionOutcome,
    OperatorActionRequest,
    OperatorActionType,
    OperatorEventType,
)


_LIGHT_ALLOWED_ACTIONS = (
    OperatorActionType.VIEW_CRITICAL_SCREENS,
    OperatorActionType.SUSPEND_PAIR,
    OperatorActionType.REQUEST_PAIR_RESUME,
    OperatorActionType.SUSPEND_ENGINE,
    OperatorActionType.SET_HALTED,
    OperatorActionType.VIEW_ALERT_HISTORY,
    OperatorActionType.ACKNOWLEDGE_CRITICAL_ALERT,
)

_LIGHT_SUSPENDABLE_ENGINES = frozenset({"engine_a", "engine_b"})


def build_light_allowed_actions() -> tuple[OperatorActionType, ...]:
    """Return the governed action surface exposed by the Light UI."""

    return _LIGHT_ALLOWED_ACTIONS


def record_screen_open(
    *,
    correlation_id: str,
    timestamp_ms: int,
    screen_id: str,
) -> OperatorActionLogEntry:
    """Record a screen-open event for the operator audit trail."""

    return OperatorActionLogEntry(
        timestamp_ms=timestamp_ms,
        correlation_id=correlation_id,
        event_type=OperatorEventType.SCREEN_OPENED,
        action=OperatorActionType.VIEW_CRITICAL_SCREENS,
        target=screen_id,
        accepted=True,
        message=f"screen opened: {screen_id}",
    )


def evaluate_light_operator_action(
    request: OperatorActionRequest,
    *,
    allowed_pairs: tuple[str, ...] = (),
    resumable_pairs: tuple[str, ...] = (),
    critical_alert_ids: tuple[str, ...] = (),
    max_light_pairs: int = 6,
) -> OperatorActionOutcome:
    """Accept or reject a Light operator action without touching runtime state."""

    requested_entry = OperatorActionLogEntry(
        timestamp_ms=request.timestamp_ms,
        correlation_id=request.correlation_id,
        event_type=OperatorEventType.ACTION_REQUESTED,
        action=request.action,
        target=request.target,
        accepted=False,
        message=f"operator action requested: {request.action.value}",
    )

    rejection_reason = _rejection_reason(
        request,
        allowed_pairs=allowed_pairs,
        resumable_pairs=resumable_pairs,
        critical_alert_ids=critical_alert_ids,
        max_light_pairs=max_light_pairs,
    )
    if rejection_reason:
        return OperatorActionOutcome(
            accepted=False,
            rejection_reason=rejection_reason,
            resulting_state="rejected",
            log_entries=(
                requested_entry,
                OperatorActionLogEntry(
                    timestamp_ms=request.timestamp_ms,
                    correlation_id=request.correlation_id,
                    event_type=OperatorEventType.ACTION_REJECTED,
                    action=request.action,
                    target=request.target,
                    accepted=False,
                    message=f"operator action rejected: {request.action.value}",
                    rejection_reason=rejection_reason,
                ),
            ),
        )

    result_event = OperatorEventType.ACTION_ACCEPTED
    result_message = f"operator action accepted: {request.action.value}"
    resulting_state = request.action.value
    if request.action == OperatorActionType.ACKNOWLEDGE_CRITICAL_ALERT:
        result_event = OperatorEventType.CRITICAL_ALERT_ACKNOWLEDGED
        result_message = "critical alert acknowledged"
        resulting_state = "critical_alert_acknowledged"
    elif request.action == OperatorActionType.SET_HALTED:
        resulting_state = "halted"
    elif request.action == OperatorActionType.SUSPEND_PAIR:
        resulting_state = "pair_suspended"
    elif request.action == OperatorActionType.REQUEST_PAIR_RESUME:
        resulting_state = "pair_resume_requested"
    elif request.action == OperatorActionType.SUSPEND_ENGINE:
        resulting_state = "engine_suspended"
    elif request.action == OperatorActionType.VIEW_ALERT_HISTORY:
        resulting_state = "alert_history_opened"
    elif request.action == OperatorActionType.VIEW_CRITICAL_SCREENS:
        resulting_state = "critical_screens_opened"

    return OperatorActionOutcome(
        accepted=True,
        resulting_state=resulting_state,
        log_entries=(
            requested_entry,
            OperatorActionLogEntry(
                timestamp_ms=request.timestamp_ms,
                correlation_id=request.correlation_id,
                event_type=result_event,
                action=request.action,
                target=request.target,
                accepted=True,
                message=result_message,
            ),
        ),
    )


def _rejection_reason(
    request: OperatorActionRequest,
    *,
    allowed_pairs: tuple[str, ...],
    resumable_pairs: tuple[str, ...],
    critical_alert_ids: tuple[str, ...],
    max_light_pairs: int,
) -> str:
    if request.profile != ProfileId.LIGHT:
        return "only profile=LIGHT is supported by the locked Light UI"
    if request.action not in _LIGHT_ALLOWED_ACTIONS:
        return _forbidden_reason(request, max_light_pairs=max_light_pairs)
    if request.action == OperatorActionType.SUSPEND_PAIR:
        if not request.target:
            return "suspend_pair requires a pair target"
        if allowed_pairs and request.target not in set(allowed_pairs):
            return "pair is outside the governed Light surface"
        return ""
    if request.action == OperatorActionType.REQUEST_PAIR_RESUME:
        if not request.target:
            return "request_pair_resume requires a pair target"
        if request.target not in set(resumable_pairs):
            return "pair resume requires conditions_lifted evidence"
        return ""
    if request.action == OperatorActionType.SUSPEND_ENGINE:
        if request.target not in _LIGHT_SUSPENDABLE_ENGINES:
            return "Light UI can only suspend engines A or B"
        return ""
    if request.action == OperatorActionType.ACKNOWLEDGE_CRITICAL_ALERT:
        if not request.target:
            return "acknowledge_critical_alert requires a critical alert id"
        if critical_alert_ids and request.target not in set(critical_alert_ids):
            return "critical alert id is not currently visible in the Light UI"
        return ""
    if request.action == OperatorActionType.VIEW_CRITICAL_SCREENS:
        return ""
    if request.action == OperatorActionType.SET_HALTED:
        return ""
    if request.action == OperatorActionType.VIEW_ALERT_HISTORY:
        return ""
    return "unsupported Light operator action"


def _forbidden_reason(
    request: OperatorActionRequest,
    *,
    max_light_pairs: int,
) -> str:
    if request.action == OperatorActionType.LOAD_COMPLETE:
        return "loading Complete is forbidden from the Light UI"
    if request.action == OperatorActionType.ACTIVATE_ENGINE:
        if request.target in {"engine_c", "engine_d"}:
            return "activating engines C/D is forbidden in Light"
        return "engine activation is not exposed by the locked Light UI"
    if request.action == OperatorActionType.ACTIVATE_PAIRS:
        if request.requested_pair_count > max_light_pairs:
            return f"activating more than {max_light_pairs} pairs is forbidden in Light"
        return "pair activation is not exposed by the locked Light UI"
    if request.action == OperatorActionType.MODIFY_RISK_CAPS:
        return "risk cap changes are forbidden in the locked Light UI"
    if request.action == OperatorActionType.BYPASS_HARD_BLOCKER:
        return "hard blocker bypass is forbidden in the locked Light UI"
    if request.action == OperatorActionType.INJECT_CONFIG:
        return "unversioned config injection is forbidden in the locked Light UI"
    return "action is outside the governed Light UI surface"


__all__ = [
    "build_light_allowed_actions",
    "record_screen_open",
    "evaluate_light_operator_action",
]
