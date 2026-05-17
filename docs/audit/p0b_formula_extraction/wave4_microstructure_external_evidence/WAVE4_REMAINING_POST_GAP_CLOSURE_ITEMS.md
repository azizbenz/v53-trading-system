# Wave 4 Remaining Post Gap Closure Items

## Remaining gaps

- pair-level empirical calibration artifacts are still absent
- optional OFI pair-zscore seam is still not implemented because rolling pair statistics are not governed yet
- normalized Kyle uses a configured standard notional but is still not wired into any engine decision path
- normalized OFI is available for calibration/context, not wired into engine decision paths
- walls/spoofing remains heuristic until empirical validation exists
- runtime consumer promotion decisions for Amihud / Corwin-Schultz / Hawkes / PIN remain intentionally conservative
- Roll fallback doctrine is recorded, but no broader fallback-governance artifact exists yet
- cockpit separation is stronger on feature-bridge surfaces than on every possible downstream analytics page

## Safe current interpretation

- raw estimator consumers remain unchanged
- normalized seams are additive only
- research-only and future-reserved estimators remain non-runtime-active
- no new strategy or side behavior was introduced
