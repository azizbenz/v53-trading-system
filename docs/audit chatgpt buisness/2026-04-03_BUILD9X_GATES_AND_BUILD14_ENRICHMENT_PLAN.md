# V5.3 - BUILD9X GATES AND BUILD14 ENRICHMENT PLAN
## Date: 2026-04-03
## Branch: codex/full-shadow-abcd-migration-20260403
## Status: PLANNED

---

# 0. Purpose

Freeze a prod-safe plan for two linked fronts:

1. formalize `Build-9X` as explicit merge gates and end-to-end governed tests
2. absorb the missing high-value `Build-14` addendum enrichments as governed
   Shadow-first enablers

This plan is designed to avoid double work while the real `Build-11` 30-day
Shadow campaign continues.

---

# 1. Strategic verdict

This is a good strategy **if and only if** it follows one strict rule:

- `Build-9X` first becomes explicit, testable governance
- `Build-14` enrichments enter first as `SHADOW_ENABLED`
- their effect is observed and compared in Shadow
- only then can some of them graduate to bounded live influence

What must **not** happen:

- no auto-learning mutation in live
- no direct promotion from idea to live
- no hidden penalty loop that changes live behavior "au fil de l'eau"
- no new autonomous engine created out of the enrichments

So the safe reading is:

- yes in Shadow: observe, compare, penalize, and even keep weak enrichments
  `DORMANT`
- no in live: do **not** let them self-tune dynamically
- yes later in live: allow only explicit post-Shadow, bounded,
  reason-coded, reversible influence

This same logic also applies to a later `Live-Complete` surface:

- Shadow first
- verdict second
- bounded live influence third
- manual downgrade / safing remains available throughout

---

# 2. What is still missing

## 2.1 Build-9X hardening missing today

The branch already has a substantial `meta_learning` package, contracts,
persistence, review queue, monitoring projection, and tests.

But the V2 doc still lacks one explicit closure layer in code:

- named merge gates with clear `PASS/FAIL`
- one explicit end-to-end governed lifecycle proof
- one proof that all mother-doc amendments are propagated through:
  - contracts
  - logs
  - persistence
  - review
  - replay export
  - monitoring/UI

The gates to formalize are:

- `NO_LIVE_MUTATION_PATH`
- `END_TO_END_ID_CORRELATION`
- `STRUCTURED_LEARNING_LOGS_PRESENT`
- `LEARNING_BACKPRESSURE_HANDLED`
- `RESOURCE_BUDGETS_RESPECTED`
- `STATISTICAL_GOVERNANCE_PRESENT`

## 2.2 Build-14 addendum absorption still missing today

The branch already has a real guarded `Build-14` base:

- `market_toxicity_snapshot`
- `execution_fragility_score`
- `limited_influence`
- Shadow/monitoring/UI exposure

But these enrichments do not yet appear as distinct absorbed bricks:

- `LOB deep filter / VWA`
- `OBI`
- `Hurst regime classifier`
- `competition monitor`
- `false breakout model`

---

# 3. Canonical absorption map

These enrichments should **not** become new engines.

They should be absorbed into existing families:

## Microstructure family

- `LOB deep filter / VWA` -> `microstructure_enriched_layer`
- `OBI` -> `microstructure_enriched_layer`
- `false breakout model` -> enriched Engine A/B validation through
  `microstructure_enriched_layer`

## Regime family

- `Hurst regime classifier` -> `regime_enriched_layer`

## Risk / portfolio family

- `competition monitor` -> `risk_contribution_monitor`

This keeps the architecture canonical:

- no engine `E/F/G`
- no bypass of `A/B/C/D`
- no bypass of risk/portfolio

---

# 4. Recommended work batches

## Lot 0 - Audit matrix before coding

Goal:

- turn the current reading into one explicit checklist

Output:

- `Build-9X V2`: point-by-point `coded / tested / monitored / missing`
- `Build-14 addendum`: point-by-point `coded / tested / monitored / missing`

Done criteria:

- every selected requirement has one owner
- nothing is coded "from memory"

## Lot 1 - Build-9X explicit merge gates

Goal:

- convert the V2 governance clauses into named tests/gates

Minimum gates to implement:

1. `NO_LIVE_MUTATION_PATH`
2. `END_TO_END_ID_CORRELATION`
3. `STRUCTURED_LEARNING_LOGS_PRESENT`
4. `LEARNING_BACKPRESSURE_HANDLED`
5. `RESOURCE_BUDGETS_RESPECTED`
6. `STATISTICAL_GOVERNANCE_PRESENT`

Expected output:

- explicit test file(s) with one gate name per assertion group
- one aggregate gate report or fixture grouping these checks

## Lot 2 - Build-9X end-to-end governed lifecycle proof

Goal:

- prove the complete lifecycle once, explicitly

Required path:

`TradeLearningInput -> Diagnostic -> Hypothesis -> Candidate -> ReplayExportBundle -> Review -> Persistence -> Monitoring/UI projection`

Done criteria:

- one end-to-end governed test
- full ID correlation
- no live mutation path
- persistence and retention fields preserved

## Lot 3 - Build-14 enrichment contracts and Shadow readers

Goal:

- add the missing Build-14 enrichments as read-only / Shadow-first readers

Order recommended:

1. `false breakout model`
2. `LOB deep filter / VWA`
3. `OBI`
4. `Hurst regime classifier`
5. `competition monitor`

Why this order:

- `false breakout model` has high direct value for A/B quality
- `LOB/VWA/OBI` are the next most coherent microstructure bundle
- `Hurst` cleanly fits the regime family
- `competition monitor` is useful but easier to overfit if added too early

Done criteria:

- each enrichment has a typed contract or snapshot
- each enrichment is attached to an existing canonical Build-14 family
- none can trade autonomously

## Lot 4 - Shadow observation wave

Goal:

- activate the new enrichments as `SHADOW_ENABLED`
- observe whether they help, hurt, or over-sterilize

Required outputs:

- structured logs
- reason codes
- per-enrichment evidence summaries
- comparison views in Shadow report / monitoring where relevant

Decision states per enrichment:

- `SHADOW_VALIDATED`
- `DORMANT`
- `RESEARCH_LOCAL`

## Lot 5 - Post-Shadow promotion policy

Goal:

- define the only safe path into live influence

Allowed post-Shadow outcomes:

- stay `READ_ONLY`
- become `LIMITED_INFLUENCE`
- become `DORMANT`

Forbidden outcome:

- dynamic self-penalizing or self-tuning live loop without explicit verdict

## Lot 6 - Later Complete rollout use

Goal:

- reuse the same policy in later `Live-Complete`

Rule:

- same logic as Light live, but never weaker
- if an enrichment is not validated in Shadow, it stays read-only or dormant

---

# 5. Impact on build closure

This plan should not reopen every build.

Practical impact:

- `Build-9X` remains a strong aligned base, but this wave hardens its
  governance closure
- `Build-14` remains aligned as a base, but this wave expands addendum
  absorption
- `Build-11` benefits because the Shadow campaign will observe richer Build-14
  evidence
- `Build-12/13` should not be reopened until `Build-11` is honestly closed
- `Build-17` may later consume these enrichments, but it should not lead this
  wave

So the work order remains:

1. keep the real `Build-11` campaign running day by day
2. harden `Build-9X` governance explicitly
3. absorb `Build-14` enrichments into Shadow
4. evaluate them in Shadow
5. only then consider bounded live influence

---

# 6. Recommended immediate next action

The best next coding wave is:

1. `Lot 0` - audit matrix `Build-9X V2` and `Build-14 addendum`
2. `Lot 1` - explicit `Build-9X` merge gates
3. `Lot 2` - end-to-end lifecycle proof

Only after these three lots:

4. start integrating the missing `Build-14` enrichments one by one

This is the lowest-risk path because it gives a strong governed frame before
adding more market-facing complexity.

---

# 7. Honest conclusion

Yes, this is a good strategy.

But the good version of the strategy is:

- governance first
- Shadow-first integration second
- verdict-driven limited live influence third

The bad version would be:

- integrate all enrichments fast
- let them penalize live opportunistically
- and only later try to reconstruct why the system changed

The branch should follow the good version only.
