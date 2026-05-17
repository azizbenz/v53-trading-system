# Detailed Depth Replay Contract

Date: `2026-05-03`

## Canonical output

`detailed_replay/{candidate_id}.json`

## Required fields

- `candidate_id`
- `pair`
- `engine_id`
- `strategy_id`
- `capital_bucket`
- `timestamp_ms`
- `execution_state`
- `executed_notional`
- `reduced_notional`
- `no_fill_flag`
- `partial_fill_flag`
- `expected_ce_net`
- `executed_only_net_return`
- `executed_only_net_return_status`
- `fee_source_status`
- `impact_source_status`
- `fill_realism_status`
- `cost_parity_status`
- `book_depth_source_status`
- `impact_depth_readiness_status`
- `reason_codes`
- `input_data_hash`
- `method_version_hash`
- `artifact_hash`

## Allowed stage readings

- `DETAILED_REPLAY_READY`
- `DETAILED_REPLAY_PARTIAL`
- `DETAILED_REPLAY_NOT_PROVEN`

## Required rules

- Detailed replay validates; it does not invent.
- No-fill and partial-fill are first-class outcomes.
- `expected_ce_net` remains expected-only.
- Missing realized cost keeps executed-only return non-proven.
- Missing capital keeps true drawdown non-proven on downstream rails.
- Limited depth, top-of-book only, or missing depth remain non-green.
- Replay/live parity remains blocked without telemetry.
