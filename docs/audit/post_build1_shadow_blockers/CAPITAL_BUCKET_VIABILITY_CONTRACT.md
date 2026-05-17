# V5.3 Capital Bucket Viability Contract

Date: `2026-05-02`

## Scope

This contract governs the per-bucket capital-readiness rail for:

- `400`
- `500`
- `1500`
- `4000`

It covers:

- per-bucket profile artifacts
- pair allow/block governance
- min-notional viability evidence
- fragmentation evidence
- promotion-ready vs non-proven semantics

It does not invent measured backtest or replay results.

## Canonical artifact path

```text
capital_profiles/{capital_bucket}.json
```

## Required per-bucket fields

```json
{
  "schema_version": "v1",
  "capital_bucket": 400,
  "quote_currency": "USDT",
  "initial_capital": null,
  "usable_sizing_capital": null,
  "reserve_buffer": null,
  "capital_source_status": "CAPITAL_SOURCE_NOT_PROVEN",
  "pair_universe": [],
  "allowed_pairs": [],
  "blocked_pairs": [],
  "max_active_pairs": null,
  "record_count": null,
  "candidate_count": null,
  "selected_count": null,
  "executed_count": null,
  "reduced_count": null,
  "no_fill_count": null,
  "hard_blocked_count": null,
  "rejected_count": null,
  "min_notional_block_rate": null,
  "capital_fragmentation_rate": null,
  "size_reduction_rate": null,
  "pair_universe_too_wide_status": "NOT_PROVEN",
  "expected_ce_net": null,
  "executed_only_net_return": null,
  "executed_only_net_return_status": "EXECUTED_NET_RETURN_NOT_PROVEN",
  "true_net_equity_max_drawdown": null,
  "true_net_equity_drawdown_status": "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN",
  "fee_source_status": "FEE_SOURCE_NOT_PROVEN",
  "impact_source_status": "IMPACT_SOURCE_NOT_PROVEN",
  "fill_realism_status": "FILL_REALISM_NOT_PROVEN",
  "cost_parity_status": "REPLAY_LIVE_COST_PARITY_NOT_PROVEN",
  "cost_model_completeness_status": "COST_MODEL_NOT_PROVEN",
  "book_depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
  "impact_depth_readiness_status": "BOOK_DEPTH_NOT_PROVEN",
  "execution_rate": null,
  "partial_fill_rate": null,
  "no_fill_rate": null,
  "sample_size_survival_status": "SAMPLE_SIZE_NOT_PROVEN",
  "promotion_status": "CAPITAL_BUCKET_NOT_PROVEN",
  "promotion_blockers": [],
  "artifact_hash": null,
  "input_data_hash": null,
  "method_version_hash": null,
  "created_at": null,
  "expires_at": null
}
```

## Promotion statuses

Allowed values:

- `CAPITAL_BUCKET_READY`
- `CAPITAL_BUCKET_NOT_PROVEN`
- `CAPITAL_BUCKET_BLOCKED_BY_BACKTEST`
- `CAPITAL_BUCKET_BLOCKED_BY_MIN_NOTIONAL`
- `CAPITAL_BUCKET_BLOCKED_BY_FRAGMENTATION`
- `CAPITAL_BUCKET_BLOCKED_BY_COST_COMPLETENESS`
- `CAPITAL_BUCKET_BLOCKED_BY_FILL_REALISM`
- `CAPITAL_BUCKET_BLOCKED_BY_DRAWDOWN`
- `CAPITAL_BUCKET_BLOCKED_BY_DEPTH`
- `CAPITAL_BUCKET_BLOCKED_BY_SAMPLE_SIZE`

## Pair decision statuses

Allowed values:

- `PAIR_ALLOWED`
- `PAIR_BLOCKED_MIN_NOTIONAL`
- `PAIR_BLOCKED_COST_COMPLETENESS`
- `PAIR_BLOCKED_DEPTH_LIMITATION`
- `PAIR_BLOCKED_FILL_REALISM`
- `PAIR_BLOCKED_NEGATIVE_EXECUTED_RETURN`
- `PAIR_BLOCKED_DRAWDOWN`
- `PAIR_BLOCKED_SAMPLE_SIZE`
- `PAIR_NOT_PROVEN`

## Min-notional reason codes

Required reason codes:

- `MIN_NOTIONAL_NOT_VIABLE_FOR_BUCKET`
- `PAIR_BLOCKED_BY_MIN_NOTIONAL`
- `PAIR_BLOCKED_BY_SIZE_REDUCTION`
- `PAIR_BLOCKED_BY_CAPITAL_FRAGMENTATION`

## Fragmentation statuses

Allowed values:

- `FRAGMENTATION_ACCEPTABLE`
- `FRAGMENTATION_HIGH`
- `PAIR_UNIVERSE_TOO_WIDE_FOR_CAPITAL`
- `FRAGMENTATION_NOT_PROVEN`

## Enforcement statuses

Allowed values:

- `CAPITAL_PROFILE_VALID`
- `CAPITAL_PROFILE_MISSING`
- `CAPITAL_PROFILE_STALE`
- `CAPITAL_PROFILE_HASH_INVALID`
- `CAPITAL_PROFILE_NOT_PROVEN`
- `NO_SUBMIT_CAPITAL_PROFILE_INVALID`

## Rules

- `400` and `500` capital must not inherit the same pair universe as `1500` and `4000` by default.
- `allowed_pairs` must be measured or remain empty / `NOT_PROVEN`.
- `blocked_pairs` must carry explicit reason codes.
- `max_active_pairs` must be bucket-specific.
- Missing measured values stay `null` or explicit `NOT_PROVEN`, never fake zero.
- `expected_ce_net` is expected-only and cannot promote a bucket alone.
- `executed_only_net_return` and `true_net_equity_max_drawdown` are required for promotion-grade bucket readiness.
- `cost_model_completeness_status` must stay non-green when fee, impact, fill realism, depth readiness, or replay/live parity is partial.
- Limited depth cannot masquerade as `BOOK_DEPTH20_AVAILABLE`.
- Static config pair lists must not override a governed capital profile.
- Missing, stale, or hash-invalid capital profiles must fail closed for `MICRO_LIVE` and `LIVE`.

## Implemented rail in current codebase

Typed contracts and helpers now exist in:

- `src/interface_contracts/capital_profile_contracts.py`
- `src/backtest_artifact_import/capital_profile_builder.py`
- `src/portfolio_minimal/allocation_router/capital_viability.py`
- `src/local_replay_runtime/artifact_exporter.py`
- `src/local_replay_runtime/replay_executor.py`
- `src/local_replay_runtime/replay_metrics_collector.py`
- `src/cockpit/state_replay_metrics.py`
- `src/cockpit/state_economic_sterilization.py`
- `src/cockpit/state_system_flow.py`

Current implementation status:

- contract exists
- deterministic artifact hash exists
- contract-validation `NOT_PROVEN` profiles can be generated for all required buckets
- replay exports can carry `capital_profiles/{bucket}.json`
- replay and cockpit now stay non-green when capital-profile evidence is missing
- enforcement helper exists for validation, bucket selection, and no-submit semantics

Still not claimed by this contract:

- measured bucket viability
- proven `allowed_pairs`
- promotion-ready `max_active_pairs`
- full VPS/runtime integration proof

