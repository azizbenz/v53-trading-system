# Build 11 Repo-Truth Audit - Shadow Runtime - 2026-04-22

## Scope

This note audits **Build 11** only:

- `protocols.shadow_runtime*`
- `protocols.contracts_shadow`
- `protocols.promotion_gates`
- the current Shadow day counter / session registry / daily orchestrator
- the current Shadow VPS service and dashboard projections

It answers one question:

> Does current Build-11 code match the doctrinal expectation closely enough, or
> is there meaningful drift between the expected Shadow runtime and the real
> implementation?

## Doctrine Claim

Current doctrinal baseline is the combination of:

- `src/manifest_registry/build_order_registry.py`
- `docs/production_deployment_plan/12_LOCAL_LAB_VS_VPS_SEPARATION.md`
- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`

Repo-doctrine summary for Build 11:

- Build 11 is the governed Shadow runtime stage.
- It must preserve the official promotion ladder:
  - Replay -> Shadow -> Micro-live -> Live-Light
- It must **not** auto-promote.
- It must enforce the 30-day Shadow gate before later promotion.
- It must remain typed, auditable, and operator-visible.
- The canonical local replay export/import rail must remain valid.

## Repo-Truth Surface

### 1. Build 11 contracts are real and strongly governed

Observed in:
- `src/protocols/contracts_shadow.py`

Current repo-truth Build-11 contracts include:
- `ShadowTruthSet`
- `ShadowValidationSet`
- `ShadowInput`
- `ShadowComparison`
- `ShadowDecision`
- `ShadowRunSummary`
- `ShadowReportArtifact`
- per-component, per-engine, and Build-14 contribution contracts

Observed governance guards include:
- `runtime_mode=SHADOW` enforced
- `profile=COMPLETE` enforced at `ShadowInput`
- no local/backtest profile fork
- `automatic_promotion_requested` explicitly forbidden

Interpretation:
- Build 11 is not a loose script rail
- the Shadow phase is already encoded as a typed governed contract surface

### 2. The core Shadow runtime rail is real

Observed in:
- `src/protocols/shadow_runtime.py`
- `src/protocols/shadow_runtime_validation.py`
- `src/protocols/shadow_runtime_inputs.py`
- `src/protocols/shadow_runtime_judgments.py`
- `src/protocols/shadow_runtime_portfolio.py`

Current repo-truth provides:
- typed input building from real payloads
- candidate comparison
- Shadow validation
- engine judgment derivation
- portfolio judgment derivation
- 30-day gate check helper

Interpretation:
- Build 11 is operationally real
- the Shadow phase is not only a counter; it is already a real comparison and
  judgment stage over full-system payloads

### 3. The 30-day gate is real and durable

Observed in:
- `src/protocols/shadow_day_counter.py`
- `src/protocols/shadow_session_registry.py`
- `src/protocols/shadow_daily_orchestrator.py`
- `src/protocols/promotion_gates.py`

Current repo-truth includes:
- persistent 30-day counter
- gap reset logic
- durable day records
- append-only session registry
- external daily slot orchestration
- explicit promotion gate checks and launcher surface

Interpretation:
- the famous “30 consecutive Shadow days” rule is not just doctrinal prose
- it is already encoded as a durable governed subsystem

### 4. Shadow VPS service is real, not hypothetical

Observed in:
- `src/protocols/shadow_vps_service.py`
- `src/protocols/shadow_live_websocket.py`
- `src/protocols/shadow_websocket_ingest.py`

Current repo-truth Build-11 service surface includes:
- persisted service state
- event journaling
- raw input slot support
- injected websocket slot support
- native live websocket capture support
- runtime evidence bundle persistence
- campaign summary persistence
- optional execution-runtime, regime-lite, info-stress, and telegram sidecars

Interpretation:
- Build 11 already has a real long-running VPS-side service rail
- this is broader than a minimal “gate check only” story

### 5. Build 11 is operator-visible

Observed in:
- `src/protocols/shadow_dashboard.py`
- `src/protocols/shadow_report_builder.py`
- `src/protocols/__init__.py`

Current repo-truth includes:
- Shadow dashboard projection
- daily report metric materialization
- canonical facade exports through `protocols`

Interpretation:
- Build 11 is already wired into the operator-facing supervision surface

## Verification Evidence

### Shadow runtime, counter, orchestrator, dashboard, registry, VPS service

Command:

```powershell
python -m pytest tests/test_protocols/test_shadow_runtime.py tests/test_protocols/test_shadow_day_counter.py tests/test_protocols/test_shadow_daily_orchestrator.py tests/test_protocols/test_shadow_dashboard.py tests/test_protocols/test_shadow_session_registry.py tests/test_protocols/test_shadow_vps_service_launcher.py -q --tb=short
```

Result:
- `80 passed`

### Promotion gates and launcher

Command:

```powershell
python -m pytest tests/test_protocols/test_promotion_gates.py tests/test_protocols/test_promotion_gates_bs_sequential_regression.py tests/test_protocols/test_shadow_gate_check_launcher.py -q --tb=short
```

Result:
- `29 passed`

### Notes on warnings

Observed warning:
- pytest cache path creation warning under `.pytest_cache`

Interpretation:
- not a Build-11 doctrine/code issue
- no audited Build-11 functional failure

## Observed Divergence

### Divergence 1 - Build 11 current code is broader than the simple markdown story

The simplified doctrinal story often compresses Build 11 to:
- Shadow gate
- 30-day evidence
- promotion readiness

Current repo-truth is broader:
- typed Shadow contracts
- full validation and judgment logic
- day counter + session registry + daily orchestrator
- Shadow VPS service
- live websocket capture
- operator/dashboard projection

Interpretation:
- this is not a dangerous code drift
- it is a real documentation compression drift

### Divergence 2 - the canonical replay->shadow rail still exists, but Build 11 now supports additional governed input modes

Doc 12 correctly states that the canonical rail
- `local_replay_runtime -> governed export -> backtest_artifact_import -> VPS Shadow`
must not be replaced.

Current repo-truth does preserve that rail, but Build 11 also supports additive
governed modes such as:
- raw dataset slot ingestion
- injected websocket slot ingestion
- native live websocket capture

Interpretation:
- current code is broader than the narrow replay-only story
- but there is no evidence that the canonical rail was removed or bypassed

### Divergence 3 - public gate helpers still expose LIGHT compatibility surfaces while core Shadow input is COMPLETE-only

Observed in:
- `src/protocols/contracts_shadow.py`
- `src/protocols/promotion_gates.py`

Current repo-truth split:
- core `ShadowInput` requires `ProfileId.COMPLETE`
- `promotion_gates.py` still exposes `check_light_to_micro_live(...)` for legacy
  compatibility/tests

Interpretation:
- this is not a broken governance surface
- but it means Build 11 is not a perfectly clean doctrinal `MATCH`
- compatibility edges still exist in the public gate helpers

## Decision

`PARTIAL`

## Why

Build 11 is clearly **implemented, typed, and green** on its audited current
surface.

What is already present:
- typed Shadow contracts
- full Shadow validation/judgment rail
- durable 30-day counter
- session registry
- daily orchestrator
- promotion gate checks
- VPS service
- websocket capture
- dashboard/report projection

So Build 11 is not `STALE_CODE`, and not broken.

But it is not `MATCH` either, for three concrete reasons:

1. the markdown story underdescribes how broad the current Build-11 surface now is
2. current Build-11 supports additive governed input modes beyond the simple
   replay-only narrative
3. the public gate helpers still retain LIGHT compatibility while the core
   Shadow runtime governance is COMPLETE-only

So the correct ruling is:
- Build 11 is operationally real and healthy
- but the doctrinal narrative is narrower and cleaner than the actual current
  repo-truth surface

## Patch Target

`docs only`

### Docs target

Clarify that current repo-truth Build 11 already includes:
- typed Shadow contracts
- full Shadow validation/judgment
- 30-day counter + registry + orchestrator
- explicit gate helpers
- VPS service and live websocket capture
- dashboard/report projection

Also clarify:
- the canonical replay/import rail still stands
- additional governed input modes exist additively
- LIGHT compatibility helpers still exist at the gate layer, even though the
  core Shadow runtime is COMPLETE-governed

### No target

No Build-11 code redesign is justified by this audit.

The current Shadow rail is already strongly governed and well tested.

## Final Verdict

Build 11 is operationally strong but doctrinally compressed.

Safe operational classification:
- `Build 11 = PARTIAL (real governed Shadow runtime, counter, gates, and VPS service exist and are green; markdown underdescribes the current Build-11 breadth, additive input modes, and remaining compatibility gate helpers)`
