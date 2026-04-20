# 2026-04-19 — Shadow VPS service graceful signal shutdown

## Docs Governants

- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`

## Current Code Seam

- launcher: `scripts/run_shadow_vps_service.py`
- runtime loop: `scripts/shadow_vps_service_runtime_support.py`
- targeted proof: `tests/test_protocols/test_shadow_vps_service_signal_shutdown.py`

## Files Changed

- `scripts/run_shadow_vps_service.py`
- `scripts/shadow_vps_service_runtime_support.py`
- `tests/test_protocols/test_shadow_vps_service_signal_shutdown.py`

## Claims Implemented

- `SIGINT` / `SIGTERM` now request a graceful stop instead of relying on abrupt interruption.
- The stop request is injected into the canonical main loop as a flag, not as a new runtime architecture.
- A stable `service_stop_requested` event is emitted before canonical finalization.
- Finalization remains canonical: `service_stopped` still comes from the existing finalizer.
- No trade, shadow-day, or promotion logic changed.

## Tests and Proof

- `rtk pytest -q tests/test_protocols/test_shadow_vps_service_signal_shutdown.py` -> `3 passed`
- `PYTHONPYCACHEPREFIX=.test_tmp/pycache python -m py_compile scripts/run_shadow_vps_service.py scripts/shadow_vps_service_runtime_support.py tests/test_protocols/test_shadow_vps_service_signal_shutdown.py` -> pass
- `python scripts/run_engineering_guardrails.py` -> `new_violations=0`

## Deferred / Not Done

- The broad historical suite `tests/test_protocols/test_shadow_vps_service_launcher.py` was not used as proof for this slice.
- Reason: in this environment, that suite’s own scratch helper writes under `build/shadow_vps_service_tests` and fails with permission errors before reaching the launcher assertions.
- No change was made to that legacy test helper in this slice.

## Completion Status

`DONE`

## Next Safe Step

Either:
- extend graceful stop semantics to any other true long-running launcher surfaces, or
- move to the next production-safe gap: governed testnet integration on the Binance spot adapter / execution bootstrap rail.
