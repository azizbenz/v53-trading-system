from __future__ import annotations

from local_replay_runtime.governed_audit_evidence_index import (
    build_governed_audit_evidence_entry,
    build_governed_audit_evidence_index,
    build_governed_audit_evidence_projection,
)
from tests.support_paths import make_repo_scratch_dir


def test_governed_audit_evidence_index_marks_test_tmp_outputs_as_scratch_only() -> None:
    scratch = make_repo_scratch_dir("governed_audit_evidence_index_tests", "scratch_only")
    artifact_path = scratch / "artifact.json"
    artifact_path.write_text("{}", encoding="utf-8")

    entry = build_governed_audit_evidence_entry(
        rail_id="run-1:capital_bucket:400",
        artifact_kind="capital_profile",
        artifact_ref=str(artifact_path),
        audited_historical=True,
        promotion_grade=True,
    )
    index = build_governed_audit_evidence_index(
        run_id="run-1",
        source_root=scratch,
        entries=(entry,),
    )

    assert entry.evidence_class.value == "SCRATCH_ONLY"
    assert "EVIDENCE_UNDER_TEST_TMP" in entry.reasons
    assert index.artifact_hash == index.artifact_hash_sha256()


def test_governed_audit_evidence_index_allows_non_test_promotion_grade_when_explicit() -> None:
    entry = build_governed_audit_evidence_entry(
        rail_id="run-2:engine:engine_a",
        artifact_kind="engine_promotion",
        artifact_ref="E:/audited/engine_promotion/engine_a/run-2.json",
        audited_historical=True,
        promotion_grade=True,
    )

    assert entry.evidence_class.value == "PROMOTION_GRADE_EVIDENCE"


def test_governed_audit_evidence_projection_counts_entries_and_fails_closed() -> None:
    entries = (
        build_governed_audit_evidence_entry(
            rail_id="run-3:run_manifest",
            artifact_kind="run_manifest",
            artifact_ref="E:/audited/run_manifest.json",
            audited_historical=True,
        ),
        build_governed_audit_evidence_entry(
            rail_id="run-3:operator:refusal_ledger",
            artifact_kind="refusal_ledger",
            artifact_ref="E:/scratch/refusal_ledger.jsonl",
        ),
    )
    index = build_governed_audit_evidence_index(
        run_id="run-3",
        source_root="E:/scratch",
        entries=entries,
    )

    projection = build_governed_audit_evidence_projection(
        index=index,
        index_path="E:/scratch/reports/governed_audit_evidence_index.json",
    )

    assert projection["governed_evidence_status"] == "EVIDENCE_AUDIT_NOT_CONFIRMED"
    assert projection["audited_evidence_count"] == 1
    assert projection["scratch_only_evidence_count"] == 1
    assert projection["promotion_grade_evidence_count"] == 0
    assert projection["run_manifest_evidence_class"] == "AUDITED_HISTORICAL_EVIDENCE"
    assert projection["refusal_ledger_evidence_class"] == "SCRATCH_ONLY"
    assert projection["trade_detail_ledger_evidence_class"] == "EVIDENCE_CLASS_NOT_PROVEN"
    assert "EVIDENCE_AUDIT_NOT_CONFIRMED" in projection["evidence_audit_blocker_codes"]
