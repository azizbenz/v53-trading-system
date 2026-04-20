# 15_ENGINE_C_AUDITS

## Included Source Docs
- docs/production_deployment_plan/update_audit/2026-04-18_doc20_phase_b3_engine_c_additive_economics_wiring.md
- docs/production_deployment_plan/update_audit/2026-04-18_engine_a_risk_code_fix_and_engine_c_truthful_runtime_patch.md

---

## Source: docs/production_deployment_plan/update_audit/2026-04-18_doc20_phase_b3_engine_c_additive_economics_wiring.md

# 2026-04-18 - doc20 Phase B3 - Engine C additive economics wiring

**Date** : 2026-04-18
**Author (master)** : Opus
**Executor (slave)** : Codex
**Time budget** : ~1h
**Governance** : doc 28 arbitration, doc 25 audit protocol, doc 26 template, doc 30 promotion register §5.3

---

## Objective

Mirror the doc20 Phase B1 (engine_a) economics wiring onto **Engine C**. Replace the legacy `forecast_strength = penalized_score * 20.0` heuristic and the naive `expected_break_even = expected_cost + delta_safe` arithmetic with the additive `forecast_normalizer` + `break_even_filter` seam already in production for engines A and B.

This is **additive only** — no canonical contract change, no new engine input field, no logic change to the historical `SignalCandidate` path.

## Docs Governants

- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md` §5 Phase 2 (engine-by-engine economics wiring)
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md` (R-QUANT-FIRST: formula already specified by Phase B1; mechanical mirror only)
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `docs/production_deployment_plan/30_PROMOTION_CALIBRATION_REGISTER.md` §5.3 (Engine C Shadow blockers)
- **Reference implementation (read-only)** : `src/engines/engine_b/engine_b_runtime_forecast_support.py` — Phase B2 already-landed pattern

## Current Code Seam

### Where engine_c stands today

`src/engines/engine_c/engine_c_runtime_forecast_support.py:38-70` — `build_forecast_signal_candidate` for engine_c currently:
- computes `forecast_strength` as `max(0.0, min(20.0, penalized_score * 20.0))` — the **exact heuristic** that doc20 Phase B1 removed for engine_a
- computes `expected_break_even` as `engine_output.expected_cost + engine_inputs.delta_safe` — naive, not via `evaluate_break_even_filter`
- does not import `evaluate_break_even_filter`, `normalize_forecast`, `BreakEvenFilterConfig`, `BreakEvenFilterDecision`, `ForecastNormalizationResult`, or `ForecastNormalizerConfig`
- has no `_EngineCForecastEconomics` dataclass equivalent to engine_b's `_EngineBForecastEconomics`

### Reference pattern (already in production for engine_b)

`src/engines/engine_b/engine_b_runtime_forecast_support.py` ships:
- `_EngineBForecastEconomics` dataclass (lines 41-46)
- `_resolve_forecast_economics` (line 251) — orchestrates normalization + break-even
- `_resolve_volatility_proxy` (line 272) — picks `atr/entry_price` else `delta_safe` fallback
- `_build_additive_break_even_decision` (line 288) — calls `evaluate_break_even_filter`
- `_resolve_break_even_reason_code` / `_resolve_break_even_conditioning_code` (lines 303, 309)
- `_resolve_raw_score_parity_*` helpers (lines 315, 329)
- `resolve_runtime_economics_reason_codes` (line 491)
- `_has_additive_economics_context` (line 504)
- `build_forecast_signal_candidate` (lines 66-101) threads `forecast_economics` into `forecast_strength`, `expected_break_even`, `conditioning_state`, `reason_codes`

### Why mirror engine_b and not engine_a

Engine_c does **not** carry `realized_kernel_vol_scale` on its `EngineCInput` (only engine_a does — see `src/engines/engine_a/engine_a_runner.py:123`). The volatility-proxy fallback chain for engine_c therefore matches engine_b's: `atr/entry_price` else `delta_safe`. **Do not** invent an engine_c `realized_kernel_vol_scale` input — that is a separate, larger seam (Phase 4 work).

### Forbidden shortcuts for this slice

- **do NOT** add any new field to `EngineCInput` or `EngineCOutput`.
- **do NOT** change `decision_contracts.SignalCandidate`.
- **do NOT** modify the canonical (historical) `signal_candidate` path — keep it byte-for-byte identical.
- **do NOT** rewrite or rename `engine_c_runner.py`.
- **do NOT** introduce `realized_kernel_vol_scale` on engine_c.
- **do NOT** copy engine_b's bet-structure semantics — engine_c keeps `BetStructure.BREAKOUT`, engine_b is `BetStructure.MEAN_REVERT`.
- **do NOT** introduce a `side="flat"` path or any fake blocked trade.

## Placement (proposed change — 2 source files modified, 1 test file modified)

### File 1 (modify): `src/engines/engine_c/engine_c_runtime_forecast_support.py`

Target: ≤ 700 lines after change (currently 371 → expected ~540).

Add, in this order, before `build_forecast_signal_candidate`:

1. Imports (extend existing block):
   ```python
   from scoring_backbone import (
       BreakEvenFilterConfig,
       BreakEvenFilterDecision,
       ForecastNormalizationResult,
       ForecastNormalizerConfig,
       evaluate_break_even_filter,
       normalize_forecast,
   )
   ```

2. Module-level configs:
   ```python
   _ENGINE_C_FORECAST_NORMALIZER_CONFIG = ForecastNormalizerConfig()
   _ENGINE_C_BREAK_EVEN_FILTER_CONFIG = BreakEvenFilterConfig()
   ```

3. Dataclass `_EngineCForecastEconomics` mirroring `_EngineBForecastEconomics` exactly (fields `normalization`, `break_even_decision`, `volatility_proxy_reason_code`, `volatility_proxy_conditioning_code`).

4. Helpers (semantics identical to engine_b, names rebranded `_b_` → `_c_`):
   - `_resolve_forecast_economics(engine_inputs, engine_output) -> _EngineCForecastEconomics`
   - `_resolve_volatility_proxy(engine_inputs) -> tuple[float, str, str]` — fallback chain `atr/entry_price` (if both > 0) else `delta_safe`
   - `_build_additive_break_even_decision(engine_inputs, engine_output) -> BreakEvenFilterDecision`
   - `_resolve_break_even_reason_code(decision) -> str`
   - `_resolve_break_even_conditioning_code(decision) -> str`

5. Modify `build_forecast_signal_candidate` (line 38) to:
   - call `_resolve_forecast_economics(engine_inputs, engine_output)`
   - replace `forecast_strength=max(0.0, min(20.0, penalized_score * 20.0))` with `forecast_strength=abs(forecast_economics.normalization.normalized_forecast)`
   - replace `expected_break_even=engine_output.expected_cost + engine_inputs.delta_safe` with `expected_break_even=forecast_economics.break_even_decision.expected_break_even`
   - thread `forecast_economics=forecast_economics` into `_build_conditioning_state(...)` and `_build_forecast_reason_codes(...)`

6. Extend `_build_conditioning_state` to append (after the existing engine_c records):
   - one record for `forecast_economics.volatility_proxy_conditioning_code`
   - one record for `_resolve_break_even_conditioning_code(forecast_economics.break_even_decision)`
   - one record per scoring conditioning record (re-use `build_scoring_conditioning_records` already imported in the engine_b file — add this import to engine_c)

7. Extend `_build_forecast_reason_codes` to merge:
   - existing engine_c reason codes
   - `forecast_economics.volatility_proxy_reason_code`
   - `_resolve_break_even_reason_code(forecast_economics.break_even_decision)`
   Use the same `merge_reason_codes` helper engine_b uses (already importable from `interface_contracts.forecast_contracts`).

8. Append at module bottom:
   ```python
   def resolve_runtime_economics_reason_codes(engine_output, runtime_input) -> tuple[str, ...]:
       """Mirror of engine_b helper for downstream runtime annotation."""
       ...

   def _has_additive_economics_context(engine_output) -> bool:
       return engine_output.expected_cost > 0.0
   ```
   Same body shape as engine_b lines 491-515.

9. Update the module `__all__` list (line 369 area) to export the new public symbols (only those used by `engine_c_runtime.py` or `engine_c_runtime_support.py`).

### File 2 (modify): `src/engines/engine_c/engine_c_runtime.py` and/or `engine_c_runtime_support.py`

Only if the runtime currently bypasses `build_forecast_signal_candidate` for any RISK_REJECTED / RISK_REDUCED / RISK_OBSERVE_ONLY / HARD_BLOCKED branch — apply the **same downstream truthfulness pattern** that engine_a got in `2026-04-18_engine_a_runtime_downstream_truthfulness.md`. If the seam is already in place (call `annotate_forecast_signal_candidate_for_runtime_status` with the new `_has_additive_economics_context`-aware reason codes), only the helper-import update is needed.

If touching is required, keep the diff minimal: thread `resolve_runtime_economics_reason_codes` into the existing `annotate_forecast_signal_candidate_for_runtime_status` call sites only.

### File 3 (new or modify): `tests/test_engines/test_engine_c/test_engine_c_runtime.py`

Add test cases mirroring engine_b's existing forecast-economics tests:

1. `test_runtime_emits_forecast_strength_via_normalizer_when_strategy_id_is_provided` — assert `forecast_strength == abs(normalize_forecast(...).normalized_forecast)`, NOT `penalized_score * 20`.
2. `test_runtime_emits_expected_break_even_via_break_even_filter` — assert `expected_break_even` matches the value returned by `evaluate_break_even_filter`, not the naive `expected_cost + delta_safe`.
3. `test_forecast_conditioning_state_includes_volatility_proxy_record` — assert one record with `family=ConditioningFamily.ENGINE_INTERNAL` and code starting with `engine_internal.engine_c.volatility_proxy.`.
4. `test_forecast_conditioning_state_includes_break_even_record` — assert one record with code starting with `engine_internal.engine_c.break_even.`.
5. `test_forecast_reason_codes_merge_break_even_branch` — assert reason codes contain a code beginning with `engine_c.break_even.`.

For each test, follow engine_b's existing equivalents byte-for-byte for fixture wiring. **Do not** rename existing engine_c test helpers; **do not** delete or weaken any existing engine_c test.

## Files Changed

- `src/engines/engine_c/engine_c_runtime_forecast_support.py` (modify, ≤ 700 lines after)
- `src/engines/engine_c/engine_c_runtime.py` and/or `engine_c_runtime_support.py` (only if downstream wiring requires — minimal diff)
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py` (modify — add 5 tests, no test removed)
- No `engine_a`, `engine_b`, `engine_d` source file may be edited.
- No `decision_contracts` or `forecast_contracts` source file may be edited.
- No `engine_c_runner.py` may be edited.
- No `EngineCInput` / `EngineCOutput` field may be added.

## Claims Implemented

- Claim 1 — `engine_c_runtime_forecast_support.py` no longer uses `penalized_score * 20.0` for `forecast_strength`. `grep -n 'penalized_score \* 20' src/engines/engine_c/engine_c_runtime_forecast_support.py` returns zero hits.
- Claim 2 — `engine_c_runtime_forecast_support.py` no longer uses `engine_output.expected_cost + engine_inputs.delta_safe` for `expected_break_even`. `grep -n 'expected_cost + .*delta_safe' src/engines/engine_c/engine_c_runtime_forecast_support.py` returns zero hits.
- Claim 3 — `engine_c_runtime_forecast_support.py` imports `evaluate_break_even_filter` and `normalize_forecast` from `scoring_backbone`.
- Claim 4 — `_EngineCForecastEconomics` dataclass exists with the same 4 fields as `_EngineBForecastEconomics`.
- Claim 5 — Existing engine_c test count for `test_engine_c_runtime.py` strictly increases by exactly the number of new tests added (≥ 5). No test is removed.
- Claim 6 — Full engine_c suite (`tests/test_engines/test_engine_c/`) passes with the same baseline pass count plus the new tests.
- Claim 7 — Engine_a and engine_b suites still pass unchanged (regression control).
- Claim 8 — `python scripts/run_engineering_guardrails.py` shows `new_violations=0`.
- Claim 9 — `decision_contracts.py` and `forecast_contracts.py` are byte-for-byte identical (`git diff --stat src/interface_contracts/` is empty).
- Claim 10 — No `EngineCInput` / `EngineCOutput` field was added (`git diff src/engines/engine_c/engine_c_runner.py` is empty).

## Tests and Proof (to be filled by Codex)

```
python -m py_compile src/engines/engine_c/engine_c_runtime_forecast_support.py src/engines/engine_c/engine_c_runtime.py src/engines/engine_c/engine_c_runtime_support.py tests/test_engines/test_engine_c/test_engine_c_runtime.py
  -> <fill: pass / fail>

rtk pytest -q tests/test_engines/test_engine_c/
  -> <fill: pass count, must equal previous baseline + N new tests>

rtk pytest -q tests/test_engines/test_engine_a/ tests/test_engines/test_engine_b/
  -> <fill: pass counts unchanged from prior session>

rtk pytest -q tests/test_microstructure/test_paper_repro.py
  -> <fill: 18 passed expected>

rtk pytest -q tests/test_protocols/
  -> <fill: 444 passed expected>

PYTHONPATH=src python scripts/run_engineering_guardrails.py
  -> <fill: new_violations=0 expected>

git diff --stat src/interface_contracts/
  -> <fill: empty expected>

git diff src/engines/engine_c/engine_c_runner.py
  -> <fill: empty expected>

wc -l src/engines/engine_c/engine_c_runtime_forecast_support.py
  -> <fill: ≤ 700 expected>

grep -c 'penalized_score \* 20' src/engines/engine_c/engine_c_runtime_forecast_support.py
  -> <fill: 0 expected>

grep -c 'expected_cost + .*delta_safe' src/engines/engine_c/engine_c_runtime_forecast_support.py
  -> <fill: 0 expected>
```

## Deferred / Not Done

- `realized_kernel_vol_scale` is not added to `EngineCInput`. If/when an engine_c calibration profile fronts a realized-kernel signal, it will be a separate slice (Phase B3-bis or Phase 4 work).
- Engine D additive economics wiring (Phase B4) is not in scope. It is the natural next slice after this one lands GREEN.
- THR-C_VPIN_MAX calibration freeze is not in scope. It is doc 30 §5.3 work and requires the calibration loader to be wired into engine_c (separate, larger slice).

## Risks / Open Questions

- Risk R1 — engine_c `_build_conditioning_state` may fail the `ConditioningRecord` validation if the `volatility_proxy` value is `0.0` and the `value` field requires `> 0`. Mitigation: copy engine_b's `value=` field exactly (engine_b survives this case in production). Codex MUST run the full engine_c suite and report the exact pass count.
- Risk R2 — `BetStructure.BREAKOUT` may not be a valid arg to `evaluate_break_even_filter` if the helper hard-coded `MEAN_REVERT` semantics. Mitigation: the helper takes `expected_gain`, `expected_cost`, `delta_safe`, `volatility_proxy` only — it is bet-structure-agnostic. If Codex hits a contract error, that is a doctrine violation to surface, NOT a silent workaround.
- Risk R3 — the existing `expected_break_even = expected_cost + delta_safe` is a documented invariant in another engine_c test; if the new value differs, that test will fail. Mitigation: this is **expected** — the failing test must be **updated to assert the new additive value** (it is the same test the engine_b equivalent has, with the same fix). If more than ~3 engine_c tests need updating, surface this to Opus before mass-editing.
- Open question O1 — does engine_c currently have a `forecast_versions` map field that needs to be extended with `forecast_normalizer_version` and `break_even_filter_version`? Codex must check `_build_forecast_versions` (currently at line 161) and extend it to mirror engine_b's `_build_forecast_versions` if-and-only-if engine_b includes those keys. If unclear, follow engine_b verbatim.

## Completion Status (to be filled by Codex)

`<fill: COMPLETE / PARTIAL / BLOCKED>`

Reason:

`<fill: one-sentence justification>`

## Next Safe Step (to be filled by Codex)

`<fill: e.g., Hand back to Opus for full-suite green-run audit; if green, propose Phase B4 spec for engine_d additive economics wiring (engine_d currently has no _runtime_forecast_support module at all).>`

---

## Opus audit checklist (post-Codex)

Opus will verify, in this order:
1. `git diff --stat` shows only the in-scope files modified (1-3 source files, 1 test file, plus this audit md). No `engine_a`, `engine_b`, `engine_d`, `decision_contracts`, `forecast_contracts`, or `engine_c_runner` file in the diff.
2. `grep -c 'penalized_score \* 20' src/engines/engine_c/engine_c_runtime_forecast_support.py` returns `0`.
3. `grep -c 'evaluate_break_even_filter' src/engines/engine_c/engine_c_runtime_forecast_support.py` returns `≥ 1`.
4. `wc -l src/engines/engine_c/engine_c_runtime_forecast_support.py` is `≤ 700`.
5. Tests: engine_c suite pass count = baseline + new test count exactly. engine_a + engine_b suites unchanged. paper_repro = 18, protocols = 444.
6. Guardrails: `new_violations=0`.
7. The `_EngineCForecastEconomics` dataclass mirrors `_EngineBForecastEconomics` field-for-field (no extra/missing field).

If any of 1-7 fails → REQUEST_FIX with precise line-level feedback.
If all pass → GREENLIGHT, update Sprint-29 memory hand-off, and write the Phase B4 (engine_d) spec doc.


---

## Source: docs/production_deployment_plan/update_audit/2026-04-18_engine_a_risk_code_fix_and_engine_c_truthful_runtime_patch.md

## Scope

- Engine A targeted safety fix in `engine_a_runtime_support.py`
- Engine C additive truthfulness patch on runner/runtime/forecast/refusal

## Governing docs

- `24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`

## Files changed

- `src/engines/engine_a/engine_a_runtime_support.py`
- `src/engines/engine_c/engine_c_runner.py`
- `src/engines/engine_c/engine_c_runner_support.py`
- `src/engines/engine_c/engine_c_runtime.py`
- `src/engines/engine_c/engine_c_runtime_support.py`
- `src/engines/engine_c/engine_c_runtime_forecast_support.py`
- `tests/test_engines/test_engine_a/test_engine_a_runtime_downstream.py`
- `tests/test_engines/test_engine_c/test_engine_c.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime_downstream.py`

## Claims implemented

- Engine A runtime risk reason extraction now tolerates `dominant_reason_code=None` or blank without unsafe `.strip()`.
- Engine C output now carries stable structured `reason_codes`.
- Engine C forecast enriched rail now carries truthful `reason_codes`, `conditioning_state`, and a stable `invalidation_ref`.
- Engine C downstream runtime states are explicit on the enriched rail for:
  - `HARD_BLOCKED`
  - `REJECTED_RANKING`
  - `REJECTED_PORTFOLIO`
  - `RISK_REJECTED`
  - `RISK_REDUCED`
  - `RISK_OBSERVE_ONLY`
- `HOOK_BLOCKED` now prefers stable structured runtime codes over free-text fallback.
- No canonical `SignalCandidate` change.
- No fake blocked trade.
- No `side="flat"`.

## Boundary kept

- `break_even_filter` was not turned into a second hard gate on the canonical decision contract.
- local duplication policy remains in the runner for pre-emit local economics
- native cross-engine coordination remains in runtime via `engine_coordination_rules`

## Verification

- `python -m pytest -q tests/test_engines/test_engine_a/test_engine_a_runtime_downstream.py tests/test_engines/test_engine_c/test_engine_c.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime_downstream.py tests/test_engines/test_engine_c/test_invalidation_mapper_c.py tests/test_engines/test_engine_c/test_output_payload_builder_c.py`
- result: `58 passed`
- `python -m py_compile ...targeted files...`
- result: pass
- `python scripts/run_engineering_guardrails.py`
- result: `new_violations=0`

## Deferred

- no economics seam harmonization for Engine C beyond additive truthfulness
- no canonical contract widening
- no coordination redesign

## Status

- `DONE`


