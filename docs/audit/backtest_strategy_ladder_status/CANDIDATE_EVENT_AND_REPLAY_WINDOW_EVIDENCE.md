# Candidate Event And Replay Window Evidence

## Overall verdict

`READY`

## Intended flow versus current source

Target industrial flow:

`raw data -> feature store -> quick backtest -> candidate events -> raw windows around candidates -> depth20 detailed replay -> final execution realism report`

The current source now implements the candidate-event, raw-window, and detailed replay stages in the canonical Strategy Ladder runner.

## Capability table

| Capability | Classification | Evidence | Reading |
|---|---|---|---|
| Candidate-event export | `READY` | `src/local_replay_runtime/strategy_ladder_candidate_discovery.py`; `scripts/run_backtest_strategy_ladder.py`; `tests/test_local_replay_runtime/test_strategy_ladder_runner.py` | Canonical candidate export now exists. |
| Candidate timestamp list | `READY` | `StrategyLadderCandidateEvent.timestamp_ms` / `timestamp_ns`; tests assert required timestamp presence | Candidate timestamps are mandatory and source-proven. |
| Candidate pair list | `READY` | same | Pair identity is canonical on every candidate event. |
| Candidate engine/source | `READY` | same | Engine/source identity is canonical on every candidate event. |
| Raw-window extractor | `READY` | `src/local_replay_runtime/strategy_ladder_raw_window_extractor.py`; tests | Deterministic raw-window extraction now exists. |
| Depth20 replay-window loader | `READY` | `src/local_replay_runtime/strategy_ladder_detailed_replay.py`; tests | Candidate-window detailed replay now exists and preserves limited/missing depth rather than faking depth20. |
| Fill/slippage/partial/no-fill replay | `READY` | same; `shadow_execution_simulator.py`; tests | Detailed replay preserves no-fill and partial-fill outcomes. |
| Final replay report | `READY` | `strategy_ladder_runner.py`; `reports/strategy_ladder_report.md`; `reports/strategy_ladder_summary.json` | Governed ladder reports are now emitted. |

## Important nuance

- Fast discovery uses `COMPAT_FEATURE_DISCOVERY`.
- That mode is accepted for v1 and explicitly labeled as not live-engine parity.
- Depth20 availability remains data-dependent. The existence of the stage does not guarantee that every future run has promotion-grade depth inputs.

## Conclusion

The canonical candidate-event -> raw-window -> detailed replay chain is now implemented and tested. Remaining limits are about governed inputs and evidence quality, not about the absence of these stages.
