# Wave 3 Side / Halal Execution Safety Evidence

Classification:
- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `CONSUMER_FOUND`

## 1. Side passthrough in routing bridge

Source file: `src/execution_backbone/execution_routing_bridge.py`

```python
def _normalize_side(side: str) -> str:
    normalized = side.strip().casefold()
    if normalized == "buy":
        return "BUY"
    if normalized == "sell":
        return "SELL"
    raise RoutingFeatureProjectionError("missing_field", f"Unsupported execution side: {side!r}")
```

Evidence:
- routing normalizes existing side only
- it does not invent side from cost, fill, or latency formulas

Test:
- `tests/unit/protocols/test_execution_routing_bridge.py::test_project_side_passthrough`

## 2. Gatekeeper preserves upstream side

Source file: `src/execution_backbone/gatekeeper/gatekeeper.py`

Evidence from inspected runtime path:
- cost, rate-limit, spread, venue constraints, and no-trade hooks veto or allow
- they do not synthesize alternate side

Reason-code evidence:
- `NoTradeReason.COST_EXCEEDS_EDGE`
- `NoTradeReason.VENUE_CONSTRAINTS`
- `NoTradeReason.HARD_BLOCKER`
- `NoTradeReason.SHARIA_BLOCKED`

## 3. Adapter translation preserves side and rejects NO_TRADE

Source file: `src/venue_adapters/binance_spot/order_translator.py`

```python
if intent.order_type == OrderType.NO_TRADE:
    raise ValueError("cannot translate NO_TRADE intent into Binance order request")
...
side = BinanceOrderSide(intent.side.upper())
```

Evidence:
- no fake-flat order is translated
- adapter uses governed intent side directly

## 4. Spot-only evidence

Source file: `src/venue_adapters/binance_spot/rest_client.py`

```python
account_type=str(payload.get("accountType", "")),
...
is_spot_trading_allowed=bool(entry.get("isSpotTradingAllowed", False)),
```

Evidence:
- inspected adapter is Binance Spot-specific
- exchange-info and account surfaces expose spot flags

## 5. No leverage or funding trigger found in execution seams

Evidence:
- no funding-rate-only trigger was found in the inspected execution backbone, venue adapter, or replay cost seams used in this pack
- no leverage sizing formula was found in the inspected execution submit path

Classification:
- `CONSUMER_FOUND`

External-audit questions:
- Contract surfaces outside the governed runtime may still mention generic `SELL`; external audit should distinguish generic contract capability from the governed spot-only production rail.
