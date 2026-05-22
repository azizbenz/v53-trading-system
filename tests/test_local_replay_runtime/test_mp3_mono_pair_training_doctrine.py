"""Tests MP3 (2026-05-21) — Mono-pair training doctrine.

Vérifie que `StrategyLadderExpectedEdgeTrainingRequest` enforce strictement
la doctrine mono-pair de V5.3 training :
1. pair: str accepted (mono-pair OK)
2. pair: tuple/list rejected with clear doctrinal error message
3. Multi-timeframe OK (timeframe field stays singular per request)
4. Data factory accepts multi-pair (sourcing scope ≠ training scope)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderDataFactoryRequest,
)
from local_replay_runtime.strategy_ladder_expected_edge_training import (
    StrategyLadderExpectedEdgeTrainingRequest,
)


def _make_valid_kwargs(tmp_path: Path, **overrides) -> dict:
    """Build minimal valid kwargs for a training request."""
    defaults = dict(
        artifact_id="test_mp3_mono_pair",
        calibration_version="v1",
        kline_root=tmp_path / "klines",
        output_dir=tmp_path / "out",
        pair="BTCUSDT",
        timeframe="15m",
        train_start="2025-01-01",
        train_end="2025-01-31",
    )
    defaults.update(overrides)
    return defaults


def test_training_request_accepts_single_str_pair_2026_05_21(tmp_path: Path) -> None:
    """Patch MP3 — pair=str (mono-pair) accepté."""
    (tmp_path / "klines").mkdir()
    request = StrategyLadderExpectedEdgeTrainingRequest(
        **_make_valid_kwargs(tmp_path, pair="BTCUSDT")
    )
    assert request.pair == "BTCUSDT"


def test_training_request_rejects_tuple_pair_with_doctrine_message_2026_05_21(
    tmp_path: Path,
) -> None:
    """Patch MP3 — pair=tuple rejected with explicit V5.3 doctrine message."""
    (tmp_path / "klines").mkdir()
    with pytest.raises(ValueError) as exc_info:
        StrategyLadderExpectedEdgeTrainingRequest(
            **_make_valid_kwargs(tmp_path, pair=("BTCUSDT", "ETHUSDT"))
        )
    err_str = str(exc_info.value)
    assert "DOCTRINE_MONO_PAIR_TRAINING" in err_str
    assert "tuple" in err_str.lower()
    assert "F13" in err_str  # mentions multi-pair future scope


def test_training_request_rejects_list_pair_with_doctrine_message_2026_05_21(
    tmp_path: Path,
) -> None:
    """Patch MP3 — pair=list rejected with same doctrinal guard."""
    (tmp_path / "klines").mkdir()
    with pytest.raises(ValueError) as exc_info:
        StrategyLadderExpectedEdgeTrainingRequest(
            **_make_valid_kwargs(tmp_path, pair=["BTCUSDT", "SOLUSDT"])
        )
    err_str = str(exc_info.value)
    assert "DOCTRINE_MONO_PAIR_TRAINING" in err_str
    assert "list" in err_str.lower()


def test_training_request_rejects_set_pair_with_doctrine_message_2026_05_21(
    tmp_path: Path,
) -> None:
    """Patch MP3 — pair=set/frozenset rejected."""
    (tmp_path / "klines").mkdir()
    with pytest.raises(ValueError) as exc_info:
        StrategyLadderExpectedEdgeTrainingRequest(
            **_make_valid_kwargs(tmp_path, pair={"BTCUSDT", "ETHUSDT"})
        )
    assert "DOCTRINE_MONO_PAIR_TRAINING" in str(exc_info.value)


def test_training_request_rejects_non_str_with_doctrine_message_2026_05_21(
    tmp_path: Path,
) -> None:
    """Patch MP3 — pair=int / None / dict also rejected."""
    (tmp_path / "klines").mkdir()
    for bad_value in (123, None, {"pair": "BTCUSDT"}):
        with pytest.raises(ValueError) as exc_info:
            StrategyLadderExpectedEdgeTrainingRequest(
                **_make_valid_kwargs(tmp_path, pair=bad_value)
            )
        assert "DOCTRINE_MONO_PAIR_TRAINING" in str(exc_info.value)


def test_data_factory_request_accepts_multi_pair_sourcing_2026_05_21(
    tmp_path: Path,
) -> None:
    """Patch MP3 — data_factory.pairs ACCEPTE tuple (sourcing ≠ training)."""
    request = StrategyLadderDataFactoryRequest(
        run_id="test_mp3_multi_pair_sourcing",
        input_root=tmp_path,
        raw_roots=(tmp_path / "raw",),
        silver_root=tmp_path / "silver",
        gold_root=tmp_path / "gold",
        pairs=("BTCUSDT", "ETHUSDT", "SOLUSDT"),  # multi-pair sourcing OK
        start="2025-01-01",
        end="2025-01-31",
    )
    assert request.pairs == ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    assert len(request.pairs) == 3


def test_training_request_doctrine_message_actionable_2026_05_21(
    tmp_path: Path,
) -> None:
    """Patch MP3 — message d'erreur guide vers data_factory.pairs ET F13."""
    (tmp_path / "klines").mkdir()
    with pytest.raises(ValueError) as exc_info:
        StrategyLadderExpectedEdgeTrainingRequest(
            **_make_valid_kwargs(tmp_path, pair=("BTCUSDT", "ETHUSDT"))
        )
    err_str = str(exc_info.value)
    # Actionable hints
    assert "data_factory.pairs" in err_str
    assert re.search(r"F13|multi.?pair.*future", err_str, re.IGNORECASE)
    assert "MONO-PAIR" in err_str.upper()
