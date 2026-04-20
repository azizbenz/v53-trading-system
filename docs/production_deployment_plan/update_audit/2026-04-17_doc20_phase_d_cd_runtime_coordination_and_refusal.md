# 2026-04-17 - Doc20 Phase D - Engine C/D runtime coordination and refusal wiring

## Governing docs
- doc 28: arbitration law
- doc 24: real placement map
- doc 20: doctrinal coordination target
- doc 25/26: audit protocol and pack template

## Scope
- additive runtime-only wiring for Engine C and Engine D
- no runner rewrite
- no fake blocked trades
- no inferred setup identity

## Files changed
- `src/engines/engine_c/engine_c_runtime.py`
- `src/engines/engine_c/engine_c_runtime_support.py`
- `src/engines/engine_d/engine_d_runtime.py`
- `src/engines/engine_d/engine_d_runtime_support.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py`
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py`

## Claims implemented
- Engine C runtime accepts optional `coordination_input` and evaluates native coordination before hook/scoring.
- Engine D runtime accepts optional `coordination_input` and applies native coordination before hook/scoring.
- C/D hard-block coordination produces `HARD_BLOCKED` without emitting a fake trade.
- C/D runtime results now expose `coordination_outcome` and `refusal_record`.
- C/D runtimes accept an optional `refusal_sink` and write governed `RefusalRecord`s on blocked/no-trade statuses.
- Engine D coordination size reduction propagates into the effective runtime size used by risk evaluation.

## Explicit boundary
- The runtime does not infer “same setup”.
- The runtime does not infer D failsafe one-shot consumption.
- These remain explicit upstream inputs inside `EngineCoordinationInput`.

## Tests added
- Engine C: coordination hard-block refusal journaling
- Engine C: coordination engine-id mismatch validation
- Engine D: coordination hard-block refusal journaling
- Engine D: coordination size reduction reaches the risk candidate

## Proof checklist
- targeted pytest on Engine C/D runtime
- `py_compile`
- guardrails

## Status
- `PARTIAL_COMPLETE`
- next safe step: if needed, expose the same coordination/native refusal seam to forecast-facing C/D runtime artifacts without widening the canonical decision contract
