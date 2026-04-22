# Build 13 Repo-Truth Audit - Live-Light - 2026-04-22

## Scope

This note audits **Build 13** only:

- `protocols.live_light_runtime`
- `protocols.live_light_runtime_gate_support`
- `protocols.live_light_runtime_support`
- `protocols.contracts_promotion` on the `LiveLight*` seam
- `protocols.live_light_dashboard`
- the current Build-13 promotion-gate exposure
- the current typed Build-14 influence seam entering Build 13

It answers one question:

> Does current Build-13 code match the doctrinal expectation closely enough, or
> is there meaningful drift between the expected Live-Light stage and the real
> implementation?

## Doctrine Claim

Current doctrinal baseline is the combination of:

- `src/manifest_registry/build_order_registry.py`
- `docs/production_deployment_plan/12_LOCAL_LAB_VS_VPS_SEPARATION.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `docs/production_deployment_plan/update_audit/2026-04-21_stage_naming_vs_profile_naming.md`

Repo-doctrine summary for Build 13:

- Build 13 is the governed **Live-Light** stage.
- It must preserve the official promotion ladder:
  - Replay -> Shadow -> Micro-live -> Live-Light
- It is a **stage name**, not a deployment profile.
- It must remain `COMPLETE`-governed on the real runtime rail.
- It must stay fail-closed and must not auto-promote to a fuller runtime tier.
- It must remain typed, auditable, and operator-visible.
- Build-14 influence must remain additive and bounded.

## Repo-Truth Surface

### 1. Build 13 contracts are real and strongly governed

Observed in:
- `src/protocols/contracts_promotion.py`

Current repo-truth Build-13 contracts include:
- `LiveLightInput`
- `LiveLightDecision`
- `LiveLightExecutionIntent`
- `LiveLightGateGroupSummary`
- `LiveLightRunSummary`

Observed governance guards include:
- `profile=COMPLETE` enforced at `LiveLightInput`
- `runtime_mode=LIVE` enforced
- `backtest_profile` explicitly forbidden
- local/VPS profile forks explicitly forbidden
- automatic promotion explicitly forbidden
- `micro_live_required_days=7` enforced
- `shadow_required_days=30` enforced

Interpretation:
- Build 13 is not a loose "live if everything looks okay" wrapper
- the Live-Light phase is already encoded as a typed governed contract surface

### 2. The core Build-13 gate is real and broader than a simple sequel to Micro-live

Observed in:
- `src/protocols/live_light_runtime.py`
- `src/protocols/live_light_runtime_gate_support.py`

Current repo-truth gate logic includes:
- Build-12 verdict and readiness checks
- explicit 30-day Shadow gate enforcement if a state dir is provided
- rollout-temporal checks
- Micro-live planned-surface consistency checks
- live budget and order-limit checks
- Shadow engine-scope and portfolio-judgment checks
- replay/import provenance and lineage checks
- onboarding / review export / observability / halt / broker / exchange readiness checks
- operator safing request blocking
- execution-runtime projection seam carry-through
- gate-group projection for audit readability

Interpretation:
- Build 13 is already a real governed small-execution gate
- the current code surface is materially broader than a minimal
  “Micro-live stable, allow tiny live” story

### 3. Build 13 now contains the canonical typed Build-14 influence seam

Observed in:
- `src/protocols/live_light_runtime.py`
- `src/protocols/live_light_runtime_support.py`

Current repo-truth Build-14 handling includes:
- only typed `Build14InfluenceSignal` or `Build14InfluenceReport` accepted
- full typed revalidation of the contract
- correlation-id matching with the current Live-Light run
- bounded guardrails for:
  - `downgrade_confidence`
  - `review_only`
  - `soft_veto`
- explicit rejection of:
  - untyped objects
  - duck-typed impostors
  - bypass semantics
  - autonomous trading semantics

Interpretation:
- old specs that described a different or looser Build-14 integration seam are
  stale against current code
- current repo-truth Build 13 already contains the canonical additive Build-14 seam

### 4. Build 13 remains operator-visible

Observed in:
- `src/protocols/live_light_dashboard.py`

Current repo-truth includes:
- normalized `LiveLightProjection`
- dashboard section cards for:
  - run state
  - verdict
  - budget
  - execution surface
  - readiness
  - gate groups
  - manual safing
  - blocking reasons

Interpretation:
- Build 13 is already projected into the supervision surface
- it is not a hidden runtime-only gate

## Verification Evidence

### Build-13 runtime, dashboard, and promotion-gate coverage

Command:

```powershell
python -m pytest tests/test_protocols/test_live_light_runtime.py tests/test_protocols/test_live_light_dashboard.py tests/test_protocols/test_promotion_gates.py tests/test_protocols/test_promotion_gates_bs_sequential_regression.py -q --tb=short
```

Result:
- `73 passed`

### Notes on warnings

Observed warnings:
- pydantic serializer warnings in model-constructed Build-14 negative tests
- pytest cache path creation warning under `.pytest_cache`

Interpretation:
- not a Build-13 doctrine/code issue
- no audited Build-13 functional failure

## Observed Divergence

### Divergence 1 - the markdown story is narrower than the current Build-13 code surface

The simplified doctrinal story often compresses Build 13 to:
- tiny governed live execution after Micro-live
- one fail-closed gate

Current repo-truth is broader:
- typed Build-13 contracts
- explicit small-execution intent seam
- import lineage and replay provenance enforcement
- engine-scope and portfolio-judgment carry-through
- broker/exchange/execution readiness checks
- gate-group audit projection
- dashboard projection

Interpretation:
- this is not a dangerous code drift
- it is a documentation compression drift

### Divergence 2 - current Build 13 already uses the typed Build-14 additive seam, not the looser seams described in older specs

Observed in:
- `src/protocols/live_light_runtime.py`
- `src/protocols/live_light_runtime_support.py`

Current repo-truth:
- accepts only typed `Build14InfluenceSignal` / `Build14InfluenceReport`
- rejects untyped or duck-typed objects
- rejects bypass/autonomous semantics
- encodes bounded review or confidence-downgrade influence

Interpretation:
- Build 13 is already stricter and more canonical than older markdown stories
- this is a stale-markdown seam, not a broken Build-13 implementation

### Divergence 3 - public promotion-gate helpers still retain legacy LIGHT compatibility while the core Build-13 runtime rail is COMPLETE-only

Observed in:
- `src/protocols/promotion_gates.py`
- `src/protocols/contracts_promotion.py`

Current repo-truth split:
- core Build-13 input and runtime rail are `COMPLETE`-governed
- `promotion_gates.py` still retains legacy `LIGHT` compatibility in the public gate package

Interpretation:
- this does not prove broken governance
- but it means Build 13 is not a perfectly clean doctrinal `MATCH`
- compatibility edges still exist in the public gate package

## Decision

`PARTIAL`

## Why

Build 13 is clearly **implemented, typed, and green** on its audited current
surface.

What is already present:
- typed Build-13 contracts
- real Build-13 gate logic
- Shadow and Micro-live readiness enforcement
- replay/import lineage enforcement
- execution/broker/exchange readiness enforcement
- typed Build-14 additive influence seam
- gate-group and dashboard projection

So Build 13 is not `STALE_CODE`, and not broken.

But it is not `MATCH` either, for three concrete reasons:

1. the markdown story underdescribes how broad the current Build-13 surface now is
2. older specs described different Build-14 seams than the current typed repo-truth
3. public promotion-gate helpers still retain legacy `LIGHT` compatibility while the
   core Build-13 runtime governance is `COMPLETE`-only

So the correct ruling is:
- Build 13 is operationally real and healthy
- but the doctrinal narrative is narrower and cleaner than the actual current
  repo-truth surface

## Patch Target

`docs only`

### Docs target

Clarify that current repo-truth Build 13 already includes:
- typed Build-13 contracts
- explicit execution-intent seam
- import provenance and lineage guards
- Shadow / Micro-live readiness and scope enforcement
- execution / broker / exchange readiness checks
- typed additive Build-14 influence handling
- gate-group and dashboard projection

Also clarify:
- `Live-Light` is a stage, not a profile
- the core Build-13 runtime rail is `COMPLETE`-governed
- `LIGHT` compatibility still exists only at the legacy public gate layer

### No target

No Build-13 code redesign is justified by this audit.

The current Live-Light rail is already strongly governed and well tested.

## Final Verdict

Build 13 is operationally strong but doctrinally compressed.

Safe operational classification:
- `Build 13 = PARTIAL (real governed Live-Light contracts, gate logic, execution-intent seam, typed Build-14 influence handling, and dashboard projection exist and are green; markdown underdescribes the current Build-13 breadth, and legacy LIGHT compatibility helpers still survive at the public gate layer while the core runtime rail is COMPLETE-only)`
