# 2026-04-18 - Doc20 additive forecast runtime seam for Engine C/D

## Governing docs
- doc 28: arbitration law
- doc 24: real placement map
- doc 19: migration order
- doc 20: enriched forecast doctrine
- doc 25/26: audit protocol and pack template

## Scope
- additive forecast-facing runtime seam for Engine C and Engine D
- no runner rewrite
- no widening of `decision_contracts.SignalCandidate`
- no fake blocked trades

## Files changed
- `src/engines/engine_c/engine_c_runtime.py`
- `src/engines/engine_c/engine_c_runtime_support.py`
- `src/engines/engine_d/engine_d_runtime.py`
- `src/engines/engine_d/engine_d_runtime_support.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py`
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py`

## Claims implemented
- Engine C runtime input now accepts optional `strategy_id`.
- Engine D runtime input now accepts optional `strategy_id`.
- C/D runtime results now expose additive `forecast_signal_candidate`.
- Historical `signal_candidate` remains unchanged and still drives the canonical runtime path.
- Forecast construction is done only inside runtime support seams.
- Engine C forecast candidate carries additive breakout/continuation/microstructure reason codes.
- Engine D forecast candidate carries additive conviction/link-type/anti-revenge reason codes.
- Engine D forecast candidate reuses `first_episode_ref.bet_structure` when coordination input provides it.

## Explicit boundary
- `invalidation_ref` remains `None` for C/D because the current runner outputs do not expose a canonical invalidation reference string.
- Version maps are truthful but minimal:
  - `scoring_version`
  - `runtime_adapter_version`
- No calibration profile IDs were invented for C/D runtime adapters.

## Tests added
- C runtime emits additive forecast signal when `strategy_id` is provided.
- C forecast reason codes include engine and scoring penalties.
- C conditioning state includes engine-internal and scoring records.
- C forecast versions remain stable.
- C runtime input rejects blank `strategy_id`.
- D runtime emits additive forecast signal when `strategy_id` is provided.
- D forecast reason codes include engine and scoring penalties.
- D conditioning state includes engine-internal and scoring records.
- D forecast versions remain stable.
- D runtime input rejects blank `strategy_id`.

## Proof checklist
- targeted `py_compile` with workspace pycache prefix
- targeted pytest on Engine C/D runtime
- targeted pytest on C/D runtime regression packs
- guardrails

## Completion status
- `PARTIAL_COMPLETE`
- next safe step: if required, harmonize A/B/C/D forecast adapter evidence through a shared audit utility without changing the runtime decision canon
