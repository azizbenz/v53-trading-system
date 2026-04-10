# Local IA Lab Ingestion Diagnostic

> Status: diagnostic addendum to the production plan, based on the real repo as of 2026-04-10.
>
> Rule of truth: current code wins over planning docs.

---

## 1. Objective

Establish what the Local IA Lab already ingests from V5.3 today, what form that ingestion takes, and what is still missing before the loop becomes:

`post-trade diagnostic -> local recalibration -> signed artifact -> VPS import`

This file is diagnostic and planning-oriented. It does not authorize a new architecture.

---

## 2. Short answer

Yes, the Local IA Lab already ingests V5.3 evidence, but not as a raw live bidirectional VPS stream.

What exists today is a governed ingestion of:
- historical market snapshots for replay/backtest
- post-trade structured traces (`DTRRecord`)
- strategy/review bundles (`TradeLearningInput`, `LearningReviewExport`, `ReplayExportBundle`)
- governed replay sidecars (`review_export`, `parity_diagnostics`, `replay_metrics`, `replay_dtr`)

What does not exist today is:
- a live always-on VPS -> Lab raw snapshot feed
- an automatic recalibration loop running on the VPS
- a separate top-level `src/local_ai_lab` package

---

## 3. Code-confirmed ingestion surfaces

### 3.1 Historical snapshot ingestion

Confirmed in:
- `src/local_replay_runtime/historical_snapshot_loader.py`
- `src/local_replay_runtime/replay_event_router.py`

What this means:
- the Lab can already load raw historical market events from `.json`, `.jsonl`, and `.csv`
- those events are typed into `HistoricalSnapshotBatch`
- those batches are routed into normalized replay datasets for backtest/replay

This is the current historical market data ingress for the Lab.

### 3.2 Post-trade trade-level ingestion

Confirmed in:
- `src/interface_contracts/meta_contracts.py`
- `src/meta_learning/post_trade_diagnostic_engine.py`
- `src/meta_minimal/meta_runtime.py`
- `scripts/run_local_lab_post_trade_review.py`

What this means:
- the Lab already has a governed trade-level trace object: `DTRRecord`
- post-trade diagnostics are built from structured evidence, not from ad hoc logs
- the current diagnostic engine combines:
  - `TradeLearningInput`
  - `DTRSummary`
  - `CRAReport`
  - `BreakEvenReport`
  - `EdgeReport`
- the Lab now also has a bounded launcher that can ingest governed `replay_dtr.json/.jsonl`
  and rebuild:
  - `meta_runtime_result.json`
  - `meta_learning_review.bundle.json`
  - `meta_learning_review.md`
  - `meta_learning_projection.json`

This is already a real post-trade analysis path.

### 3.3 Strategy / review bundle ingestion

Confirmed in:
- `src/meta_learning/contracts.py`
- `src/meta_learning/review_orchestrator.py`
- `src/meta_learning/replay_bundle_builder.py`
- `src/meta_learning/facade.py`

What this means:
- the Lab already ingests a governed `TradeLearningInput`
- it already produces and manipulates `LearningReviewExport`
- it already produces `MetaLearningReviewBundle`
- it already prepares replay handoff bundles for candidate changes

So the Lab already has a strategy-level / review-level ingestion and analysis path.

### 3.4 Governed replay artifact ingestion

Confirmed in:
- `src/local_replay_runtime/replay_executor.py`
- `src/backtest_artifact_import/export_dir_bridge.py`

What this means:
- V5.3 already exports governed replay evidence:
  - `review_export.md`
  - `parity_diagnostics.json`
  - `replay_metrics.json`
  - `replay_dtr.jsonl`
- the bridge already reloads and validates those sidecars with typed contracts

So the Lab/VPS rail is already evidence-aware, not just file-copy based.

---

## 4. Correct interpretation

The current code supports this:

1. historical snapshots enter the Lab
2. replay/backtest produces structured evidence
3. meta-learning / post-trade diagnostics analyze that evidence
4. local calibration jobs can produce signed artifacts
5. VPS imports those artifacts and consumes them on the governed runtime rail

The current code does not support this:

1. VPS streams all live runtime snapshots back to the Lab continuously
2. the Lab auto-recalibrates the VPS in real time
3. a hidden control plane silently mutates runtime thresholds

So the current loop is governed and mostly one-way:

`historical/replay evidence -> Local IA Lab -> signed artifact -> VPS`

not:

`VPS live runtime -> raw continuous feedback -> automatic Lab control loop`

---

## 5. Implications for the plan

### 5.1 What should be strengthened next

The next Lab-centered slices should reinforce:
- post-trade diagnostic completeness
- replay/review bundle completeness
- local calibration producers
- signed artifact production
- governed artifact import on the VPS side

### 5.2 What should not be invented

The plan must not drift into:
- a fake live Lab/VPS message bus
- a second runtime hidden inside the Lab
- automatic VPS-side recalibration
- a new top-level `src/local_ai_lab`

---

## 6. Actionable next steps

### A. Planning

Keep this diagnostic as a truth anchor for future slices involving:
- meta-learning
- replay/backtest
- calibration
- artifact flow

### B. Coding

Prioritize slices that improve the real loop:

1. stronger post-trade diagnostics
2. stronger local calibration artifacts
3. runtime consumers of signed calibration artifacts
4. proof that the loop remains governed from Local IA Lab to VPS

Latest closure on point 1:
- `src/meta_minimal/meta_runtime.py` now exposes a public `DTR records -> MetaRuntimeResult` rebuild path
- `scripts/run_local_lab_post_trade_review.py` now provides a governed Local IA Lab entrypoint for post-trade review from exported replay DTR evidence
- the same launcher now also accepts a governed `export_dir` and recovers sidecar provenance through `discover_local_replay_export(...)`
- the launcher now emits a future-facing ingestion sidecar `governed_input_summary.json`
- the launcher now also emits `trade_loss_attribution.json` as the bounded per-trade explanation/suggestion surface
- this sidecar is the current Local IA Lab answer to:
  - why this trade lost
  - what should prevent the next similar loss
- `scripts/run_local_lab_analysis_bundle.py` now chains one governed `export_dir` into post-trade review + EDGE calibration + a single `local_lab_analysis_summary.json`
- the same chain now also emits a governed walk-forward human-review template/summary pair
- the same chain now also emits:
  - `artifact_proof_summary.json`
  - `artifact_proof_assessment.json`
- the same chain now also emits `artifact_ablation_study.json`
- with `--baseline-export-dir`, the Lab can now compare candidate vs baseline on aligned governed `DTRRecord` ids
- the proof layer can therefore consume real:
  - `ablation_delta_net_pnl`
  - `ablation_delta_ce`
  - `block_rate_delta`
  instead of keeping those dimensions permanently empty
- the same chain now also supports governed multi-scope analysis from one export:
  - `scripts/run_local_lab_analysis_bundle.py --all-scopes`
  - `src/local_replay_runtime/local_lab_scope_matrix.py`
  - `local_lab_scope_matrix.json`
- this lets the Lab analyze one multi-scope export as a bounded `pair x engine` matrix instead of forcing manual reruns scope by scope
- each scope now materializes its own governed sidecars under `output-root/scopes/<pair>__<engine>/`
- the matrix exposes future-dashboard-ready status per scope:
  - `artifact_ablation_ready`
  - `artifact_proof_ready`
  - `artifact_proof_validation_reasons`
- proof remains conservative in the multi-scope path:
  - scope-level `total_opportunities` is recomputed from scope evidence
  - walk-forward approval stays global/human-gated
  - no scope becomes `ready` without aligned baseline evidence
- the same chain now also emits `artifact_release_candidate.json`
- this is the current Local IA Lab packaging-side answer to:
  - is the current artifact still `local_only`
  - or can it become a governed `shadow_candidate`
  - and, if blocked, by which typed reasons
- this sidecar also projects per-scope release readiness when a multi-scope matrix exists
- the same chain now also emits a bounded governed dry-run bridge:
  - `artifact_import_dry_run_bridge.json`
  - `artifact_upload_request.dry_run.json`
  - `artifact_import_request.dry_run.json`
  - `artifact_import_decision.dry_run.json`
  - `artifact_upload_decision.dry_run.json`
- this new bridge reuses the existing `backtest_artifact_import` rail instead of inventing a parallel handoff path
- the bridge now makes the source/transport semantics explicit:
  - the Local IA Lab source artifact remains the calibration artifact (`edge_gate.yml`)
  - the current governed dry-run handoff still rides on a replay-derived transport packet of kind `review_packet`
  - the sidecar now exposes that duality instead of pretending both ids/kinds are the same artifact
- it stays fail-close:
  - no hidden governance date default
  - no silent artifact class/scope defaults
  - no dry-run payloads are materialized unless the release candidate is ready and the governance inputs are explicit
- important current limitation:
  - the bridge is still a dry-run/proof-packet handoff around the governed replay/import rail
  - it is not yet the final live packaging semantics for every future Lab-produced artifact
- this new proof layer is conservative by design:
  - it computes what the repo can already justify from current Local IA Lab evidence
  - it keeps non-proven dimensions fail-close instead of fabricating a passing proof
- doctrine now reflected in code:
  - walk-forward/backtest computation can stay automated
  - approval against leakage/overlap must remain human
  - `walk_forward_pass` must stay false until that human gate is approved

### C. Explicit non-goal

Do not build a live bidirectional Local IA Lab / VPS synchronization layer in the current perimeter.

---

## 7bis. Latest bounded handoff refinement

- the Local IA Lab chain now also emits `artifact_source_summary.json`
- this gives the future dashboard and audit tooling a stable source-artifact projection without changing the governed import rail
- the dry-run handoff still rides on a replay-derived `review_packet`
- but that transport packet now also carries:
  - the real Local IA Lab source artifact ref
  - the source summary ref
  - through `ArtifactPayloadRefBundle.supplementary_refs`
- this is the current truthful answer to:
  - how the Lab artifact relates to the current VPS import packet
  - how future tooling can inspect that relation without inventing a new rail

## 7ter. Latest bounded recalibration planning refinement

- the same Local IA Lab chain now also emits `local_lab_recalibration_plan.json`
- this is the current Local IA Lab answer to:
  - which threshold families are recommended for recalibration from governed loss evidence
  - which cases must remain blocked because evidence is weak or scopes are not ready
- it stays local-only:
  - no VPS mutation
  - no direct artifact promotion
  - no bypass of replay/backtest/human review

## 7quater. Latest bounded provenance connection

- the EDGE producer now carries `local_lab_recalibration_plan.json` provenance through `edge_gate.input_summary.json`
- this means the Local IA Lab can now show, on the artifact producer itself:
  - which local plan triggered the refresh
  - whether recalibration was actually judged ready
  - which threshold ids were implicated
- this remains a local audit/provenance refinement, not a VPS-side mutation

## 7quinquies. Latest bounded release-gate projection

- the Local IA Lab handoff now projects its own release verdict explicitly in the dry-run bridge
- future tooling no longer needs to infer from separate sidecars whether a candidate is:
  - proof-backed
  - recalibration-backed
  - proof-backed with recalibration not required
- the current bridge now reports:
  - `release_gate_status`
  - `release_gate_reasons`
  - proof and recalibration readiness mirrors copied from the packaging verdict
- important invariant:
  - this is still a dry-run bridge over the current governed import rail
  - no VPS-side mutation or new artifact kind is introduced by this slice

## 7sexies. Latest bounded release-gate sidecar transport

- the same Local IA Lab handoff now also emits `artifact_release_gate_summary.json`
- that sidecar is now carried by the dry-run transport packet itself through `supplementary_refs`
- future tooling can now inspect, from the packet perimeter alone:
  - source artifact relation
  - source artifact summary
  - release-gate verdict summary
- important invariant:
  - this still does not create a live Lab -> VPS channel
  - it only makes the current dry-run handoff more self-describing and audit-ready

## 7septies. Latest bounded multi-scope release drill-down

- the Local IA Lab packaging verdict is now more self-contained for multi-scope exports
- `artifact_release_candidate.json` now carries per-scope drill-down refs and counts instead of only `pair/engine/release_ready`
- the top-level Local IA Lab summary now also exposes:
  - ready scope slugs
  - blocked scope slugs
- important invariant:
  - scope drill-down remains descriptive
  - it does not imply a new per-scope VPS import rail or per-scope live mutation path

## 7octies. Latest bounded per-scope release-sidecar transport

- multi-scope Local IA Lab runs now also emit one `artifact_release_scope_summary.json` per scope
- each sidecar binds together:
  - scope proof/review evidence
  - shared release verdict
  - shared dry-run handoff bridge
- important invariant:
  - this is still Local IA Lab packaging metadata
  - it does not create a new VPS-side import object per scope

## 7novies. Latest bounded scope-matrix packaging projection

- the Local IA Lab scope matrix now reflects both proof and release packaging status
- future tooling can now read from the same matrix:
  - proof-ready scope counts
  - release-ready scope counts
  - per-scope release blockers
  - per-scope release summary refs
- important invariant:
  - this is still a projection layer over the same Local IA Lab run
  - it does not introduce a second source of truth separate from the packaging sidecars

## 7decies. Latest bounded promotion-readiness summary

- the Local IA Lab handoff now also emits one top-level `artifact_promotion_readiness_summary.json`
- this summary bridges Local IA Lab packaging truth to canonical VPS-facing vocabulary:
  - activation stage
  - normalized promotion state
  - review state
- important invariant:
  - this is still not a promotion action
  - it is only an audit-ready summary over the same dry-run handoff rail

## 7undecies. Latest bounded Local IA Lab monitoring projection

- the same Local IA Lab handoff now also emits one compact `local_lab_monitoring_projection.json`
- this projection is intended as the stable future dashboard/monitoring surface over the same run
- it does not replace the detailed sidecars; it summarizes them
- current normalized fields include:
  - core analysis readiness
  - packaging / dry-run bridge truth
  - canonical promotion vocabulary already computed upstream
  - scope and release counts
- important invariant:
  - this remains a descriptive Local IA Lab sidecar only
  - it does not create UI coupling or any new VPS mutation path

## 7duodecies. Latest bounded Local IA Lab observability export

- the same Local IA Lab chain now also emits `local_lab_observability_export.json`
- this export reuses the repo standard `ObservabilityExport` shape instead of inventing a bespoke metrics file
- it provides:
  - numeric metric samples
  - a text-export payload for later ingestion
  - no UI coupling
- important invariant:
  - this stays descriptive over the Local IA Lab run
  - it is not a control plane and does not affect promotion/runtime behavior

## 7terdecies. Latest bounded Local IA Lab monitoring backend payload

- the same Local IA Lab chain now also emits `local_lab_monitoring_backend_payload.json`
- this payload is built from:
  - the compact `local_lab_monitoring_projection.json`
  - the standard `local_lab_observability_export.json`
- it is intended as the future backend-facing summary for detailed Local IA Lab monitoring
- current normalized content includes:
  - run/export/artifact identifiers
  - core review/proof/recalibration readiness
  - packaging and dry-run handoff truth
  - scope/release counts
  - refs back to detailed sidecars
- important invariant:
  - this remains descriptive only
  - it does not create a second source of truth
  - it does not introduce UI or VPS mutation semantics

## 7quaterdecies. Latest bounded Local IA Lab monitoring ingestion summary

- the same Local IA Lab chain now also emits `local_lab_monitoring_ingestion_summary.json`
- this summary is built from:
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- it is intended as the first monitoring-side ingestion verdict for future backend/Prometheus pipelines
- current checks are intentionally bounded:
  - payload/export `correlation_id` alignment
  - payload/export `profile` alignment
  - payload/export `runtime_mode` alignment
  - payload/export `timestamp_ms` alignment
  - non-empty metrics/text export presence
- important invariant:
  - this remains descriptive ingestion plumbing only
  - it does not create runtime coupling with Build-10
  - it does not change the governed Local IA Lab -> VPS rail

## 7quindecies. Latest bounded Local IA Lab monitoring bundle loader

- a future backend can now reload the Local IA Lab monitoring trio from disk through `src/monitoring/local_lab_bundle_loader.py`
- the loader validates:
  - file presence
  - typed JSON validity
  - alignment of `correlation_id/profile/runtime_mode/timestamp_ms`
- this is the first file-based backend ingestion path over the Local IA Lab monitoring sidecars
- important invariant:
  - it stays descriptive only
  - it does not import anything into VPS
  - it does not couple the Local IA Lab bundle to Build-10 runtime orchestration

## 7. Acceptance criteria

- [x] the current repo truth is mapped, not guessed
- [x] historical snapshot ingestion is identified
- [x] post-trade structured ingestion is identified
- [x] strategy/review bundle ingestion is identified
- [x] governed replay sidecar ingestion is identified
- [x] the missing live bidirectional loop is stated explicitly
