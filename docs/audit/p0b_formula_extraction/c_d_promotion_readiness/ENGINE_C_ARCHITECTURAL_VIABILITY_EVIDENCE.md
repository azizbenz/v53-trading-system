# Engine C Architectural Viability Evidence

## Role Proven By Source

Primary role:
- continuation / breakout engine
- fake-breakout protection
- toxic-flow veto/context
- not a standalone toxic-flow fade engine

Primary source:

```text
src/engines/engine_c/__init__.py
  "Shadow-capable breakout continuation engine."
```

Additional doctrine proof:

```text
docs/audit/p0b_formula_extraction/wave4_microstructure_external_evidence/WAVE4_EXTERNAL_AUDIT_VERDICT.md
  Engine C doctrine is explicitly continuation / breakout / fake-breakout / toxic-flow veto.
```

## Direct Formulas

Source: `src/engines/engine_c/signal_math_c.py`

```text
breakout_score =
  0.35 * breakout_strength
  + 0.25 * range_quality
  + 0.20 * compression_quality
  + 0.20 * volume_confirmation

context_score =
  0.35 * regime_favorability
  + 0.25 * pair_health
  + 0.20 * data_freshness
  + 0.20 * flow_coherence

continuation_score =
  0.45 * followthrough_room
  + 0.25 * (1 - extension_pct)
  + 0.30 * context_score

fake_breakout_risk =
  0.45 * retrace_risk
  + 0.30 * rejection_wick_ratio
  + 0.25 * (1 - volume_confirmation)
```

## Local Features And Outputs

Source: `src/engines/engine_c/engine_c_runner.py`

### Inputs proven present

- `cumulative_ofi`
- `queue_pressure`
- `vpin`
- `kyle_lambda`
- `realized_vol_current`
- `realized_vol_at_break`
- `expected_gain`
- `expected_cost`
- `candidate_size`
- `holding_period`
- `ce_min`
- `delta_safe`
- `entry_price`
- `breakout_level`

### Outputs proven present

- `breakout_score`
- `continuation_score`
- `fake_breakout_risk`
- `expected_cost`
- `ce_expected`
- `ev_net`
- `reason_codes`
- `microstructure_gate_applied`
- `microstructure_required`
- `microstructure_missing`
- `microstructure_contradictory`

## Requested Field Classification

| Field | Classification | Evidence |
|---|---|---|
| `breakout_confirmation_score` | `NOT_FOUND` | Exact field name not found; engine uses `breakout_score`. |
| `continuation_score` | `PROVEN_PRESENT`, `PROVEN_CONSUMED`, `PROVEN_EXPLAINED` | `engine_c_runner.py`, `signal_math_c.py`, runtime logs/tests. |
| `continuation_momentum` | `NOT_FOUND` | Exact field name not found. |
| `structure_confirmation` | `NOT_FOUND` | Structure logic exists, exact field name not found. |
| `false_breakout_risk` | `PROVEN_PRESENT`, `PROVEN_CONSUMED`, `PROVEN_EXPLAINED` | `signal_math_c.py`, `EngineCOutput`. |
| `microstructure_confirmation_status` | `NOT_PROVEN` | Exact field name absent; equivalent booleans exist. |
| `ofi` | `PROVEN_PRESENT`, `PROVEN_CONSUMED` | `cumulative_ofi` input and continuation validator. |
| `ofi_score` | `NOT_FOUND` | No exact local score field. |
| `raw_ofi` | `NOT_FOUND` | No exact field name; only `cumulative_ofi`. |
| `queue_pressure` | `PROVEN_PRESENT`, `PROVEN_CONSUMED` | `EngineCInput`, continuation validator, runtime logs. |
| `queue_pressure_score` | `NOT_FOUND` | No exact field name. |
| `vpin` | `PROVEN_PRESENT`, `PROVEN_CONSUMED` | `EngineCInput`, continuation validator, runtime logs. |
| `vpin_context` | `NOT_FOUND` | No exact field name. |
| `kyle_lambda` | `PROVEN_PRESENT`, `PROVEN_CONSUMED` | `EngineCInput`, continuation validator, runtime logs. |
| `kyle_lambda_context` | `NOT_FOUND` | No exact field name. |
| `realized_vol_current` | `PROVEN_PRESENT`, `PROVEN_CONSUMED`, `PROVEN_EXPLAINED` | `EngineCInput`, structure resolver, forecast fallback tests. |
| `realized_vol_context` | `NOT_FOUND` | No exact field name. |
| `expected_cost` | `PROVEN_PRESENT`, `PROVEN_CONSUMED`, `PROVEN_EXPLAINED` | `cost_feasibility_c.py`, runtime/export surfaces. |
| `expected_total_cost` | `NOT_FOUND` | Not found on Engine C local seam. |
| `expected_ce` | `PROVEN_PRESENT`, `PROVEN_CONSUMED`, `PROVEN_EXPLAINED` | Exposed as `ce_expected`. |
| `cost_preference` | `PROVEN_PRESENT`, `PROVEN_CONSUMED`, `PROVEN_EXPLAINED` | `cost_feasibility_c.py`, `block_scores`. |
| `reason_codes` | `PROVEN_PRESENT`, `PROVEN_EXPLAINED` | output payload, refusal/runtime tests. |

## Microstructure Veto / Context Proof

Source: `src/engines/engine_c/continuation_validator_c.py`

```text
reason codes:
  ENGINE_C_OFI_PERSISTENCE_REASON
  ENGINE_C_QUEUE_PRESSURE_REASON
  ENGINE_C_VPIN_TOXIC_REASON
  ENGINE_C_KYLE_LAMBDA_REASON
```

Tests:
- `tests/test_engines/test_engine_c/test_continuation_validator_c.py::test_ofi_below_threshold_rejects_with_reason`
- `tests/test_engines/test_engine_c/test_continuation_validator_c.py::test_queue_pressure_below_threshold_rejects_with_reason`
- `tests/test_engines/test_engine_c/test_continuation_validator_c.py::test_vpin_above_threshold_rejects_with_reason`
- `tests/test_engines/test_engine_c/test_continuation_validator_c.py::test_kyle_lambda_policy_is_real`

Interpretation:
- toxic-flow and order-book fields are used as confirmation / veto context
- this is not equivalent to A/B shared `market_toxicity`

## Cost / CE / Risk Consumption

Source: `src/engines/engine_c/cost_feasibility_c.py`

```text
ce_expected = (expected_gain - expected_cost) / holding_period
ev_net = candidate_size * (expected_gain - expected_cost)
```

Source: `src/engines/engine_c/engine_c_runtime_support.py`

```text
ScoringCandidateInput:
  expected_cost=engine_output.expected_cost
  expected_ce=engine_output.ce_expected

RiskCandidate:
  carriage_statuses=("risk_micro_friction_missing", "not_carried_to_risk_rail")
  carriage_reason_codes=(
    "RISK_MICRO_FRICTION_FIELD_MISSING",
    "RISK_INFO_STRESS_FIELD_MISSING",
    "RISK_REGIME_STATE_MISSING",
  )
```

Interpretation:
- expected economics are proven
- shared risk micro-friction carriage is explicitly partial

## Explainability And Reason Codes

Source: `src/engines/engine_c/engine_c_runtime_forecast_support.py` and tests

Proven reason-code families:
- `engine_c.conviction.medium`
- `engine_c.breakout.range_expansion`
- `engine_c.microstructure.confirmed`
- `engine_c.forecast.volatility_proxy.realized_vol_current`
- `engine_c.economics.break_even_cleared`

Tests:
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py::test_forecast_reason_codes_include_engine_and_penalties`
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py::test_conditioning_state_contains_engine_internal_and_scoring_records`
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py::test_runtime_hard_blocked_logs_reasons`
- `tests/test_engines/test_engine_c/test_engine_c_runtime_downstream.py::*`

## Missing Before Shadow

- Engine-specific replay execution-rate artifact
- Engine-specific executed-only net return
- Engine-specific true net-equity drawdown
- Explicit engine-specific shadow promotion artifact
- Explicit carriage of cost completeness / fee / impact / fill-realism / realized-slippage statuses

## Missing Before Micro-live

- All missing-before-shadow items
- small-capital and capital-bucket viability proof
- per-engine refusal/rejection survival and sample-size artifact
- replay/live cost parity for Engine C promotion claims

