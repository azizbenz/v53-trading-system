from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys
from threading import Thread
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4


class _GrafanaLauncherApiHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers["Content-Length"])
        self.rfile.read(content_length)
        payload = b'{"status":"success"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def _load_launcher_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_local_grafana_bootstrap.py"
    module_name = "test_run_local_grafana_bootstrap"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _scratch_dir(label: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("pytest-local-grafana-bootstrap", label)


def test_local_grafana_bootstrap_launcher_writes_summary():
    launcher = _load_launcher_module()
    scratch = _scratch_dir("launcher")
    try:
        dashboard_path = scratch / "dashboard.json"
        dashboard_path.write_text(
            json.dumps(
                {
                    "dashboard": {
                        "uid": "v53-shadow-vps-local",
                        "title": "V5.3 Shadow VPS - Local Dev Observability",
                    },
                    "overwrite": True,
                }
            ),
            encoding="utf-8",
        )
        output_dir = scratch / "output"
        server = ThreadingHTTPServer(("127.0.0.1", 0), _GrafanaLauncherApiHandler)
        host, port = server.server_address
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
        thread.start()
        try:
            exit_code = launcher.main(
                [
                    "--grafana-url",
                    f"http://{host}:{port}",
                    "--grafana-user",
                    "admin",
                    "--grafana-password",
                    "admin",
                    "--dashboard-json-path",
                    str(dashboard_path),
                    "--output-dir",
                    str(output_dir),
                ]
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        assert exit_code == 0
        summary = json.loads(
            (output_dir / "local_grafana_bootstrap.summary.json").read_text(encoding="utf-8")
        )
        assert summary["grafana_url"] == f"http://{host}:{port}"
        assert summary["dashboard_uid"] == "v53-shadow-vps-local"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
