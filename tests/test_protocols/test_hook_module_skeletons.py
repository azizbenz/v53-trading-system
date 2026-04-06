from __future__ import annotations

import importlib
from pathlib import Path

from interface_contracts import HookId, HOOK_MODULE_BY_ID
from protocols.execution_hooks import (
    HOOK_ID as EXECUTION_HOOK_ID,
    RUNTIME_OPEN as EXECUTION_RUNTIME_OPEN,
    load_execution_hook_payload,
    run_execution_hook,
)
from protocols.execution_no_trade_hook import (
    load_execution_no_trade_hook_payload,
    run_execution_no_trade_hook,
)


def _protocol_module_name(filename: str) -> str:
    return f"protocols.{Path(filename).stem}"


def test_canonical_hook_module_targets_exist_under_protocols() -> None:
    for module_filename in HOOK_MODULE_BY_ID.values():
        assert Path("src/protocols", module_filename).exists()


def test_canonical_hook_modules_import_and_match_declared_hook_ids() -> None:
    for hook_id, module_filename in HOOK_MODULE_BY_ID.items():
        module = importlib.import_module(_protocol_module_name(module_filename))
        assert module.HOOK_ID == hook_id


def test_unopened_canonical_hook_modules_are_marked_closed() -> None:
    for hook_id, module_filename in HOOK_MODULE_BY_ID.items():
        module = importlib.import_module(_protocol_module_name(module_filename))
        if hook_id == HookId.EXECUTION_NO_TRADE_FILTER:
            assert module.RUNTIME_OPEN is True
        else:
            assert module.RUNTIME_OPEN is False


def test_execution_hook_wrapper_reuses_bounded_no_trade_hook() -> None:
    assert EXECUTION_HOOK_ID == HookId.EXECUTION_NO_TRADE_FILTER
    assert EXECUTION_RUNTIME_OPEN is True
    assert load_execution_hook_payload is load_execution_no_trade_hook_payload
    assert run_execution_hook is run_execution_no_trade_hook
