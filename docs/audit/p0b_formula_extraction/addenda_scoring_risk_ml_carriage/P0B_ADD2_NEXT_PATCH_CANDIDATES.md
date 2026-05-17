# P0-B Addendum 2 - Next Patch Candidates

## FIELD_CARRIAGE_PATCH
- Populate shared scoring fields where the source data already exists and doctrine already allows it:
  - `execution_fragility`
  - `market_toxicity`
  - `spread_regime_penalty`
  - `participation_penalty`
- Scope:
  - A/B first, because equivalent local math already exists
  - C/D only after doctrine review, because the equivalent field mapping is less explicit

## FIELD_CARRIAGE_PATCH
- Populate `RiskCandidate` with already-available micro-friction and info-stress fields where runtime inputs can prove them.
- This is the highest-value carriage fix for actual gate behavior.

## FIELD_CARRIAGE_PATCH
- Populate concrete regime-state fields into the shared risk regime precheck input if doctrine confirms that the risk rail should see transported regime state.

## FIELD_CARRIAGE_PATCH
- Package `supplementary_refs` into governed engine scoring candidates only if doctrine confirms live ML/regime artifact transport is intended on VPS rail.

## COCKPIT_LABEL_PATCH
- Label these states explicitly in cockpit and audit surfaces:
  - local-math-only
  - derived-shared-scoring
  - downstream-execution-only
  - artifact-only
  - not carried to risk rail

## TEST_ONLY
- Add explicit tests for:
  - scoring candidate shared-field population
  - risk candidate micro-friction/info-stress population
  - regime precheck transported state
  - supplementary refs packaging from engine runtime to ML hook

## DOC_ONLY
- Document that execution routing is intentionally downstream and non-directional.
- Document that missing ML refs degrade safely to neutral.

## HUMAN_DECISION_REQUIRED
- Decide whether shared scoring-physics carriage is required doctrinally for C/D or whether local math plus downstream VPS execution context is sufficient.
- Decide whether live VPS rail should carry supplementary refs for ML/regime runtime inference or keep them backtest/lab only.
