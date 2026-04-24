## 2026-04-23 — RegimeDetector Feature Schema V2

### Repo-truth
- `walls_and_spoofing.py` now exposes dual persistence diagnostics:
  - `wall_persistence_conditional_bid`
  - `wall_persistence_conditional_ask`
  - `observation_coverage_ratio`
- `lob_regime_features.py` now supports explicit feature schema versions:
  - `lob_regime_feature_set.v1`
  - `lob_regime_feature_set.v2`
- canonical new training/runtime schema is:
  - `lob_regime_feature_set.v2`

### V1 vs V2
- `V1` remains backward-compatible and excludes:
  - `wall_persistence_conditional_bid`
  - `wall_persistence_conditional_ask`
  - `observation_coverage_ratio`
- `V2` includes all `V1` fields plus the three observation-quality diagnostics above.

### Governance decision
- `LobRegimeFeatureSnapshot.as_feature_map()` remains backward-compatible `V1`.
- all new ML consumption paths must request schema explicitly through:
  - `as_feature_map_for_version(feature_set_version)`
- this avoids silent drift in:
  - `feature_names`
  - `feature_hash`
  - Local IA Lab artifacts
  - VPS runtime compatibility

### End-to-end changes
- dataset builder emits `feature_set_version=lob_regime_feature_set.v2`
- trainer rows preserve `feature_set_version`
- RegimeDetector artifacts now carry:
  - `feature_set_version`
  - `feature_hash`
- transport summaries now carry:
  - `feature_set_version`
- runtime loader fail-closes on:
  - summary/artifact `feature_set_version` mismatch
  - summary/artifact `feature_hash` mismatch
- VPS runtime resolves the feature map using the artifact's explicit `feature_set_version`

### Invariants preserved
- no directional label added
- no VPS training
- no side mutation
- no A/B/C/D modification
- no quant-anchor modification

### Next constraint
- if future `V3` adds more microstructure observation features, it must repeat the same governed path:
  - snapshot versioning
  - dataset versioning
  - artifact versioning
  - transport summary versioning
  - runtime fail-closed compatibility checks
