"""Doc20 native migration - Phase C refusal seam for Engine A/B runtimes."""

Date: 2026-04-17
Status: COMPLETE

Docs gouvernants:
- `28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`
- `24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`

Code seam reel:
- `src/interface_contracts/refusal_records.py`
- `src/meta_minimal/refusal_journal/refusal_journal.py`
- `src/engines/engine_a/engine_a_runtime.py`
- `src/engines/engine_a/engine_a_runtime_support.py`
- `src/engines/engine_b/engine_b_runtime.py`
- `src/engines/engine_b/engine_b_runtime_support.py`

Claims implemented:
- Engine A runtime can now emit governed `RefusalRecord` objects on:
  - `NO_TRADE`
  - `CIRCUIT_BREAKER_BLOCKED`
  - `HOOK_BLOCKED`
  - `HARD_BLOCKED`
  - `REJECTED_RANKING`
  - `REJECTED_PORTFOLIO`
  - `RISK_REJECTED`
- Engine B runtime now exposes the same refusal-native behavior.
- The refusal seam is additive:
  - no widening of the historical canonical `SignalCandidate`
  - no fake trade emission
  - no runner rewrite
- Runtime results now expose `refusal_record` explicitly.
- Runtime constructors accept an optional governed refusal sink compatible with `RefusalJournalSink`.

Category mapping applied:
- `NO_TRADE` -> `RefusalCategory.NO_TRADE`
- `CIRCUIT_BREAKER_BLOCKED` -> `RefusalCategory.HARD_BLOCK`
- `HOOK_BLOCKED` -> `RefusalCategory.HARD_BLOCK`
- `HARD_BLOCKED` -> `RefusalCategory.HARD_BLOCK`
- `REJECTED_RANKING` -> `RefusalCategory.NO_TRADE`
- `REJECTED_PORTFOLIO` -> `RefusalCategory.PORTFOLIO_REJECTED`
- `RISK_REJECTED` -> `RefusalCategory.HARD_BLOCK`

Reason-code policy:
- prefer existing engine/runtime machine reason codes
- prefer hard-block encoded codes from Build-5 when available
- prefer Build-4 risk dominant/detail codes when available
- fall back only to stable runtime-scoped codes such as:
  - `engine_a.runtime.rejected_portfolio`
  - `engine_b.runtime.rejected_ranking`

Files changed:
- `src/engines/engine_a/engine_a_runtime.py`
- `src/engines/engine_a/engine_a_runtime_support.py`
- `src/engines/engine_b/engine_b_runtime.py`
- `src/engines/engine_b/engine_b_runtime_support.py`
- `tests/test_engines/test_engine_a/test_engine_a_runtime.py`
- `tests/test_engines/test_engine_b/test_engine_b_runtime.py`
- `tests/test_engines/test_engine_b/test_engine_b_runtime_refusals.py`

Tests and proof:
- `python -m py_compile src/engines/engine_a/engine_a_runtime.py src/engines/engine_a/engine_a_runtime_support.py src/engines/engine_b/engine_b_runtime.py src/engines/engine_b/engine_b_runtime_support.py tests/test_engines/test_engine_a/test_engine_a_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime_refusals.py`
- `rtk pytest -q tests/test_meta_minimal/test_refusal_journal.py tests/test_engines/test_engine_a/test_engine_a.py tests/test_engines/test_engine_a/test_engine_a_runtime.py tests/test_engines/test_engine_a/test_engine_a_integration.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime_refusals.py`
  - `70 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`

Deferred / not done:
- refusal conditioning summaries for non-emitted runtime paths
- wiring refusal-native behavior into Engine C/D runtimes
- promotion/shadow aggregation on refusal journals
- coordination-layer consumption of refusal records

Next safe step:
- keep doc20 Phase C additive and wire refusal-native behavior into shared reporting/aggregation,
  or open Phase D with `protocols/engine_coordination_rules.py`
