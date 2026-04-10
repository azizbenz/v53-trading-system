from __future__ import annotations

import importlib
from pathlib import Path

from interface_contracts import HookId, HOOK_MODULE_BY_ID, RUNTIME_OPEN_HOOK_IDS, is_runtime_open_hook_id
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
        assert module.RUNTIME_OPEN is is_runtime_open_hook_id(hook_id)


def test_runtime_open_hook_ids_are_governed_and_bounded() -> None:
    assert RUNTIME_OPEN_HOOK_IDS == (
        HookId.ENGINE_A_PRE_ENTRY_CONFIRMATION,
        HookId.ENGINE_B_SWEEP_VALIDATION,
        HookId.ENGINE_C_VOID_VALIDATION,
        HookId.ENGINE_D_REENTRY_VALIDATION,
        HookId.RISK_MICRO_FRICTION_PRECHECK,
        HookId.SCORING_SOFT_PENALTY_LAYER,
        HookId.PORTFOLIO_RELATIVE_RANK_ADJUSTMENT,
        HookId.EXECUTION_NO_TRADE_FILTER,
    )


def test_execution_hook_wrapper_reuses_bounded_no_trade_hook() -> None:
    assert EXECUTION_HOOK_ID == HookId.EXECUTION_NO_TRADE_FILTER
    assert EXECUTION_RUNTIME_OPEN is True
    assert load_execution_hook_payload is load_execution_no_trade_hook_payload
    assert run_execution_hook is run_execution_no_trade_hook
