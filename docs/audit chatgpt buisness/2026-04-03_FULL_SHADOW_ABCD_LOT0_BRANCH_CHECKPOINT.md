# V5.3 - FULL SHADOW A/B/C/D LOT 0 BRANCH CHECKPOINT
## Date: 2026-04-03
## Status: ACTIVE

---

# 0. Object

This note freezes the effective start of `Lot 0` for the Full Shadow
30-day migration.

Goal of Lot 0:

- preserve the current Option-B branch as a rollback checkpoint
- start the migration on a dedicated branch
- keep the doctrine change governed before any wide canon or runtime patch

---

# 1. Effective branch checkpoint

Migration branch created:

- `codex/full-shadow-abcd-migration-20260403`

Branch created from commit:

- `01b39e3`

Meaning:

- the previous branch remains the last coherent `Option B` checkpoint
- the new branch becomes the work surface for the staged `Full Shadow 30j
  A/B/C/D + Build-14` migration

---

# 2. What is and is not applied at this point

Already applied:

- governance target is frozen in the migration plan
- dedicated migration branch exists

Not yet applied:

- canonical repatch to restore `A/B/C/D` inside Build-11
- Engine C implementation
- Engine D implementation
- Build-11 contract/runtime reinjection of `C/D`

Therefore:

- this branch is the migration starting point
- but the code and canon still mostly reflect the previous Option-B state until
  Lots 1 to 4 are executed

---

# 3. Immediate next action

Next recommended step on this branch:

- execute `Lot 1`
- repatch the canonical docs so Build-11 explicitly targets
  `A/B/C/D + Build-14`
- keep downstream promotion semantics strict and non-automatic

---

# 4. Safety reading

This checkpoint exists to avoid two failure modes:

- losing the last stable Option-B rollback point
- mixing doctrine change, engine coding, and Build-11 reinjection in one wave

The migration remains staged by design.
