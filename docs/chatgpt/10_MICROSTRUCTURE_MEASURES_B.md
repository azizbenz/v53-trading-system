# 10_MICROSTRUCTURE_MEASURES_B

## Included Source Docs
- docs/production_deployment_plan/update_audit/2026-04-16_kyle_lambda.md
- docs/production_deployment_plan/update_audit/2026-04-16_hawkes_intensity.md
- docs/production_deployment_plan/update_audit/2026-04-16_pin.md
- docs/production_deployment_plan/update_audit/2026-04-16_roll_spread.md
- docs/production_deployment_plan/update_audit/2026-04-16_amihud_illiquidity.md
- docs/production_deployment_plan/update_audit/2026-04-16_corwin_schultz_spread.md
- docs/production_deployment_plan/update_audit/2026-04-16_realized_effective_spread.md

---

## Source: docs/production_deployment_plan/update_audit/2026-04-16_kyle_lambda.md

# 2026-04-16 — Kyle lambda

## Docs Governing

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `docs/production_deployment_plan/21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md`
- `docs/production_deployment_plan/29_SPRINT_FINAL_CODEX_BEFORE_MONDAY.md`
- `CODEX_PROMPT.md`

## Files Changed

- `src/data_backbone/microstructure/kyle_lambda.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `tests/test_data_backbone/microstructure/test_kyle_lambda.py`

## Claims Implemented

- Added a narrow rolling-OLS Kyle lambda estimator.
- Used Lee-Ready first, tick-rule fallback, and 1-minute interval aggregation before regression.
- Used default 1h rolling window with 4h hard cap.
- Marked non-positive or zero-variance estimates as stale instead of silently accepting them.

## Tests And Proof

- `python -m py_compile src/data_backbone/microstructure/kyle_lambda.py src/data_backbone/microstructure/__init__.py src/data_backbone/__init__.py tests/test_data_backbone/microstructure/test_kyle_lambda.py`
- `python -m pytest tests/test_data_backbone/microstructure/test_kyle_lambda.py -q`
- `python scripts/run_engineering_guardrails.py`
- Proof executed in combined microstructure run: `27 passed`, `new_violations=0`

## Completion Status

- `COMPLETE`
- Next safe step: move to `amihud_illiquidity.py` or `roll_spread.py` for cost-feasibility seams.


---

## Source: docs/production_deployment_plan/update_audit/2026-04-16_hawkes_intensity.md

# 2026-04-16 — Hawkes intensity

## Docs Governing

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `CODEX_PROMPT.md`

## Files Changed

- `src/data_backbone/microstructure/hawkes_intensity.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `tests/test_data_backbone/microstructure/test_hawkes_intensity.py`

## Claims Implemented

- Added canonical univariate exponential-kernel Hawkes intensity evaluator.
- Kept the module honest: it evaluates intensity from pre-estimated `(mu, alpha, beta)` instead of pretending to do MLE.
- Returned a frozen audit-ready record with parameter-source provenance.
- Added deterministic tests for monotone intensity, ordering validation, and invalid evaluation time.

## Tests And Proof

- `python -m py_compile src/data_backbone/microstructure/hawkes_intensity.py src/data_backbone/microstructure/__init__.py src/data_backbone/__init__.py tests/test_data_backbone/microstructure/test_hawkes_intensity.py`
- `python -m pytest tests/test_data_backbone/microstructure/test_hawkes_intensity.py -q`
- `python scripts/run_engineering_guardrails.py`
- Proof executed in combined microstructure run: `47 passed`, `new_violations=0`

## Completion Status

- `COMPLETE`
- Next safe step: wire calibrated Hawkes parameters from the future estimation seam.


---

## Source: docs/production_deployment_plan/update_audit/2026-04-16_pin.md

# 2026-04-16 — PIN

## Docs Governing

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `CODEX_PROMPT.md`

## Files Changed

- `src/data_backbone/microstructure/pin.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `tests/test_data_backbone/microstructure/test_pin.py`

## Claims Implemented

- Added canonical PIN score computation from a pre-estimated latent-state parameter set.
- Kept the module honest: no fake EM estimator, only the documented formula `alpha*mu / (alpha*mu + epsilon_b + epsilon_s)`.
- Returned a frozen audit-ready record with parameter-source provenance.
- Added deterministic tests for formula parity, unit interval, and invalid denominator.

## Tests And Proof

- `python -m py_compile src/data_backbone/microstructure/pin.py src/data_backbone/microstructure/__init__.py src/data_backbone/__init__.py tests/test_data_backbone/microstructure/test_pin.py`
- `python -m pytest tests/test_data_backbone/microstructure/test_pin.py -q`
- `python scripts/run_engineering_guardrails.py`
- Proof executed in combined microstructure run: `47 passed`, `new_violations=0`

## Completion Status

- `COMPLETE`
- Next safe step: wire parameter-estimation outputs from calibration workflows when ready.


---

## Source: docs/production_deployment_plan/update_audit/2026-04-16_roll_spread.md

# 2026-04-16 — Roll spread

## Docs Governing

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `CODEX_PROMPT.md`

## Files Changed

- `src/data_backbone/microstructure/roll_spread.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `tests/test_data_backbone/microstructure/test_roll_spread.py`

## Claims Implemented

- Added canonical Roll spread estimator from lag-one covariance of trade-price changes.
- Used the doc23 rule: `2 * sqrt(-Cov)` if covariance is negative, else `0`.
- Returned a frozen audit-ready record with covariance and provenance hash.
- Added deterministic tests for negative-covariance spread recovery, zero fallback, and ordering validation.

## Tests And Proof

- `python -m py_compile src/data_backbone/microstructure/roll_spread.py src/data_backbone/microstructure/__init__.py src/data_backbone/__init__.py tests/test_data_backbone/microstructure/test_roll_spread.py`
- `python -m pytest tests/test_data_backbone/microstructure/test_roll_spread.py -q`
- `python scripts/run_engineering_guardrails.py`
- Proof executed in combined microstructure run: `33 passed`, `new_violations=0`

## Completion Status

- `COMPLETE`
- Next safe step: move to `corwin_schultz_spread.py` or `pin.py` for the next diagnostics seam.


---

## Source: docs/production_deployment_plan/update_audit/2026-04-16_amihud_illiquidity.md

# 2026-04-16 — Amihud illiquidity

## Docs Governing

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `CODEX_PROMPT.md`

## Files Changed

- `src/data_backbone/microstructure/amihud_illiquidity.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `tests/test_data_backbone/microstructure/test_amihud_illiquidity.py`

## Claims Implemented

- Added canonical rolling Amihud illiquidity estimator on close-price bars and dollar volume.
- Used the doc23 window semantics with 24h default and no embedded decision threshold.
- Returned a frozen audit-ready record with provenance hash.
- Added deterministic tests for manual parity, non-negativity, and input ordering.

## Tests And Proof

- `python -m py_compile src/data_backbone/microstructure/amihud_illiquidity.py src/data_backbone/microstructure/__init__.py src/data_backbone/__init__.py tests/test_data_backbone/microstructure/test_amihud_illiquidity.py`
- `python -m pytest tests/test_data_backbone/microstructure/test_amihud_illiquidity.py -q`
- `python scripts/run_engineering_guardrails.py`
- Proof executed in combined microstructure run: `33 passed`, `new_violations=0`

## Completion Status

- `COMPLETE`
- Next safe step: move to `corwin_schultz_spread.py` or `pin.py` for the next diagnostics seam.


---

## Source: docs/production_deployment_plan/update_audit/2026-04-16_corwin_schultz_spread.md

# 2026-04-16 — Corwin-Schultz spread

## Docs Governing

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `CODEX_PROMPT.md`

## Files Changed

- `src/data_backbone/microstructure/corwin_schultz_spread.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `tests/test_data_backbone/microstructure/test_corwin_schultz_spread.py`

## Claims Implemented

- Added canonical Corwin-Schultz high-low spread estimator on the last two ordered bars.
- Kept the implementation faithful to the doc23 abbreviated formula.
- Returned a frozen audit-ready record with `beta`, `gamma`, `alpha`, and provenance hash.
- Added deterministic tests for positive spread, negative-value clamp, and ordering validation.

## Tests And Proof

- `python -m py_compile src/data_backbone/microstructure/corwin_schultz_spread.py src/data_backbone/microstructure/__init__.py src/data_backbone/__init__.py tests/test_data_backbone/microstructure/test_corwin_schultz_spread.py`
- `python -m pytest tests/test_data_backbone/microstructure/test_corwin_schultz_spread.py -q`
- `python scripts/run_engineering_guardrails.py`
- Proof executed in combined microstructure run: `47 passed`, `new_violations=0`

## Completion Status

- `COMPLETE`
- Next safe step: integrate these diagnostics into governed consumers.


---

## Source: docs/production_deployment_plan/update_audit/2026-04-16_realized_effective_spread.md

# 2026-04-16 — Realized / effective spread

## Docs Governing

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `CODEX_PROMPT.md`

## Files Changed

- `src/data_backbone/microstructure/realized_effective_spread.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `tests/test_data_backbone/microstructure/test_realized_effective_spread.py`

## Claims Implemented

- Added canonical quoted/effective/realized spread diagnostics for live execution observations.
- Kept the formulas exactly at the diagnostic level from doc23.
- Returned a frozen audit-ready record carrying all three spread variants and provenance hash.
- Added deterministic tests for buy, sell, and crossed-book validation.

## Tests And Proof

- `python -m py_compile src/data_backbone/microstructure/realized_effective_spread.py src/data_backbone/microstructure/__init__.py src/data_backbone/__init__.py tests/test_data_backbone/microstructure/test_realized_effective_spread.py`
- `python -m pytest tests/test_data_backbone/microstructure/test_realized_effective_spread.py -q`
- `python scripts/run_engineering_guardrails.py`
- Proof executed in combined microstructure run: `47 passed`, `new_violations=0`

## Completion Status

- `COMPLETE`
- Next safe step: wire live execution observations from `execution_cost_meter` when ready.


