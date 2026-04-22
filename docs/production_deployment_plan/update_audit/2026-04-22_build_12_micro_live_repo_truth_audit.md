# Build 12 Repo-Truth Audit - Micro-live - 2026-04-22

## Scope

This note audits **Build 12** only:

- `protocols.micro_live_runtime`
- `protocols.micro_live_runtime_support`
- `protocols.contracts_promotion` on the `MicroLive*` seam
- `protocols.micro_live_dashboard`
- the current Build-12 promotion-gate exposure

It answers one question:

> Does current Build-12 code match the doctrinal expectation closely enough, or
> is there meaningful drift between the expected Micro-live stage and the real
> implementation?

## Doctrine Claim

Current doctrinal baseline is the combination of:

- `src/manifest_registry/build_order_registry.py`
- `docs/production_deployment_plan/12_LOCAL_LAB_VS_VPS_SEPARATION.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `docs/production_deployment_plan/update_audit/2026-04-21_stage_naming_vs_profile_naming.md`

Repo-doctrine summary for Build 12:

- Build 12 is the governed **Micro-live** stage.
- It must preserve the official promotion ladder:
  - Replay -> Shadow -> Micro-live -> Live-Light
- It is a **stage name**, not a deployment profile.
- It must remain `COMPLETE`-governed on the real runtime rail.
- It must not auto-promote to live.
- It must stay typed, auditable, and operator-visible.

## Repo-Truth Surface

### 1. Build 12 contracts are real and strongly governed

Observed in:
- `src/protocols/contracts_promotion.py`

Current repo-truth Build-12 contracts include:
- `MicroLiveInput`
- `MicroLiveDecision`
- `MicroLiveExecutionPlan`
- `MicroLiveRunSummary`

Observed governance guards include:
- `profile=COMPLETE` enforced at `MicroLiveInput`
- `runtime_mode=MICRO_LIVE` enforced
- `backtest_profile` explicitly forbidden
- local/VPS profile forks explicitly forbidden
- automatic live promotion explicitly forbidden

Interpretation:
- Build 12 is not a loose campaign label
- the Micro-live phase is already encoded as a typed governed contract surface

### 2. The core Build-12 gate is real and broader than a simple stage hop

Observed in:
- `src/protocols/micro_live_runtime.py`
- `src/protocols/micro_live_runtime_support.py`

Current repo-truth gate logic includes:
- Build-11 Shadow completion and verdict checks
- 30-day Shadow temporal validation
- engine-scope filtering to SHADOW_VALIDATED and PROMOTABLE engines
- dormant / shadow-only / rewrite-required exclusions
- replay import provenance and lineage checks
- replay conflict-contract checks
- probe-surface and budget checks
- onboarding / review export / observability / halt readiness checks
- operator safing request blocking
- execution-runtime projection seam checks

Interpretation:
- Build 12 is already a real governed capital-probe gate
- the current code surface is materially broader than a minimal
  “Shadow passed, open tiny capital” story

### 3. Build 12 is explicitly COMPLETE-governed on the canonical runtime rail

Observed in:
- `src/protocols/contracts_promotion.py`
- `src/protocols/micro_live_runtime_support.py`

Current repo-truth requires:
- source payload `profile=COMPLETE`
- source payload `runtime_mode=SHADOW`
- import source profile `complete`
- no profile fork

Interpretation:
- the doctrinal distinction between
  - profiles: `LIGHT`, `COMPLETE`
  - stages: `Shadow`, `Micro-live`, `Live-Light`, `Live-Complete`
  is now correctly reflected in the core Build-12 runtime rail

### 4. Build 12 remains operator-visible

Observed in:
- `src/protocols/micro_live_dashboard.py`

Current repo-truth includes:
- normalized `MicroLiveProjection`
- dashboard section cards for:
  - run state
  - verdict
  - budget
  - probe surface
  - guardrails
  - manual safing
  - blocking reasons

Interpretation:
- Build 12 is already projected into the supervision surface
- it is not a hidden runtime-only gate

## Verification Evidence

### Build-12 runtime, dashboard, and promotion-gate regression coverage

Command:

```powershell
python -m pytest tests/test_protocols/test_micro_live_runtime.py tests/test_protocols/test_micro_live_dashboard.py tests/test_protocols/test_promotion_gates.py tests/test_protocols/test_bs37_check_all_gates_includes_micro_live_regression.py -q --tb=short
```

Result:
- `65 passed`

### Notes on warnings

Observed warning:
- pytest cache path creation warning under `.pytest_cache`

Interpretation:
- not a Build-12 doctrine/code issue
- no audited Build-12 functional failure

## Observed Divergence

### Divergence 1 - the markdown story is narrower than the current Build-12 code surface

The simplified doctrinal story often compresses Build 12 to:
- first tiny real-capital stage after Shadow
- promotion gate only

Current repo-truth is broader:
- typed Build-12 contracts
- import lineage and replay provenance enforcement
- engine-scope judgment enforcement
- portfolio-judgment carry-through
- observability / halt / onboarding gating
- execution-runtime projection seam
- operator safing projection
- dashboard projection

Interpretation:
- this is not a dangerous code drift
- it is a documentation compression drift

### Divergence 2 - the core Build-12 rail is COMPLETE-only, but legacy LIGHT compatibility still exists in public promotion-gate helpers

Observed in:
- `src/protocols/contracts_promotion.py`
- `src/protocols/micro_live_runtime_support.py`
- `src/protocols/promotion_gates.py`

Current repo-truth split:
- core Build-12 input and runtime rail are `COMPLETE`-governed
- `promotion_gates.py` still exposes `check_light_to_micro_live(...)` for legacy callers/tests

Interpretation:
- this does not prove broken governance
- but it means Build 12 is not a perfectly clean doctrinal `MATCH`
- compatibility edges still exist in the public gate package

### Divergence 3 - stage/profile drift has been doctrinally fixed, but older docs/tests were previously ambiguous

Observed in:
- `docs/production_deployment_plan/update_audit/2026-04-21_stage_naming_vs_profile_naming.md`
- `src/manifest_registry/build_order_registry.py`

Current repo-truth:
- Build 12 stage name is `Micro-live`
- Build 12 runtime rail is `COMPLETE`-governed

Interpretation:
- the code is now coherent with the clarified doctrine
- but Build 12 must still be classified `PARTIAL` because this clarification was
  needed after prior drift, and compatibility helpers still keep older semantics
  alive at the gate layer

## Decision

`PARTIAL`

## Why

Build 12 is clearly **implemented, typed, and green** on its audited current
surface.

What is already present:
- typed Build-12 contracts
- real Build-12 gate logic
- Shadow evidence and scope enforcement
- replay/import lineage enforcement
- operational-readiness enforcement
- dashboard projection

So Build 12 is not `STALE_CODE`, and not broken.

But it is not `MATCH` either, for three concrete reasons:

1. the markdown story underdescribes how broad the current Build-12 surface now is
2. the doctrinal stage/profile distinction had to be clarified explicitly after drift
3. public promotion-gate helpers still retain `LIGHT` compatibility while the
   core Build-12 runtime governance is `COMPLETE`-only

So the correct ruling is:
- Build 12 is operationally real and healthy
- but the doctrinal narrative is narrower and cleaner than the actual current
  repo-truth surface

## Patch Target

`docs only`

### Docs target

Clarify that current repo-truth Build 12 already includes:
- typed Build-12 contracts
- import provenance and lineage guards
- engine-scope and portfolio-judgment propagation
- observability / halt / onboarding gating
- execution-runtime projection seam
- dashboard projection

Also clarify:
- `Micro-live` is a stage, not a profile
- the core Build-12 runtime rail is `COMPLETE`-governed
- `LIGHT -> micro_live` compatibility helpers still exist only at the legacy gate layer

### No target

No Build-12 code redesign is justified by this audit.

The current Micro-live rail is already strongly governed and well tested.

## Final Verdict

Build 12 is operationally strong but doctrinally compressed.

Safe operational classification:
- `Build 12 = PARTIAL (real governed Micro-live contracts, gate logic, readiness enforcement, and dashboard projection exist and are green; markdown underdescribes the current Build-12 breadth, and legacy LIGHT compatibility helpers still survive at the public gate layer while the core runtime rail is COMPLETE-only)`
