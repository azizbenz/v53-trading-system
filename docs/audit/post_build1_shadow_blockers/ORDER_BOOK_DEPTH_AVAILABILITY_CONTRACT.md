# V5.3 Order Book Depth Availability Contract

Date: `2026-05-02`

## Scope

This contract governs replay/shadow order-book depth availability for execution-impact interpretation.

## Required fields

- `book_depth_available`
- `book_depth_levels`
- `book_depth_source_status`
- `book_depth_snapshot_count`
- `book_depth_event_count`
- `book_depth_missing_count`
- `book_depth_staleness_status`
- `impact_depth_level_used`
- `impact_depth_readiness_status`
- `shadow_extension_required`
- `shadow_extension_reason`
- `minimum_shadow_days_required`
- `shadow_extension_status`

## Allowed book-depth statuses

- `BOOK_DEPTH20_AVAILABLE`
- `BOOK_LIMITED_DEPTH_AVAILABLE`
- `BOOK_TOP_OF_BOOK_ONLY`
- `BOOK_DEPTH_MISSING`
- `BOOK_DEPTH_NOT_PROVEN`
- `BOOK_DEPTH_STALE`

## Allowed impact-depth statuses

- `IMPACT_SOURCE_DEPTH20_MODEL`
- `IMPACT_SOURCE_LIMITED_DEPTH_MODEL`
- `IMPACT_SOURCE_TOP_OF_BOOK_PROXY`
- `IMPACT_SOURCE_SYNTHETIC`
- `IMPACT_SOURCE_MISSING`
- `IMPACT_SOURCE_NOT_PROVEN`

## Normalization rules

- If `book_depth_levels >= 20`, `impact_source_status` may be `IMPACT_SOURCE_DEPTH20_MODEL`.
- If `1 < book_depth_levels < 20`, `impact_source_status` must be `IMPACT_SOURCE_LIMITED_DEPTH_MODEL`.
- If `book_depth_levels == 1`, `impact_source_status` must be `IMPACT_SOURCE_TOP_OF_BOOK_PROXY`.
- If `book_depth_levels == 0` or depth is absent, `impact_source_status` must be `IMPACT_SOURCE_MISSING` or `IMPACT_SOURCE_NOT_PROVEN`.
- Missing depth must not become zero impact.
- Limited depth cannot be labeled depth20.
- Top-of-book proxy cannot be treated as promotion-grade impact proof.
- `cost_model_completeness_status` cannot be `COST_MODEL_COMPLETE` while depth is missing, top-of-book only, limited, stale, or not proven.

## Shadow extension doctrine

- `BOOK_DEPTH20_AVAILABLE`:
  - `impact_depth_readiness_status = DEPTH20_AVAILABLE`
  - `shadow_extension_required = false`
  - `minimum_shadow_days_required = 30`
  - `shadow_extension_status = SHADOW_STANDARD_30D`
- `BOOK_LIMITED_DEPTH_AVAILABLE`:
  - `impact_depth_readiness_status = LIMITED_DEPTH_PARTIAL`
  - `shadow_extension_required = true`
  - `minimum_shadow_days_required = 45` for limited depth such as depth10
  - `minimum_shadow_days_required = 60` for thinner limited depth such as depth5
  - `shadow_extension_status = SHADOW_EXTENDED_45D` or `SHADOW_EXTENDED_60D`
  - `status = LIMITED_DEPTH_VALIDATED_BY_SHADOW` only after later telemetry proof
- `BOOK_TOP_OF_BOOK_ONLY`:
  - `impact_depth_readiness_status = TOP_OF_BOOK_PROXY_ONLY`
  - `shadow_extension_required = true`
  - `minimum_shadow_days_required = 60`
  - `shadow_extension_status = SHADOW_DIAGNOSTIC_ONLY`
  - `MICRO_LIVE_BLOCKED_BY_DEPTH` by default
- `BOOK_DEPTH_MISSING` or `BOOK_DEPTH_NOT_PROVEN`:
  - no promotion-grade replay impact proof
  - no micro-live promotion from replay alone
  - `shadow_extension_status = MICRO_LIVE_BLOCKED_BY_DEPTH`

## Required statuses

- `SHADOW_STANDARD_30D`
- `SHADOW_EXTENDED_45D`
- `SHADOW_EXTENDED_60D`
- `SHADOW_DIAGNOSTIC_ONLY`
- `MICRO_LIVE_BLOCKED_BY_DEPTH`
- `LIMITED_DEPTH_VALIDATED_BY_SHADOW`

## Current implementation note

The current replay rail normalizes and exports these statuses additively. It does not claim that limited depth, top-of-book, or missing depth is promotion-grade by replay alone.
