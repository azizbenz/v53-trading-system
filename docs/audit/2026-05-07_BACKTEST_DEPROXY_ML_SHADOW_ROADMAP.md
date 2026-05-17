# 2026-05-07 Backtest Deproxy -> ML -> Shadow Roadmap

Date: `2026-05-07`
Status: `WORKING_PLAN_APPROVED_FOR_EXECUTION`
Scope: canonical V5.3 backtest Strategy Ladder, ML artifact integration, bounded threshold calibration before Shadow.

## Purpose

This document records the execution order agreed for the next critical work slice.

The immediate problem is not "lack of trades" by itself.
The immediate problem is that the current backtest still depends on proxy rails, so a red or zero-trade result is not yet trustworthy enough to drive promotion or calibration decisions.

The plan below therefore prioritizes:

1. removing proxy rails from the backtest path
2. proving the native backtest path by real run artifacts
3. integrating governed ML artifacts into that now-truthful backtest path
4. comparing non-ML versus ML-backed backtest results
5. calibrating bounded dynamic thresholds for Shadow
6. rebalancing thresholds during Shadow using real Binance evidence

## Current critical reading

Two proxy conditions still matter:

1. Candidate truth rail is still compatibility-driven.
   - Current source labels still include `COMPAT_FEATURE_DISCOVERY`.
   - Native engine work is not yet the primary full-path candidate truth source.

2. Expected edge rail is still proxy-driven.
   - Current edge estimation still uses a `_TO_CALIBRATE` forward-return median proxy.
   - This blocks trustworthy interpretation of zero-trade or non-viable trade outcomes.

Because of those two points, "make trades happen" is not the immediate engineering objective.
The immediate engineering objective is to obtain a truthful backtest rail.

## Execution order

### Phase A - Deproxy the backtest

Objective:
- remove the remaining proxy rails from the canonical Strategy Ladder backtest path

Must do:
- replace compatibility-only candidate truth as the primary ladder source
- invoke native engine A/B/C/D logic on the governed ladder path, not only on a limited sample
- stop treating proxy edge estimation as sufficient backtest truth
- preserve audit-ready provenance for any remaining fallback state

Exit criteria:
- `candidate_engine_native_count > 0`
- `candidate_proxy_count == 0` on the target governed path, or an explicit documented residual exception exists
- engine-native candidate, replay, and provenance statuses are visible in the final run manifest
- the backtest result is interpretable as a real system result, even if it still produces `0 trade`

### Phase B - Run proof after Phase A

Objective:
- prove that the deproxied rail actually runs end to end

Must produce:
- canonical Strategy Ladder run artifacts
- replay artifacts
- engine / pair / strategy promotion artifacts
- capital profile artifacts
- dashboard-visible stage and blocker surfaces

Must verify:
- engines actually execute their governed logic
- features and metrics are produced on the intended path
- replay artifacts are populated and readable
- dashboard state reflects the run truthfully

Exit criteria:
- one governed run completes successfully
- replay and dashboard evidence can be inspected without relying on assumptions
- every zero-trade or refusal-heavy outcome has explicit reason codes and provenance

### Phase C - Train and wire the ML artifact

Objective:
- make ML real and governed inside the backtest path

Must do:
- launch a real training flow
- produce a governed `MlModelArtifact`
- wire artifact loading into the backtest edge path
- reuse the existing governed ML loading / staleness / hash / fallback doctrine

Hard rule:
- ML remains non-sovereign
- ML may modulate a governed signal path, but may not invent side, trade direction, leverage, or shorting

Exit criteria:
- one valid artifact is trained and loadable
- artifact usage is visible through provenance and status fields
- backtest can run both with and without the artifact on the same governed rail

### Phase D - Compare non-ML versus ML-backed backtest

Objective:
- determine whether the ML-backed path materially improves the truthful backtest

Must compare:
- same historical window
- same cost doctrine
- same engine path
- same replay path
- same artifact freshness rules

Primary comparison targets:
- executed trade count
- refusal reasons
- expected-vs-realized replay economics where available
- artifact and replay health
- engine / pair / strategy promotion surfaces

Exit criteria:
- a side-by-side result exists for:
  - backtest without ML
  - backtest with governed ML artifact
- the comparison is reproducible and artifact-backed

### Phase E - Bounded dynamic threshold calibration for Shadow

Objective:
- calibrate dynamic but bounded thresholds suitable for Shadow preparation

Context:
- historical data source is Bybit
- planned Shadow venue is Binance

Therefore:
- thresholds must be dynamic
- thresholds must be bounded
- venue drift must be explicit
- no uncontrolled threshold free-for-all is acceptable

Must do:
- preserve pair-aware / venue-aware bounds
- maintain fail-closed behavior
- document any Bybit -> Binance transfer assumptions
- only promote thresholds that remain inside governed safety bounds

Exit criteria:
- threshold artifacts or equivalent governed outputs exist
- thresholds are bounded, explainable, and venue-aware
- Shadow preparation does not rely on ad hoc manual overrides

### Phase F - Rebalance during Shadow

Objective:
- refine thresholds during the Shadow month using real Binance evidence

Must do:
- use real Shadow evidence, not backfilled narrative
- rebalance on a governed cadence
- preserve audit trail for each threshold update
- keep promotion gates fail-closed while evidence remains partial

Exit criteria:
- threshold updates are evidence-backed
- threshold drift is documented
- Shadow refinements remain compatible with later Micro-live doctrine

## Non-goals

- Do not force trades just to make the backtest look active.
- Do not enable directional ML sovereignty.
- Do not calibrate Shadow thresholds before the backtest rail is truthful.
- Do not treat Bybit evidence as Binance equivalence without explicit bounded transfer doctrine.
- Do not bypass Shadow, Micro-live, or Live promotion gates.

## Decision summary

The correct order is:

1. truthful backtest first
2. proof run second
3. ML artifact training and activation third
4. non-ML vs ML comparison fourth
5. bounded threshold calibration fifth
6. Shadow-month rebalancing last

This order is mandatory because any earlier calibration or ML judgment would otherwise rest on a backtest path still polluted by proxy behavior.

## Immediate next action

Proceed to Phase A:
- deproxy the canonical Strategy Ladder backtest path before any new calibration or Shadow-readiness claim
