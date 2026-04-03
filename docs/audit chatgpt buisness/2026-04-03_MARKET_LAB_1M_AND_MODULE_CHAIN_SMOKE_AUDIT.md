# Market Lab 1m And Module Chain Smoke Audit

## Scope

- Expose `1m` in the local HTML market lab timeframe selector.
- Verify that the same public Binance `kline_1m` flow can also be consumed by the real Shadow module chain.

## UI change

File updated:

- `src/ui/technical_dashboard_html.py`

Behavior:

- The local HTML market lab now exposes:
  - `1m`
  - `15m`
  - `1h`
  - `4h`
  - `1d`

## UI verification

- `rtk pytest tests/test_ui/test_technical_dashboard_launcher.py tests/test_ui/test_technical_dashboard.py -q`
  - result: `16 passed`
- `rtk pytest tests/test_manifest_registry/test_runtime_surface.py -q`
  - result: `21 passed`

## Real module-chain smoke

Smoke executed successfully outside sandbox through the real launcher path:

- script: `scripts/run_shadow_vps_service.py`
- pairs: `BTCUSDT`, `ETHUSDT`
- stream_types: `kline_1m`
- source: Binance public WebSocket
- mode: `native_live_websocket_auto_export`

Observed outcome:

- service run succeeded
- auto export succeeded
- shadow day succeeded
- campaign summary:
  - `success_count = 1`
  - `consecutive_days = 1`
  - `remaining_days = 29`
- live capture summary:
  - `live_capture_emitted_message_count = 4`
  - `live_capture_accepted_message_count = 4`
  - `live_capture_pair_scope = ["BTCUSDT", "ETHUSDT"]`
  - `live_capture_event_types = ["kline"]`

## Artifact roots

- HTML export:
  - `build/technical_dashboard_market_lab/technical_dashboard.html`
- module-chain smoke:
  - `build/market_lab_module_smoke`

## Conclusion

- `1m` is now available in the local market lab.
- The public Binance `kline_1m` flow is not only visible in the browser; it also traverses the real Shadow module chain successfully for `BTCUSDT` and `ETHUSDT`.
