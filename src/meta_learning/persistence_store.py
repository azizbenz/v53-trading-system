"""Append-only persistence helpers for the governed Build-9X layer."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from interface_contracts.atomic_io import atomic_write_text
from meta_learning.contracts import (
    CandidateRecord,
    DiagnosticRecord,
    ExportBundleRecord,
    HypothesisRecord,
    LearningEventRecord,
    LearningMemoryRecord,
    MetaLearningReviewBundle,
    ReviewRecord,
)
from meta_learning.retention_policy import (
    diagnostic_or_hypothesis_retention,
    export_bundle_retention,
    review_or_promotion_retention,
)


_DIAGNOSTIC_FILE = "diagnostic_records.jsonl"
_HYPOTHESIS_FILE = "hypothesis_records.jsonl"
_CANDIDATE_FILE = "candidate_records.jsonl"
_REVIEW_FILE = "review_records.jsonl"
_EVENT_FILE = "learning_events.jsonl"
_EXPORT_BUNDLE_FILE = "export_bundle_records.jsonl"
_MEMORY_FILE = "learning_memory_records.jsonl"


def _checksum(payload: object) -> str:
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class AppendOnlyMetaLearningStore:
    """Persist Build-9X records as append-only JSONL artifacts."""

    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir
        self._state_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, filename: str) -> Path:
        return self._state_dir / filename

    def _append_jsonl(self, filename: str, payload: dict[str, object]) -> Path:
        path = self._path(filename)
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        line = json.dumps(payload, ensure_ascii=False, default=str)
        if existing and not existing.endswith("\n"):
            existing += "\n"
        atomic_write_text(path, existing + line + "\n")
        return path

    def read_records(self, filename: str) -> tuple[dict[str, object], ...]:
        path = self._path(filename)
        if not path.exists():
            return ()
        records: list[dict[str, object]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            records.append(json.loads(stripped))
        return tuple(records)

    def find_records_by_entity_id(
        self,
        filename: str,
        entity_id: str,
    ) -> tuple[dict[str, object], ...]:
        return tuple(
            record
            for record in self.read_records(filename)
            if str(record.get("entity_id", "")) == entity_id
        )

    def _existing_event_ids(self) -> set[str]:
        return {
            str(record.get("event_id", ""))
            for record in self.read_records(_EVENT_FILE)
            if record.get("event_id")
        }

    def _append_event_once(
        self,
        payload: LearningEventRecord,
        *,
        existing_event_ids: set[str],
    ) -> None:
        if payload.event_id in existing_event_ids:
            return
        self._append_jsonl(
            _EVENT_FILE,
            payload.model_dump(mode="json"),
        )
        existing_event_ids.add(payload.event_id)

    def append_review_bundle(self, bundle: MetaLearningReviewBundle) -> None:
        """Persist the full Build-9X review bundle into append-only ledgers."""

        existing_event_ids = self._existing_event_ids()
        review_open = not bundle.review_decisions or any(
            decision.review_state.value in {"pending", "in_review", "needs_revision"}
            for decision in bundle.review_decisions
        )
        replay_open = any(
            candidate.governance_stage.value in {"ready_for_replay", "replay_running"}
            for candidate in bundle.candidates
        )
        for diagnostic in bundle.diagnostics:
            retention_until, retention_policy = diagnostic_or_hypothesis_retention(
                diagnostic.created_at,
            )
            record = DiagnosticRecord(
                entity_id=diagnostic.diagnostic_id,
                correlation_id=bundle.correlation_id,
                retention_until=retention_until,
                retention_policy=retention_policy,
                diagnostic=diagnostic,
            )
            self._append_jsonl(
                _DIAGNOSTIC_FILE,
                record.model_dump(mode="json"),
            )
            self._append_event_once(
                LearningEventRecord(
                    event_id=f"{diagnostic.diagnostic_id}:created",
                    entity_kind="diagnostic",
                    entity_id=diagnostic.diagnostic_id,
                    correlation_id=bundle.correlation_id,
                    event_type="diagnostic_created",
                    payload_ref=diagnostic.diagnostic_id,
                    payload_checksum=_checksum(diagnostic.model_dump(mode="json")),
                    to_state="open",
                    retention_until=retention_until,
                    retention_policy=retention_policy,
                ),
                existing_event_ids=existing_event_ids,
            )

        for hypothesis in bundle.hypotheses:
            retention_until, retention_policy = diagnostic_or_hypothesis_retention(
                hypothesis.created_at,
            )
            record = HypothesisRecord(
                entity_id=hypothesis.hypothesis_id,
                correlation_id=bundle.correlation_id,
                retention_until=retention_until,
                retention_policy=retention_policy,
                hypothesis=hypothesis,
            )
            self._append_jsonl(
                _HYPOTHESIS_FILE,
                record.model_dump(mode="json"),
            )
            self._append_event_once(
                LearningEventRecord(
                    event_id=f"{hypothesis.hypothesis_id}:registered",
                    entity_kind="hypothesis",
                    entity_id=hypothesis.hypothesis_id,
                    correlation_id=bundle.correlation_id,
                    event_type="hypothesis_registered",
                    payload_ref=hypothesis.hypothesis_id,
                    payload_checksum=_checksum(hypothesis.model_dump(mode="json")),
                    to_state="draft",
                    retention_until=retention_until,
                    retention_policy=retention_policy,
                ),
                existing_event_ids=existing_event_ids,
            )

        for candidate in bundle.candidates:
            retention_until, retention_policy = review_or_promotion_retention(
                candidate.created_at,
            )
            record = CandidateRecord(
                entity_id=candidate.candidate_id,
                correlation_id=bundle.correlation_id,
                retention_until=retention_until,
                retention_policy=retention_policy,
                candidate=candidate,
            )
            self._append_jsonl(
                _CANDIDATE_FILE,
                record.model_dump(mode="json"),
            )
            self._append_event_once(
                LearningEventRecord(
                    event_id=f"{candidate.candidate_id}:prepared",
                    entity_kind="candidate",
                    entity_id=candidate.candidate_id,
                    correlation_id=bundle.correlation_id,
                    event_type="candidate_prepared",
                    payload_ref=candidate.candidate_id,
                    payload_checksum=_checksum(candidate.model_dump(mode="json")),
                    to_state="prepared",
                    retention_until=retention_until,
                    retention_policy=retention_policy,
                ),
                existing_event_ids=existing_event_ids,
            )

        review_entity_id = bundle.review_export.export_ref or (
            f"{bundle.correlation_id}:review_export"
        )
        review_retention_until, review_retention_policy = review_or_promotion_retention(
            bundle.review_decisions[-1].created_at
            if bundle.review_decisions
            else bundle.memory_record.created_at
        )
        review_record = ReviewRecord(
            entity_id=review_entity_id,
            correlation_id=bundle.correlation_id,
            actor=bundle.review_decisions[-1].actor if bundle.review_decisions else "system_build9x",
            retention_until=review_retention_until,
            retention_policy=review_retention_policy,
            review_export=bundle.review_export,
            capacity_snapshot=bundle.capacity_snapshot,
            review_decisions=bundle.review_decisions,
            archive_eligibility=bundle.archive_eligibility,
            lifecycle_transitions=bundle.lifecycle_transitions,
        )
        self._append_jsonl(
            _REVIEW_FILE,
            review_record.model_dump(mode="json"),
        )
        review_export_checksum = _checksum(bundle.review_export.model_dump(mode="json"))
        self._append_event_once(
            LearningEventRecord(
                event_id=f"{review_entity_id}:exported:{review_export_checksum}",
                entity_kind="review",
                entity_id=review_entity_id,
                correlation_id=bundle.correlation_id,
                event_type="review_exported",
                payload_ref=review_entity_id,
                payload_checksum=review_export_checksum,
                to_state="review_exported",
                retention_until=review_retention_until,
                retention_policy=review_retention_policy,
            ),
            existing_event_ids=existing_event_ids,
        )
        for decision in bundle.review_decisions:
            decision_retention_until, decision_retention_policy = review_or_promotion_retention(
                decision.created_at,
            )
            self._append_event_once(
                LearningEventRecord(
                    event_id=decision.decision_id,
                    entity_kind="review_decision",
                    entity_id=decision.review_entity_id,
                    correlation_id=decision.correlation_id,
                    event_type="review_decision_recorded",
                    actor=decision.actor,
                    payload_ref=decision.decision_id,
                    payload_checksum=_checksum(decision.model_dump(mode="json")),
                    to_state=decision.review_state.value,
                    reason=decision.verdict,
                    retention_until=decision_retention_until,
                    retention_policy=decision_retention_policy,
                ),
                existing_event_ids=existing_event_ids,
            )
        if (
            bundle.capacity_snapshot is not None
            and bundle.capacity_snapshot.backpressure_signal_key
        ):
            event_retention_until, event_retention_policy = review_or_promotion_retention(
                bundle.memory_record.created_at,
            )
            capacity_checksum = _checksum(bundle.capacity_snapshot.model_dump(mode="json"))
            self._append_event_once(
                LearningEventRecord(
                    event_id=f"{review_entity_id}:capacity_backpressure:{capacity_checksum}",
                    entity_kind="capacity",
                    entity_id=review_entity_id,
                    correlation_id=bundle.correlation_id,
                    event_type=bundle.capacity_snapshot.backpressure_signal_key,
                    payload_ref=review_entity_id,
                    payload_checksum=capacity_checksum,
                    to_state=bundle.capacity_snapshot.capture_mode.value,
                    reason=", ".join(bundle.capacity_snapshot.blocking_reasons),
                    retention_until=event_retention_until,
                    retention_policy=event_retention_policy,
                ),
                existing_event_ids=existing_event_ids,
            )
        for transition in bundle.lifecycle_transitions:
            transition_retention_until, transition_retention_policy = review_or_promotion_retention(
                transition.created_at,
            )
            self._append_event_once(
                LearningEventRecord(
                    event_id=transition.transition_id,
                    entity_kind=transition.entity_kind,
                    entity_id=transition.entity_id,
                    correlation_id=transition.correlation_id,
                    event_type=f"{transition.entity_kind}_state_changed",
                    actor=transition.actor,
                    payload_ref=transition.transition_id,
                    payload_checksum=_checksum(transition.model_dump(mode="json")),
                    from_state=transition.from_state,
                    to_state=transition.to_state,
                    reason=transition.reason,
                    retention_until=transition_retention_until,
                    retention_policy=transition_retention_policy,
                ),
                existing_event_ids=existing_event_ids,
            )
        archive_actor = bundle.review_decisions[-1].actor if bundle.review_decisions else "system_build9x"
        for entry in bundle.archive_eligibility:
            if entry.archived_at is None:
                continue
            archive_retention_until, archive_retention_policy = review_or_promotion_retention(
                entry.archived_at,
            )
            self._append_event_once(
                LearningEventRecord(
                    event_id=f"{entry.entity_kind}:{entry.entity_id}:archived:{entry.archived_at.isoformat()}",
                    entity_kind=entry.entity_kind,
                    entity_id=entry.entity_id,
                    correlation_id=entry.correlation_id,
                    event_type=f"{entry.entity_kind}_archived",
                    actor=archive_actor,
                    payload_ref=entry.entity_id,
                    payload_checksum=_checksum(entry.model_dump(mode="json")),
                    to_state="archived",
                    reason=entry.retention_policy,
                    retention_until=archive_retention_until,
                    retention_policy=archive_retention_policy,
                ),
                existing_event_ids=existing_event_ids,
            )

        for replay_bundle in bundle.replay_bundles:
            retention_until, retention_policy, retention_locked = export_bundle_retention(
                replay_bundle.exported_at,
                review_open=review_open,
                replay_open=replay_open,
            )
            record = ExportBundleRecord(
                entity_id=replay_bundle.bundle_id,
                correlation_id=bundle.correlation_id,
                retention_until=retention_until,
                retention_policy=retention_policy,
                retention_locked=retention_locked,
                replay_bundle=replay_bundle,
            )
            self._append_jsonl(
                _EXPORT_BUNDLE_FILE,
                record.model_dump(mode="json"),
            )
            self._append_event_once(
                LearningEventRecord(
                    event_id=f"{replay_bundle.bundle_id}:exported",
                    entity_kind="replay_bundle",
                    entity_id=replay_bundle.bundle_id,
                    correlation_id=bundle.correlation_id,
                    event_type="replay_bundle_exported",
                    payload_ref=replay_bundle.bundle_id,
                    payload_checksum=replay_bundle.bundle_checksum,
                    to_state="exported",
                    retention_until=retention_until,
                    retention_policy=retention_policy,
                ),
                existing_event_ids=existing_event_ids,
            )

        memory_record = bundle.memory_record
        if not memory_record.record_id:
            memory_record = memory_record.model_copy(
                update={"record_id": f"{bundle.correlation_id}:memory_record"}
            )
        memory_retention_until, memory_retention_policy = review_or_promotion_retention(
            memory_record.created_at,
        )
        self._append_jsonl(
            _MEMORY_FILE,
            memory_record.model_dump(mode="json"),
        )
        memory_checksum = _checksum(memory_record.model_dump(mode="json"))
        self._append_event_once(
            LearningEventRecord(
                event_id=f"{memory_record.record_id}:recorded:{memory_checksum}",
                entity_kind="memory",
                entity_id=memory_record.record_id,
                correlation_id=bundle.correlation_id,
                event_type="memory_recorded",
                payload_ref=memory_record.record_id,
                payload_checksum=memory_checksum,
                to_state=memory_record.verdict or "recorded",
                retention_until=memory_retention_until,
                retention_policy=memory_retention_policy,
            ),
            existing_event_ids=existing_event_ids,
        )


__all__ = [
    "AppendOnlyMetaLearningStore",
    "_DIAGNOSTIC_FILE",
    "_HYPOTHESIS_FILE",
    "_CANDIDATE_FILE",
    "_REVIEW_FILE",
    "_EVENT_FILE",
    "_EXPORT_BUNDLE_FILE",
    "_MEMORY_FILE",
]
