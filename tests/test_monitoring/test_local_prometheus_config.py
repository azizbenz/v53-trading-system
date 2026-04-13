from __future__ import annotations

from pathlib import Path

from monitoring.local_prometheus_config import (
    build_local_prometheus_config_summary,
    build_local_prometheus_config_text,
)


def test_build_local_prometheus_config_text_includes_vps_file_sd_and_local_node():
    text = build_local_prometheus_config_text(
        vps_file_sd_path="E:/obs/shadow_vps_prometheus_file_sd.json",
        local_node_exporter_target="127.0.0.1:9100",
    )

    assert "job_name: v53_shadow_vps" in text
    assert "shadow_vps_prometheus_file_sd.json" in text
    assert "job_name: v53_local_node" in text
    assert "127.0.0.1:9100" in text


def test_build_local_prometheus_config_text_includes_windows_exporter_when_requested():
    text = build_local_prometheus_config_text(
        vps_file_sd_path="E:/obs/shadow_vps_prometheus_file_sd.json",
        local_windows_exporter_target="127.0.0.1:9182",
    )

    assert "job_name: v53_shadow_vps" in text
    assert "job_name: v53_local_windows" in text
    assert "collector: windows_exporter" in text
    assert "127.0.0.1:9182" in text


def test_build_local_prometheus_config_text_includes_local_lab_target_when_requested():
    text = build_local_prometheus_config_text(
        vps_file_sd_path="E:/obs/shadow_vps_prometheus_file_sd.json",
        local_lab_target="127.0.0.1:9200",
    )

    assert "job_name: v53_local_lab" in text
    assert "component: local_ia_lab" in text
    assert "127.0.0.1:9200" in text


def test_build_local_prometheus_config_summary_projects_expected_metadata():
    summary = build_local_prometheus_config_summary(
        vps_file_sd_path="E:/obs/shadow_vps_prometheus_file_sd.json",
        output_path="E:/obs/prometheus.local.generated.yml",
        local_node_exporter_target="127.0.0.1:9100",
    )

    assert summary.vps_file_sd_path.endswith("shadow_vps_prometheus_file_sd.json")
    assert summary.output_path.endswith("prometheus.local.generated.yml")
    assert summary.scrape_job_count == 2
    assert summary.includes_local_node_exporter is True


def test_build_local_prometheus_config_summary_tracks_windows_exporter_metadata():
    summary = build_local_prometheus_config_summary(
        vps_file_sd_path="E:/obs/shadow_vps_prometheus_file_sd.json",
        output_path="E:/obs/prometheus.local.generated.yml",
        local_windows_exporter_target="127.0.0.1:9182",
    )

    assert summary.scrape_job_count == 2
    assert summary.includes_local_windows_exporter is True
    assert summary.local_windows_exporter_target == "127.0.0.1:9182"


def test_build_local_prometheus_config_summary_tracks_local_lab_target_metadata():
    summary = build_local_prometheus_config_summary(
        vps_file_sd_path="E:/obs/shadow_vps_prometheus_file_sd.json",
        output_path="E:/obs/prometheus.local.generated.yml",
        local_lab_target="127.0.0.1:9200",
    )

    assert summary.scrape_job_count == 2
    assert summary.includes_local_lab_bridge is True
    assert summary.local_lab_target == "127.0.0.1:9200"


def test_build_local_prometheus_config_text_normalizes_relative_file_sd_path_to_absolute():
    text = build_local_prometheus_config_text(
        vps_file_sd_path=Path("build/dev_dual_role_demo/local_prometheus_scrape_bundle/shadow_vps_prometheus_file_sd.json")
    )

    expected = str(
        Path("build/dev_dual_role_demo/local_prometheus_scrape_bundle/shadow_vps_prometheus_file_sd.json").resolve()
    )
    assert expected in text
