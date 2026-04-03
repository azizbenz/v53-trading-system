# 2026-04-03 - Build-11 Target-Environment Same-Day Rerun Idempotency Audit

## Scope

Verify that rerunning the autonomous Build-11 target-environment Shadow
campaign on the **same real calendar day** does not falsely increment the
30-day counter and does not fabricate a second Shadow day.

This audit was executed on the same campaign root already used for the real
day-1 checkpoint:

- `build/build11_live_websocket_campaign`

## Command Used

The same command was rerun outside the sandbox on `2026-04-03`:

```powershell
python scripts/run_shadow_vps_service.py --service-dir build/build11_live_websocket_campaign/service --orchestrator-output-dir build/build11_live_websocket_campaign/orchestrator --shadow-output-dir build/build11_live_websocket_campaign/shadow_session --live-websocket-config build/build11_live_websocket_campaign/live_websocket_config.json --live-captures-root build/build11_live_websocket_campaign/live_captures --auto-exports-root build/build11_live_websocket_campaign/auto_exports --max-cycles 1 --poll-interval-s 0 --stop-on-error
```

## Factual Outputs After Rerun

### Campaign summary

`build/build11_live_websocket_campaign/service/shadow_vps_service.campaign_summary.json`

Key facts after the same-day rerun:

- `loop_count=2`
- `success_count=1`
- `idle_count=1`
- `resumed=true`
- `consecutive_days=1`
- `remaining_days=29`
- `promotion_gate_passed=false`

Interpretation:

- the service loop executed a second time
- but it did **not** count a second successful Shadow day
- it remained on the same honest `1/30` campaign state

### Service state

`build/build11_live_websocket_campaign/service/shadow_vps_service.state.json`

Key facts:

- `resumed=true`
- `loop_count=2`
- `success_count=1`
- `idle_count=1`
- `last_completed_session_date=2026-04-03`
- `last_error` is empty

### Session summary

`build/build11_live_websocket_campaign/shadow_session/local_replay_shadow.shadow_session_summary.json`

Key facts:

- `session_dates=[2026-04-03]`
- `consecutive_days=1`
- `remaining_days=29`
- `promotion_gate_passed=false`

No synthetic second day was created.

### Structured events

`build/build11_live_websocket_campaign/service/shadow_vps_service.events.jsonl`

New same-day rerun event chain:

1. `service_started` with resume semantics
2. `idle_no_pending_export`
3. `service_stopped`

Important absence:

- there is **no** new `shadow_day_completed` event for a fake second day

## Honest Conclusion

The Build-11 target-environment campaign is now proven idempotent for a same-day
rerun on `2026-04-03`:

- rerunning the collector on the same calendar day does not fabricate day 2
- the campaign remains at `1` consecutive day
- the service records the rerun as an idle/resume pass, not as a new valid
  Shadow day

This is the expected prod-safe behavior.

## Next Safe Action

The next honest progression step remains unchanged:

- rerun the same command on the next real calendar day `2026-04-04`
- keep the same campaign directories
- keep `session_date_override` absent

If that next-day run succeeds, the campaign should then progress honestly from
`1/30` to `2/30`.
