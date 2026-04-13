"""Generate a checked local-PC Prometheus config over V5.3 scrape handoff artifacts."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field
import yaml


def _normalized_absolute_path(path: str | Path) -> Path:
    """Return a normalized absolute path for generated config references."""

    return Path(path).expanduser().resolve()


class LocalPrometheusConfigSummary(BaseModel, frozen=True):
    """Typed summary for one generated local-PC Prometheus config bundle."""

    vps_file_sd_path: str = Field(..., min_length=1)
    output_path: str = Field(..., min_length=1)
    scrape_job_count: int = Field(default=0, ge=0)
    includes_local_node_exporter: bool = False
    local_node_exporter_target: str = ""
    includes_local_windows_exporter: bool = False
    local_windows_exporter_target: str = ""
    includes_local_lab_bridge: bool = False
    local_lab_target: str = ""
    scrape_interval: str = Field(..., min_length=1)
    evaluation_interval: str = Field(..., min_length=1)


def build_local_prometheus_config_text(
    *,
    vps_file_sd_path: str | Path,
    scrape_interval: str = "15s",
    evaluation_interval: str = "15s",
    file_sd_refresh_interval: str = "30s",
    local_node_exporter_target: str = "",
    local_windows_exporter_target: str = "",
    local_lab_target: str = "",
) -> str:
    """Build a minimal local-PC Prometheus config over the aggregated VPS file_sd bundle."""

    resolved_vps_file_sd_path = _normalized_absolute_path(vps_file_sd_path)
    scrape_configs: list[dict[str, object]] = [
        {
            "job_name": "v53_shadow_vps",
            "file_sd_configs": [
                {
                    "files": [str(resolved_vps_file_sd_path)],
                    "refresh_interval": file_sd_refresh_interval,
                }
            ],
        }
    ]
    if local_node_exporter_target:
        scrape_configs.append(
            {
                "job_name": "v53_local_node",
                "static_configs": [
                    {
                        "targets": [local_node_exporter_target],
                        "labels": {"scope": "local_pc"},
                    }
                ],
            }
        )
    if local_windows_exporter_target:
        scrape_configs.append(
            {
                "job_name": "v53_local_windows",
                "static_configs": [
                    {
                        "targets": [local_windows_exporter_target],
                        "labels": {
                            "scope": "local_pc",
                            "collector": "windows_exporter",
                        },
                    }
                ],
            }
        )
    if local_lab_target:
        scrape_configs.append(
            {
                "job_name": "v53_local_lab",
                "static_configs": [
                    {
                        "targets": [local_lab_target],
                        "labels": {
                            "scope": "local_pc",
                            "component": "local_ia_lab",
                        },
                    }
                ],
            }
        )

    payload = {
        "global": {
            "scrape_interval": scrape_interval,
            "evaluation_interval": evaluation_interval,
        },
        "scrape_configs": scrape_configs,
    }
    return yaml.safe_dump(payload, sort_keys=False)


def build_local_prometheus_config_summary(
    *,
    vps_file_sd_path: str | Path,
    output_path: str | Path,
    scrape_interval: str = "15s",
    evaluation_interval: str = "15s",
    local_node_exporter_target: str = "",
    local_windows_exporter_target: str = "",
    local_lab_target: str = "",
) -> LocalPrometheusConfigSummary:
    """Project generated local-PC Prometheus config metadata into a typed summary."""

    resolved_vps_file_sd_path = _normalized_absolute_path(vps_file_sd_path)
    resolved_output_path = _normalized_absolute_path(output_path)
    return LocalPrometheusConfigSummary(
        vps_file_sd_path=str(resolved_vps_file_sd_path),
        output_path=str(resolved_output_path),
        scrape_job_count=(
            1
            + (1 if local_node_exporter_target else 0)
            + (1 if local_windows_exporter_target else 0)
            + (1 if local_lab_target else 0)
        ),
        includes_local_node_exporter=bool(local_node_exporter_target),
        local_node_exporter_target=local_node_exporter_target,
        includes_local_windows_exporter=bool(local_windows_exporter_target),
        local_windows_exporter_target=local_windows_exporter_target,
        includes_local_lab_bridge=bool(local_lab_target),
        local_lab_target=local_lab_target,
        scrape_interval=scrape_interval,
        evaluation_interval=evaluation_interval,
    )


__all__ = [
    "LocalPrometheusConfigSummary",
    "build_local_prometheus_config_summary",
    "build_local_prometheus_config_text",
]
