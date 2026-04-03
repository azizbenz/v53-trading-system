# 2026-04-03 - Build-11 VPS Live Capture Evidence Enrichment Audit

## Scope

Strengthen the durable proof emitted by the autonomous VPS Shadow service after
the bounded native `live_websocket` smoke. The goal of this lot is not to
change Build-11 gates, but to make the persisted runtime evidence chain more
audit-ready by carrying the live capture summary itself.

## Gap Before Fix

The VPS service already persisted:

- the Shadow orchestrator refs
- the Shadow runtime evidence ref
- the final durable runtime evidence bundle

But the service-level durable bundle did not explicitly carry the native live
capture summary path and counts:

- emitted / accepted / ignored / rejected message counts
- pair scope
- event types

That made the Build-11 target-environment story weaker than necessary, because
the durable bundle proved the downstream Shadow chain better than the upstream
native capture facts.

## Fix Applied

### Typed contracts

In `src/protocols/shadow_vps_service.py`:

- `ShadowVpsServiceState` now persists:
  - `last_live_capture_snapshot_batch_ref`
  - `last_live_capture_summary_ref`
- `ShadowVpsRuntimeEvidenceBundle` now persists:
  - `live_capture_snapshot_batch_ref`
  - `live_capture_summary_ref`
  - `live_capture_emitted_message_count`
  - `live_capture_accepted_message_count`
  - `live_capture_ignored_message_count`
  - `live_capture_rejected_message_count`
  - `live_capture_pair_scope`
  - `live_capture_event_types`
- `ShadowVpsServiceEvent` now supports structured live-capture fields so the
  `live_capture_completed` event remains audit-ready, not message-only.

### Service launcher

In `scripts/run_shadow_vps_service.py`:

- the service now reconstructs a typed `ShadowLiveWebSocketCaptureResult`
  directly from the persisted native capture summary + snapshot paths
- the durable runtime evidence bundle now carries those capture facts
- the service state keeps the latest capture summary refs
- the `live_capture_completed` event now carries structured counts and scopes

## Validation

### Focused VPS live-capture surface

- `rtk pytest tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
- Result: `7 passed`

### Build-11 adjacent launcher surface

- `rtk pytest tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_protocols/test_shadow_live_websocket.py -q`
- Result: `8 passed`

### Slightly broader protocol/runtime surface

- `rtk pytest tests/test_protocols/test_shadow_daily_orchestrator.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_protocols/test_shadow_live_websocket.py -q`
- Result: `10 passed`

### Runtime export sanity

- `rtk pytest tests/test_manifest_registry/test_runtime_surface.py -q`
- Result: `21 passed`

## Honest Conclusion

This lot improves the quality of the Build-11 operational evidence chain:

- the bounded native live capture is now represented more fully in the durable
  VPS service bundle
- the service state and structured events now preserve capture facts alongside
  the downstream Shadow facts

This does **not** close Build-11. It only makes the target-environment proof
chain more honest and easier to audit while repeated real Shadow-day collection
continues.
