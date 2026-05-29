"""Integration tests for the cached A2 wrapper.

Mocks the heavyweight `run_strategy_ladder_data_factory` so we exercise only
the cache wiring (hit, miss, populate, bypass) without re-running A2 itself.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_replay_runtime import a2_cache_runner
from local_replay_runtime.a2_cache import (
    A2_CACHE_METADATA_FILENAME,
    A2_CACHE_RESULT_BLOB_FILENAME,
    PROD_SAFETY_REPORT_FILENAME,
    ANTI_LEAKAGE_REPORT_FILENAME,
    build_a2_cache_key,
    cache_root_for_hash,
    compute_input_hash,
    lookup_a2_cache,
)
from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderCompressionReport,
    StrategyLadderDataFactoryManifest,
    StrategyLadderDataFactoryRequest,
    StrategyLadderDataFactoryResult,
    StrategyLadderDataQualityReport,
    StrategyLadderGoldFeatureManifest,
    StrategyLadderPairUniverseReport,
    StrategyLadderRawSourceReport,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _make_raw_root(tmp_path: Path) -> Path:
    raw_root = tmp_path / "raw"
    _write(raw_root / "BTCUSDT" / "2025-07-01.zip", b"PK\x03\x04raw-A")
    _write(raw_root / "BTCUSDT" / "2025-07-02.zip", b"PK\x03\x04raw-B")
    return raw_root


def _make_request(tmp_path: Path, raw_root: Path) -> StrategyLadderDataFactoryRequest:
    return StrategyLadderDataFactoryRequest(
        run_id="strategy_ladder_workflow-test-cache-runner",
        input_root=tmp_path / "phase_a2_data_factory",
        raw_roots=(raw_root,),
        silver_root=tmp_path / "phase_a2_data_factory" / "silver",
        gold_root=tmp_path / "phase_a2_data_factory" / "gold",
        pairs=("BTCUSDT",),
        timeframes=("15m",),
        feature_names=("close_return", "high_low_range", "volume"),
        start="2025-07-01",
        end="2025-07-02",
        storage_format="jsonl-gz",
    )


def _build_fake_result(run_id: str) -> StrategyLadderDataFactoryResult:
    return StrategyLadderDataFactoryResult(
        manifest=StrategyLadderDataFactoryManifest(run_id=run_id),
        raw_source_report=StrategyLadderRawSourceReport(),
        pair_universe_report=StrategyLadderPairUniverseReport(),
        data_quality_report=StrategyLadderDataQualityReport(),
        silver_index=(),
        compression_report=StrategyLadderCompressionReport(),
        gold_feature_manifest=StrategyLadderGoldFeatureManifest(),
    )


class _Recorder:
    """Captures calls to the mocked underlying A2 runner."""

    def __init__(self, side_effect=None) -> None:
        self.calls = 0
        self.last_request: StrategyLadderDataFactoryRequest | None = None
        self._side_effect = side_effect

    def __call__(
        self, request: StrategyLadderDataFactoryRequest
    ) -> StrategyLadderDataFactoryResult:
        self.calls += 1
        self.last_request = request
        # Materialise the artefacts a normal A2 run would have produced.
        Path(request.silver_root).mkdir(parents=True, exist_ok=True)
        Path(request.gold_root).mkdir(parents=True, exist_ok=True)
        Path(request.input_root).mkdir(parents=True, exist_ok=True)
        _write(
            Path(request.silver_root) / "BTCUSDT.jsonl.gz",
            b"silver-bytes-" + request.run_id.encode(),
        )
        _write(
            Path(request.gold_root) / "feat.jsonl.gz",
            b"gold-bytes-" + request.run_id.encode(),
        )
        # Mimic the prod-safety + anti-leakage reports A2 writes.
        report_dir = Path(request.input_root)
        (report_dir / PROD_SAFETY_REPORT_FILENAME).write_text(
            json.dumps(
                {
                    "prod_safety_status": "RESEARCH_ONLY_NOT_PROD_SAFE",
                    "prod_safe": False,
                    "blocker_codes": [
                        "RAW_SOURCE_TYPE_INFERRED",
                        "SINGLE_PAIR_RESEARCH_ONLY",
                    ],
                }
            ),
            encoding="utf-8",
        )
        (report_dir / ANTI_LEAKAGE_REPORT_FILENAME).write_text(
            json.dumps(
                {"status": "DATA_SCIENCE_READY_FOR_RESEARCH", "blocker_codes": []}
            ),
            encoding="utf-8",
        )
        (report_dir / "a2_gold_progress_report.json").write_text(
            json.dumps({"status": "A2_COMPLETE"}),
            encoding="utf-8",
        )
        if self._side_effect is not None:
            self._side_effect(request)
        return _build_fake_result(request.run_id)


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make sure tests run with a clean cache-env."""

    monkeypatch.delenv(a2_cache_runner.ENV_CACHE_ENABLED, raising=False)
    monkeypatch.delenv(a2_cache_runner.ENV_CACHE_BASE, raising=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_cold_cache_invokes_underlying_and_populates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_root = _make_raw_root(tmp_path)
    request = _make_request(tmp_path, raw_root)
    recorder = _Recorder()
    monkeypatch.setattr(
        a2_cache_runner, "run_strategy_ladder_data_factory", recorder
    )
    cache_base = tmp_path / "cache"

    result = a2_cache_runner.run_strategy_ladder_data_factory_cached(
        request, cache_base=cache_base
    )
    assert isinstance(result, StrategyLadderDataFactoryResult)
    assert result.manifest.run_id == request.run_id
    assert recorder.calls == 1

    # Cache entry must exist with the expected hash + reports propagated.
    cache_key = build_a2_cache_key(
        raw_roots=(raw_root,),
        historical_metadata_root=None,
        pairs=request.pairs,
        engines=request.engines,
        timeframes=request.timeframes,
        feature_names=request.feature_names,
        start=request.start,
        end=request.end,
        data_types=request.data_types,
        compression=request.compression,
        storage_format=request.storage_format,
    )
    input_hash = compute_input_hash(cache_key)
    entry = lookup_a2_cache(cache_base, input_hash)
    assert entry is not None
    assert entry.prod_safety_status == "RESEARCH_ONLY_NOT_PROD_SAFE"
    assert entry.prod_safe is False
    assert "RAW_SOURCE_TYPE_INFERRED" in entry.prod_safety_blocker_codes
    assert entry.anti_leakage_status == "DATA_SCIENCE_READY_FOR_RESEARCH"
    cache_root = cache_root_for_hash(cache_base, input_hash)
    assert (cache_root / A2_CACHE_RESULT_BLOB_FILENAME).is_file()
    assert (cache_root / A2_CACHE_METADATA_FILENAME).is_file()


def test_warm_cache_skips_underlying(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_root = _make_raw_root(tmp_path)
    request_a = _make_request(tmp_path, raw_root)
    recorder = _Recorder()
    monkeypatch.setattr(
        a2_cache_runner, "run_strategy_ladder_data_factory", recorder
    )
    cache_base = tmp_path / "cache"

    # Cold call populates the cache
    a2_cache_runner.run_strategy_ladder_data_factory_cached(
        request_a, cache_base=cache_base
    )
    assert recorder.calls == 1

    # Second call with a NEW request that shares the same canonical inputs
    # (different run_id + different output paths) must hit the cache.
    request_b = request_a.model_copy(
        update={
            "run_id": "strategy_ladder_workflow-test-second-call",
            "input_root": tmp_path / "phase_a2_b",
            "silver_root": tmp_path / "phase_a2_b" / "silver",
            "gold_root": tmp_path / "phase_a2_b" / "gold",
        }
    )
    result = a2_cache_runner.run_strategy_ladder_data_factory_cached(
        request_b, cache_base=cache_base
    )
    assert recorder.calls == 1  # underlying NOT called again
    # The result keeps the SOURCE run_id (cache truthfully echoes what was
    # cached, not the new caller's run_id).
    assert result.manifest.run_id == request_a.run_id
    # Restore wrote the cached silver/gold into the new caller's paths.
    assert (request_b.silver_root / "BTCUSDT.jsonl.gz").is_file()
    assert (request_b.gold_root / "feat.jsonl.gz").is_file()
    # Reports are restored too.
    assert (request_b.input_root / PROD_SAFETY_REPORT_FILENAME).is_file()
    assert (request_b.input_root / ANTI_LEAKAGE_REPORT_FILENAME).is_file()


def test_dry_run_bypasses_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_root = _make_raw_root(tmp_path)
    request = _make_request(tmp_path, raw_root).model_copy(update={"dry_run": True})
    recorder = _Recorder()
    monkeypatch.setattr(
        a2_cache_runner, "run_strategy_ladder_data_factory", recorder
    )
    cache_base = tmp_path / "cache"
    a2_cache_runner.run_strategy_ladder_data_factory_cached(
        request, cache_base=cache_base
    )
    assert recorder.calls == 1
    # No cache directory should have been touched
    assert not cache_base.exists() or not any(cache_base.iterdir())


def test_resume_bypasses_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_root = _make_raw_root(tmp_path)
    request = _make_request(tmp_path, raw_root).model_copy(update={"resume": True})
    recorder = _Recorder()
    monkeypatch.setattr(
        a2_cache_runner, "run_strategy_ladder_data_factory", recorder
    )
    cache_base = tmp_path / "cache"
    a2_cache_runner.run_strategy_ladder_data_factory_cached(
        request, cache_base=cache_base
    )
    assert recorder.calls == 1
    assert not cache_base.exists() or not any(cache_base.iterdir())


def test_disabled_via_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_root = _make_raw_root(tmp_path)
    request = _make_request(tmp_path, raw_root)
    recorder = _Recorder()
    monkeypatch.setattr(
        a2_cache_runner, "run_strategy_ladder_data_factory", recorder
    )
    monkeypatch.setenv(a2_cache_runner.ENV_CACHE_ENABLED, "0")
    cache_base = tmp_path / "cache"
    a2_cache_runner.run_strategy_ladder_data_factory_cached(
        request, cache_base=cache_base
    )
    assert recorder.calls == 1
    assert not cache_base.exists() or not any(cache_base.iterdir())


def test_disabled_via_explicit_argument(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_root = _make_raw_root(tmp_path)
    request = _make_request(tmp_path, raw_root)
    recorder = _Recorder()
    monkeypatch.setattr(
        a2_cache_runner, "run_strategy_ladder_data_factory", recorder
    )
    cache_base = tmp_path / "cache"
    a2_cache_runner.run_strategy_ladder_data_factory_cached(
        request, cache_base=cache_base, cache_enabled=False
    )
    assert recorder.calls == 1
    assert not cache_base.exists() or not any(cache_base.iterdir())


def test_different_feature_names_force_miss(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_root = _make_raw_root(tmp_path)
    request_a = _make_request(tmp_path, raw_root)
    recorder = _Recorder()
    monkeypatch.setattr(
        a2_cache_runner, "run_strategy_ladder_data_factory", recorder
    )
    cache_base = tmp_path / "cache"

    a2_cache_runner.run_strategy_ladder_data_factory_cached(
        request_a, cache_base=cache_base
    )
    assert recorder.calls == 1

    # A run with a different feature set must miss the cache.
    request_b = request_a.model_copy(
        update={
            "run_id": "strategy_ladder_workflow-test-other-features",
            "feature_names": ("close_return",),
            "input_root": tmp_path / "phase_a2_b",
            "silver_root": tmp_path / "phase_a2_b" / "silver",
            "gold_root": tmp_path / "phase_a2_b" / "gold",
        }
    )
    a2_cache_runner.run_strategy_ladder_data_factory_cached(
        request_b, cache_base=cache_base
    )
    assert recorder.calls == 2  # underlying called again on miss


def test_populate_failure_does_not_break_a2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_root = _make_raw_root(tmp_path)
    request = _make_request(tmp_path, raw_root)
    recorder = _Recorder()
    monkeypatch.setattr(
        a2_cache_runner, "run_strategy_ladder_data_factory", recorder
    )

    def _exploding_populate(*args, **kwargs):
        raise RuntimeError("simulated populate failure")

    monkeypatch.setattr(a2_cache_runner, "populate_a2_cache", _exploding_populate)
    cache_base = tmp_path / "cache"

    # Should not raise — populate errors are swallowed
    result = a2_cache_runner.run_strategy_ladder_data_factory_cached(
        request, cache_base=cache_base
    )
    assert recorder.calls == 1
    assert result.manifest.run_id == request.run_id


def test_restore_failure_falls_back_to_uncached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_root = _make_raw_root(tmp_path)
    request_a = _make_request(tmp_path, raw_root)
    recorder = _Recorder()
    monkeypatch.setattr(
        a2_cache_runner, "run_strategy_ladder_data_factory", recorder
    )
    cache_base = tmp_path / "cache"

    # Cold populate
    a2_cache_runner.run_strategy_ladder_data_factory_cached(
        request_a, cache_base=cache_base
    )
    assert recorder.calls == 1

    # Sabotage the cache so restore raises
    cache_key = build_a2_cache_key(
        raw_roots=(raw_root,),
        historical_metadata_root=None,
        pairs=request_a.pairs,
        engines=request_a.engines,
        timeframes=request_a.timeframes,
        feature_names=request_a.feature_names,
        start=request_a.start,
        end=request_a.end,
        data_types=request_a.data_types,
        compression=request_a.compression,
        storage_format=request_a.storage_format,
    )
    import shutil as _shutil

    cache_root = cache_root_for_hash(cache_base, compute_input_hash(cache_key))
    # Remove the silver subdir to force restore_a2_from_cache to raise.
    _shutil.rmtree(cache_root / "silver")

    request_b = request_a.model_copy(
        update={
            "run_id": "strategy_ladder_workflow-test-restore-fail",
            "input_root": tmp_path / "phase_a2_b",
            "silver_root": tmp_path / "phase_a2_b" / "silver",
            "gold_root": tmp_path / "phase_a2_b" / "gold",
        }
    )
    a2_cache_runner.run_strategy_ladder_data_factory_cached(
        request_b, cache_base=cache_base
    )
    # Cache restore failed → underlying was called for request_b
    assert recorder.calls == 2
