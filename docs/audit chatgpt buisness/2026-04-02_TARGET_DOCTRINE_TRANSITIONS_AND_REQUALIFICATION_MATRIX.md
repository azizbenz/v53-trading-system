# V5.3 - TARGET DOCTRINE: TRANSITIONS AND REQUALIFICATION MATRIX
## Date: 2026-04-02
## Status: TARGET DOCTRINE PROPOSAL

---

# 0. Object

This document formalizes the target transition model requested for a single
prod-safe V5.3 rollout chain with governed requalification.

It does not replace the active canon yet.

Its role is to freeze:

- normal phase progression
- allowed downgrade paths
- fixed requalification durations
- manual operator governance requirements
- code surfaces to realign later

---

# 1. Non-negotiable rules

## 1.1 Runtime modes stay canonical

The target doctrine keeps only:

- `runtime_mode=SHADOW`
- `runtime_mode=MICRO_LIVE`
- `runtime_mode=LIVE`

No free-form extra runtime mode is introduced.

## 1.2 Durations are fixed

`x days` must never remain operator-defined or implicit.

Allowed fixed durations only:

- `30 days` for full proof
- `15 days` for confirmation or requalification

## 1.3 Phase transitions are operator-governed

Visible rollout phase changes must be triggered manually through the local
operator UI.

Required operator controls:

- `SET_HALTED`
- `DOWNGRADE_TO_MICRO_LIVE`
- `DOWNGRADE_TO_SHADOW_CONFIRMATION`
- `DOWNGRADE_TO_SHADOW_PROOF`

Each action must require:

- confirmation
- reason capture
- structured audit logging

## 1.4 Hard safety interlocks remain allowed

Automatic safety interlocks may still stop order emission immediately.

But they must not silently convert one rollout phase into another.

Meaning:

- `hard safety block` is not the same thing as
- `approved rollout downgrade`

---

# 2. Target state model

The target doctrine introduces a governed phase field on top of the canonical
runtime modes.

Proposed field:

- `qualification_phase`

Proposed values:

- `shadow_proof_30d`
- `shadow_confirmation_15d`
- `micro_live_15d`
- `live`
- `micro_live_requal_15d`
- `shadow_requal_15d`

Additional state fields:

- `requalification_reason`
- `required_days`
- `restart_policy`

Interpretation:

- `runtime_mode` keeps the canonical execution family
- `qualification_phase` explains where the system sits in the governed rollout
  or requalification path

---

# 3. Normal progression matrix

## 3.1 Forward chain

Normal target chain:

1. `runtime_mode=SHADOW`, `qualification_phase=shadow_proof_30d`
2. `runtime_mode=SHADOW`, `qualification_phase=shadow_confirmation_15d`
3. `runtime_mode=MICRO_LIVE`, `qualification_phase=micro_live_15d`
4. `runtime_mode=LIVE`, `qualification_phase=live`

## 3.2 Entry conditions

### SHADOW_PROOF_30D

Entry conditions:

- complete implementation exists
- guards, observability, reporting, and stop paths exist
- no critical canonical blocker remains open

Exit conditions:

- `30 consecutive calendar days`
- proof report complete
- logs and validation evidence complete
- post-shadow verdict produced

### SHADOW_CONFIRMATION_15D

Entry conditions:

- `SHADOW_PROOF_30D` completed
- proof report approved
- release frozen for confirmation

Exit conditions:

- `15 consecutive calendar days`
- no material drift on the frozen release
- confirmation report complete

Restart policy:

- if trading logic, risk logic, execution logic, infra shape, or exchange path
  changes materially, the 15-day confirmation restarts

### MICRO_LIVE_15D

Entry conditions:

- `SHADOW_CONFIRMATION_15D` completed
- approved confirmation report
- live broker/exchange path ready
- micro-live budget approved

Exit conditions:

- `15 calendar days minimum`
- execution drift acceptable
- reconciliation acceptable
- real cost envelope acceptable
- micro-live review complete

### LIVE

Entry conditions:

- `MICRO_LIVE_15D` completed
- micro-live review approved
- rollback and halt paths tested
- operator UI local controls available

Exit conditions:

- no fixed duration
- remains live until halted, degraded, or requalified

---

# 4. Requalification matrix

## 4.1 Allowed downgrade paths

Allowed requalification paths:

- `MICRO_LIVE_15D -> SHADOW_CONFIRMATION_15D`
- `MICRO_LIVE_15D -> SHADOW_PROOF_30D`
- `LIVE -> MICRO_LIVE_15D`
- `LIVE -> SHADOW_CONFIRMATION_15D`
- `LIVE -> SHADOW_PROOF_30D`
- `LIVE -> HALTED`
- `MICRO_LIVE_15D -> HALTED`

No arbitrary custom duration is allowed.

## 4.2 Decision rules

### Minor incident or operational drift

Recommended downgrade:

- `LIVE -> MICRO_LIVE_15D`

Examples:

- operator process issue
- bounded observability degradation
- non-structural execution friction

### Non-trivial cost, reconciliation, execution, or sizing drift

Recommended downgrade:

- `LIVE -> SHADOW_CONFIRMATION_15D`

Examples:

- repeated reconciliation mismatch
- repeated real cost drift beyond accepted envelope
- suspicious sizing behavior without a proven logic rewrite

### Material change or grave incident

Recommended downgrade:

- `LIVE -> SHADOW_PROOF_30D`

Examples:

- strategy logic change
- risk logic change
- engine behavior change
- exchange path change
- infra topology change
- serious production incident

### Critical emergency

Immediate action:

- `LIVE -> HALTED`

Then:

- operator decides whether the next governed path is
  `MICRO_LIVE_15D`, `SHADOW_CONFIRMATION_15D`, or `SHADOW_PROOF_30D`

## 4.3 Requalification duration rules

Fixed rules:

- confirmation or requalification path: `15 days`
- full proof path: `30 days`

Do not use:

- `x days`
- ad hoc operator-chosen durations
- unstated "until it feels stable" logic

---

# 5. Required code mapping later

Central files to realign if this doctrine is adopted:

- `src/protocols/contracts.py`
- `src/protocols/shadow_day_counter.py`
- `src/protocols/shadow_runtime.py`
- `src/protocols/micro_live_runtime.py`
- `src/protocols/live_light_runtime.py`
- monitoring and UI surfaces afterwards

Expected code changes:

- keep canonical `runtime_mode`
- add `qualification_phase`
- add `requalification_reason`
- add `required_days`
- add `restart_policy`
- make manual safing actions map to governed downgrade paths
- keep hard interlocks distinct from manual rollout transitions

---

# 6. Anti-hallucination execution rule

Before any code migration to this doctrine:

1. freeze this transition matrix
2. keep the active canon separate from the target doctrine
3. audit build by build against the active canon
4. classify every gap as:
   - `docs vs docs`
   - `docs vs code`
   - `tests behind`
   - `runtime evidence missing`
   - `governance change requested`
5. only then open scoped code patches

This avoids rewriting the system around a target doctrine while still being
unclear about the real state of Builds 1 to 14.

---

# 7. Status

Status frozen by this document:

- target doctrine is formalized
- fixed requalification matrix is formalized
- active canon is not replaced yet
- code migration remains blocked until the build-by-build audit and explicit
  governance decision
