# SB-001 / SB-002 Remaining Gaps

Date: `2026-05-01`

The true-economics rails now exist, but promotion readiness is still not fully closed.

## Remaining open items

- Replay fee provenance remains `OPEN`.
- Replay impact provenance remains `OPEN`.
- Fill-realism proof remains `BLOCKED_BY_LIVE_TELEMETRY`.
- Replay/live cost parity remains `BLOCKED_BY_LIVE_TELEMETRY`.
- Capital-bucket viability for `400 / 500 / 1500 / 4000` remains `BLOCKED_BY_BACKTEST`.
- Engine C/D promotion artifacts remain `OPEN`.
- Engine C/D sample-size survival artifacts remain `OPEN`.

## Operational nuance

- Executed-only return is implemented, but any executed/reduced record without proven realized cost stays `EXECUTED_NET_RETURN_MISSING_REALIZED_COST`.
- True drawdown is implemented, but any replay/shadow run without explicit capital base stays `TRUE_NET_EQUITY_DRAWDOWN_MISSING_CAPITAL`.
- These fail-closed statuses are correct and must remain non-green.

## Do not regress

- Do not fold `expected_ce_net` into realized profitability claims.
- Do not use `drawdown_proxy` as a promotion-grade drawdown substitute.
- Do not invent per-engine profitability or drawdown when source proof is missing.
