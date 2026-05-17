# V5.3 Patch 4 Remaining Capital Ladder Gaps

Date: `2026-05-02`

## Still open after Patch 4

- Measured backtest/replay capital-bucket viability artifacts are still absent for `400`, `500`, `1500`, and `4000`.
- Proven `allowed_pairs` and `max_active_pairs` are still absent for promoted buckets.
- Live free-balance sourcing for governed bucket selection is still not proven.
- Full VPS/runtime integration of capital-profile enforcement is still not proven end to end.
- Sample-size survival remains unproven at the capital-bucket layer.
- Depth / fill-realism / cost-parity partial states still block promotion-grade bucket readiness.
- Pair-level negative executed-return and drawdown evidence is still not being produced as measured bucket artifacts.

## Current correct interpretation

- The capital-profile rail exists.
- The artifact generator exists.
- The replay/cockpit non-green gating exists.
- The min-notional and fragmentation helpers exist.

What does not exist yet:

- measured bucket promotion
- proven small-capital pair universes
- full micro-live/live enforcement proof through the VPS runtime

## Required next steps

1. Run Backtest Strategy Ladder scenarios for `400 / 500 / 1500 / 4000`.
2. Produce measured per-bucket artifacts with governed hashes and freshness.
3. Feed measured profiles into replay/shadow review.
4. Prove VPS/runtime no-submit enforcement on the promoted bucket artifacts.
5. Keep cockpit states non-green until steps 1-4 are complete.
