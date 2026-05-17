# True Net Equity Drawdown Spec

Purpose:
- define the promotion-grade drawdown rail distinct from replay `drawdown_proxy`

## Formula

```text
equity_t = initial_capital + cumulative_executed_net_pnl_t
running_peak_t = max(equity_0 ... equity_t)
drawdown_t = (running_peak_t - equity_t) / running_peak_t
max_drawdown = max(drawdown_t)
```

## Rules

- `drawdown_proxy` remains diagnostic only
- true drawdown requires ordered executed net PnL and a capital base
- if ordered executed net PnL or capital base is unavailable, status becomes `TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN`
- blocked or non-executed records must not influence this rail

## Status doctrine

Allowed status examples:

- `MEASURED`
- `PARTIAL`
- `TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN`
- `NOT_AVAILABLE`

## Promotion note

Without this rail:
- replay `drawdown_proxy` must remain non-promotion-grade
- capital-bucket promotion cannot claim true net-equity drawdown proof

## Backtest reporting note

Capital-bucket backtest reporting should not only say that a strategy "works".
It should also state:

- with which capital bucket
- on which pairs
- with which average trade size
- with which execution rate
- with which costs
- with which drawdown
- with which promotion status
