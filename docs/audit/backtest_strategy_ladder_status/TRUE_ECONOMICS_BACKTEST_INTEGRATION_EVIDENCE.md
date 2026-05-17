# True Economics Backtest Integration Evidence

## Overall verdict

`PARTIAL`

## Guard rails already present

- `expected_ce_net` remains expected-only on the replay and Strategy Ladder rails.
- `drawdown_proxy` remains diagnostic-only.
- `executed_only_net_return` and `true_net_equity_max_drawdown` remain fail-closed when realized cost or capital base is missing.

Primary source files:

- `src/local_replay_runtime/replay_metrics_collector.py`
- `src/local_replay_runtime/replay_executor.py`
- `src/local_replay_runtime/strategy_ladder_detailed_replay.py`
- `src/local_replay_runtime/strategy_ladder_runner.py`
- `src/local_replay_runtime/promotion_artifact_builder.py`
- `src/interface_contracts/capital_profile_contracts.py`
- `src/interface_contracts/promotion_artifact_contracts.py`

## Level-by-level classification

| Level | `executed_only_net_return` | `true_net_equity_max_drawdown` | Evidence | Reading |
|---|---|---|---|---|
| Global | `PRODUCED` | `PRODUCED` | `ReplayMetricsSummary`; global ladder promotion bundle | Global replay economics are source-proven and remain governed. |
| Capital bucket | `PRODUCED` | `PRODUCED` | `strategy_ladder_runner.py`; `capital_profile_builder.py` | Bucket-level economics are now generated from detailed replay output. |
| Engine | `PRODUCED` | `PRODUCED` | `promotion_artifact_builder.py`; Strategy Ladder promotion export feed | Engine-level carriage is produced through the existing rail. |
| Pair | `PRODUCED` | `PRODUCED` | same | Pair-level true economics are produced through the existing rail. |
| Strategy | `PRODUCED` | `PRODUCED` | same | Strategy-level true economics are produced through the existing rail. |

## Important nuance

The rail is implemented end to end, but that does not mean every future run will be promotion-grade.

- If realized cost proof is incomplete, executed-only return remains non-proven.
- If capital base is missing, true drawdown remains non-proven.
- If cost/fill/depth/sample-size blockers remain partial, promotion readiness stays non-green even though the economics fields exist.

## Special-rule checks

| Rule | Result | Evidence |
|---|---|---|
| `drawdown_proxy` is not used as true drawdown | `PASS` | drawdown proxy remains distinct and diagnostic-only in replay and promotion artifacts |
| `expected_ce_net` is not used as realized profitability | `PASS` | replay and ladder rails preserve expected-only semantics |

## Conclusion

True-economics integration is now real across global, capital-bucket, engine, pair, and strategy ladder outputs. The verdict remains `PARTIAL` because the rails are correctly fail-closed and still depend on measured cost/fill/depth/parity/sample-size evidence before any readiness claim can become green.
