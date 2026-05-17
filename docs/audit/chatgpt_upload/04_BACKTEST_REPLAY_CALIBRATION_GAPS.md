# 04 BACKTEST REPLAY CALIBRATION GAPS

## Core gap
The Backtest owner page is materially undersupplied compared with the code already present.

Discovery evidence:
- `src/local_replay_runtime/*` -> 61 files, owner=`backtest`
- `src/calibration_methods/*` -> 21 files, owner=`backtest`
- `src/backtest_artifact_import/*` -> 16 files, owner=`backtest` or `observability`

Most of these files are `coded_not_displayed` or `runtime_only`.

## Formulas coded but not displayed

### Replay / parity / ablation
- `artifact_ablation_study.py`
  - `baseline_block_rate = _block_rate(aligned_baseline)`
  - `candidate_block_rate = _block_rate(aligned_candidate)`
  - `block_rate_delta = max(candidate_block_rate - baseline_block_rate, 0.0)`
- `shadow_execution_simulator.py`
  - `decision_match_rate`
  - `score_match_rate`
- `replay_metrics_collector.py`
  - `engine_aggregates`
  - `pair_aggregates`
  - real `exec_rate` source

### Calibration / statistical proof
- `calibration_methods/psr.py`
  - `compute_probabilistic_sharpe_ratio`
- `calibration_methods/dsr.py`
  - `compute_deflated_sharpe_ratio`
- `calibration_methods/hansen_spa.py`
- `calibration_methods/pot_gpd.py`
  - `index`
  - `ratio`
  - `xi_hat`
- `calibration_methods/stationarity.py`
  - ADF/KPSS critical values and stationarity checks
- `calibration_methods/walkforward.py`
- `calibration_methods/bootstrap.py`
  - `integrated_autocorrelation`
- `calibration_methods/execution.py`
  - robust weights
  - rate normalization

## Replay artifacts coded but not displayed
- `artifact_manifest.py`
- `artifact_proof_summary_builder.py`
- `artifact_release_candidate.py`
- `artifact_upload_bridge_candidate.py`
- `export_dir_bridge.py`
- `export_dir_bridge_support.py`
- `replay_executor.py`
  - review markdown body
  - run/replay coverage block
- replay runtime files read from bridge logic:
  - `feature_bridge.json`
  - `replay_metrics.json`
  - `replay_dtr.jsonl`
  - `replay_run_manifest.json`
  - `parity_diagnostics.json`

## Calibration proofs coded but not displayed
- PSR / DSR helpers exist but are not source-mapped onto the Backtest surface
- multiple-testing guard code exists but is currently entangled with IA Lab instead of a dedicated Backtest source map
- artifact lineage/import compatibility policy exists but is not clearly surfaced as Backtest proof

## Missing source-ledger behavior on the Backtest page
Current problem:
- the discovery audit has the source map
- the Backtest page itself does not

Required display gaps:
1. every displayed Backtest metric must show:
   - source file
   - runtime artifact or report
   - formula class
2. every absent metric must show:
   - `NOT_YET_PERSISTED`
   - `FORMULA_SOURCE_MISSING`
   - `CODED_NOT_DISPLAYED`

## Missing formula source labels
Current raw ledger still mixes:
- `REAL_QUANT_FORMULA`
- `PYDANTIC_FIELD`
- `STATUS_FLAG`
- `TEXT_OR_LIST`
- zero placeholders

Backtest cannot be considered audit-ready until its visible metrics are explicitly tagged by source class.

## P0 display target
The Backtest page should eventually show, at minimum:
- replay aggregates
- parity metrics
- artifact manifest / release candidate / proof summary refs
- calibration proof bank availability
- explicit formula source class for each displayed quant metric
