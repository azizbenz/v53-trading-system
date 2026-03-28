"""Canonical runtime surface tests for the current working-tree baseline."""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.build1
class TestCanonicalRuntimeSurface:
    """Canonical package names should expose the current runtime surface."""

    @pytest.mark.parametrize("module_name", [
        "engine_a",
        "engine_b",
        "portfolio",
        "meta",
        "meta_learning",
        "local_replay_runtime",
        "backtest_artifact_import",
        "monitoring",
        "ui",
    ])
    def test_canonical_module_imports(self, module_name: str):
        module = importlib.import_module(module_name)
        assert hasattr(module, "__all__")
        assert len(module.__all__) > 0

    def test_engine_a_facade_exports_runner_api(self):
        module = importlib.import_module("engine_a")
        assert {"EngineAInput", "EngineAOutput", "EngineADecision", "run_engine_a"} <= set(module.__all__)

    def test_engine_b_facade_exports_runner_api(self):
        module = importlib.import_module("engine_b")
        assert {"EngineBInput", "EngineBOutput", "EngineBDecision", "run_engine_b"} <= set(module.__all__)
