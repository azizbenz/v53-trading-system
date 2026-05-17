# Capital Profile Artifact Contract

Artifact path:

```text
capital_profiles/{capital_bucket}.json
```

Purpose:
- define the governed pair universe and capital-readiness envelope for one proven capital bucket
- separate backtest proposal, replay validation, shadow confirmation, and VPS enforcement

## Required JSON shape

```json
{
  "capital_bucket": 400,
  "quote_currency": "USDT",
  "allowed_pairs": [],
  "blocked_pairs": [],
  "max_active_pairs": 0,
  "max_position_notional_per_pair": 0,
  "min_trade_notional_buffer": 0,
  "min_notional_block_rate": null,
  "cost_block_rate": null,
  "fee_survival_rate": null,
  "slippage_survival_rate": null,
  "impact_survival_rate": null,
  "fill_rate": null,
  "partial_fill_rate": null,
  "execution_rate": null,
  "expected_ce_net": null,
  "executed_only_net_return": null,
  "true_net_equity_max_drawdown": null,
  "capital_fragmentation_status": "NOT_PROVEN",
  "small_capital_exclusion_rate": null,
  "recommendation": "NEEDS_MORE_DATA",
  "promotion_status": "BACKTEST_NOT_RUN",
  "shadow_required_days": 30,
  "backtest_run_id": null,
  "replay_run_id": null,
  "shadow_run_id": null,
  "method_version_hash": null,
  "input_data_hash": null,
  "artifact_hash": null,
  "created_at": null,
  "expires_at": null
}
```

## Rules

- no invented measured values
- missing measured fields stay `null` or explicit `NOT_PROVEN`, never fake zero
- `expected_ce_net` remains expected-only and must not be renamed into realized profitability
- `executed_only_net_return` and `true_net_equity_max_drawdown` may stay `null` until the corresponding rails exist
- artifact must be hashable
- artifact must be stale-detectable via `created_at` and `expires_at`
- VPS must reject missing, stale, or hash-invalid artifact state for micro-live/live enforcement

## Promotion statuses

Allowed values:

- `BACKTEST_NOT_RUN`
- `BACKTEST_CANDIDATE`
- `REPLAY_CONFIRMED`
- `SHADOW_CONFIRMED`
- `MICRO_LIVE_ELIGIBLE`
- `LIVE_ELIGIBLE`
- `NEEDS_MORE_DATA`

## Interpretation

- backtest proposes the bucket pair universe
- replay validates execution realism
- shadow confirms operational viability
- VPS enforces only `allowed_pairs` for the active proven bucket
