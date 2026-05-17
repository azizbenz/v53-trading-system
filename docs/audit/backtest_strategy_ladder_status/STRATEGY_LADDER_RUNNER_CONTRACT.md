# Strategy Ladder Runner Contract

Date: `2026-05-03`

## Canonical entrypoint

`scripts/run_backtest_strategy_ladder.py`

## Required CLI arguments

- `--run-id`
- `--input-root`
- `--feature-store-root`
- `--raw-root`
- `--output-root`
- `--pairs`
- `--engines`
- `--capital-buckets`
- `--timeframes`
- `--start`
- `--end`
- `--fast-only`
- `--detailed-only`
- `--resume`
- `--dry-run`

## Canonical output layout

`backtest_strategy_ladder/{run_id}/`

- `run_manifest.json`
- `fast_candidates/`
- `raw_windows/`
- `detailed_replay/`
- `capital_profiles/`
- `engine_promotion/`
- `pair_promotion/`
- `strategy_promotion/`
- `sample_size_survival/`
- `reports/`

## Required per-stage status fields

- `feature_store_status`
- `candidate_discovery_status`
- `candidate_export_status`
- `raw_window_extraction_status`
- `detailed_replay_status`
- `capital_profile_generation_status`
- `promotion_artifact_status`
- `sample_size_survival_status`

## Allowed ladder-level final statuses

- `STRATEGY_LADDER_READY`
- `STRATEGY_LADDER_READY_TO_RUN`
- `STRATEGY_LADDER_RAN_WITH_PARTIAL_EVIDENCE`
- `STRATEGY_LADDER_MEASURED_ARTIFACTS_PRODUCED`
- `STRATEGY_LADDER_BLOCKED_BY_FEATURE_STORE`
- `STRATEGY_LADDER_BLOCKED_BY_RAW_WINDOWS`
- `STRATEGY_LADDER_BLOCKED_BY_DEPTH_DATA`
- `STRATEGY_LADDER_BLOCKED_BY_BACKTEST_DATA`

## Required doctrine

- `--dry-run` must not emit fake measured candidates, replays, capital profiles, or promotion artifacts.
- `--fast-only` may stop after candidate export.
- `--detailed-only` requires an existing candidate export.
- Missing feature or raw inputs must fail with explicit stage statuses.
- Missing depth20 must not be rewritten as zero impact.
- `COMPAT_FEATURE_DISCOVERY` is accepted for v1, but it is explicitly not live-engine parity.
- `STRATEGY_LADDER_READY` remains a reserved audit-grade conclusion and must not be emitted from runtime evidence alone.
