# V5.3 - BUILD-11 VS BUILD-15/16/17 CANON TENSION AUDIT
## Date: 2026-04-03
## Status: RESOLVED_ON_CURRENT_BRANCH

---

# 0. Object

This note freezes a critical canonical tension discovered while preparing the
next Build-11 correction wave.

The goal is to avoid double work and to avoid a false prod-safe closure on
`engine_c`, `engine_d`, and `Build-17 Complete`.

---

# 1. Core finding

Two canonical readings currently coexist in the active corpus.

## Reading A - Build-11 requires C/D now

The Build-11 / master / build-plan reading says:

- `Shadow intégral` is `profile=LIGHT`, `runtime_mode=SHADOW`
- A/B/C/D and Build-14 are active at 100% in observation during the 30-day
  Shadow phase
- post-Shadow verdicts then decide what may go to Micro-live and Live

Primary anchors:

- `docs/specs/V5_3_BUILD11_SPEC_SHADOW_LIGHT.md`
- `docs/specs/V5_3_MASTER_FINAL_UNIQUE.md`
- `docs/specs/V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md`
- `src/protocols/shadow_runtime.py`

## Reading B - C/D belong to later builds

The Build-15 / Build-16 / Build-17 reading says:

- Build-15 is the dedicated build for Engine C
- Build-16 is the dedicated build for Engine D
- Build-17 requires Build-15 and Build-16 already validated
- Build-15 itself requires `Build-1 -> Build-14` already validated
- Build-16 itself requires `Build-1 -> Build-15` already validated

Primary anchors:

- `docs/specs/V5_3_BUILD15_SPECS_MOTEUR_C.md`
- `docs/specs/V5_3_BUILD16_SPECS_MOTEUR_D.md`
- `docs/specs/V5_3_BUILD17_SPEC_UI_COMPLETE_LIVE_COMPLETE.md`
- `src/manifest_registry/build_order_registry.py`
- `src/manifest_registry/module_inventory.py`
- `src/manifest_registry/profile_registry.py`

---

# 2. Why this matters

If we implement Engine C or Engine D now just to satisfy Build-11 gates:

- we risk violating the declared build order
- we risk doing Build-15 / Build-16 work under the wrong build number
- we risk creating double work when the dedicated Build-15 / Build-16 logic is
  implemented for real

If we keep the current Build-11 gates as-is without resolving the contradiction:

- Build-11 cannot be honestly closed
- Build-12 and Build-13 remain blocked for reasons that are partly doctrinal,
  not only technical
- audits become unstable because the code, the build order, and the protocol
  canon point in different directions

---

# 3. Current code reality

The repository currently behaves in the more conservative staged way:

- `engine_c` and `engine_d` are importable but explicitly `spec_only`
- both remain `PLANNED` in the manifest inventory
- both remain absent from runtime-active profile exposure
- the Complete dashboard exists, but its non-demo mode is explicitly
  `availability_only`
- the Complete demo is clearly labeled as a governed demo, not as a real
  `Live-Complete` runtime proof

This is currently more honest than pretending Build-15 / Build-16 are already
implemented.

---

# 4. Prod-safe conclusion

At this point, the next safe action is **not** to implement C/D under Build-11.

The next safe action is:

1. freeze the contradiction explicitly
2. keep Build-11 as `STILL_PARTIAL`
3. keep Build-12 / Build-13 blocked
4. request a governance decision on how the canon must be read

---

# 5. Recommendation

Recommended operating rule until governance resolution:

- do not claim Build-11 closure on the basis of `spec_only` C/D facades
- do not implement Build-15 / Build-16 logic inside a Build-11 fix wave
- continue only on:
  - honest evidence plumbing
  - A/B / Build-14 governance support
  - runtime proof surfaces
  - explicit audit separation between `implemented`, `planned`, and `demo`

---

# 6. Decision options

## Option A - Keep the current Shadow-integral doctrine

Meaning:

- Build-11 keeps requiring A/B/C/D in Shadow
- Build-15 / Build-16 then become later justification / hardening phases for
  engines already observed earlier

Impact:

- Build-11 remains blocked until C/D are materially implemented enough to be
  truthfully observed
- this likely pulls part of Build-15 / Build-16 work earlier

## Option B - Realign Build-11 with the staged build order

Meaning:

- Build-11 validates A/B + Build-14 only in the active Light rollout
- Build-15 introduces C in its own governed phase
- Build-16 introduces D in its own governed phase
- Build-17 stays the Complete rollout stage after Build-15 / Build-16

Impact:

- this removes the contradiction and avoids double work
- but it is a real canonical doctrine change and must be approved explicitly

---

# 7. Resolution on the current branch

The explicit governance choice `Option B` was adopted and applied on the
current branch.

Applied meaning:

- Build-11 now validates `A/B + Build-14` in the active Light Shadow rollout
- Build-15 keeps ownership of Engine C
- Build-16 keeps ownership of Engine D
- Build-17 remains the later Complete rollout stage

This resolves the frozen contradiction for the current branch without claiming
that Build-15 or Build-16 are implemented.

---

# 8. Recommended next step

My recommendation is:

- **freeze this contradiction as a governance checkpoint**
- **do not patch the master canon silently**
- **do not code Engine C/D now just to satisfy Build-11**

The next implementation lot should therefore stay on honest Build-11 closure
surfaces that are compatible with both readings, until the doctrine choice is
made explicitly.
