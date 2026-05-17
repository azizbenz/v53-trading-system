# V5.3 Fill Realism Contract

Date: `2026-05-02`

## Scope

This contract governs replay/shadow fill-realism evidence and prevents synthetic or model-only fills from being shown as measured fills.

## Required fields

- `fill_realism_status`
- `fill_source_status`
- `fill_model_name`
- `fill_model_version`
- `fill_ratio_expected`
- `fill_ratio_observed`
- `partial_fill_rate_expected`
- `partial_fill_rate_observed`
- `no_fill_rate_expected`
- `no_fill_rate_observed`
- `fill_latency_ms_expected`
- `fill_latency_ms_observed`
- `synthetic_fill_flag`
- `measured_fill_flag`
- `fill_provenance_ref`
- `fill_input_hash`
- `fill_policy_version`

## Allowed statuses

- `FILL_REALISM_PROVEN`
- `FILL_REALISM_SHADOW_MEASURED`
- `FILL_REALISM_SYNTHETIC_ONLY`
- `FILL_REALISM_MODEL_ONLY`
- `FILL_REALISM_PARTIAL`
- `FILL_REALISM_NOT_PROVEN`
- `FILL_REALISM_MISSING`

## Rules

- Synthetic fill must not be presented as measured fill.
- Model-only fill must remain non-green for promotion-grade economics.
- Measured fill requires explicit replay artifact provenance or shadow/live telemetry provenance.
- Missing fill data must not be treated as full fill.
- No-fill and partial-fill must remain first-class outcomes.
- `fill_realism_status` blocks promotion readiness unless it is `FILL_REALISM_PROVEN` or `FILL_REALISM_SHADOW_MEASURED`, or later human doctrine explicitly accepts a weaker status.

## Current implementation note

The current replay rail exports model-only fill realism conservatively by default:

- `fill_realism_status = FILL_REALISM_MODEL_ONLY`
- `fill_source_status = FILL_SOURCE_REPLAY_MODEL`
- observed fill fields remain empty unless later measured telemetry is supplied

This hardens the rail without claiming measured fill proof that does not yet exist.
