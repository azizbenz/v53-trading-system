## 2026-04-22 - ML backtest input spec repo-truth

Status: `COMPLETE_REPO_TRUTH` for the bounded V5.3 ML enabler slice.

This note freezes what the Local-Lab ML layer is allowed to read from governed backtest/replay data before training an `MlModelArtifact`.

Canonical source seam:
- `local_replay_runtime.historical_data_gateway.HistoricalReplayOpportunity`

Projected categories consumed by ML:
1. Decision-time canonical features
- `feature_values` filtered to recognized canonical feature keys and numeric values only

2. Decision-time route context
- `raw_score`
- `penalized_score`
- `final_score`
- `expected_edge_bps`
- `spread_bps`
- `slippage_bps`
- `latency_penalty_bps`
- `fill_ratio`
- `ranking_position`
- `candidate_size`
- `final_size`

3. Supervision / replay outcome context
- `gross_return_bps`
- `target_decision_state`
- `production_decision_state`
- `production_final_score`
- `production_expected_cost`
- `primary_reason`
- `hard_block_reasons`

Current target projection policy:
- `net_return_bps_after_route_cost_bps.v1`
- formula:
  - `gross_return_bps - spread_bps - slippage_bps - latency_penalty_bps`

Stricter additive target now supported:
- `net_return_bps_after_replay_realized_cost.v1`
- source:
  - replay/backtest opportunity aligned with governed replay `DTRRecord`
- formula:
  - `(gross_return - realized_cost) * 10_000`
- usage:
  - Local-Lab only
- preferred when replay DTR alignment exists
- route-cost target remains the fallback when replay DTR evidence is absent

Local-Lab training driver now exists:
- `local_replay_runtime.build_local_lab_ml_artifact_training_report(...)`
- canonical flow:
  - governed replay dataset
  - optional governed replay DTR alignment
  - ML backtest contract projection
  - `MlTrainingRow` projection
  - `MlTrainerRequest`
  - `MlModelArtifact`

Important limits:
- this does not make ML sovereign
- this does not change engine side
- this does not change promotion gates
- this does not open VPS training
- this does not replace later shadow/live proof requirements
