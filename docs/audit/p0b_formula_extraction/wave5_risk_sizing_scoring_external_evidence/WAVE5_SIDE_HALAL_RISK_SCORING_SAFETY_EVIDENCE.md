# Wave 5 Side / Halal / Risk-Scoring Safety Evidence

## Evidence 1: Risk candidate defaults to buy-side

Source file:
- `src/risk_backbone/risk_runtime_models.py`

Exact code excerpt:
```python
side: str = "buy"
```

Meaning:
- the public risk-candidate contract does not create shorting logic

## Evidence 2: Engine C runtime preserves BUY side

Source tests:
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime_downstream.py`

Assertion evidence:
```python
assert result.signal_candidate.side == Side.BUY
```

Also proven:
- hard-blocked and rejected-ranking downstream outcomes still preserve `Side.BUY`

## Evidence 3: Engine D runtime preserves BUY side

Source tests:
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py`

Assertion evidence:
```python
assert result.signal_candidate.side == Side.BUY
```

Also proven:
- forecast signal candidate stays `Side.BUY`
- first-episode linkage seams operate on `Side.BUY` history

## Evidence 4: ML cannot override side

Source test:
- `tests/test_complete_enablers/test_ml_confidence_enabler.py`

Assertion evidence:
```python
assert result.signal.ml_direction.value == "long"
assert result.engine_side == Side.SELL
```

Meaning:
- even when ML direction points one way, the engine side stays what the engine produced

Additional assertion:
```python
assert result.signal.reason_codes == ("ML_DIRECT_OVERRIDE_FORBIDDEN",)
```

## Evidence 5: NO_TRADE is not translated into a fake flat order

Source file:
- `src/execution_backbone/execution_runtime.py`

Exact code excerpt:
```python
if decision.action == HybridRoutingAction.NO_TRADE:
    return ExecutionSubmission(
        status=ExecutionSubmissionStatus.NO_TRADE,
        no_trade=NoTradeDecision(
```

Meaning:
- no fake flat order is created when the router chooses `NO_TRADE`

## Evidence 6: Spot-only interpretation remains intact

Source tests and runtime patterns:
- engine C and D runtime tests consistently assert `Side.BUY`
- no inspected scoring, risk, or portfolio seam creates leverage or short exposure
- execution venue normalization and gatekeeping operate on quantity/price/notional, not synthetic short rails

Classification summary:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `CONSUMER_FOUND`

External-audit questions:
- If SELL appears in future portfolio or execution contexts, is it always explicitly spot inventory reduction rather than shorting?
- Should side-preservation tests be added for engine A/B runtime end-to-end paths as well, even though this pack already found no contrary evidence?

