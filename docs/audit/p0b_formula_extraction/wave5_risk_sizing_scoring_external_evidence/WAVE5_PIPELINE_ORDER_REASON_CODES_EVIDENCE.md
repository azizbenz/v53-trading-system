# Wave 5 Pipeline Order / Reason Codes Evidence

## Evidence 1: Shared scoring order

Source file:
- `src/scoring_backbone/scoring_runtime.py`

Function:
- `ScoringRuntime.run_round`

Exact code excerpt:
```python
timestamp = require_runtime_timestamp(now, context="ScoringRuntime.run_round")
```

```python
candidate_pool = build_candidate_pool(tuple(ranking_candidates), blocked_keys=frozenset(blocked_keys))
portfolio_results, portfolio_rejected_keys = self._evaluate_portfolio_compatibility(
    candidate_pool,
    candidate_index=candidate_index,
    portfolio=portfolio,
)
selection_result = self._resolve_selection_result(
    candidate_pool,
    candidate_index=candidate_index,
    portfolio_rejected_keys=portfolio_rejected_keys,
    max_selections=max_selections,
    timestamp=timestamp,
)
```

Implemented order:
1. timestamp requirement
2. candidate evaluation and hard blockers
3. ranking candidate pool
4. portfolio compatibility
5. ranking resolution / selection
6. audit reconciliation

Meaning:
- hard-blocked trades never enter ranking
- ranking rejection is separate from hard block

Tests:
- `tests/test_scoring_backbone/test_scoring_runtime.py`
- `tests/test_scoring_backbone/test_scoring_integration.py`

## Evidence 2: Portfolio order

Source file:
- `src/portfolio_minimal/portfolio_orchestrator.py`

Exact code excerpt:
```python
Pipeline:
1. candidate_pool_builder  → filter positive score + size
2. conflict_checker         → deduplicate pairs by ranking_score
3. comparative_ranker       → rank by composite R_i
4. selection_resolver       → select eligible (fail-closed cluster mapping)
5. base_size_builder        → base size from profile
6. score_size_mapper        → tier + score modulation
7. portfolio_cap_applier    → apply gross/cluster/loss/beta caps
8. phantom_trade_guard      → sterilize non-viable allocations
9. allocation_reporter      → final report (viable + phantoms separated)
```

Meaning:
- the selector does not reject a trade for being too large
- sizing and caps happen after selection
- phantom sterilization is explicit, not hidden

Tests:
- `tests/test_portfolio_minimal/test_portfolio_orchestrator_minimal.py`

## Evidence 3: Candidate-pool reason codes

Source file:
- `src/portfolio_minimal/opportunity_selector/candidate_pool_builder.py`

Exact code excerpt:
```python
if candidate.penalized_score <= 0.0:
```

```python
if candidate.candidate_size <= 0.0:
```

```python
reason=CandidatePoolRejectReason.SIGNAL_EXPIRED
detail="emitted_at not set — signal age unknown, rejected while expiry checking is active"
```

Meaning:
- non-positive score, non-positive size, and stale / unknown-age signals are rejected explicitly with audits

Tests:
- `tests/test_portfolio_minimal/test_opportunity_selector_minimal.py`

## Evidence 4: Engine runtime order

Source files:
- `src/engines/engine_a/engine_a_runtime.py`
- `src/engines/engine_c/engine_c_runtime.py`
- `src/engines/engine_d/engine_d_runtime.py`

Observed order:
- engine-local run
- `NO_TRADE` if no emit
- scoring runtime
- hard block
- ranking rejection
- risk evaluation
- accepted output or refusal finalization

Meaning:
- risk sees scoring output
- execution is not run from engine runtime
- refusal records are built and persisted

Tests:
- `tests/test_engines/test_engine_c/test_engine_c_runtime_downstream.py`
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py`

## Evidence 5: Gatekeeper and execution order

Source files:
- `src/execution_backbone/gatekeeper/gatekeeper.py`
- `src/execution_backbone/execution_runtime.py`

Observed order:
- spread guard
- order type
- fee-aware edge gate
- sharia
- rate limit
- execution guard
- price limit
- venue normalization / venue constraints
- execution no-trade filter

Execution refusal excerpt:
```python
if isinstance(authorization, ExecutionRefusal):
    self._decision_reporter.record_no_trade(authorization.no_trade, timestamp=now)
    self._log_gatekeeper_refusal(authorization, opportunity, now)
    self._record_runtime_refusal(
        refusal=authorization,
        opportunity=opportunity,
```

```python
status = ExecutionSubmissionStatus.BLOCKED if authorization.disposition == ExecutionGateRefusalDisposition.BLOCKED else ExecutionSubmissionStatus.NO_TRADE
```

Meaning:
- blocked and no-trade outcomes are recorded honestly
- no fake flat order is created

Tests:
- execution-backbone tests in the requested suite

Classifications:
- `EVIDENCE_EXTRACTED`
- `CONSUMER_FOUND`
- `TEST_COVERED`

External-audit questions:
- Should risk runtime consume cost-completeness statuses before a candidate reaches the execution gate?
- Is the current refusal taxonomy sufficient for future capital-ladder blocked-trade accounting?

