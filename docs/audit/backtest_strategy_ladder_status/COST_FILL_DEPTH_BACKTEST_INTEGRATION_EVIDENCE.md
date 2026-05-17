# Cost / Fill / Depth Backtest Integration Evidence

## Overall verdict

`PARTIAL`

## Global replay/backtest rail status

| Field | Classification | Evidence | Reading |
|---|---|---|---|
| `fee_source_status` | `PRODUCED` | `replay_metrics_collector.py`; `strategy_ladder_detailed_replay.py`; `strategy_ladder_runner.py` | Explicit fee provenance is carried into ladder replay output. |
| `impact_source_status` | `PRODUCED` | same | Explicit impact provenance is carried. |
| `fill_realism_status` | `PRODUCED` | same; `shadow_execution_simulator.py` | Fill realism is explicit and fail-closed, but still non-green when only modeled. |
| `cost_parity_status` | `PRODUCED` | same | Replay/live parity stays explicit and blocked without telemetry. |
| `book_depth_source_status` | `PRODUCED` | same; `strategy_ladder_raw_window_extractor.py` | Depth status is explicit from raw-window stage through detailed replay. |
| `impact_depth_readiness_status` | `PRODUCED` | same | Promotion-grade depth readiness is explicit. |
| `shadow_extension_required` | `PRODUCED` | same | Extended-shadow doctrine is carried. |
| `minimum_shadow_days_required` | `PRODUCED` | same | Minimum shadow-day requirement is carried. |

## Carriage into downstream artifacts

| Artifact rail | Classification | Evidence | Reading |
|---|---|---|---|
| Engine promotion artifacts | `PRODUCED` | `strategy_ladder_runner.py`; `promotion_artifact_builder.py` | Engine artifacts are now fed from detailed replay output. |
| Pair promotion artifacts | `PRODUCED` | same | Pair artifacts are now fed from detailed replay output. |
| Strategy promotion artifacts | `PRODUCED` | same | Strategy artifacts are now fed from detailed replay output. |
| Capital bucket profiles | `PRODUCED` | `strategy_ladder_runner.py`; `capital_profile_builder.py` | Bucket profiles now carry these statuses from actual ladder replay output. |

## Special checks

| Check | Result | Evidence |
|---|---|---|
| Limited depth cannot become `depth20` | `PASS` | limited depth remains `BOOK_LIMITED_DEPTH_AVAILABLE` / `IMPACT_SOURCE_LIMITED_DEPTH_MODEL` |
| Missing depth cannot become zero impact | `PASS` | missing book remains explicit and non-green |
| Model-only fill cannot become measured fill | `PASS` | `FILL_REALISM_MODEL_ONLY` remains explicit |
| Replay/live parity cannot become proven without telemetry | `PASS` | default parity remains blocked or not proven without telemetry |

## Conclusion

The cost/fill/depth rail is now integrated through the Strategy Ladder path rather than only through the legacy replay export path. The verdict remains `PARTIAL` because the non-green states are still the correct reading until telemetry and depth quality are stronger.
