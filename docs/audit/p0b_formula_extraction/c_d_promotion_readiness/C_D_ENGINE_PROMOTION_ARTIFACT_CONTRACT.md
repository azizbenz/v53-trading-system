# C/D Engine Promotion Artifact Contract

Date: `2026-05-01`
Scope: future engine-specific replay/shadow promotion artifacts for Engine C and Engine D.

## Paths

- `engine_promotion/engine_c/{run_id}.json`
- `engine_promotion/engine_d/{run_id}.json`

## Required Fields

```json
{
  "engine_id": "engine_c",
  "engine_role": null,
  "shared_physics_mapping_status": "PARTIAL_BY_DESIGN",
  "run_id": null,
  "capital_bucket": null,
  "pair_universe": [],
  "record_count": null,
  "selected_count": null,
  "hard_blocked_count": null,
  "rejected_count": null,
  "executed_count": null,
  "reduced_count": null,
  "no_fill_count": null,
  "execution_rate": null,
  "partial_fill_rate": null,
  "no_fill_rate": null,
  "sample_size_survival_status": "NOT_PROVEN",
  "expected_ce_net": null,
  "executed_only_net_return": null,
  "true_net_equity_max_drawdown": null,
  "expected_cost_mean": null,
  "expected_total_cost_mean": null,
  "cost_model_completeness_status": "NOT_PROVEN",
  "fee_source_status": "NOT_PROVEN",
  "impact_source_status": "NOT_PROVEN",
  "fill_realism_status": "NOT_PROVEN",
  "realized_slippage_status": "NOT_PROVEN",
  "shadow_confirmation_status": "NOT_PROVEN",
  "promotion_status": "NOT_SHADOW_READY",
  "reason_codes_top": [],
  "artifact_hash": null,
  "input_data_hash": null,
  "method_version_hash": null,
  "created_at": null,
  "expires_at": null
}
```

## Rules

- Missing measured fields must be `null` or `NOT_PROVEN`, never fake zero.
- `expected_ce_net` remains expected-only.
- `executed_only_net_return` is required for promotion-grade readiness.
- `true_net_equity_max_drawdown` is required for promotion-grade readiness.
- `promotion_status` must stay non-green until replay plus shadow evidence exists.
- The contract must not force-map C/D local fields into A/B shared physics.

## Current Doctrine

### Engine C

- role: breakout / continuation / fake-breakout protection / toxic-flow veto-context
- `shared_physics_mapping_status = PARTIAL_BY_DESIGN`

### Engine D

- role: re-entry / second chance / first-episode linkage / anti-revenge / reformation / realized-vol context
- `shared_physics_mapping_status = PARTIAL_BY_DESIGN`

## Current Non-Green Requirements

Promotion must remain non-green when any of the following is missing:

- engine-specific executed-only net return
- engine-specific true net-equity drawdown
- engine-specific cost completeness
- engine-specific fill realism
- engine-specific shadow confirmation artifact
