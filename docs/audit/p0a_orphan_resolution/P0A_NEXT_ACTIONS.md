# P0-A Next Actions
P0-A resolved owner classification and import/runtime graph for the mandatory domains. No business logic was changed.
## Immediate implications for P0-B / P0-C / P0-D
1. `Backtest` is now the canonical display owner for `src/calibration_methods/*`, the replay-producing half of `src/local_replay_runtime/*`, and the governed export/import discovery path in `src/backtest_artifact_import/*`.
2. `IA Lab` is the owner for ML/regime training and upload-bridge files under `src/calibration_methods/*`, `src/local_replay_runtime/*`, and `src/backtest_artifact_import/*`.
3. `Trading` is the owner for `src/engines/*`, `src/data_backbone/microstructure/*`, and the execution-backbone files that explain route/cost/gate decisions.
4. `VPS` is the owner for `scripts/run_shadow_vps_service.py` and the execution-backbone files that explain runtime fills, reconciliation, breaker state, heartbeat, and queue control.
5. `src/interface_contracts/*`, `src/secrets_manager/*`, and parts of `src/venue_adapters/*` stay non-cockpit core/runtime producers. They should appear only through source-labeled projections, never as duplicated raw tables.
## Recommended execution order after P0-A
| Order | Slice | Why this is unblocked now |
|---|---|---|
| 1 | `P0-B` Formula ledger cleanup | The real quant formula bank now has clear owner destinations: Backtest, Trading, IA Lab, VPS diagnostics. |
| 2 | `P0-C` Backtest source-mapped display | Replay/calibration/import/export ownership is now explicit and can be surfaced without guessing. |
| 3 | `P0-D` VPS/Shadow control proof ownership | Service/queue/heartbeat ownership can now be pinned to `scripts/run_shadow_vps_service.py` and the VPS-side execution/runtime graph. |
## Guardrails for the next patch
- do not move non-cockpit core contracts onto cockpit pages as raw dumps
- do not classify runtime-only producers as deprecated without downstream import/runtime evidence
- keep `Trading` focused on decision/economics/engine explanation, `VPS` on service control proof, `Shadow` on readiness/verdict, `Backtest` on replay/calibration provenance, and `IA Lab` on artifact/research provenance
