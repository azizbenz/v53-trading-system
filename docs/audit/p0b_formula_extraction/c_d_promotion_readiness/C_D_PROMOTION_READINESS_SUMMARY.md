# C/D Promotion Readiness Summary

Date: `2026-04-30`
Scope: Engine C and Engine D architecture, wiring, explainability, calibration readiness, replay/shadow evidence, cost realism, and spot-only safety.

## Verdicts

### Engine C architecture verdict

`VIABLE_WITH_GAPS`

Why:
- `src/engines/engine_c/__init__.py` declares a `shadow-capable breakout continuation engine`.
- Local formulas, reason codes, microstructure veto/context, and downstream scoring/risk/refusal seams are implemented and tested.
- Shared A/B-style scoring-physics fields are intentionally partial and not force-mapped.
- Promotion-grade replay/shadow proof is still incomplete.

### Engine D architecture verdict

`VIABLE_WITH_GAPS`

Why:
- `src/engines/engine_d/__init__.py` declares a `shadow-capable re-entry engine`.
- First-episode linkage, anti-revenge, reformation, marginal-value, cost feasibility, and volatility-proxy seams are implemented and tested.
- Shared A/B-style scoring-physics fields are intentionally partial and not force-mapped.
- Promotion-grade replay/shadow proof is still incomplete.

### Engine C promotion verdict

`NOT_SHADOW_READY`

Why:
- Engine-specific replay aggregates exist, but engine-specific executed-only net return, true net-equity drawdown, and promotion artifacts are not proven.
- Engine C still carries only partial shared scoring/risk physics.
- Cost completeness, fill realism, and replay/live parity remain globally incomplete on the promotion rail.

### Engine D promotion verdict

`NOT_SHADOW_READY`

Why:
- Engine-specific replay aggregates exist, but engine-specific executed-only net return, true net-equity drawdown, and promotion artifacts are not proven.
- Engine D still carries only partial shared scoring/risk physics.
- Cost completeness, fill realism, and replay/live parity remain globally incomplete on the promotion rail.

## What Is Solid

- Engine C role is explicit: breakout / continuation with fake-breakout protection and toxic-flow veto/context.
- Engine D role is explicit: re-entry / second chance with first-episode linkage, anti-revenge guard, reformation, and realized-vol context.
- Both engines emit typed `SignalCandidate`, `ForecastSignalCandidate`, refusal records, and runtime logs.
- Both engines enter the common scoring and risk rails without bypassing them.
- Both engines keep `supplementary_refs` additive and non-directional.
- Both engines preserve spot-only `Side.BUY` semantics in the audited runtime paths.

## What Is Missing

- No per-engine executed-only net return rail.
- No per-engine true net-equity drawdown rail.
- No proven per-engine shadow promotion artifact or engine-specific promotion status.
- No full engine-specific carriage of Wave 3/5 cost completeness, fee source, impact source, fill realism, or realized slippage statuses.
- No cockpit page inspected here shows Engine C/D role plus `PARTIAL_BY_DESIGN` explicitly on the engine-why surface.
- No proof that Engine C or D should populate A/B shared fields such as `execution_fragility`, `market_toxicity`, `spread_regime_penalty`, or `participation_penalty`.

## What Must Be Patched Now

- Add explicit engine-level replay/shadow promotion artifact contracts for C and D.
- Surface Engine C/D role and `PARTIAL_BY_DESIGN` status on operator-facing engine explanation pages.
- Add engine-specific readiness status that stays non-green until executed-only net return, true drawdown, and cost realism are proven.

## What Must Wait For Backtest

- Sample-size survival thresholds.
- Capital-bucket viability for C and D.
- Per-engine replay execution-rate, no-fill-rate, and partial-fill-rate proof.
- Per-engine cost-drift and rejection-rate artifacts.

## What Must Wait For Shadow

- Shadow confirmation artifacts for C and D.
- Freshness/hash-valid engine-specific promotion artifacts.
- Live/shadow execution realism parity beyond replay expected CE.

## What Must Never Be Force-Mapped

- Engine C `false_breakout_risk` into `execution_fragility` or `spread_regime_penalty`.
- Engine C raw `OFI` / raw `VPIN` directly into shared toxicity fields without a tested normalized bridge.
- Engine D `reformation_score` into `market_toxicity`.
- Engine D `anti_revenge_state` into generic `risk_penalty`.
- Engine D realized-vol context into shared fragility fields without semantic proof.

## Key Evidence

```text
src/engines/engine_c/__init__.py
  "Shadow-capable breakout continuation engine."

src/engines/engine_d/__init__.py
  "Shadow-capable re-entry engine."

src/engines/engine_c/engine_c_runtime_support.py
  carriage_statuses=("local_math_only", "shared_scoring_physics_partial")

src/engines/engine_d/engine_d_runtime_support.py
  carriage_statuses=("local_math_only", "shared_scoring_physics_partial")

docs/audit/p0b_formula_extraction/addenda_scoring_risk_ml_carriage/P0B_ADD2_CARRIAGE_FIX_REPORT.md
  Engine C and D are "not force-mapped".
```
