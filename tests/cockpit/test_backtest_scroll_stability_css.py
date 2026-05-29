from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
COCKPIT_CSS = REPO_ROOT / "src" / "cockpit" / "static" / "cockpit.css"
BASE_TEMPLATE = REPO_ROOT / "src" / "cockpit" / "templates" / "base.html"


def _rule_body(css: str, selector: str) -> str:
    pattern = re.escape(selector) + r"\s*\{(?P<body>[^}]*)\}"
    match = re.search(pattern, css, flags=re.MULTILINE)
    assert match is not None, f"missing CSS rule for {selector}"
    return match.group("body")


def test_backtest_backbone_cards_avoid_scroll_repaint_containment() -> None:
    css = COCKPIT_CSS.read_text(encoding="utf-8")
    card_rule = (
        'body[data-page="backtest"] #backtest-backbone-parity-card,\n'
        'body[data-page="backtest"] #backtest-backbone-metrics-card'
    )
    details_rule = (
        'body[data-page="backtest"] #backtest-backbone-parity-card details,\n'
        'body[data-page="backtest"] #backtest-backbone-metrics-card details'
    )

    card_body = _rule_body(css, card_rule)
    details_body = _rule_body(css, details_rule)

    assert "BACKTEST-SCROLL-STABILITY-1" in css
    assert "contain: none;" in card_body
    assert "content-visibility: visible;" in card_body
    assert "contain: layout" not in card_body
    assert "contain: none;" in details_body
    assert "content-visibility: visible;" in details_body
    assert "contain: layout" not in details_body


def test_base_template_busts_cached_scroll_stability_css() -> None:
    template = BASE_TEMPLATE.read_text(encoding="utf-8")

    assert "/static/cockpit.css?v=20260528-scroll-stability-1" in template
