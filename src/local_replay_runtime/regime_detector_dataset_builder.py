"""Local-IA-Lab regime-training dataset builder from governed historical LOB events."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Literal, NamedTuple

from data_backbone.microstructure import (
    CANONICAL_LOB_REGIME_FEATURE_SET_VERSION,
    LobAggTrade,
    LobBookLevel,
    LobDepth20Snapshot,
    LobRegimeFeatureSnapshot,
    build_lob_regime_feature_snapshot,
)
from interface_contracts import (
    DepthEvent,
    RegimeDetectorDatasetSample,
    RegimeDetectorLabelConfig,
    RegimeDetectorTrainingDataset,
    RegimeDurationBucket,
    RegimeToxicityBucket,
    TradeEvent,
)
from local_replay_runtime.historical_snapshot_loader import HistoricalSnapshotBatch

DATASET_BUILDER_LABEL_SCOPE = "LOCAL_LAB_TRAINING_ONLY"


class _RegimeStateSignature(NamedTuple):
    toxicity: RegimeToxicityBucket
    pressure: Literal["bid", "ask", "neutral"]


def _depth_snapshot(event: DepthEvent) -> LobDepth20Snapshot:
    return LobDepth20Snapshot(
        pair=event.pair,
        timestamp_ns=event.timestamp_ms * 1_000_000,
        bids=tuple(
            LobBookLevel(price=level.price, size=level.quantity)
            for level in event.bids[:20]
        ),
        asks=tuple(
            LobBookLevel(price=level.price, size=level.quantity)
            for level in event.asks[:20]
        ),
    )


def _agg_trade(event: TradeEvent) -> LobAggTrade:
    return LobAggTrade(
        timestamp_ns=event.timestamp_ms * 1_000_000,
        price=event.price,
        quantity=event.quantity,
        aggressor_side=event.side.value,
    )


def _pair_event_streams(
    batch: HistoricalSnapshotBatch,
    *,
    pair: str,
) -> tuple[tuple[LobDepth20Snapshot, ...], tuple[LobAggTrade, ...]]:
    depth_events: list[LobDepth20Snapshot] = []
    trade_events: list[LobAggTrade] = []
    for envelope in batch.events:
        if envelope.pair != pair:
            continue
        if isinstance(envelope.event, DepthEvent):
            depth_events.append(_depth_snapshot(envelope.event))
        elif isinstance(envelope.event, TradeEvent):
            trade_events.append(_agg_trade(envelope.event))
    return (
        tuple(sorted(depth_events, key=lambda item: item.timestamp_ns)),
        tuple(sorted(trade_events, key=lambda item: item.timestamp_ns)),
    )


def _snapshot_at(
    *,
    pair: str,
    depth_events: tuple[LobDepth20Snapshot, ...],
    trade_events: tuple[LobAggTrade, ...],
    timestamp_ns: int,
    window_seconds: float,
    label_config: RegimeDetectorLabelConfig,
) -> LobRegimeFeatureSnapshot | None:
    eligible_depth = tuple(item for item in depth_events if item.timestamp_ns <= timestamp_ns)
    eligible_trades = tuple(item for item in trade_events if item.timestamp_ns <= timestamp_ns)
    if len(eligible_depth) < 2:
        return None
    snapshot = build_lob_regime_feature_snapshot(
        eligible_depth,
        eligible_trades,
        pair=pair,
        computed_at_ns=timestamp_ns,
        window_seconds=window_seconds,
        top_n=label_config.top_n_levels,
        touch_eps_bps=label_config.touch_eps_bps,
    )
    if snapshot.data_status != "ready" or snapshot.insufficient_data:
        return None
    return snapshot


def _toxicity_bucket(
    snapshot: LobRegimeFeatureSnapshot,
    *,
    label_config: RegimeDetectorLabelConfig,
) -> RegimeToxicityBucket:
    max_spoof = max(snapshot.spoof_like_suspicion_bid, snapshot.spoof_like_suspicion_ask)
    if (
        snapshot.deceptive_liquidity_score >= label_config.toxicity_critical_floor
        or snapshot.liquidity_thinning_score >= label_config.liquidity_critical_floor
        or max_spoof >= label_config.spoof_critical_floor
    ):
        return RegimeToxicityBucket.CRITICAL
    if (
        snapshot.deceptive_liquidity_score >= label_config.toxicity_elevated_floor
        or snapshot.liquidity_thinning_score >= label_config.liquidity_elevated_floor
        or max_spoof >= label_config.spoof_elevated_floor
    ):
        return RegimeToxicityBucket.ELEVATED
    return RegimeToxicityBucket.NOMINAL


def _pressure_state(
    snapshot: LobRegimeFeatureSnapshot,
    *,
    label_config: RegimeDetectorLabelConfig,
) -> Literal["bid", "ask", "neutral"]:
    if (
        snapshot.order_book_imbalance >= label_config.imbalance_flip_threshold
        and snapshot.microprice_pressure >= label_config.microprice_flip_threshold_bps
    ):
        return "bid"
    if (
        snapshot.order_book_imbalance <= -label_config.imbalance_flip_threshold
        and snapshot.microprice_pressure <= -label_config.microprice_flip_threshold_bps
    ):
        return "ask"
    return "neutral"


def _state_signature(
    snapshot: LobRegimeFeatureSnapshot,
    *,
    label_config: RegimeDetectorLabelConfig,
) -> _RegimeStateSignature:
    return _RegimeStateSignature(
        toxicity=_toxicity_bucket(snapshot, label_config=label_config),
        pressure=_pressure_state(snapshot, label_config=label_config),
    )


def _has_transition(
    current: LobRegimeFeatureSnapshot,
    future: LobRegimeFeatureSnapshot,
    *,
    label_config: RegimeDetectorLabelConfig,
) -> bool:
    current_state = _state_signature(current, label_config=label_config)
    future_state = _state_signature(future, label_config=label_config)
    if future_state != current_state:
        return True
    if (
        abs(future.deceptive_liquidity_score - current.deceptive_liquidity_score)
        >= label_config.toxicity_delta_threshold
    ):
        return True
    if (
        abs(future.liquidity_thinning_score - current.liquidity_thinning_score)
        >= label_config.toxicity_delta_threshold
    ):
        return True
    return (
        current.order_book_imbalance * future.order_book_imbalance <= 0.0
        and abs(future.order_book_imbalance - current.order_book_imbalance)
        >= label_config.imbalance_flip_threshold
    )


def _duration_bucket(consecutive_windows: int) -> RegimeDurationBucket:
    if consecutive_windows <= 1:
        return RegimeDurationBucket.FRAGILE
    if consecutive_windows == 2:
        return RegimeDurationBucket.SHORT
    if consecutive_windows == 3:
        return RegimeDurationBucket.MEDIUM
    return RegimeDurationBucket.PERSISTENT


def _sample_input_hash(
    *,
    current_snapshot: LobRegimeFeatureSnapshot,
    future_snapshots: tuple[LobRegimeFeatureSnapshot, ...],
    label_config: RegimeDetectorLabelConfig,
) -> str:
    payload = {
        "current_input_data_hash": current_snapshot.input_data_hash,
        "future_input_data_hashes": [item.input_data_hash for item in future_snapshots],
        "label_config_hash": label_config.config_hash(),
    }
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _feature_hash(feature_values: dict[str, float]) -> str:
    return sha256(
        json.dumps(
            {
                "feature_set_version": CANONICAL_LOB_REGIME_FEATURE_SET_VERSION,
                "feature_names": sorted(feature_values),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _build_sample(
    *,
    pair: str,
    anchor_timestamp_ns: int,
    current_snapshot: LobRegimeFeatureSnapshot,
    future_snapshots: tuple[LobRegimeFeatureSnapshot, ...],
    label_config: RegimeDetectorLabelConfig,
) -> RegimeDetectorDatasetSample:
    first_future = future_snapshots[0]
    current_state = _state_signature(current_snapshot, label_config=label_config)
    first_future_state = _state_signature(first_future, label_config=label_config)
    transition = 1 if _has_transition(current_snapshot, first_future, label_config=label_config) else 0
    target_state = first_future_state if transition else current_state
    consecutive = 0
    for snapshot in future_snapshots:
        if _state_signature(snapshot, label_config=label_config) != target_state:
            break
        consecutive += 1
    feature_values = current_snapshot.as_feature_map_for_version(
        CANONICAL_LOB_REGIME_FEATURE_SET_VERSION
    )
    reason_codes = (
        ("REGIME_LABEL_TRANSITION",) if transition else ("REGIME_LABEL_STABLE",)
    ) + (f"REGIME_TOXICITY_{target_state.toxicity.value.upper()}",)
    return RegimeDetectorDatasetSample(
        pair=pair,
        anchor_timestamp_ns=anchor_timestamp_ns,
        feature_values=feature_values,
        feature_set_version=CANONICAL_LOB_REGIME_FEATURE_SET_VERSION,
        transition_next_window=transition,
        duration_bucket=_duration_bucket(consecutive),
        toxicity_bucket=target_state.toxicity,
        future_steps_observed=len(future_snapshots),
        input_data_hash=_sample_input_hash(
            current_snapshot=current_snapshot,
            future_snapshots=future_snapshots,
            label_config=label_config,
        ),
        feature_hash=_feature_hash(feature_values),
        label_config_hash=label_config.config_hash(),
        reason_codes=reason_codes,
    )


def build_regime_detector_training_dataset(
    batch: HistoricalSnapshotBatch,
    *,
    dataset_id: str | None = None,
    label_config: RegimeDetectorLabelConfig | None = None,
    pair_scope: tuple[str, ...] | None = None,
) -> RegimeDetectorTrainingDataset:
    """Project raw historical depth/trade events into Local-Lab regime-training rows."""

    config = label_config or RegimeDetectorLabelConfig()
    selected_pairs = pair_scope or batch.pair_scope
    samples: list[RegimeDetectorDatasetSample] = []
    future_window_ns = int(config.future_window_seconds * 1_000_000_000)
    for pair in selected_pairs:
        depth_events, trade_events = _pair_event_streams(batch, pair=pair)
        if len(depth_events) < 2:
            continue
        for anchor in depth_events:
            current_snapshot = _snapshot_at(
                pair=pair,
                depth_events=depth_events,
                trade_events=trade_events,
                timestamp_ns=anchor.timestamp_ns,
                window_seconds=config.current_window_seconds,
                label_config=config,
            )
            if current_snapshot is None:
                continue
            future_snapshots: list[LobRegimeFeatureSnapshot] = []
            for step in range(1, config.max_future_steps + 1):
                future_snapshot = _snapshot_at(
                    pair=pair,
                    depth_events=depth_events,
                    trade_events=trade_events,
                    timestamp_ns=anchor.timestamp_ns + (future_window_ns * step),
                    window_seconds=config.future_window_seconds,
                    label_config=config,
                )
                if future_snapshot is None:
                    break
                future_snapshots.append(future_snapshot)
            if not future_snapshots:
                continue
            samples.append(
                _build_sample(
                    pair=pair,
                    anchor_timestamp_ns=anchor.timestamp_ns,
                    current_snapshot=current_snapshot,
                    future_snapshots=tuple(future_snapshots),
                    label_config=config,
                )
            )
    if not samples:
        raise ValueError("No eligible regime-detector training samples could be built")
    ordered_samples = tuple(sorted(samples, key=lambda item: (item.pair, item.anchor_timestamp_ns)))
    feature_names = ordered_samples[0].feature_names
    normalized_dataset_id = dataset_id or Path(batch.source_path).stem.replace(" ", "_")
    return RegimeDetectorTrainingDataset(
        dataset_id=normalized_dataset_id,
        source_path=batch.source_path,
        source=batch.source,
        feature_set_version=CANONICAL_LOB_REGIME_FEATURE_SET_VERSION,
        label_config_hash=config.config_hash(),
        samples=ordered_samples,
        pair_scope=tuple(sorted({sample.pair for sample in ordered_samples})),
        feature_names=feature_names,
    )


__all__ = ["DATASET_BUILDER_LABEL_SCOPE", "build_regime_detector_training_dataset"]
