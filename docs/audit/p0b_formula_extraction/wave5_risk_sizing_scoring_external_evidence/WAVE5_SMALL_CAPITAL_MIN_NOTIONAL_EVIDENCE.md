# Wave 5 Small Capital / Min-Notional Evidence

## Evidence 1: Venue min-notional is enforced fail-closed at execution normalization

Source file:
- `src/execution_backbone/execution_runtime_support.py`

Function:
- `_normalize_venue_order_fields`

Exact code excerpt:
```python
if quantity_decimal <= 0:
    return ExecutionVenueNormalizationResult(
        quantity=0.0,
        quantity_exact="0",
        error_detail="venue constraints reduce quantity to zero",
    )
```

```python
if constraints.min_notional is not None:
    if price_anchor_decimal is None:
        return ExecutionVenueNormalizationResult(
            quantity=0.0,
            quantity_exact="0",
            error_detail="min_notional requires a usable price anchor",
        )
    normalized_notional = multiply_exact(quantity_decimal, price_anchor_decimal)
    if normalized_notional < execution_decimal(
        constraints.min_notional, name="min_notional"
    ):
        return ExecutionVenueNormalizationResult(
            quantity=0.0,
            quantity_exact="0",
            error_detail="normalized order violates venue min_notional",
        )
```

Meaning:
- invalid small orders are blocked at execution normalization
- no invalid order is silently submitted

Units:
- `normalized_notional`: quote notional

Tests:
- covered in execution-backbone venue / runtime tests

Classification:
- `EVIDENCE_EXTRACTED`
- `SMALL_CAPITAL_RISK`

## Evidence 2: Venue constraints source

Source file:
- `src/execution_backbone/venue_constraints_provider.py`

Function:
- `parse_binance_exchange_info_payload`

Exact code excerpt:
```python
tick_size: str | None = None
step_size: str | None = None
min_notional: str | None = None
```

```python
if filter_type == "PRICE_FILTER":
    tick_size = _positive_decimal_str_or_none(filter_entry.get("tickSize"))
elif filter_type == "LOT_SIZE":
    step_size = _positive_decimal_str_or_none(filter_entry.get("stepSize"))
elif filter_type == "MIN_NOTIONAL":
    min_notional = _positive_decimal_str_or_none(filter_entry.get("minNotional"))
elif filter_type == "NOTIONAL" and min_notional is None:
    min_notional = _positive_decimal_str_or_none(filter_entry.get("minNotional"))
```

Meaning:
- venue min-notional and rounding inputs are sourced explicitly from exchange metadata

## Evidence 3: Replay/cockpit small-capital tracking is still not proven

Source file:
- `src/local_replay_runtime/replay_metrics_collector.py`
- `src/cockpit/state_replay_metrics.py`

Exact code excerpt:
```python
small_capital_exclusion_rate: float | None = None
small_capital_exclusion_status: str = "NOT_PROVEN"
```

Meaning:
- the field exists as an additive status seam
- no measured replay small-capital exclusion rate is produced by the inspected collector

Search result:
- search for `small_capital_exclusion_rate|small_capital_exclusion_status|min_notional_blocked_count|insufficient_capital` found only replay/cockpit status fields and execution min-notional normalization, not a measured backtest viability study

Classification:
- `EVIDENCE_EXTRACTED`
- `SMALL_CAPITAL_RISK`
- `NOT_PROVEN_NEEDS_EXTERNAL_AUDIT`

## Evidence 4: Cockpit blocked-count availability remains partial

Source file:
- `src/cockpit/state_economic_sterilization.py`

Evidence excerpt:
```python
min_notional_blocked_count: int | None = None
min_notional_blocked_count_status: str = "SOURCE_UNAVAILABLE"
```

Meaning:
- cockpit does not fake a measured min-notional blocked count
- but the metric is unavailable rather than governed and complete

Tests:
- `tests/cockpit/test_state_economic_sterilization.py`

## 400-500 EUR relevance

Backtest Ladder planning evidence:
- `docs/audit/p0b_formula_extraction/31_BACKTEST_STRATEGY_LADDER.md` explicitly asks whether the system works at `400 EUR`, `500 EUR`, `1000 EUR`, `2000 EUR`, and `4000 EUR`
- it also requires min-notional, fee model, slippage model, and blocked-trade accounting in the future capital ladder

Interpretation:
- current code proves execution-side fail-closed min-notional handling
- current code does not prove pair-level feasibility or exclusion rates for 400-500 EUR

External-audit questions:
- How many candidates per pair/engine survive min-notional, fees, and step-size rounding at 400-500 EUR?
- Does pair count fragment capital enough to make multi-pair deployment structurally uneconomic at low capital?

