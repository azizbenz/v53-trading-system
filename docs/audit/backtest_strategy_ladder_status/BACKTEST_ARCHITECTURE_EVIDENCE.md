# Backtest Architecture Evidence

## Overall classification

`PARTIALLY_UPDATED_REPLAY_BACKTEST`

## Why it is not `OLD_COARSE_BACKTEST`

- `scripts/run_backtest_strategy_ladder.py` now provides a canonical Strategy Ladder entrypoint.
- `src/local_replay_runtime/strategy_ladder_runner.py` orchestrates the full v1 ladder chain across feature loading, candidate discovery, raw windows, detailed replay, capital profiles, promotion artifacts, sample-size artifacts, and reports.
- `src/local_replay_runtime/strategy_ladder_feature_store.py`, `strategy_ladder_candidate_discovery.py`, `strategy_ladder_raw_window_extractor.py`, and `strategy_ladder_detailed_replay.py` provide dedicated ladder stages rather than a one-file coarse PnL export.
- `src/cockpit/action_support.py`, `src/cockpit/runtime_support.py`, and `src/cockpit/templates/pages/backtest.html` now expose a Strategy Ladder job kind and status projection.

## Why it is still not `STRATEGY_LADDER_READY`

- The fast stage uses `COMPAT_FEATURE_DISCOVERY`, which is accepted for v1 but is explicitly not live-engine parity.
- The runner still does not recompute A/B/C/D decisions from raw market history through canonical live engine, scoring, risk, and portfolio execution paths.
- Promotion-grade depth, fill, and parity proof still depend on real input quality and external telemetry.
- Audited historical measured ladder artifacts are not yet checked in for `400 / 500 / 1500 / 4000`.

## Capability table

| Capability | Implementation status | Test status | Evidence | Audit reading |
|---|---|---|---|---|
| Historical dataset input | `IMPLEMENTED` | `TESTED` | `scripts/run_local_replay_export.py`; `src/local_replay_runtime/historical_data_gateway.py`; `tests/test_local_replay_runtime/test_historical_data_gateway.py` | The legacy replay/export runner still supports governed historical datasets. |
| Historical snapshot-batch input | `IMPLEMENTED` | `TESTED` | `src/local_replay_runtime/historical_snapshot_loader.py`; `src/local_replay_runtime/replay_event_router.py`; `tests/test_local_replay_runtime/test_historical_snapshot_loader.py`; `tests/test_local_replay_runtime/test_replay_event_router.py` | Snapshot-batch normalization remains available on the legacy replay rail. |
| Feature-store input | `IMPLEMENTED` | `TESTED` | `src/local_replay_runtime/strategy_ladder_feature_store.py`; `tests/test_local_replay_runtime/test_strategy_ladder_runner.py` | The Strategy Ladder runner now has an explicit feature/gold-store input seam. |
| Engine A/B/C/D execution from raw history | `PARTIAL` | `TESTED` | `src/local_replay_runtime/strategy_ladder_candidate_discovery.py`; `src/local_replay_runtime/strategy_ladder_detailed_replay.py`; tests on `COMPAT_FEATURE_DISCOVERY` | Engine identity and downstream replay are source-proven, but raw-history live-engine recomputation is not. |
| Portfolio selection | `PARTIAL` | `TESTED` | `src/backtest_artifact_import/capital_profile_builder.py`; `src/portfolio_minimal/allocation_router/capital_viability.py`; `src/local_replay_runtime/strategy_ladder_runner.py` | Bucket viability and pair blocking are computed, but this is not a full raw-history portfolio runtime. |
| Risk/scoring routing | `PARTIAL` | `TESTED` | `src/local_replay_runtime/strategy_ladder_runner.py`; existing replay lineage fields and promotion builders | Risk/scoring semantics are carried through the ladder, but live runtime recomputation is not performed from raw history. |
| Execution-cost model | `PARTIAL` | `TESTED` | `src/local_replay_runtime/strategy_ladder_detailed_replay.py`; `src/local_replay_runtime/shadow_execution_simulator.py`; `src/local_replay_runtime/replay_metrics_collector.py` | The execution-realism rail is real and fail-closed, but promotion-grade completeness is still partial by doctrine. |
| Capital buckets | `IMPLEMENTED` | `TESTED` | `src/local_replay_runtime/strategy_ladder_runner.py`; `src/backtest_artifact_import/capital_profile_builder.py`; `tests/test_local_replay_runtime/test_strategy_ladder_runner.py` | The runner now generates `capital_profiles/{bucket}.json` from detailed replay output. |
| Candidate events | `IMPLEMENTED` | `TESTED` | `src/local_replay_runtime/strategy_ladder_candidate_discovery.py`; `tests/test_local_replay_runtime/test_strategy_ladder_runner.py` | Canonical candidate export now exists with timestamp, pair, engine, strategy, and hashes. |
| Depth replay windows | `IMPLEMENTED` | `TESTED` | `src/local_replay_runtime/strategy_ladder_raw_window_extractor.py`; `src/local_replay_runtime/strategy_ladder_detailed_replay.py`; `tests/test_local_replay_runtime/test_strategy_ladder_runner.py` | Candidate-window extraction and detailed replay now exist, while depth quality remains data-dependent. |
| Artifact export | `IMPLEMENTED` | `TESTED` | `src/local_replay_runtime/strategy_ladder_runner.py`; `src/local_replay_runtime/artifact_exporter.py`; `tests/test_local_replay_runtime/test_strategy_ladder_runner.py` | The runner now emits governed ladder reports plus capital and promotion artifacts. |

## Source-level runner reading

- `scripts/run_backtest_strategy_ladder.py` is the canonical ladder entrypoint.
- `src/local_replay_runtime/strategy_ladder_runner.py` is the orchestrator.
- `src/local_replay_runtime/strategy_ladder_feature_store.py` is the governed feature/gold-store seam.
- `src/local_replay_runtime/strategy_ladder_candidate_discovery.py` provides canonical candidate export in accepted compatibility mode.
- `src/local_replay_runtime/strategy_ladder_raw_window_extractor.py` provides deterministic raw-window extraction.
- `src/local_replay_runtime/strategy_ladder_detailed_replay.py` validates candidate windows with the existing replay-execution realism rail.

## Conclusion

The canonical architecture is no longer just a replay/export rail. A real Strategy Ladder runner now exists. It still remains `PARTIALLY_UPDATED_REPLAY_BACKTEST` rather than `STRATEGY_LADDER_READY` because the accepted v1 runner uses compatibility-mode fast discovery, not raw-history live-engine parity, and because measured audited historical artifacts remain absent.
