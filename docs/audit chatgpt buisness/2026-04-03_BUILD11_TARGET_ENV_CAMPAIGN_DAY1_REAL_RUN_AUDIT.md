# 2026-04-03 - Build-11 Target-Environment Campaign Day 1 Real Run Audit

## Scope

Freeze the first honest target-environment Build-11 Shadow campaign day on the
Full Shadow migration branch, using the native `live_websocket` acquisition
path and the autonomous VPS Shadow service without any artificial
`session_date_override`.

## Command Used

The real run was executed outside the sandbox with the following command:

```powershell
python scripts/run_shadow_vps_service.py --service-dir build/build11_live_websocket_campaign/service --orchestrator-output-dir build/build11_live_websocket_campaign/orchestrator --shadow-output-dir build/build11_live_websocket_campaign/shadow_session --live-websocket-config build/build11_live_websocket_campaign/live_websocket_config.json --live-captures-root build/build11_live_websocket_campaign/live_captures --auto-exports-root build/build11_live_websocket_campaign/auto_exports --max-cycles 1 --poll-interval-s 0 --stop-on-error
```

## Campaign Root

All runtime artifacts for this first real day live under:

- `build/build11_live_websocket_campaign`

The governing config used for the run is:

- `build/build11_live_websocket_campaign/live_websocket_config.json`

Important honesty rule:

- the config did **not** contain `session_date_override`
- the run therefore used the real current day `2026-04-03`

## Factual Outputs

### Service state

`build/build11_live_websocket_campaign/service/shadow_vps_service.state.json`

Key facts:

- `service_status=stopped`
- `success_count=1`
- `last_completed_session_date=2026-04-03`
- `last_live_capture_dir_ref` points to the `2026-04-03` live capture folder
- `last_runtime_evidence_bundle_ref` points to the durable per-session bundle
- `last_campaign_summary_ref` points to the cumulative campaign summary
- `last_error` is empty

### Cumulative campaign summary

`build/build11_live_websocket_campaign/service/shadow_vps_service.campaign_summary.json`

Key facts:

- `service_status=stopped`
- `acquisition_mode=native_live_websocket_auto_export`
- `accepted=false`
- `consecutive_days=1`
- `remaining_days=29`
- `promotion_gate_passed=false`
- `runtime_data_source=recorded_replay`
- `live_capture_emitted_message_count=2`
- `live_capture_accepted_message_count=2`
- `live_capture_ignored_message_count=0`
- `live_capture_rejected_message_count=0`
- `live_capture_pair_scope=[BTCUSDT]`
- `live_capture_event_types=[snapshot]`

### Native live capture summary

`build/build11_live_websocket_campaign/live_captures/2026-04-03/live_websocket_capture_summary.json`

Key facts:

- `emitted_message_count=2`
- `accepted_message_count=2`
- `ignored_message_count=0`
- `rejected_message_count=0`
- `route_count=1`
- `pair_scope=[BTCUSDT]`
- `event_types=[snapshot]`

### Durable runtime evidence bundle

`build/build11_live_websocket_campaign/service/runtime_evidence/2026-04-03.shadow_vps_runtime_evidence.json`

Key facts:

- `session_date=2026-04-03`
- `acquisition_mode=native_live_websocket_auto_export`
- live-capture refs and counts are persisted
- `accepted=false`
- `consecutive_days=1`
- `remaining_days=29`

### Shadow summary

`build/build11_live_websocket_campaign/shadow_session/local_replay_shadow.shadow_summary.json`

Key facts:

- `run_state=blocked`
- `decision.accepted=false`
- blocking reasons still require:
  - `30 consecutive days`
  - `complete shadow report`
- `shadow_days_completed=1`
- `shadow_report_ready=false`
- `active_engines=[engine_a, engine_b, engine_c, engine_d]`

### Session summary

`build/build11_live_websocket_campaign/shadow_session/local_replay_shadow.shadow_session_summary.json`

Key facts:

- `session_dates=[2026-04-03]`
- `consecutive_days=1`
- `remaining_days=29`
- `promotion_gate_passed=false`

### Structured service events

`build/build11_live_websocket_campaign/service/shadow_vps_service.events.jsonl`

Observed event chain:

1. `service_started`
2. `live_capture_completed`
3. `auto_export_completed`
4. `runtime_evidence_bundle_written`
5. `shadow_day_completed`
6. `service_stopped`

## Honest Conclusion

This is a real operational checkpoint, not a synthetic local replay-only story:

- one real target-environment campaign day was collected on `2026-04-03`
- the service captured native live websocket data
- it auto-generated governed replay inputs
- it completed one honest Shadow day
- it persisted a coherent 1-day / 29-days-remaining evidence chain

Build-11 still remains `STILL PARTIAL` because:

- only `1` real calendar day is recorded
- the 30-day gate is not met
- the complete shadow report gate is not met

## Next Safe Action

The next honest move is **not** to invent day 2 locally.

The next honest move is:

- rerun the exact same command on the next real calendar day
- reuse the same campaign directories
- keep `session_date_override` absent

If the next real-day run succeeds on `2026-04-04`, the campaign should then
progress from `1` to `2` consecutive days in the same persisted evidence chain.
