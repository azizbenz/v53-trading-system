# V5.3 Patch 4 Capital Ladder / Capital Profile Patch Report

Date: `2026-05-02`

## Scope

This patch hardens four related seams:

- capital bucket viability contracts
- per-bucket capital profile artifact generation
- min-notional and fragmentation evidence carriage
- cockpit false-green prevention for capital readiness

It does not invent measured backtest or replay results.

## What changed

- Added typed capital-profile contracts for `400`, `500`, `1500`, and `4000`.
- Added deterministic capital-profile artifact hashing.
- Added a governed capital-profile builder and JSON writer for `capital_profiles/{bucket}.json`.
- Added contract-validation `NOT_PROVEN` profiles so the artifact rail can be validated without faking measured results.
- Added fail-closed validation and enforcement helpers for:
  - missing profile
  - stale profile
  - hash-invalid profile
  - lower-proven-bucket selection
  - `allowed_pairs`
  - `blocked_pairs`
  - `max_active_pairs`
- Added min-notional viability assessment with explicit reason codes.
- Added fragmentation analysis with explicit `PAIR_UNIVERSE_TOO_WIDE_FOR_CAPITAL` semantics.
- Added replay export carriage for capital profiles and supplementary refs discovery.
- Added cockpit replay / economic-sterilization / system-flow gating so missing capital-profile evidence stays non-green.

## What did not change

- No engine logic rewrite.
- No strategy logic rewrite.
- No side logic change.
- No leverage or shorting.
- No fake `allowed_pairs`.
- No fake execution rates, returns, or drawdowns.
- No claim that any bucket is promotion-ready without measured evidence.

## Runtime doctrine now enforced

- `expected_ce_net` remains expected-only.
- `drawdown_proxy` remains diagnostic-only.
- Contract-only profiles default to `CAPITAL_BUCKET_NOT_PROVEN`.
- Non-ready buckets must not keep `allowed_pairs` populated.
- Static config pair lists do not override governed `allowed_pairs`.
- `MICRO_LIVE` and `LIVE` must fail closed on missing, stale, hash-invalid, or non-proven profiles when the enforcement helper is used.
- Replay and cockpit do not render promotion-grade economics while capital-profile artifacts remain unproven.

## Validation

- Targeted capital-profile/cockpit band: `68 passed`
- Broad portfolio/execution/local-replay/backtest-artifact-import/cockpit band: `676 passed`
- Broad risk/scoring band: `389 passed`

## Current blocker outcome

- `SB-008 capital bucket viability`: hardened to explicit contracts, artifacts, and non-green status carriage, but still lacks measured backtest/replay bucket evidence
- `MLB-002 capital profile enforcement`: helper exists and is tested, but full VPS/runtime integration proof is still not claimed
- `MLB-003 min-notional viability awareness`: helper exists and is tested, but full sizing-rail integration is still not claimed
- `MLB-004 capital fragmentation`: analysis logic exists and is tested, but measured per-bucket artifacts are still absent

Result: pipeline and fail-closed semantics are implemented; measured capital readiness remains open.

