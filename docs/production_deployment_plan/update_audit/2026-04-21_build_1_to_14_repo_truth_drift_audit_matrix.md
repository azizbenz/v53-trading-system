# Build 1→14 Repo-Truth Drift Audit Matrix — 2026-04-21

## Purpose

This note formalizes a working governance assumption:

> Builds `1` to `14` were likely implemented incrementally before the current
> Carver / Narang / Taleb markdown stack fully stabilized, so drift between
> doctrinal expectation and current code must be presumed until disproven.

This file is not a speculative rewrite plan.

It is a **repo-truth audit matrix** used to compare:

1. current code
2. current tests
3. current canonical build order
4. current doctrinal markdowns

Primary doctrinal references:
- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `docs/production_deployment_plan/12_LOCAL_LAB_VS_VPS_SEPARATION.md`
- `docs/production_deployment_plan/16_VPS_LOCAL_OBSERVABILITY_ARCHITECTURE.md`

Primary repo-truth references:
- `src/manifest_registry/build_order_registry.py`
- current `src/`
- current `tests/`

## Hard Audit Rules

1. Current code is the operational truth.
2. Markdown is doctrinal intent, not automatic implementation proof.
3. A build is not marked `MATCH` unless code + tests confirm it.
4. Known historical drift must be preserved, not hand-waved away.
5. Build order is not the same thing as runtime hot path.

## Status Vocabulary

- `MATCH`: doctrinal expectation and current code are aligned on the audited point.
- `PARTIAL`: implementation exists, but the code seam differs, or alignment is incomplete.
- `STALE_MD`: markdown expectation is no longer the right source of truth for the current code.
- `STALE_CODE`: code has drifted from still-valid doctrine and should be realigned.
- `BLOCKED`: impossible to conclude with current local proof.
- `UNAUDITED`: not yet audited at build level.

## Per-Build Audit Matrix

| Build | Canonical stage name | Hot path per signal? | Current audit status | Repo-truth anchor | Known drift / known risk |
|---|---|---:|---|---|---|
| `1` | `Dependency Architecture` | `No` | `PARTIAL` | `manifest_registry`, `interface_contracts`, DAG/bootstrap | Verified coherent and green, but the markdown story underdescribes the current Build-1 surface, especially additive contracts, engineering guardrails, and shared calibration loading |
| `2` | `Data Backbone` | `Yes` | `PARTIAL` | `data_backbone`, `regime_classifier` | Real ingress, normalization, freshness, consistency, routing, pair-health, REST bootstrap, microstructure, market-physics, and bounded `regime_lite` seams are green, but the markdown story underdescribes the current Build-2 breadth while ingress timing remains local to Build 2 rather than a full end-to-end signal path metric |
| `3` | `Execution Backbone` | `Yes` | `PARTIAL` | `execution_backbone` | Runtime and bootstrap are real and green, a canonical runtime-level `signal_arrival_monotonic_s -> submit_order(...)` metric now exists, that metric is decomposed into scoring/risk/portfolio stage slices and projected into current monitoring/UI surfaces, and a canonical typed upstream stitch into `ExecutionOpportunity` now exists in `protocols`, while later markdown execution expansion remains ahead of current repo-truth |
| `4` | `Risk Backbone` | `Yes` | `PARTIAL` | `risk_backbone` + engine runtime risk evaluation seams | Real stateful `RiskRuntime`, typed explainability, additive precheck seams, and engine hot-path integration are green, but the markdown story underdescribes the current Build-4 breadth while later doc 19/20 risk add-ons remain planned rather than current repo-truth |
| `5` | `Scoring Backbone` | `Yes` | `PARTIAL` | `scoring_backbone` + engine runtime scoring seams | Real `ScoringRuntime`, typed scoring audits, ranking/portfolio compatibility, forecast/break-even/fee-aware-edge seams, and engine hot-path integration are green, but the markdown story underdescribes the current Build-5 breadth while later doc 19/20 scoring additions are mixed: some are already real and `ml_fusion.py` remains planned rather than current repo-truth |
| `6` | `Engine A` | `Yes` | `PARTIAL` | `engines/engine_a` | Real runner, runtime, scoring/risk integration, forecast projection, and standalone adapter seams are green, but the markdown story underdescribes the current Build-6 breadth while the public adapter remains additive rather than the canonical runtime rail |
| `7` | `Engine B` | `Yes` | `PARTIAL` | `engines/engine_b` | Real runner, runtime, scoring/risk integration, forecast projection, refusal handling, and standalone adapter seams are green, while the main proven historical drift was a stale smoke scenario that had to be realigned to current Engine B code-truth |
| `8` | `Portfolio Minimal` | `Yes` | `PARTIAL` | `portfolio` facade + `portfolio_minimal` | Portfolio facade and orchestrator are real and green, and a canonical typed projection seam from viable portfolio output to `ExecutionOpportunity` now exists in `protocols`, but later doc 19/20 enrichments such as Carver vol-target sizing and `PortfolioArbitrationRecord` are not current repo-truth surfaces |
| `9` | `Meta Minimal` | `No` for order departure | `PARTIAL` | `meta`, `meta_minimal` | Canonical facade and richer `meta_minimal` runtime are real and green, but the markdown story underdescribes the current Build-9 breadth, especially typed runtime/input-source semantics, additive cost-drift and refusal-journal seams, and the facade/implementation split |
| `10` | `Monitoring + Operator UI` | `No` | `PARTIAL` | `monitoring`, `ui` | Build 10 monitoring and UI surfaces are both real and green, but the docs underdescribe the current Prometheus/Grafana operator stack and over-compress the build into a simpler single-dashboard narrative |
| `11` | `Shadow Runtime` | `No` for micro-latency; yes for campaign gating | `PARTIAL` | `protocols.shadow_runtime*` | Typed Shadow contracts, counter, gates, dashboard, and VPS service are real and green, but the markdown story underdescribes the current Build-11 breadth, additive input modes, and remaining LIGHT compatibility helpers |
| `12` | `Micro-live` | `No` for micro-latency; yes for campaign gating | `PARTIAL` | `protocols.micro_live_runtime*` | Typed Build-12 contracts, gate logic, readiness enforcement, and dashboard projection are real and green, but the markdown story underdescribes the current Build-12 breadth, and legacy `LIGHT` compatibility helpers still exist in `promotion_gates.py` while the core runtime rail is `COMPLETE`-only |
| `13` | `Live-Light` | `No` for micro-latency; yes for campaign gating | `PARTIAL` | `protocols.live_light_runtime*` | Typed Build-13 contracts, fail-closed gate logic, execution-intent seam, typed Build-14 influence handling, and dashboard projection are real and green, but the markdown story underdescribes the current Build-13 breadth, and legacy `LIGHT` compatibility helpers still exist in `promotion_gates.py` while the core runtime rail is `COMPLETE`-only |
| `14` | `Governed Enablers` | `No` by default; additive influence only | `STALE_MD` | `build14_contracts`, `monitoring.build14_observation`, `complete_enablers.limited_influence` | Old MD/spec assumptions about fake enabler outputs and bridge shapes are wrong for current code; repo-truth is the two-step pipeline |

## Proven Drift Already Confirmed

### Build 3

- `ExecutionRuntime.submit_opportunity(...)` is real and adapter-backed.
- Current repo-truth now also includes a canonical runtime-level pre-submit seam:
  - `ExecutionOpportunity.signal_arrival_monotonic_s`
  - `ExecutionOpportunity.scoring_completed_monotonic_s`
  - `ExecutionOpportunity.risk_completed_monotonic_s`
  - `ExecutionOpportunity.portfolio_completed_monotonic_s`
  - `ExecutionSubmission.signal_to_submit_s`
  - `ExecutionSubmission.signal_to_scoring_s`
  - `ExecutionSubmission.scoring_to_risk_s`
  - `ExecutionSubmission.risk_to_portfolio_s`
  - `ExecutionSubmission.portfolio_to_submit_s`
  - `LatencyMeasurement.signal_to_submit_s`
  - `LatencyMeasurement.signal_to_scoring_s`
  - `LatencyMeasurement.scoring_to_risk_s`
  - `LatencyMeasurement.risk_to_portfolio_s`
  - `LatencyMeasurement.portfolio_to_submit_s`
  - `LatencyStats.avg_signal_to_submit_s`
  - `LatencyStats.avg_signal_to_scoring_s`
  - `LatencyStats.avg_scoring_to_risk_s`
  - `LatencyStats.avg_risk_to_portfolio_s`
  - `LatencyStats.avg_portfolio_to_submit_s`
  - `LatencyStats.p90_signal_to_submit_s`
  - `LatencyStats.p90_signal_to_scoring_s`
  - `LatencyStats.p90_scoring_to_risk_s`
  - `LatencyStats.p90_risk_to_portfolio_s`
  - `LatencyStats.p90_portfolio_to_submit_s`
- Current monitoring now exports:
  - `v53_execution_fill_latency_ms_p95`
  - `v53_execution_signal_to_submit_ms_p90`
  - `v53_execution_signal_to_scoring_ms_p90`
  - `v53_execution_scoring_to_risk_ms_p90`
  - `v53_execution_risk_to_portfolio_ms_p90`
  - `v53_execution_portfolio_to_submit_ms_p90`

Conclusion:
- Build-3 is implemented.
- Build-3 pre-submit latency is now observable inside the runtime and current monitoring surface.
- current repo-truth now includes a canonical pre-submit breakdown across scoring, risk, portfolio, and submit stages.
- current repo-truth now also includes a canonical typed upstream stitch into `ExecutionOpportunity`.
- the remaining partial is later markdown execution expansion that still remains ahead of current code.

### Build 4

Current repo-truth Build 4 already includes:
- stateful `RiskRuntime`
- typed `RiskCandidate`, `RiskEvaluation`, `RiskLimits`, and explainability models
- gross / loss / beta / cluster / drawdown evaluation
- daily PnL, regime, info-stress, and micro-friction precheck seams
- regime-lite entry and safing helpers
- drawdown calibration seam
- direct engine-runtime hot-path integration

But current repo-truth does **not yet** provide the later docs 19/20 planned add-ons:
- `regime_change_detector`
- `tail_risk_meter`
- `regime_shift_watcher`

Conclusion:
- Build-4 implementation is real and green
- the markdown story is too compressed for the current code
- while some later doctrinal risk enrichments remain ahead of current code

### Build 7

The historical smoke scenario for Engine B drifted from the current engine doctrine.

What happened:
- smoke expected `EMIT`
- engine returned `NO_TRADE / CONVICTION_LOW`
- repo-truth audit showed the engine was coherent and the smoke scenario was stale
- the smoke was later aligned via `flow_coherence=0.8`

Conclusion:
- Build-7 already proved that markdown/tests can lag behind code truth.

### Build 8

Current repo-truth Build 8 already provides:
- typed `OpportunityCandidate`
- canonical `portfolio` facade
- ranking / conflict arbitration
- selection
- allocation / cap application
- phantom sterilization

But current repo-truth does **not yet** provide:
- `vol_target_sizer.py`
- `PortfolioArbitrationRecord`

Conclusion:
- Build-8 implementation is real and green
- a canonical portfolio-to-execution projection seam now exists in `protocols`
- but later doctrinal portfolio enrichments remain ahead of current code

### Build 10

Current repo-truth Build 10 includes:
- local Prometheus config generation
- Prometheus text bridging
- Grafana dashboard generation and bootstrap
- shared metric guide panels
- typed technical HTML dashboard rendering

Conclusion:
- Build-10 code is ahead of the older markdown that still treats Grafana as
  pending
- HTML is still real, but no longer the whole operator observability story

### Build 9

Current repo-truth Build 9 already includes:
- canonical `meta` facade
- richer `meta_minimal` implementation package
- typed `MetaRuntime`, `MetaRuntimeInput`, `MetaRuntimeResult`, and statuses
- explicit input-source governance for:
  - `REAL_MARKET`
  - `SHADOW_REAL`
  - `LOCAL_REPLAY`
  - `SYNTHETIC`
- explicit path-warning semantics
- additive `cost_drift_monitor`
- additive `refusal_journal`

Conclusion:
- Build-9 implementation is real and green
- but the stage-description/markdown story is narrower than current code truth
- and the current facade/implementation split must be treated as repo-truth
  rather than flattened back into an older one-layer narrative

### Build 11

Current repo-truth Build 11 already includes:
- typed Shadow contracts
- full validation/judgment rail
- 30-day counter + session registry + daily orchestrator
- explicit promotion gate helpers
- Shadow VPS service with raw, injected-websocket, and live-websocket inputs
- dashboard and report projections

Conclusion:
- Build-11 implementation is real and strongly governed
- the markdown/operator story is narrower than current code truth
- compatibility LIGHT gate helpers still exist even though core Shadow input is COMPLETE-only

### Build 12 / Build 13

Promotion-stage naming and deployment-profile naming were drifting conceptually.

Doctrinal correction already established:
- profiles:
  - `LIGHT`
  - `COMPLETE`
- stage ramp:
  - `Shadow`
  - `Micro-live`
  - `Live-Light`
  - `Live-Complete`

Conclusion:
- any markdown that conflates stage names and profile names must be treated as drift-prone until checked.

### Build 12

Current repo-truth Build 12 already includes:
- typed `MicroLiveInput`, `MicroLiveDecision`, `MicroLiveExecutionPlan`, and `MicroLiveRunSummary`
- Build-11 Shadow evidence gating
- replay/import provenance and lineage enforcement
- engine-scope and portfolio-judgment propagation
- observability / halt / onboarding gating
- execution-runtime projection seam
- dashboard projection

Conclusion:
- Build-12 implementation is real and green
- but the markdown story is narrower than current code truth
- and public promotion-gate helpers still retain a legacy `LIGHT -> micro_live`
  compatibility surface even though the core Build-12 runtime rail is
  `COMPLETE`-governed

### Build 13

Current repo-truth Build 13 already includes:
- typed `LiveLightInput`, `LiveLightDecision`, `LiveLightExecutionIntent`,
  `LiveLightGateGroupSummary`, and `LiveLightRunSummary`
- fail-closed Build-13 gate logic
- explicit small-execution intent seam
- Shadow / Micro-live readiness and scope enforcement
- replay/import provenance and lineage enforcement
- execution / broker / exchange readiness checks
- typed additive Build-14 influence handling
- gate-group and dashboard projection

Conclusion:
- Build-13 implementation is real and green
- but the markdown story is narrower than current code truth
- and public promotion-gate helpers still retain legacy `LIGHT` compatibility
  even though the core Build-13 runtime rail is `COMPLETE`-governed

### Build 14

Current repo-truth Build-14 contracts are:
- `Build14ObservationInput`
- `Build14EnablerSnapshot`
- `Build14InfluenceSignal`
- `Build14InfluenceReport`

Current repo-truth pipeline is:
1. `monitoring.build14_observation` derives observation input
2. `complete_enablers.limited_influence` evaluates to influence report

Conclusion:
- old specs describing fake `MicrostructureEnablerOutput` / `NewsEnablerOutput` /
  `RiskMetricsEnablerOutput` are stale against the current code.
- the dedicated per-build ruling remains `STALE_MD`

## Audit Workflow Per Build

For each build `N`, the audit pass must fill five items:

1. `Doctrine claim`
   - what docs `19/20/...` say the build should do
2. `Repo-truth surface`
   - current source files, contracts, runtime seams, tests
3. `Observed divergence`
   - exact mismatch if any
4. `Decision`
   - `MATCH` / `PARTIAL` / `STALE_MD` / `STALE_CODE` / `BLOCKED`
5. `Patch target`
   - docs only / code only / tests only / mixed / none

## Next Safe Audit Order

First-pass repo-truth verdicts now exist for Builds `1` to `14`.

So the next safe audit order is no longer broad backfill. It is targeted refresh on
the remaining highest-value partials:

1. `Build 10`
   - if the operator surface changes again across Prometheus/Grafana/HTML
2. `Build 9`
   - if the canonical facade/runtime split is narrowed or documented further in code
3. `Build 8`
   - if Carver/Narang portfolio enrichments land
4. `Build 3`
   - if later execution expansion modules from markdown land as current repo-truth

Reason:
- the first-pass build-level audit sweep is now materially complete
- the highest remaining value is no longer broad discovery
- it is targeted re-audit when known `PARTIAL` seams change

## Practical Operating Rule

Until this audit is complete, every new request touching Builds `1→14` should begin with:

> "Assume possible doctrine/code drift until repo-truth is checked."

That rule is now the safe default for V5.3.
