# 2026-04-03 - Build-11 VPS Campaign Summary Audit

## Scope

Add a cumulative, audit-ready campaign summary for the autonomous VPS Shadow
service so the ongoing 30-day Build-11 collection can be reviewed from one file
instead of reconstructing the story from state, events, and per-session runtime
bundles.

## Gap Before Fix

The VPS service already persisted:

- state
- structured events
- per-session runtime evidence bundles

But it still lacked one cumulative operator-facing summary telling, at a
glance:

- current service status
- campaign progress in consecutive days / remaining days
- whether the promotion gate is passed
- which acquisition mode is active
- latest live-capture stats when the run comes from native live websocket

That gap did not break Build-11 logic, but it made repeated real-day collection
harder to monitor safely.

## Fix Applied

### Typed contract

In `src/protocols/shadow_vps_service.py`:

- added `ShadowVpsCampaignSummary`
- added `last_campaign_summary_ref` to service state

### Launcher

In `scripts/run_shadow_vps_service.py`:

- the service now writes `shadow_vps_service.campaign_summary.json`
- it is refreshed after successful daily processing and again at service stop,
  so the persisted summary reflects the final service status
- the summary includes:
  - service loop counters
  - last selected/completed session dates
  - acquisition mode
  - accepted / consecutive_days / remaining_days
  - `promotion_gate_passed`
  - runtime evidence source/summary
  - latest native live capture refs and counts
  - refs to the latest bundle/report/session summary/registry/orchestrator state

### Tests

In `tests/test_protocols/test_shadow_vps_service_launcher.py`:

- multi-day dated-export flow now asserts the campaign summary exists and
  reflects `2` consecutive days / `28` remaining
- native live websocket flow now asserts the campaign summary carries the
  capture summary ref and the latest capture counts

## Validation

- `rtk pytest tests/test_protocols/test_shadow_vps_service_launcher.py -q`
- Result: `5 passed`

- `rtk pytest tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_protocols/test_shadow_live_websocket.py -q`
- Result: `8 passed`

- `rtk pytest tests/test_manifest_registry/test_runtime_surface.py -q`
- Result: `21 passed`

## Honest Conclusion

This lot does not create new Build-11 proof by itself. It improves the
operability and auditability of the repeated real-day campaign:

- one cumulative VPS summary now exists
- it stays coherent with the latest durable runtime bundle
- live-capture-derived campaigns expose their latest capture evidence directly

Build-11 still remains partial until repeated target-environment Shadow days are
actually collected.
