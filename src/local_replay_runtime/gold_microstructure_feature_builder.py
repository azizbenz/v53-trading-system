"""Gold microstructure feature manifests for the canonical Strategy Ladder rail."""

from __future__ import annotations

from pathlib import Path

from data_backbone.microstructure.feature_registry import get_feature_registry
from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.raw_data_processing_contracts import (
    GoldMicrostructureFeatureManifest,
    finalize_hashed_model,
)
from local_replay_runtime.strategy_ladder_feature_store import (
    load_strategy_ladder_feature_store,
    parse_time_boundary_to_ms,
)
from local_replay_runtime.strategy_ladder_models import deterministic_payload_hash


DECLARED_FEATURE_GROUPS = (
    "price_return_features",
    "book_liquidity_features",
    "flow_microstructure_features",
    "fragility_false_breakout_features",
    "cost_context_features",
)

QUANT_EQUATION_REFS = (
    "close_return_1m=(close_t-close_{t-1})/close_{t-1}",
    "close_return_5m=(close_t-close_{t-5m})/close_{t-5m}",
    "high_low_range=(high_t-low_t)/open_t",
    "spread_bps=10000*(best_ask-best_bid)/((best_ask+best_bid)/2)",
    "orderbook_imbalance_topk=(sum_bid_depth_k-sum_ask_depth_k)/(sum_bid_depth_k+sum_ask_depth_k)",
    "OFI=sum(event_signed_size)",
    "CVD=sum(aggressive_buy_volume-aggressive_sell_volume)",
    "VPIN=abs(buy_volume-sell_volume)/bucket_volume",
    "queue_pressure=(bid_depth_topk-ask_depth_topk)/(bid_depth_topk+ask_depth_topk)",
    "sweep_score_v1=0.45*capratio(wick_ratio,3)+0.35*capratio(vol_burst,3)+0.20*clip01(reject_indicator)",
    "fragility_score_v1=clip01(0.70*base_fragility+0.20*spread_regime_penalty+0.10*book_resiliency_penalty)",
    "break_even_bps=spread_bps+slippage_bps+fees_bps",
)


def _boundary_ms(raw_value: str, *, end_of_day: bool) -> int | None:
    value = str(raw_value or "").strip()
    if not value:
        return None
    parsed = parse_time_boundary_to_ms(value)
    if parsed is None:
        return None
    if end_of_day and len(value) == 10 and "T" not in value and " " not in value:
        return parsed + 86_399_999
    return parsed


def _feature_groups_for_row(row) -> set[str]:  # noqa: ANN001
    groups: set[str] = set()
    feature_keys = set(row.feature_values)
    if {"close_return", "high_low_range"} & feature_keys:
        groups.add("price_return_features")
    if row.spread_bps > 0.0 or row.book_depth_levels is not None or row.book_depth_source_status != "BOOK_DEPTH_NOT_PROVEN":
        groups.add("book_liquidity_features")
    if row.trade_feature_status == "TRADE_FEATURE_STATUS_READY":
        groups.add("flow_microstructure_features")
    if any(
        key in feature_keys
        for key in (
            "false_breakout_context",
            "fragility",
            "fragility_score",
            "sweep_score",
            "break_even_bps",
            "session_tags",
        )
    ):
        groups.add("fragility_false_breakout_features")
    if any(
        value > 0.0
        for value in (
            row.spread_bps,
            row.slippage_bps,
            row.latency_penalty_bps,
        )
    ):
        groups.add("cost_context_features")
    return groups


def _feature_names(rows) -> tuple[str, ...]:  # noqa: ANN001
    names: set[str] = set()
    for row in rows:
        names.update(str(key) for key in row.feature_values)
        if row.spread_bps is not None:
            names.add("spread_bps")
        if row.slippage_bps is not None:
            names.add("slippage_bps")
        if row.latency_penalty_bps is not None:
            names.add("latency_penalty_bps")
        if row.book_depth_levels is not None:
            names.add("book_depth_levels")
    return tuple(sorted(names))


def _feature_hash(rows) -> str:  # noqa: ANN001
    payload = tuple(
        {
            "timestamp_ms": row.resolved_timestamp_ms,
            "pair": row.pair,
            "timeframe": row.timeframe,
            "feature_values": row.feature_values,
            "source_ref": row.source_ref,
            "available_at_timestamp_ms": row.available_at_timestamp_ms,
            "spread_bps": row.spread_bps,
            "slippage_bps": row.slippage_bps,
            "book_depth_levels": row.book_depth_levels,
            "trade_feature_status": row.trade_feature_status,
            "kline_feature_status": row.kline_feature_status,
            "orderbook_feature_status": row.orderbook_feature_status,
        }
        for row in rows
    )
    return deterministic_payload_hash(payload)


def build_gold_microstructure_feature_manifest(
    *,
    gold_root: Path,
    pairs: tuple[str, ...] = (),
    timeframes: tuple[str, ...] = (),
    start: str = "",
    end: str = "",
) -> GoldMicrostructureFeatureManifest:
    """Build one typed gold feature manifest from the existing feature store."""

    result = load_strategy_ladder_feature_store(
        gold_root,
        pairs=pairs,
        timeframes=timeframes,
        start_ms=_boundary_ms(start, end_of_day=False),
        end_ms=_boundary_ms(end, end_of_day=True),
    )
    rows = result.rows
    generated_groups: set[str] = set()
    for row in rows:
        generated_groups.update(_feature_groups_for_row(row))
    feature_names = _feature_names(rows)
    feature_hash = _feature_hash(rows) if rows else None
    timestamp_policy = "FEATURE_TIMESTAMP_POLICY_NOT_PROVEN"
    if rows and all(
        row.available_at_timestamp_ms is None
        or row.available_at_timestamp_ms <= row.resolved_timestamp_ms
        for row in rows
    ):
        timestamp_policy = "FEATURE_TIMESTAMP_LEQ_DECISION_TIMESTAMP_ENFORCED"
    status = "GOLD_FEATURE_STORE_NOT_READY"
    blockers = list(result.blocker_codes)
    if rows:
        status = (
            "GOLD_FEATURE_STORE_READY"
            if set(DECLARED_FEATURE_GROUPS) <= generated_groups
            else "GOLD_FEATURE_STORE_PARTIAL"
        )
    elif result.feature_store_status == "FEATURE_STORE_MISSING":
        blockers.append("GOLD_FEATURE_STORE_MISSING")
    feature_registry = get_feature_registry()
    modules_used = [
        "local_replay_runtime.strategy_ladder_data_factory",
        "local_replay_runtime.strategy_ladder_feature_store",
        "data_backbone.microstructure.feature_registry",
    ]
    if "flow_microstructure_features" in generated_groups:
        modules_used.extend(
            [
                "data_backbone.microstructure.order_flow_imbalance",
                "data_backbone.microstructure.vpin",
                "data_backbone.microstructure.queue_pressure",
            ]
        )
    return finalize_hashed_model(
        GoldMicrostructureFeatureManifest(
            symbol_scope=tuple(sorted({row.pair for row in rows})) or pairs,
            timeframe_scope=tuple(sorted({row.timeframe for row in rows})) or timeframes,
            feature_row_count=len(rows),
            feature_groups_declared=DECLARED_FEATURE_GROUPS,
            feature_groups_generated=tuple(sorted(generated_groups)),
            feature_groups_missing=tuple(
                group for group in DECLARED_FEATURE_GROUPS if group not in generated_groups
            ),
            feature_timestamp_policy=timestamp_policy,
            max_feature_timestamp_ms=max((row.resolved_timestamp_ms for row in rows), default=None),
            min_feature_timestamp_ms=min((row.resolved_timestamp_ms for row in rows), default=None),
            feature_hash=feature_hash,
            feature_status=status,
            output_paths=tuple(result.input_paths),
            feature_names=feature_names,
            modules_used=tuple(dict.fromkeys(modules_used)),
            quant_equation_refs=QUANT_EQUATION_REFS,
            blocker_codes=tuple(
                dict.fromkeys(
                    (
                        *blockers,
                        *(
                            ()
                            if feature_registry
                            else ("FEATURE_REGISTRY_NOT_AVAILABLE",)
                        ),
                    )
                )
            ),
        )
    )


def build_gold_feature_quality_report(
    manifest: GoldMicrostructureFeatureManifest,
) -> dict[str, object]:
    """Build one compact quality report for operator diagnostics."""

    return {
        "schema_version": "v1",
        "feature_status": manifest.feature_status,
        "feature_row_count": manifest.feature_row_count,
        "feature_groups_declared": list(manifest.feature_groups_declared),
        "feature_groups_generated": list(manifest.feature_groups_generated),
        "feature_groups_missing": list(manifest.feature_groups_missing),
        "feature_timestamp_policy": manifest.feature_timestamp_policy,
        "feature_hash": manifest.feature_hash,
        "feature_names": list(manifest.feature_names),
        "modules_used": list(manifest.modules_used),
        "quant_equation_refs": list(manifest.quant_equation_refs),
        "output_paths": list(manifest.output_paths),
        "blocker_codes": list(manifest.blocker_codes),
    }


def write_gold_feature_reports(
    output_dir: Path,
    manifest: GoldMicrostructureFeatureManifest,
) -> tuple[str, str]:
    """Write the governed gold feature manifest and quality report."""

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "gold_microstructure_feature_manifest.json"
    quality_path = output_dir / "gold_feature_quality_report.json"
    atomic_write_json(manifest_path, manifest.model_dump(mode="json"), indent=2)
    atomic_write_json(quality_path, build_gold_feature_quality_report(manifest), indent=2)
    return str(manifest_path.resolve()), str(quality_path.resolve())


__all__ = [
    "DECLARED_FEATURE_GROUPS",
    "build_gold_feature_quality_report",
    "build_gold_microstructure_feature_manifest",
    "write_gold_feature_reports",
]
