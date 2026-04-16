"""Canonical internal facade for the governed Build-9X layer."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from meta_learning.contracts import (
    CandidateRecord,
    DiagnosticRecord,
    DiagnosticResult,
    ExportBundleRecord,
    HypothesisRecord,
    ImprovementCandidate,
    LearningCapacitySnapshot,
    LearningEventRecord,
    LearningHypothesis,
    LearningMemoryRecord,
    MetaLearningReviewBundle,
    ReplayExportBundle,
    ReviewQueueEntry,
    ReviewRecord,
    TradeLearningInput,
)
from meta_learning.persistence_store import (
    AppendOnlyMetaLearningStore,
    _CANDIDATE_FILE,
    _DIAGNOSTIC_FILE,
    _EVENT_FILE,
    _EXPORT_BUNDLE_FILE,
    _HYPOTHESIS_FILE,
    _MEMORY_FILE,
    _REVIEW_FILE,
)
from meta_learning.review_queue import build_review_queue
from meta_learning.review_resolution import apply_human_review_resolution


@runtime_checkable
class MetaLearningFacadeProtocol(Protocol):
    def ingest_learning_input(self, payload: TradeLearningInput) -> str: ...
    def create_diagnostic(self, decision_id: str) -> DiagnosticResult: ...
    def register_hypothesis(self, diagnostic_id: str) -> LearningHypothesis | None: ...
    def prepare_candidate(self, hypothesis_id: str) -> ImprovementCandidate: ...
    def export_replay_bundle(self, candidate_id: str) -> ReplayExportBundle: ...
    def mark_review_decision(self, review_id: str, decision: str, actor_id: str, reason: str) -> str: ...
    def get_diagnostic(self, diagnostic_id: str) -> DiagnosticResult: ...
    def list_hypotheses(self, status: str | None = None) -> list[LearningHypothesis]: ...
    def get_candidate(self, candidate_id: str) -> ImprovementCandidate: ...
    def get_learning_history(self, entity_id: str) -> list[LearningMemoryRecord]: ...
    def get_review_queue(self) -> list[ReviewQueueEntry]: ...
    def get_learning_counters(self, run_id: str) -> LearningCapacitySnapshot | None: ...


class MetaLearningFacade(MetaLearningFacadeProtocol):
    """Façade that hides direct ledger/bundle manipulation behind canonical calls."""

    def __init__(
        self,
        *,
        state_dir: Path | None = None,
        bundles: Iterable[MetaLearningReviewBundle] = (),
    ) -> None:
        self._state_dir = state_dir
        self._store = AppendOnlyMetaLearningStore(state_dir) if state_dir is not None else None
        self._inputs: dict[str, TradeLearningInput] = {}
        self._bundles_by_key: dict[str, MetaLearningReviewBundle] = {}
        for bundle in bundles:
            self.attach_review_bundle(bundle)

    def attach_review_bundle(self, bundle: MetaLearningReviewBundle) -> None:
        self._bundles_by_key[bundle.correlation_id] = bundle
        self._bundles_by_key[bundle.review_export.export_ref] = bundle

    def ingest_learning_input(self, payload: TradeLearningInput) -> str:
        self._inputs[payload.correlation_id] = payload
        return payload.correlation_id

    def create_diagnostic(self, decision_id: str) -> DiagnosticResult:
        bundle = self._resolve_bundle(decision_id)
        if not bundle.diagnostics:
            raise ValueError(f"No diagnostic available for decision_id {decision_id}")
        return bundle.diagnostics[0]

    def register_hypothesis(self, diagnostic_id: str) -> LearningHypothesis | None:
        for hypothesis in self._all_hypotheses():
            if diagnostic_id in hypothesis.diagnostic_ids:
                return hypothesis
        return None

    def prepare_candidate(self, hypothesis_id: str) -> ImprovementCandidate:
        for candidate in self._all_candidates():
            if hypothesis_id in candidate.hypothesis_ids:
                return candidate
        raise ValueError(f"No candidate found for hypothesis_id {hypothesis_id}")

    def export_replay_bundle(self, candidate_id: str) -> ReplayExportBundle:
        for replay_bundle in self._all_replay_bundles():
            if replay_bundle.candidate_id == candidate_id:
                return replay_bundle
        raise ValueError(f"No replay bundle found for candidate_id {candidate_id}")

    def mark_review_decision(
        self,
        review_id: str,
        decision: str,
        actor_id: str,
        reason: str,
    ) -> str:
        bundle = self._resolve_bundle(review_id)
        updated_bundle = apply_human_review_resolution(
            bundle,
            actor=actor_id,
            resolution=decision,
            rationale=reason,
            state_dir=self._state_dir,
        )
        self.attach_review_bundle(updated_bundle)
        return updated_bundle.review_decisions[-1].decision_id

    def get_diagnostic(self, diagnostic_id: str) -> DiagnosticResult:
        diagnostics_by_id = self._diagnostics_by_id()
        if diagnostic_id not in diagnostics_by_id:
            raise ValueError(f"Unknown diagnostic_id {diagnostic_id}")
        return diagnostics_by_id[diagnostic_id]

    def list_hypotheses(self, status: str | None = None) -> list[LearningHypothesis]:
        hypotheses = list(self._hypotheses_by_id().values())
        if status is not None:
            hypotheses = [
                hypothesis
                for hypothesis in hypotheses
                if hypothesis.status.value == status
            ]
        return hypotheses

    def get_candidate(self, candidate_id: str) -> ImprovementCandidate:
        candidates_by_id = self._candidates_by_id()
        if candidate_id not in candidates_by_id:
            raise ValueError(f"Unknown candidate_id {candidate_id}")
        return candidates_by_id[candidate_id]

    def get_learning_history(self, entity_id: str) -> list[LearningMemoryRecord]:
        history: list[LearningMemoryRecord] = []
        if self._store is not None:
            for record in self._store.read_records(_MEMORY_FILE):
                memory_record = LearningMemoryRecord.model_validate(record)
                if entity_id in {
                    memory_record.record_id,
                    memory_record.diagnostic_id,
                    memory_record.hypothesis_id,
                    memory_record.candidate_id,
                }:
                    history.append(memory_record)
            for record in self._store.read_records(_EVENT_FILE):
                event = LearningEventRecord.model_validate(record)
                if event.entity_id != entity_id:
                    continue
                transition = (
                    f"{event.from_state}->{event.to_state}"
                    if event.from_state or event.to_state
                    else event.event_type
                )
                history.append(
                    LearningMemoryRecord(
                        record_id=f"{entity_id}:history:{event.event_id}",
                        correlation_id=event.correlation_id,
                        diagnostics_count=0,
                        hypothesis_count=0,
                        candidate_count=0,
                        verdict=event.reason or event.to_state or event.event_type,
                        rejection_reason=event.reason or None,
                        created_at=event.created_at,
                        archived=event.to_state == "archived",
                        summary=f"{event.entity_kind}:{transition}",
                    )
                )
        for bundle in self._unique_bundles():
            memory_record = bundle.memory_record
            if entity_id in {
                memory_record.record_id,
                memory_record.diagnostic_id,
                memory_record.hypothesis_id,
                memory_record.candidate_id,
            }:
                history.append(memory_record)
        return sorted(history, key=lambda record: (record.created_at, record.record_id))

    def get_review_queue(self) -> list[ReviewQueueEntry]:
        queue = build_review_queue(
            tuple(self._hypotheses_by_id().values()),
            tuple(self._diagnostics_by_id().values()),
        )
        return list(queue)

    def get_learning_counters(self, run_id: str) -> LearningCapacitySnapshot | None:
        bundle = self._bundles_by_key.get(run_id)
        if bundle is not None:
            return bundle.capacity_snapshot
        if self._store is None:
            return None
        review_records = self._latest_models(_REVIEW_FILE, ReviewRecord)
        for record in review_records.values():
            if record.correlation_id == run_id or record.entity_id == run_id:
                return record.capacity_snapshot
        return None

    def _resolve_bundle(self, key: str) -> MetaLearningReviewBundle:
        bundle = self._bundles_by_key.get(key)
        if bundle is not None:
            return bundle
        raise ValueError(f"Unknown review bundle key {key}")

    def _unique_bundles(self) -> tuple[MetaLearningReviewBundle, ...]:
        unique: dict[str, MetaLearningReviewBundle] = {}
        for bundle in self._bundles_by_key.values():
            unique[bundle.correlation_id] = bundle
        return tuple(unique.values())

    def _latest_models(self, filename: str, model_cls: type[BaseModel]) -> dict[str, object]:
        if self._store is None:
            return {}
        latest_by_id: dict[str, object] = {}
        for record in self._store.read_records(filename):
            model = model_cls.model_validate(record)
            latest_by_id[model.entity_id] = model
        return latest_by_id

    def _diagnostics_by_id(self) -> dict[str, DiagnosticResult]:
        diagnostics = {
            record.entity_id: record.diagnostic
            for record in self._latest_models(_DIAGNOSTIC_FILE, DiagnosticRecord).values()
        }
        for bundle in self._unique_bundles():
            for diagnostic in bundle.diagnostics:
                diagnostics[diagnostic.diagnostic_id] = diagnostic
        return diagnostics

    def _hypotheses_by_id(self) -> dict[str, LearningHypothesis]:
        hypotheses = {
            record.entity_id: record.hypothesis
            for record in self._latest_models(_HYPOTHESIS_FILE, HypothesisRecord).values()
        }
        for bundle in self._unique_bundles():
            for hypothesis in bundle.hypotheses:
                hypotheses[hypothesis.hypothesis_id] = hypothesis
        return hypotheses

    def _candidates_by_id(self) -> dict[str, ImprovementCandidate]:
        candidates = {
            record.entity_id: record.candidate
            for record in self._latest_models(_CANDIDATE_FILE, CandidateRecord).values()
        }
        for bundle in self._unique_bundles():
            for candidate in bundle.candidates:
                candidates[candidate.candidate_id] = candidate
        return candidates

    def _all_hypotheses(self) -> tuple[LearningHypothesis, ...]:
        return tuple(self._hypotheses_by_id().values())

    def _all_candidates(self) -> tuple[ImprovementCandidate, ...]:
        return tuple(self._candidates_by_id().values())

    def _all_replay_bundles(self) -> tuple[ReplayExportBundle, ...]:
        replay_bundles = {
            record.entity_id: record.replay_bundle
            for record in self._latest_models(_EXPORT_BUNDLE_FILE, ExportBundleRecord).values()
        }
        for bundle in self._unique_bundles():
            for replay_bundle in bundle.replay_bundles:
                replay_bundles[replay_bundle.bundle_id] = replay_bundle
        return tuple(replay_bundles.values())


__all__ = [
    "MetaLearningFacadeProtocol",
    "MetaLearningFacade",
]
