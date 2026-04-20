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
Applies `break_even_filter` (doc 19 P2-08) with C-specific expected-cost model. If `EV^net ≤ THR-E05_floor` → no emit + `RefusalRecord(category=NO_TRADE, reason_codes=("economics.engine_c.break_even.fail", "c.break_even.fail"))`.

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
