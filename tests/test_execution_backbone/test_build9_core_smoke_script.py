from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_script_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_build9_core_smoke.py"
    sys.path.insert(0, str(repo_root / "src"))
    spec = importlib.util.spec_from_file_location("run_build9_core_smoke", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_execution_bootstrap_smoke_check_passes():
    script_module = _load_script_module()

    result = script_module._run_execution_bootstrap_smoke()

    assert result.passed is True
    assert result.name == "execution_bootstrap"
