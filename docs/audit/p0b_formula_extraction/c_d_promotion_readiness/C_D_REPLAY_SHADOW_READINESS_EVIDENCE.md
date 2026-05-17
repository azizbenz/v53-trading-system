# C/D Replay And Shadow Readiness Evidence

## Shared Replay Artifact Proof

Source: `src/local_replay_runtime/replay_metrics_collector.py`

```text
ReplayEngineAggregate:
  engine_id
  record_count
  selected_count
  hard_blocked_count
  ce_net
  expected_cost_mean
  replay_expected_cost_model_mean
  realized_cost_mean
  gross_return_mean
```

Interpretation:
- replay artifacts do expose engine-specific aggregates
- they do not expose engine-specific executed counts, executed-only net return, or true drawdown

## Readiness Matrix

| Item | Engine C | Engine D | Evidence |
|---|---|---|---|
| replay artifacts exist | `PROVEN` | `PROVEN` | `ReplayEngineAggregate`, cockpit replay state |
| shadow artifacts exist | `NOT_PROVEN` | `NOT_PROVEN` | no engine-specific shadow artifact found |
| engine-specific replay metrics exist | `PROVEN` | `PROVEN` | replay collector and cockpit `engine_aggregates` |
| engine-specific execution rate exists | `NOT_PROVEN` | `NOT_PROVEN` | no per-engine executed-count metric exported |
| engine-specific cost drift exists | `NOT_PROVEN` | `NOT_PROVEN` | not found |
| engine-specific rejected/refused counts exist | `NOT_PROVEN` | `NOT_PROVEN` | only `hard_blocked_count` aggregate is present |
| engine-specific sample-size survival exists | `NOT_PROVEN` | `NOT_PROVEN` | no survival artifact found |
| engine-specific expected CE exists | `PROVEN` | `PROVEN` | `engine_aggregates[].ce_net` |
| engine-specific executed-only net return exists | `NOT_PROVEN` | `NOT_PROVEN` | not found |
| engine-specific true net-equity drawdown exists | `NOT_PROVEN` | `NOT_PROVEN` | not found |
| engine-specific promotion status exists | `NOT_PROVEN` | `NOT_PROVEN` | not found |

## Source-Level Caveats

From `src/cockpit/state_replay_metrics.py`:

```text
expected_ce_caveat:
  "Expected CE over replay DTR records; not realized profitability."

drawdown_proxy_caveat:
  "Gross-return proxy; not net-equity max drawdown and not promotion-grade."
```

From Wave 5 audit:

```text
drawdown_proxy_promotion_grade=false
```

## Shadow Readiness Conclusion

- Both engines are architecturally `shadow_capable`.
- Neither engine is proven `SHADOW_READY`.
- Promotion-grade per-engine replay/shadow artifacts are missing.
- Current safest verdict for both engines is `NOT_SHADOW_READY`.

