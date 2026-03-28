"""Local HTML rendering for the Build-10 technical dashboard."""

from __future__ import annotations

from html import escape

from ui.contracts import DashboardCard, DashboardSection


def _status_class(status: str) -> str:
    return {
        "healthy": "status-healthy",
        "warning": "status-warning",
        "critical": "status-critical",
        "planned": "status-planned",
    }.get(status, "status-info")


def _render_card(card: DashboardCard) -> str:
    detail = f"<p class='card-detail'>{escape(card.detail)}</p>" if card.detail else ""
    return (
        f"<article class='card {_status_class(card.status)}'>"
        f"<header><span class='card-label'>{escape(card.label)}</span>"
        f"<span class='card-status'>{escape(card.status)}</span></header>"
        f"<p class='card-value'>{escape(card.value)}</p>"
        f"{detail}"
        f"</article>"
    )


def _render_section(section: DashboardSection) -> str:
    cards = "".join(_render_card(card) for card in section.cards)
    return (
        f"<section class='section'>"
        f"<h2>{escape(section.title)}</h2>"
        f"<div class='card-grid'>{cards}</div>"
        f"</section>"
    )


def _render_list(title: str, values: tuple[str, ...]) -> str:
    if not values:
        return ""
    items = "".join(f"<li>{escape(value)}</li>" for value in values)
    return f"<section class='section'><h2>{escape(title)}</h2><ul class='bullet-list'>{items}</ul></section>"


def _render_code_block(title: str, body: str) -> str:
    if not body:
        return ""
    return (
        "<details class='details-block'>"
        f"<summary>{escape(title)}</summary>"
        f"<pre>{escape(body)}</pre>"
        "</details>"
    )


def render_technical_dashboard_html(
    *,
    title: str,
    generated_at: str,
    source_mode: str,
    source_note: str,
    sections: tuple[DashboardSection, ...],
    future_panels: tuple[str, ...] = (),
    footer_notes: tuple[str, ...] = (),
    observability_text: str = "",
    raw_payload_json: str = "",
    raw_view_json: str = "",
) -> str:
    """Render a local static HTML page for the technical dashboard."""

    rendered_sections = "".join(_render_section(section) for section in sections)
    future_section = _render_list("Future Panels", future_panels)
    footer_section = _render_list("Notes", footer_notes)
    observability_block = _render_code_block("Observability Export", observability_text)
    payload_block = _render_code_block("Raw Technical Payload", raw_payload_json)
    view_block = _render_code_block("Raw Technical View", raw_view_json)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4f6f8;
      --panel: #ffffff;
      --text: #1e2933;
      --muted: #5a6872;
      --border: #d5dde5;
      --healthy: #dff6e8;
      --healthy-border: #3fa76b;
      --warning: #fff1d6;
      --warning-border: #c58b19;
      --critical: #ffe0e0;
      --critical-border: #c44141;
      --info: #e4eefc;
      --info-border: #4a7fd1;
      --planned: #ededed;
      --planned-border: #7c8590;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Tahoma, sans-serif;
      background: linear-gradient(180deg, #eef3f7 0%, var(--bg) 160px);
      color: var(--text);
    }}
    main {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 24px;
    }}
    .hero, .section, .details-block {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 14px;
      box-shadow: 0 10px 26px rgba(25, 39, 52, 0.05);
    }}
    .hero {{
      padding: 24px;
      margin-bottom: 20px;
    }}
    .hero h1 {{
      margin: 0 0 8px;
      font-size: 28px;
    }}
    .hero-meta {{
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 14px;
    }}
    .hero-note {{
      margin-top: 14px;
      padding: 12px 14px;
      border-radius: 10px;
      background: #f8fbfd;
      border: 1px solid #dfe8ef;
    }}
    .section {{
      padding: 18px;
      margin-bottom: 18px;
    }}
    .section h2 {{
      margin: 0 0 14px;
      font-size: 18px;
    }}
    .card-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
    }}
    .card {{
      border-radius: 12px;
      border: 1px solid var(--border);
      padding: 14px;
      min-height: 128px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .card header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--muted);
    }}
    .card-label {{
      font-weight: 700;
    }}
    .card-status {{
      font-weight: 700;
    }}
    .card-value {{
      margin: 0;
      font-size: 22px;
      font-weight: 700;
      line-height: 1.25;
      word-break: break-word;
    }}
    .card-detail {{
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
      white-space: pre-wrap;
    }}
    .status-healthy {{
      background: var(--healthy);
      border-color: var(--healthy-border);
    }}
    .status-warning {{
      background: var(--warning);
      border-color: var(--warning-border);
    }}
    .status-critical {{
      background: var(--critical);
      border-color: var(--critical-border);
    }}
    .status-info {{
      background: var(--info);
      border-color: var(--info-border);
    }}
    .status-planned {{
      background: var(--planned);
      border-color: var(--planned-border);
    }}
    .bullet-list {{
      margin: 0;
      padding-left: 20px;
      color: var(--muted);
    }}
    .details-block {{
      margin-bottom: 18px;
      overflow: hidden;
    }}
    .details-block summary {{
      cursor: pointer;
      padding: 14px 18px;
      font-weight: 700;
      background: #f7fafc;
    }}
    .details-block pre {{
      margin: 0;
      padding: 16px 18px;
      overflow-x: auto;
      background: #10171f;
      color: #edf3fb;
      font-size: 13px;
      line-height: 1.5;
    }}
    @media (max-width: 720px) {{
      main {{ padding: 16px; }}
      .hero {{ padding: 18px; }}
      .card-value {{ font-size: 18px; }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>{escape(title)}</h1>
      <div class="hero-meta">
        <div><strong>Generated at:</strong> {escape(generated_at)}</div>
        <div><strong>Source mode:</strong> {escape(source_mode)}</div>
      </div>
      <p class="hero-note">{escape(source_note)}</p>
    </section>
    {rendered_sections}
    {future_section}
    {observability_block}
    {payload_block}
    {view_block}
    {footer_section}
  </main>
</body>
</html>
"""


__all__ = [
    "render_technical_dashboard_html",
]
