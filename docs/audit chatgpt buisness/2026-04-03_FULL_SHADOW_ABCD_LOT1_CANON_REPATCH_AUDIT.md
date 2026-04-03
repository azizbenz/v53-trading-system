# V5.3 - FULL SHADOW A/B/C/D LOT 1 CANON REPATCH AUDIT
## Date: 2026-04-03
## Status: APPLIED_ON_MIGRATION_BRANCH

---

# 0. Object

This note freezes `Lot 1` of the staged Full Shadow migration on:

- `codex/full-shadow-abcd-migration-20260403`

Goal of Lot 1:

- repatch the active canon so Build-11 explicitly targets
  `A/B/C/D + Build-14`
- remove the residual Option-B wording that had reduced Build-11 to
  `A/B + Build-14`
- preserve the safety rule that Shadow observation never implies automatic
  Micro-live or Live promotion

---

# 1. Files repatched

Canonical docs updated:

- `docs/specs/V5_3_MASTER_FINAL_UNIQUE.md`
- `docs/specs/V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md`
- `docs/specs/V5_3_BUILD11_SPEC_SHADOW_LIGHT.md`
- `docs/specs/V5_3_BUILD12_SPEC_MICRO_LIVE_LIGHT.md`
- `docs/specs/V5_3_BUILD13_SPEC_LIVE_LIGHT.md`
- `docs/specs/V5_3_TABLE_MERGE_GATES_TESTS_GO_NO_GO.md`

---

# 2. Effective doctrine after Lot 1

Build-11 must now be read as:

- `profil=LIGHT`
- `runtime_mode=SHADOW`
- `Shadow intégral = A/B/C/D + Build-14`
- `30 jours calendaires consécutifs minimum`
- complete Shadow report required
- verdict per component required before any downstream promotion

Build-12 / Build-13 must now be read as:

- downstream rollout stages
- only components with `SHADOW_VALIDATED` may be considered for promotion
- `C/D` are no longer excluded by doctrine from Shadow observation
- `C/D` still require dedicated implementation readiness and service gates
  before any real Micro-live or Live activation

---

# 3. Important safety reading

This lot intentionally changes **canon before runtime**.

Therefore:

- the migration branch is now doctrinally ahead of the code
- this is acceptable only because the branch is dedicated to staged migration
- the repo must not claim Build-11 closure from this lot alone
- the next honest step is to make `engine_c`, then `engine_d`, real Shadow
  participants before reinjecting them into Build-11 runtime surfaces

---

# 4. Residual gaps after Lot 1

Still open:

- `engine_c` remains `spec_only`
- `engine_d` remains `spec_only`
- Build-11 runtime/contracts still reflect the previously stabilized staged
  baseline in code
- no new runtime proof was produced by this docs-only lot

Therefore:

- `Lot 2` must implement `engine_c`
- `Lot 3` must implement `engine_d`
- `Lot 4` will only then reinject `C/D` into Build-11 contracts/runtime

---

# 5. Validation performed

Validation done:

- contradiction grep on canonical docs after patch
- manual diff review of all repatched canonical files
- memory JSON scheduled for schema validation after update

Not done in this lot:

- no protocol/runtime tests were rerun because this was a docs-first doctrine
  repatch
- no code/runtime claim is made from this lot

---

# 6. Next recommended action

Next safe move:

- execute `Lot 2`
- implement `engine_c` as a real Shadow-capable engine
- keep `Build-11` runtime reinjection of `C/D` blocked until both `engine_c`
  and `engine_d` are real enough to participate honestly
