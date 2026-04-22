# Build 14 Repo-Truth Audit - Governed Enablers - 2026-04-22

## Scope

This note audits **Build 14** only:

- `src/interface_contracts/build14_contracts.py`
- `src/monitoring/build14_observation.py`
- `src/complete_enablers/__init__.py`
- `src/complete_enablers/contracts.py`
- `src/complete_enablers/enums.py`
- `src/complete_enablers/limited_influence.py`
- the currently exported Build-14 readers and bounded influence evaluators

It answers one question:

> Does current Build-14 code match the doctrinal expectation closely enough, or
> is there meaningful drift between the expected governed-enabler layer and the
> real implementation?

## Doctrine Claim

Current doctrinal baseline is the combination of:

- `src/manifest_registry/build_order_registry.py`
- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- the later arbitration/repo-truth notes that already rejected fake Build-14 bridge shapes

Repo-doctrine summary for Build 14:

- Build 14 is canonical **Governed Enablers**.
- It is an additive layer only.
- It must not replace canonical Builds `2` to `13`.
- It must not become a new autonomous engine.
- It must not bypass engines, risk, or portfolio.

## Repo-Truth Surface

### 1. Build 14 is governed first through shared typed contracts, not through reader-local ad hoc payloads

Observed in:
- `src/interface_contracts/build14_contracts.py`
- `src/complete_enablers/contracts.py`
- `src/complete_enablers/enums.py`

Current repo-truth canonical contracts are:
- `Build14EnablerContract`
- `Build14ObservationInput`
- `Build14EnablerSnapshot`
- `Build14InfluenceSignal`
- `Build14InfluenceReport`

Current repo-truth guardrails already enforce:
- `classification == build14_enabler`
- never override engines
- never bypass risk
- never bypass portfolio
- never trade autonomously
- `live_promotion_eligible=True` only when `hard_state=shadow_validated`

Interpretation:
- Build 14 is not a loose collection of experiment objects
- it is already a typed, guarded addendum layer

### 2. The canonical Build-14 pipeline is already the two-step observation -> influence path

Observed in:
- `src/monitoring/build14_observation.py`
- `src/complete_enablers/limited_influence.py`

Current repo-truth pipeline is:

1. derive a `Build14ObservationInput` from existing governed monitoring surfaces
   - `derive_build14_observation_from_snapshot(...)`
   - `derive_build14_observation_from_payload(...)`
2. evaluate bounded Build-14 output
   - `evaluate_build14_shadow_activation(...)`
   - `evaluate_build14_limited_influence(...)`

Interpretation:
- this is the canonical Build-14 seam today
- there is no single magic bridge object
- there is no fake multi-output family such as:
  - `MicrostructureEnablerOutput`
  - `NewsEnablerOutput`
  - `RiskMetricsEnablerOutput`

### 3. Current Build 14 already exposes real reader snapshots, but only as evidence inside the governed contract system

Observed in:
- `src/complete_enablers/__init__.py`
- reader modules re-exported there

Current repo-truth readers include:
- `build_market_toxicity_snapshot`
- `build_execution_fragility_score`
- `build_lob_deep_filter_vwa_snapshot`
- `build_order_book_imbalance_snapshot`
- `build_micro_edge_exit_governor_snapshot`
- `build_micro_edge_entry_timing_snapshot`
- `build_false_breakout_snapshot`
- `build_hurst_regime_snapshot`
- `build_competition_monitor_snapshot`

Interpretation:
- Build 14 is broader than one or two toy enrichments
- but these readers still terminate in governed `Build14EnablerSnapshot` evidence
- they do not constitute parallel engines

### 4. Shadow and post-Shadow live semantics are already distinct and bounded

Observed in:
- `src/complete_enablers/limited_influence.py`
- `src/interface_contracts/build14_contracts.py`

Current repo-truth already distinguishes:
- `SHADOW_ENABLED`
  - fully active inside Shadow comparison
  - action `SHADOW_APPLY`
  - no live promotion
- `READ_ONLY`
  - observational only
  - zero penalty
  - full budget
- `LIMITED_INFLUENCE`
  - bounded influence only
  - may downgrade confidence
  - may require review
  - may soft-veto

Interpretation:
- current Build 14 is not "always shadow only"
- but it is also not "live engine promotion"
- it is explicitly bounded and governed after Shadow

### 5. There is still no canonical cross-module facade that directly collapses payload -> report in one place

Observed in:
- `src/monitoring/build14_observation.py`
- `src/complete_enablers/limited_influence.py`
- current DAG policy already established in repo-truth notes

Interpretation:
- this is intentional repo-truth, not a missing implementation bug
- the current system preserves the two-step pipeline because `monitoring` and
  `complete_enablers` stay separated by the DAG
- so a speculative "universal Build-14 bridge" would be the wrong patch target

## Verification Evidence

### Focused Build-14 proof bundle

Command:

```powershell
python -m pytest tests/test_complete_enablers/test_contracts.py tests/test_monitoring/test_build14_observation.py -q --tb=short
```

Result:
- `26 passed`
- `1 warning`

Warning detail:
- pytest cache creation warning under `.pytest_cache`

Interpretation:
- current Build-14 contracts, reader/export surface, bounded influence evaluators,
  and observation derivation helpers are green on the audited bundle
- the warning is cache-related only, not a Build-14 functional failure

## Observed Divergence

### Divergence 1 - old Build-14 specs that described fake output families are stale against current code

Old speculative shapes such as:
- `MicrostructureEnablerOutput`
- `NewsEnablerOutput`
- `RiskMetricsEnablerOutput`

are not current repo-truth.

Current repo-truth uses:
- one observation contract
- snapshot evidence
- one bounded influence signal/report system

Interpretation:
- this is not code drift
- it is stale markdown/spec drift

### Divergence 2 - the real Build-14 architecture is a two-step pipeline, not a one-shot bridge

Current repo-truth:
- `monitoring` derives observation input
- `complete_enablers` evaluates bounded influence

Interpretation:
- any story that expects a single direct bridge object is incomplete against current code truth
- preserving the two-step shape is part of the architecture, not accidental fragmentation

### Divergence 3 - current Build 14 is already richer than "read-only experiments", but still fully bounded

Current repo-truth already supports:
- `READ_ONLY`
- `LIMITED_INFLUENCE`
- review-only / soft-veto outcomes

But it still forbids:
- engine bypass
- risk bypass
- portfolio bypass
- autonomous trading

Interpretation:
- the meaningful doctrinal line is not "Build 14 never influences anything"
- it is "Build 14 may influence only in a bounded, governed way"

## Decision

`STALE_MD`

## Why

Build 14 current code is coherent, typed, and green on its audited surface.

What is already present:
- canonical Build-14 contracts
- canonical observation derivation seam
- canonical bounded influence seam
- real reader snapshot family
- explicit Shadow vs post-Shadow bounded live semantics
- hard guardrails against bypass and autonomy

So current Build 14 is not `STALE_CODE`, and not broken.

The real drift is elsewhere:

1. older markdown/spec stories described fake output families that do not match the code
2. older bridge narratives described the wrong architecture shape
3. older summaries often understate the fact that bounded post-Shadow influence is already part of repo-truth

So the correct ruling is:
- current Build 14 code is the right source of truth
- the stale layer is the older markdown/spec narrative around Build 14 shape

## Patch Target

`docs only`
