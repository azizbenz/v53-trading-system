# Wave 2 Drawdown and Risk Proxy Audit

## Source
- `src/local_replay_runtime/replay_metrics_collector.py::_drawdown_proxy`

## Implemented formula
```text
running += record.gross_return
peak = max(peak, running)
worst = min(worst, running - peak)
drawdown_proxy = abs(worst)
```

## What it is
- A path-dependent loss proxy built on cumulative `gross_return`.
- It is a replay-level proxy for worst peak-to-trough loss on the gross-return path.

## What it is not
- Not a full equity-curve max drawdown on net returns after realized cost.
- Not a portfolio-aware drawdown across capital allocation.
- Not a promotion-grade downside metric by itself.

## Why the current label is mostly safe
- The producer and cockpit both call it `drawdown_proxy`.
- That naming is materially safer than calling it `max_drawdown`.

## Remaining risks
- `_replay_metrics.html` displays the numeric value without additional caveat.
- No explicit sample threshold is attached in `state_replay_metrics.py`.
- No evidence was found that promotion gates consume `drawdown_proxy` directly.

## Promotion eligibility
- `HUMAN_DECISION_REQUIRED`
- Until a true drawdown seam is proven, `drawdown_proxy` should not be treated as a decisive promotion/risk gate metric.

## Wave 2 verdict
- Formula status: `MATCH_INTERNAL_CONVENTION`
- Display status: safe only if it stays explicitly labeled `proxy`
- Producer patch: `NO`
