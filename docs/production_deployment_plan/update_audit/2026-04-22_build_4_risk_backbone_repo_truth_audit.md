# Build 4 Repo-Truth Audit - Risk Backbone - 2026-04-22

## Scope

This note audits **Build 4** only:

- `risk_backbone.risk_runtime*`
- current gross / loss / beta / cluster guards
- current daily PnL breaker, info-stress, and regime-lite entry surfaces
- the engine-runtime risk integration seams currently calling Build 4

It answers one question:

> Does current Build-4 code match the doctrinal expectation closely enough, or
> is there meaningful drift between the expected Risk Backbone and the real
> implementation?

## Doctrine Claim

Current doctrinal baseline is the combination of:

- `src/manifest_registry/build_order_registry.py`
- `docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`

Repo-doctrine summary for Build 4:

- Build 4 is the governed **Risk Backbone** stage.
- It must own the risk guard surface before later scoring/engine/runtime layers rely on it.
- It must cover:
  - exposure / gross limits
  - loss budgeting
  - correlation / cluster pressure
  - BTC-factor / beta pressure
- It must remain typed, auditable, and fail-closed.
- Later docs 19/20 also describe planned Phase-4 add-ons such as:
  - `regime_change_detector`
  - `tail_risk_meter`
  - `regime_shift_watcher`

## Repo-Truth Surface

### 1. Build 4 is a real stateful runtime, not just a few static guards

Observed in:
- `src/risk_backbone/risk_runtime.py`
- `src/risk_backbone/risk_runtime_runtime.py`
- `src/risk_backbone/risk_runtime_evaluation_support.py`
- `src/risk_backbone/risk_runtime_models.py`

Current repo-truth Build-4 runtime includes:
- `RiskRuntime`
- typed `RiskCandidate`, `RiskEvaluation`, `RiskLimits`
- stateful portfolio snapshot management
- position register / release logic
- explicit `now`-based evaluation
- structured explainability and stable reason codes

Interpretation:
- Build 4 is not a loose helper package
- it is already a stateful governed runtime rail

### 2. The primary guard chain is real and broad

Observed in:
- `src/risk_backbone/risk_runtime_evaluation_support.py`

Current repo-truth guard chain includes:
- gross-cap guard
- loss-cap guard
- beta-cap guard with explicit beta-mapping freshness checks
- cluster-cap guard
- drawdown guard
- daily PnL precheck hook
- regime precheck hook
- info-stress precheck hook
- micro-friction precheck hook
- severe execution-pressure reduction logic

Interpretation:
- current Build 4 is broader than the short build-order description
- it already includes typed hook seams and explainability, not only hard caps

### 3. Build 4 already exposes additive operator/runtime risk surfaces

Observed in:
- `src/risk_backbone/__init__.py`
- `src/risk_backbone/daily_pnl_breaker_entry_gate.py`
- `src/risk_backbone/info_stress_monitor.py`
- `src/risk_backbone/regime_lite_entry_gate.py`
- `src/risk_backbone/regime_lite_safing.py`
- `src/risk_backbone/risk_runtime_drawdown_calibration.py`

Current repo-truth also includes:
- typed daily PnL breaker entry gate
- typed info-stress monitor and entry gate
- regime-lite entry gating and safing recommendation
- drawdown calibration seam

Interpretation:
- Build 4 is already connected to the operator/runtime governance layer
- it is not limited to raw caps only

### 4. Engines already depend on Build 4 on the hot path

Observed in:
- `src/engines/engine_a/engine_a_runtime.py`
- `src/engines/engine_b/engine_b_runtime.py`
- `src/engines/engine_c/engine_c_runtime.py`
- `src/engines/engine_d/engine_d_runtime.py`

Current repo-truth:
- engines instantiate or receive `RiskRuntime`
- engines call `evaluate_candidate(...)`
- risk results map into runtime statuses such as:
  - risk rejected
  - risk reduced
  - risk observe-only

Interpretation:
- Build 4 is not theoretical
- it is already part of the real per-signal hot path for the engines

## Verification Evidence

### Build-4 runtime, additive gates, and engine-runtime integration

Command:

```powershell
python -m pytest tests/test_risk_backbone/test_risk_runtime.py tests/test_risk_backbone/test_risk_integration.py tests/test_risk_backbone/test_daily_pnl_breaker_entry_gate.py tests/test_risk_backbone/test_info_stress_monitor.py tests/test_risk_backbone/test_regime_lite_entry_gate.py tests/test_risk_backbone/test_regime_lite_safing.py tests/test_engines/test_engine_a/test_engine_a_runtime_downstream.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime_downstream.py tests/test_engines/test_engine_d/test_engine_d_runtime.py -q --tb=short
```

Result:
- `121 passed`

### Notes on local sandbox behavior

Observed once during the first run:
- three tests failed under sandbox because their fixtures could not create
  `build/...` temporary directories

Rerun outside the sandbox:
- full command passed with `121 passed`

Interpretation:
- not a Build-4 doctrine/code issue
- no audited Build-4 functional failure

## Observed Divergence

### Divergence 1 - the markdown story is narrower than the current Build-4 code surface

The simplified doctrinal story often compresses Build 4 to:
- risk budgets
- exposure
- correlation
- BTC factor

Current repo-truth is broader:
- stateful `RiskRuntime`
- typed explainability and stable reason details
- explicit timestamp discipline
- daily PnL breaker precheck
- info-stress precheck
- regime precheck
- micro-friction precheck
- execution-pressure reduction path
- regime-lite entry/safing surfaces

Interpretation:
- this is not dangerous code drift
- it is a documentation compression drift

### Divergence 2 - some later docs 19/20 Phase-4 risk add-ons are still ahead of current repo-truth

Observed in docs:
- `regime_change_detector`
- `tail_risk_meter`
- `regime_shift_watcher`

Observed in current code:
- those packages are not present under `src/risk_backbone/`

Interpretation:
- current Build 4 is real and healthy
- but some later markdown risk expansions remain planned, not current repo-truth

### Divergence 3 - Build 4 code is strongly typed and integrated, but the build-order description remains too compressed

Observed in:
- `src/manifest_registry/build_order_registry.py`

Current build-order description:
- `Budgets risque, exposition, correlation, facteur BTC`

Current repo-truth is broader:
- stateful runtime
- explainability
- hookable prechecks
- calibration seam
- engine hot-path integration

Interpretation:
- the current registry description is directionally correct
- but operationally underdescribes the real Build-4 seam

## Decision

`PARTIAL`

## Why

Build 4 is clearly **implemented, typed, and green** on its audited current
surface.

What is already present:
- real `RiskRuntime`
- typed risk models and explainability
- gross / loss / beta / cluster / drawdown evaluation
- daily PnL, info-stress, regime, and micro-friction precheck seams
- regime-lite entry/safing surfaces
- drawdown calibration seam
- engine-runtime hot-path integration

So Build 4 is not `STALE_CODE`, and not broken.

But it is not `MATCH` either, for three concrete reasons:

1. the markdown story underdescribes how broad the current Build-4 surface now is
2. later docs 19/20 describe additional risk modules that are still planned rather than current repo-truth
3. the build-order description is directionally correct but operationally too compressed for the current implementation

So the correct ruling is:
- Build 4 is operationally real and healthy
- but the doctrinal narrative is narrower in some places and ahead of code in others

## Patch Target

`docs only`

### Docs target

Clarify that current repo-truth Build 4 already includes:
- stateful `RiskRuntime`
- typed explainability and stable reason-code emission
- daily PnL / info-stress / regime / micro-friction precheck seams
- regime-lite entry and safing helpers
- engine hot-path integration

Also clarify:
- `regime_change_detector`
- `tail_risk_meter`
- `regime_shift_watcher`

remain later planned enrichments, not baseline current Build-4 repo-truth.

### No target

No Build-4 code redesign is justified by this audit.

The current risk rail is already strongly governed and well tested.

## Final Verdict

Build 4 is operationally strong but doctrinally mixed.

Safe operational classification:
- `Build 4 = PARTIAL (real stateful RiskRuntime, typed explainability, additive precheck seams, and engine hot-path integration exist and are green; markdown underdescribes the current Build-4 breadth, while some later doc 19/20 risk add-ons remain planned rather than current repo-truth)`
