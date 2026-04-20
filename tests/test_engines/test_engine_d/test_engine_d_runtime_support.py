from __future__ import annotations

from math import nan
from types import SimpleNamespace

import pytest

from engines.engine_d.engine_d_runtime_support import (
    require_scoring_version,
    resolve_runtime_now,
    resolve_scoring_audit,
    to_regime_id,
)
from interface_contracts import RegimeId


def test_resolve_runtime_now_from_timestamp() -> None:
    assert resolve_runtime_now(1_700_000_000_000, None, context="test") == pytest.approx(1_700_000_000.0)


def test_resolve_runtime_now_rejects_invalid_now() -> None:
    with pytest.raises(ValueError, match="requires finite now"):
        resolve_runtime_now(1_700_000_000_000, nan, context="test")


def test_require_scoring_version_rejects_blank() -> None:
    with pytest.raises(ValueError, match="requires non-empty scoring_version"):
        require_scoring_version("   ", context="test")


def test_resolve_scoring_audit_found() -> None:
    round_result = SimpleNamespace(audits=(SimpleNamespace(engine_id="engine_d", pair="BTCUSDT"),))
    audit = resolve_scoring_audit(round_result, engine_id="engine_d", pair="BTCUSDT")
    assert audit is not None
    assert audit.engine_id == "engine_d"


def test_resolve_scoring_audit_missing() -> None:
    round_result = SimpleNamespace(audits=(SimpleNamespace(engine_id="engine_a", pair="ETHUSDT"),))
    audit = resolve_scoring_audit(round_result, engine_id="engine_d", pair="BTCUSDT")
    assert audit is None


def test_to_regime_id_mapping_known_and_unknown() -> None:
    assert to_regime_id("breakout") == RegimeId.BREAKOUT
    assert to_regime_id("something_else") == RegimeId.UNKNOWN
