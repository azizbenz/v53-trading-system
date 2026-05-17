# 02 REAL QUANT FORMULAS ONLY

## Reclassification used for this package
The raw discovery ledger used `CODE_FORMULA_FOUND` too broadly. For this compact package, entries were reclassified into:
- `REAL_QUANT_FORMULA`
- `OPERATIONAL_DIAGNOSTIC`
- `THRESHOLD_CONSTANT`
- `PYDANTIC_FIELD`
- `STATUS_FLAG`
- `REPORT_VALUE`
- `TEXT_OR_LIST`
- `FALSE_POSITIVE`

Only `REAL_QUANT_FORMULA` and `OPERATIONAL_DIAGNOSTIC` appear below.

## REAL_QUANT_FORMULA

### Backtest / Replay
| Formula | Source file | Why it is real |
|---|---|---|
| `baseline_block_rate = _block_rate(aligned_baseline)` | `src/local_replay_runtime/artifact_ablation_study.py` | Actual baseline block-rate derivation. |
| `candidate_block_rate = _block_rate(aligned_candidate)` | `src/local_replay_runtime/artifact_ablation_study.py` | Actual candidate block-rate derivation. |
| `block_rate_delta = max(candidate_block_rate - baseline_block_rate, 0.0)` | `src/local_replay_runtime/artifact_ablation_study.py` | Explicit delta computation. |
| `decision_match_rate = round_float64(decision_matches / decision_compared, 6) if decision_compared else 0.0` | `src/local_replay_runtime/shadow_execution_simulator.py` | Real parity metric between replay and shadow behavior. |
| `score_match_rate = round_float64(score_matches / score_compared, 6) if score_compared else 0.0` | `src/local_replay_runtime/shadow_execution_simulator.py` | Real score-parity metric. |
| `engine_aggregates = tuple(... ce_net=sum(record.ce_expected) ... expected_cost_mean ... realized_cost_mean ... gross_return_mean ...)` | `src/local_replay_runtime/replay_metrics_collector.py` | Core engine-level replay aggregate derivation. |
| `pair_aggregates = tuple(... ce_net=sum(record.ce_expected) ... expected_cost_mean ... realized_cost_mean ... gross_return_mean ...)` | `src/local_replay_runtime/replay_metrics_collector.py` | Core pair-level replay aggregate derivation. |
| `blocked_threshold_count = sum(1 for threshold in thresholds if threshold.review_status == "blocked")` | `src/local_replay_runtime/local_lab_execution_review.py` | Real threshold review metric. |
| `partial_threshold_count = sum(1 for threshold in thresholds if threshold.review_status == "partial")` | `src/local_replay_runtime/local_lab_execution_review.py` | Real review metric. |
| `ready_threshold_count = sum(1 for threshold in thresholds if threshold.review_status == "ready")` | `src/local_replay_runtime/local_lab_execution_review.py` | Real review metric. |

### Calibration / Statistics
| Formula | Source file | Why it is real |
|---|---|---|
| `integrated_autocorrelation = 1.0 + sum(lag * autocorrelation for lag, autocorrelation in positive_autocorrelations)` | `src/calibration_methods/bootstrap.py` | Genuine stationary-bootstrap statistic. |
| `new_weights = tuple(1.0 if abs(residual) <= threshold else threshold / abs(residual) for residual in residuals)` | `src/calibration_methods/execution.py` | Real robust weighting logic. |
| `rate_series = tuple((call_count / duration_s) * 60.0 for call_count, duration_s in zip(...))` | `src/calibration_methods/execution.py` | Real rate normalization. |
| `index = int(math.floor((len(values) - 1) * probability))` | `src/calibration_methods/pot_gpd.py` | Tail-risk quantile index. |
| `ratio = (mean_excess * mean_excess) / variance` | `src/calibration_methods/pot_gpd.py` | GPD fitting intermediate. |
| `xi_hat = 0.5 * (1.0 - ratio)` | `src/calibration_methods/pot_gpd.py` | Tail-shape estimator. |

### Control / Operability math
| Formula | Source file | Why it is real |
|---|---|---|
| `operability_score = SystemOperabilityScore(...)` | `src/cockpit/state_system_flow.py` | Real multi-input operator verdict composition. |
| `stages = (Market Data Capture, Replay Metrics, Feature Bridge, Engines, Scoring, Queue, VPS Service, Cockpit Actions)` with stage status derivation | `src/cockpit/state_system_flow.py` | Real operational chain computation, not just a text badge. |
| `exec_rate = self.executed_count / self.total_records` | `src/cockpit/state_replay_metrics.py` | Real replay execution-rate formula, unlike `exec_rate = 0.0` placeholders elsewhere. |

## OPERATIONAL_DIAGNOSTIC
| Diagnostic | Source file | Why it stays in this file |
|---|---|---|
| `queue_trace` | `src/cockpit/state_queue_trace.py` | True operator diagnostic for queue visibility vs service consumption proof. |
| `service_liveness` | `src/cockpit/state_service_liveness.py` | True operator diagnostic for cockpit vs Shadow service liveness. |
| `warmup_explainer` | `src/cockpit/state_warmup_explainer.py` | Operational readiness diagnostic; not a quant formula, but critical proof surface. |
| `kill_proof` | `src/cockpit/state_kill_proof.py` | Operational control proof diagnostic. |

## Explicit exclusions from this file
These remain important, but they are **not** "real quant formulas":
- `Field(default=0.0, ...)` rows
- `ce_net = 0.0` placeholder rows
- `exec_rate = 0.0` placeholder rows
- boolean readiness flags like `feature_lineage_present = False`
- text/list builders like `lines = [...]`
- mappings like `_ENGINE_TO_STRATEGY = {...}`
