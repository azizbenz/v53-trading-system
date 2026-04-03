# V5.3 - BUILD-11 NATIVE LIVE_WEBSOCKET SMOKE AND FALSE-GREEN FIX AUDIT
## Date: 2026-04-03
## Branch: codex/full-shadow-abcd-migration-20260403
## Status: PARTIAL_TARGET_ENVIRONMENT_PROOF_FROZEN

---

# 0. Purpose

This audit freezes two linked facts on the Full Shadow migration branch:

- a bounded native `live_websocket` Build-11 smoke was executed successfully outside
  the sandbox against the real network path
- the local replay Shadow runner was corrected so the persisted
  `shadow_summary.json` no longer emits a false `30/30 + shadow_report_ready=true`
  signal after only one governed Shadow day

This is a prod-safe checkpoint, not a declaration that Build-11 is fully closed.

---

# 1. What was observed before the fix

## 1.1 Sandbox run

Inside the default sandbox, the bounded command:

```powershell
python scripts/run_shadow_vps_service.py --service-dir build\build11_live_websocket_smoke\service --orchestrator-output-dir build\build11_live_websocket_smoke\orchestrator --shadow-output-dir build\build11_live_websocket_smoke\shadow_session --live-websocket-config build\build11_live_websocket_smoke\live_websocket_config.json --live-captures-root build\build11_live_websocket_smoke\live_captures --auto-exports-root build\build11_live_websocket_smoke\auto_exports --max-cycles 1 --poll-interval-s 0 --stop-on-error
```

ended with:

- `service_status=degraded`
- `last_error="Native live_websocket adapter failed to connect"`
- no capture summary file materialized

This is now treated as a sandbox/network-path limitation, not as proof of a code bug.

## 1.2 Real issue discovered after the first successful network run

After rerunning outside the sandbox, the network path worked, but the produced
artifacts were inconsistent:

- `shadow_session_summary.json` correctly said `consecutive_days=1`, `remaining_days=29`
- but `shadow_summary.json` still said `shadow_days_completed=30` and
  `shadow_report_ready=true`

That was a false green and an unacceptable promotion signal.

---

# 2. Root cause

In `scripts/run_local_replay_shadow.py`, the persisted `shadow_input` / `shadow_summary`
were still built from a provisional validation input hard-coded with:

- `shadow_days_completed=30`
- `shadow_report_ready=True`

That provisional summary was useful for counting a governed day, but it was not
valid as the final persisted promotion artifact.

---

# 3. Fix applied

The runner now has two distinct phases:

1. a provisional in-memory summary used only to decide whether the current Shadow
   day counts toward the 30-day counter
2. a final persisted `shadow_input.json` and `shadow_summary.json` rebuilt from the
   real `ShadowDayCounter` report after the day is recorded

Effect:

- day counting remains intact
- persisted promotion artifacts now tell the truth
- one bounded day no longer impersonates a 30-day completed Shadow

---

# 4. Validation

## 4.1 Focused code/test validation

```powershell
rtk pytest tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py -q
```

Result:

- `13 passed`

Broader Build-11 refresh:

```powershell
rtk pytest tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_daily_orchestrator.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_protocols/test_shadow_runtime.py tests/test_protocols/test_shadow_day_counter.py tests/test_regression_alignment.py -q
```

Result:

- `100 passed`

## 4.2 Target-environment smoke after the fix

The bounded rerun outside the sandbox:

```powershell
python scripts/run_shadow_vps_service.py --service-dir build\build11_live_websocket_smoke_fixed\service --orchestrator-output-dir build\build11_live_websocket_smoke_fixed\orchestrator --shadow-output-dir build\build11_live_websocket_smoke_fixed\shadow_session --live-websocket-config build\build11_live_websocket_smoke\live_websocket_config.json --live-captures-root build\build11_live_websocket_smoke_fixed\live_captures --auto-exports-root build\build11_live_websocket_smoke_fixed\auto_exports --max-cycles 1 --poll-interval-s 0 --stop-on-error
```

produced a coherent chain:

- native live capture completed
- governed auto-export completed
- daily orchestrator completed one Shadow day
- runtime evidence bundle written

Key produced facts:

- `live_websocket_capture_summary.json`
  - `accepted_message_count=2`
  - `pair_scope=["BTCUSDT"]`
  - `event_types=["snapshot", "trade"]`
- `shadow_summary.json`
  - `run_state="blocked"`
  - `decision.accepted=false`
  - `blocking_reasons` include `30 consecutive days` and `complete shadow report`
  - `shadow_days_completed=1`
  - `shadow_report_ready=false`
- `shadow_session_summary.json`
  - `consecutive_days=1`
  - `remaining_days=29`
  - `promotion_gate_passed=false`
- `runtime_evidence bundle`
  - `acquisition_mode="native_live_websocket_auto_export"`
  - `accepted=false`
  - `consecutive_days=1`
  - `remaining_days=29`

---

# 5. Honest conclusion

What is now proven on this branch:

- the native `live_websocket` path can work against the real network when run
  outside the sandbox
- the autonomous VPS service can capture, auto-export, orchestrate one governed
  Shadow day, and write a durable runtime evidence bundle
- the persisted Build-11 promotion artifacts now report an honest
  `1 day / 29 remaining / not ready` state

What is still not proven:

- a real 30-day target-environment Shadow chain
- final Build-11 closure
- downstream Build-12 / Build-13 operational readiness

Verdict:

- `Build-11` remains `STILL_PARTIAL`
- `GAP-005` is reduced but not closed

---

# 6. Next safe move

The next safe move is not more local reinterpretation.

It is either:

- continue collecting real governed Shadow days on the target environment
- or stop here and preserve this bounded proof as the last honest checkpoint

