# V5.3 SB-005 / SB-006 Fill Realism, Cost Parity, and Depth Patch Report

Date: `2026-05-02`

## Scope

This patch hardens three execution-realism seams:

- order-book depth availability
- fill-realism provenance/status
- replay/live cost parity status

It does not claim measured fill proof or telemetry-backed replay/live parity.

## What changed

- Added governed replay/shadow depth-availability contract fields and normalization.
- Added explicit limited-depth, top-of-book-only, missing-depth, and stale-depth statuses.
- Added shadow-extension doctrine carriage:
  - `SHADOW_STANDARD_30D`
  - `SHADOW_EXTENDED_45D`
  - `SHADOW_EXTENDED_60D`
  - `SHADOW_DIAGNOSTIC_ONLY`
  - `MICRO_LIVE_BLOCKED_BY_DEPTH`
- Added explicit fill-realism evidence carriage with model-only vs measured separation.
- Added explicit replay/live cost-parity evidence carriage with telemetry-blocked default.
- Updated replay review markdown and exported replay metrics payloads.
- Updated cockpit replay/system-flow/economic-sterilization surfaces to show non-green depth/fill/parity states.

## What did not change

- No engine logic rewrite.
- No side logic change.
- No fake depth20.
- No measured fill invention.
- No replay/live parity promotion without telemetry.
- `expected_ce_net` remains expected-only.
- `drawdown_proxy` remains diagnostic-only.

## Runtime doctrine now enforced

- No depth20: no promotion-grade impact proof by replay alone.
- Limited depth: extended shadow.
- Top-of-book only: diagnostic shadow, micro-live blocked by default.
- No book: no promotion-grade replay impact.
- Model-only or synthetic fill cannot be displayed as measured fill.
- Replay/live cost parity cannot be shown as proven without telemetry.

## Validation

- Focused targeted band: `39 passed`
- Broad execution/local-replay/backtest-artifact-import/cockpit band: `561 passed`
- Broad risk/scoring band: `389 passed`

## Current blocker outcome

- `SB-005 fill realism`: hardened to explicit non-green status carriage, but still telemetry-dependent
- `SB-006 replay/live cost parity`: hardened to explicit non-green status carriage, but still telemetry-dependent

Result: blocker semantics are closed; telemetry-backed proof remains open.
