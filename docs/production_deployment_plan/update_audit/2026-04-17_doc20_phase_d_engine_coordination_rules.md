"""Doc20 native migration - Phase D engine coordination rules seam."""

Date: 2026-04-17
Status: PARTIAL

Docs gouvernants:
- `28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`
- `24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`

Code seam reel:
- `src/protocols/engine_coordination_rules.py`
- `src/protocols/closed_episode_journal.py`
- `src/interface_contracts/forecast_contracts.py`
- `src/interface_contracts/refusal_records.py`

Claims implemented:
- Added a native typed coordination seam in the mandated package:
  - `EngineCoordinationInput`
  - `EngineCoordinationThresholds`
  - `EngineCoordinationOutcome`
  - `evaluate_engine_coordination`
- Implemented the additive rule surface for:
  - `R-AC-1` A holding -> C hard block
  - `R-AC-2` recent A fire on same setup -> C hard block
  - `R-D-1` missing or mismatched historical linkage -> D hard block
  - `R-D-2` consecutive D stops reset-required -> D hard block
  - `R-D-3` explicit failsafe override after expiry -> D permit
  - `R-D-4` D size multiplier -> `0.5`
- Hard-block outcomes emit:
  - `ConditioningRecord(family=HARD_BLOCK, ...)`
  - `RefusalRecord(category=HARD_BLOCK, ...)`
- Permit outcomes do not create fake refusals.

Design boundary:
- The seam does **not** infer “same structural setup”.
- The seam does **not** infer whether the failsafe override was already consumed once.
- Both judgments remain explicit inputs:
  - `recent_a_fire_same_setup_at_ns`
  - `d_failsafe_override_available`

This keeps the module additive and honest instead of freezing hidden state logic in the wrong layer.

Files changed:
- `src/protocols/engine_coordination_rules.py`
- `src/protocols/__init__.py`
- `tests/test_protocols/test_engine_coordination_rules.py`

Tests and proof:
- `python -m py_compile` with `PYTHONPYCACHEPREFIX=.test_tmp/pycache`
- `rtk pytest -q tests/test_protocols/test_closed_episode_journal.py tests/test_protocols/test_engine_coordination_rules.py tests/test_engines/test_engine_a/test_engine_a_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime_refusals.py`
  - `65 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`

Deferred / not done:
- direct runtime wiring into C and D
- persistent one-shot tracking for `R-D-3` override consumption
- A/C setup-hash resolution upstream
- portfolio arbitration record integration

Next safe step:
- wire `engine_coordination_rules` into C/D runtime support with refusal journaling and no fake candidate emission,
  only after explicit upstream inputs for setup identity and failsafe-slot state are available
