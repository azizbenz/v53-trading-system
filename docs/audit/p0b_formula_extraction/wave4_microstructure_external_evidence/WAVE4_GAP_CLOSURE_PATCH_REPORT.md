# Wave 4 Gap Closure Patch Report

## Files modified

- `src/data_backbone/microstructure/kyle_lambda.py`
- `src/data_backbone/microstructure/order_flow_imbalance.py`
- `src/data_backbone/microstructure/feature_registry.py`
- `src/data_backbone/microstructure/__init__.py`
- `src/cockpit/state_feature_bridge.py`
- `src/cockpit/templates/partials/_feature_bridge.html`
- targeted tests
- gap-closure docs

## Normalized Kyle status

Closed additively.

- raw Kyle formula unchanged
- added `normalized_kyle_impact_bps_for_standard_notional`
- added supporting metadata:
  - `raw_kyle_lambda`
  - `reference_mid_price`
  - `standard_quote_notional`
  - `normalized_unit_status`
  - `normalized_cross_pair_comparable`
- raw seam remains non-comparable across pairs
- normalized seam is the only comparable seam

## Normalized OFI status

Closed additively.

- raw OFI formula unchanged
- added `ofi_depth_adjusted`
- added supporting metadata:
  - `raw_ofi`
  - `top_k_bid_depth`
  - `top_k_ask_depth`
  - `depth_adjusted_unit_status`
  - `depth_adjusted_cross_pair_comparable`
  - `depth_adjustment_status`
- zero depth now yields explicit insufficient-depth status

## Walls/spoofing calibration-note status

Closed in documentation.

- created `WALLS_SPOOFING_CALIBRATION_NOTE.md`
- current heuristic weights and limitations are explicit
- calibration requirement remains explicit

## Threshold calibration artifact spec status

Closed in documentation.

- created `MICROSTRUCTURE_THRESHOLD_CALIBRATION_SPEC.md`
- no thresholds were invented
- pair/regime artifact contract is defined for later calibration work

## Runtime-consumer registry decisions

Closed in metadata.

Registry now distinguishes lifecycle from raw consumer path:
- OFI: `ACTIVE_ENGINE_INPUT`
- VPIN: `ACTIVE_ENGINE_INPUT`
- raw Kyle: `ACTIVE_ENGINE_INPUT`
- realized kernel: `ACTIVE_ENGINE_INPUT`
- queue pressure: `ACTIVE_ENGINE_INPUT`
- walls/spoofing family: `ACTIVE_RUNTIME`
- realized effective spread: `ACTIVE_EXECUTION_GATE`
- Amihud: `RESEARCH_ONLY`
- Roll: `FALLBACK_ONLY`
- Corwin-Schultz: `RESEARCH_ONLY`
- Hawkes: `FUTURE_RESERVED`
- PIN: `FUTURE_RESERVED`

Intent notes were added where needed:
- `PAIR_LIQUIDITY_REPORT`
- `MISSING_L2_SPREAD_FALLBACK`
- `OHLC_FALLBACK`
- `ENGINE_C_INTENSITY_RESEARCH`
- `OFFLINE_PARAMETER_SEAM`

## Cockpit downstream separation status

Improved.

- feature bridge still distinguishes artifact presence from runtime proof
- family rows now show runtime lifecycle and registry intent
- research-only and future-reserved families stay non-runtime-active
- system flow continues to stay yellow when only artifact proof exists

## Tests run

- targeted microstructure normalization/status band
- targeted Engine C / D and regime runtime band
- broad requested microstructure + cockpit band

## Remaining gaps

See `WAVE4_REMAINING_POST_GAP_CLOSURE_ITEMS.md`.
