from __future__ import annotations

from fastapi.testclient import TestClient

from cockpit.server import create_app

from ._operational_helpers import (
    build_paths,
    cleanup_scratch,
    scratch_dir,
    seed_phase25_files,
    write_queue_request,
    write_queue_result,
)


def test_api_snapshot_exposes_operational_proof_and_pages_render_ids() -> None:
    scratch = scratch_dir("routes_operational_proof")
    try:
        paths = build_paths(scratch)
        seed_phase25_files(paths)
        write_queue_request(paths, request_id="req-1")
        write_queue_result(paths, request_id="req-1")
        client = TestClient(create_app(paths=paths))

        payload = client.get("/api/snapshot").json()
        assert "operational_proof" in payload
        assert "freshness" in payload["operational_proof"]
        assert "queue_trace" in payload["operational_proof"]
        assert payload["operational_proof"]["warmup_explainer"]["final_state"] == "blocked"
        assert payload["operational_proof"]["service_liveness"]["control_ready"] is False
        alert_ids = {alert["alert_id"] for alert in payload["runtime"]["alerts"]}
        assert "cockpit:warmup_blocked" in alert_ids
        assert "cockpit:service_degraded_not_control_ready" in alert_ids
        assert "cockpit:queue_only_not_consumed" in alert_ids
        assert "cockpit:engine_cd_dormant" in alert_ids
        assert "cockpit:refusal_journal_missing" in alert_ids

        overview = client.get("/")
        assert overview.status_code == 200
        assert 'id="system-operability-score"' in overview.text
        assert 'id="operability-blocker-summary"' in overview.text
        assert 'id="source-freshness"' in overview.text
        assert 'id="queue-consumption-trace"' in overview.text
        assert 'id="service-liveness"' in overview.text
        assert 'id="kill-proof-status"' in overview.text

        trading = client.get("/trading")
        assert trading.status_code == 200
        assert 'id="engine-why-state"' in trading.text
        assert 'id="economic-sterilization"' in trading.text

        lab = client.get("/lab")
        assert lab.status_code == 200
        assert 'id="run-comparison"' in lab.text
        assert 'id="lab-vps-transfer"' in lab.text
    finally:
        cleanup_scratch(scratch)


def test_pages_render_when_operational_sources_are_missing() -> None:
    scratch = scratch_dir("routes_operational_missing")
    try:
        paths = build_paths(scratch)
        client = TestClient(create_app(paths=paths))
        assert client.get("/").status_code == 200
        assert client.get("/trading").status_code == 200
        assert client.get("/lab").status_code == 200
    finally:
        cleanup_scratch(scratch)
