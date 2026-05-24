"""Machine-readable grounding registry for Strategy Ladder ML feature inputs."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json


FEATURE_GROUNDING_REGISTRY_VERSION = "v1"
FEATURE_GROUNDING_REGISTRY_FILENAME = "feature_grounding_registry.json"
FEATURE_GROUNDING_CONTRACT_REPORT_FILENAME = "feature_grounding_contract_report.json"


class FeatureGroundingClass(StrEnum):
    KLINE_GROUNDED = "KLINE_GROUNDED"
    TRADE_GROUNDED = "TRADE_GROUNDED"
    ORDERBOOK_GROUNDED = "ORDERBOOK_GROUNDED"
    MICROSTRUCTURE_A2_GROUNDED = "MICROSTRUCTURE_A2_GROUNDED"
    ENGINE_REPLAY_GROUNDED = "ENGINE_REPLAY_GROUNDED"
    EXECUTION_REPLAY_GROUNDED = "EXECUTION_REPLAY_GROUNDED"
    LABEL_REPLAY_GROUNDED = "LABEL_REPLAY_GROUNDED"
    STATIC_VENUE_MODEL = "STATIC_VENUE_MODEL"


class FeatureGroundingStatus(StrEnum):
    FEATURE_GROUNDING_OK = "FEATURE_GROUNDING_OK"
    FEATURE_REQUIRES_B2 = "FEATURE_REQUIRES_B2"
    FEATURE_REQUIRES_A2_ORDERBOOK = "FEATURE_REQUIRES_A2_ORDERBOOK"
    FEATURE_REQUIRES_TRADES = "FEATURE_REQUIRES_TRADES"
    FEATURE_LABEL_NOT_ALLOWED_AS_RUNTIME_INPUT = (
        "FEATURE_LABEL_NOT_ALLOWED_AS_RUNTIME_INPUT"
    )
    FEATURE_GROUNDING_UNKNOWN_BLOCKED = "FEATURE_GROUNDING_UNKNOWN_BLOCKED"


class FeatureGroundingEntry(BaseModel, frozen=True):
    schema_version: str = "feature_grounding.entry.v1"
    feature_name: str = Field(..., min_length=1)
    family: str = Field(..., min_length=1)
    grounding: FeatureGroundingClass
    available_at_decision_time: bool
    allowed_as_training_input: bool
    allowed_as_runtime_input: bool
    requires_b2: bool = False
    requires_a2_orderbook: bool = False
    requires_trade_window: bool = False
    requires_post_window: bool = False
    is_label_or_outcome: bool = False
    notes: str = ""


class FeatureGroundingReportRow(BaseModel, frozen=True):
    feature_name: str
    selected: bool = True
    family: str = ""
    grounding: str = ""
    available_at_decision_time: bool = False
    allowed_as_training_input: bool = False
    allowed_as_runtime_input: bool = False
    requires_b2: bool = False
    requires_a2_orderbook: bool = False
    requires_trade_window: bool = False
    requires_post_window: bool = False
    is_label_or_outcome: bool = False
    status: str = FeatureGroundingStatus.FEATURE_GROUNDING_OK.value
    blocker_reason: str = ""
    notes: str = ""


class FeatureGroundingContractReport(BaseModel, frozen=True):
    schema_version: str = "feature_grounding.contract_report.v1"
    registry_version: str = FEATURE_GROUNDING_REGISTRY_VERSION
    generated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    status: str = "FEATURE_GROUNDING_CONTRACT_OK"
    selected_feature_count: int = 0
    b2_run_root_present: bool = False
    a2_orderbook_available: bool = False
    trade_window_available: bool = False
    execution_replay_available: bool = False
    rows: tuple[FeatureGroundingReportRow, ...] = ()
    blocker_reasons: tuple[str, ...] = ()


def _entry(
    feature_name: str,
    *,
    family: str,
    grounding: FeatureGroundingClass,
    available_at_decision_time: bool,
    allowed_as_training_input: bool = True,
    allowed_as_runtime_input: bool = True,
    requires_b2: bool = False,
    requires_a2_orderbook: bool = False,
    requires_trade_window: bool = False,
    requires_post_window: bool = False,
    is_label_or_outcome: bool = False,
    notes: str = "",
) -> FeatureGroundingEntry:
    return FeatureGroundingEntry(
        feature_name=feature_name,
        family=family,
        grounding=grounding,
        available_at_decision_time=available_at_decision_time,
        allowed_as_training_input=allowed_as_training_input,
        allowed_as_runtime_input=allowed_as_runtime_input,
        requires_b2=requires_b2,
        requires_a2_orderbook=requires_a2_orderbook,
        requires_trade_window=requires_trade_window,
        requires_post_window=requires_post_window,
        is_label_or_outcome=is_label_or_outcome,
        notes=notes,
    )


def _label(feature_name: str, notes: str) -> FeatureGroundingEntry:
    return _entry(
        feature_name,
        family="label_or_outcome",
        grounding=FeatureGroundingClass.LABEL_REPLAY_GROUNDED,
        available_at_decision_time=False,
        allowed_as_training_input=False,
        allowed_as_runtime_input=False,
        requires_b2=True,
        requires_post_window=True,
        is_label_or_outcome=True,
        notes=notes,
    )


_INITIAL_ENTRIES: tuple[FeatureGroundingEntry, ...] = (
    _entry(
        "close_return",
        family="legacy_kline",
        grounding=FeatureGroundingClass.KLINE_GROUNDED,
        available_at_decision_time=True,
        notes="Computed from current/past OHLCV without future labels.",
    ),
    _entry(
        "high_low_range",
        family="legacy_kline",
        grounding=FeatureGroundingClass.KLINE_GROUNDED,
        available_at_decision_time=True,
        notes="Computed from current OHLCV bar range.",
    ),
    _entry(
        "volume",
        family="legacy_kline",
        grounding=FeatureGroundingClass.KLINE_GROUNDED,
        available_at_decision_time=True,
        notes="Current/past OHLCV volume.",
    ),
    _entry(
        "spread_bps",
        family="microstructure",
        grounding=FeatureGroundingClass.ORDERBOOK_GROUNDED,
        available_at_decision_time=True,
        requires_a2_orderbook=True,
        notes="Ex-ante top-of-book spread if sourced at or before decision timestamp.",
    ),
    _entry(
        "book_depth_levels",
        family="microstructure",
        grounding=FeatureGroundingClass.ORDERBOOK_GROUNDED,
        available_at_decision_time=True,
        requires_a2_orderbook=True,
        notes="Order book depth level count at or before decision timestamp.",
    ),
    _entry(
        "queue_pressure",
        family="microstructure",
        grounding=FeatureGroundingClass.ORDERBOOK_GROUNDED,
        available_at_decision_time=True,
        requires_a2_orderbook=True,
        notes="Ex-ante queue pressure from the order book.",
    ),
    _entry(
        "cumulative_ofi",
        family="microstructure",
        grounding=FeatureGroundingClass.MICROSTRUCTURE_A2_GROUNDED,
        available_at_decision_time=True,
        requires_a2_orderbook=True,
        notes="Order-flow imbalance over a causal pre-decision window.",
    ),
    _entry(
        "vpin",
        family="microstructure",
        grounding=FeatureGroundingClass.MICROSTRUCTURE_A2_GROUNDED,
        available_at_decision_time=True,
        requires_trade_window=True,
        notes="VPIN over a causal pre-decision trade window.",
    ),
    _entry(
        "kyle_lambda",
        family="microstructure",
        grounding=FeatureGroundingClass.TRADE_GROUNDED,
        available_at_decision_time=True,
        requires_trade_window=True,
        notes="Kyle lambda is allowed only when estimated from past trades.",
    ),
    _entry(
        "realized_vol_current",
        family="microstructure",
        grounding=FeatureGroundingClass.KLINE_GROUNDED,
        available_at_decision_time=True,
        notes="Allowed only when computed from historical bars/trades up to decision time.",
    ),
    _entry(
        "slippage_bps",
        family="execution_cost",
        grounding=FeatureGroundingClass.EXECUTION_REPLAY_GROUNDED,
        available_at_decision_time=True,
        requires_b2=True,
        notes="Allowed as input only if simulated causally at entry timestamp.",
    ),
    _entry(
        "break_even_bps",
        family="execution_cost",
        grounding=FeatureGroundingClass.EXECUTION_REPLAY_GROUNDED,
        available_at_decision_time=True,
        requires_b2=True,
        notes="Cost/edge feasibility scalar from replay or governed execution model.",
    ),
    _entry(
        "latency_penalty_bps",
        family="execution_cost",
        grounding=FeatureGroundingClass.EXECUTION_REPLAY_GROUNDED,
        available_at_decision_time=True,
        requires_b2=True,
        notes="Replay-grounded unless a static venue model is explicitly declared.",
    ),
    _entry(
        "fill_ratio",
        family="execution_cost",
        grounding=FeatureGroundingClass.EXECUTION_REPLAY_GROUNDED,
        available_at_decision_time=True,
        requires_b2=True,
        notes="Requires execution replay or a causal fill model.",
    ),
    _entry(
        "depth_fill_ratio",
        family="execution_cost",
        grounding=FeatureGroundingClass.EXECUTION_REPLAY_GROUNDED,
        available_at_decision_time=True,
        requires_b2=True,
        notes="Requires depth-walk replay or a causal fill model.",
    ),
    _entry(
        "fragility_score",
        family="build14_observed",
        grounding=FeatureGroundingClass.ENGINE_REPLAY_GROUNDED,
        available_at_decision_time=True,
        requires_b2=True,
        notes="Build-14 observed/enabler scalar carried through replay context.",
    ),
    _entry(
        "false_breakout_context",
        family="engine_context",
        grounding=FeatureGroundingClass.ENGINE_REPLAY_GROUNDED,
        available_at_decision_time=True,
        requires_b2=True,
        notes="Engine context scalar allowed only at decision timestamp.",
    ),
    _entry(
        "realized_vol_at_break",
        family="engine_context",
        grounding=FeatureGroundingClass.ENGINE_REPLAY_GROUNDED,
        available_at_decision_time=True,
        requires_b2=True,
        notes="Breakout-time volatility snapshot, not a future outcome.",
    ),
    _entry(
        "micro_edge_exit_governor_observed",
        family="build14_observed",
        grounding=FeatureGroundingClass.ENGINE_REPLAY_GROUNDED,
        available_at_decision_time=True,
        requires_b2=True,
        notes="Build-14 observed exit-governor scalar.",
    ),
    _entry(
        "micro_edge_entry_timing_observed",
        family="build14_observed",
        grounding=FeatureGroundingClass.ENGINE_REPLAY_GROUNDED,
        available_at_decision_time=True,
        requires_b2=True,
        notes="Build-14 observed entry-timing scalar.",
    ),
    _entry(
        "history_score",
        family="engine_d_governance",
        grounding=FeatureGroundingClass.ENGINE_REPLAY_GROUNDED,
        available_at_decision_time=True,
        requires_b2=True,
        notes="Engine D context at the decision timestamp.",
    ),
    _entry(
        "marginal_value_score",
        family="engine_d_governance",
        grounding=FeatureGroundingClass.ENGINE_REPLAY_GROUNDED,
        available_at_decision_time=True,
        requires_b2=True,
        notes="Engine D marginal value context at the decision timestamp.",
    ),
    _entry(
        "reentry_lateness",
        family="engine_d_governance",
        grounding=FeatureGroundingClass.ENGINE_REPLAY_GROUNDED,
        available_at_decision_time=True,
        requires_b2=True,
        notes="Engine D re-entry timing context at the decision timestamp.",
    ),
    _entry(
        "concentration_headroom",
        family="engine_d_governance",
        grounding=FeatureGroundingClass.ENGINE_REPLAY_GROUNDED,
        available_at_decision_time=True,
        requires_b2=True,
        notes="Remaining concentration headroom before native hard gates.",
    ),
    _entry(
        "anti_revenge_state__active",
        family="engine_d_governance",
        grounding=FeatureGroundingClass.ENGINE_REPLAY_GROUNDED,
        available_at_decision_time=True,
        requires_b2=True,
        notes="One-hot engine governance state at decision time.",
    ),
    _entry(
        "anti_revenge_state__cooling",
        family="engine_d_governance",
        grounding=FeatureGroundingClass.ENGINE_REPLAY_GROUNDED,
        available_at_decision_time=True,
        requires_b2=True,
        notes="One-hot engine governance state at decision time.",
    ),
    _entry(
        "anti_revenge_state__idle",
        family="engine_d_governance",
        grounding=FeatureGroundingClass.ENGINE_REPLAY_GROUNDED,
        available_at_decision_time=True,
        requires_b2=True,
        notes="One-hot engine governance state at decision time.",
    ),
    _label("mfe_bps", "Maximum favorable excursion is a post-decision outcome."),
    _label("mae_bps", "Maximum adverse excursion is a post-decision outcome."),
    _label("realized_pnl", "Realized PnL is a post-decision outcome."),
    _label("realized_net_edge", "Realized net edge is a post-decision outcome."),
    _label("selected_count", "Selection count is an aggregate outcome, not a runtime input."),
    _label("executed_count", "Execution count is an aggregate outcome, not a runtime input."),
    _label("break_even_outcome", "Break-even success is a label/outcome."),
    _label(
        "post_window_adverse_selection",
        "Post-window adverse selection looks beyond decision time.",
    ),
    _label("future_return", "Future return is a label."),
    _label("label_forward_return", "Forward-return label cannot be a runtime input."),
    _label("label_forward_return_h1", "Forward-return label cannot be a runtime input."),
    _label("label_forward_return_h5", "Forward-return label cannot be a runtime input."),
    _label("label_forward_return_h10", "Forward-return label cannot be a runtime input."),
    _label("trade_success", "Trade success/failure is a post-decision outcome."),
    _label("executed_only_net_return", "Executed-only net return is a training label."),
    _label("expected_ce_net", "Expected CE net is a target/proxy label, not runtime input."),
)


FEATURE_GROUNDING_REGISTRY: dict[str, FeatureGroundingEntry] = {
    entry.feature_name: entry for entry in _INITIAL_ENTRIES
}
LABEL_OR_OUTCOME_FEATURE_NAMES = frozenset(
    name for name, entry in FEATURE_GROUNDING_REGISTRY.items() if entry.is_label_or_outcome
)


def get_feature_grounding_registry() -> dict[str, FeatureGroundingEntry]:
    return dict(FEATURE_GROUNDING_REGISTRY)


def feature_grounding_entry(feature_name: str) -> FeatureGroundingEntry | None:
    return FEATURE_GROUNDING_REGISTRY.get(feature_name.strip())


def _row_status(
    entry: FeatureGroundingEntry | None,
    *,
    b2_run_root_present: bool,
    a2_orderbook_available: bool,
    trade_window_available: bool,
    execution_replay_available: bool,
) -> tuple[FeatureGroundingStatus, str]:
    if entry is None:
        return (
            FeatureGroundingStatus.FEATURE_GROUNDING_UNKNOWN_BLOCKED,
            FeatureGroundingStatus.FEATURE_GROUNDING_UNKNOWN_BLOCKED.value,
        )
    if entry.is_label_or_outcome:
        return (
            FeatureGroundingStatus.FEATURE_LABEL_NOT_ALLOWED_AS_RUNTIME_INPUT,
            "ML_LABEL_FEATURE_AS_RUNTIME_INPUT_BLOCKED",
        )
    if entry.requires_b2 and not (b2_run_root_present or execution_replay_available):
        return (
            FeatureGroundingStatus.FEATURE_REQUIRES_B2,
            FeatureGroundingStatus.FEATURE_REQUIRES_B2.value,
        )
    if entry.requires_a2_orderbook and not (a2_orderbook_available or b2_run_root_present):
        return (
            FeatureGroundingStatus.FEATURE_REQUIRES_A2_ORDERBOOK,
            FeatureGroundingStatus.FEATURE_REQUIRES_A2_ORDERBOOK.value,
        )
    if entry.requires_trade_window and not (trade_window_available or b2_run_root_present):
        return (
            FeatureGroundingStatus.FEATURE_REQUIRES_TRADES,
            FeatureGroundingStatus.FEATURE_REQUIRES_TRADES.value,
        )
    return (FeatureGroundingStatus.FEATURE_GROUNDING_OK, "")


def build_feature_grounding_contract_report(
    selected_feature_names: tuple[str, ...],
    *,
    b2_run_root_present: bool = False,
    a2_orderbook_available: bool = False,
    trade_window_available: bool = False,
    execution_replay_available: bool = False,
) -> FeatureGroundingContractReport:
    rows: list[FeatureGroundingReportRow] = []
    blockers: list[str] = []
    for feature_name in tuple(dict.fromkeys(name.strip() for name in selected_feature_names if name.strip())):
        entry = feature_grounding_entry(feature_name)
        status, blocker = _row_status(
            entry,
            b2_run_root_present=b2_run_root_present,
            a2_orderbook_available=a2_orderbook_available,
            trade_window_available=trade_window_available,
            execution_replay_available=execution_replay_available,
        )
        if blocker:
            blockers.append(f"{feature_name}:{blocker}")
        rows.append(
            FeatureGroundingReportRow(
                feature_name=feature_name,
                family="" if entry is None else entry.family,
                grounding="" if entry is None else entry.grounding.value,
                available_at_decision_time=(
                    False if entry is None else entry.available_at_decision_time
                ),
                allowed_as_training_input=(
                    False if entry is None else entry.allowed_as_training_input
                ),
                allowed_as_runtime_input=(
                    False if entry is None else entry.allowed_as_runtime_input
                ),
                requires_b2=False if entry is None else entry.requires_b2,
                requires_a2_orderbook=(
                    False if entry is None else entry.requires_a2_orderbook
                ),
                requires_trade_window=(
                    False if entry is None else entry.requires_trade_window
                ),
                requires_post_window=(
                    False if entry is None else entry.requires_post_window
                ),
                is_label_or_outcome=(
                    False if entry is None else entry.is_label_or_outcome
                ),
                status=status.value,
                blocker_reason=blocker,
                notes="" if entry is None else entry.notes,
            )
        )
    return FeatureGroundingContractReport(
        status=(
            "FEATURE_GROUNDING_CONTRACT_BLOCKED"
            if blockers
            else "FEATURE_GROUNDING_CONTRACT_OK"
        ),
        selected_feature_count=len(rows),
        b2_run_root_present=b2_run_root_present,
        a2_orderbook_available=a2_orderbook_available,
        trade_window_available=trade_window_available,
        execution_replay_available=execution_replay_available,
        rows=tuple(rows),
        blocker_reasons=tuple(dict.fromkeys(blockers)),
    )


def write_feature_grounding_registry(path: Path) -> Path:
    payload = {
        "schema_version": "feature_grounding.registry.v1",
        "registry_version": FEATURE_GROUNDING_REGISTRY_VERSION,
        "features": [
            entry.model_dump(mode="json")
            for entry in sorted(
                FEATURE_GROUNDING_REGISTRY.values(),
                key=lambda item: item.feature_name,
            )
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, payload, indent=2)
    return path


def write_feature_grounding_contract_report(
    path: Path,
    report: FeatureGroundingContractReport,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, report.model_dump(mode="json"), indent=2)
    return path


__all__ = [
    "FEATURE_GROUNDING_CONTRACT_REPORT_FILENAME",
    "FEATURE_GROUNDING_REGISTRY_FILENAME",
    "FEATURE_GROUNDING_REGISTRY_VERSION",
    "FeatureGroundingClass",
    "FeatureGroundingContractReport",
    "FeatureGroundingEntry",
    "FeatureGroundingReportRow",
    "FeatureGroundingStatus",
    "LABEL_OR_OUTCOME_FEATURE_NAMES",
    "build_feature_grounding_contract_report",
    "feature_grounding_entry",
    "get_feature_grounding_registry",
    "write_feature_grounding_contract_report",
    "write_feature_grounding_registry",
]
