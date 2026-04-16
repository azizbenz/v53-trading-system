"""Local Grafana HTTP API helpers for datasource and dashboard bootstrap."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field

from monitoring.grafana_types import GrafanaPayload


class LocalGrafanaBootstrapSummary(BaseModel, frozen=True):
    """Typed summary for one local Grafana bootstrap run."""

    grafana_url: str = Field(..., min_length=1)
    datasource_name: str = Field(..., min_length=1)
    datasource_uid: str = Field(..., min_length=1)
    dashboard_uid: str = Field(..., min_length=1)
    dashboard_title: str = Field(..., min_length=1)
    datasource_status_code: int = Field(..., ge=100, le=599)
    dashboard_status_code: int = Field(..., ge=100, le=599)
    output_path: str = Field(..., min_length=1)


def _basic_auth_headers(username: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _request_json(
    method: str,
    url: str,
    payload: GrafanaPayload,
    headers: dict[str, str],
) -> tuple[int, GrafanaPayload]:
    request = Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method=method,
    )
    with urlopen(request, timeout=15) as response:
        status_code = response.getcode()
        body = response.read().decode("utf-8")
    parsed = json.loads(body) if body else {}
    return status_code, parsed


def build_prometheus_datasource_payload(
    *,
    name: str = "Prometheus",
    uid: str = "prometheus",
    url: str = "http://127.0.0.1:9090",
) -> GrafanaPayload:
    """Build the Grafana Prometheus datasource payload."""

    return {
        "name": name,
        "uid": uid,
        "type": "prometheus",
        "access": "proxy",
        "url": url,
        "isDefault": True,
        "basicAuth": False,
        "jsonData": {"httpMethod": "POST"},
    }


def load_dashboard_payload(path: str | Path) -> GrafanaPayload:
    """Load one Grafana dashboard import payload from disk."""

    return json.loads(Path(path).expanduser().resolve().read_text(encoding="utf-8"))


def bootstrap_local_grafana(
    *,
    grafana_url: str,
    username: str,
    password: str,
    dashboard_payload_path: str | Path,
    datasource_name: str = "Prometheus",
    datasource_uid: str = "prometheus",
    prometheus_url: str = "http://127.0.0.1:9090",
    output_path: str | Path,
) -> LocalGrafanaBootstrapSummary:
    """Create/update the Prometheus datasource and import the dashboard into local Grafana."""

    resolved_output = Path(output_path).expanduser().resolve()
    dashboard_payload = load_dashboard_payload(dashboard_payload_path)
    headers = _basic_auth_headers(username, password)
    datasource_payload = build_prometheus_datasource_payload(
        name=datasource_name,
        uid=datasource_uid,
        url=prometheus_url,
    )
    try:
        datasource_status_code, _ = _request_json(
            "POST",
            f"{grafana_url.rstrip('/')}/api/datasources",
            datasource_payload,
            headers,
        )
    except HTTPError as exc:
        if exc.code != 409:
            raise
        datasource_status_code, _ = _request_json(
            "PUT",
            f"{grafana_url.rstrip('/')}/api/datasources/uid/{quote(datasource_uid, safe='')}",
            datasource_payload,
            headers,
        )
    dashboard_status_code, _ = _request_json(
        "POST",
        f"{grafana_url.rstrip('/')}/api/dashboards/db",
        dashboard_payload,
        headers,
    )
    dashboard = dashboard_payload["dashboard"]
    return LocalGrafanaBootstrapSummary(
        grafana_url=grafana_url,
        datasource_name=datasource_name,
        datasource_uid=datasource_uid,
        dashboard_uid=dashboard["uid"],
        dashboard_title=dashboard["title"],
        datasource_status_code=datasource_status_code,
        dashboard_status_code=dashboard_status_code,
        output_path=str(resolved_output),
    )


__all__ = [
    "LocalGrafanaBootstrapSummary",
    "bootstrap_local_grafana",
    "build_prometheus_datasource_payload",
    "load_dashboard_payload",
]
