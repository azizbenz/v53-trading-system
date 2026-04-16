# 24 - V5.3 Update Surgical Integration Map

Date: 2026-04-15
Scope: reconcile docs 18 -> 23 with the real codebase, identify the exact landing zone for each update, and prevent "plan drift" or false completion claims.

## 0. Non-negotiable doctrine

- Preserve canonical V5.3 architecture.
- Do not invent profiles beyond `LIGHT` and `COMPLETE`.
- Do not invent engines beyond `A/B/C/D`.
- Build-14 remains additive and bounded; it does not replace canonical builds.
- Do not bypass Shadow, Micro-live, or Live promotion gates.
- Keep audit-ready outputs, typed contracts, and structured logs.
- Treat current code as source of truth when docs and code disagree.

## 1. Reading method used here

This document is not a rewrite of docs 19 -> 23. It is a surgical map.

Each conclusion below is tagged as one of:

- `DONE_IN_CODE`: already implemented in current code.
- `PARTIAL_SEAM_EXISTS`: not done as specified, but the repo already has a real insertion seam.
- `DOC_STALE`: the document still describes the past, not the current repo.
- `NEW_WORK_VALID`: genuinely missing and worth building.
- `NEW_WORK_DEFER`: valid idea, but should not land before upstream seams are green.
- `DOC_PATH_MISMATCH`: the idea is valid, but the target path in the doc does not match the actual architecture.
- `DOC_CONFLICT`: the wording of the doc conflicts with current canonical types or invariants.
- `VALID_GOVERNANCE`: keep as doctrine or sequencing rule, not as an implementation gap by itself.

## 2. Code truth already delivered

These items are no longer future work, even if docs 18 or 19 still describe them as missing.

| Item | Doc reference | Proof in code | Status |
| --- | --- | --- | --- |
| Binance venue-side quota tracker | doc 19 line 74; doc 18 lines 33, 72, 76, 289, 459 | `src/venue_adapters/binance_spot/rate_limiter.py`; wired in `src/venue_adapters/binance_spot/rest_client.py:229` | `DONE_IN_CODE` |
| Pair catalog | doc 19 line 85 | `src/interface_contracts/pair_catalog.py:64` | `DONE_IN_CODE` |
| Shadow gate checker | doc 18 lines 307, 468; doc 19 line 173 | `scripts/shadow_gate_check.py:73`; `scripts/shadow_gate_check.py:125` | `DONE_IN_CODE` |
| Hansen SPA | doc 18 lines 142, 305 | `src/calibration_methods/hansen_spa.py:31`; tested in `tests/test_calibration_methods/test_hansen_spa.py` | `DONE_IN_CODE` |
| Engine C exists and is shadow-capable | doc 19 line 52 is stale | `src/engines/engine_c/__init__.py:26-27`; `src/engines/engine_c/engine_c_runner.py` | `DONE_IN_CODE` |
| Engine D exists and is shadow-capable | doc 19 line 52 is stale | `src/engines/engine_d/__init__.py:26-27`; `src/engines/engine_d/engine_d_runner.py` | `DONE_IN_CODE` |
| C protocol bridge groundwork | doc 21 lines 79-82, 199 | `src/protocols/engine_c_void_validation_bridge.py:49-87` | `PARTIAL_SEAM_EXISTS` |
| D protocol bridge groundwork | doc 22 lines 74-79, 240 | `src/protocols/engine_d_reentry_validation_bridge.py:52-89` | `PARTIAL_SEAM_EXISTS` |
| Build-14 microstructure-like heuristics already exist | doc 23 formal package still absent | `src/complete_enablers/order_book_imbalance.py`; `src/complete_enablers/market_toxicity_snapshot.py` | `PARTIAL_SEAM_EXISTS` |

## 3. High-value mismatches between docs and repo

### 3.1 Doc 18 is now historical, not authoritative

- Doc 18 lines 33, 72, 76, 289 still talk about `rate_limiter.py` as absent. That is no longer true.
- Doc 18 lines 301 -> 307 still list `psr.py`, `ks_test.py`, `energy_distance.py`, `hansen_spa.py`, `shadow_gate_check.py` as open work. That is stale for all except whatever remains around their orchestration or broader proof-gate evidence.
- Therefore doc 18 remains useful as audit framing, but it is no longer a reliable implementation ledger.

Verdict: `DOC_STALE`

### 3.2 Doc 19 line 52 is materially false now

Doc 19 line 52 says the current system has "4 engines (A/B only coded)". Current code disproves that:

- `src/engines/engine_c/__init__.py:26-27`
- `src/engines/engine_d/__init__.py:26-27`

Verdict: `DOC_STALE`

### 3.3 Doc 20 enriched `SignalCandidate` is not a literal drop-in replacement

Doc 20 lines 81 -> 150 define a much richer Narang-grade contract. Current code still constructs the old `SignalCandidate` directly in runtime builders:

- `src/engines/engine_a/engine_a_runtime.py:657-684`
- `src/engines/engine_b/engine_b_runtime_support.py:482-...`
- `src/engines/engine_c/engine_c_runtime.py:639-656`
- `src/engines/engine_d/engine_d_runtime.py:644-664`

Current canonical contract is still:

- `src/interface_contracts/decision_contracts.py:59-93`

Verdict: `NEW_WORK_VALID`, but the phrase "drop-in replacement" is misleading in the current repo.

### 3.4 Doc 20 line 411 conflicts with the current `Side` enum

Doc 20 line 411 proposes blocked emissions still produce a `SignalCandidate` with `side="flat"`.

Current enum:

- `src/interface_contracts/domain_types.py:150-153`

Only `buy` and `sell` exist. There is no `flat`.

Verdict: do not implement that wording literally. Use `ConditioningRecord` plus `RefusalRecord`, not a fake "flat" trade candidate.

### 3.5 Docs 20 -> 22 propose `meta_engine/*`, but this repo has no `meta_engine/`

Current top-level packages include `meta`, `meta_minimal`, `meta_learning`, and `monitoring`, but not `meta_engine`.

Verdict: `DOC_PATH_MISMATCH`

## 4. Line-by-line verdict by source document

This is "line-by-line" at the useful level: line ranges that materially change code placement or sequencing.

### 4.1 Doc 19 - `19_MULTIPAIR_MODERNIZATION_PLAN.md`

| Lines | Claim or task | Code truth | Verdict | Surgical action |
| --- | --- | --- | --- | --- |
| 52 | "A/B only coded" | C and D already exist and are shadow-capable | `DOC_STALE` | Rewrite mentally as "A/B/C/D coded, C/D need doctrinal deepening" |
| 74 | venue `rate_limiter.py` missing | Implemented | `DONE_IN_CODE` | Remove from active backlog |
| 85 | `pair_catalog.py` | Implemented | `DONE_IN_CODE` | Remove from active backlog |
| 90 | `RefusalRecord` + `RefusalJournal` | Missing | `NEW_WORK_VALID` | Add contract first, journal second |
| 99 -> 104 | microstructure package + feature contract + feature promotion | Package absent, Build-14 heuristics already exist elsewhere | `PARTIAL_SEAM_EXISTS` | Create canonical `data_backbone/microstructure/`, then feed existing Build-14 readers from it |
| 105 -> 109 | enriched contract, normalizer, break-even, cost drift | Missing | `NEW_WORK_VALID` | Land contract seam before engines or monitors |
| 109 | B toxic-flow fade sub-signal | Missing, but B already has toxicity and microstructure inputs | `PARTIAL_SEAM_EXISTS` | Extend Engine B as sub-signal, not as new engine |
| 118 -> 129 | ML enabler, model risk, strategy drift, coordination rules, residualized momentum | Mostly absent | `NEW_WORK_VALID` | Keep ML modulation bounded; coordination rules before C/D doctrinal refactor |
| 139 -> 146 | sizing, regime change, tail risk, crowding, regime shift | Mostly absent | `NEW_WORK_VALID` | Sequence after forecast normalization and economics seam |
| 154 -> 157 | hybrid router, TWAP, portfolio arbitration | Missing | `NEW_WORK_VALID` | Land only after economics, portfolio record, and execution cost truth are in place |
| 173 | use `shadow_gate_check` in tier transitions | Script exists | `DONE_IN_CODE` | Keep, but remember it still returns `FAIL` until evidence exists |
| 187, 191, 194, 196, 199 | reinforced prohibitions | Mostly consistent with repo doctrine | `VALID_GOVERNANCE` | Treat as constraints, not backlog |
| 212 -> 221 | new threshold IDs | Mostly not wired yet | `NEW_WORK_VALID` | Add only when the consuming module lands; do not catalog speculative thresholds |
| 290, 293 | hard execution order | Correct in spirit | `VALID_GOVERNANCE` | Keep order but rewrite around existing C/D code rather than greenfield C/D |

### 4.2 Doc 20 - `20_CARVER_NARANG_TALEB_INTEGRATION.md`

| Lines | Claim or task | Code truth | Verdict | Surgical action |
| --- | --- | --- | --- | --- |
| 36 -> 43 | enriched contract families | Not in code | `NEW_WORK_VALID` | Add as backward-compatible contract seam, not a hard switch |
| 55, 57 | `forecast_normalizer.py`, `break_even_filter.py` | Missing | `NEW_WORK_VALID` | Place in `src/scoring_backbone/` |
| 153 -> 157 | `model_risk_registry`, `strategy_drift_monitor`, `cost_drift_monitor`, `crowding_suspicion_monitor`, `regime_shift_watcher` | Absent | `NEW_WORK_VALID` | Place by actual architecture, not doc fantasy paths |
| 200 -> 203 | Taleb quadruple filter | Not a module yet | `NEW_WORK_VALID` | Use as promotion-gate composition rule, not a monolithic package |
| 205 -> 227 | `RefusalRecord` | Absent | `NEW_WORK_VALID` | Contract in `interface_contracts`; persistence in meta path |
| 229 -> 230 | `tail_risk_meter` | Absent | `NEW_WORK_VALID` | Put under `risk_backbone` |
| 250 -> 258 | phase deltas P1/P2 | Still mostly valid | `NEW_WORK_VALID` | Keep order, but do not call P2-06 "drop-in" |
| 265 -> 266 | model risk + strategy drift | Missing | `NEW_WORK_VALID` | Integrate with artifact and review flow, not only runtime |
| 280 -> 282 | tail risk, crowding, regime shift | Missing | `NEW_WORK_VALID` | Runtime/risk path |
| 287 | portfolio arbitration record | Missing | `NEW_WORK_VALID` | Wire through `portfolio_minimal` |
| 298 -> 302 | new thresholds | Missing | `NEW_WORK_VALID` | Catalog only with real consumers |
| 318 -> 324 | prohibitions | Good doctrine | `VALID_GOVERNANCE` | Keep as hard constraints |
| 398 -> 405 | `engine_coordination_rules` implemented in `src/meta_engine/...` | No such package exists | `DOC_PATH_MISMATCH` | Put coordination core near `protocols/` and expose typed contracts |
| 411 | blocked candidate with `side="flat"` | Conflicts with current enum | `DOC_CONFLICT` | Use refusal + conditioning trace instead |
| 474 | `strategy_identity.py` "Implementation" | File absent | `NEW_WORK_VALID` | Optional downstream seam after enriched contract lands |

### 4.3 Doc 21 - `21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md`

| Lines | Claim or task | Code truth | Verdict | Surgical action |
| --- | --- | --- | --- | --- |
| 3 | C blocked until coordination rules are green | Sensible | `VALID_GOVERNANCE` | Keep |
| 26 | A/C mutual exclusion hard block | Not implemented canonically | `NEW_WORK_VALID` | Implement in coordination layer before deepening C |
| 40 -> 46 | greenfield file layout | Current C already has parallel files with different names | `PARTIAL_SEAM_EXISTS` | Refactor existing C modules, do not create a second Engine C stack |
| 63 -> 68 | breakout detector based on realized kernel vol | Not present | `NEW_WORK_VALID` | Evolve `structure_resolver_c.py` or split out `structure_detector_c.py` only if needed |
| 73 -> 75 | OFI, queue, VPIN confirmation | Not present as canonical package | `NEW_WORK_VALID` | First build doc 23 canonical features |
| 79 -> 82 | `a_exclusion_guard_c.py` via coordination rules | No canonical guard yet | `NEW_WORK_VALID` | Implement after coordination core exists |
| 101 -> 105 | break-even + invalidation wiring | break-even filter missing; invalidation exists in C already | `PARTIAL_SEAM_EXISTS` | Reuse `invalidation_mapper_c.py`; add economics gate upstream |
| 107 -> 127 | signal reporter using enriched contract | current runtime builds old contract directly | `NEW_WORK_VALID` | Move only after contract seam lands |
| 152 -> 158 | C thresholds | not wired | `NEW_WORK_VALID` | Add with calibrations, not hardcodes |
| 182 -> 187 | prohibitions | Correct | `VALID_GOVERNANCE` | Keep |
| 206 | "implementation blocked" | C is already implemented, but not at doc-21 doctrinal depth | `DOC_STALE` | Read as "doctrinal continuation blocked by coordination rules" |

### 4.4 Doc 22 - `22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md`

| Lines | Claim or task | Code truth | Verdict | Surgical action |
| --- | --- | --- | --- | --- |
| 21, 29 | D needs historical linkage and strategy beta | Current D has partial lineage fields only | `PARTIAL_SEAM_EXISTS` | Deepen existing D, do not rebuild D from zero |
| 41 -> 50 | greenfield D file layout | Existing D stack already present with different names | `PARTIAL_SEAM_EXISTS` | Split only where current D cannot express the new behavior |
| 68 -> 79 | first episode resolver + R-D-1/R-D-2/R-D-3 | Not canonical yet | `NEW_WORK_VALID` | Build on top of current D linkage fields and protocol bridge |
| 83 -> 112 | structure reformation, marginal EV, tighter invalidation | Current D has analogous steps but simpler semantics | `PARTIAL_SEAM_EXISTS` | Refactor existing D stages, not replacement |
| 144 -> 170 | strategy beta formal rule | Not in code | `NEW_WORK_VALID` | Put rule into coordination/history layer, not only runner-local code |
| 197 -> 201 | D thresholds | not wired | `NEW_WORK_VALID` | Add with calibrated catalog entries |
| 230 | no D without first episode | consistent with doctrine | `VALID_GOVERNANCE` | Hard rule |
| 253 -> 257 | D has higher bar than A/B/C | correct | `VALID_GOVERNANCE` | Keep |

### 4.5 Doc 23 - `23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`

| Lines | Claim or task | Code truth | Verdict | Surgical action |
| --- | --- | --- | --- | --- |
| 23 -> 34 | canonical microstructure package layout | package absent | `NEW_WORK_VALID` | Create `src/data_backbone/microstructure/` |
| 64 -> 281 | formal feature definitions | not implemented canonically | `NEW_WORK_VALID` | Implement only in the order given at lines 391 -> 398 |
| 293 | `feature_registry.py` contract | absent | `NEW_WORK_VALID` | This must land first |
| 314 | SHAP + promotion pipeline recap | no canonical feature store/promotion seam yet | `NEW_WORK_VALID` | Connect to Build-14, do not bypass it |
| 336 | 1990s TA prohibition | aligned with current doctrine | `VALID_GOVERNANCE` | Keep |
| 391 -> 398 | immediate order | correct and useful | `VALID_GOVERNANCE` | Follow as written |

## 5. Surgical placement map

This is the core of the document: where each update should land in the real repo.

| Update | Doc origin | Doc target path | Recommended surgical target in current repo | Why this target is correct |
| --- | --- | --- | --- | --- |
| Enriched `SignalCandidate`, `ForecastTargetClass`, `ForecastHorizonClass`, `BetStructure`, `ConditioningRecord` | doc 20 lines 81 -> 150 | `src/interface_contracts/forecast_contracts.py` | `src/interface_contracts/decision_contracts.py` as the canonical contract seam, optionally with helper enums in a new sibling `forecast_contracts.py` | Current A/B/C/D runtimes all build `decision_contracts.SignalCandidate` directly; a second competing canonical contract would increase churn |
| `RefusalRecord` | doc 19 line 90; doc 20 lines 205 -> 227 | `src/interface_contracts/refusal_records.py` | `src/interface_contracts/refusal_records.py` | Path is already right |
| `RefusalJournal` | doc 19 line 90; doc 20 line 250 | `src/meta_engine/refusal_journal/` | `src/meta_minimal/refusal_journal/` with canonical export via `src/meta/__init__.py` | This repo already uses `meta`/`meta_minimal`, not `meta_engine`; refusal logging is runtime meta-observability, not post-hoc learning only |
| `forecast_normalizer.py` | doc 19 line 106; doc 20 lines 51 -> 57 | `src/scoring_backbone/forecast_normalizer.py` | `src/scoring_backbone/forecast_normalizer.py` | Path fits current architecture |
| `break_even_filter.py` | doc 19 line 107; doc 20 lines 57, 255 -> 258 | `src/scoring_backbone/break_even_filter.py` | `src/scoring_backbone/break_even_filter.py` | Path fits current architecture |
| `cost_drift_monitor` | doc 19 line 108; doc 20 lines 153, 258 | `src/meta_engine/cost_drift_monitor/` | `src/meta_minimal/cost_drift_monitor/` or `src/meta_learning/cost_drift_monitor/`; prefer `meta_minimal` if runtime alerts are immediate, `meta_learning` if batch review-driven | The repo has no `meta_engine`; choose runtime meta path if it must alert live |
| `model_risk_registry` | doc 19 line 126; doc 20 lines 153, 265 | `src/meta_engine/model_risk_registry/` | `src/meta_learning/model_risk_registry/` | This is promotion and artifact governance, not a hot-path runtime primitive |
| `strategy_drift_monitor` | doc 19 line 127; doc 20 lines 154, 266 | `src/meta_engine/strategy_drift_monitor/` | `src/meta_learning/strategy_drift_monitor/` with a runtime-facing adapter/hook if needed | It belongs near review/governance and promotion evidence |
| `engine_coordination_rules` | doc 19 line 128; doc 20 lines 394 -> 416 | `src/meta_engine/engine_coordination_rules/` | `src/protocols/engine_coordination_rules.py` or `src/protocols/engine_coordination_rules/` plus contract types in `src/interface_contracts/` | Current cross-engine C/D validation groundwork already lives in `protocols/`; this is where conditioning belongs operationally |
| residualized momentum feature | doc 19 line 129 | `src/data_backbone/cross_sectional/residualized_momentum.py` | same path is acceptable | This is a data feature, not an engine |
| revised Carver vol targeting | doc 19 line 139 | `allocation_router/vol_target_sizer.py` | `src/portfolio_minimal/allocation_router/vol_target_sizer.py` | Actual portfolio path is `portfolio_minimal/allocation_router/`, not a floating top-level `allocation_router/` |
| `regime_change_detector` | doc 19 lines 140 -> 141 | `src/risk_backbone/regime_change_detector/` | same path is acceptable | Fits existing `risk_backbone` style |
| `tail_risk_meter` | doc 19 line 144; doc 20 lines 229 -> 230 | `src/risk_backbone/tail_risk_meter/` | same path is acceptable | Fits existing `risk_backbone` style |
| `crowding_suspicion_monitor` | doc 19 line 145; doc 20 lines 156, 281 | `src/meta_engine/crowding_suspicion_monitor/` | `src/meta_learning/crowding_suspicion_monitor/` | Cross-engine longitudinal overlap monitoring aligns with review/governance surfaces |
| `regime_shift_watcher` | doc 19 line 146; doc 20 lines 157, 282 | `src/risk_backbone/regime_shift_watcher/` | same path is acceptable | Fits risk backbone |
| `hybrid_router` | doc 19 line 154 | `execution_backbone/order_decider/hybrid_router.py` | `src/execution_backbone/order_decider/hybrid_router.py` | Path matches current execution stack |
| `twap_decomposer` | doc 19 line 155 | `execution_backbone/twap_decomposer.py` | `src/execution_backbone/twap_decomposer.py` or `src/execution_backbone/order_decider/twap_decomposer.py`; prefer top-level `execution_backbone` if shared beyond decision step | Keep execution slicing separate from basic order-type selection |
| `PortfolioArbitrationRecord` | doc 19 line 157; doc 20 line 287 | `src/portfolio_minimal/arbitration_record.py` | `src/portfolio_minimal/arbitration_record.py` + `src/portfolio_minimal/portfolio_orchestrator.py` integration | Matches actual portfolio stack |
| Engine C doctrinal continuation spec | doc 21 | greenfield `engine_c/*` files | evolve `src/engines/engine_c/structure_resolver_c.py`, `signal_math_c.py`, `conviction_builder_c.py`, `cost_feasibility_c.py`, `invalidation_mapper_c.py`, `engine_c_runtime.py`; add only missing files where current stack cannot express the new semantics | C already exists; a parallel C stack would be architectural duplication |
| Engine D doctrinal re-entry spec | doc 22 | greenfield `engine_d/*` files | evolve `src/engines/engine_d/context_resolver_d.py`, `signal_math_d.py`, `conviction_builder_d.py`, `cost_feasibility_d.py`, `invalidation_mapper_d.py`, `engine_d_runtime.py`; add history helpers only where current stack lacks semantics | D already exists; keep continuity with current hooks and lineage fields |
| Canonical microstructure package | doc 23 | `src/data_backbone/microstructure/*` | same path is correct, then wire consumers in `engines/*`, `complete_enablers/*`, and `scoring_backbone/*` | Doc 23 is genuinely new code |

## 6. Quant / trader verdict

### 6.1 What is genuinely strong in the update set

- The Carver `forecast -> normalized forecast -> vol target -> capped size` chain is intellectually correct and improves comparability across engines.
- Narang-style conditioning and portfolio grammar are the right answer for a multi-engine system. The current repo still talks mostly through simplified contracts.
- Taleb-style refusal logging and parity discipline are necessary if this is meant for production and not only for backtest aesthetics.
- Doc 23 is directionally strong. OFI, VPIN, queue pressure, realized kernel vol, Kyle lambda, and spread diagnostics are the right family for modern crypto microstructure work.

### 6.2 What is dangerous if implemented naively

- Replacing the canonical `SignalCandidate` in one jump would create a broad uncontrolled refactor across engines, scoring, risk, portfolio, execution, and tests.
- Treating Engine C and Engine D as if they did not exist would waste real groundwork already present in the repo and create forked logic.
- Building execution sophistication (`hybrid_router`, TWAP) before economics truth (`break_even_filter`, cost drift, refusal logging, arbitration record) is the wrong order.
- Building doc 23 features as isolated research files without a registry, calibration seam, and consumers would create another dead package.

### 6.3 My trading-system judgment

If this were my production system, I would call docs 19 -> 23 intellectually valid but operationally unsafe unless landed in this exact order:

1. contract seam
2. refusal logging seam
3. canonical microstructure registry and 4 upstream features
4. economics seam (`forecast_normalizer`, `break_even_filter`)
5. coordination seam
6. only then doctrinal deepening of C and D

That order is the difference between a real institutional refactor and a research hallucination.

## 7. Hard execution order from here

### Phase A - freeze the truth seam

1. Update doc 18 mentally to historical status only.
2. Accept that doc 19 line 52 is stale.
3. Freeze a single truth table of `DONE / PARTIAL / MISSING`.

Completion proof:

- this document exists
- every future task references a real path and a real owner seam

### Phase B - contract before features

1. Extend the canonical decision contract seam for Narang fields.
2. Add `RefusalRecord`.
3. Add `RefusalJournal`.

Completion proof:

- A/B/C/D can still emit without breakage
- current tests still construct the contract
- blocked or refused paths can be logged without inventing fake trades

### Phase C - canonical microstructure package

Implement doc 23 in the exact order of lines 391 -> 398:

1. `feature_registry.py`
2. `realized_kernel_vol.py`
3. `order_flow_imbalance.py`
4. `vpin.py`
5. `queue_pressure.py`
6. `kyle_lambda.py`, `amihud_illiquidity.py`
7. `hawkes_intensity.py`
8. diagnostics-only features after that

Completion proof:

- package exists under `src/data_backbone/microstructure/`
- registry is canonical
- at least one current engine or Build-14 reader consumes the canonical outputs

### Phase D - economics and drift

1. `forecast_normalizer.py`
2. `break_even_filter.py`
3. `cost_drift_monitor`

Completion proof:

- expected cost, expected break-even, expected CE, and EV-net have one canonical meaning
- no engine emits when economics are structurally negative

### Phase E - coordination before C/D doctrinal refactor

1. `engine_coordination_rules`
2. strategy beta rule for D
3. refusal logging for hard blocks

Completion proof:

- A/C overlap hard-block works
- D without first-episode linkage is impossible
- D consecutive-stop reset rule is stateful and auditable

### Phase F - only now deepen engines

1. Engine B toxic-flow fade as sub-signal
2. Engine C doctrinal continuation upgrade
3. Engine D doctrinal second-chance upgrade

Completion proof:

- C uses canonical OFI / queue / VPIN / realized-kernel evidence
- D uses historical linkage, first episode resolution, and strategy beta
- neither engine creates a parallel contract or bypass path

### Phase G - risk, portfolio, execution sophistication

1. `model_risk_registry`
2. `strategy_drift_monitor`
3. `tail_risk_meter`
4. `regime_shift_watcher`
5. `crowding_suspicion_monitor`
6. `PortfolioArbitrationRecord`
7. `hybrid_router`
8. `twap_decomposer`

Completion proof:

- every promoted trade answers the portfolio questions
- every execution sophistication layer has a cost and refusal audit

## 8. Anti-hallucination operating rules

Use these rules for every future session:

1. Never mark a task as done because the doc says it exists. Mark it done only if the code file exists and has a real caller.
2. Never mark a task as done because unit tests are green. A feature is done only when there is code, tests, and a runtime or artifact consumer.
3. Never say "drop-in replacement" for `SignalCandidate` unless all four runtimes and downstream consumers are migrated.
4. Never create `meta_engine/` unless the repo is explicitly restructured. Use existing packages.
5. Never treat Engine C or D as greenfield again. They are already real codebases.
6. Never add thresholds to the catalog before the consuming module exists.
7. Never say "shadow gate green" because the script exists. The gate is green only when the report evidence passes.
8. Every new task must cite:
   - source doc and line range
   - target file
   - current code seam
   - proof of completion

## 9. Immediate next slices recommended

Recommended next three slices, in order:

1. `RefusalRecord` + `RefusalJournal`
2. canonical contract seam for enriched `SignalCandidate`
3. `data_backbone/microstructure/feature_registry.py` + `realized_kernel_vol.py`

Do not start Engine C or Engine D doctrinal rewrites before these three slices are green.

## 10. Final synthesis

Docs 19 -> 23 contain a strong update program, but not all of it should be taken literally.

- Some items are already done and must be removed from the active backlog.
- Some items are valid but must land in different packages than the docs propose.
- The contract seam is the main upstream dependency.
- Engine C and D are continuation/refinement work, not greenfield work.
- Doc 23 is the cleanest genuinely new package and should be treated as foundational infrastructure.

This document is therefore the surgical landing map that should govern future implementation, not the raw prose of docs 19 -> 23 taken at face value.
