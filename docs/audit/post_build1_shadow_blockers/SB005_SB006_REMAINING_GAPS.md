# V5.3 SB-005 / SB-006 Remaining Gaps

Date: `2026-05-02`

## Still open

- Measured shadow/live fill telemetry proving `FILL_REALISM_PROVEN` or `FILL_REALISM_SHADOW_MEASURED`
- Empirical fill calibration beyond replay model-only expectations
- Telemetry-backed `REPLAY_SHADOW_COST_PARITY_PROVEN` or `REPLAY_LIVE_COST_PARITY_PROVEN`
- Replay/live parity drift evidence by named cost component
- Human doctrine, if any, for when limited depth could ever be promotion-grade

## Current safe state

- Missing depth cannot collapse to zero impact.
- Limited depth cannot masquerade as depth20.
- Top-of-book proxy cannot masquerade as promotion-grade impact.
- Model-only fill cannot masquerade as measured fill.
- Replay/live parity cannot masquerade as proven without telemetry.
- Cockpit surfaces remain non-green while these gaps remain open.

## Status classification

- `SB-005`: `PARTIAL`
- `SB-006`: `PARTIAL`
- `BLK-002`: still telemetry-blocked for measured fill proof
- `W3-OPEN-006`: still telemetry-blocked for parity proof
