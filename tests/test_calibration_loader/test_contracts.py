from __future__ import annotations

from calibration_loader import CalibrationArtifact


def _payload() -> dict[str, object]:
    return {
        "artifact_id": "edge-thresholds-v1",
        "version": "v1",
        "produced_by": "local_ia_lab",
        "generated_at": "2026-04-09T10:15:00Z",
        "thresholds": (
            {
                "threshold_id": "THR-E01",
                "value": 2.0,
                "source_module": "src/scoring_backbone/fee_aware_edge_gate.py",
                "calibration_artifact": "config/calibration/v1/edge_gate.yml",
            },
            {
                "threshold_id": "THR-E02",
                "value": 15,
                "source_module": "src/scoring_backbone/fee_aware_edge_gate.py",
                "calibration_artifact": "config/calibration/v1/edge_gate.yml",
            },
        ),
        "signature": {
            "signed_by": "operator.aziz",
            "signed_at": "2026-04-09T12:00:00Z",
        },
    }


def test_calibration_artifact_computes_stable_payload_hash() -> None:
    artifact = CalibrationArtifact.model_validate(_payload())

    payload_hash = artifact.payload_hash_sha256()

    assert len(payload_hash) == 64
    assert payload_hash == artifact.payload_hash_sha256()


def test_calibration_artifact_accepts_matching_optional_payload_hash() -> None:
    payload = _payload()
    unsigned_artifact = CalibrationArtifact.model_validate(payload)
    payload["signature"]["payload_hash_sha256"] = unsigned_artifact.payload_hash_sha256()

    artifact = CalibrationArtifact.model_validate(payload)

    assert artifact.signature.payload_hash_sha256 == artifact.payload_hash_sha256()


def test_calibration_artifact_rejects_duplicate_threshold_ids() -> None:
    payload = _payload()
    payload["thresholds"] = (
        payload["thresholds"][0],
        payload["thresholds"][0],
    )

    try:
        CalibrationArtifact.model_validate(payload)
    except ValueError as exc:
        assert "threshold_ids must be unique" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected duplicate threshold ids to be rejected")

