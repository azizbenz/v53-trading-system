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
        "engine_c",
        "engine_d",
        "portfolio",
        "meta",
        "meta_learning",
        "local_replay_runtime",
        "backtest_artifact_import",
        "protocols",
        "alerting",
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

    def test_engine_a_facade_exports_runtime_api(self):
        module = importlib.import_module("engine_a")
        assert {"EngineARuntime", "EngineARuntimeInput", "EngineARuntimeResult", "EngineARuntimeStatus"} <= set(module.__all__)

    def test_engine_b_facade_exports_runner_api(self):
        module = importlib.import_module("engine_b")
        assert {"EngineBInput", "EngineBOutput", "EngineBDecision", "run_engine_b"} <= set(module.__all__)

    def test_engine_b_facade_exports_runtime_api(self):
        module = importlib.import_module("engine_b")
        assert {"EngineBRuntime", "EngineBRuntimeInput", "EngineBRuntimeResult", "EngineBRuntimeStatus"} <= set(module.__all__)

    def test_meta_facade_exports_runtime_api(self):
        module = importlib.import_module("meta")
        assert {"MetaInputSource", "MetaRuntime", "MetaRuntimeConfig", "MetaRuntimeInput", "MetaRuntimeResult", "MetaRuntimeStatus"} <= set(module.__all__)

    def test_engine_c_facade_exports_runner_api(self):
        module = importlib.import_module("engine_c")
        assert {
            "EngineCInput",
            "EngineCOutput",
            "EngineCDecision",
            "run_engine_c",
        } <= set(module.__all__)

    def test_engine_c_facade_exports_runtime_api(self):
        module = importlib.import_module("engine_c")
        assert {
            "EngineCRuntime",
            "EngineCRuntimeInput",
            "EngineCRuntimeResult",
            "EngineCRuntimeStatus",
        } <= set(module.__all__)

    def test_engine_d_facade_exports_runner_api(self):
        module = importlib.import_module("engine_d")
        assert {
            "EngineDInput",
            "EngineDOutput",
            "EngineDDecision",
            "run_engine_d",
        } <= set(module.__all__)

    def test_engine_d_facade_exports_runtime_api(self):
        module = importlib.import_module("engine_d")
        assert {
            "EngineDRuntime",
            "EngineDRuntimeInput",
            "EngineDRuntimeResult",
            "EngineDRuntimeStatus",
        } <= set(module.__all__)
