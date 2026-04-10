from __future__ import annotations

from pathlib import Path

from interface_contracts import ProfileId, RuntimeMode
from monitoring.contracts import ObservabilityExport
from monitoring.observability_io import write_observability_text_payload


def _scratch_dir() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "build" / "pytest-observability-io"


def test_write_observability_text_payload_persists_text_with_trailing_newline():
    scratch = _scratch_dir()
    scratch.mkdir(parents=True, exist_ok=True)
    path = scratch / "local_lab_observability.prom"
    export = ObservabilityExport(
        timestamp_ms=1_800_000_000_000,
        correlation_id="corr-obs-io",
        profile=ProfileId.COMPLETE,
        runtime_mode=RuntimeMode.LOCAL_REPLAY,
        samples=(),
        text_payload="# V5.3 Local IA Lab observability export\nv53_test_metric 1.0",
    )

    write_observability_text_payload(export, path)

    content = path.read_text(encoding="utf-8")
    assert content.endswith("\n")
    assert "# V5.3 Local IA Lab observability export" in content
    assert "v53_test_metric 1.0" in content
