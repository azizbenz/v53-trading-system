# Build-5 Scoring Backbone Evidence

Date: `2026-05-01`

## Scope

Primary source rails:

- `src/scoring_backbone/scoring_runtime.py`
- `src/scoring_backbone/scoring_runtime_support.py`
- `src/scoring_backbone/fee_aware_edge_gate.py`
- `src/scoring_backbone/raw_score_builder/*`
- `src/scoring_backbone/hard_block_gate/*`
- `src/scoring_backbone/penalty_aggregator/*`
- `src/scoring_backbone/ranking_router/*`
- downstream-only enabler reference: `src/complete_enablers/ml_scoring_soft_penalty_hook.py`

## Proved Capabilities

### `ScoringCandidateInput` exists

Evidence:

- `scoring_runtime_support.py`

### Base-score path exists

Evidence:

- `raw_score_builder/raw_score_calculator.py`
- `raw_score_builder/feature_selector.py`

### Soft / hard / rank pipeline exists

Evidence:

- `scoring_runtime.py`
- `penalty_aggregator/*`
- `hard_block_gate/*`
- `ranking_router/*`

### ML non-positive modulation is compatible with scoring

Status: `PROVEN`

Reason:

- current scoring carriage and test coverage assume ML may reduce score or leave it unchanged, not increase it

### Cost partial status is carried

Status: `PROVEN`

Observed fields:

- `cost_model_completeness_status`
- `fee_source_status`
- `impact_source_status`
- `fill_realism_status`
- `realized_slippage_status`
- `scoring_risk_cost_completeness_status`

### `supplementary_refs` are carried

Status: `PROVEN`

Observed in:

- `ScoringCandidateInput`
- carriage audit surface resolution

### Reason codes are carried

Status: `PROVEN`

Observed fields:

- `carriage_reason_codes`
- `artifact_hook_reason_codes`
- `cost_readiness_reason_codes`
- scoring explainability `reason_codes`

### C/D partial-by-design is respected

Status: `PROVEN`

Observed fields:

- `shared_physics_mapping_status`
- `engine_role`

Current doctrine:

- C/D local math remains allowed
- forced A/B-style shared mapping is not required for core Build-5 coherence

## Semantic Safety Checks

### Scoring does not create side

Status: `PROVEN`

### ML cannot increase score

Status: `PROVEN`

### ML cannot create trade

Status: `PROVEN`

### Expected CE is not realized PnL

Status: `PROVEN`

### Partial cost model cannot green readiness

Status: `PROVEN`

Observed readiness:

- `SCORING_RISK_COST_COMPLETENESS_PARTIAL`

### Missing `supplementary_refs` are neutral

Status: `PROVEN`

Observed status:

- `ML_NEUTRAL_NO_REFS`

### Directional refs are forbidden

Status: `PROVEN`

Observed status:

- `ML_DIRECTIONAL_REF_FORBIDDEN`

### No forced C/D mapping into A/B shared physics

Status: `PROVEN`

## Test Evidence

Relevant suites found:

- `tests/test_scoring_backbone/test_scoring_runtime.py`
- `tests/test_scoring_backbone/test_scoring_integration.py`
- `tests/test_scoring_backbone/test_raw_score_builder.py`
- `tests/test_scoring_backbone/test_penalty_aggregator.py`
- `tests/test_scoring_backbone/test_hard_block_gate.py`
- `tests/test_scoring_backbone/test_ranking_router.py`
- `tests/test_scoring_backbone/test_fee_aware_edge_gate.py`
- threshold tests for A/B/C/D score rails

Executed in the combined Build-2..5 band:

- `912 passed`

## Remaining Gaps

- scoring still depends on explicit cost completeness to avoid false-green economics
- expected CE remains expected-only
- engine-specific executed-only profitability and true drawdown remain absent
- later cockpit/operator surfaces still need to keep doctrinal caveats visible

## Verdict

Build-5 verdict: `PARTIAL`

Reason:

- the scoring backbone is implemented, typed, and heavily tested
- promotion-grade economics and some operator-facing completeness still depend on later measured rails
