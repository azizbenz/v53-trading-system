# 00 TRIAGE SUMMARY

## Evidence base
- Source discovery inputs:
  - `docs/cockpit/PAGE_SOURCE_DISCOVERY_MATRIX.md`
  - `docs/cockpit/PAGE_METRIC_OWNERSHIP_MATRIX.md`
  - `docs/cockpit/PAGE_FORMULA_SOURCE_LEDGER.md`
  - `docs/cockpit/PAGE_MISSING_SOURCE_BACKLOG.md`
  - `docs/cockpit/FILE_SOURCE_LEDGER.md`
  - `docs/cockpit/PAGE_DUPLICATION_AUDIT.md`
- Discovery totals already produced:
  - 8 real cockpit surfaces
  - 792 production files inventoried
  - 496 formula-ledger rows
  - 458 missing/backlog rows
  - 139 duplication rows

## Package stance
- This package does **not** treat `orphan_candidate` as unused code.
- This package does **not** treat `CODE_FORMULA_FOUND` as "real quant formula" by default.
- This package compresses the discovery into:
  - P0 orphan/import-graph resolution
  - real formula isolation
  - false-green cockpit risks
  - backtest/replay/calibration display gaps
  - VPS/Shadow control-proof ownership gaps
  - patch order

## Compact findings
### P0 findings
1. The biggest unexposed dashboard inventory is **Backtest/Replay/Calibration**:
   - `src/local_replay_runtime/*` -> 61 files
   - `src/calibration_methods/*` -> 21 files
   - `src/backtest_artifact_import/*` -> 16 files
   - all already coded, mostly `coded_not_displayed` or `runtime_only`
2. The **engine codebase** is materially underrepresented in cockpit display:
   - `src/engines/*` -> 64 files
   - owner candidate = Trading
   - current cockpit shows engine status, but not engine-source ownership depth
3. **VPS/Shadow control proof** is duplicated across `overview`, `shadow`, `vps`, and sometimes `lab`:
   - `operational_proof.service_liveness.*`
   - `operational_proof.queue_trace.*`
   - this creates a high false-green risk if one copy drifts from the owner page
4. The current formula ledger is noisy:
   - many `Field(default=0.0, ...)`
   - many boolean/status flags
   - many text/list builders
   - many zero placeholders like `ce_net = 0.0`
   - therefore the raw ledger is not safe for human quant review without reclassification

### P1 findings
1. `Overview` still carries too many deep-domain duplicates from:
   - `lab_review.*`
   - `model_risk.*`
   - `refusal_journal.*`
   - `feature_bridge.*`
   - `calibration.*`
2. `Trading` still carries non-owner duplication for calibration and feature lineage reminders that should be collapsed.
3. `IA Lab` still mixes true source-status, review state, and placeholder persistence states too loosely.

## Reclassified formula counts
This package reclassifies the 496 raw formula rows into:
- `REAL_QUANT_FORMULA`: 64
- `OPERATIONAL_DIAGNOSTIC`: 2
- `THRESHOLD_CONSTANT`: 171
- `PYDANTIC_FIELD`: 59
- `STATUS_FLAG`: 45
- `REPORT_VALUE`: 11
- `TEXT_OR_LIST`: 31
- `FALSE_POSITIVE`: 113

## Required reading order
1. `01_P0_ORPHAN_RESOLUTION_QUEUE.md`
2. `02_REAL_QUANT_FORMULAS_ONLY.md`
3. `03_COCKPIT_FALSE_GREEN_RISKS.md`
4. `04_BACKTEST_REPLAY_CALIBRATION_GAPS.md`
5. `05_VPS_SHADOW_CONTROL_PROOF_GAPS.md`
6. `06_DASHBOARD_DUPLICATION_COLLAPSE_PLAN.md`
7. `07_NEXT_PATCH_ORDER.md`

## Completion status
`TRIAGE_PACKAGE_READY`
