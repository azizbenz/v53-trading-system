"""Runtime tests for Build-5 scoring backbone."""

import base64
from datetime import UTC, datetime
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

import scoring_backbone.scoring_runtime as scoring_runtime_module
from backtest_artifact_import import package_ml_model_artifact_for_transport
from complete_enablers import MlScoringSoftPenaltyHook, MlScoringSoftPenaltyHookConfig
from interface_contracts import MlModelArtifact, MlModelWindow, PromotionState
from scoring_backbone import ScoringCandidateInput, ScoringRuntime
from scoring_backbone.hard_block_gate.blocker_evaluator import BlockerCondition
from scoring_backbone.penalty_aggregator.penalty_registry import PenaltyDefinition, PenaltyRegistry, PenaltyType
from scoring_backbone.ranking_router.candidate_pool_builder import CandidatePool, RankingCandidate
from scoring_backbone.penalty_aggregator.score_penalty_builder import ScorePenaltyItem
from scoring_backbone.penalty_aggregator.size_penalty_builder import SizePenaltyItem
from scoring_backbone.ranking_router.portfolio_compatibility_checker import PortfolioState
from scoring_backbone.ranking_router.selection_resolver import SelectionOutcome
from tests.support_paths import make_repo_scratch_dir


pytestmark = pytest.mark.build5


def _registry() -> PenaltyRegistry:
    registry = PenaltyRegistry()
    registry.register(PenaltyDefinition(penalty_id="stale", name="Staleness", penalty_type=PenaltyType.SCORE))
    registry.register(PenaltyDefinition(penalty_id="spread", name="Spread", penalty_type=PenaltyType.SCORE))
    registry.register(PenaltyDefinition(penalty_id="size_stale", name="Staleness sizing", penalty_type=PenaltyType.SIZE))
    return registry


def _candidate(
    *,
    engine_id: str,
    pair: str,
    raw_features: dict[str, float],
    expected_ce: float,
    expected_cost: float,
    projected_size: float,
    projected_loss: float,
    projected_beta_impact: float,
    cluster_id: str,
    score_penalties: tuple[ScorePenaltyItem, ...] = (),
    size_penalties: tuple[SizePenaltyItem, ...] = (),
    blocker_conditions: BlockerCondition | None = None,
    corr_penalty: float = 0.0,
    risk_penalty: float = 0.0,
    execution_fragility: float = 0.0,
    market_toxicity: float = 0.0,
    spread_regime_penalty: float = 0.0,
    participation_penalty: float = 0.0,
    cost_model_completeness_status: str = "UNKNOWN",
    fee_source_status: str = "UNKNOWN",
    impact_source_status: str = "UNKNOWN",
    fill_realism_status: str = "UNKNOWN",
    realized_slippage_status: str = "UNKNOWN",
    raw_score_multiplier: float = 1.0,
    raw_score_add: float = 0.0,
    raw_score_cap: float | None = None,
    scoring_version: str = "5.0",
    supplementary_refs: tuple[str, ...] = (),
    carriage_statuses: tuple[str, ...] = (),
    carriage_reason_codes: tuple[str, ...] = (),
) -> ScoringCandidateInput:
    return ScoringCandidateInput(
        engine_id=engine_id,
        pair=pair,
        raw_features=raw_features,
        supplementary_refs=supplementary_refs,
        carriage_statuses=carriage_statuses,
        carriage_reason_codes=carriage_reason_codes,
        allowed_features=frozenset({"momentum", "flow"}),
        weights={"momentum": 2.0, "flow": 1.0},
        scoring_version=scoring_version,
        raw_score_multiplier=raw_score_multiplier,
        raw_score_add=raw_score_add,
        raw_score_cap=raw_score_cap,
        score_penalties=score_penalties,
        size_penalties=size_penalties,
        blocker_conditions=blocker_conditions or BlockerCondition(),
        expected_cost=expected_cost,
        expected_ce=expected_ce,
        projected_size=projected_size,
        projected_loss=projected_loss,
        projected_beta_impact=projected_beta_impact,
        cluster_id=cluster_id,
        corr_penalty=corr_penalty,
        risk_penalty=risk_penalty,
        execution_fragility=execution_fragility,
        market_toxicity=market_toxicity,
        spread_regime_penalty=spread_regime_penalty,
        participation_penalty=participation_penalty,
        cost_model_completeness_status=cost_model_completeness_status,
        fee_source_status=fee_source_status,
        impact_source_status=impact_source_status,
        fill_realism_status=fill_realism_status,
        realized_slippage_status=realized_slippage_status,
    )


def _artifact(*, prediction: float) -> MlModelArtifact:
    created_at = datetime(2026, 4, 22, 12, 0, tzinfo=UTC)
    return MlModelArtifact.create(
        feature_names=("momentum", "flow"),
        feature_hash="1" * 64,
        pair_universe=("BTCUSDT",),
        train_window=MlModelWindow(
            start_at=datetime(2025, 9, 24, tzinfo=UTC),
            end_at=datetime(2026, 3, 22, tzinfo=UTC),
        ),
        validation_window=MlModelWindow(
            start_at=datetime(2026, 3, 23, tzinfo=UTC),
            end_at=datetime(2026, 4, 21, tzinfo=UTC),
        ),
        oos_sharpe=1.0,
        backtest_sharpe=1.2,
        ks_test_features_pvalue=0.4,
        shadow_diff_pct=0.02,
        promotion_state=PromotionState.REPLAY_ONLY,
        training_seed=4,
        created_at=created_at,
        calibration_version="cal.v1",
        dataset_hash="2" * 64,
        model_bytes_b64=base64.b64encode(
            json.dumps({"prediction": prediction}).encode("utf-8")
        ).decode("ascii"),
    )


def _fake_lightgbm_module() -> SimpleNamespace:
    class FakeBooster:
        def __init__(self, *, model_str: str | None = None, model_file: str | None = None) -> None:
            assert model_file is None
            payload = json.loads(model_str or "{}")
            self._prediction = float(payload.get("prediction", 0.5))

        def predict(self, rows: list[list[float]]) -> list[float]:
            assert rows
            return [self._prediction]

    return SimpleNamespace(Booster=FakeBooster)


def _scratch_dir(label: str) -> Path:
    return make_repo_scratch_dir(
        "scoring_backbone_ml_scoring_runtime_tests",
        label,
    )


def _packaged_artifact_refs(
    *,
    label: str,
    prediction: float,
    stale_after: datetime | None = None,
) -> tuple[Path, Path, tuple[str, ...]]:
    export_dir = _scratch_dir(f"{label}_export")
    source_dir = _scratch_dir(f"{label}_source")
    source_path = source_dir / "ml_model_artifact.json"
    artifact = _artifact(prediction=prediction)
    if stale_after is not None:
        payload = artifact.model_dump(mode="python")
        payload["stale_after"] = stale_after
        artifact = MlModelArtifact.create(**payload)
    source_path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    transport_package = package_ml_model_artifact_for_transport(
        export_dir,
        source_artifact_ref=str(source_path),
    )
    return (
        export_dir,
        source_dir,
        (
            transport_package.transport_artifact_ref,
            transport_package.summary_ref,
            transport_package.source_summary_ref,
        ),
    )


class TestScoringRuntime:
    def test_runtime_keeps_high_confidence_ml_neutral_without_uplift(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "complete_enablers.ml_confidence_enabler._load_lightgbm_module",
            lambda: _fake_lightgbm_module(),
        )
        export_dir, source_dir, supplementary_refs = _packaged_artifact_refs(
            label="runtime_ml_hook",
            prediction=0.9,
        )
        runtime = ScoringRuntime(
            _registry(),
            soft_penalty_hook=MlScoringSoftPenaltyHook(
                config=MlScoringSoftPenaltyHookConfig(alpha=0.3),
            ),
        )

        try:
            result = runtime.run_round(
                (
                    _candidate(
                        engine_id="eng_a",
                        pair="BTCUSDT",
                        raw_features={"momentum": 1.0, "flow": 0.5},
                        supplementary_refs=supplementary_refs,
                        expected_ce=0.2,
                        expected_cost=0.05,
                        projected_size=10.0,
                        projected_loss=1.0,
                        projected_beta_impact=0.01,
                        cluster_id="majors",
                    ),
                ),
                portfolio=PortfolioState(
                    remaining_gross_capacity=1000.0,
                    remaining_loss_capacity=100.0,
                    remaining_beta_capacity=1.0,
                    remaining_cluster_capacity={"majors": 500.0},
                ),
                max_selections=1,
                now=4.0,
            )

            audit = result.audits[0]
            assert audit.raw_score_result.base_raw_score == pytest.approx(2.5)
            assert audit.raw_score_result.raw_score_multiplier == pytest.approx(1.0)
            assert audit.raw_score_result.raw_score == pytest.approx(2.5)
            assert "ML_ARTIFACT_ACTIVE" in audit.explainability.artifact_hook_reason_codes
            assert "ML_SCORE_MODULATION_ACTIVE" in audit.explainability.artifact_hook_reason_codes
            assert "ML_ACTIVE_GOVERNED_REFS" in audit.explainability.carriage_statuses
            assert audit.economics.artifact_raw_score_multiplier_delta == pytest.approx(0.0)
            assert audit.selection_entry is not None
            assert audit.selection_entry.outcome == SelectionOutcome.SELECTED
        finally:
            shutil.rmtree(export_dir, ignore_errors=True)
            shutil.rmtree(source_dir, ignore_errors=True)

    def test_runtime_marks_stale_ml_refs_as_neutral_not_active(self) -> None:
        export_dir, source_dir, supplementary_refs = _packaged_artifact_refs(
            label="runtime_ml_stale",
            prediction=0.8,
            stale_after=datetime(2026, 4, 22, 12, 0, tzinfo=UTC),
        )
        runtime = ScoringRuntime(
            _registry(),
            soft_penalty_hook=MlScoringSoftPenaltyHook(
                config=MlScoringSoftPenaltyHookConfig(alpha=0.3),
            ),
        )

        try:
            result = runtime.run_round(
                (
                    _candidate(
                        engine_id="eng_a",
                        pair="BTCUSDT",
                        raw_features={"momentum": 1.0, "flow": 0.5},
                        supplementary_refs=supplementary_refs,
                        expected_ce=0.2,
                        expected_cost=0.05,
                        projected_size=10.0,
                        projected_loss=1.0,
                        projected_beta_impact=0.01,
                        cluster_id="majors",
                    ),
                ),
                portfolio=PortfolioState(
                    remaining_gross_capacity=1000.0,
                    remaining_loss_capacity=100.0,
                    remaining_beta_capacity=1.0,
                    remaining_cluster_capacity={"majors": 500.0},
                ),
                max_selections=1,
                now=datetime(2026, 4, 22, 12, 1, tzinfo=UTC).timestamp(),
            )

            audit = result.audits[0]
            assert audit.raw_score_result.base_raw_score == pytest.approx(2.5)
            assert audit.raw_score_result.raw_score == pytest.approx(2.5)
            assert "ML_STALE_NEUTRAL" in audit.explainability.carriage_statuses
            assert "ML_ACTIVE_GOVERNED_REFS" not in audit.explainability.carriage_statuses
            assert "ML_ARTIFACT_STALE" in audit.explainability.artifact_hook_reason_codes
            assert audit.economics.artifact_raw_score_multiplier_delta == pytest.approx(0.0)
        finally:
            shutil.rmtree(export_dir, ignore_errors=True)
            shutil.rmtree(source_dir, ignore_errors=True)

    def test_runtime_marks_hash_mismatched_ml_refs_as_disabled_not_active(self) -> None:
        export_dir, source_dir, supplementary_refs = _packaged_artifact_refs(
            label="runtime_ml_hash_mismatch",
            prediction=0.8,
        )
        runtime = ScoringRuntime(
            _registry(),
            soft_penalty_hook=MlScoringSoftPenaltyHook(
                config=MlScoringSoftPenaltyHookConfig(alpha=0.3),
            ),
        )

        try:
            summary_path = Path(supplementary_refs[1])
            summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
            summary_payload["artifact_hash"] = "f" * 64
            summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

            result = runtime.run_round(
                (
                    _candidate(
                        engine_id="eng_a",
                        pair="BTCUSDT",
                        raw_features={"momentum": 1.0, "flow": 0.5},
                        supplementary_refs=supplementary_refs,
                        expected_ce=0.2,
                        expected_cost=0.05,
                        projected_size=10.0,
                        projected_loss=1.0,
                        projected_beta_impact=0.01,
                        cluster_id="majors",
                    ),
                ),
                portfolio=PortfolioState(
                    remaining_gross_capacity=1000.0,
                    remaining_loss_capacity=100.0,
                    remaining_beta_capacity=1.0,
                    remaining_cluster_capacity={"majors": 500.0},
                ),
                max_selections=1,
                now=4.1,
            )

            audit = result.audits[0]
            assert audit.raw_score_result.base_raw_score == pytest.approx(2.5)
            assert audit.raw_score_result.raw_score == pytest.approx(2.5)
            assert "ML_HASH_MISMATCH_DISABLED" in audit.explainability.carriage_statuses
            assert "ML_ACTIVE_GOVERNED_REFS" not in audit.explainability.carriage_statuses
            assert "ML_ARTIFACT_HASH_MISMATCH" in audit.explainability.artifact_hook_reason_codes
            assert audit.economics.artifact_raw_score_multiplier_delta == pytest.approx(0.0)
        finally:
            shutil.rmtree(export_dir, ignore_errors=True)
            shutil.rmtree(source_dir, ignore_errors=True)

    def test_runtime_preserves_raw_score_and_exposes_shared_scoring_carriage_metadata(self) -> None:
        runtime = ScoringRuntime(_registry())

        result = runtime.run_round(
            (
                _candidate(
                    engine_id="eng_a",
                    pair="BTCUSDT",
                    raw_features={"momentum": 1.0, "flow": 0.5},
                    expected_ce=0.2,
                    expected_cost=0.05,
                    projected_size=10.0,
                    projected_loss=1.0,
                    projected_beta_impact=0.01,
                    cluster_id="majors",
                    execution_fragility=0.8,
                    market_toxicity=0.7,
                    spread_regime_penalty=0.6,
                    carriage_statuses=(
                        "derived_shared_scoring",
                        "shared_scoring_physics_carried",
                        "shared_scoring_physics_partial",
                    ),
                    carriage_reason_codes=("SCORING_SHARED_PHYSICS_MAPPING_NOT_PROVEN",),
                ),
            ),
            portfolio=PortfolioState(
                remaining_gross_capacity=1000.0,
                remaining_loss_capacity=100.0,
                remaining_beta_capacity=1.0,
                remaining_cluster_capacity={"majors": 500.0},
            ),
            max_selections=1,
            now=4.0,
        )

        audit = result.audits[0]
        assert audit.raw_score_result.base_raw_score == pytest.approx(2.5)
        assert audit.raw_score_result.raw_score == pytest.approx(2.5)
        assert "shared_scoring_physics_carried" in audit.explainability.carriage_statuses
        assert "shared_scoring_physics_partial" in audit.explainability.carriage_statuses
        assert "ml_refs_missing_neutral" in audit.explainability.carriage_statuses
        assert "ML_NEUTRAL_NO_REFS" in audit.explainability.carriage_statuses
        assert "SCORING_SHARED_PHYSICS_MAPPING_NOT_PROVEN" in audit.explainability.carriage_reason_codes
        assert "ML_REFS_MISSING_NEUTRAL" in audit.explainability.carriage_reason_codes
        assert audit.economics.carriage_statuses == audit.explainability.carriage_statuses

    def test_runtime_carries_partial_cost_model_without_changing_scoring_math(self) -> None:
        runtime = ScoringRuntime(_registry())

        result = runtime.run_round(
            (
                _candidate(
                    engine_id="eng_a",
                    pair="BTCUSDT",
                    raw_features={"momentum": 1.0, "flow": 0.5},
                    expected_ce=0.2,
                    expected_cost=0.05,
                    projected_size=10.0,
                    projected_loss=1.0,
                    projected_beta_impact=0.01,
                    cluster_id="majors",
                    cost_model_completeness_status="PARTIAL_NO_FEE_NO_IMPACT",
                    fee_source_status="NOT_PROVEN",
                    impact_source_status="NOT_PROVEN",
                    fill_realism_status="PARTIAL",
                    realized_slippage_status="NOT_PROVEN",
                ),
            ),
            portfolio=PortfolioState(
                remaining_gross_capacity=1000.0,
                remaining_loss_capacity=100.0,
                remaining_beta_capacity=1.0,
                remaining_cluster_capacity={"majors": 500.0},
            ),
            max_selections=1,
            now=4.5,
        )

        audit = result.audits[0]
        assert audit.raw_score_result.base_raw_score == pytest.approx(2.5)
        assert audit.raw_score_result.raw_score == pytest.approx(2.5)
        assert audit.explainability.scoring_risk_cost_completeness_status == (
            "SCORING_RISK_COST_COMPLETENESS_PARTIAL"
        )
        assert "COST_MODEL_INCOMPLETE" in audit.explainability.cost_readiness_reason_codes
        assert audit.explainability.execution_ready is False
        assert audit.explainability.promotion_ready is False
        assert audit.economics.cost_model_completeness_status == "PARTIAL_NO_FEE_NO_IMPACT"
        assert audit.economics.execution_ready is False
        assert audit.economics.promotion_ready is False

    def test_runtime_defaults_missing_cost_completeness_to_unknown_not_complete(self) -> None:
        runtime = ScoringRuntime(_registry())

        result = runtime.run_round(
            (
                _candidate(
                    engine_id="eng_a",
                    pair="BTCUSDT",
                    raw_features={"momentum": 1.0, "flow": 0.5},
                    expected_ce=0.2,
                    expected_cost=0.05,
                    projected_size=10.0,
                    projected_loss=1.0,
                    projected_beta_impact=0.01,
                    cluster_id="majors",
                ),
            ),
            portfolio=PortfolioState(
                remaining_gross_capacity=1000.0,
                remaining_loss_capacity=100.0,
                remaining_beta_capacity=1.0,
                remaining_cluster_capacity={"majors": 500.0},
            ),
            max_selections=1,
            now=4.6,
        )

        audit = result.audits[0]
        assert audit.explainability.cost_model_completeness_status == "UNKNOWN"
        assert audit.economics.cost_model_completeness_status == "UNKNOWN"
        assert audit.economics.execution_ready is False

    def test_runtime_applies_scoring_soft_penalty_hook_before_raw_score_calculation(self):
        def _soft_penalty(_hook_input):
            return scoring_runtime_module.ScoringSoftPenaltyLayerOutcome(
                raw_score_multiplier_delta=-0.10,
                raw_score_add=-0.02,
                raw_score_cap=2.0,
                reason_codes=("ARTIFACT_SCORING_SOFT_REDUCE",),
                detail="artifact scoring soft penalty applied",
            )

        runtime = ScoringRuntime(_registry(), soft_penalty_hook=_soft_penalty)
        result = runtime.run_round(
            (
                _candidate(
                    engine_id="eng_a",
                    pair="BTCUSDT",
                    raw_features={"momentum": 1.0, "flow": 0.5},
                    expected_ce=0.2,
                    expected_cost=0.05,
                    projected_size=10.0,
                    projected_loss=1.0,
                    projected_beta_impact=0.01,
                    cluster_id="majors",
                    raw_score_multiplier=1.10,
                    raw_score_add=0.05,
                    raw_score_cap=2.20,
                ),
            ),
            portfolio=PortfolioState(
                remaining_gross_capacity=1000.0,
                remaining_loss_capacity=100.0,
                remaining_beta_capacity=1.0,
                remaining_cluster_capacity={"majors": 500.0},
            ),
            max_selections=1,
            now=4.0,
        )

        audit = result.audits[0]
        assert audit.raw_score_result.base_raw_score == pytest.approx(2.5)
        assert audit.raw_score_result.raw_score_multiplier == pytest.approx(1.0)
        assert audit.raw_score_result.raw_score_add == pytest.approx(0.03)
        assert audit.raw_score_result.raw_score_cap == pytest.approx(2.0)
        assert audit.raw_score_result.raw_score == pytest.approx(2.0)
        assert audit.explainability.artifact_hook_reason_codes == ("ARTIFACT_SCORING_SOFT_REDUCE",)
        assert "artifact=mult=-0.1000,add=-0.0200,cap=2.0" in audit.explainability.summary
        assert audit.economics.artifact_raw_score_multiplier_delta == pytest.approx(-0.10)
        assert audit.economics.artifact_raw_score_add == pytest.approx(-0.02)
        assert audit.economics.artifact_raw_score_cap == pytest.approx(2.0)

    def test_runtime_applies_raw_score_adjustments_before_penalties(self):
        runtime = ScoringRuntime(_registry())
        result = runtime.run_round(
            (
                _candidate(
                    engine_id="eng_a",
                    pair="BTCUSDT",
                    raw_features={"momentum": 1.0, "flow": 0.5},
                    expected_ce=0.2,
                    expected_cost=0.05,
                    projected_size=10.0,
                    projected_loss=1.0,
                    projected_beta_impact=0.01,
                    cluster_id="majors",
                    raw_score_multiplier=1.10,
                    raw_score_add=0.05,
                    raw_score_cap=2.20,
                ),
            ),
            portfolio=PortfolioState(
                remaining_gross_capacity=1000.0,
                remaining_loss_capacity=100.0,
                remaining_beta_capacity=1.0,
                remaining_cluster_capacity={"majors": 500.0},
            ),
            max_selections=1,
            now=5.0,
        )

        audit = result.audits[0]
        assert audit.raw_score_result.base_raw_score == pytest.approx(2.5)
        assert audit.raw_score_result.raw_score_multiplier == pytest.approx(1.10)
        assert audit.raw_score_result.raw_score_add == pytest.approx(0.05)
        assert audit.raw_score_result.raw_score_cap == pytest.approx(2.20)
        assert audit.raw_score_result.raw_score == pytest.approx(2.20)
        assert audit.economics.penalized_score == pytest.approx(2.20)
        assert audit.selection_entry is not None
        assert audit.selection_entry.outcome == SelectionOutcome.SELECTED

    def test_runtime_distinguishes_penalty_from_relative_ranking_rejection(self):
        runtime = ScoringRuntime(_registry())
        portfolio = PortfolioState(
            remaining_gross_capacity=1000.0,
            remaining_loss_capacity=100.0,
            remaining_beta_capacity=1.0,
            remaining_cluster_capacity={"majors": 500.0},
        )
        result = runtime.run_round(
            (
                _candidate(
                    engine_id="eng_a",
                    pair="BTCUSDT",
                    raw_features={"momentum": 1.2, "flow": 0.8, "forbidden": 9.0},
                    expected_ce=0.1,
                    expected_cost=0.2,
                    projected_size=50.0,
                    projected_loss=5.0,
                    projected_beta_impact=0.05,
                    cluster_id="majors",
                    score_penalties=(
                        ScorePenaltyItem(penalty_id="stale", value=2.8, reason="data stale"),
                        ScorePenaltyItem(penalty_id="spread", value=0.1, reason="wide spread"),
                    ),
                    size_penalties=(SizePenaltyItem(penalty_id="size_stale", multiplier=0.1, reason="stale sizing"),),
                ),
                _candidate(
                    engine_id="eng_b",
                    pair="ETHUSDT",
                    raw_features={"momentum": 1.3, "flow": 1.0},
                    expected_ce=0.2,
                    expected_cost=0.1,
                    projected_size=50.0,
                    projected_loss=5.0,
                    projected_beta_impact=0.05,
                    cluster_id="majors",
                ),
            ),
            portfolio=portfolio,
            max_selections=1,
            now=10.0,
        )
        btc = next(audit for audit in result.audits if audit.pair == "BTCUSDT")
        eth = next(audit for audit in result.audits if audit.pair == "ETHUSDT")
        assert btc.is_phantom is True
        assert btc.hard_block_decision.is_blocked is False
        assert btc.selection_entry is not None
        assert btc.selection_entry.outcome == SelectionOutcome.REJECTED_RANKING
        assert btc.explainability.dominant_feature_keys == ("momentum", "flow")
        assert btc.explainability.dominant_score_penalty_ids == ("stale", "spread")
        assert btc.explainability.dominant_size_penalty_ids == ("size_stale",)
        assert btc.explainability.selection_outcome_code == "rejected_ranking"
        assert "selection=rejected_ranking" in btc.explainability.summary
        assert "cost=0.2000" in btc.explainability.summary
        assert "ce=0.1000" in btc.explainability.summary
        assert btc.economics.expected_cost == pytest.approx(0.2)
        assert btc.economics.expected_ce == pytest.approx(0.1)
        assert btc.economics.penalized_score == pytest.approx(0.3)
        assert btc.economics.final_size_multiplier == pytest.approx(0.1)
        assert btc.economics.phantom_trade is True
        assert btc.economics.phantom_reason_code == "PHANTOM_RISK"
        assert btc.economics.selection_outcome_code == "rejected_ranking"
        assert eth.selection_entry is not None
        assert eth.selection_entry.outcome == SelectionOutcome.SELECTED

    def test_runtime_explicit_hard_block_never_reaches_ranking(self):
        runtime = ScoringRuntime(_registry())
        result = runtime.run_round(
            (
                _candidate(
                    engine_id="eng_a",
                    pair="BTCUSDT",
                    raw_features={"momentum": 1.0, "flow": 1.0},
                    expected_ce=0.2,
                    expected_cost=0.1,
                    projected_size=10.0,
                    projected_loss=1.0,
                    projected_beta_impact=0.01,
                    cluster_id="majors",
                    blocker_conditions=BlockerCondition(is_pair_suspended=True),
                ),
            ),
            portfolio=PortfolioState(
                remaining_gross_capacity=100.0,
                remaining_loss_capacity=100.0,
                remaining_beta_capacity=1.0,
                remaining_cluster_capacity={"majors": 100.0},
            ),
            max_selections=1,
            now=20.0,
        )
        audit = result.audits[0]
        assert audit.hard_block_decision.is_blocked is True
        assert audit.explainability.hard_block_codes == ("HB_PAIR_SUSPENDED",)
        assert "hard_block=HB_PAIR_SUSPENDED" in audit.explainability.summary
        assert audit.economics.hard_blocked is True
        assert audit.economics.selection_outcome_code == ""
        assert audit.selection_entry is None
        assert result.candidate_pool.pool_size == 0

    def test_runtime_respects_portfolio_rejection_without_hiding_it_as_hard_block(self):
        runtime = ScoringRuntime(_registry())
        result = runtime.run_round(
            (
                _candidate(
                    engine_id="eng_a",
                    pair="BTCUSDT",
                    raw_features={"momentum": 1.1, "flow": 0.9},
                    expected_ce=0.2,
                    expected_cost=0.05,
                    projected_size=150.0,
                    projected_loss=10.0,
                    projected_beta_impact=0.05,
                    cluster_id="majors",
                ),
            ),
            portfolio=PortfolioState(
                remaining_gross_capacity=100.0,
                remaining_loss_capacity=100.0,
                remaining_beta_capacity=1.0,
                remaining_cluster_capacity={"majors": 100.0},
            ),
            max_selections=1,
            now=30.0,
        )
        audit = result.audits[0]
        assert audit.hard_block_decision.is_blocked is False
        assert audit.portfolio_result is not None
        assert audit.portfolio_result.verdict.value == "rejected_exposure"
        assert audit.selection_entry is not None
        assert audit.selection_entry.outcome == SelectionOutcome.REJECTED_PORTFOLIO
        assert audit.explainability.portfolio_verdict_code == "rejected_exposure"
        assert audit.explainability.selection_outcome_code == "rejected_portfolio"
        assert audit.economics.portfolio_verdict_code == "rejected_exposure"
        assert audit.economics.selection_outcome_code == "rejected_portfolio"
        assert audit.economics.ranking_score is not None

    def test_runtime_projects_market_physics_scores_without_changing_selection_logic(self):
        runtime = ScoringRuntime(_registry())
        result = runtime.run_round(
            (
                _candidate(
                    engine_id="eng_a",
                    pair="BTCUSDT",
                    raw_features={"momentum": 1.1, "flow": 0.9},
                    expected_ce=0.2,
                    expected_cost=0.05,
                    projected_size=50.0,
                    projected_loss=5.0,
                    projected_beta_impact=0.05,
                    cluster_id="majors",
                    execution_fragility=0.8,
                    market_toxicity=0.8,
                    spread_regime_penalty=0.6,
                ),
            ),
            portfolio=PortfolioState(
                remaining_gross_capacity=1000.0,
                remaining_loss_capacity=100.0,
                remaining_beta_capacity=1.0,
                remaining_cluster_capacity={"majors": 500.0},
            ),
            max_selections=1,
            now=35.0,
        )
        audit = result.audits[0]
        assert audit.selection_entry is not None
        assert audit.selection_entry.outcome == SelectionOutcome.SELECTED
        assert audit.explainability.physics_pressure_state == "elevated"
        assert "physics=elevated" in audit.explainability.summary
        assert audit.economics.physics_pressure_state == "elevated"
        assert audit.economics.execution_survivability_score < 1.0
        assert audit.economics.micro_friction_score > 0.0

    def test_runtime_is_reproducible_for_identical_round_inputs(self):
        candidates = (
            _candidate(
                engine_id="eng_a",
                pair="BTCUSDT",
                raw_features={"momentum": 1.2, "flow": 0.8},
                expected_ce=0.2,
                expected_cost=0.05,
                projected_size=20.0,
                projected_loss=2.0,
                projected_beta_impact=0.02,
                cluster_id="majors",
            ),
            _candidate(
                engine_id="eng_b",
                pair="ETHUSDT",
                raw_features={"momentum": 0.8, "flow": 0.7},
                expected_ce=0.15,
                expected_cost=0.07,
                projected_size=20.0,
                projected_loss=2.0,
                projected_beta_impact=0.02,
                cluster_id="alts",
            ),
        )
        portfolio = PortfolioState(
            remaining_gross_capacity=1000.0,
            remaining_loss_capacity=100.0,
            remaining_beta_capacity=1.0,
            remaining_cluster_capacity={"majors": 500.0, "alts": 500.0},
        )
        result_a = ScoringRuntime(_registry()).run_round(candidates, portfolio=portfolio, max_selections=1, now=40.0)
        result_b = ScoringRuntime(_registry()).run_round(candidates, portfolio=portfolio, max_selections=1, now=40.0)

        assert result_a.selection_result.entries == result_b.selection_result.entries
        assert tuple((audit.pair, audit.score_payload.raw_score) for audit in result_a.audits) == tuple(
            (audit.pair, audit.score_payload.raw_score) for audit in result_b.audits
        )

    def test_runtime_requires_explicit_now(self):
        runtime = ScoringRuntime(_registry())

        with pytest.raises(ValueError, match="requires explicit now"):
            runtime.run_round(
                (
                    _candidate(
                        engine_id="eng_a",
                        pair="BTCUSDT",
                        raw_features={"momentum": 1.0, "flow": 1.0},
                        expected_ce=0.2,
                        expected_cost=0.1,
                        projected_size=10.0,
                        projected_loss=1.0,
                        projected_beta_impact=0.01,
                        cluster_id="majors",
                    ),
                ),
                portfolio=PortfolioState(
                    remaining_gross_capacity=100.0,
                    remaining_loss_capacity=100.0,
                    remaining_beta_capacity=1.0,
                    remaining_cluster_capacity={"majors": 100.0},
                ),
                max_selections=1,
            )

    def test_runtime_rejects_blank_scoring_version_candidate(self):
        with pytest.raises(ValueError, match="scoring_version must be non-empty"):
            _candidate(
                engine_id="eng_a",
                pair="BTCUSDT",
                raw_features={"momentum": 1.0, "flow": 1.0},
                expected_ce=0.2,
                expected_cost=0.1,
                projected_size=10.0,
                projected_loss=1.0,
                projected_beta_impact=0.01,
                cluster_id="majors",
                scoring_version="   ",
            )

    def test_runtime_rejects_duplicate_candidate_keys(self):
        runtime = ScoringRuntime(_registry())
        candidate = _candidate(
            engine_id="eng_a",
            pair="BTCUSDT",
            raw_features={"momentum": 1.0, "flow": 1.0},
            expected_ce=0.2,
            expected_cost=0.1,
            projected_size=10.0,
            projected_loss=1.0,
            projected_beta_impact=0.01,
            cluster_id="majors",
        )

        with pytest.raises(ValueError, match="duplicate candidate key eng_a:BTCUSDT"):
            runtime.run_round(
                (candidate, candidate),
                portfolio=PortfolioState(
                    remaining_gross_capacity=100.0,
                    remaining_loss_capacity=100.0,
                    remaining_beta_capacity=1.0,
                    remaining_cluster_capacity={"majors": 100.0},
                ),
                max_selections=1,
                now=50.0,
            )

    def test_runtime_fails_explicitly_on_candidate_pool_desync(self, monkeypatch):
        runtime = ScoringRuntime(_registry())

        def _broken_build_candidate_pool(
            all_candidates: tuple[RankingCandidate, ...],
            blocked_keys: frozenset[tuple[str, str]],
        ) -> CandidatePool:
            return CandidatePool(
                candidates=(
                    RankingCandidate(
                        engine_id="ghost_engine",
                        pair="BTCUSDT",
                        penalized_score=1.0,
                        size_multiplier=1.0,
                        expected_cost=0.1,
                        expected_ce=0.2,
                        projected_risk=0.0,
                        cluster_id="majors",
                    ),
                ),
                total_submitted=len(all_candidates),
                hard_blocked=0,
            )

        monkeypatch.setattr(scoring_runtime_module, "build_candidate_pool", _broken_build_candidate_pool)

        with pytest.raises(
            ValueError,
            match="ScoringRuntime.run_round candidate pool references unknown candidate ghost_engine:BTCUSDT",
        ):
            runtime.run_round(
                (
                    _candidate(
                        engine_id="eng_a",
                        pair="BTCUSDT",
                        raw_features={"momentum": 1.0, "flow": 1.0},
                        expected_ce=0.2,
                        expected_cost=0.1,
                        projected_size=10.0,
                        projected_loss=1.0,
                        projected_beta_impact=0.01,
                        cluster_id="majors",
                    ),
                ),
                portfolio=PortfolioState(
                    remaining_gross_capacity=100.0,
                    remaining_loss_capacity=100.0,
                    remaining_beta_capacity=1.0,
                    remaining_cluster_capacity={"majors": 100.0},
                ),
                max_selections=1,
                now=60.0,
            )
