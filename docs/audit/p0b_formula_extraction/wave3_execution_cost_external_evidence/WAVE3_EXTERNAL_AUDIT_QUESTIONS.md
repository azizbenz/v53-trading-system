# Wave 3 External Audit Questions

1. Replay expected-cost seam:
- Is replay `_expected_cost` intentionally defined as `spread + scaled slippage + scaled latency penalty`, with fee and impact omitted?
- If yes, where is that doctrine written and how should external audit compare it to live/shadow measured total cost?

2. Fee units:
- Are Binance `makerCommission` / `takerCommission` integer fields mapped to bps, fraction, or exchange-native integer units before they become `maker_fee_bps` / `taker_fee_bps` in routing?

3. Impact realism:
- Is `lambda_impact_bps * sqrt(participation_ratio)` the governed impact proxy for taker path only, or is there a separate calibrated market-impact doctrine elsewhere?

4. Replay fill realism:
- Does historical `fill_ratio` come from measured execution telemetry, or from a synthetic heuristic derived during replay dataset assembly?

5. Realized slippage:
- Should realized slippage exist as a separate metric, or is the system intentionally exposing only realized total cost decomposition?

6. Cost parity:
- What is the governed relationship between replay `production_expected_cost`, replay simulated `expected_cost`, and live/shadow measured `total_cost`?

7. Fail-open policy:
- Are fail-open paths for missing rate-limit telemetry or invalid spread doctrinally acceptable for VPS non-HFT?

8. Venue constraints:
- Is small-capital systematic min-notional exclusion an expected product behavior or a scenario requiring operator warning/reporting?

9. Cockpit placeholders:
- Should cockpit execution adapters that still default `expected_cost`, `realized_cost`, or blocked sub-counts to `0.0` be hardened to explicit unavailable states?

10. Side/halal safety:
- Can external audit confirm that governed production usage of `SELL` remains compatible with spot-only doctrine and does not imply hidden shorting?
