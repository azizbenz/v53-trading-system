# C/D Correction Patch Report

Date: `2026-05-01`
Scope: governance, readiness states, replay aggregate status carriage, cockpit visibility, and gap tracking for Engine C and Engine D.

## Patch Summary

- Added explicit `shared_physics_mapping_status` carriage for Engine C and Engine D with current value `PARTIAL_BY_DESIGN`.
- Added explicit C/D role metadata on the scoring/risk candidate rails and surfaced it on the cockpit engine-why surface.
- Added explicit `NOT_PROVEN` cost, fee, impact, fill-realism, and realized-slippage statuses on the C/D scoring and risk seams instead of relying on silent defaults.
- Extended replay engine aggregates additively with non-invented counts and promotion-readiness status placeholders.
- Added cockpit/operator visibility for missing promotion evidence so C/D remain non-green while replay/shadow economics are incomplete.
- Preserved existing `carriage_statuses=("local_math_only", "shared_scoring_physics_partial")`.

## What Was Not Changed

- Engine C strategy logic was not rewritten.
- Engine D strategy logic was not rewritten.
- No C/D local feature was force-mapped into A/B shared physics.
- No side logic was changed.
- No shorting or leverage was introduced.
- No executed-only return or true drawdown value was invented.
- Expected CE remains expected-only.

## Current Governed State

### Engine C

- `engine_role`: `Breakout / continuation engine with fake-breakout protection and toxic-flow veto/context.`
- `shared_physics_mapping_status`: `PARTIAL_BY_DESIGN`
- `promotion_readiness_status`: `ENGINE_PROMOTION_NOT_READY`

### Engine D

- `engine_role`: `Re-entry / second-chance engine with first-episode linkage, anti-revenge, reformation, and realized-vol context.`
- `shared_physics_mapping_status`: `PARTIAL_BY_DESIGN`
- `promotion_readiness_status`: `ENGINE_PROMOTION_NOT_READY`

## Replay Aggregate Additions

Additive per-engine fields now include:

- `engine_role`
- `shared_physics_mapping_status`
- `executed_count`
- `reduced_count`
- `rejected_count`
- `execution_rate`
- `fill_realism_status`
- `executed_only_net_return_status`
- `true_net_equity_drawdown_status`
- `shadow_confirmation_status`
- `promotion_status`

Fields that are not source-proven remain `None`, `NOT_PROVEN`, or `*_NOT_PROVEN`.

## Cockpit Operator Caveat

The cockpit now surfaces the following for Engine C and Engine D:

- engine role
- `PARTIAL_BY_DESIGN`
- promotion readiness status
- missing promotion evidence
- cost completeness status
- executed-only return status
- true drawdown status
- shadow confirmation status

Required caveat:

```text
Engine C/D local math is active, but A/B-style shared scoring physics mapping is PARTIAL_BY_DESIGN.
This is not a defect.
Promotion readiness still requires engine-specific replay/shadow economics.
```

## Tests

- `tests/test_engines/test_engine_c/test_engine_c_runtime.py`
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py`
- `tests/test_local_replay_runtime/test_replay_executor.py`
- `tests/cockpit/test_state_engine_why.py`

## Remaining Measured Gaps

- engine-specific replay/shadow promotion artifacts do not exist yet
- engine-specific executed-only net return is not proven
- engine-specific true net-equity drawdown is not proven
- engine-specific shadow confirmation artifacts are not proven
- engine-specific sample-size survival artifacts are not proven
- engine-specific fill/no-fill promotion economics are not proven
