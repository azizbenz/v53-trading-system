# Market Lab HTML Public Binance Smoke Audit

## Scope

- Add a local HTML market lab to the technical dashboard.
- Support local operator selection for:
  - pair: `BTCUSDT`, `ETHUSDT`
  - timeframe: `15m`, `1h`, `4h`, `1d`
  - view: `candles`, `line`
- Keep the source public and Shadow-safe:
  - initial candle history from Binance public klines
  - live updates from Binance public WebSocket `kline_*`

## Code touched

- `src/ui/technical_dashboard_html.py`
- `tests/test_ui/test_technical_dashboard_launcher.py`

## Behavior

- The exported technical dashboard now includes a `Live Market Lab` section.
- The section contains:
  - pair selector
  - timeframe selector
  - view selector
  - reload button
  - connection status
  - SVG chart renderer
- The chart can render:
  - candle view from OHLC klines
  - line view from close prices

## Verification

### Local UI tests

- `rtk pytest tests/test_ui/test_technical_dashboard_launcher.py tests/test_ui/test_technical_dashboard.py -q`
  - result: `16 passed`
- `rtk pytest tests/test_manifest_registry/test_runtime_surface.py -q`
  - result: `21 passed`

### Real public Binance smoke

Smoke executed successfully outside sandbox with:

- pairs: `BTCUSDT`, `ETHUSDT`
- stream: `kline_15m`
- mode: public WebSocket only

Observed result:

- `accepted_message_count = 4`
- `pair_scope = ["BTCUSDT", "ETHUSDT"]`
- `event_types = ["kline"]`

Artifact directory:

- `build/market_lab_public_smoke`

## Conclusion

- The local HTML market lab is now present.
- The public Binance WebSocket source works for `BTCUSDT` and `ETHUSDT` with `kline_15m`.
- The HTML surface is ready for local manual inspection in a browser.
