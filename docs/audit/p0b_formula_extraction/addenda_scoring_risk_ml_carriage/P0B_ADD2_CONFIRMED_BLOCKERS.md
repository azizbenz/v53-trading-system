# P0-B Addendum 2 - Confirmed Blockers

## Blocker 1
- Type: `FIELD_CARRIAGE_GAP`
- Impact:
  - trade selection interpretation
  - cockpit false-green risk
- Proof:
  - `ScoringCandidateInput` exposes `execution_fragility`, `market_toxicity`, `spread_regime_penalty`, `participation_penalty`
  - A/B/C/D scoring candidate builders do not populate those fields
- Why it matters:
  - shared scoring physics code exists
  - current live builders leave it at zero defaults
  - this can be misread as active shared carriage when it is a silent no-op

## Blocker 2
- Type: `RISK_GATE_CARRIAGE_GAP`
- Impact:
  - risk gate
  - promotion confidence
  - cockpit false-green risk
- Proof:
  - `RiskCandidate` supports micro-friction and info-stress inputs
  - A/B/C/D risk builders pass only pair/size/loss/beta
- Why it matters:
  - risk micro-friction hook receives nominal derived scores
  - info-stress hook receives `None`
  - live governed risk rail is effectively fail-open/neutral on these missing fields

## Blocker 3
- Type: `ML_REF_CARRIAGE_GAP`
- Impact:
  - trade selection modulation
  - promotion gate interpretation
- Proof:
  - ML soft-penalty hook reads `candidate.supplementary_refs`
  - A/B/C/D do not prove packaging of `supplementary_refs`
- Why it matters:
  - generic hook exists and is tested
  - live engine-specific carriage into that hook is not proven

## Blocker 4
- Type: `REGIME_REINJECTION_GAP`
- Impact:
  - risk gate
  - scoring interpretation
  - cockpit false-green risk
- Proof:
  - regime outputs are decisional in execution routing
  - regime outputs are not uniformly proven in shared scoring or risk carriers
  - risk regime precheck input is not populated with concrete regime state by current engine runtime paths
- Why it matters:
  - execution sees regime context
  - risk/scoring do not uniformly see the same governed regime state

## Not blockers
- lack of direct HFT-style L2 inputs inside engines by itself
- existence of compatibility SHORT enums without governed activation proof

