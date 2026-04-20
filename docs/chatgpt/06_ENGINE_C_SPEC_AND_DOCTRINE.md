# 06_ENGINE_C_SPEC_AND_DOCTRINE

## Included Source Docs
- docs/production_deployment_plan/21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md
- docs/production_deployment_plan/27_OPUS_TO_CODEX_AUDIT_DOCS21_22_PASS2.md
- docs/production_deployment_plan/update_audit/2026-04-16_engine_c_continuation_microstructure_wiring.md

---

## Source: docs/production_deployment_plan/21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md

# 21 — Engine C Specification: Breakout Continuation

**Status**: SPEC — doctrinal deepening of an existing Engine C implementation, gated by doc 20 §11 `engine_coordination_rules` being green.
**Date**: 2026-04-15
**Parent canon**: V5.3; companion: docs 19, 20, 22, 23.
**Version pin**: `doc_23@834f7fae4a06847121670559dd5bfd65c28d82da`
**Scope**: full Narang-grade specification for Engine C, distinct from Engine A (initial detection) and from Engine B (mean-reversion). This is **not** a greenfield engine spec: `src/engines/engine_c/` already exists and must be evolved surgically.

---

## 0. One-line definition (user doctrine, doc 20 §13.1)

> **C = Breakout Continuation** — "capter des sorties de range et des continuations post-breakout, *seulement si* cette continuation n'est pas déjà absorbée par A."

Engine C fires on the **continuation leg** after a breakout, when A is not holding the same (pair, direction) and the continuation is not duplicating A's exposure.

---

## 1. Structural separation vs A (mandatory)

| Dimension | A (Premium Trend / Expansion) | C (Breakout Continuation) |
|---|---|---|
| Triggering event | Initial trend expansion / first clean breakout from consolidation | Continuation leg **after** a breakout already occurred (possibly captured or missed by A) |
| Time window of detection | Contemporaneous with breakout formation | Post-breakout: t ∈ [breakout_t + 1 bar, breakout_t + continuation_window] where continuation_window ≤ 4h (medium horizon) |
| Conviction profile | High — premium conviction, Tier-3 compatible, `forecast_strength ∈ [0, 20]` | Medium — `forecast_strength ∈ [0, 15]` |
| Bet structure | `BREAKOUT` or `DIRECTIONAL_{LONG,SHORT}` | `BREAKOUT` (continuation variant) |
| Mutual exclusion | — | **HARD_BLOCK** if A holds same (pair, direction) within THR-X08, or A recently exited same setup within THR-X09 (doc 20 §11 rules R-AC-1/R-AC-2) |

If these rules are violated → append `ConditioningRecord(family=HARD_BLOCK, code="hard_block.ac_mutual_exclusion.*")` + `RefusalRecord(category=HARD_BLOCK)`, and emit **no** canonical `SignalCandidate`. **Never a soft penalty.**

---

## 2. Surgical landing map onto the existing `engine_c/` implementation

```
src/engines/engine_c/
├── __init__.py
├── engine_c_runner.py                  # existing runner; keep as orchestration seam
├── engine_c_runtime.py                 # existing runtime; current SignalCandidate builder seam
├── structure_resolver_c.py             # existing breakout-reference / structure seam to evolve first
├── signal_math_c.py                    # existing continuation math seam; may absorb OFI/VPIN/queue logic first
├── conviction_builder_c.py             # existing conviction seam
├── cost_feasibility_c.py               # existing cost seam; extend with break-even filter
├── invalidation_mapper_c.py            # existing invalidation seam
├── output_payload_builder_c.py         # existing payload seam
├── a_exclusion_guard_c.py              # REQUIRED — isolation of R-AC coordination logic is a testable contract seam
├── continuation_validator_c.py         # REQUIRED — keeps continuation math testable outside the runtime facade
└── signal_reporter_c.py                # OPTIONAL — may stay inside `engine_c_runtime.py` if the facade remains surgical

tests/test_engines/test_engine_c/
├── existing Engine C tests remain authoritative
├── add targeted tests for structure / continuation / exclusion / cost / invalidation
└── do not create a parallel Engine C test stack detached from the current runtime
```

---

## 3. Signal pipeline (stage by stage)

### Stage 1 — `structure_detector_c.py`
Detects a completed **breakout reference event** in a trailing window of length `THR-C_LOOKBACK` (default 1h, cap 4h). A breakout reference is:
- Long: price closed ≥ `upper_range_high + k × ATR_equivalent_realized_vol` where `ATR_equivalent_realized_vol` uses realized kernel volatility (Barndorff-Nielsen, doc 23 §3.5), not 1990s ATR.
- Short: mirror.

Output: `BreakoutReference(t_break, level, direction, realized_vol_at_break, queue_state_at_break)`.

### Stage 2 — `continuation_validator_c.py`
Validates that *now* is a valid continuation moment:
1. Price holding above breakout level: no bar close back below `level − ε` since `t_break`.
2. Microstructure confirmation: cumulative OFI (doc 23 §3.1) in break direction ≥ `THR-C_OFI_MIN` over last N events.
3. Queue state: top-of-book on continuation side shows ≥ `THR-C_QUEUE_MIN` notional (no thin-book trap).
4. VPIN not in toxic regime (doc 23 §3.2): if VPIN > `THR-C_VPIN_MAX` → skip (toxic flow = likely fade setup, not continuation). [Rang 1 + 2] no crypto-specific rank-1 paper threshold fixes `THR-C_VPIN_MAX = 0.5`, so the authoritative value is `TBD_shadow_calibration` until shadow evidence closes it.

Output: `ContinuationValidation(accepted: bool, reason_codes: tuple[str, ...])`.

### Stage 3 — `a_exclusion_guard_c.py` (required helper)
Queries `engine_coordination_rules`:
- Is A holding (pair, direction) now? → HARD_BLOCK, append refusal, emit no canonical SignalCandidate.
- Did A fire on the same structural setup within THR-X09? → HARD_BLOCK.
- `same_structural_setup` matching: same (pair, direction) AND `breakout_reference.level` within ±0.5 × `realized_vol_at_break` of A's entry level.

Output: `AExclusionVerdict(blocked: bool, rule_fired: Literal["R-AC-1", "R-AC-2", None], conditioning_record: ConditioningRecord | None)`.

### Stage 4 — `conviction_builder_c.py` (Carver-normalised)
Builds `forecast_direction ∈ [−1, 1]` and raw `forecast_strength_raw`. Then **Carver normalisation** via `forecast_normalizer` (doc 19 P2-07):
```
forecast_strength_normalised = (forecast_strength_raw / E[|F_raw|_C]) × 10
```
then clip to [0, 15] (doc 20 §11.4).

Signals fed into raw:
- Continuation strength = (current_price − breakout_level) / realized_vol_at_break.
- OFI persistence since t_break.
- Queue pressure direction (Kyle λ estimate, doc 23 §3.3).

**Forbidden inputs** (doc 23 §6): RSI, MACD, Stochastic, Bollinger, Williams %R, parabolic SAR. Hard contract check at unit-test level.

### Stage 5 — `cost_feasibility_c.py`
Applies `break_even_filter` (doc 19 P2-08) with C-specific expected-cost model. If `EV^net ≤ THR-W01_floor` → no emit + `RefusalRecord(category=NO_TRADE, reason_codes=("c.break_even.fail",))`.

### Stage 6 — `invalidation_mapper_c.py`
Structural invalidation = return below breakout level by more than `THR-C_INVALIDATION_VOL × realized_vol_at_break` (default 1.0, cap 2.0). Stored as `InvalidationContract` with `invalidation_ref` wired into `SignalCandidate`.

### Stage 7 — enriched signal assembly seam (`signal_reporter_c.py` additively, or `engine_c_runtime.py` surgically)
Assembles:
```python
SignalCandidate(
    strategy_id=StrategyIdentity.resolve(engine_id="C", pair=P, regime=regime, ...).identity_str,
    engine_id="C",
    pair=P,
    side=<buy|sell>,
    forecast_direction=...,
    forecast_strength=...,                      # normalised, clipped [0, 15]
    forecast_horizon_class=ForecastHorizonClass.MEDIUM,
    forecast_target_class=ForecastTargetClass.DIRECTION_PLUS_STRENGTH_PLUS_HORIZON,
    bet_structure=BetStructure.BREAKOUT,        # continuation variant
    confidence_band=...,
    conditioning_state=(... A_exclusion_record, ..., cost_record),
    expected_cost=...,
    expected_break_even=...,
    expected_ce=...,
    expected_gain=...,
    invalidation_ref=<InvalidationContract.id>,
    reason_codes=("c.continuation.ofi_persistence", "c.microstructure.queue_ok", ...),
    versions={"engine_c": "0.1.0", "calibration": "<hash>", ...},
)
```

---

## 4. Conditioning state (Narang §3.3 family placement)

| Check | Family | Example code |
|---|---|---|
| A holds same (pair, direction) | HARD_BLOCK | `hard_block.ac_mutual_exclusion.a_holding` |
| A exited same setup < THR-X09 | HARD_BLOCK | `hard_block.ac_recent_fire` |
| Pair health / data freshness | HARD_BLOCK | `hard_block.pair_health.stale_book` |
| Structure quality below min | ENGINE_INTERNAL | `engine_internal.c.structure_weak` |
| VPIN toxic | ENGINE_INTERNAL | `engine_internal.c.vpin_toxic` |
| Cost > EV floor | SCORING | `scoring.cost_penalty.break_even_fail` |
| Correlation cluster full | PORTFOLIO | `portfolio.cluster_budget_exhausted` |

---

## 5. Thresholds (governed; calibrated where marked)

**P1-5 authoritative replacement table [Rang 1 + 2]**: the compact legacy table below is now superseded for implementation. Use this table for formulas, defaults, hard caps, and calibration seams.

| ID | Meaning | Default | Hard cap | Module | Calibration module |
|---|---|---|---|---|---|
| THR-X08 | A→C mutual exclusion window | 2h | 12h | `engine_coordination_rules` (doc 20 §11) | `— (policy-governed)` |
| THR-X09 | A recent-fire suppression | 4h | 24h | `engine_coordination_rules` (doc 20 §11) | `— (policy-governed)` |
| THR-C_LOOKBACK | Breakout-reference lookback window | 1h | 4h | `structure_detector_c` | `risk_runtime_drawdown_calibration.py` |
| THR-C_OFI_MIN | Min cumulative OFI persistence | calibrated | — | `continuation_validator_c` | `risk_runtime_drawdown_calibration.py` |
| THR-C_QUEUE_MIN | Min top-of-book notional | calibrated | — | `continuation_validator_c` | `risk_runtime_drawdown_calibration.py` |
| THR-C_VPIN_MAX | Max VPIN before toxic skip | TBD_shadow_calibration | — | `continuation_validator_c` | `risk_runtime_drawdown_calibration.py` |
| THR-C_INVALIDATION_VOL | Invalidation vol multiple | 1.0 | 2.0 | `invalidation_mapper_c` | `risk_runtime_drawdown_calibration.py` |
| THR-C_RK_BANDWIDTH_C | Realized-kernel bandwidth constant `c` | 0.4 | 1.0 | `structure_detector_c` | `risk_runtime_drawdown_calibration.py` |
| THR-C_RK_BUCKET_SIZE | Realized-kernel bucket duration | 5 min | 15 min | `structure_detector_c` | `risk_runtime_drawdown_calibration.py` |
| THR-C_OFI_WINDOW | OFI cumulation window (events) | 500 events | 2000 events | `continuation_validator_c` | `risk_runtime_drawdown_calibration.py` |
| THR-C_KYLE_WINDOW | Kyle λ regression window | 1h | 4h | `continuation_validator_c` | `risk_runtime_drawdown_calibration.py` |
| THR-C_VPIN_BUCKETS | VPIN equal-volume bucket count | 50 buckets/day | 100 buckets/day | `continuation_validator_c` | `risk_runtime_drawdown_calibration.py` |

All calibrated `THR-C_*` rows above land through `risk_runtime_drawdown_calibration.py`; `THR-X08/THR-X09` remain policy-governed coordination rails. Any residual legacy mention of `THR-C_VPIN_MAX ≤ 0.5` below is superseded by this authoritative table because no crypto-specific rank-1 threshold source was found.

| ID | Meaning | Default | Hard cap | Module |
|---|---|---|---|---|
| THR-X08 | A↔C mutual exclusion window | 2h | 12h | `engine_coordination_rules` (doc 20 §11) |
| THR-X09 | A recent-fire suppression | 4h | 24h | `engine_coordination_rules` (doc 20 §11) |
| THR-C_LOOKBACK | Breakout-reference lookback window | 1h | 4h | `structure_detector_c` |
| THR-C_OFI_MIN | Min cumulative OFI persistence | calibrated | — | `continuation_validator_c` |
| THR-C_QUEUE_MIN | Min top-of-book notional | calibrated | — | `continuation_validator_c` |
| THR-C_VPIN_MAX | Max VPIN before toxic skip | superseded by authoritative table above | — | `continuation_validator_c` |
| THR-C_INVALIDATION_VOL | Invalidation vol multiple | 1.0 | 2.0 | `invalidation_mapper_c` |

All follow the calibration-seam pattern (`risk_runtime_drawdown_calibration.py`).

---

## 6. Test matrix (minimum to land)

**P1-5 paper-repro extension [Rang 1]**: the base suites below remain required, and the following paper-reproduction suites are now mandatory additions.

**P1-6 authoritative replacement matrix [Rang 2]**: use the matrix below for implementation planning. The compact legacy matrix retained lower in this section is audit history only.

| Suite | Min tests | Focus | Hypothesis | Paper repro |
|---|---|---|---|---|
| `test_structure_detector_c.py` | 8 | Synthetic breakout + no-breakout; realized-vol scaling | yes | — |
| `test_continuation_validator_c.py` | 10 | OFI persistence + queue + VPIN toxic skip | yes | — |
| `test_a_exclusion_guard_c.py` | 8 | R-AC-1 hits, R-AC-2 hits, both clear, edge cases at THR boundary | yes | — |
| `test_conviction_builder_c.py` | 6 | Carver normalisation `E[|F|] ≈ 10` then clip to [0, 15] | yes | — |
| `test_cost_feasibility_c.py` | 4 | Break-even pass/fail | — | — |
| `test_invalidation_mapper_c.py` | 4 | Structural invalidation triggers | yes | — |
| `test_signal_reporter_c.py` | 6 | Full SignalCandidate assembly contract validity | — | — |
| `test_engine_c_runtime.py` | 4 | End-to-end with fixtures | — | — |
| `test_realized_kernel_repro.py` | 1 | Fixed-seed simulation reproduces Barndorff-Nielsen et al. (2008) Table 1 order of magnitude | — | yes |
| `test_ofi_repro.py` | 1 | OFI sign follows Cont-Kukanov-Stoikov directional prediction under bid-up / ask-down queue updates | — | yes |
| `test_kyle_lambda_repro.py` | 1 | `lambda_hat > 0` under informed-flow synthetic data consistent with Kyle (1985) eq.(1) | — | yes |
| `test_vpin_repro.py` | 1 | VPIN tends to 1.0 under 100% one-sided informed flow | — | yes |
| **Total** | **≥ 54** | | | |

| Suite | Min tests | Focus |
|---|---|---|
| `test_realized_kernel_repro.py` | 1 | Paper repro: Barndorff-Nielsen et al. (2008) Table 1 order of magnitude on fixed-seed simulation |
| `test_ofi_repro.py` | 1 | Paper repro: Cont-Kukanov-Stoikov directional sign under bid-up / ask-down queue updates |
| `test_kyle_lambda_repro.py` | 1 | Paper repro: Kyle linear-impact prediction with `lambda_hat > 0` under informed-flow synthetic data |
| `test_vpin_repro.py` | 1 | Paper repro: VPIN tends to 1.0 under 100% one-sided informed flow |

These four suites raise the minimum C landing bar from `≥ 50` to `≥ 54` tests.

| Suite | Min tests | Focus |
|---|---|---|
| `test_structure_detector_c.py` | 8 | Synthetic breakout + no-breakout; realized-vol scaling |
| `test_continuation_validator_c.py` | 10 | OFI persistence + queue + VPIN toxic skip |
| `test_a_exclusion_guard_c.py` | 8 | R-AC-1 hits, R-AC-2 hits, both clear, edge cases at THR boundary |
| `test_conviction_builder_c.py` | 6 | Carver normalisation `E[|F|] ≈ 10` then clip to [0, 15] |
| `test_cost_feasibility_c.py` | 4 | Break-even pass/fail |
| `test_invalidation_mapper_c.py` | 4 | Structural invalidation triggers |
| `test_signal_reporter_c.py` | 6 | Full SignalCandidate assembly contract validity |
| `test_engine_c_runtime.py` | 4 | End-to-end with fixtures |
| **Total** | **≥ 50** | |

---

## 7. Prohibitions specific to Engine C

1. **No** emission while A holds same (pair, direction) within THR-X08. Never a soft penalty.
2. **No** 1990s TA indicator as trigger (RSI, MACD, Stochastic, Bollinger, Williams, CCI, DMI, parabolic SAR). Doc 23 §6 applies.
3. **No** re-use of A's structure detector logic — C has its own post-breakout-reference detector.
4. **No** override by ML enabler (doc 19 P3-X).
5. **No** calibration of THR-X08 / THR-X09 below default via operator toggle — only via full calibration pipeline with shadow parity check.
6. **No** live deployment before the A-exclusion guard has been shadow-verified for ≥ 2 weeks with zero R-AC violations leaking through.

---

## 8. Promotion pipeline for C

C follows the same pipeline as every V5.3 engine:

`Replay → Shadow (≥ 4 weeks, universe ≥ 20 pairs) → Micro-live (tier-bounded) → Live-Light (T3+)`

Promotion to Live-Light requires:
- Quadruple filter green (doc 20 §4.2).
- `engine_coordination_rules` audit: 0 R-AC-1 / R-AC-2 violations in shadow window.
- Sharpe-deflated shadow Sharpe ≥ 1.0 on ≥ 50 trades, using Harvey-Liu-Zhu 2016 eq.(8) `SR_deflated = SR × √((N−k_HLZ)/(N−1))`; [Rang 1 + 2 + 4] current V5.3 `multiple_testing_guard.py` seam exposes two explicit modes: `k_HLZ = pairs_tested` in observed-shadow mode and `k_HLZ = max(pairs_tested, 20)` in promotion-floor mode. The current docs 21/22 default is the user-selected observed-shadow mode, so the current numeric default is `k_HLZ = pairs_tested` (currently `12` in the repo pair catalogue), while `promotion_floor` remains an explicit conservative non-default option (module blob `b2aafc74bd5abdefc8810e69f1562e9cc6881007`).
- `expected_cost` vs `realised_cost` drift ≤ THR-D01 (20%).
- Cross-regime stability ≥ 3 buckets (doc 20 §4.2).

---

## Annexe A — Formules microstructure — specification complete

Every formula below is rank-1 sourced. Parameter defaults/caps are V5.3-governed values; calibration lands through `risk_runtime_drawdown_calibration.py`.

### A.1 Realized kernel volatility — Barndorff-Nielsen, Hansen, Lunde, Shephard (2008)

**Paper source [Rang 1]**: *Designing Realized Kernels to Measure the Ex-Post Variation of Equity Prices in the Presence of Noise*, Econometrica 76(6), eq.(3.1)–(3.7), DOI `10.3982/ECTA6495`.

**Operational form used in V5.3**:

```text
RK_t = gamma_0 + sum_{h=1}^{H} k_P((h - 1) / H) * (gamma_h + gamma_{-h})
gamma_h = sum_{j=h+1}^{n} r_j * r_{j-h}
r_j = log(P_j) - log(P_{j-1})

k_P(x) = 1 - 6x^2 + 6|x|^3      for 0 <= |x| <= 1/2
       = 2(1 - |x|)^3           for 1/2 < |x| <= 1
       = 0                      for |x| > 1

H = ceil(c * n^(3/5))
```

**Variables**:
- `P_j`: bucket-close price at bucket `j`
- `r_j`: log-return on bucket `j`
- `gamma_h`: realized autocovariance of lag `h`
- `H`: kernel bandwidth
- `n`: number of buckets in the estimation window
- `k_P(.)`: flat-top Parzen kernel

**Parameters**:
- `THR-C_RK_BANDWIDTH_C = 0.4` default, hard cap `1.0`, calibration seam `risk_runtime_drawdown_calibration.py`
- `THR-C_RK_BUCKET_SIZE = 5 min` default, hard cap `15 min`, calibration seam `risk_runtime_drawdown_calibration.py`

### A.2 Order Flow Imbalance (OFI) — Cont, Kukanov, Stoikov (2014)

**Paper source [Rang 1]**: *The Price Impact of Order Book Events*, Journal of Financial Econometrics 12(1), eq.(1)–(3), DOI `10.1093/jjfinec/nbt003`.

**Operational form used in V5.3**:

```text
e_n = 1{P^b_n >= P^b_{n-1}} * q^b_n
    - 1{P^b_n <= P^b_{n-1}} * q^b_{n-1}
    - 1{P^a_n <= P^a_{n-1}} * q^a_n
    + 1{P^a_n >= P^a_{n-1}} * q^a_{n-1}

OFI_t(N) = sum_{n=t-N+1}^{t} e_n
```

**Variables**:
- `(P^b_n, q^b_n)`: best bid price and displayed size at event `n`
- `(P^a_n, q^a_n)`: best ask price and displayed size at event `n`
- `e_n`: signed contribution of order-book event `n`
- `OFI_t(N)`: cumulative imbalance over the last `N` events

**Parameters**:
- `THR-C_OFI_WINDOW = 500 events` default, hard cap `2000 events`, calibration seam `risk_runtime_drawdown_calibration.py`

### A.3 Kyle λ — Kyle (1985) linear impact relation

**Paper source [Rang 1]**: *Continuous Auctions and Insider Trading*, Econometrica 53(6), eq.(1), DOI `10.2307/1913210`.

**Paper relation**:

```text
p_t = v_t + lambda * y_t
```

where `y_t` is signed aggregate order flow and `lambda` is the linear price-impact coefficient.

**V5.3 estimation seam [Rang 2 operationalisation of the rank-1 relation]**:

```text
Delta m_t = lambda_hat * SignedVolume_t + epsilon_t
```

estimated by rolling OLS on the current microstructure window.

**Variables**:
- `m_t`: mid-price
- `Delta m_t`: mid-price change over interval `t`
- `SignedVolume_t`: signed net volume over interval `t`
- `lambda_hat`: rolling impact estimate used by Engine C

**Parameters**:
- `THR-C_KYLE_WINDOW = 1h` default, hard cap `4h`, calibration seam `risk_runtime_drawdown_calibration.py`

### A.4 VPIN — Easley, Lopez de Prado, O'Hara (2012)

**Paper source [Rang 1]**: *Flow Toxicity and Liquidity in a High-Frequency World*, Review of Financial Studies 25(5), eq.(2)–(4), DOI `10.1093/rfs/hhs053`.

**Operational form used in V5.3**:

```text
V_bucket = DailyVolume / B
V_tau^B = V_bucket * Z(Delta p_tau / sigma_{Delta p})
V_tau^S = V_bucket - V_tau^B
VPIN_n = (1 / (n * V_bucket)) * sum_{tau=1}^{n} |V_tau^B - V_tau^S|
```

**Variables**:
- `B`: equal-volume bucket count per day
- `V_bucket`: target volume per bucket
- `Delta p_tau`: price change over bucket `tau`
- `sigma_{Delta p}`: volatility of bucket price changes used by bulk-volume classification
- `V_tau^B`, `V_tau^S`: estimated buy and sell volume in bucket `tau`
- `Z(.)`: standard normal CDF
- `VPIN_n`: toxicity estimate over the rolling `n` buckets

**Parameters**:
- `THR-C_VPIN_BUCKETS = 50 buckets/day` default, hard cap `100 buckets/day`, calibration seam `risk_runtime_drawdown_calibration.py`
- rolling bucket window `n = 50` default, hard cap `100`, calibration seam `risk_runtime_drawdown_calibration.py`

---

**Status**: SPEC COMPLETE. Doctrinal deepening is blocked until doc 19 P3-10 (`engine_coordination_rules`) is merged + shadow-verified.


---

## Source: docs/production_deployment_plan/27_OPUS_TO_CODEX_AUDIT_DOCS21_22_PASS2.md

# 27 — Opus → Codex : Audit docs 21 & 22 + brief pass-2

**Date** : 2026-04-16 (rev-2 aligné sur docs 25/26/28)
**Auteur** : Opus (critical audit)
**Destinataire** : Codex (implementation + doc revision)
**Statut audit** : PARTIAL — ACCEPT-WITH-FIXES
**Score global** : 7.5/10
**Cibles auditées** : `21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md` + `22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md` (post-édition Codex)
**Fonction du doc** : canal de communication Opus ↔ Codex. Toute exécution Codex sur les fixes ci-dessous doit référencer ce doc par son numéro (doc 27) dans les commits et rapports.
**Protocoles référencés** :
- doc 25 `25_UPDATE_AUDIT_PROTOCOL.md` (format audit pack)
- doc 26 `26_UPDATE_AUDIT_PACK_TEMPLATE.md` (template audit pack)
- doc 28 `28_ARBITRATION_PROTOCOL_OPUS_CODEX.md` (résolution des désaccords, 4 rangs d'autorité)

**Audit pack compagnon** : `docs/production_deployment_plan/update_audit/2026-04-16_docs21_22_opus_audit.md`

---

## Convention de marquage (lecture obligatoire)

Dans ce doc, chaque proposition est étiquetée :

- **`CONSTRAINT_DOCTRINAL`** — rang 1 (littérature) ou rang 2 (canon V5.3) au sens doc 28. **Non-négociable.** Codex applique tel quel.
- **`PROPOSAL_OPUS`** — suggestion Opus **sans** rang 1/2 sourcé. Codex doit soit (a) trouver un rang 1/2 qui la confirme, soit (b) proposer une alternative rang 1/2, soit (c) ouvrir un bloc Dispute (doc 28 §5) et escalader rang 3 (shadow) ou rang 4 (user).
- **`CODEX_TO_MEASURE`** — valeur à extraire du code existant par Codex (pas une proposition Opus). Codex lit, rapporte, pas d'invention.

Toute formule ou constante non étiquetée est lue par défaut comme `PROPOSAL_OPUS`. Si Codex détecte un doute sur le marquage, il ouvre un bloc Dispute.

---

## 0. Règles de collaboration

1. Codex applique les P0 avant tout merge ; les P1 peuvent être pipelinés en PR séparée.
2. Chaque fix produit une entrée datée en §8 "Journal d'exécution Codex" + une entrée audit pack compagnon.
3. Pas de `silent strategy change` : toute substitution de formule/constante non listée ici requiert un bloc Dispute (doc 28).
4. TEXT ONLY quand Codex répond à un audit ; CODE + DOC pour les fixes.
5. Source of truth doctrinale : docs 19, 20, 23 + `CLAUDE.md`. Ce doc 27 ne peut pas les contredire.
6. **Désaccord Opus ↔ Codex** → protocole doc 28. Ni l'un ni l'autre ne tranche par opinion ; arbitrage par rang 1 (paper) > rang 2 (canon) > rang 3 (shadow) > rang 4 (user).
7. **Collision avec code existant** : si Codex trouve qu'un contrat/module proposé ici existe déjà partiellement ailleurs (ex : un `EpisodeMemory` dans `exit_pipeline`), il **ne fusionne pas silencieusement** — il ouvre un bloc Dispute pour arbitrer entre (a) reuse, (b) rename, (c) create-new-and-deprecate.
8. **Rollback** : chaque fix P0 devrait idéalement être un commit atomique sur une branche dédiée `fix/doc27-P0-<n>` pour rollback `git revert` propre. **Déviation acceptée pour ce pass** : Codex a appliqué les 4 P0 sur la branche existante `codex/full-shadow-abcd-migration-20260403` (340 fichiers modifiés). Les fichiers P0 sont identifiables par path (voir audit pack §Files Changed). Pour les futurs pass, la règle branche atomique reste recommandée.

---

## 1. Verdict d'audit

| Dimension | Score | Statut |
|---|---|---|
| Fidélité architecturale (canon V5.3, A/B/C/D, pas de greenfield) | 9/10 | ✅ |
| Fidélité MD (cohérence inter-docs 19/20/23) | 8/10 | ✅ |
| Code-quant (formules Carver, microstructure, HLZ) | 5/10 | ⚠️ |
| Stratégie (R-AC, R-D, strategy β, exclusion mutuelle) | 8/10 | ✅ |
| Objectifs Opus (side buy/sell, no meta_engine, calibration seam) | 9/10 | ✅ |
| Testabilité (contrats explicites, pyramide ≥50 tests) | 7/10 | ⚠️ |
| **Global pondéré** | **7.5/10** | **PARTIAL** |

---

## 2. Ce que Codex a BIEN fait (à conserver tel quel)

1. **Greenfield → doctrinal deepening** : les deux docs mappent correctement les fichiers existants (`src/engines/engine_c/`, `src/engines/engine_d/`). Ne pas régresser.
2. **`side="flat"` éliminé** : remplacé par `ConditioningRecord(family=HARD_BLOCK) + RefusalRecord(category=HARD_BLOCK)`, emit no canonical `SignalCandidate`. Conforme `Side ∈ {buy, sell}` (`src/interface_contracts/domain_types.py:150-153`).
3. **Test paths** : `tests/test_protocols/test_engine_coordination_rules/` (pas `test_meta_engine`). `src/meta_engine/` n'existe pas.
4. **Grammaire Narang 4-familles** respectée : `HARD_BLOCK | ENGINE_INTERNAL | SCORING | PORTFOLIO`.
5. **Strategy β** : pseudocode explicite doc 22 §4 (states + reset on fresh A + failsafe R-D-3).
6. **R-D-4 hardcodé** : sizing `0.5×` dans `vol_target_sizer`, pas calibration-driven.

---

## 3. P0 — BLOQUANTS (à corriger avant tout merge)

### P0-1. Définir `revenge_risk_penalty = f(...)` — doc 22 §3 Stage 4

**Problème** : doc 22 dit `revenge_risk_penalty = f(consecutive_stop_count, time_since_last_stop)` sans définir `f`. Un implémenteur choisira arbitrairement → `silent strategy change`.

**Rang d'autorité attendu (doc 28)** : rang 1 si littérature (prospect theory Kahneman-Tversky 1979, behavioral microstructure Lo-Repin 2002, Odean 1998 disposition effect) couvre une forme fonctionnelle exploitable ; sinon rang 4 (escalade user pour choix doctrinal).

**Action Codex — étape 1 (obligatoire)** : recherche rang 1, timebox 30 min. Rapport dans bloc Dispute `D-2026-04-16-001`. Sources à consulter :
- Kahneman-Tversky 1979 (prospect theory, loss aversion λ ≈ 2.25)
- Odean 1998 (disposition effect — reluctance to realize losses)
- Lo-Repin 2002 (psychophysiology of trading — revenge trading patterns)
- Coval-Shumway 2005 (do behavioral biases affect prices — loss-chasing)
- Linnainmaa 2010 (why do (some) households trade so much — revenge)

**Propositions Opus (étiquetées)** :

`PROPOSAL_OPUS` — forme exponentielle décroissante :
```
revenge_risk_penalty(n, Δt) = α · n² · exp(-Δt / τ)
  n  = consecutive_stop_count  (int, bornée à THR-X11)
  Δt = time_since_last_stop    (hours)
  α  = THR-D_REVENGE_SCALE     (default 0.25, cap 1.0, calibrated)
  τ  = THR-D_REVENGE_DECAY     (default 12h, cap 48h, calibrated)
```

`PROPOSAL_OPUS` — alternative linéaire-seuil :
```
revenge_risk_penalty(n, Δt) = α · n · max(0, 1 − Δt/τ)
```

**Aucune des deux n'est `CONSTRAINT_DOCTRINAL`.** Codex doit :
1. Appliquer étape 1 (recherche rang 1) avant toute implémentation.
2. Si rang 1 trouvé → utilise la forme du paper, écrit ça dans doc 22 Annexe A avec citation complète (author year eq DOI), et clôt la Dispute.
3. Si rang 1 non trouvé → bloc Dispute escaladé rang 4 avec options A/B/C (A = forme exponentielle Opus, B = linéaire-seuil Opus, C = alternative Codex sourcée).

**Propriétés minimales (CONSTRAINT_DOCTRINAL, quelle que soit la forme retenue)** :
- monotone croissante en `n`
- monotone décroissante en `Δt`
- bornée supérieurement (pas d'explosion)
- `n=0 ⇒ penalty=0`
- `lim_{Δt→∞} penalty = 0`

**Acceptance** : `marginal_value_estimator_d.py` implémente la formule arbitrée avec paramètres via calibration seam `risk_runtime_drawdown_calibration`. Test unitaire vérifiant les 5 propriétés ci-dessus + test `paper_repro` sur un cas figure du paper cité (si rang 1). Bloc Dispute `D-2026-04-16-001` clôturé `RESOLVED`.

### P0-2. Spécifier contrat `ClosedEpisodeJournal` + `EpisodeRef`

**Problème** : doc 22 §3 Stage 1 invoque `closed_episode_journal` sans contrat. N'existe dans aucun doc 19/20/23/24.

**Rang d'autorité attendu (doc 28)** : rang 2 — dérivation directe de la grammaire Narang (doc 20 §3) + Pydantic V5.3 patterns (`SignalCandidate`, `RefusalRecord`). Pas de controverse scientifique, seulement discipline de contrat.

**Étape 0 obligatoire (CODEX_TO_MEASURE)** : avant d'implémenter, Codex **scan le repo** pour détecter l'existence partielle :
```bash
rtk grep -r "episode_memory\|closed_episode\|episode_journal\|EpisodeRef\|episode_reference" src/
rtk grep -r "class.*Episode" src/ --include="*.py"
```
Rapport dans bloc Dispute `D-2026-04-16-002` si match non-trivial → arbitrage reuse/rename/create-new avant d'écrire quoi que ce soit.

**Action Codex (après étape 0)** :
1. Ajouter Annexe B à doc 22 avec les contrats Pydantic v2 frozen :

```python
class EpisodeRef(BaseModel):
    model_config = ConfigDict(frozen=True)
    episode_id: UUID
    engine_id_of_origin: Literal["A", "C"]          # D ne peut pas référencer un D
    pair: str
    direction: Literal["long", "short"]
    entry_level: Decimal
    exit_level: Decimal
    bet_structure: BetStructure
    forecast_horizon_class: ForecastHorizonClass
    forecast_target_class: ForecastTargetClass
    closed_at: int                                   # ns UTC
    close_reason: Literal["take_profit", "structural_exit", "time_stop", "stop_out"]
    realized_pnl_decimal: Decimal

class ClosedEpisodeJournal(BaseModel):
    """Frozen append-only record of closed A/C episodes, queried by engine_d."""
    model_config = ConfigDict(frozen=True)
    episodes: tuple[EpisodeRef, ...]                 # append-only tuple
    schema_version: str
    last_append_at: int                              # ns UTC
```

2. Remonter dans **doc 19 un nouveau livrable P3-10.5** : `closed_episode_journal.py` (path : `src/protocols/closed_episode_journal.py`) branché sur les hooks d'exit du portfolio/execution pipeline. `CONSTRAINT_DOCTRINAL` : path `src/protocols/` (canon V5.3 CLAUDE.md), pas `src/meta_engine/`.
3. Rappel R-D contractuel : R-D-1 refuse `close_reason == "stop_out"` (D ne réengage que sur sorties valides). Doc 22 §8 Prohibition 4 déjà présente — la renforcer par une validation Pydantic (`model_validator` levant `ValueError` si engine D reçoit un EpisodeRef stop_out).

**Acceptance** : `closed_episode_journal.py` existe, testé (append-only invariant + filter stop_out + property-based hypothesis sur append ordering), et `first_episode_resolver_d.py` l'utilise. Bloc Dispute `D-2026-04-16-002` clôturé.

### P0-3. Trancher "optional/required" par helper

**Problème** : §2 des deux docs liste "optional additive helpers". Ambiguïté : le §3 invoque ces helpers par nom → implémentation et tests divergeraient si absents.

**Rang d'autorité attendu (doc 28)** : rang 2 — principe Narang "isolation of hard rules for testability" (doc 20 §11 + Narang ch.3 §3.3 grammaire conditioning). Les helpers qui portent des règles HARD_BLOCK doivent être testables indépendamment du runtime → REQUIS. Les helpers qui sont seulement factorisation esthétique → OPTIONNEL.

**Action Codex** — modifier §2 comme suit :

**Doc 21 §2** :
| Helper | Status final |
|---|---|
| `a_exclusion_guard_c.py` | **REQUIS** — isolation R-AC est un contrat testable critique |
| `continuation_validator_c.py` | **REQUIS** — sépare OFI/VPIN/queue du math continuation |
| `signal_reporter_c.py` | OPTIONNEL — peut rester dans `engine_c_runtime.py` |

**Doc 22 §2** :
| Helper | Status final |
|---|---|
| `first_episode_resolver_d.py` | **REQUIS** — lecture `closed_episode_journal` |
| `historical_linkage_guard_d.py` | **REQUIS** — R-D-1/R-D-2/R-D-3 |
| `consecutive_stop_counter_d.py` | **REQUIS** — state strategy β |
| `anti_revenge_cooldown_d.py` | OPTIONNEL — peut fusionner avec `historical_linkage_guard_d` |
| `signal_reporter_d.py` | OPTIONNEL — peut rester dans `engine_d_runtime.py` |

**Acceptance** : §2 réécrit avec tableau ci-dessus. Les §7 (tests) listent des suites explicitement pour chaque helper REQUIS.

### P0-4. Spécifier `k_HLZ` explicite dans barres de promotion

**Problème** : docs 21 §8 et 22 §9 invoquent "Sharpe-deflated" sans énoncer `k` utilisé dans `SR_deflated = SR × √((N−k)/(N−1))`. Sans `k` déclaré, la déflation est ajustable → contournable.

**Rang d'autorité attendu (doc 28)** : rang 1 (Harvey-Liu-Zhu 2016 eq.(8)) pour la formule + rang 2 (`multiple_testing_guard.py` module V5.3) pour la valeur numérique de `k`.

**Étape 0 obligatoire (CODEX_TO_MEASURE)** : Codex **lit** `src/calibration_methods/multiple_testing_guard.py` (ou équivalent — scanner si le path exact diffère) et **rapporte la valeur réelle de `k`** déjà implémentée, incluant la règle de calcul. Pas de guess.

```bash
rtk grep -r "multiple_testing_guard\|k_hlz\|deflated_sharpe\|harvey_liu_zhu" src/
rtk read src/calibration_methods/multiple_testing_guard.py
```

**Propositions Opus (étiquetées PROPOSAL_OPUS, à confirmer contre module réel)** :
```
k_HLZ = n_engines_candidates × n_pairs_shadow × n_regimes_evaluated
     = 4 × 20 × 4                        # hypothèse V5.3 si module absent
     = 320
```

Pour D spécifiquement (doc 22 §9), la règle `n_engines_candidates` dépend de l'ordre d'évaluation (A/B/C puis D, ou A/B/C/D ensemble). Codex mesure et rapporte.

**Action Codex après étape 0** :
- Si module existe → utiliser valeur réelle + formule réelle. Mettre à jour doc 21/22 avec nombres exacts et référence git hash du module.
- Si module n'existe pas → créer bloc Dispute `D-2026-04-16-004`, escalade rang 1 (re-dériver de HLZ 2016) + livrable doc 19 nouveau pour créer `multiple_testing_guard.py`.

**Acceptance** : §8 (doc 21) et §9 (doc 22) citent `k_HLZ` avec (a) la règle de composition, (b) la valeur numérique courante V5.3, (c) la référence HLZ 2016 eq.(8), (d) le git hash du module `multiple_testing_guard.py`. Test parity : `SR_deflated(SR=1.0, N=50, k=<valeur réelle>)` produit valeur hardcodée dans test.

**Closure note 2026-04-16 (Rang 1 + 2 + 4)** :
- `src/calibration_methods/multiple_testing_guard.py` exists.
- Formula source remains Harvey-Liu-Zhu 2016 eq.(8) [Rang 1].
- Current V5.3 composition is `k_HLZ = pairs_tested` in observed-shadow mode and `k_HLZ = max(pairs_tested, 20)` in promotion-floor mode [Rang 2 via doc 20 §12.2 + module].
- Current default used by docs 21/22 is the user-selected observed-shadow mode, so `k_HLZ = pairs_tested` [Rang 4].
- Current numeric default in the repo pair catalogue is `k_HLZ = 12`; `promotion_floor` remains available as an explicit non-default conservative option.
- Module blob hash: `b2aafc74bd5abdefc8810e69f1562e9cc6881007`.

---

## 4. P0-5 — BLOQUANT (élevé depuis P1 — règle R-QUANT-FIRST, doc 28 §2bis)

> **Justification de l'élévation** : un dev qui code sans formule complète produit un `silent strategy change` par omission. Les formules quant doivent être complètes AVANT toute implémentation. Ce n'est pas un "nice-to-have" — c'est la première chose qu'un dev doit avoir sous les yeux.

### P0-5a. Compléter formules quant en Annexe A — doc 21

Ajouter **§Annexe A "Formules microstructure — spécification complète"** à doc 21 :

**a) Realized kernel volatility** `CONSTRAINT_DOCTRINAL` (Barndorff-Nielsen-Hansen-Lunde-Shephard 2008)
```
σ_RK = Σ_{h=-H}^{H} k(h/H) · γ(h)

γ(h) = Σ_j r_j · r_{j+h}              # autocovariance réalisée d'ordre h
r_j  = log(P_j) - log(P_{j-1})         # log-return sur bucket
k(x) = Parzen kernel:
       k(x) = 1 - 6x² + 6|x|³         si |x| ≤ 0.5
       k(x) = 2(1 - |x|)³             si 0.5 < |x| ≤ 1
       k(x) = 0                         sinon
H    = ⌈c · n^(3/5)⌉                   # bandwidth
c    = THR-C_RK_BANDWIDTH_C            # default 0.4, cap 1.0, calibration seam
n    = nombre de buckets dans fenêtre
bucket_size = THR-C_RK_BUCKET_SIZE     # default 5 min, cap 15 min

Source: Barndorff-Nielsen et al. 2008 eq.(3.1)-(3.7)
DOI: 10.3982/ECTA6495
```

**b) OFI** `CONSTRAINT_DOCTRINAL` (Cont-Kukanov-Stoikov 2014)
```
OFI_t = Σ_{i=t-N+1}^{t} [ΔQ^b_i · 𝟙(P^b_i ≥ P^b_{i-1}) - ΔQ^a_i · 𝟙(P^a_i ≤ P^a_{i-1})]

ΔQ^b_i = changement de quantité au meilleur bid à l'event i
ΔQ^a_i = changement de quantité au meilleur ask à l'event i
N       = THR-C_OFI_WINDOW             # default 500 events, cap 2000

Source: Cont, Kukanov, Stoikov 2014 eq.(1)-(3)
DOI: 10.1093/jjfinec/nbt003
```

**c) Kyle λ** `CONSTRAINT_DOCTRINAL` (Kyle 1985)
```
ΔP_t = λ · SignedVolume_t + ε_t

estimation: OLS rolling sur fenêtre de THR-C_KYLE_WINDOW
SignedVolume = volume × sign(trade_direction)   # Lee-Ready ou tick rule
λ = coefficient de régression (price impact / unité de volume signé)
THR-C_KYLE_WINDOW = default 1h, cap 4h

Source: Kyle 1985 eq.(1)
DOI: 10.2307/1913210
```

**d) VPIN** `CONSTRAINT_DOCTRINAL` (Easley-López de Prado-O'Hara 2012)
```
VPIN = (1/n) · Σ_{τ=1}^{n} |V^S_τ - V^B_τ| / V_bucket

V_bucket = DailyVolume / THR-C_VPIN_BUCKETS    # default 50, cap 100
V^S_τ, V^B_τ = volume sell/buy par bucket (classification Bulk Volume)
n = nombre de buckets dans fenêtre glissante (default 50)
THR-C_VPIN_BUCKETS = default 50, cap 100

Source: Easley, López de Prado, O'Hara 2012 eq.(2)-(4)
DOI: 10.1093/rfs/hhs053
```

**Nouveaux thresholds à ajouter à la table §5 de doc 21** :

| ID | Meaning | Default | Hard cap | Module |
|---|---|---|---|---|
| THR-C_RK_BANDWIDTH_C | Realized kernel bandwidth constant | 0.4 | 1.0 | `structure_detector_c` |
| THR-C_RK_BUCKET_SIZE | Realized kernel bucket duration | 5 min | 15 min | `structure_detector_c` |
| THR-C_OFI_WINDOW | OFI cumulation window (events) | 500 | 2000 | `continuation_validator_c` |
| THR-C_KYLE_WINDOW | Kyle λ regression window | 1h | 4h | `continuation_validator_c` |
| THR-C_VPIN_BUCKETS | VPIN bucket count per day | 50 | 100 | `continuation_validator_c` |

### P0-5b. Compléter formules quant en Annexe A — doc 22

Pour Engine D, les mêmes formules s'appliquent mais avec deux précisions D-spécifiques :
- OFI est **recalculé** sur la fenêtre post-close du `first_episode_ref` (pas hérité)
- Realized kernel est **recalculé** (le contexte vol change entre l'épisode original et le re-entry)
- Kyle λ est recalculé sur la fenêtre courante

### P0-5c. Tests paper_repro obligatoires (couplé avec P0-5a/b)

Ajouter à la test matrix de doc 21 §6 et doc 22 §7 :

| Suite | Test | Paper reproduit |
|---|---|---|
| `test_realized_kernel_repro.py` | σ_RK sur données simulées (seed fixe) reproduit Barndorff-Nielsen 2008 Table 1 order of magnitude | ECTA6495 Table 1 |
| `test_ofi_repro.py` | OFI positif quand bid queue croît + ask queue décroît | Cont-Kukanov 2014 §3 directional prediction |
| `test_kyle_lambda_repro.py` | λ > 0 sur données synthétiques avec informed trader | Kyle 1985 basic prediction eq.(1) |
| `test_vpin_repro.py` | VPIN → 1.0 quand 100% informed flow (tous trades du même côté) | Easley-López 2012 boundary case |

---

## 4bis. P1 — NON-BLOQUANTS (pass séparé OK)

### P1-6. Tests hypothesis + published-paper reproduction

Doc 21 §6 et doc 22 §7 listent boundary tests. Ajouter colonne "hypothesis" (property-based) et "paper_repro" au-delà des 4 tests minimaux de P0-5c — obligation CODEX_PROMPT R34.

### P1-7. Table "D-sur-A vs D-sur-C" — doc 22 §3 Stage 8

`first_episode_ref.bet_structure` héritée peut être `DIRECTIONAL_LONG` (si A) ou `BREAKOUT` (si C). Clarifier conviction profile et invalidation behavior pour chaque cas.

### P1-8. Référence calibration seam explicite

Dans les tables §5 (doc 21) et §6 (doc 22), ajouter colonne "calibration_module" pointant vers `risk_runtime_drawdown_calibration.py` ou équivalent.

### P1-9. Version-pin renvois doc 23

Doc 21/22 invoquent doc 23 sans hash ni version. Ajouter `doc_23@<hash>` dans header.

### P1-10. Sources VPIN threshold crypto

`THR-C_VPIN_MAX ≤ 0.5` sans citation. Soit citer étude crypto, soit marquer explicitement "TBD_shadow_calibration".

---

## 5. Corrections parallèles à propager sur docs 19 et 20 (hors scope pass-2 21/22 mais dépendant)

Ces corrections étaient identifiées avant l'audit et restent dues — Codex peut les regrouper dans un PR dédié :

1. Remplacer toute référence `src/meta_engine/` par `src/meta_minimal/` (runtime), `src/meta_learning/` (governance), ou `src/protocols/` (coordination) selon contexte.
2. Supprimer toute occurrence résiduelle de `side="flat"` dans doc 20 §11 si présente.
3. Requalifier "drop-in replacement" (doc 20 P2-06) en "backward-compatible extension with optional fields then per-engine migration".
4. Doc 19 §2 : corriger "A/B only coded" → "A/B/C/D codés ; C/D requièrent doctrinal deepening (voir docs 21, 22)".

---

## 6. Ordre d'exécution recommandé

1. **P0-2** en premier (`ClosedEpisodeJournal` débloque R-D-1 et donc tout `first_episode_resolver_d`).
2. **P0-1** ensuite (`revenge_risk_penalty` débloque `marginal_value_estimator_d` + tests).
3. **P0-3** (impact test matrix — les suites changent selon status REQUIS/OPTIONNEL).
4. **P0-4** (gate promotion, pas gate implémentation — peut venir en dernier mais requis avant shadow gate check).
5. **P0-5** (formules quant complètes — **BLOQUANT**, élevé depuis P1-5 par règle R-QUANT-FIRST doc 28 §2bis). Doit être fait AVANT toute implémentation de feature microstructure. Branche `fix/doc27-P0-5-quant-formulas`.
6. Puis P1-6 → P1-10 en PR séparée.
7. §5 (corrections docs 19/20) en PR parallèle indépendant.

---

## 7. Format de livrable attendu de Codex

Chaque fix P0 produit :

```
BLOC FIX P0-<n>
-----------------------------
files_touched:
  - <path> (modified|created)
diff_summary: <2-3 lignes>
acceptance_checks:
  - [✓|✗] <criterion 1>
  - [✓|✗] <criterion 2>
tests_added:
  - tests/<path>::<testname>
calibration_thresholds_added:
  - THR-<ID> = default/cap (module)
open_questions: <liste ou "none">
status: COMPLETE | PARTIAL | BLOCKED
next_safe_step: <une ligne>
```

---

## 8. Journal d'exécution Codex

*(Codex ajoute une entrée datée après chaque fix appliqué. Format : `YYYY-MM-DD | fix_id | status | commit_hash | dispute_id | notes`.)*

| Date | Fix ID | Status | Commit | Dispute | Notes |
|---|---|---|---|---|---|
| 2026-04-16 | P0-1 | COMPLETE | pending_local_commit | D-2026-04-16-001 | User option C applied: no continuous penalty, explicit replay/backtest observability added on Engine D validation rail |
| 2026-04-16 | P0-2 | COMPLETE | pending_local_commit | D-2026-04-16-002 | `closed_episode_journal.py` created with frozen append-only `EpisodeRef` / `ClosedEpisodeJournal` + persistence + eligibility filtering |
| 2026-04-16 | P0-3 | COMPLETE | pending_local_commit | — | Helpers reclassified REQUIRED/OPTIONAL in docs 21/22 per rank-2 doctrine |
| 2026-04-16 | P0-4 | COMPLETE | pending_local_commit | D-2026-04-16-004 | `multiple_testing_guard.py` created with HLZ eq.(8) seam; docs 21/22 now default to user-selected `k_HLZ = pairs_tested`, with `promotion_floor = max(pairs_tested, 20)` kept explicit and non-default; module blob `b2aafc74bd5abdefc8810e69f1562e9cc6881007` |
| 2026-04-16 | P0-5 | COMPLETE | pending_local_commit | — | Docs 21/22 now include rank-1 Annex A microstructure formulas, new THR-C microstructure threshold rows with `calibration_module`, explicit `paper_repro` tests, and the measured OFI DOI correction to `10.1093/jjfinec/nbt003` |

## 9. Registre des disputes ouvertes par ce doc

*(Synchronisé avec doc 28 §7.)*

| ID | Sujet | Rang visé | Responsable initial | Statut |
|---|---|---|---|---|
| `D-2026-04-16-001` | Forme fonctionnelle `revenge_risk_penalty` | 1 (papier) sinon 4 (user) | Codex (recherche) | RESOLVED — user option C + replay/backtest observability required |
| `D-2026-04-16-002` | Collision `ClosedEpisodeJournal` avec code existant | 2 (canon) | Codex (scan repo) | RESOLVED — create-new |
| `D-2026-04-16-003` | Réservé — P0-3 REQUIS/OPTIONNEL helpers | 2 | Codex | CLOSED_WITHOUT_DISPUTE — P0-3 applied without Codex objection |
| `D-2026-04-16-004` | `k_HLZ` valeur réelle vs proposition Opus 320 | 1 + 2 + 4 | Codex (lit module) | RESOLVED — Opus k=320 rejected; pair-count seam retained per HLZ eq.(8) + doc 20 §12.2, and docs 21/22 default switched by user choice to `k_HLZ = pairs_tested`; `promotion_floor` kept explicit non-default; module blob `b2aafc74bd5abdefc8810e69f1562e9cc6881007` |

---

## 10. Hand-back Opus + audit pack obligatoire

Après chaque P0 Codex produit :
1. Commit atomique sur branche `fix/doc27-P0-<n>`.
2. Entrée dans §8 Journal ci-dessus.
3. Mise à jour de `docs/production_deployment_plan/update_audit/2026-04-16_docs21_22_opus_audit.md` (sections `Files Changed`, `Claims Implemented`, `Tests and Proof`, `Completion Status`) conforme template doc 26.
4. Clôture du bloc Dispute associé dans doc 28 §7 (statut RESOLVED + evidence).

Après les 5 P0 complets : Codex signale à Opus pour re-audit selon protocole 25. Si re-audit verdict ≥ 8.5/10 → merge autorisé et docs 21/22 passent de `SPEC` à `APPROVED as SPEC`.

---

## 11. Ordre d'exécution canonique

1. `D-2026-04-16-002` (scan repo collision `ClosedEpisodeJournal`) — 10 min.
2. `D-2026-04-16-004` (lecture module `multiple_testing_guard`) — 10 min.
3. `D-2026-04-16-001` (recherche littérature `revenge_risk_penalty`) — 30 min timebox.
4. Si rang 1 trouvé sur P0-1 → appliquer ; sinon ouvrir escalade rang 4 user et appliquer strictement la décision user (ici: option C = pas de pénalité continue, mais observabilité replay/backtest obligatoire).
5. P0-2 implémentation (après 1).
6. P0-4 implémentation (après 2).
7. P0-1 implémentation (après 3 ou escalade résolue).
8. P0-3 implémentation (indépendant, peut se paralléliser).
9. P1 en PR séparée après merge P0.

---

**Fin du brief. Codex : commencer par les 3 mesures `CODEX_TO_MEASURE` (disputes 002, 004, 001) AVANT toute écriture de code.**

---

## 12. Addendum P0-5 closure (2026-04-16)

**Rang utilise** : `1 + 2`

- P0-5 is now complete. Docs 21/22 carry Annex A formula blocks with complete equations, variable definitions, defaults, hard caps, and calibration seams.
- Tables §5 (doc 21) and §6 (doc 22) now include the explicit `calibration_module` column and the new `THR-C_RK_*`, `THR-C_OFI_WINDOW`, `THR-C_KYLE_WINDOW`, `THR-C_VPIN_BUCKETS` rows.
- Test matrices now include authoritative replacement visibility for both `hypothesis` and `paper_repro`, plus the explicit suites for realized kernel, OFI, Kyle lambda, and VPIN.
- Measured DOI correction: the Cont-Kukanov-Stoikov paper DOI is `10.1093/jjfinec/nbt003` [Rang 1], not the stale placeholder DOI carried in the raw brief.
- Final paper-repro suite names are `test_realized_kernel_repro.py`, `test_ofi_repro.py`, `test_kyle_lambda_repro.py`, and `test_vpin_repro.py`.
- Docs 21/22 now pin `doc_23@834f7fae4a06847121670559dd5bfd65c28d82da` and mark `THR-C_VPIN_MAX` as `TBD_shadow_calibration` rather than keeping the uncited `≤ 0.5` claim as authoritative.
- Effective handback condition is now "after the 5 P0 complets" rather than "after the 4 P0 complets".


---

## Source: docs/production_deployment_plan/update_audit/2026-04-16_engine_c_continuation_microstructure_wiring.md

# 2026-04-16 — Engine C continuation microstructure wiring

## Objective

Wire the canonical microstructure package into the first governed consumer seam for Engine C without rewriting the runtime rail.

## Docs Governants

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `docs/production_deployment_plan/21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md`
- `docs/production_deployment_plan/29_SPRINT_FINAL_CODEX_BEFORE_MONDAY.md`
- `CODEX_PROMPT.md`

## Current Code Seam

- `src/engines/engine_c/engine_c_runner.py` already owned Stage 2 continuation viability.
- `src/engines/engine_c/engine_c_runtime.py` already consumed only `EngineCOutput` and must remain compatible.
- `src/data_backbone/microstructure/*` now exists, but Engine C was not consuming any of its signals yet.

## Placement

- New pure validator seam in `src/engines/engine_c/continuation_validator_c.py`
- Additive fields on `EngineCInput`, `EngineCLogEntry`, and `EngineCOutput`
- Runner wiring only in `engine_c_runner.py`
- Runtime compatibility pass-through only in `engine_c_runtime.py`

## Files Changed

- `src/engines/engine_c/signal_math_c.py`
- `src/engines/engine_c/continuation_validator_c.py`
- `src/engines/engine_c/engine_c_runner.py`
- `src/engines/engine_c/engine_c_runtime.py`
- `src/engines/engine_c/__init__.py`
- `tests/test_engines/test_engine_c/test_continuation_validator_c.py`
- `tests/test_engines/test_engine_c/test_engine_c.py`
- `tests/test_engines/test_engine_c/test_engine_c_runtime.py`

## Claims Implemented

- Added a pure `continuation_validator_c` seam that applies continuation maturity plus additive OFI / queue pressure / VPIN gates.
- Kept Engine C runtime architecture unchanged: the runtime still consumes `EngineCOutput`; no new profile, no new engine, no gate bypass.
- Made microstructure gating transitional and explicit:
  - OFI and queue pressure gate only when metrics are provided.
  - VPIN gate only when both `vpin` and `continuation_vpin_max` are provided.
  - If metrics are absent, the legacy continuation path remains active and auditable.
- Added audit fields to runner/runtime logs and outputs:
  - `cumulative_ofi`
  - `queue_pressure`
  - `vpin`
  - `kyle_lambda`
  - `microstructure_gate_applied`
- Added a new no-trade category `microstructure_unconfirmed` to separate structural continuation failure from microstructure confirmation failure.

## Tests and Proof

- `python -m py_compile src\engines\engine_c\signal_math_c.py src\engines\engine_c\continuation_validator_c.py src\engines\engine_c\engine_c_runner.py src\engines\engine_c\engine_c_runtime.py src\engines\engine_c\__init__.py tests\test_engines\test_engine_c\test_continuation_validator_c.py tests\test_engines\test_engine_c\test_engine_c.py tests\test_engines\test_engine_c\test_engine_c_runtime.py`
- `rtk pytest -q tests/test_engines/test_engine_c/test_continuation_validator_c.py tests/test_engines/test_engine_c/test_engine_c.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_data_backbone/microstructure/test_order_flow_imbalance.py tests/test_data_backbone/microstructure/test_queue_pressure.py tests/test_data_backbone/microstructure/test_vpin.py`
- `python scripts/run_engineering_guardrails.py`
- Proof executed:
  - `py_compile` passed
  - `Pytest: 36 passed`
  - `new_violations=0`

## Deferred / Not Done

- Engine C runtime does not compute OFI / queue pressure / VPIN itself yet; it consumes precomputed values through `EngineCInput`.
- `kyle_lambda` is surfaced in logs/output but not yet used as a hard gate because no governed threshold was introduced in this slice.
- No scoring-weight change was made; microstructure acts as a governed continuation gate, not a new scoring feature.

## Risks / Open Questions

- `THR-C_VPIN_MAX` remains `TBD_shadow_calibration`; the runner only applies the VPIN veto when the threshold is explicitly supplied.
- Upstream wiring from real order-book / trade streams into `EngineCInput` still needs a dedicated seam to avoid duplicate calculation paths.

## Completion Status

- `COMPLETE`

## Next Safe Step

- Wire a single upstream Engine C assembler that maps canonical microstructure records into `EngineCInput` without teaching the runtime to compute LOB features inline.


