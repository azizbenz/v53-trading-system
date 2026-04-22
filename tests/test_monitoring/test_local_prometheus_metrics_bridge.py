from __future__ import annotations

from pathlib import Path
import shutil
from threading import Thread
from urllib.request import urlopen
from uuid import uuid4

from monitoring.local_prometheus_metrics_bridge import (
    build_local_prometheus_metrics_bridge_server,
    build_local_prometheus_metrics_bridge_summary,
)


def _scratch_dir(label: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("pytest-local-prometheus-metrics-bridge-unit", label)


def test_build_local_prometheus_metrics_bridge_summary_projects_expected_fields():
    scratch = _scratch_dir("summary")
    try:
        prom_path = scratch / "payload.prom"
        prom_path.write_text("metric_a 1\n", encoding="utf-8")

        summary = build_local_prometheus_metrics_bridge_summary(
            source_prom_path=prom_path,
            listen_host="127.0.0.1",
            listen_port=9100,
        )

        assert summary.status == "ready"
        assert summary.source_exists is True
        assert summary.listen_port == 9100
        assert summary.source_path.endswith("payload.prom")
        assert summary.source_kind == "prometheus_text_file"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_local_prometheus_metrics_bridge_server_serves_metrics_and_ready():
    scratch = _scratch_dir("serve_metrics")
    try:
        prom_path = scratch / "payload.prom"
        prom_path.write_text("# HELP metric_a demo\nmetric_a 1\n", encoding="utf-8")
        server = build_local_prometheus_metrics_bridge_server(
            source_prom_path=prom_path,
            listen_host="127.0.0.1",
            listen_port=0,
        )
        host, port = server.server_address
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
        thread.start()
        try:
            metrics_body = urlopen(f"http://{host}:{port}/metrics", timeout=5).read().decode("utf-8")
            ready_body = urlopen(f"http://{host}:{port}/-/ready", timeout=5).read().decode("utf-8")

            assert "metric_a 1" in metrics_body
            assert ready_body.strip() == "ready"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_local_prometheus_metrics_bridge_server_returns_503_when_source_missing():
    scratch = _scratch_dir("missing")
    try:
        prom_path = scratch / "missing.prom"
        server = build_local_prometheus_metrics_bridge_server(
            source_prom_path=prom_path,
            listen_host="127.0.0.1",
            listen_port=0,
        )
        host, port = server.server_address
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
        thread.start()
        try:
            try:
                urlopen(f"http://{host}:{port}/metrics", timeout=5)
                assert False, "expected missing source to return HTTP 503"
            except Exception as exc:  # noqa: BLE001
                assert "503" in str(exc)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_local_prometheus_metrics_bridge_server_serves_observability_export_text_payload():
    scratch = _scratch_dir("observability_export")
    try:
        export_path = scratch / "local_lab_observability_export.json"
        export_path.write_text(
            '{"text_payload": "# HELP metric_a demo\\nmetric_a 1\\n"}',
            encoding="utf-8",
        )
        summary = build_local_prometheus_metrics_bridge_summary(
            observability_export_path=export_path,
            listen_host="127.0.0.1",
            listen_port=9200,
        )
        server = build_local_prometheus_metrics_bridge_server(
            observability_export_path=export_path,
            listen_host="127.0.0.1",
            listen_port=0,
        )
        host, port = server.server_address
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
        thread.start()
        try:
            metrics_body = urlopen(f"http://{host}:{port}/metrics", timeout=5).read().decode("utf-8")
            ready_body = urlopen(f"http://{host}:{port}/-/ready", timeout=5).read().decode("utf-8")

            assert summary.source_kind == "observability_export_json"
            assert "metric_a 1" in metrics_body
            assert ready_body.strip() == "ready"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
