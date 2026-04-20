from __future__ import annotations

import pytest

from data_backbone.microstructure import (
    ENGINE_C_MICROSTRUCTURE_INPUT_FIELDS,
    ENGINE_D_MICROSTRUCTURE_INPUT_FIELDS,
    EngineAMicrostructureProvenance,
    EngineCMicrostructureProvenance,
    EngineDMicrostructureProvenance,
    build_engine_a_microstructure_provenance,
    build_engine_a_runner_microstructure_updates,
    build_engine_c_microstructure_provenance,
    build_engine_c_runner_microstructure_updates,
    build_engine_d_microstructure_provenance,
    build_engine_d_runner_microstructure_updates,
    compose_engine_c_input_payload,
    compose_engine_d_input_payload,
)
from data_backbone.microstructure.kyle_lambda import KyleLambdaRecord
from data_backbone.microstructure.order_flow_imbalance import OrderFlowImbalanceRecord
from data_backbone.microstructure.queue_pressure import QueuePressureRecord
from data_backbone.microstructure.realized_kernel_vol import RealizedKernelVolRecord
from data_backbone.microstructure.vpin import VpinRecord
from engines.engine_a.engine_a_runner import EngineAInput
from engines.engine_c.engine_c_runner import EngineCInput
from engines.engine_d.engine_d_models import EngineDInput


def _ofi_record(pair: str = "BTCUSDT") -> OrderFlowImbalanceRecord:
    return OrderFlowImbalanceRecord(
        value=12.5,
        partial_window=False,
        low_sample_confidence=False,
        n_events_received=20,
        window_used=(19, 9.5),
        n_events_used=20,
        method_version_hash="a" * 64,
        pair=pair,
        computed_at_ns=1_000_000_000,
        input_data_hash="b" * 64,
    )


def _realized_kernel_record(pair: str = "BTCUSDT", *, value: float = 0.08) -> RealizedKernelVolRecord:
    return RealizedKernelVolRecord(
        value=value,
        kernel_variance=value * value,
        bandwidth=3,
        low_sample_confidence=False,
        insufficient_variation=False,
        n_events_received=12,
        window_used=(12, 3_600.0),
        n_events_used=12,
        method_version_hash="c" * 64,
        pair=pair,
        computed_at_ns=1_000_000_000,
        input_data_hash="d" * 64,
    )


def _kyle_record(pair: str = "BTCUSDT") -> KyleLambdaRecord:
    return KyleLambdaRecord(
        value=0.0008,
        normalized_value=0.000008,
        is_stale=False,
        stale_reason=None,
        partial_window=False,
        low_sample_confidence=False,
        insufficient_variation=False,
        derived_input_warning=None,
        n_events_received=40,
        n_intervals_used=10,
        n_intervals_effective=9,
        window_used=(None, 3_600.0),
        n_events_used=30,
        method_version_hash="e" * 64,
        pair=pair,
        computed_at_ns=1_000_000_000,
        input_data_hash="f" * 64,
    )


def _queue_record(pair: str = "BTCUSDT") -> QueuePressureRecord:
    return QueuePressureRecord(
        value=0.31,
        top_k_used=5,
        partial_window=False,
        low_sample_confidence=False,
        bid_volume_used=15.0,
        ask_volume_used=8.0,
        window_used=(1, None),
        n_events_used=1,
        method_version_hash="1" * 64,
        pair=pair,
        computed_at_ns=1_000_000_000,
        input_data_hash="2" * 64,
    )


def _vpin_record(pair: str = "BTCUSDT") -> VpinRecord:
    return VpinRecord(
        value=0.22,
        bucket_volume=100.0,
        n_buckets_used=10,
        n_complete_buckets=10,
        n_events_received=100,
        partial_window=False,
        low_sample_confidence=False,
        insufficient_variation=False,
        derived_input_warning=None,
        window_used=(10, 7_200.0),
        n_events_used=95,
        method_version_hash="3" * 64,
        pair=pair,
        computed_at_ns=1_000_000_000,
        input_data_hash="4" * 64,
    )


def test_engine_a_microstructure_provenance_builds_runner_updates() -> None:
    provenance = EngineAMicrostructureProvenance(
        pair="btcusdt",
        ofi_record=_ofi_record(),
        ofi_flow_score=0.83,
        realized_kernel_record=_realized_kernel_record(),
        realized_kernel_vol_scale=0.64,
        realized_vol_current=0.08,
        kyle_lambda_record=_kyle_record(),
        kyle_lambda_cost_uplift=0.0002,
    )

    updates = provenance.to_runner_updates()
    engine_input = EngineAInput(
        pair="BTCUSDT",
        direction_score=0.8,
        continuation_score=0.7,
        structure_quality=0.75,
        zone_proximity=0.6,
        trend_stability=0.55,
        candidate_size=1.0,
        entry_price=100.0,
        atr=1.0,
        **updates,
    )

    assert updates == {
        "ofi_flow_score": 0.83,
        "realized_kernel_vol_scale": 0.64,
        "realized_vol_current": 0.08,
        "kyle_lambda_cost_uplift": 0.0002,
    }
    assert engine_input.ofi_flow_score == pytest.approx(0.83)
    assert engine_input.realized_kernel_vol_scale == pytest.approx(0.64)
    assert engine_input.realized_vol_current == pytest.approx(0.08)
    assert engine_input.kyle_lambda_cost_uplift == pytest.approx(0.0002)


def test_engine_c_microstructure_provenance_builds_runner_updates() -> None:
    provenance = EngineCMicrostructureProvenance(
        pair="BTCUSDT",
        ofi_record=_ofi_record(),
        cumulative_ofi=12.5,
        queue_pressure_record=_queue_record(),
        queue_pressure=0.31,
        vpin_record=_vpin_record(),
        vpin=0.22,
        kyle_lambda_record=_kyle_record(),
        kyle_lambda=0.0008,
        realized_vol_current_record=_realized_kernel_record(value=0.018),
        realized_vol_current=0.018,
        realized_vol_at_break_record=_realized_kernel_record(value=0.02),
        realized_vol_at_break=0.02,
    )

    updates = provenance.to_runner_updates()
    engine_input = EngineCInput(
        pair="BTCUSDT",
        breakout_strength=0.8,
        range_quality=0.7,
        compression_quality=0.65,
        volume_confirmation=0.7,
        followthrough_room=0.72,
        extension_pct=0.25,
        candidate_size=1.0,
        **updates,
    )

    assert updates == {
        "cumulative_ofi": 12.5,
        "queue_pressure": 0.31,
        "vpin": 0.22,
        "kyle_lambda": 0.0008,
        "realized_vol_current": 0.018,
        "realized_vol_at_break": 0.02,
    }
    assert engine_input.cumulative_ofi == pytest.approx(12.5)
    assert engine_input.queue_pressure == pytest.approx(0.31)
    assert engine_input.vpin == pytest.approx(0.22)
    assert engine_input.kyle_lambda == pytest.approx(0.0008)
    assert engine_input.realized_vol_current == pytest.approx(0.018)
    assert engine_input.realized_vol_at_break == pytest.approx(0.02)


def test_engine_d_microstructure_provenance_builds_runner_updates() -> None:
    provenance = EngineDMicrostructureProvenance(
        pair="BTCUSDT",
        realized_vol_current_record=_realized_kernel_record(value=0.018),
        realized_vol_current=0.018,
        realized_vol_post_close_record=_realized_kernel_record(value=0.015),
        realized_vol_post_close=0.015,
    )

    updates = provenance.to_runner_updates()
    engine_input = EngineDInput(
        pair="BTCUSDT",
        prior_trade_quality=0.8,
        reformation_quality=0.7,
        pullback_quality=0.6,
        continuation_room=0.7,
        concentration_headroom=0.8,
        marginal_edge=0.75,
        reentry_lateness=0.2,
        structure_reformed_detected=True,
        candidate_size=1.0,
        entry_price=100.0,
        reentry_anchor_price=99.0,
        **updates,
    )

    assert updates == {
        "realized_vol_current": 0.018,
        "realized_vol_post_close": 0.015,
    }
    assert engine_input.realized_vol_current == pytest.approx(0.018)
    assert engine_input.realized_vol_post_close == pytest.approx(0.015)


def test_engine_a_provenance_requires_record_when_scalar_is_present() -> None:
    with pytest.raises(ValueError, match="ofi_record is required"):
        EngineAMicrostructureProvenance(pair="BTCUSDT", ofi_flow_score=0.8)


def test_engine_c_provenance_rejects_pair_mismatch() -> None:
    with pytest.raises(ValueError, match="must match provenance pair"):
        EngineCMicrostructureProvenance(
            pair="ETHUSDT",
            ofi_record=_ofi_record(pair="BTCUSDT"),
            cumulative_ofi=10.0,
        )


def test_build_engine_c_microstructure_provenance_uses_canonical_values() -> None:
    provenance = build_engine_c_microstructure_provenance(
        pair="btcusdt",
        ofi_record=_ofi_record(),
        queue_pressure_record=_queue_record(),
        vpin_record=_vpin_record(),
        kyle_lambda_record=_kyle_record(),
        realized_vol_current_record=_realized_kernel_record(value=0.018),
        realized_vol_at_break_record=_realized_kernel_record(value=0.02),
    )

    assert provenance.pair == "BTCUSDT"
    assert provenance.to_runner_updates() == {
        "cumulative_ofi": 12.5,
        "queue_pressure": 0.31,
        "vpin": 0.22,
        "kyle_lambda": 0.0008,
        "realized_vol_current": 0.018,
        "realized_vol_at_break": 0.02,
    }


def test_build_engine_d_microstructure_provenance_uses_canonical_values() -> None:
    provenance = build_engine_d_microstructure_provenance(
        pair="btcusdt",
        realized_vol_current_record=_realized_kernel_record(value=0.018),
        realized_vol_post_close_record=_realized_kernel_record(value=0.015),
    )

    assert provenance.pair == "BTCUSDT"
    assert provenance.to_runner_updates() == {
        "realized_vol_current": 0.018,
        "realized_vol_post_close": 0.015,
    }


def test_build_engine_a_microstructure_provenance_keeps_scalar_mapping_explicit() -> None:
    provenance = build_engine_a_microstructure_provenance(
        pair="BTCUSDT",
        ofi_record=_ofi_record(),
        ofi_flow_score=0.83,
        realized_kernel_record=_realized_kernel_record(),
        realized_kernel_vol_scale=0.64,
        realized_vol_current=0.08,
        kyle_lambda_record=_kyle_record(),
        kyle_lambda_cost_uplift=0.0002,
    )

    assert provenance.to_runner_updates() == {
        "ofi_flow_score": 0.83,
        "realized_kernel_vol_scale": 0.64,
        "realized_vol_current": 0.08,
        "kyle_lambda_cost_uplift": 0.0002,
    }


def test_build_engine_a_microstructure_provenance_does_not_invent_scalar_mapping() -> None:
    provenance = build_engine_a_microstructure_provenance(
        pair="BTCUSDT",
        ofi_record=_ofi_record(),
        realized_kernel_record=_realized_kernel_record(),
        kyle_lambda_record=_kyle_record(),
    )

    assert provenance.to_runner_updates() == {
        "ofi_flow_score": None,
        "realized_kernel_vol_scale": None,
        "realized_vol_current": None,
        "kyle_lambda_cost_uplift": 0.0,
    }


def test_build_engine_c_runner_microstructure_updates_returns_current_seam_payload() -> None:
    updates = build_engine_c_runner_microstructure_updates(
        pair="BTCUSDT",
        ofi_record=_ofi_record(),
        queue_pressure_record=_queue_record(),
        vpin_record=_vpin_record(),
        kyle_lambda_record=_kyle_record(),
        realized_vol_current_record=_realized_kernel_record(value=0.018),
        realized_vol_at_break_record=_realized_kernel_record(value=0.02),
    )

    assert updates == {
        "cumulative_ofi": 12.5,
        "queue_pressure": 0.31,
        "vpin": 0.22,
        "kyle_lambda": 0.0008,
        "realized_vol_current": 0.018,
        "realized_vol_at_break": 0.02,
    }


def test_build_engine_d_runner_microstructure_updates_returns_current_seam_payload() -> None:
    updates = build_engine_d_runner_microstructure_updates(
        pair="BTCUSDT",
        realized_vol_current_record=_realized_kernel_record(value=0.018),
        realized_vol_post_close_record=_realized_kernel_record(value=0.015),
    )

    assert updates == {
        "realized_vol_current": 0.018,
        "realized_vol_post_close": 0.015,
    }


def test_build_engine_a_runner_microstructure_updates_preserves_explicit_scalar_ownership() -> None:
    updates = build_engine_a_runner_microstructure_updates(
        pair="BTCUSDT",
        ofi_record=_ofi_record(),
        ofi_flow_score=0.83,
        realized_kernel_record=_realized_kernel_record(),
        realized_kernel_vol_scale=0.64,
        realized_vol_current=0.08,
        kyle_lambda_record=_kyle_record(),
        kyle_lambda_cost_uplift=0.0002,
    )

    assert updates == {
        "ofi_flow_score": 0.83,
        "realized_kernel_vol_scale": 0.64,
        "realized_vol_current": 0.08,
        "kyle_lambda_cost_uplift": 0.0002,
    }


def test_compose_engine_c_input_payload_builds_engine_c_input_compatible_payload() -> None:
    payload = compose_engine_c_input_payload(
        {
            "pair": "btcusdt",
            "breakout_strength": 0.8,
            "range_quality": 0.7,
            "compression_quality": 0.65,
            "volume_confirmation": 0.7,
            "followthrough_room": 0.72,
            "extension_pct": 0.25,
            "candidate_size": 1.0,
        },
        pair="BTCUSDT",
        ofi_record=_ofi_record(),
        queue_pressure_record=_queue_record(),
        vpin_record=_vpin_record(),
        kyle_lambda_record=_kyle_record(),
        realized_vol_current_record=_realized_kernel_record(value=0.018),
        realized_vol_at_break_record=_realized_kernel_record(value=0.02),
    )

    assert ENGINE_C_MICROSTRUCTURE_INPUT_FIELDS.issubset(payload)
    engine_input = EngineCInput(**payload)
    assert engine_input.pair == "BTCUSDT"
    assert engine_input.cumulative_ofi == pytest.approx(12.5)
    assert engine_input.queue_pressure == pytest.approx(0.31)
    assert engine_input.vpin == pytest.approx(0.22)
    assert engine_input.kyle_lambda == pytest.approx(0.0008)
    assert engine_input.realized_vol_current == pytest.approx(0.018)
    assert engine_input.realized_vol_at_break == pytest.approx(0.02)


def test_compose_engine_c_input_payload_rejects_conflicting_microstructure_ownership() -> None:
    with pytest.raises(ValueError, match="conflicting Engine C microstructure field: vpin"):
        compose_engine_c_input_payload(
            {
                "pair": "BTCUSDT",
                "breakout_strength": 0.8,
                "range_quality": 0.7,
                "compression_quality": 0.65,
                "volume_confirmation": 0.7,
                "followthrough_room": 0.72,
                "extension_pct": 0.25,
                "candidate_size": 1.0,
                "vpin": 0.55,
            },
            pair="BTCUSDT",
            vpin_record=_vpin_record(),
        )


def test_compose_engine_c_input_payload_rejects_pair_mismatch() -> None:
    with pytest.raises(ValueError, match="base_payload pair must match canonical microstructure pair"):
        compose_engine_c_input_payload(
            {"pair": "ETHUSDT"},
            pair="BTCUSDT",
            ofi_record=_ofi_record(),
        )


def test_compose_engine_d_input_payload_builds_engine_d_input_compatible_payload() -> None:
    payload = compose_engine_d_input_payload(
        {
            "pair": "btcusdt",
            "prior_trade_quality": 0.8,
            "reformation_quality": 0.7,
            "pullback_quality": 0.6,
            "continuation_room": 0.7,
            "concentration_headroom": 0.8,
            "marginal_edge": 0.75,
            "reentry_lateness": 0.2,
            "structure_reformed_detected": True,
            "candidate_size": 1.0,
            "entry_price": 100.0,
            "reentry_anchor_price": 99.0,
        },
        pair="BTCUSDT",
        realized_vol_current_record=_realized_kernel_record(value=0.018),
        realized_vol_post_close_record=_realized_kernel_record(value=0.015),
    )

    assert ENGINE_D_MICROSTRUCTURE_INPUT_FIELDS.issubset(payload)
    engine_input = EngineDInput(**payload)
    assert engine_input.pair == "BTCUSDT"
    assert engine_input.realized_vol_current == pytest.approx(0.018)
    assert engine_input.realized_vol_post_close == pytest.approx(0.015)


def test_compose_engine_d_input_payload_rejects_conflicting_microstructure_ownership() -> None:
    with pytest.raises(ValueError, match="conflicting Engine D microstructure field: realized_vol_current"):
        compose_engine_d_input_payload(
            {
                "pair": "BTCUSDT",
                "realized_vol_current": 0.03,
            },
            pair="BTCUSDT",
            realized_vol_current_record=_realized_kernel_record(value=0.018),
        )


def test_compose_engine_d_input_payload_rejects_pair_mismatch() -> None:
    with pytest.raises(ValueError, match="base_payload pair must match canonical microstructure pair"):
        compose_engine_d_input_payload(
            {"pair": "ETHUSDT"},
            pair="BTCUSDT",
            realized_vol_current_record=_realized_kernel_record(value=0.018),
        )
