# V5.3 Replay / Live Cost Parity Contract

Date: `2026-05-02`

## Scope

This contract governs replay-to-shadow/live cost parity evidence and prevents replay expected cost from being presented as realized live cost.

## Required fields

- `cost_parity_status`
- `replay_cost_components`
- `shadow_cost_components`
- `live_cost_components`
- `replay_fee_bps`
- `shadow_fee_bps`
- `live_fee_bps`
- `replay_impact_bps`
- `shadow_impact_bps`
- `live_impact_bps`
- `replay_slippage_bps`
- `shadow_slippage_bps`
- `live_slippage_bps`
- `replay_fill_ratio`
- `shadow_fill_ratio`
- `live_fill_ratio`
- `cost_drift_bps`
- `cost_drift_status`
- `parity_sample_count`
- `parity_window_start`
- `parity_window_end`
- `parity_input_hash`
- `parity_policy_version`

## Allowed statuses

- `REPLAY_LIVE_COST_PARITY_PROVEN`
- `REPLAY_SHADOW_COST_PARITY_PROVEN`
- `REPLAY_LIVE_COST_PARITY_PARTIAL`
- `REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY`
- `REPLAY_LIVE_COST_PARITY_NOT_PROVEN`
- `REPLAY_LIVE_COST_PARITY_MISSING`

## Rules

- Replay/live parity cannot be `PROVEN` without telemetry.
- Replay/shadow parity can be partial only if shadow telemetry exists.
- Cost parity must compare named components, not only total cost.
- If fee, impact, slippage, or fill components are missing, parity cannot be complete.
- Replay expected cost remains distinct from live realized cost.
- Missing parity must keep promotion readiness non-green.

## Current implementation note

The current replay rail exports parity status additively and conservatively:

- `cost_parity_status = REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY` by default
- named replay-side components are exported when known
- shadow/live-side components remain empty until measured telemetry exists

This closes the semantic ambiguity without claiming telemetry-backed parity that does not yet exist.
