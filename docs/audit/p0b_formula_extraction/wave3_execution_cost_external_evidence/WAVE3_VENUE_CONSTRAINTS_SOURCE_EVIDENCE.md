# Wave 3 Venue Constraints Source Evidence

Classification:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `CONSUMER_FOUND`

## 1. Venue metadata parse

Source file: `src/execution_backbone/venue_constraints_provider.py`  
Function: `parse_binance_exchange_info_payload`

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

Outputs:
- `VenueConstraintSnapshot.tick_size`
- `VenueConstraintSnapshot.step_size`
- `VenueConstraintSnapshot.min_notional`

Units:
- decimal strings representing price tick, quantity step, and quote-currency notional floor

Tests:
- `tests/test_execution_backbone/test_venue_constraints_provider.py::test_parse_binance_exchange_info_payload_normalizes_constraints`
- `...::test_parse_binance_exchange_info_payload_accepts_notional_filter`

## 2. Cache-only critical path

Source file: `src/execution_backbone/venue_constraints_provider.py`  
Function: `fetch_venue_constraints`

```python
"""Return cached constraints only. Never makes network calls.

BS-66: HTTP must NOT happen on the execution critical path.
"""
```

Evidence:
- critical path is cache-only
- `pre_warm()` performs HTTP fetch at startup

Tests:
- `tests/test_execution_backbone/test_venue_constraints_provider.py::test_pre_warm_fetches_then_persists_cache`
- `...::test_fetch_returns_none_on_cache_miss_no_http`

## 3. Quantity/price/min-notional normalization

Source file: `src/execution_backbone/execution_runtime_support.py`  
Function: `_normalize_venue_order_fields`

```python
quantity_decimal = (
    quantize_down_to_step(quantity_decimal, constraints.step_size)
    if constraints.step_size is not None
    else quantity_decimal
)
...
normalized_price_decimal = (
    quantize_down_to_step(price_limit, constraints.tick_size)
    if side.lower() == "buy"
    else quantize_up_to_step(price_limit, constraints.tick_size)
)
...
normalized_notional = multiply_exact(quantity_decimal, price_anchor_decimal)
if normalized_notional < execution_decimal(constraints.min_notional, name="min_notional"):
    return ExecutionVenueNormalizationResult(
        quantity=0.0,
        quantity_exact="0",
        error_detail="normalized order violates venue min_notional",
    )
```

Plain-text behavior:
- quantity is rounded down to step size
- buy limit price is rounded down to tick size
- sell limit price is rounded up to tick size
- min-notional violation fail-closes the order before submit

Missing behavior:
- if price anchor is unavailable and min-notional is required, normalization fails closed with `"min_notional requires a usable price anchor"`

## 4. Runtime enforcement

Source file: `src/execution_backbone/gatekeeper/gatekeeper.py`

```python
if normalization.error_detail is not None:
    return self._refuse(
        gate_name=ExecutionGateName.VENUE_CONSTRAINTS,
        disposition=ExecutionGateRefusalDisposition.NO_TRADE,
        reason=NoTradeReason.VENUE_CONSTRAINTS,
        ...
    )
```

Evidence:
- invalid normalized orders do not reach the adapter
- rejected trades get explicit `VENUE_CONSTRAINTS` refusal

Tests:
- execution runtime tests cover min-notional and venue normalization paths

Consumer risk:
- small capital can systematically block trades if normalized notional drops under venue minimum

Classification:
- `CONSUMER_FOUND`
- `HUMAN_OR_EXTERNAL_AUDIT_REQUIRED` for product-level small-capital consequences
