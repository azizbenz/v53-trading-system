# V5.3 — Codex Execution Prompt

## Slice

**Gap Closure Slice A — Execution Fidelity + Gap Register Synchronization**

**Date:** 2026-05-09  
**Target repo:** `v53_trading_system`  
**Runtime mode:** `LOCAL_REPLAY`  
**Priority:** P0/P1 before stronger Shadow-readiness claims  
**Do not treat this as a new architecture. This is a surgical convergence slice.**

---

# 0. Opening Context for Codex

You are working on **V5.3 Gap Closure Slice A — Execution Fidelity and Gap Register Synchronization**.

MemPalace policy:
- Perform the MemPalace check first.
- State whether project memory was found for `v53_trading_system`.
- Current codebase remains the source of truth.
- Do not use memory as a replacement for reading files you modify.

Global invariants:
- One shared V5.3 codebase.
- No new runtime profile.
- Use `runtime_mode=LOCAL_REPLAY`.
- No bypass of Shadow / Micro-live / Live promotion gates.
- No live venue side effects in replay.
- No import of `venue_adapters` into replay.
- No import of live `protocols` transport concerns into replay.
- No new engine outside A/B/C/D.
- Build-14 remains additive and bounded.
- ML remains non-sovereign and non-positive.
- No promotion-grade claim without evidence.
- No false-green cockpit state.
- No second canon.
- No broad rewrite.

Current state:
- Lot 0 realigned the declared DAG and removed invalid `cockpit -> local_replay_runtime` and `local_replay_runtime <-> backtest_artifact_import` couplings.
- Lot 1 added a typed replay execution seam while keeping `shadow_execution_simulator` as the default provider.
- Lot 2 added partial canonical execution convergence via `execution_runtime_projection_path`, THR-X04 spread guard, and THR-X05 slippage model.
- Lot 3 added bounded Build-14 / `complete_enablers` provenance for Engine C/D replay.

Mission:
- Close patchable P1 execution-realism gaps.
- Add a stronger execution-fidelity matrix to replay artifacts.
- Prevent replay/ML artifacts from claiming full canonical labels while execution is still partial or proxy.
- Synchronize `P0B_FINAL_GAP_REGISTER.md` with Lots 0–3 and this slice without falsely resolving data-blocked gaps.

---

# 1. Source of Truth Files to Read First

Read these before editing:

```text
P0B_FINAL_GAP_REGISTER.md
src/local_replay_runtime/replay_execution_contracts.py
src/local_replay_runtime/replay_execution_runtime.py
src/local_replay_runtime/replay_execution_projection_loader.py
src/local_replay_runtime/shadow_execution_simulator.py
src/local_replay_runtime/strategy_ladder_detailed_replay.py
src/local_replay_runtime/strategy_ladder_runner.py
src/local_replay_runtime/strategy_ladder_models.py
src/local_replay_runtime/ml_backtest_projection.py
src/local_replay_runtime/local_lab_ml_artifact_training.py
src/cockpit/state_replay_metrics.py
src/cockpit/state_system_flow.py
src/cockpit/state_economic_sterilization.py
src/manifest_registry/dependency_registry.py
```

Also inspect related tests before editing:

```text
tests/test_local_replay_runtime/test_replay_execution_runtime.py
tests/test_local_replay_runtime/test_shadow_execution_simulator.py
tests/test_local_replay_runtime/test_strategy_ladder_runner.py
tests/cockpit/test_state_replay_metrics.py
tests/cockpit/test_state_system_flow.py
tests/cockpit/test_state_economic_sterilization.py
tests/test_manifest_registry/test_dependencies.py
```

If file names differ in the current repo, locate the nearest equivalent by grep, but do not invent new broad packages.

---

# 2. Target Gaps

Primary register gaps to update or progress:

```text
W3-OPEN-001 — Replay fee provenance is explicit, but promotion-grade replay fee input is not proven.
W3-OPEN-002 — Replay impact provenance is explicit and depth-aware, but promotion-grade replay impact is not proven.
W3-OPEN-003 — Fill realism carries model-only vs measured statuses, but measured-vs-synthetic proof is absent.
W3-OPEN-006 — Replay/shadow/live cost parity has status carriage, but telemetry-backed parity proof is absent.
BLK-001 — Replay fee and impact provenance.
BLK-002 — Fill realism measured-vs-synthetic proof and empirical p_fill_proxy calibration.
```

Secondary gaps that must remain open unless real evidence exists:

```text
W3-OPEN-004 — Empirical p_fill_proxy calibration absent.
W3-OPEN-005 — Standalone realized-slippage metric vs folded-cost doctrine unresolved.
W5-OPEN-002 — Historical 400/500/1500/4000 bucket outputs absent.
W5-CAPITAL-006 — Capital ladder viability still blocked by historical Strategy Ladder artifacts.
W6-OPEN-003 — ML anti-leakage proof artifact not implemented.
CD-OPEN-001 — Engine C/D promotion artifacts not proven.
```

Do **not** mark data-blocked, telemetry-blocked, or human-decision-blocked gaps as resolved.

---

# 3. Core Problem

The current system has improved execution realism, but it still risks over-reading partial execution realism as promotion-grade truth.

This slice must make replay artifacts explicitly answer:

```text
Which execution components are canonical?
Which execution components are proxy/model-only?
Which components are synthetic?
Which components are missing?
Can the resulting labels be used for ML promotion?
Can the resulting economics be displayed green?
Can the resulting capital bucket be promoted?
```

The goal is not to make every component fully canonical in this slice. The goal is to make every component's evidence level explicit and machine-checkable.

---

# 4. Required Execution Fidelity Matrix

Add or extend a typed execution-fidelity matrix on replay artifacts.

At minimum, every candidate/trade-level replay result and every aggregate replay summary should expose these component source statuses:

```text
fee_source_status
impact_source_status
spread_source_status
slippage_source_status
fill_source_status
partial_fill_source_status
adverse_selection_source_status
routing_source_status
venue_constraints_source_status
```

Allowed source statuses should be explicit and typed. Suggested enum values:

```text
MISSING
CONFIGURED
EXCHANGE_METADATA_BACKED
MODEL_ONLY
SYNTHETIC_ONLY
REPLAY_PROXY
PARTIAL_CANONICAL
CANONICAL_MODEL
MEASURED_REPLAY
SHADOW_OBSERVED
MICRO_LIVE_OBSERVED
NOT_APPLICABLE
```

If current enums already exist, reuse them instead of inventing near-duplicates. If a new enum is necessary, keep it local to the replay execution seam unless a shared contract is clearly required.

---

# 5. Required Global Execution Fidelity Status

Add or extend a global status per replay result:

```text
REPLAY_PROXY_ONLY
PARTIAL_CANONICAL_EXECUTION
FULL_CANONICAL_REPLAY
SHADOW_OBSERVED
MICRO_LIVE_OBSERVED
```

Rules:

```text
REPLAY_PROXY_ONLY:
  All or most economics come from simulator/proxy assumptions.

PARTIAL_CANONICAL_EXECUTION:
  At least one canonical component is active, but fee/impact/fill/slippage/routing are not all promotion-grade.

FULL_CANONICAL_REPLAY:
  All required execution components are canonical replay-grade and no required source is missing/model-only/synthetic.

SHADOW_OBSERVED:
  Shadow telemetry exists and is linked to the replay/candidate evidence.

MICRO_LIVE_OBSERVED:
  Micro-live telemetry exists and is linked to the replay/candidate evidence.
```

Do not allow `FULL_CANONICAL_REPLAY` when:

```text
fill_source_status is MODEL_ONLY, SYNTHETIC_ONLY, MISSING, or REPLAY_PROXY
fee_source_status is only CONFIGURED when promotion-grade fee proof is required
impact_source_status is only top-of-book proxy / limited-depth proxy where depth20 is required
slippage_source_status is unresolved or folded-cost doctrine is not accepted
routing_source_status is missing while routing assumptions affect fills/costs
```

---

# 6. ML Label Safety Rule

Any ML training/projection artifact produced from replay must carry:

```text
label_source_status
execution_fidelity_status
label_promotion_eligible
label_blocking_reasons
```

Required rule:

```text
A label cannot be marked FULL_CANONICAL or PROMOTION_ELIGIBLE unless execution_fidelity_status is FULL_CANONICAL_REPLAY or stronger.
```

If the label is generated under `PARTIAL_CANONICAL_EXECUTION`, it may be used for research or diagnostics only:

```text
label_source_status = PARTIAL_CANONICAL_EXECUTION_LABEL
label_promotion_eligible = false
label_blocking_reasons includes execution_fidelity_not_full_canonical
```

If the label is generated under `REPLAY_PROXY_ONLY`:

```text
label_source_status = REPLAY_PROXY_LABEL
label_promotion_eligible = false
label_blocking_reasons includes replay_proxy_label
```

Do not modify ML doctrine to allow positive score uplift.

---

# 7. BLK-002 Doctrine Correction

The current blocker wording risks a circular dependency:

```text
Fill realism measured-vs-synthetic proof is required before Shadow,
but measured fill telemetry is blocked until Shadow/live telemetry exists.
```

Update the register and/or relevant doctrine wording to split:

```text
Before Shadow telemetry collection:
  - contracts and status carriage must exist
  - missing/model-only/synthetic fill must remain non-green
  - no promotion-grade claim is allowed

Before Shadow sign-off:
  - measured fill telemetry must exist
  - measured-vs-synthetic proof must exist
  - replay/shadow fill parity must be assessed
  - p_fill_proxy calibration must be produced if proxy fill remains used

Before Micro-live:
  - fill realism must be either measured, calibrated OOS, or explicitly blocked
```

Do not weaken gating. Clarify phases to avoid impossible preconditions.

---

# 8. Artifact / Cockpit Display Requirements

Replay and cockpit surfaces must not render green when any critical fidelity source is missing, model-only, synthetic, stale, or insufficient.

Cockpit / operator surfaces should display:

```text
execution_fidelity_status
fee_source_status
impact_source_status
spread_source_status
slippage_source_status
fill_source_status
partial_fill_source_status
adverse_selection_source_status
routing_source_status
venue_constraints_source_status
label_source_status if ML projection exists
non_green_blocking_reasons
```

Display labels should be operator-safe:

```text
PARTIAL_CANONICAL_EXECUTION = caution / amber
REPLAY_PROXY_ONLY = non-green
FULL_CANONICAL_REPLAY = green only if sample/freshness/cost completeness also pass
SHADOW_OBSERVED = green only if parity and drift checks pass
```

Do not display expected CE as realized PnL.

---

# 9. Gap Register Update Rules

Update `P0B_FINAL_GAP_REGISTER.md` only after code/tests support the change.

Required updates:

1. Add evidence for Lots 0–3 if not already reflected:
   - DAG realignment.
   - replay execution seam.
   - partial execution backbone convergence via THR-X04/THR-X05.
   - Build-14 / complete_enablers replay provenance.

2. For this slice, move only patched carriage/status gaps forward.

3. Keep open:
   - telemetry-backed fee/impact/fill proof if no telemetry exists.
   - p_fill_proxy calibration if no OOS artifact exists.
   - replay/shadow/live parity if no shadow/live telemetry artifact exists.
   - capital bucket viability if historical bucket outputs do not exist.
   - ML anti-leakage proof artifact if not implemented.

4. Add explicit `Last update = 2026-05-09` for modified open rows.

5. If a row is clarified but not closed, set status to `IN_PROGRESS` or keep existing status. Do not use `RESOLVED_DOC_ONLY` for code-required gaps unless it is genuinely a doctrine-only resolution.

---

# 10. Forbidden Changes

Do not:

```text
- mark model-only fill as measured
- collapse missing fee/impact/fill/slippage to zero
- allow cockpit green when cost/fill/source completeness is partial
- import live protocols into replay
- import venue_adapters into replay
- create a new backtest runtime
- create a new profile beyond LIGHT/COMPLETE
- create a new engine
- make ML positive/uplifting
- mark ML labels promotion-grade from proxy replay labels
- resolve telemetry-blocked gaps with documentation only
- weaken DAG/layer validation
- hide proxy logic behind generic ACTIVE labels
```

---

# 11. Suggested Implementation Plan

## Step 1 — Inspect current contract surface

Find existing enums/models for:

```text
execution fidelity
fee provenance
impact provenance
fill realism
slippage source
parity status
ML label source
```

Prefer reusing current models over adding duplicates.

## Step 2 — Add execution fidelity component matrix

Add a compact typed model such as:

```python
class ReplayExecutionComponentFidelity(BaseModel):
    fee_source_status: ExecutionComponentSourceStatus
    impact_source_status: ExecutionComponentSourceStatus
    spread_source_status: ExecutionComponentSourceStatus
    slippage_source_status: ExecutionComponentSourceStatus
    fill_source_status: ExecutionComponentSourceStatus
    partial_fill_source_status: ExecutionComponentSourceStatus
    adverse_selection_source_status: ExecutionComponentSourceStatus
    routing_source_status: ExecutionComponentSourceStatus
    venue_constraints_source_status: ExecutionComponentSourceStatus
```

Use the repo’s existing Pydantic / dataclass style. Do not force this exact name if the repo already has a better convention.

## Step 3 — Compute global execution fidelity

Add a pure helper:

```python
def resolve_execution_fidelity_status(matrix: ReplayExecutionComponentFidelity) -> ExecutionFidelityStatus:
    ...
```

Rules must fail conservative.

## Step 4 — Attach matrix to replay outputs

Attach to:

```text
ReplayExecutionResult / diagnostics
StrategyLadder detailed replay result
StrategyLadder candidate parity payload
Replay metrics summary if applicable
Cockpit replay metrics projection
```

Do not alter existing backward-compatible fields unless necessary. Additive migration preferred.

## Step 5 — Gate ML labels

Find ML projection/training dataset builders and ensure label source reflects execution fidelity.

Expected behavior:

```text
FULL_CANONICAL_REPLAY or stronger -> labels may be eligible depending on other gates
PARTIAL_CANONICAL_EXECUTION -> research-only label
REPLAY_PROXY_ONLY -> research-only / non-promotion label
```

## Step 6 — Update cockpit false-green logic

Add or extend non-green conditions for partial/proxy execution fidelity.

## Step 7 — Update gap register

Update only rows supported by evidence and tests.

---

# 12. Tests to Run

Minimum targeted test band:

```bash
python -m pytest -q tests/test_local_replay_runtime/test_replay_execution_runtime.py
python -m pytest -q tests/test_local_replay_runtime/test_shadow_execution_simulator.py
python -m pytest -q tests/test_local_replay_runtime/test_strategy_ladder_runner.py
python -m pytest -q tests/cockpit/test_state_replay_metrics.py
python -m pytest -q tests/cockpit/test_state_system_flow.py
python -m pytest -q tests/cockpit/test_state_economic_sterilization.py
python -m pytest -q tests/test_manifest_registry/test_dependencies.py
```

If ML projection tests exist, also run:

```bash
python -m pytest -q tests/test_local_replay_runtime/test_ml_backtest_projection.py
python -m pytest -q tests/test_calibration_methods/test_ml_trainer.py
python -m pytest -q tests/test_complete_enablers/test_ml_fusion.py
python -m pytest -q tests/test_complete_enablers/test_ml_scoring_soft_penalty_hook.py
```

Run DAG/layer validation tests:

```bash
python -m pytest -q tests/test_dag_validator tests/test_manifest_registry
```

If RTK fails because of temporary directory issues, use `python -m pytest` and report the RTK limitation explicitly.

---

# 13. Acceptance Criteria

This slice is accepted only if:

```text
1. Replay artifacts expose component-level execution fidelity.
2. Replay artifacts expose a global execution_fidelity_status.
3. FULL_CANONICAL_REPLAY cannot be emitted from model-only/synthetic/missing fill or incomplete critical sources.
4. ML labels produced from replay cannot be promotion-eligible under REPLAY_PROXY_ONLY or PARTIAL_CANONICAL_EXECUTION.
5. Cockpit remains non-green for partial/proxy/missing execution evidence.
6. BLK-002 wording is clarified into Shadow telemetry collection vs Shadow sign-off vs Micro-live readiness.
7. P0B_FINAL_GAP_REGISTER.md is updated conservatively without falsely resolving telemetry/backtest-blocked gaps.
8. DAG/layer tests remain green.
9. Existing replay behavior remains backward-compatible unless intentionally versioned.
```

---

# 14. Expected Final Report Format

When finished, report:

```text
MemPalace check: performed / not available
Project memory: found / not found
Current codebase source of truth: confirmed

Slice result:
- files changed
- execution fidelity matrix added/extended
- global execution fidelity status added/extended
- ML label safety rule added/extended
- cockpit non-green gating updated/confirmed
- gap register rows updated

Evidence:
- tests run and pass counts
- DAG/layer validation status
- any limitations

Remaining open gaps:
- telemetry-backed fill proof
- replay/shadow/live parity proof
- p_fill_proxy calibration
- capital bucket historical artifacts
- ML anti-leakage proof artifact

Next recommended slice:
- Capital Bucket Evidence Run
or
- Engine C/D Promotion Evidence Run
```

---

# 15. Important Final Reminder

Do not try to make V5.3 look more ready than it is.

The goal of this slice is not to turn partial replay into full proof. The goal is to make partial replay impossible to misread as full proof.

