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

---

## 7ter. Latest execution ingestion closure

The Local IA Lab execution-ingestion rail now goes beyond evidence transport and supports first bounded execution models on service-owned telemetry:
- `THR-X03` from quota probe telemetry + official quota cap
- `THR-X05` from service-owned `size/slippage` traces

Current truthful boundary:
- the bounded models exist on the Lab side
- the evidence remains service-owned and typed
- this still does not authorize any automatic VPS-side recalibration or live mutation
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

## 7sexdecies. Latest bounded Local IA Lab observability text export

- the same Local IA Lab chain now also emits `local_lab_observability.prom`
- this file is derived directly from the standard `ObservabilityExport.text_payload`
- it is the first scrape-friendly text export over the Local IA Lab monitoring truth
- important invariant:
  - it stays descriptive only
  - it does not create a new runtime
  - it does not change any governed handoff or promotion semantics

## 7. Acceptance criteria

- [x] the current repo truth is mapped, not guessed
- [x] historical snapshot ingestion is identified
- [x] post-trade structured ingestion is identified
- [x] strategy/review bundle ingestion is identified
- [x] governed replay sidecar ingestion is identified
- [x] the missing live bidirectional loop is stated explicitly

## 7septdecies. Latest bounded Local IA Lab research-priority scorer

- the same Local IA Lab chain now also emits `local_lab_research_priority.json`
- this sidecar is built from governed Local IA Lab evidence already produced by the chain:
  - per-trade loss attribution
  - scope matrix when available
  - proof/release readiness
- its purpose is bounded:
  - rank which `pair x engine` scope deserves the next replay/recalibration cycle
  - separate `trace_capture` work from true recalibration work
  - expose a future-monitoring-ready summary without creating UI coupling
- important invariant:
  - this is not a runtime model
  - this does not mutate VPS behavior
  - this does not create promotion authority

## 7octodecies. Latest bounded Local IA Lab loss-surrogate scorer

- the same Local IA Lab chain now also emits `local_lab_loss_surrogate_report.json`
- this sidecar is the first truly trained but still transparent Local IA Lab model:
  - `model_family=transparent_linear_loss_surrogate_v1`
  - `model_kind=diagonal_lda_linear_score`
  - local-only only
  - research-only only
- training inputs remain no-lookahead and decision-time only:
  - `raw_score`
  - `penalized_score`
  - `final_score`
  - `expected_cost`
  - `ce_expected`
  - `candidate_size`
  - `final_size`
  - `ranking_position`
- its purpose is bounded:
  - estimate which scopes currently carry the highest modeled loss pressure
  - surface a compact future-monitoring-ready signal
  - not replace detailed per-trade attribution or proof sidecars
- important invariant:
  - this is not a VPS/runtime model
  - this does not mutate promotion state
  - this does not authorize artifact import by itself

## 7novodecies. Latest bounded Local IA Lab surrogate-guided planning

- the same Local IA Lab chain now also feeds the trained loss surrogate into:
  - `local_lab_research_priority`
  - `local_lab_recalibration_plan`
- the integration stays bounded:
  - it can elevate research priority for a scope
  - it can add a local replay recommendation for a high-risk scope
  - it cannot by itself authorize recalibration publication or VPS import
- important invariant:
  - the surrogate remains advisory only
  - proof/release/promotion semantics stay governed elsewhere
  - no VPS/runtime coupling is introduced

## 7vicies. Latest bounded Local IA Lab replay candidate queue

- the same Local IA Lab chain now also emits `local_lab_replay_candidate_queue.json`
- this queue is derived from current local-only planning truth:
  - research priority
  - recalibration plan
  - surrogate-guided evidence already emitted by the bundle
- its purpose is bounded:
  - identify the next replay/research scopes the Lab should process
  - keep blocked work visible (`trace_capture`, `human_scope_review`, `manual_loss_review`)
  - expose a compact future-monitoring-ready workflow surface without UI coupling
- important invariant:
  - this is not a runtime scheduler
  - this does not mutate VPS behavior
  - this does not create promotion authority

## 7unvicies. Latest bounded Local IA Lab replay ticket index

- the same Local IA Lab chain now also emits `local_lab_replay_ticket_index.json`
- this index is derived from the local replay candidate queue and reuses the canonical `LocalReplayRequest` contract
- its purpose is bounded:
  - prepare governed local replay tickets for future automation or operator review
  - keep blocked tickets explicit when the queue is not truly replay-ready
  - expose a compact future-monitoring-ready work surface without UI coupling
- important invariant:
  - this is not an execution surface
  - this does not mutate VPS behavior
  - this does not create promotion authority

## 7duovicies. Latest bounded Local IA Lab replay dispatch plan

- the same Local IA Lab chain now also emits `local_lab_replay_dispatch_plan.json`
- this plan is derived from the governed replay ticket index and stays explicitly non-executing
- its purpose is bounded:
  - separate ready local replay work from blocked local replay work
  - prepare a future automation/loader surface without running anything
  - expose a compact future-monitoring-ready dispatch truth without UI coupling
- important invariant:
  - this is not an execution surface
  - this does not mutate VPS behavior
  - this does not create promotion authority

## 7tervicies. Latest bounded Local IA Lab workflow/monitoring discovery manifests

- the same Local IA Lab chain now also emits `local_lab_replay_workflow_manifest.json`
- this manifest binds together the current local replay workflow sidecars:
  - replay candidate queue
  - replay ticket index
  - replay dispatch plan
- on the monitoring side, the chain now also emits `local_lab_monitoring_bundle_manifest.json`
- this manifest binds together the current monitoring ingestion sidecars:
  - monitoring backend payload
  - observability export
  - monitoring ingestion summary
  - optional replay workflow manifest ref
- purpose:
  - future backend/Prometheus/dashboard ingestion should discover one manifest first, not hardcode sidecar names
  - keep the bundle self-describing and audit-ready
- important invariant:
  - local-only discovery surface
  - no UI coupling
  - no VPS/runtime mutation
  - no promotion authority

## 7quattuorvicies. Latest bounded Local IA Lab monitoring bundle discovery

- `src/monitoring/local_lab_bundle_discovery.py` now exists as the next bounded backend step over the monitoring bundle manifest
- purpose:
  - scan a root for Local IA Lab monitoring bundle manifests
  - order bundles by latest governed timestamp
  - load the latest valid monitoring bundle without hardcoded directory knowledge
- important invariant:
  - still local/backend only
  - still no UI coupling
  - still no VPS/runtime mutation
  - still no promotion authority

## 7quinvicies. Latest bounded Local IA Lab monitoring feed

- `src/monitoring/local_lab_monitoring_feed.py` now exists over discovered monitoring bundles
- purpose:
  - summarize latest bundle truth plus bundle counts by backend status/ingestion readiness
  - prepare the first compact multi-bundle backend surface without opening every bundle in detail
- important invariant:
  - still local/backend only
  - still no UI coupling
  - still no VPS/runtime mutation
  - still no promotion authority

## 7sexvicies. Latest bounded Local IA Lab calibration-methods review

- the same Local IA Lab chain now also emits `local_lab_calibration_methods_review.json`
- this review is the first direct proof-side consumer of the shared calibration-methods core:
  - purged walk-forward geometry
  - Deflated Sharpe Ratio
- its purpose is bounded:
  - make Local IA Lab calibration-method evidence explicit on the proof rail
  - keep insufficient history visible as `partial`
  - block local proof when DSR is truly computed and fails floor
- the same truth now also propagates into:
  - `local_lab_analysis_summary.json`
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- important invariant:
  - still local-only
  - still no UI coupling
  - still no VPS/runtime mutation
  - human walk-forward approval remains a separate hard gate

## 7septemvicies. Latest bounded Local IA Lab release/dry-run calibration-methods propagation

- the same Local IA Lab chain now also carries calibration-methods truth into:
  - `artifact_release_candidate.json`
  - `artifact_release_gate_summary.json`
  - `artifact_import_dry_run_bridge.json`
- purpose:
  - make the handoff explicitly say whether the candidate is calibration-methods-backed
  - keep proof-backed vs calibration-backed truth readable before any future VPS import
- important invariant:
  - still local-only
  - still no UI coupling
  - still no VPS/runtime mutation

## 7octovicies. Latest bounded Local IA Lab monitoring manifest/discovery/feed calibration-methods propagation

- the monitoring bundle manifest now carries compact calibration-methods truth
- discovery and compact feed now propagate it across multiple Local IA Lab bundles
- purpose:
  - let future backend ingestion count ready vs partial vs blocked calibration-methods bundles without opening every sidecar manually
  - keep discovery manifest-first and audit-ready
- important invariant:
  - still local/backend only
  - still no UI coupling
  - still no VPS/runtime mutation

## 7novemvicies. Latest bounded Local IA Lab tail-risk review

- the same Local IA Lab chain now also consumes exported governed `DTRRecord` history for strategy-level tail-risk evidence
- `src/calibration_methods/pot_gpd.py` now provides the bounded POT-GPD helper used by:
  - `src/local_replay_runtime/local_lab_tail_risk_review.py`
- `scripts/run_local_lab_analysis_bundle.py` now emits `local_lab_tail_risk_review.json`
- current scope is intentionally top-level, not pair-engine scope:
  - daily breaker `THR-R01`
  - weekly breaker `THR-R02`
  - monthly breaker `THR-R03`
- purpose:
  - make exported replay/post-trade history usable for bounded EVT-style Local IA Lab review
  - expose compact future-dashboard/backend truth without changing release semantics
- important invariant:
  - still local-only
  - still no UI coupling
  - still no VPS/runtime mutation
  - not yet a release gate by itself

## 7tricies. Latest bounded Local IA Lab stationarity gate

- the same Local IA Lab chain now also emits explicit MI-9 evidence from `src/calibration_methods/stationarity.py`
- `local_lab_calibration_methods_review.json` now carries:
  - `stationarity_status`
  - `stationarity_ready`
  - `stationarity_pass`
  - dual ADF + KPSS result
- purpose:
  - make no-lookahead calibration evidence stricter before any artifact is considered locally proof-backed
  - keep insufficient history explicit as `partial`
  - block local proof when stationarity truly fails, not only when DSR fails
- compact future-dashboard/backend truth now also propagates into:
  - `local_lab_calibration_normalized_report.json`
  - `local_lab_analysis_summary.json`
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- important invariant:
  - still local-only
  - still no UI coupling
  - still no VPS/runtime mutation

## 7untricies. Latest bounded shared human hard-cap helper

- the same Local IA Lab chain now also uses `src/calibration_methods/hard_cap_floor.py`
- purpose:
  - centralize conservative publication against human floors/caps
  - keep audit semantics explicit with:
    - `hard_cap_satisfied`
    - `hard_cap_binding`
- current bounded consumers:
  - `edge_gate_calibration`
  - `local_lab_tail_risk_review`
  - `local_lab_calibration_normalized_report`
- important invariant:
  - still local-only
  - still no UI coupling
  - still no VPS/runtime mutation

## 7duotricies. Latest bounded Local IA Lab multiple-testing review

- the same Local IA Lab chain now also emits explicit MI-12 evidence from:
  - `src/calibration_methods/multiple_testing.py`
  - `src/local_replay_runtime/local_lab_multiple_testing_review.py`
- current truth:
  - the bounded Local IA Lab calibration families are still conservative interval-publication outputs
  - therefore MI-12 is currently explicit `not_required_interval_publication`, not a fake p-value correction pass
  - future hypothesis-test families can still consume the shared Holm-Bonferroni helper when real comparable p-values exist
- this same truth now also propagates into:
  - normalized calibration report
  - proof assessment
  - Local IA Lab analysis summary
  - monitoring/backend/observability bundle sidecars
- important invariant:
  - still local-only
  - still no UI coupling
  - still no VPS/runtime mutation

## 7tertricies. Latest bounded Local IA Lab execution review

- the same Local IA Lab chain now also emits explicit EXECUTION evidence from:
  - `src/calibration_methods/execution.py`
  - `src/local_replay_runtime/local_lab_execution_review.py`
- current truth:
  - `THR-X01` and `THR-X02` can now be reviewed locally when dedicated execution telemetry is provided
  - the default bundle remains explicit `partial` when no execution telemetry sidecar exists
  - no replay export sidecar is silently reinterpreted as venue telemetry
- this same truth now also propagates into:
  - analysis summary
  - monitoring projection/backend/observability
  - monitoring bundle manifest/discovery/feed
- important invariant:
  - still local-only
  - still no UI coupling
  - still no VPS/runtime mutation
  - not yet a proof or release gate by itself

## 7quatertricies. Latest execution runtime projection handoff

- the same Local IA Lab chain now also emits typed future-runtime handoff evidence from:
  - `src/local_replay_runtime/local_lab_execution_runtime_projection.py`
- current truth:
  - `THR-X03` is now projected into a future `rate_limiter` contract
  - `THR-X05` is now projected into a future `slippage_model` contract
  - the projection is service-owned/review-owned handoff metadata only; it is not a runtime mutation
- this same truth now also propagates into:
  - artifact proof assessment
  - artifact release candidate
  - top-level Local IA Lab analysis summary
- important invariant:
  - still local-only
  - still no UI coupling
  - still no VPS/runtime mutation
  - still no gate bypass

## 7quinquetricies. Latest canonical runtime consumer seam

- new current truth:
  - the future-runtime handoff is no longer projection-only
  - `src/execution_backbone/rate_limiter.py` and `src/execution_backbone/slippage_model.py` now exist as bounded canonical consumers for:
    - `THR-X03 -> rate_limiter`
    - `THR-X05 -> slippage_model`
- current bounded behavior:
  - `ExecutionRuntime` only consumes them when they are injected explicitly
  - `THR-X05` is applied conservatively as extra expected-cost friction with audit metadata
  - `THR-X03` remains fail-open unless live metadata already provides `rest_quota_ratio_current`
- invariant preserved:
  - still no automatic VPS bootstrap wiring
  - still no gate bypass
  - still no hidden runtime activation

## 7sexquinquagies. Latest runtime projection bootstrap bridge

- new current truth:
  - `execution_runtime_projection_bridge.py` now loads the Lab-side runtime projection artifact fail-open
  - `execution_runtime_bootstrap.py` now accepts `execution_runtime_projection_path`
  - the canonical runtime can therefore recover `THR-X03/X05` consumers from the same handoff JSON, without manual constructor assembly
- invariant preserved:
  - still explicit opt-in only
  - still no bootstrap activation unless the path is provided
  - still no gate bypass

## 7septsexquinquagies. Latest Build-10 visibility for the runtime projection bridge

- new current truth:
  - Build-10 now exposes the Local IA Lab `execution_runtime_projection_path` seam as a typed monitoring/dashboard/observability surface
  - this surface is separate from the older compiled `execution_no_trade_bridge`, so the operator can distinguish:
    - bounded compiled hook status
    - bounded `THR-X03/X05` runtime-consumer loadability
- invariant preserved:
  - still no hidden runtime activation
  - still descriptive only; no gate or runtime behavior is changed by monitoring projection
  - still no gate bypass
