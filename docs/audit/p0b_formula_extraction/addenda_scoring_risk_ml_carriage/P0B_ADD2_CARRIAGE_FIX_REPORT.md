# P0B ADD2 - Carriage Fix Report

## Scope
- Patch type: additive governed carriage only
- No engine signal logic changed
- No side logic changed
- No new formulas introduced
- No cockpit templates changed
- No short, leverage, or fake-flat route added

## Files modified
- `src/complete_enablers/__init__.py`
- `src/complete_enablers/ml_confidence_enabler.py`
- `src/complete_enablers/regime_detector_runtime.py`
- `src/complete_enablers/supplementary_refs_governance.py`
- `src/scoring_backbone/scoring_runtime_support.py`
- `src/risk_backbone/risk_runtime_models.py`
- `src/risk_backbone/risk_runtime_explainability.py`
- `src/risk_backbone/risk_runtime_evaluation_support.py`
- `src/engines/engine_a/engine_a_runtime.py`
- `src/engines/engine_a/engine_a_scoring_candidate_builder.py`
- `src/engines/engine_b/engine_b_runtime.py`
- `src/engines/engine_b/engine_b_runtime_support.py`
- `src/engines/engine_c/engine_c_runtime.py`
- `src/engines/engine_c/engine_c_runtime_support.py`
- `src/engines/engine_d/engine_d_runtime.py`
- `src/engines/engine_d/engine_d_runtime_support.py`
- `tests/test_complete_enablers/test_ml_confidence_enabler.py`
- `tests/test_complete_enablers/test_ml_scoring_soft_penalty_hook.py`
- `tests/test_complete_enablers/test_regime_detector_runtime.py`
- `tests/test_scoring_backbone/test_scoring_runtime.py`
- `tests/test_risk_backbone/test_risk_runtime.py`
- `tests/test_engines/test_engine_a/test_engine_a_runtime.py`
- `tests/test_engines/test_engine_b/test_engine_b_runtime.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py`
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py`

## RiskCandidate carriage status
- Engine A:
  - carried: `execution_fragility`, `market_toxicity`, `spread_regime_penalty`
  - explicit status: `risk_micro_friction_carried`
  - explicit missing reasons: `RISK_INFO_STRESS_FIELD_MISSING`, `RISK_REGIME_STATE_MISSING`
- Engine B:
  - carried: `execution_fragility`, `market_toxicity`, `spread_regime_penalty`
  - explicit status: `risk_micro_friction_carried`
  - explicit missing reasons: `RISK_INFO_STRESS_FIELD_MISSING`, `RISK_REGIME_STATE_MISSING`
- Engine C:
  - not force-mapped
  - explicit statuses: `risk_micro_friction_missing`, `not_carried_to_risk_rail`
  - explicit reasons: `RISK_MICRO_FRICTION_FIELD_MISSING`, `RISK_INFO_STRESS_FIELD_MISSING`, `RISK_REGIME_STATE_MISSING`
- Engine D:
  - not force-mapped
  - explicit statuses: `risk_micro_friction_missing`, `not_carried_to_risk_rail`
  - explicit reasons: `RISK_MICRO_FRICTION_FIELD_MISSING`, `RISK_INFO_STRESS_FIELD_MISSING`, `RISK_REGIME_STATE_MISSING`

## ScoringCandidateInput carriage status
- Engine A:
  - carried: `execution_fragility`, `market_toxicity`, `spread_regime_penalty`
  - preserved existing derived raw features
  - explicit statuses: `derived_shared_scoring`, `shared_scoring_physics_carried`, `shared_scoring_physics_partial`
  - explicit reason: `SCORING_SHARED_PHYSICS_MAPPING_NOT_PROVEN`
- Engine B:
  - carried: `execution_fragility`, `market_toxicity`, `spread_regime_penalty`
  - preserved existing derived raw features
  - explicit statuses: `derived_shared_scoring`, `shared_scoring_physics_carried`, `shared_scoring_physics_partial`
  - explicit reason: `SCORING_SHARED_PHYSICS_MAPPING_NOT_PROVEN`
- Engine C:
  - not force-mapped
  - explicit statuses: `local_math_only`, `shared_scoring_physics_partial`
  - explicit reasons:
    - `SCORING_SHARED_PHYSICS_MAPPING_NOT_PROVEN`
    - `HUMAN_DECISION_REQUIRED_FOR_C_D_SHARED_CARRIAGE`
    - `REGIME_SCORING_REINJECTION_PARTIAL`
- Engine D:
  - not force-mapped
  - explicit statuses: `local_math_only`, `shared_scoring_physics_partial`
  - explicit reasons:
    - `SCORING_SHARED_PHYSICS_MAPPING_NOT_PROVEN`
    - `HUMAN_DECISION_REQUIRED_FOR_C_D_SHARED_CARRIAGE`
    - `REGIME_SCORING_REINJECTION_PARTIAL`

## Fields not carried and why
- `participation_penalty`
  - not populated anywhere in this patch
  - reason: no proven governed source was available
- `spread_bps`
- `reference_spread_bps`
- `depth_ratio`
- `order_cancellation_rate`
- `taker_imbalance`
- `micro_vol_divergence`
  - not force-mapped into risk
  - reason: no existing engine runtime source was proven on the governed rail

## ML supplementary refs status
- `supplementary_refs` transport remains `tuple[str, ...]`
- carrier support was added to engine runtime inputs and scoring candidates
- empty refs are explicit neutral:
  - status: `ml_refs_missing_neutral`
  - reason: `ML_REFS_MISSING_NEUTRAL`
- stale artifact handling is explicit:
  - status: `ml_refs_stale`
  - reason: `ML_ARTIFACT_STALE`
- hash mismatch disables ML contribution:
  - reason: `ML_ARTIFACT_HASH_MISMATCH`
- transport declared but no usable artifact:
  - reason: `ML_REFS_NOT_AVAILABLE`
- direct override remains forbidden:
  - reason: `ML_DIRECT_OVERRIDE_FORBIDDEN`
- directional refs are rejected:
  - reason: `ML_DIRECTIONAL_REF_FORBIDDEN`

## Regime boundary status
- Allowed non-directional regime refs remain:
  - `regime_transition_risk`
  - `regime_stability_score`
  - `market_toxicity_score`
  - `expected_duration_bucket`
- Directional regime refs are rejected:
  - `REGIME_DIRECTIONAL_REF_FORBIDDEN`
- Regime carriage remains intentionally partial outside already-proven execution consumption:
  - `REGIME_SCORING_REINJECTION_PARTIAL`
  - `REGIME_RISK_REINJECTION_PARTIAL`

## Engine status
- Engine A: shared scoring carriage improved, risk carriage improved, ML refs carrier enabled, side unchanged
- Engine B: shared scoring carriage improved, risk carriage improved, ML refs carrier enabled, side unchanged
- Engine C: explicit partial status only, no forced semantic mapping
- Engine D: explicit partial status only, no forced semantic mapping

## Side / halal / spot-only safety result
- No side mutation introduced by scoring carriage
- No side mutation introduced by risk carriage
- No side mutation introduced by ML supplementary refs handling
- No short route introduced
- No leverage route introduced
- No fake-flat route introduced
- Spot-only governed rail preserved

## Tests run
- `python -c "compile(...)"` over modified source files: `PASS`
- `python -m pytest -q tests/test_complete_enablers/test_ml_confidence_enabler.py tests/test_complete_enablers/test_ml_scoring_soft_penalty_hook.py tests/test_complete_enablers/test_regime_detector_runtime.py --tb=short --disable-warnings --basetemp=tmp_pytest_add2_complete_enablers`
  - result: `21 passed`
- `python -m pytest -q tests/test_scoring_backbone/test_scoring_runtime.py tests/test_risk_backbone/test_risk_runtime.py --tb=short --disable-warnings --basetemp=tmp_pytest_add2_scoring_risk_rerun`
  - logic result: scoring/risk patch tests passed
  - environment failure: one `PermissionError` on `build/pytest-risk-runtime-daily-breaker/...`
- `python -m pytest -q tests/test_engines/test_engine_a/test_engine_a_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_d/test_engine_d_runtime.py --tb=short --disable-warnings --basetemp=tmp_pytest_add2_engines_rerun3`
  - result: `104 passed`

## Overall status
- `RiskCandidate` carriage patched where source values exist
- A/B shared scoring carriage patched where semantics are clear
- C/D unresolved mappings documented, not forced
- ML/regime ref governance enforced
- Remaining partials are explicit and audit-visible
