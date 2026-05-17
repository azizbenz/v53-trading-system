# Wave 4 Remaining Microstructure Gaps

Superseded in part by the gap-closure patch. See `WAVE4_REMAINING_POST_GAP_CLOSURE_ITEMS.md` for the current post-normalization remainder.

These gaps remained explicit immediately after the semantic-safety patch.

## Remaining gaps

- normalized Kyle lambda bps/notional seam
- normalized OFI or depth-adjusted OFI seam
- formal calibration note for wall/spoofing heuristics
- empirical threshold calibration for VPIN / Kyle / OFI per pair
- governed runtime-consumer decision for Amihud / Roll / Corwin-Schultz / Hawkes / PIN
- stronger module-boundary isolation for dataset-builder directional labels if product doctrine later requires it
- stronger cockpit separation between artifact-present and runtime-consumed across every downstream page

## Why they remain open

- No new estimator normalization seam was introduced in this patch.
- No new calibration artifact was introduced in this patch.
- No new runtime consumer wiring was forced for research-only estimators.
- No strategy logic was changed.

## Safe current interpretation

- Kyle lambda is engine-local and unnormalized.
- OFI is raw signed-size imbalance under engine-local thresholds.
- Queue pressure can be insufficient-depth, not safely neutral.
- Walls/spoofing are heuristic context, not a calibrated production detector.
- Runtime regime outputs are non-directional only.
- Training labels stay local-lab-only.
