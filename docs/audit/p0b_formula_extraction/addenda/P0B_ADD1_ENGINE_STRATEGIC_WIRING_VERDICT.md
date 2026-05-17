# P0-B Addendum 1 - Engine Strategic Wiring Verdict

## Summary

| Engine | Verdict | Reason |
|---|---|---|
| A | `HEALTHY_DIRECT_WIRING` | Direct upstream-governed seams for OFI, realized-kernel scale/current vol, Kyle uplift, plus direct fragility/toxicity/spread inputs and shared downstream scoring/risk/execution rails. |
| B | `HEALTHY_DIRECT_WIRING` | Direct toxic-flow and anti-breakout microstructure wiring (`vpin_current`, `toxic_flow_correlation`, `microstructure_breakout_confirmation`) plus direct fragility/toxicity/spread inputs. |
| C | `HEALTHY_DIRECT_WIRING` | Direct continuation microstructure gate with OFI, queue pressure, VPIN, Kyle lambda, realized-vol seam, and explicit contradictory/missing/confirmed forecast conditioning. |
| D | `HEALTHY_INDIRECT_WIRING_FOR_VPS_NON_HFT` | Direct realized-kernel seam is proven; broader LOB/toxicity/regime families are consumed downstream via shared execution and artifact/regime rails rather than direct engine imports, which is valid for VPS non-HFT doctrine. |

## VPS non-HFT sufficiency

Conclusion: `YES_WITH_BOUNDARIES`

Why:
- direct L2-style imports are not required for every engine
- downstream shared scoring/risk/execution layers do consume micro-friction, toxicity, spread, routing, and regime context
- artifact-level regime / wall / spoof families are consumed in dataset and runtime inference paths even when they are not direct engine inputs

This means "not directly imported into A/B/C/D" is not by itself a defect.

Important boundary:
- the repo contains shared scoring-physics and risk-hook formulas for fragility / toxicity / spread-regime / micro-friction
- but current A/B/C/D `ScoringCandidateInput` builders do not prove those dedicated fields are populated on the common scoring rail
- therefore those shared formulas should not be counted as active engine wiring until that carriage is explicitly proven

## Hard blockers before claiming stronger wiring than proven

1. Per-engine ML supplementary-ref packaging is not proven.
2. A/B/C/D scoring-candidate builders do not currently prove carriage of `execution_fragility / market_toxicity / spread_regime_penalty / participation_penalty` into the shared scoring-physics rail.
3. Artifact-to-engine reinjection of regime-detector outputs is only partially explicit; shared downstream execution use is proven, but engine-local named-field mapping is not uniformly explicit.
4. Several library features remain computed/tested but not proven on live engine, scoring, risk, or execution rails:
   - `PIN`
   - `Amihud`
   - `Roll spread`
   - `Corwin-Schultz`
   - `Hawkes intensity`

## Backtest / Shadow / Live implications

- Backtest/replay math is not blocked by weak engine wiring.
- Shadow observability can remain truthful with the current wiring.
- The next wiring risk is not Engine A/B/C/D direct math; it is proving where artifact-only and ML-only context enters the governed rails.
