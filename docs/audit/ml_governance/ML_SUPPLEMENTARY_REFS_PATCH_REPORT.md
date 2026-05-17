# ML Supplementary Refs Patch Report

## Files modified
- `src/complete_enablers/__init__.py`
- `src/complete_enablers/ml_confidence_enabler.py`
- `src/complete_enablers/regime_detector_runtime.py`
- `src/complete_enablers/supplementary_refs_governance.py`
- `src/scoring_backbone/scoring_runtime_support.py`
- `src/engines/engine_a/engine_a_runtime.py`
- `src/engines/engine_a/engine_a_scoring_candidate_builder.py`
- `src/engines/engine_b/engine_b_runtime.py`
- `src/engines/engine_b/engine_b_runtime_support.py`
- `src/engines/engine_c/engine_c_runtime.py`
- `src/engines/engine_c/engine_c_runtime_support.py`
- `src/engines/engine_d/engine_d_runtime.py`
- `src/engines/engine_d/engine_d_runtime_support.py`

## What changed
- Added a shared governance validator for supplementary refs
- Added explicit directional-ref rejection for ML and regime loaders
- Added scoring carriage metadata for ML/risk/scoring audit labels
- Added `supplementary_refs` transport fields to engine runtime inputs
- Carried `supplementary_refs` into `ScoringCandidateInput`

## What did not change
- No engine signal formulas
- No side logic
- No order direction creation
- No cockpit templates
- No calibration formulas

## Engine status
- Engine A:
  - can carry `supplementary_refs`
  - defaults to neutral if no governed refs are passed
- Engine B:
  - can carry `supplementary_refs`
  - defaults to neutral if no governed refs are passed
- Engine C:
  - can carry `supplementary_refs`
  - remains partial in shared scoring physics
- Engine D:
  - can carry `supplementary_refs`
  - remains partial in shared scoring physics

## Current limitation
- The transport rail is now present and governed
- The current production runtime path does not yet prove a non-empty live upstream source for all engines
- Therefore the default live state remains explicit neutral unless a governed source passes refs

## Safety result
- `supplementary_refs` cannot mutate side
- directional keys are rejected
- direct ML override stays forbidden
- no short or leverage route is introduced
