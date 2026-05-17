# SB-003 / SB-004 Remaining Gaps

Date: `2026-05-01`

The replay cost-provenance rails are now explicit and fail-closed, but promotion-grade execution economics are still not fully closed.

## Remaining open items

- Replay fee provenance remains `IN_PROGRESS`, not fully resolved, because the rail can carry `FEE_SOURCE_CONFIGURED`, `FEE_SOURCE_EXCHANGE_METADATA`, `FEE_SOURCE_ESTIMATED`, or `FEE_SOURCE_NOT_PROVEN` without proving a universally measured replay fee source.
- Replay impact provenance remains `IN_PROGRESS`, not fully resolved, because the rail can carry `IMPACT_SOURCE_DEPTH20_MODEL`, `IMPACT_SOURCE_ESTIMATED`, `IMPACT_SOURCE_SYNTHETIC`, or `IMPACT_SOURCE_NOT_PROVEN` without proving a universally measured replay impact source.
- Fill-realism proof remains `BLOCKED_BY_LIVE_TELEMETRY`.
- Replay/live cost parity remains `BLOCKED_BY_LIVE_TELEMETRY`.
- Capital-bucket viability for `400 / 500 / 1500 / 4000` remains `BLOCKED_BY_BACKTEST`.
- Engine C/D promotion artifacts remain `OPEN`.
- Engine C/D sample-size survival artifacts remain `OPEN`.

## Operational nuance

- A configured or exchange-metadata fee source is explicit and auditable, but it is not the same thing as a measured live fee ledger.
- A depth20 impact model is explicit and auditable, but it is not the same thing as measured live market impact.
- `COST_MODEL_COMPLETE` remains intentionally strict and is blocked by missing fill realism, replay/live parity, or realized-cost-source proof even when fee and impact statuses are explicit.
- Executed-only return can carry a numeric diagnostic value while still remaining `EXECUTED_NET_RETURN_NOT_PROVEN` if cost completeness is partial.
- True drawdown can remain blocked by the executed-return guard if replay economics are still partial.

## Do not regress

- Do not fold `expected_ce_net` into realized profitability claims.
- Do not treat configured, estimated, or synthetic replay cost as measured venue cost.
- Do not downgrade missing fee or impact to zero.
- Do not allow `COST_MODEL_COMPLETE` when fee/impact/fill/parity proof is incomplete.
- Do not let executed-only profitability or true drawdown turn green while cost completeness is partial.
