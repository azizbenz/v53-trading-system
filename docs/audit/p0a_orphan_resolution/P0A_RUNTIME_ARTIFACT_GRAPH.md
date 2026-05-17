# P0-A Runtime Artifact Graph
Scope: mandatory P0 domains only. This graph lists producer/consumer evidence for runtime artifacts without changing any runtime logic.
## Artifact Family Summary
| Artifact | Producers | Consumers | Producer Domains | Consumer Domains |
|---|---|---|---|---|
| `.sealed.json` | none | credential_loader.py | none | venue_adapters (1) |
| `auto_exports/*/feature_bridge.json` | none | run_shadow_vps_service.py | none | scripts (1) |
| `auto_exports/*/parity_diagnostics.json` | none | run_shadow_vps_service.py | none | scripts (1) |
| `auto_exports/*/replay_metrics.json` | none | run_shadow_vps_service.py | none | scripts (1) |
| `auto_exports/*/replay_run_manifest.json` | none | run_shadow_vps_service.py | none | scripts (1) |
| `config/calibration/v1/edge_gate.yml` | none | edge_gate_calibration.py | none | local_replay_runtime (1) |
| `dashboard_command_queue/*` | none | run_shadow_vps_service.py | none | scripts (1) |
| `engine_d_state_snapshot_manifest.json` | engine_state_snapshot_d.py | engine_state_snapshot_d.py | engines (1) | engines (1) |
| `engine_d_state_snapshots.jsonl` | engine_state_snapshot_d.py | engine_state_snapshot_d.py | engines (1) | engines (1) |
| `feature_bridge.json` | artifact_exporter.py | artifact_exporter.py, export_dir_bridge.py, replay_orchestrator_resume.py | local_replay_runtime (1) | local_replay_runtime (2), backtest_artifact_import (1) |
| `kill_switch_state.json` | emergency_circuit_breaker.py | emergency_circuit_breaker.py | execution_backbone (1) | execution_backbone (1) |
| `live_websocket_config.json` | none | run_shadow_vps_service.py | none | scripts (1) |
| `local_lab_replay_candidate_queue.json` | none | local_lab_replay_workflow_loader.py | none | local_replay_runtime (1) |
| `local_lab_replay_dispatch_plan.json` | none | local_lab_replay_workflow_loader.py | none | local_replay_runtime (1) |
| `local_lab_replay_ticket_index.json` | none | local_lab_replay_workflow_loader.py | none | local_replay_runtime (1) |
| `local_lab_replay_workflow_manifest.json` | none | local_lab_replay_workflow_loader.py | none | local_replay_runtime (1) |
| `local_replay_runtime_evidence.json` | none | runtime_evidence.py | none | local_replay_runtime (1) |
| `ml_model_artifact.json` | none | ml_model_transport.py | none | backtest_artifact_import (1) |
| `ml_model_artifact.summary.json` | none | ml_model_transport.py | none | backtest_artifact_import (1) |
| `parity_diagnostics.json` | artifact_exporter.py | artifact_exporter.py, export_dir_bridge.py, replay_orchestrator_resume.py | local_replay_runtime (1) | local_replay_runtime (2), backtest_artifact_import (1) |
| `performance_mode_guard.json` | none | replay_orchestrator_execution.py, replay_orchestrator_resume.py | none | local_replay_runtime (2) |
| `regime_detector_artifact.json` | none | regime_detector_transport.py | none | backtest_artifact_import (1) |
| `regime_detector_artifact.summary.json` | none | regime_detector_transport.py | none | backtest_artifact_import (1) |
| `replay_chunk_session.json` | none | replay_orchestrator_execution.py, replay_orchestrator_io.py, replay_orchestrator_resume.py | none | local_replay_runtime (3) |
| `replay_dtr.json` | none | export_dir_bridge.py | none | backtest_artifact_import (1) |
| `replay_dtr.jsonl` | artifact_exporter.py | artifact_exporter.py, export_dir_bridge.py, replay_orchestrator_resume.py | local_replay_runtime (1) | local_replay_runtime (2), backtest_artifact_import (1) |
| `replay_metrics.json` | artifact_exporter.py | artifact_exporter.py, export_dir_bridge.py, replay_orchestrator_resume.py | local_replay_runtime (1) | local_replay_runtime (2), backtest_artifact_import (1) |
| `replay_run_manifest.json` | artifact_exporter.py, replay_orchestrator_io.py | artifact_exporter.py, export_dir_bridge.py, local_lab_execution_telemetry_artifact.py, replay_orchestrator_io.py, replay_orchestrator_resume.py | local_replay_runtime (2) | local_replay_runtime (4), backtest_artifact_import (1) |
| `replay_session_config.json` | none | replay_orchestrator_execution.py, replay_orchestrator_io.py, replay_orchestrator_resume.py | none | local_replay_runtime (3) |
| `replay_session_state.json` | none | replay_orchestrator_execution.py, replay_orchestrator_resume.py, replay_state_store.py | none | local_replay_runtime (3) |
| `review_export.md` | artifact_exporter.py | export_dir_bridge.py | local_replay_runtime (1) | backtest_artifact_import (1) |
| `run_consistency_guard.json` | none | replay_orchestrator_execution.py, replay_orchestrator_resume.py | none | local_replay_runtime (2) |
| `service/runtime_evidence_bundle.json` | none | run_shadow_vps_service.py | none | scripts (1) |
| `shadow_vps_service.campaign_summary.json` | run_shadow_vps_service.py | none | scripts (1) | none |
| `shadow_vps_service.events.jsonl` | run_shadow_vps_service.py | none | scripts (1) | none |
| `shadow_vps_service.pid` | run_shadow_vps_service.py | none | scripts (1) | none |
| `shadow_vps_service.state.json` | run_shadow_vps_service.py | none | scripts (1) | none |
| `shadow_vps_service_execution_telemetry.archive.json` | run_shadow_vps_service.py | none | scripts (1) | none |
| `shadow_vps_service_execution_telemetry.json` | run_shadow_vps_service.py | none | scripts (1) | none |
| `shadow_vps_service_monitoring_backend_payload.json` | run_shadow_vps_service.py | none | scripts (1) | none |
| `shadow_vps_service_observability_export.json` | run_shadow_vps_service.py | none | scripts (1) | none |
| `shadow_vps_service_prometheus_file_sd.json` | run_shadow_vps_service.py | none | scripts (1) | none |
| `shadow_vps_service_recent_events.json` | run_shadow_vps_service.py | none | scripts (1) | none |
| `shadow_vps_service_scrape_manifest.json` | run_shadow_vps_service.py | none | scripts (1) | none |
| `{source}.sealed.json` | sealer.py | loader.py, sealer.py | secrets_manager (1) | secrets_manager (2) |

## scripts producer/consumer rows
| File | Reads | Writes | Evidence Note |
|---|---|---|---|
| `scripts/run_shadow_vps_service.py` | auto_exports/*/feature_bridge.json, auto_exports/*/parity_diagnostics.json, auto_exports/*/replay_metrics.json, auto_exports/*/replay_run_manifest.json, dashboard_command_queue/*, live_websocket_config.json, service/runtime_evidence_bundle.json | shadow_vps_service.campaign_summary.json, shadow_vps_service.events.jsonl, shadow_vps_service.pid, shadow_vps_service.state.json, shadow_vps_service_execution_telemetry.archive.json, shadow_vps_service_execution_telemetry.json, shadow_vps_service_monitoring_backend_payload.json, shadow_vps_service_observability_export.json, shadow_vps_service_prometheus_file_sd.json, shadow_vps_service_recent_events.json, shadow_vps_service_scrape_manifest.json | Run the autonomous long-running VPS Shadow service. |

## backtest_artifact_import producer/consumer rows
| File | Reads | Writes | Evidence Note |
|---|---|---|---|
| `src/backtest_artifact_import/export_dir_bridge.py` | feature_bridge.json, parity_diagnostics.json, replay_dtr.json, replay_dtr.jsonl, replay_metrics.json, replay_run_manifest.json, review_export.md | none | Typed bridge from governed LOCAL_REPLAY export directories to import/upload contracts. |
| `src/backtest_artifact_import/ml_model_transport.py` | ml_model_artifact.json, ml_model_artifact.summary.json | none | Governed supplementary transport helpers for bounded ML model artifacts. |
| `src/backtest_artifact_import/regime_detector_transport.py` | regime_detector_artifact.json, regime_detector_artifact.summary.json | none | Governed supplementary transport helpers for RegimeDetectorML artifacts. |

## calibration_methods producer/consumer rows
No direct runtime artifact reads/writes were detected in this mandatory domain.

## data_backbone/microstructure producer/consumer rows
No direct runtime artifact reads/writes were detected in this mandatory domain.

## engines producer/consumer rows
| File | Reads | Writes | Evidence Note |
|---|---|---|---|
| `src/engines/engine_d/engine_state_snapshot_d.py` | engine_d_state_snapshot_manifest.json, engine_d_state_snapshots.jsonl | engine_d_state_snapshot_manifest.json, engine_d_state_snapshots.jsonl | Append-only persistence for Engine D consecutive-stop state snapshots. |

## execution_backbone producer/consumer rows
| File | Reads | Writes | Evidence Note |
|---|---|---|---|
| `src/execution_backbone/emergency_circuit_breaker.py` | kill_switch_state.json | kill_switch_state.json | GEM-10 / QWEN-07 — Emergency Circuit Breaker with disk persistence. |

## interface_contracts producer/consumer rows
No direct runtime artifact reads/writes were detected in this mandatory domain.

## local_replay_runtime producer/consumer rows
| File | Reads | Writes | Evidence Note |
|---|---|---|---|
| `src/local_replay_runtime/artifact_exporter.py` | feature_bridge.json, parity_diagnostics.json, replay_dtr.jsonl, replay_metrics.json, replay_run_manifest.json | feature_bridge.json, parity_diagnostics.json, replay_dtr.jsonl, replay_metrics.json, replay_run_manifest.json, review_export.md | Artifact exporter for governed LOCAL_REPLAY runs. |
| `src/local_replay_runtime/edge_gate_calibration.py` | config/calibration/v1/edge_gate.yml | none | Local IA Lab EDGE calibration from governed replay DTR evidence. |
| `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py` | replay_run_manifest.json | none | Service-owned execution telemetry archive for Local IA Lab THR-X01 to THR-X05. |
| `src/local_replay_runtime/local_lab_replay_workflow_loader.py` | local_lab_replay_candidate_queue.json, local_lab_replay_dispatch_plan.json, local_lab_replay_ticket_index.json, local_lab_replay_workflow_manifest.json | none | File-based loader for Local IA Lab replay workflow sidecars. |
| `src/local_replay_runtime/replay_dtr_exporter.py` | Replay DTR exports must use .json or .jsonl | none | Export helpers for governed LOCAL_REPLAY DTR artifacts. |
| `src/local_replay_runtime/replay_orchestrator_execution.py` | performance_mode_guard.json, replay_chunk_session.json, replay_session_config.json, replay_session_state.json, run_consistency_guard.json | none | Execution pipeline for governed LOCAL_REPLAY orchestration. |
| `src/local_replay_runtime/replay_orchestrator_io.py` | replay_chunk_session.json, replay_run_manifest.json, replay_session_config.json | replay_run_manifest.json | Sidecar IO helpers for governed LOCAL_REPLAY exports. |
| `src/local_replay_runtime/replay_orchestrator_resume.py` | feature_bridge.json, parity_diagnostics.json, performance_mode_guard.json, replay_chunk_session.json, replay_dtr.jsonl, replay_metrics.json, replay_run_manifest.json, replay_session_config.json, replay_session_state.json, run_consistency_guard.json | none | Resume helpers for governed LOCAL_REPLAY orchestration. |
| `src/local_replay_runtime/replay_state_store.py` | replay_session_state.json | none | State persistence for governed LOCAL_REPLAY sessions. |
| `src/local_replay_runtime/runtime_evidence.py` | local_replay_runtime_evidence.json | none | Stateful runtime evidence recorder for governed LOCAL_REPLAY sessions. |

## secrets_manager producer/consumer rows
| File | Reads | Writes | Evidence Note |
|---|---|---|---|
| `src/secrets_manager/loader.py` | {source}.sealed.json | none | Load sealed secret envelopes without leaking plaintext outside memory. |
| `src/secrets_manager/sealer.py` | {source}.sealed.json | {source}.sealed.json | Seal plaintext secrets into a typed encrypted envelope. |

## venue_adapters producer/consumer rows
| File | Reads | Writes | Evidence Note |
|---|---|---|---|
| `src/venue_adapters/binance_spot/credential_loader.py` | .sealed.json | none | Credential loaders for Binance Spot with runtime-safe policy seams. |
