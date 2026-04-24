# IA Lab Governed Repo-Truth Closure - 2026-04-22

## Scope
- Freeze the current repo-truth status of the governed IA Lab rail only.
- This note does **not** claim that V5.3 already has a classical ML training lab.
- This note does **not** reopen the quant APIs or the VPS live path.

## Canonical claim
- The governed IA Lab rail is now closed strongly enough to be treated as a real repo-truth subsystem:
  - `backtest_artifact_import`
  - `calibration_loader`
  - `local_replay_runtime`
  - `meta_learning`
- The closure is the governed loop:
  - replay export
  - import/build bridge
  - calibration artifact load
  - local replay review/export
  - meta-learning review bundle
  - release candidate / dry-run shadow import bridge

## What changed since the older IA Lab slices note
- The old red fronts called out in `2026-04-21_ia_lab_slices_0_to_5.md` are no longer red for the governed IA Lab scope:
  - `tests/test_backtest_artifact_import/test_export_dir_bridge.py`
  - `tests/test_calibration_loader/test_loader.py`
  - `tests/test_local_replay_runtime/*`
- The quant residual slice `B/B/B/B` is also closed at the seam-proof level without widening public APIs.

## Proof bundle

### Package bundle proof
- Command:
  - `rtk pytest tests/test_backtest_artifact_import tests/test_calibration_loader tests/test_local_replay_runtime tests/test_meta_learning -q --tb=short --basetemp=.test_tmp/pytest_ia_lab_bundle`
- Result:
  - `357 passed`

### High-level governed analysis bundle proof
- Command:
  - `rtk pytest tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q --tb=short --basetemp=.test_tmp/pytest_local_lab_analysis_bundle`
- Result:
  - `7 passed`
- Why this matters:
  - This launcher suite already provides the single high-level governed proof path.
  - It proves dry-run shadow import readiness on the Local IA Lab sidecar rail without bypassing typed contracts.
  - It also proves the opposite blocked paths in the same launcher family.

### Quant seam closure proof
- Companion notes:
  - `2026-04-22_quant_anchor_closure_b_repo_truth.md`
  - `2026-04-22_quant_anchor_residues_doctrinal_answers_addendum.md`
- Meaning:
  - PSR, DSR, POT-GPD, and Energy are now closed by seam-proof `B/B/B/B`, not by API widening or external datasets.

## Repo-truth reading

### What is complete
- Governed replay/export/import/calibration/review packaging is green enough to count as a closed local subsystem.
- The canonical integrated proof already exists in test space; no duplicate proof rail is required.
- The Local IA Lab -> dry-run shadow candidate path is proven through the existing launcher suite.

### What is not being claimed
- This does **not** mean that IA Lab is a classical ML lab with explicit `sklearn` / `xgboost` / `torch` training surfaces.
- This does **not** mean that the VPS live path depends on Local IA Lab.
- This does **not** authorize opening a new top-level ML architecture now.

## Status
- Governed IA Lab: `COMPLETE_REPO_TRUTH`
- Classical ML layer: `NOT_OPENED_BY_DESIGN`
- Quant seam closure: `COMPLETE_AT_CURRENT_API_SEAMS`

## Correction to planning doctrine
- `2026-04-21_codex_5day_coding_plan_sprint32.md` is no longer the right direct pilot for IA Lab work.
- That sprint plan is broader and oriented toward pre-`MICRO_LIVE` system work.
- For IA Lab specifically, the current pilot truth is:
  - governed local subsystem closed
  - quant seam residuals closed by `B/B/B/B`
  - next strategic layer, if opened later, is offline bounded ML only

## Next honest step
- Do **not** reopen another IA Lab closure slice just to duplicate proofs.
- Keep the current governed IA Lab rail stable.
- If the project wants more capability after this point, the next explicit decision is whether to open a bounded offline ML layer on top of this closed governed base.
