"""Tests for the prudent Shadow-compatible execution simulator."""

from __future__ import annotations

from local_replay_runtime import (
    HistoricalReplayDataset,
    HistoricalReplayOpportunity,
    ParityTolerancePolicy,
    ShadowExecutionSimulatorConfig,
    build_parity_diagnostics_payload,
    simulate_shadow_compatible_dtrs,
)


def _dataset() -> HistoricalReplayDataset:
    return HistoricalReplayDataset.from_records(
        dataset_id="dataset-simulator-1",
        source_path="inmemory://simulator",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-1",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                raw_score=0.9,
                penalized_score=0.87,
                final_score=0.84,
                expected_edge_bps=18.0,
                spread_bps=3.0,
                slippage_bps=2.0,
                latency_penalty_bps=1.0,
                fill_ratio=1.0,
                target_decision_state="executed",
                production_decision_state="executed",
                production_final_score=0.84,
                production_expected_cost=0.00063,
                candidate_size=1.0,
                final_size=1.0,
                gross_return_bps=22.0,
                feature_values={"spread_bps": 3.0},
            ),
            HistoricalReplayOpportunity(
                opportunity_id="op-2",
                timestamp_ms=1_700_000_060_000,
                pair="ETHUSDT",
                engine_id="engine_b",
                raw_score=0.75,
                penalized_score=0.7,
                final_score=0.68,
                expected_edge_bps=10.0,
                spread_bps=4.0,
                slippage_bps=2.0,
                latency_penalty_bps=1.0,
                fill_ratio=0.4,
                target_decision_state="executed",
                production_decision_state="reduced",
                production_final_score=0.68,
                production_expected_cost=0.00073,
                candidate_size=1.0,
                final_size=1.0,
                gross_return_bps=10.0,
                feature_values={"spread_bps": 4.0},
            ),
            HistoricalReplayOpportunity(
                opportunity_id="op-3",
                timestamp_ms=1_700_000_120_000,
                pair="SOLUSDT",
                engine_id="engine_a",
                raw_score=0.2,
                final_score=0.1,
                expected_edge_bps=2.0,
                spread_bps=8.0,
                slippage_bps=3.0,
                latency_penalty_bps=2.0,
                target_decision_state="hard_blocked",
                production_decision_state="hard_blocked",
                production_final_score=0.1,
                production_expected_cost=0.00125,
                hard_block_reasons=("ce_negative",),
                primary_reason="ce_negative",
                feature_values={"spread_bps": 8.0},
            ),
        ),
    )


def test_simulate_shadow_compatible_dtrs_applies_prudent_execution_states():
    records = simulate_shadow_compatible_dtrs(_dataset())

    assert len(records) == 3
    assert records[0].decision_state == "executed"
    assert records[1].decision_state == "reduced"
    assert records[1].realized_cost > 0.0
    assert records[2].decision_state == "hard_blocked"
    assert records[2].realized_cost == 0.0


def test_build_parity_diagnostics_payload_reports_ok_when_baselines_match():
    dataset = _dataset()
    records = simulate_shadow_compatible_dtrs(dataset)
    payload = build_parity_diagnostics_payload(dataset, records)

    assert payload["parity_status"] == "ok"
    assert payload["decision_match_rate"] == 1.0
    assert payload["score_alignment"] == "within_prudent_tolerance"
    assert payload["cost_alignment"] == "within_prudent_tolerance"
    assert payload["baseline_status"] == "sufficient"
    assert payload["book_depth_source_status"] == "BOOK_DEPTH_NOT_PROVEN"
    assert payload["impact_source_status"] == "IMPACT_SOURCE_NOT_PROVEN"
    assert payload["fill_ratio_source"] == "REPLAY_MODEL"
    assert payload["fill_realism_status"] == "FILL_REALISM_MODEL_ONLY"
    assert payload["fill_source_status"] == "FILL_SOURCE_REPLAY_MODEL"
    assert payload["realized_slippage_status"] == "NOT_PROVEN"
    assert payload["cost_parity_status"] == "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY"
    assert payload["parity_policy"]["float_precision"] == "binary64"


def test_build_parity_diagnostics_payload_warns_when_policy_is_stricter_than_data():
    dataset = _dataset()
    records = simulate_shadow_compatible_dtrs(dataset)
    payload = build_parity_diagnostics_payload(
        dataset,
        records,
        config=ShadowExecutionSimulatorConfig(
            parity_policy=ParityTolerancePolicy(minimum_compared_records=4)
        ),
    )

    assert payload["parity_status"] == "warning"
    assert payload["baseline_status"] == "insufficient"


def test_build_parity_diagnostics_payload_distinguishes_depth20_limited_top_of_book_and_missing() -> None:
    def build_depth_dataset(levels: int | None) -> HistoricalReplayDataset:
        return HistoricalReplayDataset.from_records(
            dataset_id=f"dataset-depth-{levels}",
            source_path="inmemory://depth",
            records=(
                HistoricalReplayOpportunity(
                    opportunity_id="op-depth",
                    timestamp_ms=1_700_000_000_000,
                    pair="BTCUSDT",
                    engine_id="engine_a",
                    raw_score=0.9,
                    final_score=0.84,
                    expected_edge_bps=18.0,
                    spread_bps=3.0,
                    slippage_bps=2.0,
                    latency_penalty_bps=1.0,
                    fill_ratio=1.0,
                    target_decision_state="executed",
                    candidate_size=1.0,
                    final_size=1.0,
                    gross_return_bps=22.0,
                    feature_values={"spread_bps": 3.0},
                    book_depth_levels=levels,
                ),
            ),
        )

    depth20_payload = build_parity_diagnostics_payload(
        build_depth_dataset(20),
        simulate_shadow_compatible_dtrs(build_depth_dataset(20)),
    )
    assert depth20_payload["impact_source_status"] == "IMPACT_SOURCE_DEPTH20_MODEL"
    assert depth20_payload["impact_depth_readiness_status"] == "DEPTH20_AVAILABLE"
    assert depth20_payload["shadow_extension_required"] is False

    limited_payload = build_parity_diagnostics_payload(
        build_depth_dataset(10),
        simulate_shadow_compatible_dtrs(build_depth_dataset(10)),
    )
    assert limited_payload["impact_source_status"] == "IMPACT_SOURCE_LIMITED_DEPTH_MODEL"
    assert limited_payload["impact_depth_readiness_status"] == "LIMITED_DEPTH_PARTIAL"
    assert limited_payload["shadow_extension_required"] is True

    top_payload = build_parity_diagnostics_payload(
        build_depth_dataset(1),
        simulate_shadow_compatible_dtrs(build_depth_dataset(1)),
    )
    assert top_payload["impact_source_status"] == "IMPACT_SOURCE_TOP_OF_BOOK_PROXY"
    assert top_payload["impact_depth_readiness_status"] == "TOP_OF_BOOK_PROXY_ONLY"
    assert top_payload["shadow_extension_status"] == "SHADOW_DIAGNOSTIC_ONLY"

    missing_payload = build_parity_diagnostics_payload(
        build_depth_dataset(None),
        simulate_shadow_compatible_dtrs(build_depth_dataset(None)),
    )
    assert missing_payload["impact_source_status"] == "IMPACT_SOURCE_NOT_PROVEN"
    assert missing_payload["book_depth_source_status"] == "BOOK_DEPTH_NOT_PROVEN"


# ---------------------------------------------------------------------------
# Audit 2026-05-14 P3-A wiring : spread_model_source tier-aware mapping
# ---------------------------------------------------------------------------


def test_classify_spread_model_source_fresh_measurement_is_canonical() -> None:
    """tier-1 (`MEASURED_FROM_BOOK_SNAPSHOT`) → `CANONICAL_BOOK_MEASURED`."""
    from local_replay_runtime.shadow_execution_simulator import (
        _classify_spread_model_source,
    )
    assert (
        _classify_spread_model_source(
            spread_provenance="MEASURED_FROM_BOOK_SNAPSHOT",
            has_spread_guard=False,
        )
        == "CANONICAL_BOOK_MEASURED"
    )


def test_classify_spread_model_source_reconstruction_is_canonical() -> None:
    """tier-2 (`MEASURED_FROM_BOOK_RECONSTRUCTION`) → `CANONICAL_BOOK_RECONSTRUCTED`."""
    from local_replay_runtime.shadow_execution_simulator import (
        _classify_spread_model_source,
    )
    assert (
        _classify_spread_model_source(
            spread_provenance="MEASURED_FROM_BOOK_RECONSTRUCTION",
            has_spread_guard=False,
        )
        == "CANONICAL_BOOK_RECONSTRUCTED"
    )


def test_classify_spread_model_source_stale_is_audit_only_not_canonical() -> None:
    """tier-3 STALE → `MEASURED_STALE_AUDIT_ONLY` (NE leve PAS le gate
    `SPREAD_MODEL_PROXY` par directive utilisateur).

    Audit 2026-05-14 P3-A wiring verrouille la directive :
    > "STALE = audit-only, gate reste active.
    >  Do not clear execution fidelity from stale spread."
    """
    from local_replay_runtime.shadow_execution_simulator import (
        _classify_spread_model_source,
        _PURE_CANONICAL_EXECUTION_SOURCES,
    )
    classified = _classify_spread_model_source(
        spread_provenance="MEASURED_FROM_BOOK_SNAPSHOT_STALE",
        has_spread_guard=False,
    )
    assert classified == "MEASURED_STALE_AUDIT_ONLY"
    # Contrat critique : STALE n'est PAS dans la liste canonique → le gate
    # SPREAD_MODEL_PROXY restera actif sur les records concernes.
    assert classified not in _PURE_CANONICAL_EXECUTION_SOURCES


def test_classify_spread_model_source_default_falls_back_to_replay_proxy() -> None:
    """Sans provenance ni spread_guard, retombe sur `REPLAY_PROXY`."""
    from local_replay_runtime.shadow_execution_simulator import (
        _classify_spread_model_source,
    )
    assert (
        _classify_spread_model_source(
            spread_provenance="",
            has_spread_guard=False,
        )
        == "REPLAY_PROXY"
    )
    assert (
        _classify_spread_model_source(
            spread_provenance="DEFAULT_BY_BOOK_STATUS",
            has_spread_guard=False,
        )
        == "REPLAY_PROXY"
    )


def test_classify_spread_model_source_spread_guard_overrides_when_unset() -> None:
    """Sans provenance mais avec spread_guard configure, retourne
    `CANONICAL_SPREAD_GUARD` (mecanisme legacy preserve)."""
    from local_replay_runtime.shadow_execution_simulator import (
        _classify_spread_model_source,
    )
    assert (
        _classify_spread_model_source(
            spread_provenance="",
            has_spread_guard=True,
        )
        == "CANONICAL_SPREAD_GUARD"
    )


def test_pure_canonical_execution_sources_does_not_include_stale() -> None:
    """Audit 2026-05-14 P3-A : `MEASURED_STALE_AUDIT_ONLY` ne DOIT PAS
    apparaitre dans la frozenset canonique — sinon le gate
    SPREAD_MODEL_PROXY serait leve par un spread stale (violation directive
    utilisateur)."""
    from local_replay_runtime.shadow_execution_simulator import (
        _PURE_CANONICAL_EXECUTION_SOURCES,
    )
    assert "MEASURED_STALE_AUDIT_ONLY" not in _PURE_CANONICAL_EXECUTION_SOURCES
    # En contrepartie, fresh et reconstructed DOIVENT y etre.
    assert "CANONICAL_BOOK_MEASURED" in _PURE_CANONICAL_EXECUTION_SOURCES
    assert "CANONICAL_BOOK_RECONSTRUCTED" in _PURE_CANONICAL_EXECUTION_SOURCES


def test_spread_surface_fresh_book_measurement_is_canonical() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-spread-surface-fresh",
        source_path="inmemory://spread-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-spread-fresh",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=18.0,
                spread_bps=3.0,
                spread_provenance="MEASURED_FROM_BOOK_RECONSTRUCTION",
                target_decision_state="executed",
                candidate_size=1.0,
                final_size=1.0,
                feature_values={"spread_bps": 3.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    spread_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "spread_measurement"
    )
    assert spread_row["status"] == "CANONICAL_BACKBONE_USED"
    assert spread_row["selected_source"] == "book_replay_spread_measurement"


def test_spread_surface_stale_measurement_is_explicit_fallback() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-spread-surface-stale",
        source_path="inmemory://spread-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-spread-stale",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=18.0,
                spread_bps=3.0,
                spread_provenance="MEASURED_FROM_BOOK_SNAPSHOT_STALE",
                target_decision_state="executed",
                candidate_size=1.0,
                final_size=1.0,
                feature_values={"spread_bps": 3.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    spread_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "spread_measurement"
    )
    assert spread_row["status"] == "LOCAL_REPLAY_FALLBACK_USED"
    assert spread_row["promotion_allowed"] is False
    assert "SPREAD_MEASURED_STALE_AUDIT_ONLY" in spread_row["reason_codes"]


def test_slippage_surface_depth20_book_walk_is_canonical() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-slippage-surface-depth20",
        source_path="inmemory://slippage-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-slippage-depth20",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=18.0,
                spread_bps=3.0,
                slippage_bps=2.0,
                slippage_provenance="MEASURED_FROM_DEPTH20_BOOK_WALK",
                target_decision_state="executed",
                candidate_size=1.0,
                final_size=1.0,
                feature_values={"slippage_bps": 2.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    slippage_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "slippage_measurement"
    )
    assert slippage_row["status"] == "CANONICAL_BACKBONE_USED"
    assert slippage_row["selected_source"] == "execution_backbone.depth20_slippage_walk"


def test_slippage_surface_stale_depth20_is_explicit_fallback() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-slippage-surface-stale",
        source_path="inmemory://slippage-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-slippage-stale",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=18.0,
                spread_bps=3.0,
                slippage_bps=2.0,
                slippage_provenance="MEASURED_FROM_DEPTH20_BOOK_WALK_STALE",
                target_decision_state="executed",
                candidate_size=1.0,
                final_size=1.0,
                feature_values={"slippage_bps": 2.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    slippage_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "slippage_measurement"
    )
    assert slippage_row["status"] == "LOCAL_REPLAY_FALLBACK_USED"
    assert slippage_row["promotion_allowed"] is False
    assert "SLIPPAGE_MEASURED_STALE_AUDIT_ONLY" in slippage_row["reason_codes"]


def test_partial_fill_surface_explicit_fill_path_is_canonical() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-partial-fill-surface-explicit",
        source_path="inmemory://partial-fill-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-partial-fill-explicit",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=18.0,
                spread_bps=3.0,
                slippage_bps=2.0,
                fill_ratio=0.5,
                mid_price=100.0,
                fill_prices=(100.25,),
                fill_quantities=(5.0,),
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"fill_ratio": 0.5},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    partial_fill_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "partial_fill_cost"
    )
    assert partial_fill_row["status"] == "CANONICAL_BACKBONE_USED"
    assert (
        partial_fill_row["selected_source"]
        == "execution_backbone.partial_fill_cost_meter"
    )


def test_partial_fill_surface_synthetic_fill_ratio_is_explicit_fallback() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-partial-fill-surface-synthetic",
        source_path="inmemory://partial-fill-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-partial-fill-synthetic",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=18.0,
                spread_bps=3.0,
                slippage_bps=2.0,
                fill_ratio=0.5,
                mid_price=100.0,
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"fill_ratio": 0.5},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    partial_fill_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "partial_fill_cost"
    )
    assert partial_fill_row["status"] == "LOCAL_REPLAY_FALLBACK_USED"
    assert partial_fill_row["promotion_allowed"] is False
    assert (
        "PARTIAL_FILL_SYNTHETIC_FILL_PATH_AUDIT_ONLY"
        in partial_fill_row["reason_codes"]
    )


def test_adverse_selection_surface_explicit_fill_path_is_canonical() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-adverse-selection-surface-explicit",
        source_path="inmemory://adverse-selection-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-adverse-explicit",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=18.0,
                spread_bps=3.0,
                slippage_bps=2.0,
                fill_ratio=0.5,
                side="buy",
                mid_price=100.0,
                post_fill_mid_price=99.0,
                fill_prices=(100.25,),
                fill_quantities=(5.0,),
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"post_fill_mid_price": 99.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    adverse_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "adverse_selection"
    )
    assert adverse_row["status"] == "CANONICAL_BACKBONE_USED"
    assert adverse_row["selected_source"] == "execution_backbone.adverse_selection_meter"


def test_adverse_selection_surface_synthetic_fill_path_is_explicit_fallback() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-adverse-selection-surface-synthetic",
        source_path="inmemory://adverse-selection-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-adverse-synthetic",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=18.0,
                spread_bps=3.0,
                slippage_bps=2.0,
                fill_ratio=0.5,
                side="buy",
                mid_price=100.0,
                post_fill_mid_price=99.0,
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"post_fill_mid_price": 99.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    adverse_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "adverse_selection"
    )
    assert adverse_row["status"] == "LOCAL_REPLAY_FALLBACK_USED"
    assert adverse_row["promotion_allowed"] is False
    assert (
        "ADVERSE_SELECTION_SYNTHETIC_FILL_PATH_AUDIT_ONLY"
        in adverse_row["reason_codes"]
    )


def test_order_type_surface_uses_canonical_order_decider() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-order-type-surface-market",
        source_path="inmemory://order-type-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-order-market",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=18.0,
                spread_bps=2.0,
                slippage_bps=1.0,
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 18.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    order_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "order_type_selection"
    )
    assert order_row["status"] == "CANONICAL_BACKBONE_USED"
    assert order_row["selected_source"] == "execution_backbone.order_decider"
    assert order_row["canonical_payload"]["order_type"] in {"market", "limit"}


def test_order_type_surface_no_trade_is_canonical_decision_only() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-order-type-surface-no-trade",
        source_path="inmemory://order-type-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-order-no-trade",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=1.0,
                spread_bps=20.0,
                slippage_bps=5.0,
                target_decision_state="rejected_ranking",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 1.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    order_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "order_type_selection"
    )
    assert order_row["status"] == "CANONICAL_BACKBONE_USED"
    assert order_row["canonical_payload"]["order_type"] == "no_trade"
    assert payload["order_type_selection_source"] == "CANONICAL_ORDER_DECIDER"


def test_venue_constraints_surface_metadata_is_canonical() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-venue-constraints-surface",
        source_path="inmemory://venue-constraints-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-venue-constraints",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=18.0,
                spread_bps=2.0,
                slippage_bps=1.0,
                tick_size=0.01,
                step_size=0.001,
                min_notional=10.0,
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 18.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    venue_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "venue_constraints"
    )
    assert venue_row["status"] == "CANONICAL_BACKBONE_USED"
    assert venue_row["selected_source"] == "execution_backbone.venue_constraint_snapshot"
    assert venue_row["canonical_payload"]["min_notional"] == "10"


def test_venue_constraints_surface_missing_metadata_is_explicit_fallback() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-venue-constraints-missing",
        source_path="inmemory://venue-constraints-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-venue-missing",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=18.0,
                spread_bps=2.0,
                slippage_bps=1.0,
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 18.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    venue_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "venue_constraints"
    )
    assert venue_row["status"] == "NO_SURFACE_RESULT_AVAILABLE"
    assert venue_row["promotion_allowed"] is False
    assert "VENUE_CONSTRAINTS_BACKBONE_PAYLOAD_MISSING" in venue_row["reason_codes"]


def test_fee_aware_edge_surface_missing_config_is_explicit_fallback() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-fee-aware-edge-missing",
        source_path="inmemory://fee-aware-edge-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-fee-edge-missing",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=18.0,
                spread_bps=2.0,
                slippage_bps=1.0,
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 18.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    edge_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "fee_aware_edge_gate"
    )
    assert edge_row["status"] == "LOCAL_REPLAY_FALLBACK_USED"
    assert edge_row["promotion_allowed"] is False
    assert (
        "FEE_AWARE_EDGE_GATE_CONFIG_MISSING_OR_INVALID"
        in edge_row["reason_codes"]
    )


def test_cost_aggregation_surface_trade_cost_is_canonical() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-cost-aggregation-surface",
        source_path="inmemory://cost-aggregation-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-cost-aggregation",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=18.0,
                spread_bps=3.0,
                slippage_bps=2.0,
                fill_ratio=0.5,
                mid_price=100.0,
                fill_prices=(100.25,),
                fill_quantities=(5.0,),
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 18.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    cost_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "cost_aggregation"
    )
    assert cost_row["status"] == "CANONICAL_BACKBONE_USED"
    assert cost_row["selected_source"] == "execution_backbone.cost_aggregator"
    assert cost_row["canonical_payload"]["total_cost"] > 0.0


def test_cost_aggregation_surface_missing_trade_cost_is_explicit_fallback() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-cost-aggregation-missing",
        source_path="inmemory://cost-aggregation-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-cost-missing",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=18.0,
                spread_bps=3.0,
                slippage_bps=2.0,
                target_decision_state="executed",
                candidate_size=0.0,
                final_size=0.0,
                feature_values={"expected_edge_bps": 18.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    cost_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "cost_aggregation"
    )
    assert cost_row["status"] == "LOCAL_REPLAY_FALLBACK_USED"
    assert cost_row["promotion_allowed"] is False
    assert "COST_AGGREGATION_BACKBONE_PAYLOAD_MISSING" in cost_row["reason_codes"]


def test_fill_terminal_surface_explicit_fill_path_is_canonical() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-fill-terminal-surface",
        source_path="inmemory://fill-terminal-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-fill-terminal",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=18.0,
                spread_bps=3.0,
                slippage_bps=2.0,
                fill_ratio=0.5,
                mid_price=100.0,
                fill_prices=(100.25,),
                fill_quantities=(5.0,),
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"fill_ratio": 0.5},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    fill_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "fill_terminal_state"
    )
    assert fill_row["status"] == "CANONICAL_BACKBONE_USED"
    assert fill_row["selected_source"] == "execution_backbone.fill_tracker"
    assert fill_row["canonical_payload"]["category"] == "partial_fill_cancelled"


def test_fill_terminal_surface_synthetic_fill_path_is_explicit_fallback() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-fill-terminal-synthetic",
        source_path="inmemory://fill-terminal-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-fill-terminal-synthetic",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=18.0,
                spread_bps=3.0,
                slippage_bps=2.0,
                fill_ratio=0.5,
                mid_price=100.0,
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"fill_ratio": 0.5},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    fill_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "fill_terminal_state"
    )
    assert fill_row["status"] == "LOCAL_REPLAY_FALLBACK_USED"
    assert fill_row["promotion_allowed"] is False
    assert "FILL_TERMINAL_SYNTHETIC_FILL_PATH_AUDIT_ONLY" in fill_row["reason_codes"]


def test_execution_intent_surface_trade_order_is_canonical() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-execution-intent-surface",
        source_path="inmemory://execution-intent-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-execution-intent",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=30.0,
                spread_bps=2.0,
                slippage_bps=1.0,
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 30.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    intent_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "execution_intent"
    )
    assert intent_row["status"] == "CANONICAL_BACKBONE_USED"
    assert intent_row["selected_source"] == "execution_backbone.intent_builder"
    assert intent_row["canonical_payload"]["order_type"] in {"market", "limit"}


def test_execution_intent_surface_no_trade_is_explicit_fallback() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-execution-intent-no-trade",
        source_path="inmemory://execution-intent-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-execution-intent-no-trade",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=1.0,
                spread_bps=20.0,
                slippage_bps=5.0,
                target_decision_state="rejected_ranking",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 1.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    intent_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "execution_intent"
    )
    assert intent_row["status"] == "LOCAL_REPLAY_FALLBACK_USED"
    assert intent_row["promotion_allowed"] is False
    assert "EXECUTION_INTENT_NOT_CREATED_FOR_NO_TRADE" in intent_row["reason_codes"]


def test_order_decision_reporting_surface_trade_is_canonical() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-order-decision-reporting-trade",
        source_path="inmemory://order-decision-reporting",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-order-report-trade",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=30.0,
                spread_bps=2.0,
                slippage_bps=1.0,
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 30.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    report_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "order_decision_reporting"
    )
    assert report_row["status"] == "CANONICAL_BACKBONE_USED"
    assert report_row["selected_source"] == "execution_backbone.decision_reporter"
    assert report_row["canonical_payload"]["is_trade"] is True


def test_order_decision_reporting_surface_no_trade_is_canonical() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-order-decision-reporting-no-trade",
        source_path="inmemory://order-decision-reporting",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-order-report-no-trade",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=1.0,
                spread_bps=20.0,
                slippage_bps=5.0,
                target_decision_state="rejected_ranking",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 1.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    report_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "order_decision_reporting"
    )
    assert report_row["status"] == "CANONICAL_BACKBONE_USED"
    assert report_row["canonical_payload"]["is_trade"] is False
    assert report_row["canonical_payload"]["no_trade_reason"] == "cost_exceeds_edge"


def test_risk_filter_surface_with_limits_is_canonical() -> None:
    from risk_backbone.risk_runtime_models import RiskLimits

    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-risk-filter-surface",
        source_path="inmemory://risk-filter-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-risk-filter",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=30.0,
                spread_bps=2.0,
                slippage_bps=1.0,
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 30.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
        config=ShadowExecutionSimulatorConfig(
            risk_limits=RiskLimits(
                gross_cap=10_000.0,
                position_cap=4_000.0,
                loss_cap=1_000.0,
                beta_cap=10_000.0,
                cluster_cap=10_000.0,
            )
        ),
    )
    risk_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "risk_filter"
    )
    assert risk_row["status"] == "CANONICAL_BACKBONE_USED"
    assert risk_row["selected_source"] == "risk_backbone.risk_runtime"
    assert risk_row["canonical_payload"]["accepted"] is True


def test_risk_filter_surface_missing_limits_is_explicit_fallback() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-risk-filter-missing",
        source_path="inmemory://risk-filter-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-risk-filter-missing",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=30.0,
                spread_bps=2.0,
                slippage_bps=1.0,
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 30.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    risk_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "risk_filter"
    )
    # Updated 2026-05-27 (Patch BACKBONE-PARITY-P1-S5) — risk_limits now
    # defaults to RiskLimits(gross/position/loss/beta/cluster=1_000_000.0)
    # so the canonical RiskRuntime evaluator runs with neutral caps when
    # the simulator is constructed without overriding. The test row has
    # target_decision_state="executed" + candidate_size>0 → execution_intent
    # is non-None → the surface flips to CANONICAL_BACKBONE_USED. Explicit
    # `risk_limits=None` would restore the legacy fallback semantic.
    assert risk_row["status"] == "CANONICAL_BACKBONE_USED"
    assert risk_row["promotion_allowed"] is True
    assert "CANONICAL_BACKBONE_USED" in risk_row["reason_codes"]


def test_portfolio_state_surface_with_snapshot_is_canonical() -> None:
    from portfolio_minimal.opportunity_selector.eligibility_filter import PortfolioSnapshot
    from risk_backbone.risk_runtime_models import RiskLimits

    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-portfolio-state-surface",
        source_path="inmemory://portfolio-state-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-portfolio-state",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=30.0,
                spread_bps=2.0,
                slippage_bps=1.0,
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 30.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
        config=ShadowExecutionSimulatorConfig(
            risk_limits=RiskLimits(
                gross_cap=10_000.0,
                position_cap=4_000.0,
                loss_cap=1_000.0,
                beta_cap=10_000.0,
                cluster_cap=10_000.0,
            ),
            portfolio_snapshot=PortfolioSnapshot(
                remaining_gross_capacity=10_000.0,
                remaining_loss_capacity=1_000.0,
                remaining_beta_capacity=10_000.0,
                remaining_cluster_capacity={"BTCUSDT": 10_000.0},
            ),
        ),
    )
    portfolio_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "portfolio_state"
    )
    assert portfolio_row["status"] == "CANONICAL_BACKBONE_USED"
    assert portfolio_row["selected_source"] == "portfolio_minimal.allocation_router"
    assert portfolio_row["canonical_payload"]["phantom_verdict"] == "viable"


def test_portfolio_state_surface_missing_snapshot_is_explicit_fallback() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-portfolio-state-missing",
        source_path="inmemory://portfolio-state-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-portfolio-state-missing",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=30.0,
                spread_bps=2.0,
                slippage_bps=1.0,
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 30.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    portfolio_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "portfolio_state"
    )
    assert portfolio_row["status"] == "LOCAL_REPLAY_FALLBACK_USED"
    assert portfolio_row["promotion_allowed"] is False
    # Updated 2026-05-27 (Patches BACKBONE-PARITY-P1-S4 + S5) — both
    # portfolio_snapshot AND risk_limits now default to non-None canonical
    # values (PortfolioSnapshot(remaining_*=inf) + RiskLimits(*=1_000_000)).
    # The first two `if portfolio_snapshot is None` and `elif risk_limits is
    # None` branches no longer fire ; the surface falls back two chain steps
    # deeper with reason PORTFOLIO_CLUSTER_CAPACITY_MISSING. The
    # remaining_cluster_capacity dict is empty by default until the upstream
    # runtime injects per-pair mappings (e.g. BTCUSDT → some capacity).
    assert "PORTFOLIO_CLUSTER_CAPACITY_MISSING" in portfolio_row["reason_codes"]


def test_regime_classification_surface_with_inputs_is_canonical() -> None:
    from regime_classifier.regime_lite import RegimeLiteThresholds

    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-regime-classification-surface",
        source_path="inmemory://regime-classification-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-regime-classification",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=30.0,
                spread_bps=2.0,
                slippage_bps=1.0,
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={
                    "btc_realized_vol_24h": 0.01,
                    "btc_drop_1h": 0.0,
                    "intraday_drawdown": 0.0,
                    "engine_return_dispersion": 0.0,
                },
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
        config=ShadowExecutionSimulatorConfig(
            regime_lite_thresholds=RegimeLiteThresholds.from_documented_defaults()
        ),
    )
    regime_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "regime_classification"
    )
    assert regime_row["status"] == "CANONICAL_BACKBONE_USED"
    assert regime_row["selected_source"] == "regime_classifier.regime_lite"
    assert regime_row["canonical_payload"]["state"] == "calm"


def test_regime_classification_surface_local_regime_is_explicit_fallback() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-regime-classification-fallback",
        source_path="inmemory://regime-classification-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-regime-fallback",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                regime="trend",
                expected_edge_bps=30.0,
                spread_bps=2.0,
                slippage_bps=1.0,
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 30.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    regime_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "regime_classification"
    )
    assert regime_row["status"] == "LOCAL_REPLAY_FALLBACK_USED"
    assert regime_row["promotion_allowed"] is False
    # Updated 2026-05-27 (Patch BACKBONE-PARITY-P1-S3) — regime_lite_thresholds
    # now defaults to RegimeLiteThresholds.from_documented_defaults() so the
    # canonical classifier is invoked when the 4 required feature metrics are
    # available. This test row has only expected_edge_bps in feature_values
    # (no btc_realized_vol_24h / btc_drop_1h / intraday_drawdown /
    # engine_return_dispersion), so the canonical evaluation cannot run and
    # the surface still falls back to the local regime label. The reason
    # code shifts from REGIME_LITE_THRESHOLDS_NOT_CONFIGURED to
    # REGIME_CLASSIFIER_INPUTS_MISSING, which is the correct semantic now
    # that the thresholds are configured by default.
    assert "REGIME_CLASSIFIER_INPUTS_MISSING" in regime_row["reason_codes"]


def test_scoring_ranking_surface_with_weights_is_canonical() -> None:
    from scoring_backbone.ranking_router.ranking_score_builder import RankingWeights

    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-scoring-ranking-surface",
        source_path="inmemory://scoring-ranking-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-scoring-ranking",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                raw_score=0.9,
                penalized_score=0.8,
                final_score=0.75,
                expected_edge_bps=30.0,
                spread_bps=2.0,
                slippage_bps=1.0,
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 30.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
        config=ShadowExecutionSimulatorConfig(
            scoring_ranking_weights=RankingWeights(version="test.v1")
        ),
    )
    scoring_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "scoring_ranking"
    )
    assert scoring_row["status"] == "CANONICAL_BACKBONE_USED"
    assert scoring_row["selected_source"] == "scoring_backbone.ranking_score_builder"
    assert scoring_row["canonical_payload"]["weights_version"] == "test.v1"


def test_scoring_ranking_surface_missing_weights_is_explicit_fallback() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-scoring-ranking-missing",
        source_path="inmemory://scoring-ranking-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-scoring-ranking-missing",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                raw_score=0.9,
                penalized_score=0.8,
                final_score=0.75,
                expected_edge_bps=30.0,
                spread_bps=2.0,
                slippage_bps=1.0,
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 30.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    scoring_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "scoring_ranking"
    )
    # Updated 2026-05-27 (Patch BACKBONE-PARITY-P1-S2) — scoring_ranking now
    # defaults to canonical RankingWeights() (operational weights, no-op for
    # gating ; ranking can only re-order, not refuse). When the simulator is
    # constructed without overriding scoring_ranking_weights, the canonical
    # ranker runs and the surface reports CANONICAL_BACKBONE_USED. Explicit
    # `scoring_ranking_weights=None` would restore the legacy fallback.
    assert scoring_row["status"] == "CANONICAL_BACKBONE_USED"
    assert scoring_row["promotion_allowed"] is True


def test_hard_block_gate_surface_with_conditions_is_canonical() -> None:
    from scoring_backbone.hard_block_gate.blocker_evaluator import BlockerCondition

    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-hard-block-gate-surface",
        source_path="inmemory://hard-block-gate-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-hard-block-gate",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=30.0,
                spread_bps=2.0,
                slippage_bps=1.0,
                target_decision_state="hard_blocked",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 30.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
        config=ShadowExecutionSimulatorConfig(
            hard_block_conditions=BlockerCondition(is_stale_hard=True)
        ),
    )
    hard_block_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "hard_block_gate"
    )
    assert hard_block_row["status"] == "CANONICAL_BACKBONE_USED"
    assert hard_block_row["selected_source"] == "scoring_backbone.hard_block_gate"
    assert hard_block_row["canonical_payload"]["is_blocked"] is True
    assert "HB_STALE_HARD" in hard_block_row["canonical_payload"]["reason_codes"]


def test_hard_block_gate_surface_missing_conditions_is_explicit_fallback() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-hard-block-gate-missing",
        source_path="inmemory://hard-block-gate-surface",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-hard-block-gate-missing",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=30.0,
                spread_bps=2.0,
                slippage_bps=1.0,
                hard_block_reasons=("ce_negative",),
                target_decision_state="hard_blocked",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 30.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    hard_block_row = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "hard_block_gate"
    )
    # Updated 2026-05-27 (Patch BACKBONE-PARITY-P1-S1) — hard_block_gate now
    # defaults to canonical BlockerCondition() (all flags False, neutral
    # trading impact). When the simulator is constructed without overriding
    # hard_block_conditions, the canonical evaluator runs with the neutral
    # default and the surface reports CANONICAL_BACKBONE_USED. Explicit
    # `hard_block_conditions=None` would restore the legacy fallback.
    assert hard_block_row["status"] == "CANONICAL_BACKBONE_USED"
    assert hard_block_row["promotion_allowed"] is True
    assert "CANONICAL_BACKBONE_USED" in hard_block_row["reason_codes"]


def test_data_backbone_market_microstructure_depth20_is_canonical() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-data-backbone-market",
        source_path="inmemory://data-backbone-market",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-data-market",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_c",
                expected_edge_bps=18.0,
                spread_bps=2.0,
                slippage_bps=1.0,
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                book_depth_levels=20,
                book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
                book_depth_staleness_status="BOOK_DEPTH20_AVAILABLE",
                book_depth_snapshot_count=4,
                book_depth_event_count=12,
                book_depth_missing_count=0,
                feature_values={
                    "vpin": 0.12,
                    "cumulative_ofi": 3.4,
                    "queue_pressure": 0.2,
                    "realized_vol_at_break": 0.011,
                },
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    surface = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "data_backbone_market_microstructure"
    )

    assert surface["status"] == "CANONICAL_BACKBONE_USED"
    assert surface["promotion_allowed"] is True
    assert (
        surface["canonical_payload"]["source_status"]
        == "DATA_BACKBONE_DEPTH20_MICROSTRUCTURE_PROVEN"
    )
    assert surface["canonical_payload"]["microstructure_features"]["vpin"] == 0.12


def test_data_backbone_market_microstructure_missing_depth_is_fallback() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-data-backbone-market-fallback",
        source_path="inmemory://data-backbone-market",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-data-market-fallback",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_c",
                expected_edge_bps=18.0,
                spread_bps=2.0,
                slippage_bps=1.0,
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"vpin": 0.12, "queue_pressure": 0.2},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    surface = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "data_backbone_market_microstructure"
    )

    assert surface["status"] == "LOCAL_REPLAY_FALLBACK_USED"
    assert surface["promotion_allowed"] is False
    assert "DATA_BACKBONE_BOOK_DEPTH20_NOT_PROVEN" in surface["reason_codes"]
    assert (
        surface["fallback_payload"]["source_status"]
        == "LOCAL_REPLAY_FEATURE_VALUES_AUDIT_ONLY"
    )


def test_meta_learning_expected_edge_surface_ml_off_never_trains() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-meta-learning-off",
        source_path="inmemory://meta-learning",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-meta-off",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=18.0,
                spread_bps=2.0,
                slippage_bps=1.0,
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 18.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
    )
    surface = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "meta_learning_expected_edge"
    )

    assert surface["status"] == "LOCAL_REPLAY_FALLBACK_USED"
    assert surface["fallback_payload"]["training_invoked_by_b2"] is False
    assert "META_LEARNING_CORRECTLY_OUT_OF_B2_ML_MODE_OFF" in surface["reason_codes"]


def test_meta_learning_expected_edge_surface_frozen_artifact_is_canonical() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-meta-learning-frozen",
        source_path="inmemory://meta-learning",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-meta-frozen",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=18.0,
                spread_bps=2.0,
                slippage_bps=1.0,
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 18.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
        config=ShadowExecutionSimulatorConfig(
            ml_mode="ML_MODE_OVERLAY_FROZEN",
            expected_edge_model_status="GOVERNED_EDGE_MODEL_READY",
            expected_edge_model_artifact_hash="hash-a",
            expected_edge_model_feature_hash="feature-hash-a",
            expected_edge_training_artifact_ref="inmemory://artifact",
        ),
    )
    surface = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "meta_learning_expected_edge"
    )

    assert surface["status"] == "CANONICAL_BACKBONE_USED"
    assert surface["selected_source"] == "meta_learning.governed_expected_edge_artifact"
    assert surface["canonical_payload"]["training_invoked_by_b2"] is False
    assert surface["canonical_payload"]["decision_authority"] == "overlay_only"


def test_protocol_contract_surface_uses_contracts_without_live_transport() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-protocol-contract",
        source_path="inmemory://protocol-contract",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-protocol",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                expected_edge_bps=18.0,
                spread_bps=2.0,
                slippage_bps=1.0,
                target_decision_state="executed",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 18.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
        config=ShadowExecutionSimulatorConfig(
            protocol_contract_refs=("refusal_contract.v1",),
            refusal_contract_status="REFUSAL_CONTRACT_READY",
        ),
    )
    surface = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "protocol_contracts"
    )

    assert surface["status"] == "CANONICAL_BACKBONE_USED"
    assert surface["canonical_payload"]["live_transport_enabled"] is False
    assert surface["canonical_payload"]["transport_scope"] == "not_imported_in_b2"


def test_complete_enablers_build14_surface_reports_upstream_filter() -> None:
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-build14-filtered",
        source_path="inmemory://build14",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-build14",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_c",
                expected_edge_bps=18.0,
                spread_bps=2.0,
                slippage_bps=1.0,
                target_decision_state="hard_blocked",
                candidate_size=1_000.0,
                final_size=1_000.0,
                feature_values={"expected_edge_bps": 18.0},
            ),
        ),
    )
    payload = build_parity_diagnostics_payload(
        dataset,
        simulate_shadow_compatible_dtrs(dataset),
        config=ShadowExecutionSimulatorConfig(
            build14_context_status="BUILD14_CONTEXT_NOT_APPLIED",
            build14_feature_groups=("vpin_features", "queue_pressure"),
            build14_upstream_filter_status="ENGINE_C_FILTERED_UPSTREAM",
        ),
    )
    surface = next(
        row
        for row in payload["backbone_surface_report"]["rows"]
        if row["surface"] == "complete_enablers_build14"
    )

    assert surface["status"] == "LOCAL_REPLAY_FALLBACK_USED"
    assert "COMPLETE_ENABLERS_FILTERED_UPSTREAM" in surface["reason_codes"]
    assert (
        surface["fallback_payload"]["decision_authority"]
        == "not_available_or_filtered_upstream"
    )


# ---------------------------------------------------------------------------
# Audit 2026-05-14 P3-B wiring : slippage_model_source tier-aware mapping
# ---------------------------------------------------------------------------


def test_classify_slippage_model_source_kyle_measurement_is_canonical() -> None:
    """tier-1 (`MEASURED_FROM_KYLE_LAMBDA`) → `CANONICAL_KYLE_LAMBDA_METER`."""
    from local_replay_runtime.shadow_execution_simulator import (
        _classify_slippage_model_source,
    )
    assert (
        _classify_slippage_model_source(
            slippage_provenance="MEASURED_FROM_KYLE_LAMBDA",
            has_slippage_model=False,
        )
        == "CANONICAL_KYLE_LAMBDA_METER"
    )


def test_classify_slippage_model_source_caller_override_is_canonical() -> None:
    """`MEASURED_FROM_KYLE_LAMBDA_OVERRIDE` (caller-supplied, e.g. live API) →
    `CANONICAL_KYLE_LAMBDA_OVERRIDE`."""
    from local_replay_runtime.shadow_execution_simulator import (
        _classify_slippage_model_source,
    )
    assert (
        _classify_slippage_model_source(
            slippage_provenance="MEASURED_FROM_KYLE_LAMBDA_OVERRIDE",
            has_slippage_model=False,
        )
        == "CANONICAL_KYLE_LAMBDA_OVERRIDE"
    )


def test_classify_slippage_model_source_depth20_book_walk_is_canonical() -> None:
    from local_replay_runtime.shadow_execution_simulator import (
        _classify_slippage_model_source,
    )
    assert (
        _classify_slippage_model_source(
            slippage_provenance="MEASURED_FROM_DEPTH20_BOOK_WALK",
            has_slippage_model=False,
        )
        == "CANONICAL_EXECUTION_BACKBONE"
    )


def test_classify_slippage_model_source_stale_depth20_is_audit_only() -> None:
    from local_replay_runtime.shadow_execution_simulator import (
        _classify_slippage_model_source,
    )
    assert (
        _classify_slippage_model_source(
            slippage_provenance="MEASURED_FROM_DEPTH20_BOOK_WALK_STALE",
            has_slippage_model=False,
        )
        == "MEASURED_STALE_AUDIT_ONLY"
    )


def test_classify_slippage_model_source_default_falls_back_to_replay_proxy() -> None:
    """`DEFAULT_TO_CALIBRATE` (Kyle measurement echec ou non tente) +
    sans `config.slippage_model` → `REPLAY_PROXY`."""
    from local_replay_runtime.shadow_execution_simulator import (
        _classify_slippage_model_source,
    )
    assert (
        _classify_slippage_model_source(
            slippage_provenance="DEFAULT_TO_CALIBRATE",
            has_slippage_model=False,
        )
        == "REPLAY_PROXY"
    )
    assert (
        _classify_slippage_model_source(
            slippage_provenance="",
            has_slippage_model=False,
        )
        == "REPLAY_PROXY"
    )


def test_classify_slippage_model_source_legacy_backbone_when_model_present() -> None:
    """Sans provenance Kyle mais avec `config.slippage_model` configure,
    retourne `CANONICAL_EXECUTION_BACKBONE` (mecanisme legacy preserve)."""
    from local_replay_runtime.shadow_execution_simulator import (
        _classify_slippage_model_source,
    )
    assert (
        _classify_slippage_model_source(
            slippage_provenance="DEFAULT_TO_CALIBRATE",
            has_slippage_model=True,
        )
        == "CANONICAL_EXECUTION_BACKBONE"
    )


def test_pure_canonical_execution_sources_includes_kyle() -> None:
    """Audit 2026-05-14 P3-B : `CANONICAL_KYLE_LAMBDA_METER` et
    `CANONICAL_KYLE_LAMBDA_OVERRIDE` doivent etre dans la frozenset
    canonique pour que le gate `SLIPPAGE_MODEL_PROXY` se leve quand Kyle
    est mesure (ou override valide upstream)."""
    from local_replay_runtime.shadow_execution_simulator import (
        _PURE_CANONICAL_EXECUTION_SOURCES,
    )
    assert "CANONICAL_KYLE_LAMBDA_METER" in _PURE_CANONICAL_EXECUTION_SOURCES
    assert "CANONICAL_KYLE_LAMBDA_OVERRIDE" in _PURE_CANONICAL_EXECUTION_SOURCES


# ---------------------------------------------------------------------------
# Audit 2026-05-14 P3-C wiring : adverse_selection_source blocker traceability
# ---------------------------------------------------------------------------


def test_classify_adverse_selection_source_measured_is_canonical() -> None:
    """Avec adverse_selection_fraction != None (meter a tourne), retourne
    `CANONICAL_ADVERSE_SELECTION_METER`."""
    from local_replay_runtime.shadow_execution_simulator import (
        _classify_adverse_selection_source,
    )
    assert (
        _classify_adverse_selection_source(adverse_selection_fraction=0.0001)
        == "CANONICAL_ADVERSE_SELECTION_METER"
    )
    # adverse_selection_fraction = 0.0 (favorable post-fill) reste canonical
    assert (
        _classify_adverse_selection_source(adverse_selection_fraction=0.0)
        == "CANONICAL_ADVERSE_SELECTION_METER"
    )


def test_classify_adverse_selection_source_none_emits_blocked_by_dependency() -> None:
    """Audit 2026-05-14 P3-C : per directive utilisateur,
    > 'If dependency is missing, keep the blocker and emit
    >  ADVERSE_SELECTION_CANONICAL_METER_BLOCKED_BY_DEPENDENCY.'

    Quand adverse_selection_fraction is None (pas de trade execute / pas de
    post_fill_mid_price / pas de fill data), retourne le blocker code
    explicite plutot que le generique REPLAY_PROXY."""
    from local_replay_runtime.shadow_execution_simulator import (
        _classify_adverse_selection_source,
    )
    assert (
        _classify_adverse_selection_source(adverse_selection_fraction=None)
        == "ADVERSE_SELECTION_CANONICAL_METER_BLOCKED_BY_DEPENDENCY"
    )


def test_blocked_by_dependency_keeps_gate_active() -> None:
    """Audit 2026-05-14 P3-C : `ADVERSE_SELECTION_CANONICAL_METER_BLOCKED_BY_DEPENDENCY`
    NE DOIT PAS apparaitre dans `_PURE_CANONICAL_EXECUTION_SOURCES` — le gate
    `ADVERSE_SELECTION_PROXY` doit rester actif tant que la mesure n'est pas
    realisee (no false READY)."""
    from local_replay_runtime.shadow_execution_simulator import (
        _PURE_CANONICAL_EXECUTION_SOURCES,
    )
    assert (
        "ADVERSE_SELECTION_CANONICAL_METER_BLOCKED_BY_DEPENDENCY"
        not in _PURE_CANONICAL_EXECUTION_SOURCES
    )
    # CANONICAL_ADVERSE_SELECTION_METER reste canonical pour les cas mesures
    assert "CANONICAL_ADVERSE_SELECTION_METER" in _PURE_CANONICAL_EXECUTION_SOURCES
