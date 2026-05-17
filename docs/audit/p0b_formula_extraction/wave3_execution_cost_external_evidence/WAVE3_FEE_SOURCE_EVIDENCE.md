# Wave 3 Fee Source Evidence

Classification:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `CONSUMER_FOUND`
- `FEE_SOURCE_NOT_PROVEN` for replay expected-cost seam

## 1. Explicit fee measurement seam

Source file: `src/execution_backbone/execution_cost_meter/fee_meter.py`  
Function: `compute_fee`

```python
gross_value_exact = multiply_exact(price, quantity)
fee_amount_decimal = execution_decimal(fee_amount, name="fee_amount")
fee_rate_exact = divide_exact_or_zero(fee_amount_decimal, gross_value_exact)
```

Plain-text formula:
- `gross_value = price * quantity`
- `fee_rate = fee_amount / gross_value`

Inputs:
- `price`
- `quantity`
- `fee_amount`
- `fee_asset`
- `maker`

Output:
- `FeeBreakdown.fee_rate`
- `FeeBreakdown.fee_amount`

Units:
- `fee_rate`: fraction
- `fee_amount`: quote currency or fee asset-denominated amount carried as numeric amount
- `gross_value`: notional

Scope:
- per-fill or per-trade explicit fee breakdown

Semantics:
- measured if `fee_amount` comes from venue event
- not replay-only
- maker/taker flag present, but cost formula itself is generic

Tests:
- `tests/test_execution_backbone/test_execution_cost_meter.py::TestFeeMeter::test_compute_fee`
- `tests/test_execution_backbone/test_execution_cost_meter.py::TestFeeMeter::test_maker_flag`

Consumers:
- execution runtime cost recording
- cost aggregator

## 2. Ex-ante fee estimate fallback

Source file: `src/execution_backbone/execution_cost_meter/fee_meter.py`  
Function: `estimate_fee`

```python
def estimate_fee(
    price: float,
    quantity: float,
    fee_rate: float = 0.001,  # default 10bps taker
) -> float:
    return decimal_to_float64(multiply_exact(multiply_exact(price, quantity), fee_rate))
```

Plain-text formula:
- `estimated_fee = price * quantity * fee_rate`

Units:
- quote currency / notional currency

One-way or round-trip:
- one-way fee estimate

Maker/taker:
- generic fallback, default comment says `10bps taker`

Tests:
- `tests/test_execution_backbone/test_execution_cost_meter.py::TestFeeMeter::test_estimate_fee`

External-audit question:
- Is the default `0.001` fee rate a governed venue-specific assumption or a generic fallback only?

## 3. Runtime consumption of measured or fallback fees

Source file: `src/execution_backbone/execution_runtime.py`  
Function: `_record_fill_event`, `_record_trade_cost`

```python
fill_event = FillEvent(
    ...
    fee=event.fee_amount,
    fee_asset=event.fee_asset,
)
...
explicit_fee = aggregated.total_fees
if explicit_fee <= 0:
    explicit_fee = estimate_fee(aggregated.average_price, aggregated.total_filled_qty, fee_rate=fee_rate)
...
compute_trade_cost(
    ...
    explicit_fee=explicit_fee,
    ...
    expected_cost=intent.expected_cost,
)
```

Plain-text evidence:
- Live/shadow runtime prefers measured fill fees from venue events.
- If aggregated measured fees are missing or zero, runtime falls back to `estimate_fee(...)`.

Outputs:
- `explicit_fee`
- `TradeCost.explicit_fee`

Consumers:
- `CostAggregator.record`
- break-even / realized-cost analysis downstream

False-green risk:
- Missing measured fee can silently fall back to estimated fee. That is not a placeholder zero, but external audit should check whether fallback usage is visible enough.

## 4. Venue fee source evidence

Source file: `src/venue_adapters/binance_spot/rest_client.py`  
Function: `_parse_account_snapshot`

```python
return BinanceAccountSnapshot(
    maker_commission=int(payload.get("makerCommission", 0)),
    taker_commission=int(payload.get("takerCommission", 0)),
    buyer_commission=int(payload.get("buyerCommission", 0)),
    seller_commission=int(payload.get("sellerCommission", 0)),
    ...
)
```

Source file: `src/execution_backbone/execution_routing_bridge.py`  
Function: `_project_impl`

```python
maker_fee_bps=float(venue_fees.maker_fee_bps),
taker_fee_bps=float(venue_fees.taker_fee_bps),
```

Source file: `src/execution_backbone/order_decider/hybrid_router_equations.py`

```python
return expected_edge_bps - taker_fee_bps - expected_taker_slippage_bps
```

Evidence:
- Venue-specific fee fields exist in account and routing surfaces.
- Hybrid routing explicitly consumes maker/taker fee bps.

Ambiguity:
- The exact unit conversion path from Binance integer commission fields into routed `maker_fee_bps` / `taker_fee_bps` was not fully proven in this pack.

Classification:
- `AMBIGUITY_FOUND`
- `UNIT_AMBIGUITY`

## 5. Fee inclusion in replay expected-cost seam

Source file: `src/local_replay_runtime/shadow_execution_simulator.py`  
Function: `_expected_cost`

```python
return (
    row.spread_bps
    + row.slippage_bps * config.slippage_multiplier
    + row.latency_penalty_bps * config.latency_penalty_multiplier
) / 10_000.0
```

Evidence:
- No explicit fee term is present in replay `_expected_cost`.

Classification:
- `FEE_SOURCE_NOT_PROVEN`
- `EXPECTED_REALIZED_AMBIGUITY`

External-audit questions:
- Is fee intentionally absent from replay prudent expected cost?
- If so, is there an upstream data-prebaked `slippage_bps` or `expected_edge_bps` convention that already embeds fees?
- If not, how should replay expected CE be interpreted versus live/shadow measured realized cost?
