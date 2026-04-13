"""Dev-only local HTTP bridge that serves a Prometheus text payload over /metrics."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Final
from typing import Literal

from pydantic import BaseModel, Field


DEFAULT_METRICS_PATH: Final[str] = "/metrics"
DEFAULT_READY_PATH: Final[str] = "/-/ready"
PrometheusTextSourceKind = Literal["prometheus_text_file", "observability_export_json"]


def resolve_local_prometheus_text_source(
    *,
    source_prom_path: str | Path | None = None,
    observability_export_path: str | Path | None = None,
) -> tuple[Path, PrometheusTextSourceKind]:
    """Resolve one metrics text source from either a raw `.prom` file or an observability export."""

    if source_prom_path and observability_export_path:
        raise ValueError(
            "Provide only one of source_prom_path or observability_export_path"
        )
    if source_prom_path:
        return Path(source_prom_path).expanduser().resolve(), "prometheus_text_file"
    if observability_export_path:
        return Path(observability_export_path).expanduser().resolve(), "observability_export_json"
    raise ValueError(
        "One of source_prom_path or observability_export_path must be provided"
    )


def load_local_prometheus_text_payload(
    *,
    source_prom_path: str | Path | None = None,
    observability_export_path: str | Path | None = None,
) -> tuple[str, Path, PrometheusTextSourceKind]:
    """Load the Prometheus text payload from the configured source."""

    resolved_source, source_kind = resolve_local_prometheus_text_source(
        source_prom_path=source_prom_path,
        observability_export_path=observability_export_path,
    )
    if source_kind == "prometheus_text_file":
        return (
            resolved_source.read_text(encoding="utf-8"),
            resolved_source,
            source_kind,
        )

    payload = json.loads(resolved_source.read_text(encoding="utf-8"))
    text_payload = payload.get("text_payload")
    if not isinstance(text_payload, str) or not text_payload.strip():
        raise ValueError(
            "observability_export_json must contain a non-empty text_payload"
        )
    return text_payload, resolved_source, source_kind


class LocalPrometheusMetricsBridgeSummary(BaseModel, frozen=True):
    """Typed summary for one local dev metrics bridge instance."""

    status: str = Field(..., min_length=1)
    detail: str = Field(..., min_length=1)
    listen_host: str = Field(..., min_length=1)
    listen_port: int = Field(..., ge=0, le=65535)
    metrics_path: str = Field(default=DEFAULT_METRICS_PATH, min_length=1)
    ready_path: str = Field(default=DEFAULT_READY_PATH, min_length=1)
    source_path: str = Field(..., min_length=1)
    source_kind: PrometheusTextSourceKind
    source_exists: bool = False
    output_path: str = ""
    mode: str = Field(default="serve_prometheus_text_source", min_length=1)


def build_local_prometheus_metrics_bridge_summary(
    *,
    source_prom_path: str | Path | None = None,
    observability_export_path: str | Path | None = None,
    listen_host: str,
    listen_port: int,
    output_path: str | Path = "",
    metrics_path: str = DEFAULT_METRICS_PATH,
    ready_path: str = DEFAULT_READY_PATH,
) -> LocalPrometheusMetricsBridgeSummary:
    """Project dev bridge configuration into a typed summary."""

    resolved_source, source_kind = resolve_local_prometheus_text_source(
        source_prom_path=source_prom_path,
        observability_export_path=observability_export_path,
    )
    resolved_output = str(Path(output_path).expanduser().resolve()) if output_path else ""
    source_exists = resolved_source.exists()
    status = "ready" if source_exists else "warning"
    detail = (
        f"http://{listen_host}:{listen_port}{metrics_path} -> {resolved_source} "
        f"({source_kind}) / source_exists={source_exists}"
    )
    return LocalPrometheusMetricsBridgeSummary(
        status=status,
        detail=detail,
        listen_host=listen_host,
        listen_port=listen_port,
        metrics_path=metrics_path,
        ready_path=ready_path,
        source_path=str(resolved_source),
        source_kind=source_kind,
        source_exists=source_exists,
        output_path=resolved_output,
    )


def build_local_prometheus_metrics_bridge_server(
    *,
    source_prom_path: str | Path | None = None,
    observability_export_path: str | Path | None = None,
    listen_host: str = "127.0.0.1",
    listen_port: int = 9100,
    metrics_path: str = DEFAULT_METRICS_PATH,
    ready_path: str = DEFAULT_READY_PATH,
) -> ThreadingHTTPServer:
    """Create a local HTTP server that serves the current `.prom` file over /metrics."""

    resolved_source, source_kind = resolve_local_prometheus_text_source(
        source_prom_path=source_prom_path,
        observability_export_path=observability_export_path,
    )

    class _MetricsBridgeHandler(BaseHTTPRequestHandler):
        server_version = "V53LocalPromBridge/1.0"
        metrics_bridge_source = resolved_source
        metrics_bridge_source_kind = source_kind
        metrics_bridge_metrics_path = metrics_path
        metrics_bridge_ready_path = ready_path

        def do_GET(self) -> None:  # noqa: N802
            if self.path == self.metrics_bridge_metrics_path:
                self._serve_metrics()
                return
            if self.path == self.metrics_bridge_ready_path:
                self._serve_ready()
                return
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def _load_metrics_text(self) -> str:
            text_payload, _, _ = load_local_prometheus_text_payload(
                source_prom_path=(
                    self.metrics_bridge_source
                    if self.metrics_bridge_source_kind == "prometheus_text_file"
                    else None
                ),
                observability_export_path=(
                    self.metrics_bridge_source
                    if self.metrics_bridge_source_kind == "observability_export_json"
                    else None
                ),
            )
            return text_payload

        def _serve_metrics(self) -> None:
            if not self.metrics_bridge_source.exists():
                body = (
                    "# local_prometheus_metrics_bridge source file missing\n"
                    f'# source="{self.metrics_bridge_source}"\n'
                ).encode("utf-8")
                self.send_response(HTTPStatus.SERVICE_UNAVAILABLE)
                self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            try:
                body = self._load_metrics_text().encode("utf-8")
            except Exception as exc:  # noqa: BLE001
                body = (
                    "# local_prometheus_metrics_bridge source load failed\n"
                    f'# source="{self.metrics_bridge_source}"\n'
                    f'# error="{type(exc).__name__}: {exc}"\n'
                ).encode("utf-8")
                self.send_response(HTTPStatus.SERVICE_UNAVAILABLE)
                self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _serve_ready(self) -> None:
            source_ready = False
            if self.metrics_bridge_source.exists():
                try:
                    self._load_metrics_text()
                    source_ready = True
                except Exception:  # noqa: BLE001
                    source_ready = False
            body = b"ready\n" if source_ready else b"missing_source\n"
            status = HTTPStatus.OK if source_ready else HTTPStatus.SERVICE_UNAVAILABLE
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer((listen_host, listen_port), _MetricsBridgeHandler)


__all__ = [
    "DEFAULT_METRICS_PATH",
    "DEFAULT_READY_PATH",
    "LocalPrometheusMetricsBridgeSummary",
    "build_local_prometheus_metrics_bridge_server",
    "build_local_prometheus_metrics_bridge_summary",
    "load_local_prometheus_text_payload",
    "resolve_local_prometheus_text_source",
]
