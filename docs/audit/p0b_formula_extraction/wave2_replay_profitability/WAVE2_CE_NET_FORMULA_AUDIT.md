# Wave 2 CE Net Formula Audit

## What `ce_net` is in current code
- Source:
  - `src/local_replay_runtime/shadow_execution_simulator.py`
  - `src/local_replay_runtime/replay_metrics_collector.py`
- Per-record definition:
  - `ce_expected = (expected_edge_bps / 10_000.0) - expected_cost`
- Aggregate definition:
  - `ce_net = sum(record.ce_expected for record in records)`

## Economic meaning
- `ce_net` is **expected CE**, not realized CE.
- It is already **net of expected cost** at the record level.
- It is not mixed with realized cost in the replay collector formula.
- It is therefore an **ex-ante economic aggregate**, not a realized PnL aggregate.

## Are blocked / no-trade / phantom records included?
- Yes.
- `replay_metrics_collector.py` sums `record.ce_expected` across all DTR records.
- In `shadow_execution_simulator.py`, `ce_expected` is computed even when:
  - `decision_state == HARD_BLOCKED`
  - `decision_state == REJECTED_RANKING`
  - `decision_state == PHANTOM`
  - execution factor is `0.0`
- This means blocked and phantom records can still contribute ex-ante CE evidence.

## Is it gross or net of all expected costs?
- Net of expected costs only.
- It is not net of realized costs.
- The expected-cost components are inherited from `_expected_cost(...)`:
  - spread
  - slippage
  - latency penalty
- There is no realized-fill adjustment inside `ce_expected`.

## Pair / engine / global reconciliation
- Pair, engine, and global `ce_net` all use the same per-record field: `record.ce_expected`.
- Structural reconciliation is strong because all three are built from the same DTR set.
- Exact equality of:
  - `sum(pair.ce_net) == global.ce_net`
  - `sum(engine.ce_net) == global.ce_net`
  is very likely under typical data, but not explicitly tested and may be sensitive to per-group rounding to 6 decimals.

## Can `ce_net` support a profitability verdict?
- It can support an **expected-economics** verdict.
- It cannot, by itself, support a **realized-profitability** verdict.
- It should not be described as net realized PnL.

## Cockpit safety
- Current cockpit risk:
  - `state_replay_metrics.py` defaults `ce_net` to `0.0`
  - `_replay_metrics.html` colors `ce_net >= 0` as positive
- Therefore:
  - `ce_net` must not be shown green when `total_records == 0`
  - `ce_net` must not be read as realized performance

## Verdict
- `ce_net` formula: `MATCH_INTERNAL_CONVENTION`
- `ce_net` display semantics: `HUMAN_DECISION_REQUIRED`
- Producer patch in Wave 2: `NO`

## Safe recommendation
- Keep producer formula unchanged.
- Future cockpit/state patch should label `ce_net` as:
  - `expected_ce_net`
  - or at minimum `expected CE net`
- Future cockpit/state patch should prevent green profitability signaling when:
  - `total_records == 0`
  - source is stale
  - replay is partial / insufficient sample
