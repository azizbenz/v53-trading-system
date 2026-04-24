## 2026-04-23 — RegimeDetector feature profiles V1

### Repo-truth
- Feature Schema V2 is now available and versioned end-to-end.
- The next governed decision is not "add more columns".
- The next governed decision is: which subset of the schema does Local IA Lab train by default?

### Implemented decision
- A dedicated calibration seam now exists for RegimeDetector feature profiles.
- Supported profiles:
  - `core_v1`
  - `extended_v2`
  - `full_v2`

### Semantics
- `core_v1`
  - bounded, compressed profile
  - base regime context + compact walls/spoofing signals
- `extended_v2`
  - default Local IA Lab training profile
  - includes the V2 observation-quality metrics:
    - `wall_persistence_conditional_bid`
    - `wall_persistence_conditional_ask`
    - `observation_coverage_ratio`
- `full_v2`
  - full snapshot schema
  - kept available for ablation/research, not forced as the default training path

### Consumption path
- dataset builder emits full governed schema `lob_regime_feature_set.v2`
- projection layer can now select:
  - explicit `selected_feature_names`
  - or an explicit `feature_profile`
- Local IA Lab helper now trains the RegimeDetector with an explicit feature profile
- default Local IA Lab profile is:
  - `extended_v2`

### Governance preserved
- no directional semantics added
- no VPS training
- no A/B/C/D modification
- no quant-anchor modification
- runtime remains artifact-only

### Audit note
- the trainer now preserves the explicit profile ordering in `artifact.feature_names`
- the profile choice is visible in the Local IA Lab training report
- the artifact still remains governed by:
  - `feature_set_version`
  - `feature_names`
  - `feature_hash`
