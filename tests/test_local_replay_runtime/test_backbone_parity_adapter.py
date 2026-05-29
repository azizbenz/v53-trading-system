from __future__ import annotations

from local_replay_runtime.backbone_parity_adapter import (
    BACKBONE_CONTRACT_INCOMPLETE,
    BACKBONE_LOCAL_REPLAY_PARITY_CONFLICT,
    BACKBONE_RESULT_MISSING,
    CANONICAL_BACKBONE_USED,
    LOCAL_REPLAY_FALLBACK_USED,
    NO_SURFACE_RESULT_AVAILABLE,
    BackboneParityPolicy,
    attach_backbone_surface_status,
    build_backbone_parity_surface_report,
    resolve_backbone_surface,
)


def test_canonical_backbone_used_when_contract_ready_and_payload_present() -> None:
    resolution = resolve_backbone_surface(
        surface="fee_measurement",
        canonical_payload={"fee_rate": 0.001, "fee_source_status": "EXCHANGE_METADATA"},
        local_replay_payload={"fee_rate": 0.001, "fee_source_status": "EXCHANGE_METADATA"},
        contract_ready=True,
        policy=BackboneParityPolicy(compared_fields=("fee_rate",)),
    )

    assert resolution.status == CANONICAL_BACKBONE_USED
    assert resolution.selected_source == "canonical_backbone"
    assert resolution.promotion_allowed is True
    assert resolution.conflict_fields == ()


def test_local_replay_fallback_is_explicit_when_contract_incomplete() -> None:
    resolution = resolve_backbone_surface(
        surface="slippage_measurement",
        canonical_payload=None,
        local_replay_payload={"slippage_bps": 1.2},
        contract_ready=False,
        fallback_reason="ADD_DEPTH20_MEASURED_SLIPPAGE_CONTRACT",
    )

    assert resolution.status == LOCAL_REPLAY_FALLBACK_USED
    assert resolution.selected_source == "local_replay_runtime"
    assert resolution.promotion_allowed is False
    assert BACKBONE_CONTRACT_INCOMPLETE in resolution.reason_codes
    assert "ADD_DEPTH20_MEASURED_SLIPPAGE_CONTRACT" in resolution.reason_codes


def test_missing_backbone_result_uses_fallback_without_promotion() -> None:
    resolution = resolve_backbone_surface(
        surface="spread_measurement",
        canonical_payload={},
        local_replay_payload={"spread_bps": 0.8},
        contract_ready=True,
        fallback_reason="CANONICAL_SPREAD_PAYLOAD_EMPTY",
    )

    assert resolution.status == LOCAL_REPLAY_FALLBACK_USED
    assert resolution.promotion_allowed is False
    assert BACKBONE_RESULT_MISSING in resolution.reason_codes
    assert "CANONICAL_SPREAD_PAYLOAD_EMPTY" in resolution.reason_codes


def test_backbone_local_replay_conflict_blocks_promotion() -> None:
    resolution = resolve_backbone_surface(
        surface="break_even",
        canonical_payload={"ev_net": 0.5, "allowed": True},
        local_replay_payload={"ev_net": -0.1, "allowed": False},
        contract_ready=True,
        policy=BackboneParityPolicy(compared_fields=("ev_net", "allowed")),
    )

    assert resolution.status == BACKBONE_LOCAL_REPLAY_PARITY_CONFLICT
    assert resolution.selected_source == "none"
    assert resolution.promotion_allowed is False
    assert set(resolution.conflict_fields) == {"ev_net", "allowed"}


def test_no_surface_result_available_when_both_payloads_missing() -> None:
    resolution = resolve_backbone_surface(
        surface="risk_filtering",
        canonical_payload=None,
        local_replay_payload=None,
        contract_ready=True,
    )

    assert resolution.status == NO_SURFACE_RESULT_AVAILABLE
    assert resolution.selected_source == "none"
    assert resolution.promotion_allowed is False


def test_attach_status_and_surface_report_are_deterministic() -> None:
    canonical = resolve_backbone_surface(
        surface="fee_measurement",
        canonical_payload={"fee_rate": 0.001},
        local_replay_payload={"fee_rate": 0.001},
        contract_ready=True,
        policy=BackboneParityPolicy(compared_fields=("fee_rate",)),
    )
    fallback = resolve_backbone_surface(
        surface="slippage_measurement",
        canonical_payload=None,
        local_replay_payload={"slippage_bps": 1.0},
        contract_ready=False,
    )

    payload = attach_backbone_surface_status({"value": 1}, fallback)
    assert payload["value"] == 1
    assert payload["backbone_surface_status"]["status"] == LOCAL_REPLAY_FALLBACK_USED

    report = build_backbone_parity_surface_report((canonical, fallback))
    assert report["surface_count"] == 2
    assert report["promotion_allowed"] is False
    assert report["status_counts"][CANONICAL_BACKBONE_USED] == 1
    assert report["status_counts"][LOCAL_REPLAY_FALLBACK_USED] == 1
