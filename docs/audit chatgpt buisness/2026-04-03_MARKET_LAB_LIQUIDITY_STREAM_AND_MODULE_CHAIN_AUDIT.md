# 2026-04-03 Market Lab Liquidity Stream And Module-Chain Audit

## Scope

- Add `book_ticker` and `depth` liquidity telemetry to the local HTML Market Lab.
- Verify the same public Binance market-data perimeter can still traverse the real module chain through `run_shadow_vps_service.py`.
- Keep the lot prod-safe and audit-ready.

## Initial blocker

The first real module-chain smoke with:

- `pairs = BTCUSDT, ETHUSDT`
- `stream_types = kline_1m, book_ticker, depth`

failed before ingestion. The service degraded with:

- `Observed websocket ingestion requires at least one message`

The concrete failure mode was consistent with Binance public websocket control-message limits:

- the native adapter was sending one `SUBSCRIBE` request per pair/stream combination
- that meant 6 control messages on one connection for `2 pairs x 3 streams`
- the public Binance websocket docs limit incoming control messages to 5 per second

## Code correction

The native adapter in:

- `src/protocols/shadow_live_websocket.py`

now batches pending subscriptions per endpoint and flushes them as a single `SUBSCRIBE` payload on first receive.

This changed the behavior from:

- multiple sequential `SUBSCRIBE` JSON messages

to:

- one `SUBSCRIBE` JSON message carrying the full parameter list

The local HTML Market Lab in:

- `src/ui/technical_dashboard_html.py`

was also extended to expose public liquidity telemetry with:

- `1m / 15m / 1h / 4h / 1d`
- `Candles / Line`
- `book_ticker` status line
- `depth` status line

The HTML now opens a combined public Binance stream:

- `@kline_<tf>`
- `@bookTicker`
- `@depth`

for the selected pair.

## Test proof

Focused green evidence:

- `rtk pytest tests/test_protocols/test_shadow_live_websocket.py tests/test_ui/test_technical_dashboard_launcher.py tests/test_ui/test_technical_dashboard.py -q`
  - result: `20 passed`
- `rtk pytest tests/test_manifest_registry/test_runtime_surface.py -q`
  - result: `21 passed`

The adapter test now explicitly proves that a multi-pair multi-stream request is batched into one `SUBSCRIBE` call.

## Runtime proof

A real public Binance smoke was rerun outside the sandbox through the actual module chain using:

- `BTCUSDT`
- `ETHUSDT`
- `kline_1m`
- `book_ticker`
- `depth`

via `scripts/run_shadow_vps_service.py`.

Outcome:

- the service no longer failed with zero-ingest
- the run completed through:
  - live capture
  - auto export
  - governed shadow day
- the service reached `shadow_day_completed`

Captured result on this bounded runtime window:

- `emitted_message_count = 2`
- `accepted_message_count = 2`
- `pair_scope = [BTCUSDT, ETHUSDT]`
- `event_types = [depth]`

Important nuance:

- this proves the module chain is no longer blocked by subscription fan-out
- it does **not** yet prove that the bounded runtime window observed all three requested stream families on that run
- the observed subset on this concrete run was `depth`

## Verdict

This lot is **successful but narrowly interpreted**:

- `HTML Market Lab liquidity telemetry`: implemented
- `module-chain public Binance smoke`: green after subscription batching
- `full trio observed on one real bounded run`: not yet proven

## Next action

Do not reopen doctrine or invent new runtime profiles.

If more runtime richness is wanted later, the next safe follow-up is:

1. keep the current batching fix
2. rerun a bounded public-market smoke with a longer capture window
3. verify whether `kline`, `book_ticker`, and `depth` all appear in one real capture summary

This does not replace the main prod-safe priority:

- the real `Build-11` 30-day target-environment campaign remains the main runtime closure path
