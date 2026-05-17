# Engine D Architectural Viability Evidence

## Role Proven By Source

Primary role:
- re-entry / second chance engine
- first-episode linked
- anti-revenge / cooldown / reset-state seam
- reformation and marginal-value gate
- realized-vol context

Primary source:

```text
src/engines/engine_d/__init__.py
  "Shadow-capable re-entry engine."
```

Additional doctrine proof:

```text
docs/audit/p0b_formula_extraction/wave4_microstructure_external_evidence/WAVE4_EXTERNAL_AUDIT_VERDICT.md
  Engine D doctrine is explicitly re-entry / first-episode / anti-revenge / realized-vol context.
```

## Direct Formulas

Source: `src/engines/engine_d/signal_math_d.py`

```text
history_score =
  0.55 * prior_trade_quality
  + 0.25 * pair_health
  + 0.20 * data_freshness

context_score =
  0.35 * regime_favorability
  + 0.25 * pair_health
  + 0.20 * data_freshness
  + 0.20 * flow_coherence

reformation_score =
  0.45 * reformation_quality
  + 0.30 * pullback_quality
  + 0.25 * context_score

marginal_value_score =
  0.35 * marginal_edge
  + 0.30 * continuation_room
  + 0.20 * concentration_headroom
  + 0.15 * (1 - reentry_lateness)
```

## Local Features And Outputs

Source: `src/engines/engine_d/engine_d_runner.py`

### Inputs proven present

- `first_episode_id`
- `first_episode_engine_id`
- `first_episode_close_reason`
- `consecutive_stop_count`
- `last_stop_at_ns`
- `last_fresh_a_detection_at_ns`
- `anti_revenge_state`
- `prior_trade_quality`
- `reformation_quality`
- `pullback_quality`
- `continuation_room`
- `concentration_headroom`
- `marginal_edge`
- `reentry_lateness`
- `structure_reformed_detected`
- `realized_vol_current`
- `realized_vol_post_close`
- `expected_gain`
- `expected_cost`

### Outputs proven present

- `origin_context_id`
- `origin_trade_id`
- `link_type`
- `first_episode_id`
- `first_episode_engine_id`
- `first_episode_close_reason`
- `consecutive_stop_count`
- `anti_revenge_state`
- `anti_revenge_blocked`
- `history_score`
- `reformation_score`
- `marginal_value_score`
- `concentration_risk`
- `expected_cost`
- `ce_expected`
- `ev_net`
- `reason_codes`

## Requested Field Classification

| Field | Classification | Evidence |
|---|---|---|
| `first_episode_ref` | `NOT_FOUND` | Exact output field absent; reference is carried through coordination input. |
| `first_episode_ref_present` | `NOT_FOUND` | Exact field not found. |
| `closed_episode_ref` | `NOT_FOUND` | Exact field not found. |
| `reentry_age_minutes` | `NOT_FOUND` | Exact field not found; related logic exists via `reentry_lateness` and `THR-D_MIN_GAP`. |
| `timing_window_score` | `NOT_FOUND` | Exact field not found. |
| `structure_recovery_score` | `NOT_FOUND` | Exact field not found; nearest local field is `reformation_score`. |
| `reformation_score` | `PROVEN_PRESENT`, `PROVEN_CONSUMED`, `PROVEN_EXPLAINED` | `signal_math_d.py`, output payload, runtime logs/tests. |
| `history_score` | `PROVEN_PRESENT`, `PROVEN_CONSUMED`, `PROVEN_EXPLAINED` | `signal_math_d.py`, output payload, runtime logs/tests. |
| `context_score` | `PROVEN_EXPLAINED` | computed in local math, not carried as a named output field. |
| `marginal_value_score` | `PROVEN_PRESENT`, `PROVEN_CONSUMED`, `PROVEN_EXPLAINED` | estimator, output payload, runtime logs/tests. |
| `stale_signal_score` | `NOT_FOUND` | Exact field not found. |
| `anti_revenge_state` | `PROVEN_PRESENT`, `PROVEN_CONSUMED`, `PROVEN_EXPLAINED` | input, output, reentry hook, runtime tests. |
| `consecutive_stop_count` | `PROVEN_PRESENT`, `PROVEN_CONSUMED`, `PROVEN_EXPLAINED` | input, output, stop-counter tests. |
| `realized_kernel_volatility` | `NOT_FOUND` | Exact field name not found; engine uses realized-vol seams as runtime proxies. |
| `realized_vol_current` | `PROVEN_PRESENT`, `PROVEN_CONSUMED`, `PROVEN_EXPLAINED` | input, fallback tests. |
| `realized_vol_post_close` | `PROVEN_PRESENT`, `PROVEN_CONSUMED`, `PROVEN_EXPLAINED` | input, forecast reason-code tests. |
| `expected_cost` | `PROVEN_PRESENT`, `PROVEN_CONSUMED`, `PROVEN_EXPLAINED` | `cost_feasibility_d.py`, runtime/export surfaces. |
| `expected_total_cost` | `NOT_FOUND` | Not found on Engine D local seam. |
| `expected_ce` | `PROVEN_PRESENT`, `PROVEN_CONSUMED`, `PROVEN_EXPLAINED` | exposed as `ce_expected`. |
| `reentry_cost_feasibility` | `DOC_ONLY` | addendum language exists; exact field name not found. |
| `reentry_window_status` | `NOT_FOUND` | Exact field name not found. |
| `reason_codes` | `PROVEN_PRESENT`, `PROVEN_EXPLAINED` | output payload, runtime/refusal tests. |

## First-Episode / Anti-Revenge Proof

Source: `src/engines/engine_d/first_episode_resolver_d.py`

```text
thresholds:
  THR-D_LOOKBACK
  THR-D_MIN_GAP
```

Source: `src/engines/engine_d/consecutive_stop_counter_d.py`

```text
policy defaults:
  stop limit = 1
  failsafe reset = 24h
```

Tests:
- `tests/test_engines/test_engine_d/test_first_episode_resolver_d.py::*`
- `tests/test_engines/test_engine_d/test_consecutive_stop_counter_d.py::*`
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py::test_runtime_surfaces_anti_revenge_observability_for_backtest`

Interpretation:
- Engine D does implement explicit first-episode and anti-revenge seams
- the state is explainable and visible in logs/hooks

## Cost / CE / Risk Consumption

Source: `src/engines/engine_d/cost_feasibility_d.py`

```text
ce_expected = (expected_gain - expected_cost) / holding_period
ev_net = candidate_size * (expected_gain - expected_cost)
```

Source: `src/engines/engine_d/engine_d_runtime_support.py`

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

Proven reason-code families:
- `engine_d.conviction.high`
- `engine_d.link_type.prior_trade`
- `engine_d.invalidation.present`
- `engine_d.forecast.volatility_proxy.realized_vol_post_close`
- `engine_d.forecast.volatility_proxy.realized_vol_current_fallback`
- `engine_d.economics.break_even_cleared`

Tests:
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py::test_forecast_reason_codes_include_engine_and_penalties`
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py::test_conditioning_state_contains_engine_internal_and_scoring_records`
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py::test_runtime_uses_current_realized_vol_fallback_when_post_close_vol_is_missing`
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py::test_runtime_surfaces_anti_revenge_observability_for_backtest`

## Missing Before Shadow

- Engine-specific replay execution-rate artifact
- Engine-specific executed-only net return
- Engine-specific true net-equity drawdown
- Explicit engine-specific shadow promotion artifact
- Explicit carriage of cost completeness / fee / impact / fill-realism / realized-slippage statuses

## Missing Before Micro-live

- All missing-before-shadow items
- capital-bucket viability for re-entry behavior
- per-engine refusal/rejection survival and sample-size artifact
- replay/live cost parity for Engine D promotion claims

