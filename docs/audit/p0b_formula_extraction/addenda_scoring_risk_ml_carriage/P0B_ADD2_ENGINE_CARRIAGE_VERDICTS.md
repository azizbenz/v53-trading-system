# P0-B Addendum 2 - Engine Carriage Verdicts

## Engine A
- Verdict: `LOCAL_MATH_ONLY_BUT_ACCEPTABLE`
- Proven local carriage:
  - `execution_fragility`
  - `market_toxicity`
  - `spread_regime_penalty`
  - `regime_favorability`
  - `pair_health`
  - `data_freshness`
  - `flow_coherence`
- Proven shared-scoring equivalent:
  - `fragility_score`
  - `toxicity_score`
  - `micro_friction_score`
- Missing shared carriage:
  - `execution_fragility` field in `ScoringCandidateInput`
  - `market_toxicity` field in `ScoringCandidateInput`
  - `spread_regime_penalty` field in `ScoringCandidateInput`
  - `participation_penalty`
  - `supplementary_refs`
- Downstream gates:
  - execution routing uses regime and live microstructure later
  - risk runtime does not receive A's micro-friction fields
- Strategic risk:
  - shared scoring physics is partially duplicated via derived features
  - risk and ML carriage remain incomplete

## Engine B
- Verdict: `LOCAL_MATH_ONLY_BUT_ACCEPTABLE`
- Proven local carriage:
  - `execution_fragility`
  - `market_toxicity`
  - `spread_regime_penalty`
  - `regime_favorability`
  - `pair_health`
  - `data_freshness`
  - `flow_coherence`
- Proven shared-scoring equivalent:
  - `fragility_score`
  - `toxicity_score`
  - `micro_friction_score`
- Missing shared carriage:
  - `execution_fragility` field in `ScoringCandidateInput`
  - `market_toxicity` field in `ScoringCandidateInput`
  - `spread_regime_penalty` field in `ScoringCandidateInput`
  - `participation_penalty`
  - `supplementary_refs`
- Downstream gates:
  - execution routing uses regime and live microstructure later
  - risk runtime does not receive B's micro-friction fields
- Strategic risk:
  - shared scoring still works through derived features
  - shared ML/risk transport is still partial

## Engine C
- Verdict: `PARTIAL_CARRIAGE`
- Proven local carriage:
  - `regime_favorability`
  - `pair_health`
  - `data_freshness`
  - `flow_coherence`
  - direct engine microstructure from Addendum 1 remains valid
- Missing shared carriage:
  - `execution_fragility`
  - `market_toxicity`
  - `spread_regime_penalty`
  - `participation_penalty`
  - `supplementary_refs`
- Shared scoring note:
  - no A/B-style derived `fragility_score/toxicity_score/micro_friction_score` carriage was proven
- Downstream gates:
  - execution routing uses regime and live microstructure later
  - risk runtime does not receive C's micro-friction fields
- Strategic risk:
  - engine C remains decisional
  - shared scoring/risk ML carriage is weaker than A/B

## Engine D
- Verdict: `PARTIAL_CARRIAGE`
- Proven local carriage:
  - `realized_kernel_volatility` via runtime input assembly
  - `regime_favorability`
  - `pair_health`
  - `data_freshness`
  - `flow_coherence`
- Missing shared carriage:
  - `execution_fragility`
  - `market_toxicity`
  - `spread_regime_penalty`
  - `participation_penalty`
  - `supplementary_refs`
- Downstream gates:
  - execution routing uses regime and live microstructure later
  - risk runtime does not receive D's micro-friction fields
- Strategic risk:
  - direct realized-kernel seam is proven
  - shared scoring/risk/ML carriage around friction and artifacts is still partial

## Cross-engine summary
- A/B: local micro-friction math plus derived shared-scoring features
- C/D: local engine math and downstream execution context are real, but shared carriage is more incomplete
- All engines: risk micro-friction/info-stress fields are not populated into `RiskCandidate`
- All engines: `supplementary_refs` live carriage to ML hook is not proven
