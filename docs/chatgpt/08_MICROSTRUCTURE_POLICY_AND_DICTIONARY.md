# 08_MICROSTRUCTURE_POLICY_AND_DICTIONARY

## Included Source Docs
- docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md
- docs/production_deployment_plan/update_audit/2026-04-16_no_1990s_ta_gate.md

---

## Source: docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md

# 23 — Microstructure Feature Dictionary + Formal 1990s-TA Prohibition

**Status**: CANONICAL REFERENCE — every microstructure feature used by V5.3 engines and enablers is defined here by exact formula + reference paper + V5.3 wiring.
**Date**: 2026-04-15
**Parent canon**: V5.3; companion: docs 19, 20, 21, 22.
**Scope**: formal definitions for OFI, VPIN, Kyle λ, Amihud, Roll, Corwin-Schultz, realized kernel (Barndorff-Nielsen), Hawkes intensity, PIN / adjusted PIN, plus formal prohibition of 1990s TA indicators.

---

## 0. Purpose

- Give every implementer (and every engine spec) a single place to look up the exact formula, paper reference, and V5.3 module wiring for each microstructure feature.
- Freeze the prohibition list of 1990s indicators so no engine, scoring layer, or enabler can reintroduce them by accident.
- Serve as the contract basis for `tests/test_data_backbone/microstructure/` — published-paper check values.

---

## 1. Directory layout

```
src/data_backbone/microstructure/
├── __init__.py
├── order_flow_imbalance.py             # OFI — Cont-Kukanov (2014)
├── vpin.py                             # VPIN — Easley-Lopez-O'Hara (2012)
├── kyle_lambda.py                      # Kyle λ — Kyle (1985); regression-based estimator
├── amihud_illiquidity.py               # Amihud — Amihud (2002)
├── roll_spread.py                      # Roll effective spread — Roll (1984)
├── corwin_schultz_spread.py            # High-low spread — Corwin-Schultz (2012)
├── realized_kernel_vol.py              # Realized kernel — Barndorff-Nielsen et al. (2008)
├── hawkes_intensity.py                 # Hawkes intensity — Bacry-Mastromatteo-Muzy (2015)
├── pin.py                              # PIN / adjusted PIN — Easley-Kiefer-O'Hara (1996)
├── queue_pressure.py                   # Book imbalance — standard
├── spread_dynamics.py                  # Realized spread / effective spread live
└── feature_registry.py                 # central enumeration + calibration seam per feature

tests/test_data_backbone/microstructure/
├── test_order_flow_imbalance.py
├── test_vpin.py
├── test_kyle_lambda.py
├── test_amihud_illiquidity.py
├── test_roll_spread.py
├── test_corwin_schultz_spread.py
├── test_realized_kernel_vol.py
├── test_hawkes_intensity.py
├── test_pin.py
├── test_queue_pressure.py
└── test_feature_registry.py
```

---

## 2. Common conventions

- Timestamps: `int64` nanoseconds (V5.3 canon).
- Prices: `Decimal` for exchange-level, `float64` for feature math (explicit cast).
- Volumes: base asset quantity, `float64`.
- Windows: always expressed as `(window_events: int | None, window_seconds: float | None)` — at least one populated; event-window preferred for microstructure features (avoids clock-time aliasing).
- Every feature returns a frozen Pydantic record carrying: `value`, `window_used`, `n_events_used`, `method_version_hash`, `pair`, `computed_at_ns`, `input_data_hash` (for reproducibility).

---

## 3. Feature definitions

### 3.1 Order Flow Imbalance (OFI) — Cont-Kukanov

**Reference**: Cont R., Kukanov A., Stoikov S. (2014) *The Price Impact of Order Book Events*, Journal of Financial Econometrics 12(1), 47–88.

**Formula** (best-bid/best-ask event-driven form):

Let at event `n` the best bid/ask prices and sizes be `(P^b_n, q^b_n, P^a_n, q^a_n)`. Define:

```
e_n = I{P^b_n >= P^b_{n-1}} · q^b_n  − I{P^b_n <= P^b_{n-1}} · q^b_{n-1}
    − I{P^a_n <= P^a_{n-1}} · q^a_n  + I{P^a_n >= P^a_{n-1}} · q^a_{n-1}
```

Then `OFI_window = Σ e_n` over the window.

**V5.3 wiring**:
- Consumed by: Engine C (`continuation_validator_c`), Engine A (conviction builder), ML enabler.
- Window default: 200 events (calibrated).
- THR: `THR-C_OFI_MIN` (per-engine).

**Test check value**: Cont-Kukanov (2014) §5 published reference trace → our implementation within ±2% of paper's reported OFI on the supplied synthetic fixture.

---

### 3.2 VPIN — Volume-synchronized Probability of Informed Trading

**Reference**: Easley D., López de Prado M., O'Hara M. (2012) *Flow Toxicity and Liquidity in a High-Frequency World*, Review of Financial Studies 25(5), 1457–1493.

**Formula**:
1. Partition volume into equal-volume buckets of size `V`.
2. For each bucket `τ`, classify buy vs sell volume via **bulk volume classification** (BVC):
   ```
   V^B_τ = V · Z(Δp_τ / σ_Δp)    where Z is standard normal CDF
   V^S_τ = V − V^B_τ
   ```
3. VPIN over rolling `n` buckets:
   ```
   VPIN_n = Σ_{τ} |V^B_τ − V^S_τ| / (n · V)
   ```

**V5.3 wiring**:
- Consumed by: Engine C (`continuation_validator_c` — skip if VPIN > THR-C_VPIN_MAX, since toxic flow is a fade setup, not continuation), Engine B (sub-signal `toxic_flow_fade` — doc 19 P2-10).
- Bucket size `V`: per-pair calibrated to give ≈ 50 buckets/day.
- Rolling window: 50 buckets (≈ 1 day).
- THR: `THR-C_VPIN_MAX` for C; internal thresholds for B sub-signal.

**Test check value**: Easley-López-O'Hara (2012) Table 2 synthetic reproduction on ES futures fixture → VPIN within ±0.02 of published.

---

### 3.3 Kyle's λ — Price impact coefficient

**Reference**: Kyle A. (1985) *Continuous Auctions and Insider Trading*, Econometrica 53(6), 1315–1335.

**Formula** (regression-based estimator, standard market microstructure practice):

```
Δp_t = λ · q_t^signed + ε_t
```

where `Δp_t` is the price change over interval `t` and `q_t^signed` is signed net order flow (positive for net buy). Estimate `λ` via OLS over rolling window of `N` intervals.

**V5.3 wiring**:
- Consumed by: Engine C (conviction input), Engine A (cost feasibility), execution backbone (slippage pre-estimate).
- Window: 500 events (calibrated).
- Sanity check: `λ > 0` or mark feature stale.

**Test check value**: Hasbrouck textbook synthetic VAR → λ recovered within 5%.

---

### 3.4 Amihud illiquidity ratio

**Reference**: Amihud Y. (2002) *Illiquidity and stock returns: cross-section and time-series effects*, Journal of Financial Markets 5(1), 31–56.

**Formula**:

```
ILLIQ_t = |r_t| / V_t
```

where `r_t` is the absolute return over bar `t` and `V_t` is dollar volume. Averaged over rolling window:

```
ILLIQ_window = (1/N) · Σ_{t} |r_t| / V_t
```

**V5.3 wiring**:
- Consumed by: portfolio layer (pair selection criterion doc 20 §12.2), cost feasibility (all engines), `pair_catalog` health check.
- Window: 24h rolling (1-min bars).

**Test check value**: Amihud (2002) Table 1 cross-section reproduction on synthetic.

---

### 3.5 Roll effective spread estimator

**Reference**: Roll R. (1984) *A Simple Implicit Measure of the Effective Bid-Ask Spread in an Efficient Market*, Journal of Finance 39(4), 1127–1139.

**Formula**:

```
Spread_Roll = 2 · √(− Cov(Δp_t, Δp_{t−1}))     if Cov < 0
            = 0                                  otherwise
```

**V5.3 wiring**:
- Consumed by: `execution_cost_meter` (realized-cost backstop when L1 spread is unreliable).
- Window: 1h rolling on trade prints.

**Test check value**: Roll (1984) synthetic with known spread → recovered within ±10%.

---

### 3.6 Corwin-Schultz high-low spread estimator

**Reference**: Corwin S. A., Schultz P. (2012) *A Simple Way to Estimate Bid-Ask Spreads from Daily High and Low Prices*, Journal of Finance 67(2), 719–760.

**Formula** (abbreviated):

```
β_t = [ln(H_t / L_t)]^2 + [ln(H_{t+1} / L_{t+1})]^2
γ_t = [ln(H_{t,t+1} / L_{t,t+1})]^2      (2-day high/low span)
α_t = (√(2β) − √β) / (3 − 2√2) − √(γ / (3 − 2√2))
Spread_CS = 2·(e^{α_t} − 1) / (1 + e^{α_t})
```

**V5.3 wiring**:
- Consumed by: `pair_catalog` diagnostics, lab-side cross-exchange parity checks.
- Cadence: daily on 1h bars.

**Test check value**: Corwin-Schultz (2012) reproduction on NYSE TAQ fixture → within ±5%.

---

### 3.7 Realized kernel volatility — Barndorff-Nielsen et al.

**Reference**: Barndorff-Nielsen O. E., Hansen P. R., Lunde A., Shephard N. (2008) *Designing Realized Kernels to Measure the Ex-Post Variation of Equity Prices in the Presence of Noise*, Econometrica 76(6), 1481–1536.

**Formula** (flat-top Parzen kernel, standard implementation):

```
RK_t = γ_0 + Σ_{h=1}^{H} k((h−1)/H) · (γ_h + γ_{−h})
γ_h  = Σ_{j} (p_{t_j} − p_{t_{j−1}})·(p_{t_{j−h}} − p_{t_{j−h−1}})
k(x) = flat-top Parzen kernel, 0 ≤ x ≤ 1
```

Bandwidth `H` selected per Barndorff-Nielsen-Hansen-Lunde-Shephard (2008) optimal rule.

**V5.3 wiring**:
- Consumed by: Engine A (vol scaling), Engine C (`structure_detector_c` — replaces 1990s ATR!), `vol_target_sizer`, `regime_shift_watcher`.
- Window: 1h, 4h, 24h rolling.
- **This is the V5.3-canonical realized-vol estimator.** No ATR.

**Test check value**: BNHLS (2008) simulation Table 1 → recovered within ±3%.

---

### 3.8 Hawkes intensity — order arrival clustering

**Reference**: Bacry E., Mastromatteo I., Muzy J.-F. (2015) *Hawkes Processes in Finance*, Market Microstructure and Liquidity 1(1).

**Formula** (exponential-kernel univariate Hawkes):

```
λ(t) = μ + Σ_{t_i < t} α · e^{−β (t − t_i)}
```

Calibration via MLE on event times `{t_i}`. For multivariate (buys vs sells), extend to matrix `α_{ij}`, `β_{ij}`.

**V5.3 wiring**:
- Consumed by: Engine C (`continuation_validator_c` — high self-exciting intensity in break direction = valid continuation evidence), ML enabler.
- Window: 1000 events rolling.

**Test check value**: simulated Hawkes process with known (μ, α, β) → recovered parameters within ±10%.

---

### 3.9 PIN / adjusted PIN — Probability of Informed Trading

**Reference**: Easley D., Kiefer N., O'Hara M., Paperman J. (1996) *Liquidity, Information, and Infrequently Traded Stocks*, Journal of Finance 51(4), 1405–1436. Adjusted PIN: Duarte-Young (2009).

**Formula** (abbreviated — EM-estimation of latent state model):

Parameters: `(α, δ, μ, ε_B, ε_S)` — probability of info event, probability info bad, info-trade intensity, buy/sell uninformed intensities.

```
PIN = α·μ / (α·μ + ε_B + ε_S)
```

Estimated via EM on daily buy/sell trade counts.

**V5.3 wiring**:
- Consumed by: lab-side pair selection diagnostics (doc 20 §12.2 criterion 7).
- Cadence: weekly recompute.
- Not live-gated (too slow and noisy for live signals); lives in `calibration_methods/pair_health/`.

**Test check value**: Easley et al. (1996) Table reproduction on synthetic buy/sell counts.

---

### 3.10 Queue pressure / book imbalance

**Formula**:

```
I_t = (Q^b_t − Q^a_t) / (Q^b_t + Q^a_t)         ∈ [−1, 1]
```

where `Q^b_t`, `Q^a_t` are top-of-book sizes (or top-K aggregated).

**V5.3 wiring**:
- Consumed by: every engine, execution backbone.
- Top-K: default K=5 levels.

---

### 3.11 Realized / effective spread (live)

**Formulas**:
- Quoted spread: `S_q = P^a − P^b`.
- Effective spread: `S_e = 2 · |P_exec − m|`, where `m = (P^a + P^b)/2` midpoint at execution.
- Realized spread (5-min): `S_r = 2 · D_t · (P_exec − m_{t+5min})`, where `D_t ∈ {+1, −1}` for buy/sell.

**V5.3 wiring**:
- Consumed by: `execution_cost_meter`, `cost_drift_monitor`.

---

## 4. Feature registry contract

`src/data_backbone/microstructure/feature_registry.py` exposes:

```python
class MicrostructureFeatureSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    feature_id: str                         # e.g. "ofi.cont_kukanov"
    reference_paper: str                    # full citation
    default_window_events: int | None
    default_window_seconds: float | None
    calibration_seam_path: str              # e.g. "src/calibration_methods/ofi_cont_kukanov_calibration.py"
    consumed_by: tuple[str, ...]            # engine_ids or module names
    promotion_state: Literal["DISCOVERED", "VALIDATED", "CANDIDATE_VPS", "SHADOW_VPS", "LIVE_VPS"]
    method_version: str                     # semver
```

Every microstructure feature used anywhere in V5.3 must appear in this registry. CI job `rtk python -m dag_validator --check-feature-registry` fails if a feature is consumed without a registry entry.

---

## 5. SHAP + promotion pipeline (recap from doc 19 Phase 2)

```
DISCOVERED (lab replay)
    ↓ validation: stationarity + ≥ 50 signal events
VALIDATED
    ↓ replay-vs-live correlation ≥ 0.95 on 7d window
CANDIDATE_VPS
    ↓ shadow-vs-live parity (doc 20 §4.2 filter ✔)
SHADOW_VPS
    ↓ quadruple filter green + Sharpe-deflation check (Harvey-Liu-Zhu)
LIVE_VPS
```

Harvey-Liu-Zhu (2016) deflation:
```
SR_deflated = SR · √((N − k) / (N − 1))
```
where `k` = number of features tested. Promotion to LIVE_VPS requires `SR_deflated ≥ 0.8 · SR_backtest` (doc 19 Phase 3 promotion gate).

---

## 6. Formal prohibition — 1990s TA indicators

The following indicators are **forbidden** as:
- Emission triggers for engines A / B / C / D
- Inputs to `forecast_direction`, `forecast_strength`
- Inputs to ML enabler features **as raw TA** (derived structural variants OK if they pass feature-registry promotion)
- Inputs to `structure_detector_*`, `continuation_validator_*`, `conviction_builder_*`

**Prohibited list**:

| Indicator | Period of origin | V5.3 substitute |
|---|---|---|
| RSI (Wilder 1978) | 1970s | Realized kernel vol (§3.7), OFI persistence (§3.1) |
| MACD (Appel 1970s–80s) | 1970s | VPIN (§3.2), Hawkes intensity (§3.8) |
| Stochastic oscillator (Lane 1950s, popular 1980s) | 1950s–80s | OFI (§3.1), queue pressure (§3.10) |
| Bollinger Bands (Bollinger 1980s) | 1980s | Realized kernel (§3.7) + microstructure-aware bands |
| Williams %R (Williams 1970s) | 1970s | Same as Stochastic substitute |
| CCI (Commodity Channel Index, Lambert 1980) | 1980 | Realized vol + residualized return |
| DMI / ADX (Wilder 1978) | 1970s | OFI persistence + Hawkes intensity |
| Parabolic SAR (Wilder 1978) | 1970s | Structural invalidation contracts (engines' own invalidation_mapper_*.py) |
| Ichimoku (Hosoda 1960s, pub. 1969) | 1960s | Structural levels from L2 book + realized vol |
| Elliott waves | subjective | not replaced — rejected as non-falsifiable |
| Candlestick-pattern recognition | subjective | not replaced — rejected as pattern-fitting |

**Authorised as features / context only, never as sole trigger** (CLAUDE.md rule reaffirmed):
- ATR — only as legacy **context** overlay in Complete UI; **never** as signal input for engines. V5.3 canonical vol estimator is §3.7 realized kernel.
- Realized-vol estimators Yang-Zhang, Garman-Klass, Parkinson — permitted as feature inputs and as realized-vol substitutes for pre-HF pairs where L2 data is thin.
- Simple EMA — permitted only as smoothing primitive applied to microstructure features (§3.1–§3.11), never as a signal by itself.

**Enforcement**: a unit test `test_no_1990s_ta_in_engine_inputs.py` scans every engine's input-feature registry and fails if any feature_id matches the prohibited list (e.g. regex `(?i)\b(rsi|macd|stoch|bbands?|williams|adx|sar|ichimoku)\b` in `feature_id`, `module_path`, or `consumed_by` records).

---

## 7. Test matrix minimum

| Suite | Min tests |
|---|---|
| `test_order_flow_imbalance.py` | 4 (check value + edge cases) |
| `test_vpin.py` | 4 |
| `test_kyle_lambda.py` | 3 |
| `test_amihud_illiquidity.py` | 3 |
| `test_roll_spread.py` | 3 |
| `test_corwin_schultz_spread.py` | 3 |
| `test_realized_kernel_vol.py` | 4 |
| `test_hawkes_intensity.py` | 3 |
| `test_pin.py` | 2 |
| `test_queue_pressure.py` | 2 |
| `test_feature_registry.py` | 3 (registry integrity + promotion state transitions) |
| `test_no_1990s_ta_in_engine_inputs.py` | 1 (the scan itself) + per-engine assertions |
| **Total** | **≥ 30** |

---

## 8. Immediate implementation order (follows doc 19 Phase 2)

1. `feature_registry.py` + `test_feature_registry.py` first — nothing else is added without a registry entry.
2. `realized_kernel_vol.py` (§3.7) — upstream dependency of multiple engines and of `regime_shift_watcher`.
3. `order_flow_imbalance.py` (§3.1) — baseline feature for C, B sub-signals, ML enabler.
4. `vpin.py` (§3.2) — required for B sub-signal P2-10 (VPIN-fade) + C skip rule.
5. `queue_pressure.py` (§3.10) — required for C continuation validator.
6. `kyle_lambda.py` (§3.3), `amihud_illiquidity.py` (§3.4) — cost feasibility + pair selection.
7. `hawkes_intensity.py` (§3.8) — C continuation evidence.
8. `roll_spread.py`, `corwin_schultz_spread.py`, `pin.py` — diagnostics / lab-side.
9. `test_no_1990s_ta_in_engine_inputs.py` — mandatory CI gate, final step.

---

## 9. Citation bibliography (condensed)

1. Amihud Y. (2002). *Illiquidity and stock returns*. JFM 5(1), 31–56.
2. Bacry E., Mastromatteo I., Muzy J.-F. (2015). *Hawkes Processes in Finance*. MML 1(1).
3. Barndorff-Nielsen O. E., Hansen P. R., Lunde A., Shephard N. (2008). *Designing Realized Kernels…*. Econometrica 76(6), 1481–1536.
4. Cont R., Kukanov A., Stoikov S. (2014). *The Price Impact of Order Book Events*. JFE 12(1), 47–88.
5. Corwin S. A., Schultz P. (2012). *A Simple Way to Estimate Bid-Ask Spreads from Daily High and Low Prices*. JF 67(2), 719–760.
6. Easley D., Kiefer N., O'Hara M., Paperman J. (1996). *Liquidity, Information, and Infrequently Traded Stocks*. JF 51(4), 1405–1436.
7. Easley D., López de Prado M., O'Hara M. (2012). *Flow Toxicity and Liquidity in a High-Frequency World*. RFS 25(5), 1457–1493.
8. Harvey C. R., Liu Y., Zhu H. (2016). *… and the Cross-Section of Expected Returns*. RFS 29(1), 5–68.
9. Kyle A. S. (1985). *Continuous Auctions and Insider Trading*. Econometrica 53(6), 1315–1335.
10. Roll R. (1984). *A Simple Implicit Measure of the Effective Bid-Ask Spread*. JF 39(4), 1127–1139.

---

**Status**: REFERENCE DICTIONARY COMPLETE — every microstructure feature used anywhere in V5.3 must be defined here, consumed via `feature_registry`, and CI-gated against the 1990s-TA prohibition list.


---

## Source: docs/production_deployment_plan/update_audit/2026-04-16_no_1990s_ta_gate.md

# 2026-04-16 — No 1990s TA gate

## Docs Governing

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `CODEX_PROMPT.md`

## Files Changed

- `tests/test_data_backbone/microstructure/test_no_1990s_ta_in_engine_inputs.py`

## Claims Implemented

- Added the final doc23 CI gate for prohibited 1990s-TA markers.
- The test scans the canonical microstructure feature registry and engine source trees.
- The banned regex covers RSI, MACD, Stochastic, Bollinger/BBands, Williams, ADX, SAR, Ichimoku, and CCI.

## Tests And Proof

- `python -m pytest tests/test_data_backbone/microstructure/test_no_1990s_ta_in_engine_inputs.py -q`
- `python scripts/run_engineering_guardrails.py`
- Proof executed in combined microstructure run: `47 passed`, `new_violations=0`

## Completion Status

- `COMPLETE`
- Next safe step: keep this gate in the targeted microstructure regression pack.


