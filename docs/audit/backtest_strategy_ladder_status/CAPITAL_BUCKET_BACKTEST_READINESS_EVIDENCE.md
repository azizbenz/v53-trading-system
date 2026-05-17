# Capital Bucket Backtest Readiness Evidence

## Overall verdict

`PIPELINE_EXISTS_BUT_NO_MEASURED_DATA`

## Source proof

- `src/interface_contracts/capital_profile_contracts.py` defines canonical required buckets:
  `REQUIRED_CAPITAL_BUCKETS = (400, 500, 1500, 4000)`.
- `src/local_replay_runtime/strategy_ladder_runner.py` now generates `capital_profiles/{bucket}.json` from actual detailed replay output.
- `src/backtest_artifact_import/capital_profile_builder.py` builds, validates, hashes, writes, and enforces capital bucket profiles.
- `src/portfolio_minimal/allocation_router/capital_viability.py` provides min-notional and fragmentation analysis used by the runner.

## Critical limitation

The runner can now produce measured bucket artifacts, but no audited historical Strategy Ladder run outputs are checked in for `400 / 500 / 1500 / 4000`.

That means the pipeline is real, but promotion-grade measured bucket evidence is still absent at repo level.

## Per-bucket classification

| Bucket | Classification | Evidence | Reading |
|---|---|---|---|
| `400` | `READY_TO_RUN` | canonical runner + bucket builder + targeted tests | The bucket rail can now be run from detailed replay output, but no audited historical output is present. |
| `500` | `READY_TO_RUN` | same | same |
| `1500` | `READY_TO_RUN` | same | same |
| `4000` | `READY_TO_RUN` | same | same |

## Required fields status

| Field group | Status | Evidence | Reading |
|---|---|---|---|
| `allowed_pairs` / `blocked_pairs` / `max_active_pairs` | `PRODUCED` | `strategy_ladder_runner.py`; `capital_profile_builder.py` | Produced from detailed replay output, but still empty/non-green when evidence is weak or absent. |
| `min_notional_block_rate` | `PRODUCED` | same; `capital_viability.py` | Produced from bucket replay evidence and fail-closed helper inputs. |
| `capital_fragmentation_rate` | `PRODUCED` | same | Produced from bucket replay evidence and fragmentation analysis. |
| `executed_only_net_return` | `PRODUCED` | same | Produced from detailed replay output for each bucket. |
| `true_net_equity_max_drawdown` | `PRODUCED` | same | Produced from detailed replay output for each bucket. |
| `cost_model_completeness_status` / `fill_realism_status` / `book_depth_source_status` / `sample_size_survival_status` / `promotion_status` | `PRODUCED` | same | Produced and kept fail-closed; non-ready statuses are expected until real evidence is sufficient. |

## Conclusion

Capital-ladder generation is no longer contract-only. It is wired into the canonical Strategy Ladder runner. The remaining blocker is the absence of audited historical bucket runs, not the absence of the pipeline itself.
