from __future__ import annotations

from cockpit.state_kill_proof import read_kill_proof

from ._operational_helpers import build_paths, cleanup_scratch, scratch_dir


def test_kill_proof_defaults_to_not_proven() -> None:
    scratch = scratch_dir("kill_proof_missing")
    try:
        paths = build_paths(scratch)
        snapshot = read_kill_proof(paths)
        assert snapshot.kill_switch_status == "NOT_PROVEN"
    finally:
        cleanup_scratch(scratch)


def test_kill_proof_promotes_valid_evidence_and_flags_corrupt_payload() -> None:
    scratch = scratch_dir("kill_proof_valid")
    try:
        paths = build_paths(scratch)
        proof_path = paths.service_dir / "kill_proof.json"
        proof_path.write_text('{"latency_ms": 500, "result": "halted"}', encoding="utf-8")
        snapshot = read_kill_proof(paths)
        assert snapshot.kill_switch_status == "PROVEN_SHADOW"

        proof_path.write_text("{bad json", encoding="utf-8")
        snapshot = read_kill_proof(paths)
        assert snapshot.source_status == "parse_error"
    finally:
        cleanup_scratch(scratch)
