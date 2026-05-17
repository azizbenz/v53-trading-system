# Backtest Strategy Ladder Status Summary

Date: `2026-05-03`

## Verdicts

- Backtest architecture verdict: `PARTIALLY_UPDATED_REPLAY_BACKTEST`
- Capital ladder verdict: `PIPELINE_EXISTS_BUT_NO_MEASURED_DATA`
- True economics integration verdict: `PARTIAL`
- Cost/fill/depth integration verdict: `PARTIAL`
- Candidate event / depth replay verdict: `READY`
- Engine/pair/strategy promotion compatibility: `READY`
- ML / VectorBT status: `RESEARCH_ONLY`

## What exists

- A canonical Strategy Ladder entrypoint now exists at `scripts/run_backtest_strategy_ladder.py`.
- The ladder runner now implements:
  `feature/gold-store input -> fast candidate discovery -> candidate export -> raw-window extraction -> detailed replay -> capital profile generation -> promotion/sample-size artifact feed -> final report`.
- A dedicated feature-store seam exists under `src/local_replay_runtime/strategy_ladder_feature_store.py` with JSONL/CSV support and optional Parquet support when the dependency is already present.
- Fast candidate discovery now exports governed candidate timestamps, pair identity, engine identity, strategy identity, and deterministic candidate IDs through `fast_candidates/candidate_events.jsonl`.
- Raw-window extraction now exports canonical per-candidate `window_manifest.json` files with explicit missing-book, missing-trades, missing-OHLCV, and limited-depth states.
- Candidate-window detailed replay now exports per-candidate replay artifacts and uses existing replay economics, fill, parity, and depth rails without inventing measured results.
- Measured capital-bucket profile generation is now wired into the runner for `400 / 500 / 1500 / 4000`.
- Existing `engine_promotion/*`, `pair_promotion/*`, `strategy_promotion/*`, and `sample_size_survival/*` rails are now fed from detailed replay output rather than remaining contract-only.
- Cockpit backtest surfaces now expose Strategy Ladder stage statuses and blockers.

## What is old

- `scripts/run_local_replay_export.py` remains the legacy governed replay/export runner and is still valid for its original dataset-driven workflow.
- The Strategy Ladder fast stage uses `COMPAT_FEATURE_DISCOVERY`, which is accepted for v1 but is explicitly not live-engine parity.
- The runner still does not recompute full A/B/C/D engine, scoring, risk, and portfolio decisions directly from raw market history.

## What is missing

- Governed populated historical feature/gold-store inputs are not checked in as audited Strategy Ladder datasets.
- Audited historical Strategy Ladder run outputs are not yet present for `400 / 500 / 1500 / 4000`.
- Guaranteed depth20 raw-book coverage is not proven across the intended replay universe.
- Telemetry-backed fill realism and replay/live cost parity remain partial and non-green by doctrine.
- Full live-engine recomputation from raw history remains a future parity upgrade, not part of the current accepted v1 compatibility mode.

## What must be patched before running Strategy Ladder

- No additional structural runner patch is required for a first governed Strategy Ladder execution.
- A real first run still requires governed feature-store rows plus raw trade/book/OHLCV roots.
- If strict live-engine parity from raw history is required, a later raw-history engine-recomputation patch is still needed.

## What can wait until after first backtest

- Optional analytics modules such as robustness, regret, and lifecycle overlays.
- Broader cockpit polish beyond the current stage/blocker projection.
- VPS/runtime integration refinements that depend on measured bucket artifacts rather than on runner existence alone.
- Shadow confirmation, which remains outside backtest scope by doctrine.

## Whether Patch 5 is required before Strategy Ladder

- The Strategy Ladder runner rail requested by Patch 5 is now implemented.
- The remaining blockers are governed data availability, audited historical runs, and later evidence promotion, not the absence of the runner itself.
