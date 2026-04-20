# 18_REPO_ALIGNMENT_PROMOTION_OPS

## Included Source Docs
- docs/production_deployment_plan/update_audit/2026-04-17_repo_alignment_matrix_local_lab_vps_shadow.md
- docs/production_deployment_plan/update_audit/2026-04-17_shadow_vps_service_process_metrics_service_path.md
- docs/production_deployment_plan/update_audit/2026-04-17_promotion_calibration_register.md

---

## Source: docs/production_deployment_plan/update_audit/2026-04-17_repo_alignment_matrix_local_lab_vps_shadow.md

# REPO ALIGNMENT MATRIX - LOCAL LAB / VPS / SHADOW / ENGINES

## Objective

Freeze one rail-by-rail truth table before more implementation work. The goal of this slice is to reconcile the active April 15/16 planning docs with the current repo so future edits land on real seams, respect the `Local IA Lab -> signed artifact -> VPS` topology, and do not mistake stale planning language for missing code.

## Docs Governants

- `docs/production_deployment_plan/15_LOCAL_LAB_INGESTION_DIAGNOSTIC.md` `§2-§6`
- `docs/production_deployment_plan/16_VPS_LOCAL_OBSERVABILITY_ARCHITECTURE.md` `§2-§7`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md` `§0-§7`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md` `§1-§8`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `docs/production_deployment_plan/27_OPUS_TO_CODEX_AUDIT_DOCS21_22_PASS2.md` `governance and dispute framing`
- `docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md` `rank hierarchy`
- `docs/production_deployment_plan/29_SPRINT_FINAL_CODEX_BEFORE_MONDAY.md` `remaining sprint closure checklist`

## Current Code Seam

- Canonical repo truth today lives in the current code, not in old planning statements.
- The rails that matter for this alignment pass are:
  - `src/local_replay_runtime/`
  - `src/monitoring/`
  - `src/backtest_artifact_import/`
  - `src/protocols/`
  - `src/engines/engine_a/`
  - `src/engines/engine_c/`
  - `src/engines/engine_d/`
  - `src/data_backbone/microstructure/`
- Forbidden shortcut for this slice:
  - do not invent a new top-level Local Lab package
  - do not invent a second VPS runtime
  - do not treat doc 20 as permission to rewrite rich existing engines from zero

## Placement

- Target file: `docs/production_deployment_plan/update_audit/2026-04-17_repo_alignment_matrix_local_lab_vps_shadow.md`
- Doc target path: not prescribed by docs 15/16; required by audit protocol 25
- Actual landing decision: store the matrix as an audit pack so later slices can cite one stable truth table instead of re-deriving repo state from chat history

## Files Changed

- `docs/production_deployment_plan/update_audit/2026-04-17_repo_alignment_matrix_local_lab_vps_shadow.md`

## Claims Implemented

- Active April 15/16 canon is reconciled against current repo rails in one place -> `docs/production_deployment_plan/update_audit/2026-04-17_repo_alignment_matrix_local_lab_vps_shadow.md`
- Local Lab, VPS observability, artifact import, and Shadow rails are classified as `DONE_IN_CODE`, `PARTIAL_SEAM_EXISTS`, `DOC_STALE`, or `USER_ARBITRATION_REQUIRED` -> `docs/production_deployment_plan/update_audit/2026-04-17_repo_alignment_matrix_local_lab_vps_shadow.md`
- The plan now includes an explicit stop-and-ask rule when a richer cross-rail function/helper is needed instead of guessing from doc 20 alone -> `docs/production_deployment_plan/update_audit/2026-04-17_repo_alignment_matrix_local_lab_vps_shadow.md`

## Alignment Matrix

### 1. Global reading rule

- `Rang 2`: current code is the operational source of truth.
- `Rang 2`: docs 15/16/24 define topology and sequencing, not permission for greenfield replacement of already-rich rails.
- `Rang 4`: if a weaker rail appears to need a new function/helper to reach the richness of C/D, stop and ask the user instead of guessing placement or semantics.

### 2. Rail-by-rail truth table

| Rail | Governing docs | Real code seam | Current verdict | Why | Next safe move |
| --- | --- | --- | --- | --- | --- |
| Local IA Lab ingestion and replay analysis | docs 15, 24 | `src/local_replay_runtime/` | `DONE_IN_CODE` + `PARTIAL_SEAM_EXISTS` | The repo already has replay ingestion, post-trade review, calibration review, execution review, release candidate, promotion readiness, and scope-matrix rails. Docs 15/24 remain valid as topology and sequencing anchors, but not as proof that these rails are absent. | Audit completeness and consumers before adding any new Lab helper. |
| Signed artifact packaging and import | docs 15, 24 | `src/local_replay_runtime/artifact_release_candidate.py`, `src/backtest_artifact_import/` | `DONE_IN_CODE` + `PARTIAL_SEAM_EXISTS` | Controlled dry-run import, upload bridges, validators, proof summaries, release candidate state, and compatibility/signature policy already exist. | Check whether any remaining gap is wiring, not missing package surface. |
| VPS observability export | docs 16, 24 | `src/monitoring/`, `src/protocols/shadow_vps_service.py`, `scripts/shadow_vps_service_monitoring_support.py` | `DONE_IN_CODE` + `PARTIAL_SEAM_EXISTS` | Typed contracts, observability export, dashboard payloads, local Prometheus bridge, and process metrics sampler exist. Service-path proof now confirms bounded `.prom`, node_exporter textfile, and scrape manifest/file_sd writes. Remaining work is deployment/integration proof, not greenfield exporter code. | Treat remaining work as integration/deployment verification only. |
| Local monitoring / Grafana / Prometheus side | docs 16 | `src/monitoring/local_*` | `DONE_IN_CODE` + `PARTIAL_SEAM_EXISTS` | Local config generation, Grafana payloads, bundle loader/discovery, and Prometheus bridge already exist. Remaining work looks more like integration proof than greenfield code. | Verify end-to-end scrape handoff and bundle consistency, not package creation. |
| Shadow / Micro-live / Live gates | docs 16, 24, 28 | `src/protocols/` | `DONE_IN_CODE` + `VALID_GOVERNANCE` | Shadow runtime, micro-live, live-light, promotion gates, dashboards, service monitoring, and runtime bootstrap already exist. The hard rule is to avoid bypassing these gates, not to create new gate stacks. | Keep all future slices bounded to existing gate rails. |
| Engine A | docs 20, 24 | `src/engines/engine_a/` | `PARTIAL_SEAM_EXISTS` | Engine A is present and recently hardened on feasibility/conviction/input guards. It is still thinner than C/D in quant richness, but the next additions should be chosen explicitly, not guessed from doc 20. | Review runtime/support/reporting against C/D baseline and stop for user arbitration on real richness gaps. |
| Engine C | docs 21, 24, 29 | `src/engines/engine_c/` | `DONE_IN_CODE` + `PARTIAL_SEAM_EXISTS` | Engine C is rich, shadow-capable, and already carries doctrinal deepening plus microstructure continuation wiring. It should now be treated as a reference rail for weaker engines, not as an unfinished greenfield spec. | Only close explicit residual gaps; do not rebuild. |
| Engine D | docs 22, 24, 29 | `src/engines/engine_d/` | `DONE_IN_CODE` + `PARTIAL_SEAM_EXISTS` | Engine D is rich, anti-revenge aware, and already carries structured refusal, lineage, and runtime status rails. It is also a reference rail. | Only close explicit residual gaps; do not rebuild. |
| Canonical microstructure package | docs 23, 24, 29 | `src/data_backbone/microstructure/` | `DONE_IN_CODE` + `PARTIAL_SEAM_EXISTS` | The canonical package exists and already includes registry, realized kernel, OFI, VPIN, Kyle lambda, queue pressure, Amihud, Roll, Corwin-Schultz, Hawkes, PIN, and spread diagnostics. Remaining work is hardening and consumer wiring. | Continue bounded hardening on existing files only. |

### 3. Stale-doc conclusions that should no longer drive implementation

- Doc 15 does **not** justify creating a new `src/local_ai_lab/` package.
- Doc 15 does **not** justify any live bidirectional VPS -> Lab control plane.
- Doc 16 no longer proves that `ObservabilityExport`, `TechnicalDashboardPayload`, local Prometheus bridge, or process metrics surfaces are absent; they already exist in `src/monitoring/`.
- Doc 24 remains the strongest sequencing map, but its role is to place work on existing seams, not to authorize parallel greenfield stacks for C or D.
- Doc 20 must be read as a doctrinal delta over already-rich engines, not as a literal replacement spec for code that predates it.

### 4. Richness-gap review rule

Before changing Engine A, Engine B, Local Lab, VPS, or any shared rail, compare them against rich existing rails first:

- `engine_c`
- `engine_d`

If a missing function/helper looks genuinely necessary to bring a weaker rail to comparable production depth, stop and ask the user with:

1. the exact gap detected
2. why current code is below the C/D baseline
3. options for where the function should live
4. impact on contracts/tests/consumers
5. recommended option

Do **not** guess the placement from doc 20 alone.

### 4.1 Engine-specific semantic reservoirs are mandatory

- Engine A and Engine B must each keep their own rich local semantic reservoir.
- Do **not** flatten A/B into generic consumers of C/D semantics.
- Do **not** treat C/D as templates to copy mechanically into A/B.
- Only move logic into shared seams when it is truly transversal:
  - contracts
  - refusal logging
  - economics seams
  - canonical microstructure features
  - portfolio coordination
  - promotion/artifact governance

Verified engine intent from current docs and code:

- Engine A:
  - doc 20 positions A as the **initial detection** engine for trend expansion / first structural breakout
  - code seam lives in `src/engines/engine_a/structure_detector_a.py`, `context_validator_a.py`, `conviction_builder_a.py`, `invalidation_mapper_a.py`
  - A therefore needs its own richer semantics around first-entry structural trend logic, not a copy of C continuation logic
- Engine B:
  - doc 13 and doc 20 position B as a **mean-reversion** engine with stricter CE/cost posture
  - code seam lives in `src/engines/engine_b/local_mean_estimator_b.py`, `excess_detector_b.py`, `anti_breakout_filter_b.py`, `conviction_builder_b.py`, `invalidation_mapper_b.py`
  - doc 20 / doc 23 also state VPIN-fade is a **B sub-signal**, not a new engine
  - B therefore needs its own richer semantics around local mean, excess, anti-breakout, and flow-aware fade logic, not a copy of D re-entry or C breakout-continuation logic

Practical rule for future A/B slices:

- compare A/B to C/D for engineering quality and audit depth
- do **not** assume the same trading semantics
- if the next missing A/B richness is not already obvious from code/docs, stop and ask the user instead of inventing it

### 5. Immediate code candidates after this matrix

The smallest plausible next slices are:

1. review Engine A for missing **A-specific** richness around first-entry structural trend logic, then stop for user arbitration if the next gap is semantic rather than mechanical
2. review Engine B for missing **B-specific** richness around mean-reversion / fade semantics, then stop for user arbitration if the next gap is semantic rather than mechanical
3. or continue bounded hardening on existing microstructure files where window/hash/quality flags remain weaker than the new standard

## Tests and Proof

- `Get-Content docs/production_deployment_plan/15_LOCAL_LAB_INGESTION_DIAGNOSTIC.md -TotalCount 220` -> reviewed
- `Get-Content docs/production_deployment_plan/16_VPS_LOCAL_OBSERVABILITY_ARCHITECTURE.md -TotalCount 260` -> reviewed
- `Get-Content docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md -TotalCount 260` -> reviewed
- `Get-Content docs/production_deployment_plan/29_SPRINT_FINAL_CODEX_BEFORE_MONDAY.md -TotalCount 260` -> reviewed
- `rtk grep -n "signed artifact|artifact import|dry_run|release_candidate|governed_input_summary|artifact_proof" src/local_replay_runtime src/backtest_artifact_import` -> confirms real artifact/release/import rails exist
- `rtk grep -n "runtime_mode|ObservabilityExport|TechnicalDashboardPayload|process_metrics|prometheus|\\.prom|cpu_pct|ram_pct" src/monitoring src/protocols` -> confirms real VPS/local observability rails exist
- `Get-ChildItem src/local_replay_runtime | Select-Object Name` -> confirms Local Lab code seam breadth
- `Get-ChildItem src/monitoring | Select-Object Name` -> confirms monitoring seam breadth
- `Get-ChildItem src/backtest_artifact_import | Select-Object Name` -> confirms controlled import seam breadth
- `Get-ChildItem src/protocols | Select-Object Name` -> confirms Shadow/Micro-live/Live/promotion rails exist
- `Get-ChildItem src/engines/engine_a | Select-Object Name` -> reviewed current A seam
- `Get-ChildItem src/engines/engine_c | Select-Object Name` -> reviewed current C seam
- `Get-ChildItem src/engines/engine_d | Select-Object Name` -> reviewed current D seam

## Deferred / Not Done

- No runtime code was changed in this slice.
- Real VPS service-path verification for process metrics and `.prom` export is not closed yet.
- No new richness helper/function has been added to weaker rails yet; that must follow the stop-and-ask rule if it becomes semantic rather than mechanical.

## Risks / Open Questions

- The biggest current risk is confusing old planning language with true missing code and accidentally building duplicate rails.
- The next unresolved question is whether the highest-value next slice is VPS process-metrics wiring or Engine A richness alignment against C/D.
- If Engine A needs genuinely new semantics rather than just guards/wiring, user arbitration is required before placement.

## Completion Status

`COMPLETE`

Reason:

The matrix exists, cites the governing docs, points to real seams, and records which areas are truly missing versus already present or stale in planning docs.

## Next Safe Step

`Verify the real VPS process-metrics and .prom export path end-to-end on existing files before deciding whether the next code slice is observability wiring or Engine A richness alignment.`


---

## Source: docs/production_deployment_plan/update_audit/2026-04-17_shadow_vps_service_process_metrics_service_path.md

# SHADOW VPS SERVICE PROCESS METRICS SERVICE PATH

## Objective

Prove whether the real Shadow VPS service path already wires bounded process metrics sampling and Prometheus-style export, or whether doc 16 still points to a real missing gap. This slice is proof-oriented: add end-to-end behavioral coverage on the existing service support path instead of inventing new monitoring architecture.

## Docs Governants

- `docs/production_deployment_plan/16_VPS_LOCAL_OBSERVABILITY_ARCHITECTURE.md` `§3-§7`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md` `Phase G posture: current code wins`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md` `§1-§8`
- `docs/production_deployment_plan/update_audit/2026-04-17_repo_alignment_matrix_local_lab_vps_shadow.md`

## Current Code Seam

- Canonical file today: `scripts/shadow_vps_service_monitoring_support.py`
- Why this seam is the right place: it is the real service-path helper that samples process metrics, builds the monitoring payload, writes the bounded `.prom` export, writes the node_exporter textfile payload, and emits the scrape manifest/file_sd artifacts.
- Forbidden shortcut for this slice: do not create a second monitoring writer or a parallel VPS exporter stack under `src/`.

## Placement

- Target file: `tests/test_monitoring/test_shadow_vps_service_monitoring_support.py`
- Doc target path: docs 16 only names likely code targets, not a mandatory test path
- Actual landing decision: add a behavioral test at the monitoring test seam while keeping the runtime code unchanged because the service path already exists

## Files Changed

- `tests/test_monitoring/test_shadow_vps_service_monitoring_support.py`
- `docs/production_deployment_plan/update_audit/2026-04-17_shadow_vps_service_process_metrics_service_path.md`

## Claims Implemented

- The real Shadow VPS service support path already samples process metrics and writes bounded monitoring artifacts -> `scripts/shadow_vps_service_monitoring_support.py`
- End-to-end proof now exists that one service-path call writes:
  - backend payload JSON
  - observability export JSON
  - `.prom` text payload
  - optional node_exporter textfile payload
  - optional scrape manifest
  - optional Prometheus file_sd JSON
  -> `tests/test_monitoring/test_shadow_vps_service_monitoring_support.py`
- The optional outputs are now explicitly guarded by test coverage when node_exporter/scrape inputs are absent -> `tests/test_monitoring/test_shadow_vps_service_monitoring_support.py`

## Tests and Proof

- `$env:PYTHONPYCACHEPREFIX='.test_tmp/pycache'; python -m py_compile tests/test_monitoring/test_shadow_vps_service_monitoring_support.py` -> pass
- `$env:TEMP='.test_tmp'; $env:TMP='.test_tmp'; $env:PYTHONPYCACHEPREFIX='.test_tmp/pycache'; python -m pytest tests/test_monitoring/test_shadow_vps_service_monitoring_support.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_monitoring/test_process_metrics.py -q` -> `5 passed, 1 warning`
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`

## Deferred / Not Done

- No runtime code change was needed in this slice.
- This slice does not prove production deployment of node_exporter itself; it proves the service writes the bounded artifacts for that rail.
- This slice does not audit Grafana or local Prometheus ingestion end-to-end.

## Risks / Open Questions

- Doc 16 is partially stale on code existence, but that does not automatically prove all production deployment wiring is exercised outside tests.
- If a future gap appears here, it should be a service-path wiring gap, not an excuse to add a second exporter architecture.

## Completion Status

`COMPLETE`

Reason:

The real service-path proof is now executed and clean. The sampler, bounded `.prom` export, node_exporter textfile write, and scrape manifest/file_sd write are all covered without adding a second monitoring architecture.

## Next Safe Step

`Move to the next bounded observability gap only if it is a real deployment/integration gap, not a stale-doc code-existence claim.`


---

## Source: docs/production_deployment_plan/update_audit/2026-04-17_promotion_calibration_register.md

# 2026-04-17 Promotion Calibration Register

## Docs Governants

- `docs/production_deployment_plan/12_LOCAL_LAB_VS_VPS_SEPARATION.md`
- `docs/production_deployment_plan/13_CALIBRATION_METHODS.md`
- `docs/production_deployment_plan/14_SHADOW_GATE_MATH.md`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `docs/production_deployment_plan/update_audit/2026-04-17_engine_a_prompt_correction_hardening.md`
- `docs/production_deployment_plan/update_audit/2026-04-17_engine_b_reaudit_residual_fixes.md`
- `docs/production_deployment_plan/update_audit/2026-04-16_engine_c_continuation_microstructure_wiring.md`
- `docs/production_deployment_plan/update_audit/2026-04-16_docs21_22_opus_audit.md`
- `docs/production_deployment_plan/update_audit/2026-04-17_repo_alignment_matrix_local_lab_vps_shadow.md`

## Current Code Seam

- Promotion blockers were already present, but spread across:
  - engine audit packs
  - docs `12`, `13`, `14`
  - repo alignment notes
- No durable doc in `production_deployment_plan/` said in one place:
  - what still needs calibration before Shadow sign-off
  - what still needs proof before `G2.3 -> MICRO_LIVE`
  - what remains required before Live scaling

## Files Changed

- `docs/production_deployment_plan/30_PROMOTION_CALIBRATION_REGISTER.md`
- `docs/production_deployment_plan/00_README.md`
- `docs/production_deployment_plan/update_audit/2026-04-17_promotion_calibration_register.md`

## Claims Implemented

- Added a durable promotion-calibration register at `30_PROMOTION_CALIBRATION_REGISTER.md`.
- The register distinguishes:
  - `READY_FOR_SHADOW`
  - `NEEDS_MORE_CALIBRATION`
  - `RESEARCH_ONLY`
  - `DO_NOT_PROMOTE`
- The register is stage-specific:
  - before Shadow sign-off
  - before Micro-live
  - before Live scaling
- The register explicitly separates:
  - statistical calibration
  - deterministic governance proof
  - signed-artifact requirements
- Engine A, B, C, D, canonical microstructure, and shared promotion rails are all covered in one place.
- `00_README.md` now points to the new register and acknowledges the current extended doc set.

## Tests and Proof

- `rtk grep -n "Shadow/Micro-live|Micro-live|promotion|calibration|READY_FOR_SHADOW|NEEDS_MORE_CALIBRATION|DO_NOT_PROMOTE|RESEARCH_ONLY|before promotion" docs/production_deployment_plan docs/production_deployment_plan/update_audit`
- `rtk read docs/production_deployment_plan/12_LOCAL_LAB_VS_VPS_SEPARATION.md`
- `rtk read docs/production_deployment_plan/13_CALIBRATION_METHODS.md`
- `rtk read docs/production_deployment_plan/14_SHADOW_GATE_MATH.md`
- `rtk read docs/production_deployment_plan/update_audit/2026-04-17_engine_a_prompt_correction_hardening.md`
- `rtk read docs/production_deployment_plan/update_audit/2026-04-17_engine_b_reaudit_residual_fixes.md`
- `rtk read docs/production_deployment_plan/update_audit/2026-04-16_engine_c_continuation_microstructure_wiring.md`
- `rtk read docs/production_deployment_plan/update_audit/2026-04-16_docs21_22_opus_audit.md`
- `python scripts/run_engineering_guardrails.py`

Proof target:

- new register exists in the durable plan folder, not only in `update_audit/`
- the register covers A/B/C/D plus shared rails
- the register names stage-specific blockers instead of vague "to calibrate later"
- guardrails remain clean

## Completion Status

`COMPLETE`

## Next Safe Step

Use `30_PROMOTION_CALIBRATION_REGISTER.md` as the durable checkpoint every time an engine slice changes:

- verdict
- Shadow blockers
- Micro-live blockers
- Live-scaling blockers


