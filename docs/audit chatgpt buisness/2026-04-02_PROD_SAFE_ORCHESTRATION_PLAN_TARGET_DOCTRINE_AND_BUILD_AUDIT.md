# V5.3 - PROD-SAFE ORCHESTRATION PLAN
## Date: 2026-04-02
## Status: ACTIVE

---

# 0. Object

This document organizes the next critical phase so that we do not hallucinate,
rewrite the canon too early, or continue coding on a confused foundation.

Objective:

- formalize the target doctrine as a proposal
- commit the currently safe accumulated lot
- perform a build-by-build `code vs md` audit
- classify all drifts before any broad doctrinal migration
- continue coding only after the state of truth is stable

---

# 1. Working principles

## 1.1 Truth order

Truth order remains:

1. active canonical specs
2. real code
3. tests
4. runtime evidence when relevant
5. audit docs and handoffs as context only

## 1.2 Anti-hallucination rule

No statement such as "done", "aligned", or "ready" may be made from memory
alone.

Each critical claim must point to:

- a doc reference
- a code reference
- a test reference
- runtime proof when the build touches real promotion or live execution

## 1.3 Small-lot rule

We do not rewrite all docs first.
We do not rewrite all code first.
We do not keep one giant WIP forever.

We move in bounded lots with explicit entry and exit criteria.

---

# 2. Execution sequence

## Phase A - Freeze target doctrine inputs

Deliverables:

- target doctrine decision doc
- transition and requalification matrix
- memory JSON updated

Goal:

- separate `active canon` from `target doctrine`
- freeze the intended future machine of states before touching more code

Exit condition:

- the future target path is documented enough to avoid improvisation

## Phase B - Commit the current safe accumulated lot

Scope:

- docs already written
- protocol/UI/monitoring safing work
- launcher propagation work
- targeted tests already green

Rules:

- exclude temp files
- keep commit local first
- do not push yet unless explicitly requested

Exit condition:

- the current safe lot is no longer only in the dirty worktree

## Phase C - Build-by-build audit against the active canon

Execution order:

1. Build-1 to Build-5
2. Build-6 to Build-10
3. Build-11 to Build-13
4. Build-14
5. transversal consolidation

Per-build output:

1. canonical obligations
2. code surfaces
3. tests and their real evidentiary value
4. runtime proof when relevant
5. gap classification
6. provisional verdict
7. next action owner:
   - `docs`
   - `code`
   - `tests`
   - `runtime`
   - `governance`

Exit condition:

- every open drift has a named owner and a correction order

## Phase D - Drift correction waves

Priority order:

1. structural integrity
   - Build-1 DAG and boundary drift
2. rollout truth chain
   - Build-11 closure
   - Build-12 readiness
   - Build-13 readiness
3. Build-14 exposed-state normalization
4. test realignment where canon/code already agree
5. runtime proof gaps

Rule:

- only patch what has been classified
- no global rewrite

## Phase E - Governance decision checkpoint

Question to answer only after the audit:

- keep the active canon and only patch contradictions
or
- approve the target single-chain doctrine migration

Rule:

- the target doctrine must not silently replace the active canon mid-audit

## Phase F - Continue coding on the approved frame

If active canon stays:

- continue corrections on the active LIGHT/COMPLETE frame

If target doctrine is approved:

- open a dedicated migration wave for contracts, counters, gates, and UI states

---

# 3. Operational decision gates

## Gate G1 - Can we commit now?

Yes, if:

- temp files are excluded
- targeted tests for the modified code surface are green
- docs/memory reflect the current truth

## Gate G2 - Can we rewrite canonical specs now?

No, unless:

- the build-by-build audit has completed
- governance explicitly approves the migration

## Gate G3 - Can we continue deep coding now?

Only in scoped areas where:

- the drift is already classified
- the owner is clear
- the patch is local and testable

---

# 4. Concrete work packets

## Packet P1 - Safe commit packet

Includes:

- doctrine/audit docs
- protocol safing contracts
- monitoring propagation
- technical dashboard operator controls
- launcher end-to-end safing projection
- related tests

## Packet P2 - Audit packet

Includes:

- build-by-build reread of active canon
- code mapping per build
- test mapping per build
- updated memory and gap register

## Packet P3 - Correction packet

Includes only classified drifts with a narrow write scope.

Examples:

- Build-1 DAG correction
- Build-14 exposure vocabulary correction
- test-only realignment when canon/code already converge

## Packet P4 - Migration packet

Blocked until governance decision.

Would later include:

- `qualification_phase`
- requalification semantics
- new fixed durations
- governed downgrade state machine

---

# 5. Stop conditions

Stop and reframe if any of these happens:

- doc says one thing and code says another and ownership is unclear
- tests are green but do not prove the claimed behavior
- runtime evidence is missing for a live-relevant claim
- a requested change is actually a governance rewrite, not a correction

When this happens:

- update memory
- write the contradiction down
- do not "patch forward by intuition"

---

# 6. Recommended immediate next steps

1. write and freeze the target transition matrix
2. sync memory JSON
3. run focused validation on the current modified surface
4. create one clean local commit for the accumulated safe lot
5. reopen the build-by-build audit using the active canon
6. classify drifts before any broader code migration

---

# 7. Status

This is the active orchestration frame for the next critical stage.

Interpretation:

- commit first
- audit second
- classify drifts third
- continue coding only on a stable decision frame
