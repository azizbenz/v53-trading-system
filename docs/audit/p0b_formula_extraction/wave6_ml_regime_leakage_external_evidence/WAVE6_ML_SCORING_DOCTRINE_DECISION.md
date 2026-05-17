# Wave 6 ML Scoring Doctrine Decision

Date: 2026-04-30
Decision scope: scoring-time ML influence only.

## Canonical decision

- ML is non-sovereign.
- ML cannot create trades.
- ML cannot mutate side.
- ML cannot increase score in the current V5.3 release.
- Positive ML modulation is `FUTURE_RESERVED` pending separate OOS and governance proof.

## Current canonical seam

Canonical doctrine name:

- `ML_SCORE_NON_POSITIVE_MODULATION`

Compatibility alias:

- `soft penalty`

Compatibility rule:

- Hook ids, file names, and compatibility labels may still contain `soft_penalty`.
- Operator-facing doctrine must state that current modulation is non-positive only.

## Runtime doctrine

Allowed:

- bounded score reduction
- neutral no-op modulation
- neutral fallback on missing/stale/invalid artifact state

Forbidden:

- positive score uplift
- candidate creation
- side mutation
- direct trade decision
- directional runtime outputs

## Status vocabulary

Current governed/readiness states:

- `ML_NEUTRAL_NO_REFS`
- `ML_STALE_NEUTRAL`
- `ML_HASH_MISMATCH_DISABLED`
- `ML_DIRECTIONAL_REF_FORBIDDEN`
- `ML_ACTIVE_GOVERNED_REFS`

Documented governance states:

- `ML_FORMALISM_BLOCKED`
- `ML_PROMOTION_BLOCKED`

Meaning:

- missing refs neutralize ML only
- stale/hash mismatch disables ML only
- base engine scoring remains available
- promotion remains blocked while `ml.formalism.unresolved` stands

## Promotion doctrine

- `ml.formalism.unresolved` blocks ML promotion
- it does not block the non-ML base system
- it does not authorize live ML

