"""Tests for the local technical dashboard HTML renderer."""

from __future__ import annotations

from ui import DashboardCard, DashboardSection, render_technical_dashboard_html


def test_render_technical_dashboard_html_renders_sections_future_panels_and_exports():
    html = render_technical_dashboard_html(
        title="V5.3 Technical Dashboard",
        generated_at="2026-03-28 10:00:00 UTC",
        source_mode="demo_payload",
        source_note="Governed demo payload only.",
        sections=(
            DashboardSection(
                title="Build-10",
                cards=(
                    DashboardCard(
                        key="build10_state",
                        label="State",
                        value="implemented",
                        status="healthy",
                        detail="Typed payload, view, and HTML supervision pipeline are active.",
                    ),
                ),
            ),
            DashboardSection(
                title="System",
                cards=(
                    DashboardCard(
                        key="headline",
                        label="Headline",
                        value="warning",
                        status="warning",
                        detail="2 active alerts",
                    ),
                ),
            ),
        ),
        future_panels=("technical_supervision", "observability_export", "artifact_import"),
        footer_notes=("One V5.3 only.",),
        observability_text="# sample\nv53_system_active_alert_count 2",
        raw_payload_json='{"correlation_id": "corr-1"}',
        raw_view_json='{"sections": 1}',
        additional_sections_html="<section id='selection-assistant'>Selection assistant</section>",
        additional_script="<script>window.__selectionAssistant = true;</script>",
    )

    assert "V5.3 Technical Dashboard" in html
    assert "Source mode:" in html
    assert "demo_payload" in html
    assert "Build-10" in html
    assert "System" in html
    assert "Headline" in html
    assert "status-warning" in html
    assert "2 active alerts" in html
    assert "Future Panels" in html
    assert "Build-10 Technical Supervision" in html
    assert "observability_export" in html
    assert "Observability Export" in html
    assert "Raw Technical Payload" in html
    assert "Raw Technical View" in html
    assert "One V5.3 only." in html
    assert "Selection assistant" in html
    assert "window.__selectionAssistant" in html


def test_render_technical_dashboard_html_omits_optional_blocks_when_empty():
    html = render_technical_dashboard_html(
        title="V5.3 Technical Dashboard",
        generated_at="2026-03-28 10:00:00 UTC",
        source_mode="availability_only",
        source_note="No runtime snapshot loaded.",
        sections=(
            DashboardSection(
                title="Replay & Import",
                cards=(
                    DashboardCard(
                        key="artifact_manifest",
                        label="Artifact Manifest",
                        value="not available",
                        status="planned",
                        detail="No replay bundle loaded.",
                    ),
                ),
            ),
        ),
    )

    assert "Replay &amp; Import" in html
    assert "Artifact Manifest" in html
    assert "not available" in html
    assert "Observability Export" not in html
    assert "Raw Technical Payload" not in html
    assert "Raw Technical View" not in html
    assert "Selection assistant" not in html
