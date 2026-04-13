# Binance Shadow PowerShell Bootstrap

## Scope

- Install or persist the Binance API environment variables used by the live Shadow VPS service.
- Materialize the governed `live_websocket_config.json` under `build/build11_live_websocket_campaign`.
- Launch one bounded Shadow service cycle on native Binance streaming.
- Regenerate the canonical Build-10 HTML dashboard from the resulting runtime artifacts.

## PowerShell env bootstrap

Use the workspace-local script:

```powershell
Set-Location "E:\claude  v5.3\v53_trading_system"

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Install-BinanceApiEnv.ps1 `
  -ApiKey "<BINANCE_API_KEY>" `
  -ApiSecret "<BINANCE_API_SECRET>" `
  -PersistUser
```

Notes:

- This sets:
  - `BINANCE_API_KEY`
  - `BINANCE_API_SECRET`
  - `V53_BINANCE_API_KEY`
  - `V53_BINANCE_SECRET_KEY`
  - `V53_BINANCE_LABEL`
- The script never prints secret values.

## Live Shadow launch

```powershell
Set-Location "E:\claude  v5.3\v53_trading_system"

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-BinanceShadowLiveCampaign.ps1 `
  -PersistUserEnv `
  -EnableTimeSyncProbe
```

Optional governed artifact refs:

```powershell
Set-Location "E:\claude  v5.3\v53_trading_system"

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-BinanceShadowLiveCampaign.ps1 `
  -PersistUserEnv `
  -EnableTimeSyncProbe `
  -ExecutionRuntimeProjectionPath ".\build\dev_dual_role_demo\local_lab_projection_demo\direct_runtime_projection\local_lab_execution_runtime_projection.json" `
  -RegimeLiteAssessmentPath ".\build\governed\regime_lite_assessment.json" `
  -RegimeLiteSafingRecommendationPath ".\build\governed\regime_lite_safing_recommendation.json"
```

## Public-only fallback

When no Binance API env vars are available, the launcher keeps the market-data stream and disables authenticated user-data automatically:

```powershell
Set-Location "E:\claude  v5.3\v53_trading_system"

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-BinanceShadowLiveCampaign.ps1 `
  -PublicOnly `
  -EnableTimeSyncProbe
```

## Produced artifacts

- `build/build11_live_websocket_campaign/live_websocket_config.json`
- `build/build11_live_websocket_campaign/service/...`
- `build/build11_live_websocket_campaign/live_captures/...`
- `build/build11_live_websocket_campaign/technical_dashboard/technical_dashboard.html`

## Current operator status on this Windows machine

- The PowerShell bootstrap now works end-to-end for:
  - env installation
  - governed campaign materialization
  - bounded Shadow service launch
  - Build-10 HTML dashboard regeneration
- The earlier `WinError 10013` observation was caused by the Codex sandbox network restriction, not by the host Windows firewall or missing API env.
- The same bounded launcher now succeeds when executed outside the sandbox on the real host.
- Current operated campaign artifacts show:
  - `last_completed_session_date=2026-04-12`
  - `last_error=""`
  - `execution_telemetry_status=written`
  - `live_user_data_authenticated=true`
  - `live_capture_pair_scope=[BTCUSDT, ETHUSDT]`

## Doctrine

- `Shadow` only, no live order path.
- Typed config and typed governed artifact refs only.
- No secret storage in repo JSON files.
- Dashboard remains a read-only consumer of runtime artifacts.
