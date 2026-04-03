# V5.3 - FULL SHADOW 30J A/B/C/D MIGRATION PLAN
## Date: 2026-04-03
## Status: PLANNED_NOT_APPLIED

---

# 0. Decision frame

User-selected target doctrine:

- one governed `Shadow 30 days` phase must test the full solution
- Build-11 Shadow must therefore observe:
  - `engine_a`
  - `engine_b`
  - `engine_c`
  - `engine_d`
  - `Build-14` enablers
- later promotion remains strictly gated:
  - Shadow observation of a component does **not** imply automatic Micro-live
    or Live promotion

Important boundary:

- this migration plan does **not** mean the new doctrine is already applied on
  the current branch
- as of 2026-04-03, the active branch still runs on the previously applied
  `Option B` baseline until the migration lots below are executed on a
  dedicated branch

---

# 1. Recommendation

Recommended path:

- adopt `Full Shadow 30j A/B/C/D + Build-14`
- but execute it as a staged migration, not as a single massive rewrite

Why this is the correct reading if the objective is "test the whole solution in
one Shadow window":

- without reinjecting `C/D`, Build-11 only proves `A/B + Build-14`
- that is coherent for the current branch, but it does **not** test the whole
  solution
- if the true target is full-system proof before downstream rollout, then
  `C/D` must be real Shadow participants, not later optional add-ons

Main impact:

- `Option B` becomes a temporary branch state, not the final target doctrine
- Build-15 and Build-16 stop meaning "engines later in another shadow story"
- instead, they become implementation/hardening waves required to make the
  full Build-11 Shadow honest

---

# 2. What changes if we adopt this path

## 2.1 Doctrine impact

Build-11 becomes:

- `LIGHT + SHADOW`
- `A/B/C/D + Build-14 active in observation`
- `30 consecutive days minimum`
- complete shadow report required
- verdict per component required before any later promotion

Build-12 / Build-13 become:

- downstream rollout stages using only components explicitly validated in
  Shadow
- **not** automatic activation of all `A/B/C/D`

Build-15 / Build-16 become:

- implementation and hardening waves for `engine_c` and `engine_d`
- no longer separate doctrinal excuses for keeping `C/D` out of Build-11

Build-17 becomes:

- later `UI Complete + Live-Complete` stage
- still downstream of real `C/D` implementation and Shadow verdicts

## 2.2 Code impact

Files that will eventually need repatching:

- `docs/specs/V5_3_MASTER_FINAL_UNIQUE.md`
- `docs/specs/V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md`
- `docs/specs/V5_3_BUILD11_SPEC_SHADOW_LIGHT.md`
- `docs/specs/V5_3_BUILD12_SPEC_MICRO_LIVE_LIGHT.md`
- `docs/specs/V5_3_BUILD13_SPEC_LIVE_LIGHT.md`
- `docs/specs/V5_3_BUILD15_SPECS_MOTEUR_C.md`
- `docs/specs/V5_3_BUILD16_SPECS_MOTEUR_D.md`
- `docs/specs/V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md`
- `src/protocols/contracts.py`
- `src/protocols/shadow_runtime.py`
- `src/protocols/shadow_day_counter.py`
- `src/protocols/shadow_dashboard.py`
- `src/protocols/micro_live_runtime.py`
- `src/protocols/live_light_runtime.py`
- `scripts/run_local_replay_shadow.py`
- `src/engines/engine_c/*`
- `src/engines/engine_d/*`

## 2.3 Risk impact

Main risks:

- breaking the newly stabilized Option-B Build-11 chain too early
- mixing doctrine patching and engine coding in the same commit wave
- creating false-green tests with `C/D` visible in docs/UI but not real in
  runtime
- overcoding Build-17 before `C/D` are actually integrated into Shadow

Therefore:

- do **not** start by patching everything at once
- do **not** start by coding Build-17
- do **not** reactivate `C/D` in Build-11 contracts before `engine_c` and
  `engine_d` are minimally executable in Shadow

---

# 3. Execution plan by lot

## Lot 0 - Governance freeze and migration branch

Objective:

- freeze the target doctrine before reopening the canon

Actions:

- record the decision `Full Shadow 30j A/B/C/D`
- create a dedicated migration branch from the current branch head
- keep the current branch readable as the last stable Option-B checkpoint

Deliverables:

- this migration plan
- memory update
- dedicated branch for migration work

Impact:

- no product behavior change yet
- lowest-risk point to stop or revise

Exit criteria:

- governance target frozen
- migration branch created

## Lot 1 - Canon repatch to Full Shadow

Objective:

- rewrite the active doctrine so Build-11 explicitly requires `A/B/C/D +
  Build-14`

Actions:

- patch master/build-plan/build-11/build-12/build-13/table specs
- repatch Build-15 and Build-16 docs so they describe implementation and
  hardening waves, not later doctrinal activation excuses
- explicitly preserve this rule:
  - Shadow observation of `C/D` does not imply automatic live promotion

Deliverables:

- canonical docs aligned on Full Shadow

Impact:

- docs become ahead of the code for a short period
- acceptable only on the dedicated migration branch

Exit criteria:

- no active contradiction remains between Build-11 and Build-15/16 docs

## Lot 2 - Engine C shadow-capable implementation

Objective:

- make `engine_c` real enough to participate honestly in Shadow

Minimum scope:

- importable runtime implementation
- candidate emission
- scoring inputs and outputs
- logs / DTR compatibility
- metrics visible in monitoring payloads
- explicit tests

Non-goals:

- no automatic live promotion
- no Build-17 work
- no optimization wave

Deliverables:

- `engine_c` no longer `spec_only`
- focused Build-15 tests green

Impact:

- first meaningful code expansion
- still isolated from Build-11 contracts at this point

Exit criteria:

- `engine_c` can be exercised in Shadow-facing tests without facade-only hacks

## Lot 3 - Engine D shadow-capable implementation

Objective:

- make `engine_d` real enough to participate honestly in Shadow

Minimum scope:

- importable runtime implementation
- candidate emission
- scoring inputs and outputs
- logs / DTR compatibility
- metrics visible in monitoring payloads
- explicit tests

Non-goals:

- no automatic live promotion
- no Build-17 work

Deliverables:

- `engine_d` no longer `spec_only`
- focused Build-16 tests green

Impact:

- second meaningful code expansion
- still isolated from Build-11 contracts until both engines exist

Exit criteria:

- `engine_d` can be exercised in Shadow-facing tests without facade-only hacks

## Lot 4 - Reinject C/D into Build-11 Shadow contracts and runners

Objective:

- make Build-11 truly full-system in local/runtime terms

Actions:

- repatch Build-11 required engine sets in contracts/runtime/day-counter/report
- repatch local runner and Shadow VPS chain to emit `A/B/C/D`
- restore 4-engine component assessments and comparisons
- keep Build-12 / Build-13 downstream gates strict and non-automatic

Deliverables:

- Build-11 local chain expects and handles `A/B/C/D + Build-14`

Impact:

- this is the main destabilizing lot
- it must happen only after Lots 2 and 3 are green

Exit criteria:

- local replay -> Shadow -> orchestrator -> VPS chain is green on `A/B/C/D`

## Lot 5 - Focused Full Shadow validation suites

Objective:

- prove that the migrated local chain is coherent before any real Shadow run

Actions:

- rerun targeted protocol/runtime/dashboard suites
- refresh audits for Build-11 and Build-15/16
- classify remaining gaps strictly into:
  - doc drift
  - code drift
  - environment/runtime proof gap

Deliverables:

- refreshed audit notes
- memory update
- honest readiness verdict

Impact:

- no doctrine drift should remain after this lot

Exit criteria:

- Build-11 local Full Shadow chain green
- remaining blockers, if any, are runtime-environment blockers only

## Lot 6 - Target-environment runtime proof

Objective:

- move from local proof to real operating proof

Actions:

- execute or prepare native `live_websocket` smoke on target environment
- start the governed real `Shadow 30 days` window for `A/B/C/D + Build-14`
- persist full evidence bundles and final report sections

Deliverables:

- real Shadow evidence
- 30-day report chain
- per-component verdicts

Impact:

- this is where Build-11 can honestly move toward closure

Exit criteria:

- real 30-day Shadow proof exists
- complete report exists
- component verdicts exist

## Lot 7 - Downstream rollout preparation

Objective:

- reopen Build-12 / Build-13 only after real Shadow verdicts

Actions:

- determine which components are promoted, kept dormant, or held for later
- keep budgets bounded
- keep Light rollout disciplined even if all four engines were observed in
  Shadow

Deliverables:

- validated rollout subset for Micro-live
- updated downstream gates if needed

Impact:

- avoids the dangerous confusion "observed in Shadow = automatically live"

Exit criteria:

- downstream rollout set is explicit and audit-ready

---

# 4. Clear suggestions

## Suggestion 1

Use a dedicated migration branch.

Reason:

- the current branch is the last coherent Option-B checkpoint
- mixing the migration directly into it would remove our rollback point

Impact:

- slightly more Git overhead
- much lower risk of losing a stable baseline

## Suggestion 2

Do **not** start by reinjecting `C/D` into Build-11 contracts.

Reason:

- if `engine_c` and `engine_d` stay `spec_only`, Build-11 immediately becomes
  false-green or red again

Impact:

- less churn in the Shadow chain
- clearer defect ownership

## Suggestion 3

Treat Build-15 and Build-16 as implementation waves first, not as later
doctrinal activation phases.

Reason:

- this is the minimum coherent way to make Full Shadow honest

Impact:

- more work upfront
- less doctrinal contradiction later

## Suggestion 4

Keep Build-17 out of the critical path until Lots 2 to 6 are materially green.

Reason:

- Build-17 UI can be polished later
- it does not solve the real proof problem

Impact:

- lower risk of double work
- better focus on runtime truth

---

# 5. Recommended start order

Recommended immediate next sequence:

1. Lot 0
2. Lot 1
3. Lot 2
4. Lot 3
5. Lot 4

Only after these five lots:

6. Lot 5
7. Lot 6
8. Lot 7

---

# 6. Final reading

If the real product goal is:

- "test the whole solution in one Shadow 30-day window"

then this migration is the correct path.

It is **more work now** than keeping Option B,
but it avoids a two-story validation narrative where:

- Build-11 proves only `A/B + Build-14`
- later phases try to retroactively prove `C/D`

This plan is therefore:

- not the smallest-work path
- but the clearest full-proof path
- provided it is executed in disciplined lots and not as a single refactor
