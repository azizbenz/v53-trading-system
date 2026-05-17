# 01 P0 ORPHAN RESOLUTION QUEUE

## Reclassification rule used here
- `P0_ORPHAN_RESOLUTION_REQUIRED`
  - fundamental production domain
  - dashboard ownership/import graph unresolved
  - cannot be dismissed as unused
- `P1_ORPHAN_RESOLUTION_REQUIRED`
  - relevant but not on the critical dashboard/control path
- `LIKELY_DEPRECATED`
  - older standalone surface or superseded launcher with no clear cockpit owner
- `TEST_HELPER`
  - tooling/support for test or smoke infrastructure, not a dashboard source owner
- `DOC_ONLY`
  - documentation or non-runtime helper
- `UNKNOWN_NEEDS_IMPORT_GRAPH`
  - real production code, but current discovery cannot assign an owner honestly

## P0 mandatory resolution set
These domains are promoted to P0 even when discovery labeled them `coded_not_displayed` or `insufficient_evidence`. The reason is not "unused code"; the reason is "dashboard ownership/import graph still unresolved".

| Scope | Discovery evidence | Package classification | Why P0 |
|---|---|---|---|
| `src/interface_contracts/*` | 33 files, all owner=`unknown`, mix of `orphan_candidate` and `insufficient_evidence` | `P0_ORPHAN_RESOLUTION_REQUIRED` | Typed contracts drive every dashboard truth boundary. Unknown ownership here means the dashboard can miss entire slices. |
| `src/execution_backbone/*` | 48 files, all owner=`unknown` | `P0_ORPHAN_RESOLUTION_REQUIRED` | Execution cost, breaker, fill, and runtime execution proof are core to Trading/VPS truth. |
| `src/venue_adapters/*` | 15 files, owner=`shadow`, mostly `coded_not_displayed` | `P0_ORPHAN_RESOLUTION_REQUIRED` | Venue auth/account/execution state is part of Shadow/VPS control proof and should be source-mapped. |
| `src/secrets_manager/*` | 8 files, owner=`shadow`, 1 `runtime_only` | `P0_ORPHAN_RESOLUTION_REQUIRED` | Credential status is a control surface input. Current cockpit can show status without showing the true contract edges. |
| `src/calibration_methods/*` | 21 files, all owner=`backtest`, all `coded_not_displayed` | `P0_ORPHAN_RESOLUTION_REQUIRED` | This is the real quant formula bank. Leaving it off-screen makes Backtest scientifically incomplete. |
| `src/local_replay_runtime/*` | 61 files, owner=`backtest`, `coded_not_displayed` + `runtime_only` | `P0_ORPHAN_RESOLUTION_REQUIRED` | Replay artifacts, proof summaries, parity, and calibration evidence live here. |
| `src/backtest_artifact_import/*` | 16 files, owner=`backtest` or `observability` | `P0_ORPHAN_RESOLUTION_REQUIRED` | Local->VPS artifact lineage/import proof is coded but underexposed. |
| `src/engines/*` | 64 files, owner=`trading`, almost all `coded_not_displayed` | `P0_ORPHAN_RESOLUTION_REQUIRED` | Trading page currently shows status, not source-mapped engine internals/formula ownership. |
| `src/data_backbone/microstructure/*` | 17 files, owner=`unknown`, all `insufficient_evidence` | `P0_ORPHAN_RESOLUTION_REQUIRED` | These are fundamental microstructure primitives; unknown ownership means feature provenance may still be incomplete. |
| `scripts/run_shadow_vps_service.py` | owner=`vps`, `coded_not_displayed` | `P0_ORPHAN_RESOLUTION_REQUIRED` | This is the long-running VPS control plane and should be first-class in the VPS/Shadow proof map. |

## P0 shadow/runtime extras
These are not in the mandatory list but are still P0 because they materially affect live pair/engine control and Shadow evidence.

| File | Current owner | Package classification | Why |
|---|---|---|---|
| `scripts/build_shadow_live_plan.py` | `shadow` | `P0_ORPHAN_RESOLUTION_REQUIRED` | Governs canonical live pair scope. |
| `scripts/local_replay_shadow_engines.py` | `shadow` | `P0_ORPHAN_RESOLUTION_REQUIRED` | Links replay findings back into Shadow engine evidence. |
| `scripts/run_local_replay_shadow.py` | `shadow` | `P0_ORPHAN_RESOLUTION_REQUIRED` | Explicit replay->Shadow bridge runner. |
| `scripts/shadow_gate_check_support.py` | `shadow` | `P0_ORPHAN_RESOLUTION_REQUIRED` | Shadow gate proof logic. |
| `scripts/shadow_vps_service_context_support.py` | `vps` | `P0_ORPHAN_RESOLUTION_REQUIRED` | Runtime context/loop proof. |
| `scripts/shadow_vps_service_execution_support.py` | `vps` | `P0_ORPHAN_RESOLUTION_REQUIRED` | Execution cycle proof. |
| `scripts/shadow_vps_service_runtime_support.py` | `vps` | `P0_ORPHAN_RESOLUTION_REQUIRED` | Runtime loop proof. |

## P1 resolution set
These matter, but not before the P0 contract/import graph is resolved.

| File / family | Package classification | Why |
|---|---|---|
| `src/complete_enablers/*` with owner `unknown` | `P1_ORPHAN_RESOLUTION_REQUIRED` | Build-14 addendum logic is important, but not as fundamental as Shadow/VPS/Backtest core proof. |
| `scripts/run_governance_snapshot_seed.py` | `P1_ORPHAN_RESOLUTION_REQUIRED` | Cockpit-adjacent, but seeded snapshots are not the first proof gap to close. |
| `scripts/run_local_grafana_dashboard.py` and `scripts/run_local_lab_grafana_dashboard.py` | `P1_ORPHAN_RESOLUTION_REQUIRED` | Observability surface helpers, secondary after owner/source cleanup. |
| `scripts/run_local_prometheus_*` | `P1_ORPHAN_RESOLUTION_REQUIRED` | Useful for observability packaging, not first for control truth. |

## Likely deprecated / not primary cockpit path
| File | Package classification | Why |
|---|---|---|
| `scripts/run_complete_dashboard.py` | `LIKELY_DEPRECATED` | Separate Build-17 dashboard path appears older than the unified cockpit shell. |
| `scripts/run_build9_core_smoke_support.py` | `TEST_HELPER` | Smoke support, not a primary dashboard source owner. |
| `scripts/run_engineering_guardrails.py` | `TEST_HELPER` | Guardrail tooling, not a dashboard truth source. |

## Unknown items that need import graph before any judgment
| File | Package classification | Why |
|---|---|---|
| `scripts/run_sharia_account_audit.py` | `UNKNOWN_NEEDS_IMPORT_GRAPH` | Could belong to IA Lab or a future compliance surface; current cockpit ownership not proven. |
| `scripts/run_sharia_pair_screening_audit.py` | `UNKNOWN_NEEDS_IMPORT_GRAPH` | Same issue: real code, unclear cockpit owner. |
| `src/complete_enablers/ml_runtime_artifact_loader.py` | `UNKNOWN_NEEDS_IMPORT_GRAPH` | Could feed IA Lab, Trading, or Shadow depending actual wiring. |

## Resolution method
For every P0 item above:
1. build import graph
2. build runtime artifact graph
3. assign exact cockpit owner page
4. decide `displayed` vs `coded_not_displayed` vs `runtime_only`
5. add source labels before adding UI
