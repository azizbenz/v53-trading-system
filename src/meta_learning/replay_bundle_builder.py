"""Build governed replay handoff bundles from Build-9X candidates."""

from __future__ import annotations

import hashlib
import importlib
import json
from types import ModuleType

from meta_learning.enums import CandidateKind
from meta_learning.contracts import (
    ImprovementCandidate,
    LearningHypothesis,
    ReplayComparisonProtocol,
    ReplayExportBundle,
    TradeLearningInput,
)


_FEATURE_SCHEMA_VERSION = "v53.feature_schema.v1"
_FORMULA_SCHEMA_VERSION = "v53.formula_schema.v1"
_REGIME_LOGIC_VERSION = "v53.regime_logic.v1"
_COST_MODEL_VERSION = "v53.cost_model.v1"


def _local_replay_runtime() -> ModuleType:
    return importlib.import_module("local_replay_runtime")


def _tests_required(
    candidate: ImprovementCandidate,
    hypotheses: tuple[LearningHypothesis, ...],
) -> tuple[str, ...]:
    categories = {hypothesis.category for hypothesis in hypotheses}
    tests = {
        "tests/test_meta_learning/test_contracts.py",
        "tests/test_meta_learning/test_build9x_integration.py",
    }
    if "trace_coverage" in categories:
        tests.add("tests/test_meta_learning/test_build9x_diagnostics.py")
    if {"cost_drift", "sterilization"} & categories:
        tests.add("tests/test_meta_learning/test_build9x_candidates.py")
    if "near_miss" in categories:
        tests.add("tests/test_meta_learning/test_near_miss_and_candidates.py")
    if candidate.kind == CandidateKind.BUILD14_ENABLER:
        tests.add("tests/test_meta_learning/test_governance_edge_cases.py")
    return tuple(sorted(tests))


def _comparison_protocol(
    candidate: ImprovementCandidate,
    hypotheses: tuple[LearningHypothesis, ...],
    replay_scope: str,
) -> ReplayComparisonProtocol:
    categories = {hypothesis.category for hypothesis in hypotheses}
    metrics = ["ce_net", "dtr_coverage", "sterilization_rate", "edge_net"]
    if "cost_drift" in categories:
        metrics.append("expected_vs_realized_cost")
    if "near_miss" in categories:
        metrics.append("near_miss_conversion_rate")
    rejection_criteria = [
        "candidate introduces an ungoverned live mutation path",
        "candidate degrades Build-9 observability or DTR coverage",
        "candidate increases cost drift without offsetting edge",
    ]
    target_components = tuple(
        sorted(
            {
                hypothesis.target_component
                for hypothesis in hypotheses
                if hypothesis.target_component
            }
        )
    )
    signal_families = tuple(
        sorted(
            {
                hypothesis.signal_family
                for hypothesis in hypotheses
                if hypothesis.signal_family
            }
        )
    )
    expected_replay_evidence = tuple(
        dict.fromkeys(
            evidence
            for hypothesis in hypotheses
            for evidence in hypothesis.expected_replay_evidence
        )
    )
    expected_shadow_evidence = tuple(
        dict.fromkeys(
            evidence
            for hypothesis in hypotheses
            for evidence in hypothesis.expected_shadow_evidence
        )
    )
    return ReplayComparisonProtocol(
        protocol_id=f"{candidate.candidate_id}:comparison_protocol",
        candidate_id=candidate.candidate_id,
        evaluation_scope=replay_scope,
        target_components=target_components,
        signal_families=signal_families,
        expected_replay_evidence=expected_replay_evidence,
        expected_shadow_evidence=expected_shadow_evidence,
        comparison_metrics=tuple(metrics),
        rejection_criteria=tuple(rejection_criteria),
    )


def _shared_core_hash(trade_input: TradeLearningInput) -> str:
    payload = (
        f"{trade_input.source_version}|"
        f"{trade_input.strategy_classification.value}|"
        f"{trade_input.engine_id.value}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _contracts_version(hypotheses: tuple[LearningHypothesis, ...]) -> str:
    versions = tuple(
        dict.fromkeys(
            hypothesis.contracts_version
            for hypothesis in hypotheses
            if hypothesis.contracts_version
        )
    )
    if not versions:
        return "build9x.contracts.v1"
    if len(versions) == 1:
        return versions[0]
    return "+".join(versions)


def _resolve_replay_scope(
    candidate: ImprovementCandidate,
    candidate_hypotheses: tuple[LearningHypothesis, ...],
    trade_input: TradeLearningInput,
) -> str:
    return candidate.replay_scope or next(
        (
            hypothesis.required_replay_scope
            for hypothesis in candidate_hypotheses
            if hypothesis.required_replay_scope
        ),
        f"{trade_input.profile.value}:{trade_input.pair}:{trade_input.engine_id.value}:local_replay",
    )


def _build_payload_refs(
    *,
    candidate: ImprovementCandidate,
    diagnostic_ids: tuple[str, ...],
    review_export_ref: str,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                review_export_ref,
                f"{candidate.candidate_id}:feature_bridge",
                f"{candidate.candidate_id}:parity_diagnostics",
                f"{candidate.candidate_id}:replay_metrics",
                f"{candidate.candidate_id}:replay_dtr",
                *diagnostic_ids,
                *candidate.hypothesis_ids,
                candidate.candidate_id,
            }
        )
    )


def _build_replay_bundle_for_candidate(
    *,
    candidate: ImprovementCandidate,
    trade_input: TradeLearningInput,
    candidate_hypotheses: tuple[LearningHypothesis, ...],
    shared_core_hash: str,
    review_export_ref: str,
    dataset_ref: object | None,
    clock_ref: object | None,
    local_replay_runtime: ModuleType,
) -> ReplayExportBundle:
    replay_scope = _resolve_replay_scope(candidate, candidate_hypotheses, trade_input)
    tests_required = candidate.tests_required or _tests_required(
        candidate,
        candidate_hypotheses,
    )
    comparison_protocol = _comparison_protocol(
        candidate,
        candidate_hypotheses,
        replay_scope,
    )
    replay_request = local_replay_runtime.LocalReplayRequest(
        correlation_id=trade_input.correlation_id,
        profile=trade_input.profile,
        strategy_classification=trade_input.strategy_classification,
        lineage_version=f"{trade_input.source_version}.build9x",
        replay_reason=candidate.summary,
    )
    diagnostic_ids = tuple(
        diagnostic_id
        for hypothesis in candidate_hypotheses
        for diagnostic_id in hypothesis.diagnostic_ids
    )
    target_components = tuple(
        sorted(
            {
                hypothesis.target_component
                for hypothesis in candidate_hypotheses
                if hypothesis.target_component
            }
        )
    )
    expected_shadow_evidence = tuple(
        dict.fromkeys(
            evidence
            for hypothesis in candidate_hypotheses
            for evidence in hypothesis.expected_shadow_evidence
        )
    )
    execution_plan = local_replay_runtime.LocalReplayOrchestrator.prepare_bundle(
        replay_request,
        artifact_id=f"{candidate.candidate_id}:artifact",
        strategy_version=trade_input.source_version,
        payload_refs=_build_payload_refs(
            candidate=candidate,
            diagnostic_ids=diagnostic_ids,
            review_export_ref=review_export_ref,
        ),
        dataset_ref=dataset_ref,
        clock_ref=clock_ref,
        diagnostic_ids=diagnostic_ids,
        hypothesis_ids=candidate.hypothesis_ids,
        candidate_ids=(candidate.candidate_id,),
        target_components=target_components,
        expected_shadow_evidence=expected_shadow_evidence,
        review_export_ref=review_export_ref,
        feature_bridge_ref=f"{candidate.candidate_id}:feature_bridge",
        parity_diagnostics_ref=f"{candidate.candidate_id}:parity_diagnostics",
        replay_metrics_ref=f"{candidate.candidate_id}:replay_metrics",
        replay_dtr_ref=f"{candidate.candidate_id}:replay_dtr",
        notes=f"Build-9X governed replay handoff for {candidate.candidate_id}",
    )
    checksum_payload = json.dumps(
        {
            "execution_plan": execution_plan.model_dump(mode="json"),
            "comparison_protocol": comparison_protocol.model_dump(mode="json"),
            "tests_required": tests_required,
        },
        sort_keys=True,
        default=str,
    )
    return ReplayExportBundle(
        bundle_id=f"{candidate.candidate_id}:replay_bundle",
        candidate_id=candidate.candidate_id,
        hypothesis_ids=candidate.hypothesis_ids,
        source_version=trade_input.source_version,
        contracts_version=_contracts_version(candidate_hypotheses),
        feature_schema_version=_FEATURE_SCHEMA_VERSION,
        formula_schema_version=_FORMULA_SCHEMA_VERSION,
        regime_logic_version=_REGIME_LOGIC_VERSION,
        cost_model_version=_COST_MODEL_VERSION,
        replay_scope=replay_scope,
        tests_required=tests_required,
        comparison_protocol=comparison_protocol,
        execution_plan=execution_plan,
        shared_core_hash=shared_core_hash,
        bundle_checksum=hashlib.sha256(checksum_payload.encode("utf-8")).hexdigest(),
    )


def build_replay_export_bundles(
    trade_input: TradeLearningInput,
    hypotheses: tuple[LearningHypothesis, ...],
    candidates: tuple[ImprovementCandidate, ...],
    *,
    review_export_ref: str,
    dataset_ref: object | None = None,
    clock_ref: object | None = None,
) -> tuple[ReplayExportBundle, ...]:
    """Build deterministic replay handoff bundles for Build-9X candidates."""

    local_replay_runtime = _local_replay_runtime()
    hypotheses_by_id = {
        hypothesis.hypothesis_id: hypothesis for hypothesis in hypotheses
    }
    shared_core_hash = _shared_core_hash(trade_input)
    replay_bundles: list[ReplayExportBundle] = []

    for candidate in candidates:
        candidate_hypotheses = tuple(
            hypotheses_by_id[hypothesis_id]
            for hypothesis_id in candidate.hypothesis_ids
            if hypothesis_id in hypotheses_by_id
        )
        replay_bundles.append(
            _build_replay_bundle_for_candidate(
                candidate=candidate,
                trade_input=trade_input,
                candidate_hypotheses=candidate_hypotheses,
                shared_core_hash=shared_core_hash,
                review_export_ref=review_export_ref,
                dataset_ref=dataset_ref,
                clock_ref=clock_ref,
                local_replay_runtime=local_replay_runtime,
            )
        )

    return tuple(replay_bundles)


def enrich_candidates_with_replay_refs(
    candidates: tuple[ImprovementCandidate, ...],
    replay_bundles: tuple[ReplayExportBundle, ...],
) -> tuple[ImprovementCandidate, ...]:
    """Attach replay references and checks to candidates without mutating inputs."""

    bundles_by_candidate = {
        bundle.candidate_id: bundle for bundle in replay_bundles
    }
    enriched: list[ImprovementCandidate] = []

    for candidate in candidates:
        replay_bundle = bundles_by_candidate.get(candidate.candidate_id)
        if replay_bundle is None:
            enriched.append(candidate)
            continue
        enriched.append(
            candidate.model_copy(
                update={
                    "candidate_version": f"{candidate.candidate_id}.v1",
                    "tests_required": replay_bundle.tests_required,
                    "replay_scope": replay_bundle.replay_scope,
                    "replay_bundle_reference": replay_bundle.bundle_id,
                    "comparison_protocol_reference": replay_bundle.comparison_protocol.protocol_id,
                    "shared_core_hash": replay_bundle.shared_core_hash,
                    "validation_notes": replay_bundle.execution_plan.validation_notes,
                }
            )
        )

    return tuple(enriched)


__all__ = [
    "build_replay_export_bundles",
    "enrich_candidates_with_replay_refs",
]
