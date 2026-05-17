from __future__ import annotations

import json
from pathlib import Path
import shutil

from protocols import ShadowLiveWebSocketConfig


def _load_input_support_module():
    from tests.test_protocols.test_shadow_vps_service_launcher import _load_service_module

    _load_service_module()
    import shadow_vps_service_input_support as input_support

    return input_support


def _scratch_dir(label: str) -> Path:
    from tests.test_protocols.test_shadow_vps_service_launcher import _scratch_dir

    return _scratch_dir(label)


def _write_required_export_files(
    export_dir: Path,
    *,
    feature_bridge_payload: dict[str, object],
    replay_metrics_payload: dict[str, object],
) -> None:
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / "replay_run_manifest.json").write_text("{}", encoding="utf-8")
    (export_dir / "review_export.md").write_text("# review\n", encoding="utf-8")
    (export_dir / "parity_diagnostics.json").write_text("{}", encoding="utf-8")
    (export_dir / "replay_dtr.jsonl").write_text("", encoding="utf-8")
    (export_dir / "feature_bridge.json").write_text(
        json.dumps(feature_bridge_payload),
        encoding="utf-8",
    )
    (export_dir / "replay_metrics.json").write_text(
        json.dumps(replay_metrics_payload),
        encoding="utf-8",
    )


def test_ensure_auto_export_from_live_websocket_regenerates_legacy_export_without_lineage_or_cd(
    monkeypatch,
) -> None:
    input_support = _load_input_support_module()
    output_dir = _scratch_dir("input_support_live_export_regeneration")

    try:
        live_captures_root = output_dir / "live_captures"
        auto_exports_root = output_dir / "auto_exports"
        session_date = "2026-04-28"
        live_capture_dir = live_captures_root / session_date
        live_capture_dir.mkdir(parents=True, exist_ok=True)
        (live_capture_dir / "live_websocket_capture_summary.json").write_text(
            "{}",
            encoding="utf-8",
        )
        (live_capture_dir / "live_websocket_snapshot_batch.json").write_text(
            "[]",
            encoding="utf-8",
        )

        auto_export_dir = auto_exports_root / session_date
        _write_required_export_files(
            auto_export_dir,
            feature_bridge_payload={
                "lineage_lock_status": "missing",
                "engines": ["engine_a", "engine_b"],
            },
            replay_metrics_payload={
                "engine_aggregates": [
                    {"engine_id": "engine_a"},
                    {"engine_id": "engine_b"},
                ]
            },
        )

        live_config = ShadowLiveWebSocketConfig(
            session_date_override=session_date,
            route_hints_by_pair={
                "BTCUSDT": [
                    {"route_id": "btc-engine-a", "engine_id": "engine_a"},
                    {"route_id": "btc-engine-c", "engine_id": "engine_c"},
                ],
                "ETHUSDT": [
                    {"route_id": "eth-engine-b", "engine_id": "engine_b"},
                    {"route_id": "eth-engine-d", "engine_id": "engine_d"},
                ],
            },
        )

        export_launcher_calls: list[list[str]] = []

        class _FakeExportLauncher:
            @staticmethod
            def main(argv: list[str]) -> int:
                export_launcher_calls.append(list(argv))
                return 0

        monkeypatch.setattr(
            input_support,
            "_load_local_replay_export_module",
            lambda: _FakeExportLauncher(),
        )
        monkeypatch.setattr(
            input_support,
            "capture_live_websocket_snapshot_batch",
            lambda *args, **kwargs: None,
        )

        returned_capture_dir, returned_export_dir = input_support._ensure_auto_export_from_live_websocket(
            live_config,
            live_captures_root=live_captures_root,
            auto_exports_root=auto_exports_root,
        )

        assert returned_capture_dir == live_capture_dir
        assert returned_export_dir == auto_export_dir
        assert export_launcher_calls
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
