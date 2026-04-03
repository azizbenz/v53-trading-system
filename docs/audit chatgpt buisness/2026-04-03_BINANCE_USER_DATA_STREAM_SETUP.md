# Binance User Data Stream Setup

## Scope

- Public market data stays on Binance public WebSocket streams.
- Private account data uses Binance authenticated WebSocket API.
- Active local campaign scope: `BTCUSDT`, `ETHUSDT`.

## Secrets

Do not store Binance secrets in the repository or in JSON config files.

Use local environment variables instead:

```powershell
$env:BINANCE_API_KEY="your_api_key"
$env:BINANCE_API_SECRET="your_api_secret"
```

## Local campaign config

The local ignored campaign file:

- `build/build11_live_websocket_campaign/live_websocket_config.json`

is expected to use:

- `pairs=["BTCUSDT","ETHUSDT"]`
- `user_data_stream_enabled=true`
- `user_data_api_key_env_var="BINANCE_API_KEY"`
- `user_data_api_secret_env_var="BINANCE_API_SECRET"`

## Run

```powershell
python "E:\claude  v5.3\v53_trading_system\scripts\run_shadow_vps_service.py" --service-dir "E:\claude  v5.3\v53_trading_system\build\build11_live_websocket_campaign\service" --orchestrator-output-dir "E:\claude  v5.3\v53_trading_system\build\build11_live_websocket_campaign\orchestrator" --shadow-output-dir "E:\claude  v5.3\v53_trading_system\build\build11_live_websocket_campaign\shadow_session" --live-websocket-config "E:\claude  v5.3\v53_trading_system\build\build11_live_websocket_campaign\live_websocket_config.json" --live-captures-root "E:\claude  v5.3\v53_trading_system\build\build11_live_websocket_campaign\live_captures" --auto-exports-root "E:\claude  v5.3\v53_trading_system\build\build11_live_websocket_campaign\auto_exports" --max-cycles 1 --poll-interval-s 0 --stop-on-error
```

## Expected artifacts

- public market capture summary:
  - `live_websocket_capture_summary.json`
- private user-data capture summary:
  - `live_user_data_capture_summary.json`
- private user-data raw events:
  - `live_user_data_events.jsonl`

## Notes

- Public market streams provide pair prices and market events.
- Private user-data stream provides account-linked events for the authenticated Binance profile.
- Private user-data stream does not replace public market data.
