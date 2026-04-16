# 20 — Carver / Narang / Taleb Integration into V5.3

**Status**: AUDIT + EXECUTION ADDENDUM to `19_MULTIPAIR_MODERNIZATION_PLAN.md`
**Date**: 2026-04-14
**Source documents** (read in full):
- `E:/claude  v5.3/modernisation de v5.3/V5_3_CARVER_INTEGRATION_FOR_CODE.md` (666 lines)
- `E:/claude  v5.3/modernisation de v5.3/MATH CARVNER.docx` (Carver mathematical annex)
- `E:/claude  v5.3/modernisation de v5.3/V5_3_NARANG_INTEGRATION_MD.md` (568 lines)
- `E:/claude  v5.3/modernisation de v5.3/V5_3_ANNEXE_TALEB_FOOLED_BY_RANDOMNESS.md` (371 lines)

**Hierarchy reminder**: this doc is **subordinate** to the V5.3 master canon and to the official pipeline `Replay → Shadow → Micro-live → Live-Light`. It does **not** create new engines, profiles, venues, or bypass any gate. It enriches contracts, hardens governance, and inserts targeted tasks into the existing 6-phase plan from doc 19.

---

## 0. One-line verdicts

| Source | Role for V5.3 | Verdict |
|---|---|---|
| **Carver** | Quant skeleton: forecast standardisation, vol targeting, sizing, portfolio diversification | **ACCEPT 70%** as math discipline (Light: items 1–7 of §9 below; Complete: items 8–11) |
| **Carver math annex** | Concrete formulas to bind to specific modules | **ACCEPT** as canonical reference for THR-S07, scoring scaling, FDM/IDM in Build-14+ |
| **Narang** | System grammar: alpha/risk/cost/portfolio/execution/data + model risk + crowding | **ACCEPT 80%** as architecture grammar; **REJECT** HFT, equities-style stat arb forms, off-the-shelf models as crutch |
| **Taleb** | Anti-illusion governance: blowup, survivorship, noise, alternative histories | **ACCEPT 100%** as governance discipline; **REJECT** turning Taleb into a new module or anti-model dogma |

**Combined synthesis**:
> Carver gives V5.3 the **shape**, Narang gives it the **grammar**, Taleb gives it the **honesty**. None of the three replaces the V5.3 canon, the LIGHT/COMPLETE profiles, or the official validation pipeline.

---

## 1. What changes vs doc 19

Doc 19 stays the executable backbone (Phases 0 → 6, 7 pairs, Build-14 enabler pattern, no engine demolition). This doc adds **cross-cutting requirements** that bolt on at specific phases without reordering them.

### Net delta
| Area | Doc 19 baseline | After this addendum |
|---|---|---|
| `SignalCandidate` contract | direction + score + cost + gain | **enriched** with `forecast_strength`, `forecast_horizon_class`, `bet_structure`, `conditioning_state`, `expected_break_even`, `expected_ce`, `invalidation_ref`, `reason_codes` |
| Sizing formula | `vol_target / atr_14d × capital` (Phase 4, THR-S07) | **Carver-canonical**: `N = (forecast/10) × (vol_target × capital) / instrument_value_vol`, with V5.3 caps and CE filter |
| Risk layers | 9 + Regime-Change Detector = 10 | 10 + **anti-blowup convexity guard** + **crowding-suspicion monitor** as soft signals into existing layers |
| Refusal logging | partial (DTR, hard_block_gate) | **mandatory** structured `RefusalRecord` for every no-trade, no-fill, phantom, version invalidation (Taleb §3.3) |
| Model risk | absent | new `model_risk_registry` (LAB-side) tracking drift across replay → shadow → micro-live → live |
| Forecast taxonomy | implicit | explicit enum `ForecastTargetClass` (Narang §3.2) |
| Conditioning vetoes | scattered | classified into **4 official families** (Narang §3.3): engine-internal / scoring / hard-block / portfolio |
| Quadruple filter | implicit | explicit gate before any promotion: `cost_real ✔ + queue_risk ✔ + parity_local_shadow_live ✔ + regime_robustness ✔` (Taleb §8) |

---

## 2. Carver — math integration map

Source: `MATH CARVNER.docx` + `V5_3_CARVER_INTEGRATION_FOR_CODE.md`.

### 2.1 NOW (Light, integrated into existing phases)
| Carver brick | V5.3 module | Phase | Threshold |
|---|---|---|---|
| Net return / Sharpe / variance per moteur, paire, portfolio | `src/meta_minimal/edge_tracker_prudent_minimal/` (already exists, enrich) | P2 | — |
| Standardised forecast `F_i ∝ E[r_i]/σ_i`, `ForecastScalar = 10/E[|F|]` | `scoring_backbone/forecast_normalizer.py` (NEW) | **P2** | calibrated `ForecastScalar` per engine, computed offline |
| Vol-target sizing `VolScalar = DailyCashVolTarget / InstrumentValueVol`, then `N = (F/10) × VolScalar` | `portfolio_minimal/allocation_router/vol_target_sizer.py` (replaces fixed sizing per P4-01) | **P4** | THR-S07 (already in doc 19) |
| Cost / break-even / EV-net `EV^net = x × (E[g] − E[c])`; no-trade if EV^net ≤ 0 | `scoring_backbone/break_even_filter.py` (NEW, gates emission) | **P2** | reuse THR-W01 (W-Carver) for min EV^net floor |
| CE per moteur/paire/portefeuille | `src/meta_minimal/cra_monitor/` (already exists) | P0 (already green) | — |
| Diversification min (caps, cluster, BTC budget) | `risk_backbone/correlation_cluster_guard` + `btc_factor_guard` (already exist) | P4 | — |

### 2.2 LATER (Complete, parked)
- Forecast Diversification Multiplier: `FDM = 1/√(W H W^T)` with negative correlations floored at 0 (Carver explicit recommendation).
- Instrument Diversification Multiplier (IDM): same shape on instrument-return correlation matrix.
- Full portfolio variance `Var(R_p) = w^T Σ w`, marginal risk contribution `MRC_j = (Σw)_j / σ_p`, RC = w_j × MRC_j.
- Shrunk covariance (Ledoit-Wolf) for Complete UI risk panel.

These ship as **Build-14/15 enablers**, not as Light.

### 2.3 PROHIBITED (Carver's own warnings, V5.3-aligned)
- ❌ Full-Kelly sizing — Carver criticises aggressive systems; V5.3 stays prudent.
- ❌ Heavy parameter optimisation per pair — keep 2–4 variants max per engine.
- ❌ Replace A/B/C/D with a single ML "king" — Carver rejects single-model tropism.
- ❌ Treat Carver's optimisation as live-promotable without the V5.3 governance pipeline.

---

## 3. Narang — grammar integration map

Source: `V5_3_NARANG_INTEGRATION_MD.md`.

### 3.1 Enriched `SignalCandidate` contract (additive migration seam for Phase 2)
File to create: `src/interface_contracts/forecast_contracts.py`

Current code truth: the canonical runtime contract still lives in `src/interface_contracts/decision_contracts.py`, and engines A/B/C/D build it directly. Therefore the Narang-grade contract must land additively first (`forecast_contracts.py` + adapters), then migrate progressively. It is **not** a one-shot drop-in replacement.

```python
from enum import Enum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class ForecastTargetClass(str, Enum):
    DIRECTION_ONLY = "direction_only"
    DIRECTION_PLUS_STRENGTH = "direction_plus_strength"
    DIRECTION_PLUS_STRENGTH_PLUS_HORIZON = "direction_plus_strength_plus_horizon"
    RELATIVE_FORECAST = "relative_forecast"
    INTRINSIC_FORECAST = "intrinsic_forecast"

class ForecastHorizonClass(str, Enum):
    INTRABAR = "intrabar"        # < 1 min
    SHORT = "short"              # 1–15 min
    MEDIUM = "medium"            # 15 min – 4 h
    LONG = "long"                # > 4 h

class BetStructure(str, Enum):
    DIRECTIONAL_LONG = "directional_long"
    DIRECTIONAL_SHORT = "directional_short"
    MEAN_REVERT = "mean_revert"
    BREAKOUT = "breakout"
    CARRY = "carry"

class ConditioningFamily(str, Enum):
    ENGINE_INTERNAL = "engine_internal"     # qualité structure / pattern / contexte moteur
    SCORING = "scoring"                     # pénalité coût / staleness / fragilité régime
    HARD_BLOCK = "hard_block"               # pair_health / data_freshness / budget dépassé
    PORTFOLIO = "portfolio"                 # conflit corrélation / BTC factor / opportunity cost

class ConditioningRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    family: ConditioningFamily
    code: str                       # e.g. "scoring.cost_penalty.absorptive"
    value: float | None = None
    triggered_no_trade: bool = False

class SignalCandidate(BaseModel):
    """Narang-grade enriched contract layer (migrated progressively from the current canonical SignalCandidate)."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    strategy_id: str
    engine_id: Literal["A", "B", "C", "D"]
    pair: str
    side: Literal["buy", "sell"]
    # Carver standardised forecast in [-20, +20] (per Carver scaling, scaled to E[|F|]=10)
    forecast_direction: float = Field(ge=-1.0, le=1.0)
    forecast_strength: float = Field(ge=0.0, le=20.0)
    forecast_horizon_class: ForecastHorizonClass
    forecast_target_class: ForecastTargetClass
    bet_structure: BetStructure
    confidence_band: float | None = Field(default=None, ge=0.0, le=1.0)
    conditioning_state: tuple[ConditioningRecord, ...]
    expected_cost: float = Field(ge=0.0)            # in account ccy
    expected_break_even: float = Field(ge=0.0)
    expected_ce: float                              # capital efficiency, can be negative
    expected_gain: float
    invalidation_ref: str | None = None             # link to invalidation contract
    reason_codes: tuple[str, ...] = ()
    versions: dict[str, str]                        # engine_version, calibration_version, ...
```

### 3.2 New modules (Phase 4–5 additions)
| Module | Path | Mission | Phase |
|---|---|---|---|
| `model_risk_registry` | `src/meta_learning/model_risk_registry/` | Track drift replay → shadow → micro-live → live (cost, frequency, CE, DTR) | P3 (created), P4 (active) |
| `strategy_drift_monitor` | `src/meta_learning/strategy_drift_monitor/` | Per-engine drift on forecast distribution + win-rate + CE | P3 |
| `cost_drift_monitor` | `src/meta_minimal/cost_drift_monitor/` | Drift `expected_cost` vs realised, alert >20% bias | P2 |
| `crowding_suspicion_monitor` | `src/meta_learning/crowding_suspicion_monitor/` | Detect implicit multi-edge collapse (engines A and B drift to same trades) | P4 |
| `regime_shift_watcher` | `src/risk_backbone/regime_shift_watcher/` | Soft signal feeding regime_change_detector (extends P4-02) | P4 |

### 3.3 Three-layer cost doctrine (Phase 2–3 reinforcement)
Replaces P5-XX scattered cost handling.
1. **Ex-ante** — `expected_cost`, `expected_break_even`, `expected_ce` populated on every `SignalCandidate`. No-trade if cost ≥ EV.
2. **Realised (shadow / live)** — `execution_cost_meter` records explicit fee + slippage + impact + partial-fill penalty + drift vs ex-ante.
3. **Meta** — per-pair / per-engine cost drift, break-even inflation, phantom-trade rate, cost-shock alerts (`cost_drift_monitor` above).

### 3.4 Five portfolio arbitration questions (Phase 5)
Doc 19's `portfolio_minimal/allocation_router` becomes opinionated — it must **explicitly score every accepted candidate** against the 5 Narang questions and log the answer:
1. best net score?
2. best expected CE?
3. best capital lock-up utilisation?
4. lowest correlated-budget consumption?
5. lowest hidden structural risk addition?

Output: `PortfolioArbitrationRecord` (frozen Pydantic) attached to every promoted intent. **No raw-score-only selection.**

### 3.5 Reject from Narang (explicit)
- ❌ HFT speed obsession.
- ❌ Equities/futures stat-arb forms (sector-neutral models, US risk models).
- ❌ Off-the-shelf models as conceptual crutch.
- ❌ Plugin research libre non versionné.
- ❌ ML opaque non auditable in Light core.

---

## 4. Taleb — governance integration map

Source: `V5_3_ANNEXE_TALEB_FOOLED_BY_RANDOMNESS.md`.

### 4.1 Six obligations (cross-cutting, every phase)
1. **Luck ≠ skill** → no engine promoted on win-rate alone; require net-of-cost edge + CE + stress + cross-regime stability.
2. **Blowup risk** → reject any engine with hidden negative convexity, even with great win-rate.
3. **Survivorship bias** → log refused/phantom/no-fill/abandoned-run with structured codes.
4. **Noise vs signal** → real-time monitoring is for safety only; strategic verdicts come from aggregated periods.
5. **Alternative histories** → mandatory replay + adverse scenarios + cost stress + latency stress + partial-fill stress.
6. **Survival > apparent performance** → kill-switch and gates always preferred to "looks good lately".

### 4.2 Quadruple filter (mandatory promotion gate)
Inserted **before** any phase-end gate in doc 19. A feature/engine/version cannot promote unless **all four** are green:
| Filter | Concrete check | Source module |
|---|---|---|
| ✔ Real cost | `realised_cost ≤ 1.2 × expected_cost` over last 200 events | `execution_cost_meter` + `cost_drift_monitor` |
| ✔ Queue risk | `worst_drawdown_5pct_tail ≥ −2 × avg_drawdown` (no fat-left-tail) | `loss_budgeter` extension `tail_risk_meter` (NEW) |
| ✔ Parity local/shadow/live | `|metric_local − metric_shadow| / metric_local < 10%` on PnL, fill-rate, CE | `model_risk_registry` |
| ✔ Cross-regime robustness | metric stable across ≥ 3 regime buckets (vol-low / vol-mid / vol-high) | `regime_shift_watcher` + `cra_monitor` |

### 4.3 New module: `RefusalRecord` (Phase 1 add)
Anti-survivorship-bias logger. Path: `src/interface_contracts/refusal_records.py`.

```python
class RefusalCategory(str, Enum):
    NO_TRADE = "no_trade"               # engine emitted but EV/CE/cost rejected
    NO_FILL = "no_fill"                 # order placed but never filled
    PHANTOM = "phantom"                 # would have filled in shadow but skipped in live
    HARD_BLOCK = "hard_block"           # gated by risk layer
    PORTFOLIO_REJECTED = "portfolio_rejected"  # lost arbitration
    VERSION_INVALIDATED = "version_invalidated"

class RefusalRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    timestamp_ns: int
    pair: str
    engine_id: Literal["A", "B", "C", "D"] | None
    category: RefusalCategory
    reason_codes: tuple[str, ...]
    counterfactual_pnl: float | None = None  # what we would have made (if known)
```

Stored alongside accepted-trade journal. Surfaces in dashboards. **Required** for Taleb survivorship-bias compliance.

### 4.4 New module: `tail_risk_meter` (Phase 4 add)
Path: `src/risk_backbone/tail_risk_meter/`.
- Computes 5%-tail conditional loss per engine over rolling 500 events.
- Halts engine if `tail_loss_5pct > 3 × median_loss` (anti-blowup).
- Threshold ID: **THR-T01** (hard cap 5×, default 3×).

### 4.5 Reject from Taleb (explicit)
- ❌ Turn Taleb into a new engine.
- ❌ Use Taleb as anti-formalisation excuse.
- ❌ Use Taleb to refuse measurement.

---

## 5. Phase-by-phase delta (against doc 19)

### Phase 0 — unchanged
Already complete (2902 → 2940 green after Phase 1 plumbing landed).

### Phase 1 — multi-pair plumbing — **+1 task**
| ID | Task | Files | Test gate |
|---|---|---|---|
| **P1-07 (NEW)** | Add `RefusalRecord` contract + `RefusalJournal` writer (frozen append-only) | `src/interface_contracts/refusal_records.py` + `src/meta_minimal/refusal_journal/` | unit: every refusal category writes valid record; journal rejects mutation |

### Phase 2 — microstructure — **+3 tasks**
| ID | Task | Files | Test gate |
|---|---|---|---|
| **P2-06 (NEW)** | Implement enriched `SignalCandidate` per §3.1 as an additive migration seam; migrate engines A/B emission via adapters before any canonical merge | `src/interface_contracts/forecast_contracts.py` + engine adapters | every existing engine test still green; new contract tests ≥ 15 |
| **P2-07 (NEW)** | `forecast_normalizer.py`: implement Carver `F_i ∝ E[r_i]/σ_i` with `ForecastScalar = 10/E[|F|]` learned offline per engine | `src/scoring_backbone/forecast_normalizer.py` + calibration seam | unit: `E[|F_normalised|] ≈ 10` after scaling |
| **P2-08 (NEW)** | `break_even_filter.py`: gates `SignalCandidate` emission on `EV^net = x × (E[g] − E[c]) > THR-W01_floor` (Carver §7) | `src/scoring_backbone/break_even_filter.py` + calibration | unit: cost ≥ gain → no emit; cost ≪ gain → emit |
| **P2-09 (NEW)** | `cost_drift_monitor`: ex-ante vs ex-post cost tracking, alerts when bias > 20% | `src/meta_minimal/cost_drift_monitor/` | unit: synthetic cost stream with 30% bias → alert fires |

### Phase 3 — ML enabler — **+2 tasks, +1 hard rule**
- **Hard rule (Carver+Narang)**: ML enabler **cannot** override engine A/B/C/D output. It only modulates the score via THR-M01 with `α ≤ 0.5` cap (already in doc 19). Reaffirm in PR description.

| ID | Task | Files | Test gate |
|---|---|---|---|
| **P3-08 (NEW)** | `model_risk_registry`: track per-model `train_window`, `oos_sharpe`, `feature_hash`, `promotion_state`, replay vs shadow vs live drift | `src/meta_learning/model_risk_registry/` | drift simulator → registry flags promotion-block |
| **P3-09 (NEW)** | `strategy_drift_monitor`: per-engine drift on forecast distribution, WR, CE; emit `RefusalRecord` if drift halts the engine | `src/meta_learning/strategy_drift_monitor/` | synthetic drift → engine paused, refusal logged |

### Phase 4 — vol-target + regime — **rewrite P4-01 + add 3 tasks**
- **P4-01 REVISED** (Carver-canonical): replace fixed sizing with the **full Carver chain**:
  ```
  instrument_value_vol = price × instrument_pct_vol × point_value
  vol_scalar = (capital × annual_vol_target / sqrt(252)) / instrument_value_vol
  N_candidate = (forecast_normalised / 10) × vol_scalar
  N_final = clip(N_candidate × CE_filter × cluster_filter × btc_filter, min_notional, max_position_cap)
  ```
  Threshold THR-S07 stays (vol target ≤ 2%). **Forecast must be Carver-normalised** (P2-07) before this stage.

| ID | Task | Files | Test gate |
|---|---|---|---|
| **P4-05 (NEW)** | `tail_risk_meter`: rolling 500-event 5%-tail loss per engine, halt if > 3× median (THR-T01) | `src/risk_backbone/tail_risk_meter/` + calibration | unit: heavy-tailed synthetic stream → halt fires |
| **P4-06 (NEW)** | `crowding_suspicion_monitor`: alert if engine A & B trade overlap > 70% over rolling 100 trades (false multi-edge) | `src/meta_learning/crowding_suspicion_monitor/` | unit: overlapping streams → alert |
| **P4-07 (NEW)** | `regime_shift_watcher`: 3 regime buckets (vol-low/mid/high); CE-stability check feeds P4-02 detector | `src/risk_backbone/regime_shift_watcher/` | unit: regime swap → bucket change reported |

### Phase 5 — execution — **+1 task**
| ID | Task | Files | Test gate |
|---|---|---|---|
| **P5-03 (NEW)** | `PortfolioArbitrationRecord`: every promoted intent carries answers to Narang's 5 questions; refused candidates get `PORTFOLIO_REJECTED` `RefusalRecord` | `src/portfolio_minimal/arbitration_record.py` + extend `src/portfolio_minimal/portfolio_orchestrator.py` / allocation router | unit: 5-candidate batch → 1 promoted with full record, 4 refused with codes |

### Phase 6 — capital ramp — **add quadruple filter as gate**
Each tier transition (`$100 → $200 → $500 → $2K → $4K`) must additionally pass §4.2 quadruple filter, machine-checked by `capital_ramp_gate.py`. **Operator cannot override.**

---

## 6. New threshold IDs (additions to doc 19's list)

| ID | Meaning | Hard cap | Default | Module |
|---|---|---|---|---|
| **THR-W01** | Min `EV^net` floor for SignalCandidate emission | 0.0 (cannot disable) | $0.05/event | `break_even_filter` |
| **THR-T01** | Tail-loss multiplier vs median triggering engine halt | ≤ 5× | 3× | `tail_risk_meter` |
| **THR-D01** | Cost-drift bias % triggering alert | ≤ 50% | 20% | `cost_drift_monitor` |
| **THR-D02** | Strategy drift KS p-value triggering pause | ≥ 0.001 | 0.01 | `strategy_drift_monitor` |
| **THR-C01** | Engine-overlap % triggering crowding alert | ≤ 90% | 70% | `crowding_suspicion_monitor` |
| **THR-Q01** | Quadruple-filter parity tolerance (`|metric_local − metric_shadow| / metric_local`) | ≤ 25% | 10% | `capital_ramp_gate` |
| **THR-X08** | A↔C mutual-exclusion window same (pair, direction) — C blocked while A holds | ≤ 12h | 2h | `engine_coordination_rules` |
| **THR-X09** | A recent-fire suppression of C on same setup (post-exit absorption window) | ≤ 24h | 4h | `engine_coordination_rules` |
| **THR-X10** | D anti-revenge parametric-cooldown **failsafe** (only fires if no fresh A detection within 72h; strategy β is primary) | ≤ 48h | 24h | `engine_coordination_rules` |
| **THR-X11** | D max consecutive re-entries per (pair, direction) before structural reset required | ≤ 3 | 1 | `engine_coordination_rules` |
| **THR-F01** | B sub-signal max intra-family correlation (VPIN-fade vs existing B signal) | ≤ 0.9 | 0.7 | `engine_b.sub_signals` |

All follow the existing calibration-seam pattern (`risk_runtime_drawdown_calibration.py`).

---

## 7. Reinforced prohibitions (delta vs doc 19 §3)

In addition to doc 19's list, Sonnet must **also not**:

9. Emit a `SignalCandidate` without `forecast_horizon_class`, `bet_structure`, `expected_cost`, `expected_ce`, `reason_codes`. (Narang §3.1)
10. Use ML enabler output to bypass engine emission or to set side independently. (Carver + Narang)
11. Promote a feature/model/engine without all four quadruple-filter checks green. (Taleb §4.2)
12. Use Kelly-full sizing or Kelly fraction > 0.5. (Carver §4.3)
13. Skip `RefusalRecord` writing on any rejected candidate, no-fill, phantom, or version invalidation. (Taleb §3.3)
14. Tune any threshold purely on backtest PnL improvement. (Taleb §3.1, Carver §9 anti-overfitting)
15. Implement Forecast Diversification Multiplier or full portfolio variance optimisation in Light. (Carver: those are Complete-only.)

---

## 8. Test matrix delta (in addition to doc 19 §5)

| Suite | Expected new tests |
|---|---|
| `tests/test_interface_contracts/test_forecast_contracts.py` | ≥ 20 |
| `tests/test_interface_contracts/test_refusal_records.py` | ≥ 8 |
| `tests/test_meta_minimal/test_refusal_journal/` | ≥ 10 |
| `tests/test_meta_learning/test_model_risk_registry/` | ≥ 15 |
| `tests/test_meta_learning/test_strategy_drift_monitor/` | ≥ 10 |
| `tests/test_meta_minimal/test_cost_drift_monitor/` | ≥ 8 |
| `tests/test_meta_learning/test_crowding_suspicion_monitor/` | ≥ 6 |
| `tests/test_scoring_backbone/test_forecast_normalizer.py` | ≥ 12 |
| `tests/test_scoring_backbone/test_break_even_filter.py` | ≥ 10 |
| `tests/test_risk_backbone/test_tail_risk_meter/` | ≥ 10 |
| `tests/test_risk_backbone/test_regime_shift_watcher/` | ≥ 8 |
| `tests/test_portfolio_minimal/test_arbitration_record.py` | ≥ 8 |
| **TOTAL** | **≥ 125 new tests** |

Final target after this addendum: `rtk pytest tests/` → ~3115+ green.

---

## 9. Carver-NOW vs LATER vs RESEARCH (synthesis from `MATH CARVNER.docx`)

### NOW — Light, integrated into Phases 1–4
1. Net return / variance / observed Sharpe per moteur, paire, portefeuille.
2. Engines A/B forecasts on a common standardised scale (Carver `F` with `ForecastScalar`).
3. Volatility targeting at portfolio level.
4. Sizing based on instrument vol + standardised forecast + V5.3 caps.
5. Cost / break-even / EV-net discipline.
6. CE per moteur / paire / portefeuille (already exists, surface).
7. Minimum portfolio diversification (caps + cluster + BTC budget — already exists, no heavy optimisation).

### LATER — Complete only (Build-15/16/17)
8. Full Forecast Diversification Multiplier.
9. Full Instrument Diversification Multiplier.
10. Complete portfolio variance + MRC + RC.
11. Shrunk covariance / advanced analytics (Complete UI).

### RESEARCH — documented only, no Light dependency
- Carver's parameter-fitting heuristics for trend strategies (engine D candidate, post-Live-Light).
- Carver's commentary on Sharpe interpretation (post-mortem doctrine).

---

## 10. Verdict and immediate next action

**Verdict**: the three frameworks are **mutually reinforcing and non-redundant**:
- Carver tells V5.3 *how to be shaped* (forecast → vol target → sizing → portfolio).
- Narang tells V5.3 *how to talk to itself* (contracts, conditioning families, model risk, cost layers).
- Taleb tells V5.3 *how not to lie to itself* (refusal logging, blowup, parity, cross-regime).

None contradicts the V5.3 canon, the Build-14 enabler pattern, or the LIGHT/COMPLETE separation. All three reinforce: **no engine demolition, no profile invention, no pipeline bypass.**

**Next immediate action for Sonnet**:
1. Read this doc + doc 19 in full.
2. Apply Phase 1 delta first: implement `RefusalRecord` + `RefusalJournal` (P1-07).
3. Do **not** start Phase 2 microstructure work until P1-07 is green and merged, because every subsequent module writes to the journal.
4. Then enter Phase 2 with the **enriched `SignalCandidate` migration seam** (P2-06) **before** any microstructure feature lands — the contract is upstream of all features.

---

**Status**: ADDENDUM COMPLETE — execution-ready, subordinate to V5.3 canon and to doc 19.

---

## 11. Engine Coordination Rules (Narang-grade conditioning, NOT Carver FDM)

**Why not Carver FDM**: Carver's Forecast Diversification Multiplier handles *correlated but independent* forecasts sharing a common bet structure. V5.3 engines A/B/C/D have **different bet_structures** and must enforce **categorical exclusion at the conditioning layer**, not a continuous haircut. Narang §3.3 HARD_BLOCK family is the correct mechanism.

### 11.1 Rule set (to land in `src/protocols/engine_coordination_rules.py` with typed contracts in `src/interface_contracts/`)

| Rule | Trigger | Effect | Threshold |
|---|---|---|---|
| **R-AC-1** | A holds open position (pair=P, direction=d) | C emission on (P, d) → HARD_BLOCK `ConditioningRecord(code="hard_block.ac_mutual_exclusion.a_holding")` | THR-X08 (window = holding duration + 2h grace, cap 12h) |
| **R-AC-2** | A exited (pair=P, direction=d) within last THR-X09 on same structural setup | C emission on (P, d, same_setup) → HARD_BLOCK `ConditioningRecord(code="hard_block.ac_recent_fire")` | THR-X09 (4h default, cap 24h) |
| **R-D-1** | D emission without `first_episode_ref` pointing to a completed A or C episode on same (pair, direction) | HARD_BLOCK `ConditioningRecord(code="hard_block.d_no_historical_linkage")` | — (structural, no threshold) |
| **R-D-2** | D attempted on (pair, direction) where prior D consecutive stop count ≥ THR-X11 without intervening fresh A detection | HARD_BLOCK `ConditioningRecord(code="hard_block.d_consecutive_stops_reset_required")` | THR-X11 (1 default, cap 3) — **strategy β** |
| **R-D-3** (failsafe) | R-D-2 in effect AND no fresh A detection arrived within 72h | After THR-X10 timer, R-D-2 expires and D may re-emit once (then R-D-2 resumes) | THR-X10 (24h default, cap 48h) |
| **R-D-4** | D position sizing | `N_D = 0.5 × N_first_episode_reference` (D is never a primary sized entry) | hard-coded 0.5 multiplier; no calibration override |

### 11.2 Conditioning records emitted

Every engine emission carries in `conditioning_state` the evaluation trace. Blocked paths append a HARD_BLOCK `ConditioningRecord` and a `RefusalRecord(category=HARD_BLOCK, reason_codes=(…,))` to `RefusalJournal`. Blocked paths do **not** emit a canonical `SignalCandidate`; this avoids inventing a fake `side="flat"` state that does not exist in the runtime enum.

### 11.3 What this is NOT

- NOT Carver FDM (no forecast correlation haircut).
- NOT a soft scoring penalty (these are HARD_BLOCKs, not Narang SCORING family).
- NOT an IDM (Instrument Diversification Multiplier) concern.
- NOT operator-overrideable.

### 11.4 Forecast strength ranges per engine (Narang §3.1 + Carver §F scaling)

| Engine | `forecast_strength` range | Rationale |
|---|---|---|
| A | [0, 20] | Full Carver scale; A is the conviction engine (Tier-3 candidate). |
| B | [0, 15] | MR bet; capped to prevent B from displacing A on score. |
| C | [0, 15] | Continuation bet; not a replacement for A's conviction. |
| D | [0, 10] | Re-entry is by construction a *lower-confidence* second attempt. |

Hard-coded at the Pydantic contract layer (`Field(ge=0.0, le=20.0)` for A, etc.) via engine-specific subclasses or validated at the engine-runtime layer. **Enforce at contract, not at scoring.**

---

## 12. Local / VPS resource allocation + capital reality

### 12.1 Architecture reality (user confirmed)

| Component | Hardware | Responsibility | Profile |
|---|---|---|---|
| **Local lab PC** | 32 GB RAM, i7, GPU 1060 6 GB | Heavy compute: calibration, ML training, walk-forward, backtests, microstructure feature research, SHAP, drift registries, 20+ pair shadow analytics | `LAB_ONLY` + `SHARED` for contracts |
| **VPS** | Minimal (execution-class) | Live execution, WS ingestion, order routing, order-state machine, kill-switches, Prometheus/Grafana export | `VPS_ONLY` + `SHARED` |
| **Transport** | `backtest_artifact_import` | Calibration files, ML models, promotion records, threshold catalogs flow **Local → VPS** one-way; logs flow VPS → Local via Prometheus scrape + Grafana | `TRANSPORT` |

**Hard rule**: VPS never trains, never runs LightGBM fit, never runs Optuna. VPS loads artefacts and executes. Local never places orders on Binance.

### 12.2 Shadow universe vs Live universe (Carver-inspired selection)

- **Shadow universe** (Local + VPS shadow): **≥ 20 instruments always**. This is the population from which live candidates are drawn.
- **Live universe**: tier-gated subset (T1=3 → T5=16). Selection criteria are **ex-ante structural**, NOT post-hoc PnL (Taleb §3.3 anti-survivorship):
  1. Binance spot liquidity (avg daily volume ≥ $100M)
  2. L2 book depth stability (queue half-life > 5s at ±5 bps)
  3. Tick/lot constraints compatible with €300 notional (`min_notional × 3` feasible)
  4. Cross-pair residualized correlation < 0.85 vs already-selected pairs
  5. Sharpe-deflated shadow performance (Harvey-Liu-Zhu haircut `SR_deflated = SR × √((N−k)/(N−1))` with k = pairs tested)
  6. Cost stability: `cost_drift_monitor` green in shadow ≥ 4 weeks
  7. Structural regime coverage: pair traded across ≥ 3 regime buckets (doc 20 §4.2)

**No pair enters Live on PnL ranking alone.**

### 12.3 Capital reality

| Label | Figure | Meaning |
|---|---|---|
| **Real starting capital** | **€300–€400** | T1 deployment. 3 pairs. Engine A only live. |
| **Binance spot `min_notional`** | $5 per order | Real constraint. With 3× buffer → €15 min order. |
| **Ceiling headroom** | **$4,000** | T5. Reached by *evolution of capital*, not by injecting €4K on day one. |
| **Tier progression** | Gated | doc 19 §6 table, doc 20 §4.2 quadruple filter, doc 20 §11 coordination audit. |

No reference to "$4K starting capital" should exist anywhere in the codebase or calibration files. If found → bug. Use `capital_reality_catalog.py` or similar SHARED constants module.

### 12.4 Strategy identity per Carver §doctrine

Each strategy has identity: `{engine_id, pair, regime_bucket, forecast_target_class, bet_structure, calibration_version}`. A "strategy" is *not* just an engine — it is the tuple. This means engine A on BTC in regime vol-high is a distinct strategy from engine A on ETH in regime vol-low. Promotion, refusal, and PnL aggregation happen at the **strategy tuple level**, not the engine level.

Planned landing path: `StrategyIdentity` frozen Pydantic model in `src/interface_contracts/strategy_identity.py`; every `SignalCandidate.strategy_id` resolves to one `StrategyIdentity`.

---

## 13. Engine Canon — A / B / C / D (user doctrine, verbatim then formalised)

### 13.1 User doctrine (verbatim)

> **A = Premium Trend / Expansion**: "moteur haute conviction / cherche les meilleurs trades, pas la fréquence / capte un trend déjà propre ou une expansion bien structurée / seul moteur naturellement compatible avec une concentration contrôlée plus forte, donc le seul vrai candidat régulier au Tier 3."
>
> **B = Mean Reversion Intraday**: "augmente la fréquence utile / recycle le capital plus vite / capte des excès de court terme suivis d'un retour vers une moyenne locale."
>
> **C = Breakout Continuation**: "capter des sorties de range et des continuations post-breakout / seulement si cette continuation n'est pas déjà absorbée par A."
>
> **D = Re-entry / Second Chance**: "réengager du capital après un premier contexte déjà validé / seulement quand une nouvelle structure exploitable se reforme / seulement si la valeur marginale de ce réengagement est positive."

### 13.2 Formalised contracts (feed docs 21/22)

| Engine | `bet_structure` | `forecast_target_class` | Primary vs dependent | Tier |
|---|---|---|---|---|
| A | `BREAKOUT` or `DIRECTIONAL_{LONG,SHORT}` (trend expansion) | `DIRECTION_PLUS_STRENGTH_PLUS_HORIZON` (long horizon) | Primary | T1+ |
| B | `MEAN_REVERT` | `DIRECTION_PLUS_STRENGTH` (short horizon, intrabar/short) | Primary | T2+ |
| C | `BREAKOUT` (continuation post-breakout, distinct from A's initial detection) | `DIRECTION_PLUS_STRENGTH_PLUS_HORIZON` (medium horizon) | Primary, **gated by R-AC-1/R-AC-2** | T3+ |
| D | Same `bet_structure` as `first_episode_ref.bet_structure` | Same `forecast_target_class` as first episode, `forecast_strength ∈ [0, 10]` | **Dependent** (requires `first_episode_ref`) | T4+ |

### 13.3 Why C ≠ A (structural separation)

A fires on the **initial detection** of trend expansion / structural breakout. C fires on the **continuation leg after a breakout that A did not capture** (either A was in risk-off, or A's setup wasn't triggered yet). If A is already long on the same (pair, direction) within THR-X08, C's continuation leg is *already absorbed* by A's running exposure — duplicating it = unpriced crowding risk → HARD_BLOCK.

### 13.4 Why D ≠ C (structural separation)

C requires only current-bar evidence of continuation. D requires **historical evidence** (`first_episode_ref`) that the context was already validated in a prior closed episode, AND current-bar evidence that a new exploitable structure is re-forming. D is *never* a primary entry; it is a sized re-engagement (0.5× of first-episode reference).

### 13.5 S1/S2 placement (from user directive)

- **S1 — Toxic flow fade (VPIN contrarian)**: B sub-signal (doc 19 P2-10), NOT engine C. VPIN-fade is contrarian (fade the toxic flow), `bet_structure = MEAN_REVERT` → MR family → B.
- **S2 — Residualized cross-pair momentum**: Build-14 feature feeding `ml_confidence_enabler` (doc 19 P3-11), NOT engine C or D. Cross-sectional relative-value has `bet_structure = RELATIVE_FORECAST`, incompatible with C (`BREAKOUT`) and D (mirror of first episode).

---
