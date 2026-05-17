# Wave 5 Scoring Formula Source Evidence

## Evidence 1: Raw score construction

Source file:
- `src/scoring_backbone/raw_score_builder/raw_score_calculator.py`

Function:
- `calculate_raw_score`

Exact code excerpt:
```python
base_raw_score = sum(contributions.values())
raw_score = base_raw_score * normalized_multiplier + normalized_add
if normalized_cap is not None:
    raw_score = min(raw_score, normalized_cap)
```

Plain-text formula:
- `base_raw_score = Σ(weight_i * feature_i)`
- `raw_score = base_raw_score * raw_score_multiplier + raw_score_add`
- `raw_score = min(raw_score, raw_score_cap)` when a cap exists

Input variables:
- `feature_values`
- `feature_weights`
- `raw_score_multiplier`
- `raw_score_add`
- `raw_score_cap`

Output variable:
- `RawScoreResult.raw_score`

Units:
- score, engine-local numeric scale

Denominator:
- none

Scope:
- per-candidate

Semantics:
- expected / governed runtime scoring value
- not realized profitability

Missing-field behavior:
- missing weight means no contribution
- non-finite multiplier/add/cap raise
- blank `scoring_version` raises

Downstream consumers:
- `src/scoring_backbone/scoring_runtime.py`
- engine runtime scoring states before ranking

Tests:
- `tests/test_scoring_backbone/test_raw_score_builder.py`
- assertions cover weighted contributions, cap behavior, ignored missing weights, reproducibility, and blank-version rejection

False-green risk:
- low by itself; risk appears only if downstream consumers over-read score as economics

Small-capital risk:
- none directly

Side/halal risk:
- none directly; no side field is created here

Classifications:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `CONSUMER_FOUND`

## Evidence 2: Additive score penalties

Source file:
- `src/scoring_backbone/penalty_aggregator/score_penalty_builder.py`

Function:
- `build_score_penalty`

Exact code excerpt:
```python
total = sum(p.value for p in penalties)
adjusted = raw_score - total
```

Plain-text formula:
- `total_penalty = Σ penalty_value`
- `adjusted_score = raw_score - total_penalty`

Input variables:
- `raw_score`
- `penalties`

Output variable:
- `ScorePenaltyResult.adjusted_score`

Units:
- score

Denominator:
- none

Scope:
- per-candidate

Semantics:
- governed runtime score reduction

Missing-field behavior:
- empty penalties remain valid and imply zero penalty
- invalid penalty IDs are validated against the registry

Downstream consumers:
- `src/scoring_backbone/scoring_runtime.py`

Tests:
- `tests/test_scoring_backbone/test_penalty_aggregator.py`

Classifications:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`

## Evidence 3: Break-even / CE / EV gate

Source file:
- `src/scoring_backbone/break_even_filter.py`

Function:
- `evaluate_break_even`

Exact code excerpt:
```python
expected_break_even = expected_cost + delta_safe
ev_net = candidate_size * (expected_gain - expected_cost)

edge_cleared = expected_gain > expected_break_even
if not resolved_config.strict_break_even:
    edge_cleared = expected_gain >= expected_break_even

ce_cleared = True
if expected_ce is not None and ce_min is not None:
    ce_cleared = expected_ce >= ce_min

ev_cleared = ev_net > resolved_config.min_ev_net
allowed = edge_cleared and ce_cleared and ev_cleared
```

Reason-code excerpt:
```python
if not edge_cleared:
    reason_code = "BREAK_EVEN_NOT_CLEARED"
elif not ce_cleared:
    reason_code = "CE_BELOW_MINIMUM"
elif not ev_cleared:
    reason_code = "EV_NET_BELOW_FLOOR"
```

Plain-text formula:
- `expected_break_even = expected_cost + delta_safe`
- `ev_net = candidate_size * (expected_gain - expected_cost)`
- candidate allowed only if edge, CE, and EV all clear

Input variables:
- `expected_gain`
- `expected_cost`
- `delta_safe`
- `expected_ce`
- `ce_min`
- `candidate_size`
- `min_ev_net`

Output variable:
- `BreakEvenFilterDecision.allowed`

Units:
- `expected_gain`, `expected_cost`, `expected_ce`: fraction-like economics rail
- `ev_net`: quote-currency EV rail if `candidate_size` is quote notional, else sizing-dependent scalar

Denominator:
- CE denominator is upstream-defined; this seam only compares provided `expected_ce`

Scope:
- per-candidate

Semantics:
- expected, not realized

Missing-field behavior:
- CE gate only active if both `expected_ce` and `ce_min` are provided
- invalid finite/non-negative checks fail closed with exceptions

Downstream consumers:
- shared scoring / engine-local economics checks

Tests:
- `tests/test_scoring_backbone/test_break_even_filter.py`

False-green risk:
- `EXPECTED_REALIZED_AMBIGUITY` if downstream UI markets this as realized profitability

Classifications:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `EXPECTED_REALIZED_AMBIGUITY`

## Evidence 4: Fee-aware edge threshold

Source file:
- `src/execution_backbone/fee_aware_edge_gate.py`

Function:
- `evaluate_fee_aware_edge`

Exact code excerpt:
```python
expected_cost_bps = expected_cost * 10_000.0
threshold_bps = max(
    thresholds.edge_multiplier * expected_cost_bps,
    thresholds.min_absolute_edge_bps,
)
allowed = expected_edge_bps >= threshold_bps
```

Reason-code excerpt:
```python
reason_code="" if allowed else "EDGE_INSUFFICIENT_VS_FEES"
```

Plain-text formula:
- convert expected cost fraction to bps
- threshold is `max(edge_multiplier * expected_cost_bps, min_absolute_edge_bps)`
- allow only if expected edge in bps clears that threshold

Input variables:
- `expected_edge_bps`
- `expected_cost`
- config thresholds

Output variable:
- `FeeAwareEdgeDecision.allowed`

Units:
- `expected_edge_bps`, `expected_cost_bps`, `threshold_bps`: bps

Denominator:
- none

Scope:
- per-candidate / per-order gate

Semantics:
- expected economics gate

Missing-field behavior:
- invalid non-finite values raise

Downstream consumers:
- `src/execution_backbone/execution_runtime_support.py`
- gatekeeper authorization rail

Tests:
- `tests/test_scoring_backbone/test_fee_aware_edge_gate.py`

Classifications:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `CONSUMER_FOUND`

## Evidence 5: ML penalty / confidence is non-sovereign

Source file:
- `src/complete_enablers/ml_scoring_soft_penalty_hook.py`
- `src/complete_enablers/ml_confidence_enabler.py`

Functions:
- `MlScoringSoftPenaltyHook.__call__`
- `MlConfidenceEnabler.apply_to_engine_score`

Exact code excerpt:
```python
if artifact is None:
    return MlConfidenceSignal(
        ml_confidence=0.5,
        ml_direction=MlDirection.FLAT,
        artifact_status=MlArtifactStatus.MISSING,
        reason_codes=("ML_ARTIFACT_MISSING",),
    )
```

```python
elif not allow_direct_ml_confidence_override:
    signal = MlConfidenceSignal(
        ml_confidence=0.5,
        ml_direction=MlDirection.FLAT,
        artifact_status=MlArtifactStatus.INVALID,
        artifact_id=None if artifact is None else artifact.artifact_hash,
        reason_codes=("ML_DIRECT_OVERRIDE_FORBIDDEN",),
    )
```

Plain-text behavior:
- missing or stale ML artifacts degrade to neutral confidence
- direct ML override is forbidden unless explicitly allowed
- ML can reduce or modulate scoring confidence, but it does not create side or a trade by itself

Inputs:
- `artifact`
- `supplementary_refs`
- `ml_confidence`
- `engine_side`

Outputs:
- `MlConfidenceSignal`
- score-fusion / penalty outcome

Units:
- confidence score `0..1`
- multiplier delta on score in the soft-penalty hook

Scope:
- per-candidate

Side/halal risk:
- protected; direct override is forbidden

Tests:
- `tests/test_complete_enablers/test_ml_confidence_enabler.py`
- `tests/test_scoring_backbone/test_scoring_runtime.py`

Classifications:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `CONSUMER_FOUND`

## Evidence 6: Engine C / D shared scoring remains partial-by-design

Source file:
- `src/engines/engine_d/engine_d_runtime_support.py`

Function:
- `build_scoring_candidate`

Exact code excerpt:
```python
carriage_statuses=("local_math_only", "shared_scoring_physics_partial"),
carriage_reason_codes=(
    "SCORING_SHARED_PHYSICS_MAPPING_NOT_PROVEN",
    "HUMAN_DECISION_REQUIRED_FOR_C_D_SHARED_CARRIAGE",
    "REGIME_SCORING_REINJECTION_PARTIAL",
),
```

Plain-text meaning:
- Engine D scoring candidate intentionally carries partial shared-physics status.
- Engine C mirrors the same doctrine in its own runtime-support rail and tests.

Tests:
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py`
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py`
- `tests/test_scoring_backbone/test_scoring_runtime.py`

Classifications:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `HUMAN_OR_EXTERNAL_AUDIT_REQUIRED`

External-audit questions:
- Should any future scoring promotion consume Wave 3 cost-completeness statuses directly rather than only in cockpit display logic?
- Is current score scale sufficiently comparable across engines, or intentionally engine-local?
- Should Engine C and Engine D ever move beyond partial shared-physics carriage, and under what evidence threshold?

