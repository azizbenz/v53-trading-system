from __future__ import annotations

from io import StringIO
from pathlib import Path
import re
import tokenize


_ATR_TOKEN = re.compile(r"(?i)\batr\b")
_CENTRAL_ENGINE_PATHS = (
    Path("src/engines/engine_a/engine_a_runtime_support.py"),
    Path("src/engines/engine_a/invalidation_mapper_a.py"),
    Path("src/engines/engine_c/engine_c_runtime_forecast_support.py"),
    Path("src/engines/engine_c/invalidation_mapper_c.py"),
    Path("src/engines/engine_c/structure_resolver_c.py"),
    Path("src/engines/engine_d/engine_d_runtime_support.py"),
    Path("src/engines/engine_d/invalidation_mapper_d.py"),
)
_ENGINE_SCOPES = (
    Path("src/engines/engine_a"),
    Path("src/engines/engine_c"),
    Path("src/engines/engine_d"),
)
_ALLOWED_OVERLAY_PATHS = (
    Path("src/engines/engine_a/engine_a_runner.py"),
    Path("src/engines/engine_c/engine_c_runner.py"),
    Path("src/engines/engine_c/engine_c_runner_support.py"),
    Path("src/engines/engine_d/engine_d_models.py"),
    Path("src/engines/engine_d/engine_d_runner.py"),
)


def _python_code_contains_atr_name(content: str) -> bool:
    for token in tokenize.generate_tokens(StringIO(content).readline):
        if token.type == tokenize.NAME and token.string.lower() == "atr":
            return True
    return False


def _contains_forbidden_central_atr(*, path: Path, content: str) -> bool:
    return path in _CENTRAL_ENGINE_PATHS and _python_code_contains_atr_name(content)


def test_central_atr_guard_catches_fixture_reintroduction() -> None:
    assert _contains_forbidden_central_atr(
        path=Path("src/engines/engine_c/engine_c_runtime_forecast_support.py"),
        content="volatility_scale = atr / entry_price",
    )


def test_central_atr_guard_allows_legacy_overlay_fixture() -> None:
    assert not _contains_forbidden_central_atr(
        path=Path("src/engines/engine_c/engine_c_runner.py"),
        content="atr: float = 0.0",
    )


def test_python_code_detector_ignores_comments_and_strings() -> None:
    assert not _python_code_contains_atr_name('# ATR is forbidden only on central rails\nx = "atr overlay"\n')
    assert _python_code_contains_atr_name("volatility_scale = atr / entry_price\n")


def test_no_central_atr_tokens_in_migrated_engine_paths() -> None:
    offenders: list[str] = []

    for path in _CENTRAL_ENGINE_PATHS:
        content = path.read_text(encoding="utf-8")
        if _contains_forbidden_central_atr(path=path, content=content):
            offenders.append(path.as_posix())

    assert offenders == []


def test_allowed_overlay_paths_are_explicitly_outside_central_guard_scope() -> None:
    for path in _ALLOWED_OVERLAY_PATHS:
        assert path not in _CENTRAL_ENGINE_PATHS


def test_atr_name_tokens_in_engine_code_are_restricted_to_explicit_overlay_allowlist() -> None:
    offenders: list[str] = []

    for scope in _ENGINE_SCOPES:
        for path in sorted(scope.rglob("*.py")):
            if path in _ALLOWED_OVERLAY_PATHS:
                continue
            content = path.read_text(encoding="utf-8")
            if _python_code_contains_atr_name(content):
                offenders.append(path.as_posix())

    assert offenders == []
