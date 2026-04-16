from __future__ import annotations

from pathlib import Path
import re

from data_backbone.microstructure import FEATURE_REGISTRY


_BANNED_PATTERN = re.compile(
    r"(?i)\b(rsi|macd|stoch|bbands?|bollinger|williams|adx|sar|ichimoku|cci)\b"
)
_ENGINE_SOURCE_ROOTS = (
    Path("src/engines/engine_a"),
    Path("src/engines/engine_b"),
    Path("src/engines/engine_c"),
    Path("src/engines/engine_d"),
)


def test_no_1990s_ta_in_feature_registry() -> None:
    offenders: list[str] = []
    for feature_id, spec in FEATURE_REGISTRY.items():
        if _BANNED_PATTERN.search(feature_id):
            offenders.append(f"feature_id:{feature_id}")
        for consumer in spec.consumed_by:
            if _BANNED_PATTERN.search(consumer):
                offenders.append(f"consumed_by:{feature_id}:{consumer}")
    assert offenders == []


def test_no_1990s_ta_tokens_in_engine_source_tree() -> None:
    offenders: list[str] = []
    for root in _ENGINE_SOURCE_ROOTS:
        for path in root.rglob("*.py"):
            content = path.read_text(encoding="utf-8")
            if _BANNED_PATTERN.search(content):
                offenders.append(path.as_posix())
    assert offenders == []
