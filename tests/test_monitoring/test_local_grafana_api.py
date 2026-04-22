from __future__ import annotations

import json
from pathlib import Path
import shutil
from threading import Thread
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from monitoring.local_grafana_api import (
    bootstrap_local_grafana,
    build_prometheus_datasource_payload,
)
from tests.support_paths import make_repo_scratch_dir


def _scratch_dir(label: str) -> Path:
    return make_repo_scratch_dir("pytest-local-grafana-api", label)


class _GrafanaApiHandler(BaseHTTPRequestHandler):
    datasource_requests: list[dict] = []
    dashboard_requests: list[dict] = []
    datasource_exists: bool = False

    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers["Content-Length"])
        payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        if self.path == "/api/datasources":
            if self.datasource_exists:
                self._respond({"message": "datasource exists"}, 409)
                return
            self.datasource_requests.append(payload)
            self._respond({"datasource": {"uid": payload["uid"]}}, 200)
            return
        if self.path == "/api/dashboards/db":
            self.dashboard_requests.append(payload)
            self._respond({"status": "success", "uid": payload["dashboard"]["uid"]}, 200)
            return
        self._respond({"message": "not found"}, 404)

    def do_PUT(self) -> None:  # noqa: N802
        content_length = int(self.headers["Content-Length"])
        payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        if self.path == "/api/datasources/uid/prometheus":
            self.datasource_requests.append(payload)
            self._respond({"datasource": {"uid": payload["uid"]}}, 200)
            return
        self._respond({"message": "not found"}, 404)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _respond(self, body: dict, status: int) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def test_build_prometheus_datasource_payload_projects_expected_fields():
    payload = build_prometheus_datasource_payload(
        name="Prometheus",
        uid="prometheus",
        url="http://127.0.0.1:9090",
    )

    assert payload["type"] == "prometheus"
    assert payload["uid"] == "prometheus"
    assert payload["url"] == "http://127.0.0.1:9090"


def test_bootstrap_local_grafana_posts_datasource_and_dashboard():
    output_dir = _scratch_dir("bootstrap")
    dashboard_path = output_dir / "dashboard.json"
    dashboard_path.write_text(
        json.dumps(
            {
                "dashboard": {"uid": "v53-shadow-vps-local", "title": "V5.3 Shadow VPS"},
                "overwrite": True,
            }
        ),
        encoding="utf-8",
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), _GrafanaApiHandler)
    host, port = server.server_address
    thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
    thread.start()
    try:
        summary = bootstrap_local_grafana(
            grafana_url=f"http://{host}:{port}",
            username="admin",
            password="admin",
            dashboard_payload_path=dashboard_path,
            output_path=output_dir / "summary.json",
        )

        assert summary.datasource_status_code == 200
        assert summary.dashboard_status_code == 200
        assert summary.datasource_uid == "prometheus"
        assert _GrafanaApiHandler.datasource_requests[-1]["type"] == "prometheus"
        assert _GrafanaApiHandler.dashboard_requests[-1]["dashboard"]["uid"] == "v53-shadow-vps-local"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        shutil.rmtree(output_dir, ignore_errors=True)


def test_bootstrap_local_grafana_updates_existing_datasource_on_conflict():
    output_dir = _scratch_dir("conflict")
    dashboard_path = output_dir / "dashboard.json"
    dashboard_path.write_text(
        json.dumps(
            {
                "dashboard": {"uid": "v53-shadow-vps-local", "title": "V5.3 Shadow VPS"},
                "overwrite": True,
            }
        ),
        encoding="utf-8",
    )
    _GrafanaApiHandler.datasource_exists = True
    server = ThreadingHTTPServer(("127.0.0.1", 0), _GrafanaApiHandler)
    host, port = server.server_address
    thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
    thread.start()
    try:
        summary = bootstrap_local_grafana(
            grafana_url=f"http://{host}:{port}",
            username="admin",
            password="admin",
            dashboard_payload_path=dashboard_path,
            output_path=output_dir / "summary.json",
        )

        assert summary.datasource_status_code == 200
        assert _GrafanaApiHandler.datasource_requests[-1]["uid"] == "prometheus"
    finally:
        _GrafanaApiHandler.datasource_exists = False
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        shutil.rmtree(output_dir, ignore_errors=True)
