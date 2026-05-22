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
