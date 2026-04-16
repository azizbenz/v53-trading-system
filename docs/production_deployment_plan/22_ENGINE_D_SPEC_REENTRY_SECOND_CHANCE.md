# 22 — Engine D Specification: Re-entry / Second Chance

**Status**: SPEC — doctrinal deepening of an existing Engine D implementation; blocked until Engine C (doc 21) is shadow-green ≥ 4 weeks.
**Date**: 2026-04-15
**Parent canon**: V5.3; companion docs: 19, 20, 21, 23.
**Version pin**: `doc_23@834f7fae4a06847121670559dd5bfd65c28d82da`
**Scope**: full Narang-grade specification for Engine D. D is **never a primary entry** — it is a structural re-engagement bound to a prior A or C episode. This is **not** a greenfield engine spec: `src/engines/engine_d/` already exists and must be evolved surgically.

---

## 0. One-line definition (user doctrine, doc 20 §13.1)

> **D = Re-entry / Second Chance** — "réengager du capital après un premier contexte déjà validé / seulement quand une nouvelle structure exploitable se reforme / seulement si la valeur marginale de ce réengagement est positive."

D re-engages capital *only* after:
1. A prior A or C episode on the same (pair, direction) **closed** (`first_episode_ref`).
2. A **new** exploitable structure is re-forming now.
3. The marginal value of this re-engagement is **positive** net of cost and of the anti-revenge discipline.

---

## 1. Structural separation vs A and C

| Dimension | A | C | D |
|---|---|---|---|
| Historical context needed | None (initial) | Post-breakout reference (current-bar evidence) | **Prior closed A or C episode** (`first_episode_ref`) + current-bar evidence |
| Primary vs dependent | Primary | Primary (gated by A exclusion) | **Dependent** — never primary |
| Conviction profile | `forecast_strength ∈ [0, 20]` | `[0, 15]` | `[0, 10]` |
| Sizing | Full Carver chain | Full Carver chain | `N_D = 0.5 × N_first_episode_reference` (hard rule R-D-4) |
| Consecutive-stop rule | N/A | N/A | **Strategy β**: blocked after THR-X11 consecutive stops until fresh A detection on (pair, direction) resets context |

---

## 2. Surgical landing map onto the existing `engine_d/` implementation

```
src/engines/engine_d/
├── __init__.py
├── engine_d_runner.py                 # existing runner; keep as orchestration seam
├── engine_d_runtime.py                # existing runtime; current SignalCandidate builder seam
├── context_resolver_d.py              # existing context / linkage seam to deepen first
├── signal_math_d.py                   # existing re-entry math seam
├── conviction_builder_d.py            # existing conviction seam
├── cost_feasibility_d.py              # existing cost seam
├── invalidation_mapper_d.py           # existing invalidation seam
├── output_payload_builder_d.py        # existing payload seam
├── first_episode_resolver_d.py        # REQUIRED — explicit history resolution from closed_episode_journal
├── historical_linkage_guard_d.py      # REQUIRED — isolated R-D-1 / R-D-2 / R-D-3 enforcement seam
├── consecutive_stop_counter_d.py      # REQUIRED — persistent strategy β state seam
├── anti_revenge_cooldown_d.py         # OPTIONAL — may fold into historical_linkage_guard_d if behavior stays explicit
└── signal_reporter_d.py               # OPTIONAL — may stay inside `engine_d_runtime.py` if the facade remains surgical

tests/test_engines/test_engine_d/
├── existing Engine D tests remain authoritative
├── add targeted tests for episode resolution / linkage / beta reset / marginal EV
└── do not create a parallel Engine D test stack detached from the current runtime
```

---

## 3. Signal pipeline

### Stage 1 — `first_episode_resolver_d.py`
Scans `closed_episode_journal` (a frozen append-only record of closed trades from A and C) for the most recent closed episode on the current (pair, direction) within a lookback window `THR-D_LOOKBACK` (default 12h, cap 48h).

- If no such episode → append `RefusalRecord(category=HARD_BLOCK, reason_codes=("d.no_first_episode",))` and emit no canonical `SignalCandidate`.
- If found → bind `first_episode_ref = EpisodeRef(episode_id, engine_id_of_origin, pair, direction, entry_level, exit_level, bet_structure, closed_at)`.

### Stage 2 — `historical_linkage_guard_d.py` (R-D-1 + R-D-2)
Queries `engine_coordination_rules`:

- **R-D-1 check**: does `SignalCandidate.first_episode_ref` exist? If no → HARD_BLOCK.
- **R-D-2 check**: on same (pair, direction), `consecutive_stop_count ≥ THR-X11`? If yes AND no fresh A detection has occurred since last stop → HARD_BLOCK with `code="hard_block.d_consecutive_stops_reset_required"`. **This is strategy β.**
- **R-D-3 check** (failsafe): if R-D-2 is blocking AND last D stop was > 72h ago AND no fresh A detection occurred → after `THR-X10` (24h default) timer, allow one D emission (then R-D-2 resumes normal enforcement).

Output: `HistoricalLinkageVerdict(blocked: bool, rule_fired, conditioning_record)`.

### Stage 3 — `structure_reformation_detector_d.py`
Detects a **new** exploitable structure on (pair, direction), distinct from `first_episode_ref`:
- New swing structure formed *after* `first_episode_ref.closed_at`.
- Price has re-approached the original level with fresh microstructure evidence (OFI alignment, queue state).
- Time since `first_episode_ref.closed_at` ≥ `THR-D_MIN_GAP` (default 15 min, cap 2h) — prevents over-trading on noise.

Output: `StructureReformation(detected: bool, evidence_codes: tuple[str, ...])`.

### Stage 4 — `marginal_value_estimator_d.py`
Computes marginal EV:
```
marginal_EV = E[gain_d] − E[cost_d]
```
Rank-4 user arbitration `D-2026-04-16-001` selected option `C`: no continuous `revenge_risk_penalty` is introduced at this stage. Anti-revenge discipline remains enforced by strategy β / R-D-2 / R-D-3 and must surface explicitly in replay/backtest evidence (closed episode journal + Engine D validation observability fields). If `marginal_EV ≤ THR-W01_floor` (doc 19 THR-W01) → no emit.

**Anti-overfitting discipline** (Carver + Taleb): `marginal_value_estimator_d` is **not** retunable per pair without shadow parity check of ≥ 4 weeks.

### Stage 5 — `conviction_builder_d.py`
Carver-normalised, clip to [0, 10]. Inputs:
- Structure-reformation evidence strength.
- OFI alignment vs first-episode direction.
- Time-decay factor (freshness of re-entry opportunity).

### Stage 6 — `cost_feasibility_d.py`
`break_even_filter` applied with D-specific cost model that accounts for: smaller position (0.5×), potentially worse microstructure (re-entry often in reactive phase).

### Stage 7 — `invalidation_mapper_d.py`
Invalidation = same structural level as `first_episode_ref`'s invalidation, but tightened by 0.5× (re-entry has less margin for error).

### Stage 8 — `signal_reporter_d.py`
```python
SignalCandidate(
    strategy_id=StrategyIdentity.resolve(engine_id="D", pair=P, regime=regime, ...).identity_str,
    engine_id="D",
    pair=P,
    side=<mirror first_episode_ref.direction>,
    forecast_direction=...,
    forecast_strength=...,                         # clipped [0, 10]
    forecast_horizon_class=first_episode_ref.forecast_horizon_class,  # inherits
    forecast_target_class=first_episode_ref.forecast_target_class,    # inherits
    bet_structure=first_episode_ref.bet_structure,                    # inherits
    confidence_band=...,
    conditioning_state=(
        ConditioningRecord(family=ENGINE_INTERNAL, code="engine_internal.d.structure_reformation", ...),
        ConditioningRecord(family=SCORING, code="scoring.d.marginal_ev_positive", value=marginal_EV),
        ...
    ),
    expected_cost=...,
    expected_break_even=...,
    expected_ce=...,
    expected_gain=...,
    invalidation_ref=<tightened InvalidationContract.id>,
    reason_codes=("d.reentry.valid_first_episode", "d.structure_reforming", ...),
    versions={...},
)
```

**Sizing rule R-D-4**: downstream `vol_target_sizer` (doc 19 P4-01) must multiply `N_D` by 0.5 when `engine_id == "D"`. This is hard-coded in `vol_target_sizer`, not calibration-driven.

---

## 4. Strategy β (consecutive-stop reset rule) — formal spec

```
state_per(pair, direction):
    consecutive_stop_count: int = 0
    last_stop_at: datetime | None = None
    last_fresh_a_detection_at: datetime | None = None

on D position closed with loss:
    if consecutive_stop_count < THR-X11:  # default 1
        consecutive_stop_count += 1
        last_stop_at = now
    else:
        raise InvariantViolation  # should have been HARD_BLOCKed before entry

on A emission (engine_coordination_rules notifies):
    last_fresh_a_detection_at = now
    if last_fresh_a_detection_at > last_stop_at:
        consecutive_stop_count = 0   # β reset

on D emission attempt:
    if consecutive_stop_count >= THR-X11:
        if last_fresh_a_detection_at is None or last_fresh_a_detection_at <= last_stop_at:
            # strategy β primary rule: blocked until fresh A detection
            if now - last_stop_at > 72h:
                # R-D-3 failsafe: after 72h + THR-X10 elapsed, allow one emission
                if now - last_stop_at > 72h + THR-X10:
                    permit_single = True
            HARD_BLOCK unless permit_single
```

State lives in `consecutive_stop_counter_d.py` with persistence via `RefusalJournal` + a frozen-append-only `EngineStateSnapshot` record so VPS restart preserves state.

---

## 5. Conditioning state (family placement)

| Check | Family | Code |
|---|---|---|
| No `first_episode_ref` | HARD_BLOCK | `hard_block.d_no_historical_linkage` (R-D-1) |
| Consecutive-stop threshold hit, β requires fresh A | HARD_BLOCK | `hard_block.d_consecutive_stops_reset_required` (R-D-2) |
| β failsafe window not yet reached | HARD_BLOCK | `hard_block.d_failsafe_cooldown_active` (R-D-3) |
| No new structure re-formed | ENGINE_INTERNAL | `engine_internal.d.no_reformation` |
| Structure re-formation below quality | ENGINE_INTERNAL | `engine_internal.d.reformation_weak` |
| Marginal EV ≤ floor | SCORING | `scoring.d.marginal_ev_fail` |
| Pair health stale | HARD_BLOCK | `hard_block.pair_health.stale_book` |

---

## 6. Thresholds

**P1-5 authoritative replacement table [Rang 1 + 2]**: the compact legacy table below is now superseded for implementation. D reuses the C microstructure thresholds where explicitly listed.

| ID | Meaning | Default | Hard cap | Module | Calibration module |
|---|---|---|---|---|---|
| THR-X10 | D anti-revenge parametric cooldown failsafe | 24h | 48h | `anti_revenge_cooldown_d` | `— (policy-governed)` |
| THR-X11 | D max consecutive re-entries before reset required | 1 | 3 | `consecutive_stop_counter_d` | `— (policy-governed)` |
| THR-D_LOOKBACK | `first_episode_ref` lookback window | 12h | 48h | `first_episode_resolver_d` | `risk_runtime_drawdown_calibration.py` |
| THR-D_MIN_GAP | Min gap between first_episode close and D emission | 15 min | 2h | `structure_reformation_detector_d` | `risk_runtime_drawdown_calibration.py` |
| THR-D_MARGINAL_EV_FLOOR | Min marginal EV after revenge penalty | inherits THR-W01 | — | `marginal_value_estimator_d` | `risk_runtime_drawdown_calibration.py` |
| THR-C_RK_BANDWIDTH_C | Realized-kernel bandwidth constant for D re-entry window | 0.4 | 1.0 | `structure_reformation_detector_d` | `risk_runtime_drawdown_calibration.py` |
| THR-C_RK_BUCKET_SIZE | Realized-kernel bucket duration for D re-entry window | 5 min | 15 min | `structure_reformation_detector_d` | `risk_runtime_drawdown_calibration.py` |
| THR-C_OFI_WINDOW | OFI post-close cumulation window (events) | 500 events | 2000 events | `structure_reformation_detector_d` | `risk_runtime_drawdown_calibration.py` |
| THR-C_KYLE_WINDOW | Kyle λ regression window for current re-entry context | 1h | 4h | `structure_reformation_detector_d` | `risk_runtime_drawdown_calibration.py` |
| THR-C_VPIN_BUCKETS | VPIN equal-volume bucket count for D toxicity check | 50 buckets/day | 100 buckets/day | `structure_reformation_detector_d` | `risk_runtime_drawdown_calibration.py` |

| ID | Meaning | Default | Hard cap | Module |
|---|---|---|---|---|
| THR-X10 | D anti-revenge parametric cooldown failsafe | 24h | 48h | `anti_revenge_cooldown_d` |
| THR-X11 | D max consecutive re-entries before reset required | 1 | 3 | `consecutive_stop_counter_d` |
| THR-D_LOOKBACK | `first_episode_ref` lookback window | 12h | 48h | `first_episode_resolver_d` |
| THR-D_MIN_GAP | Min gap between first_episode close and D emission | 15 min | 2h | `structure_reformation_detector_d` |
| THR-D_MARGINAL_EV_FLOOR | Min marginal EV after revenge penalty | inherits THR-W01 | — | `marginal_value_estimator_d` |

---

## 7. Test matrix (minimum to land)

**P1-5 paper-repro extension [Rang 1]**: the base suites below remain required, and the following paper-reproduction suites are now mandatory additions for D's recalculated post-close window.

**P1-6 authoritative replacement matrix [Rang 2]**: use the matrix below for implementation planning. The compact legacy matrix retained lower in this section is audit history only.

| Suite | Min tests | Focus | Hypothesis | Paper repro |
|---|---|---|---|---|
| `test_first_episode_resolver_d.py` | 6 | No episode, one episode in window, multiple episodes (most recent wins), outside lookback | yes | — |
| `test_historical_linkage_guard_d.py` | 10 | R-D-1 / R-D-2 / R-D-3 permutations | yes | — |
| `test_structure_reformation_detector_d.py` | 8 | Reformation detected, no reformation, gap too small, gap OK | yes | — |
| `test_marginal_value_estimator_d.py` | 6 | Positive EV, negative EV, revenge penalty scaling | yes | — |
| `test_consecutive_stop_counter_d.py` | 6 | Counter increments, β reset on fresh A, failsafe arms after 72h | yes | — |
| `test_anti_revenge_cooldown_d.py` | 4 | THR-X10 timer arms and releases | yes | — |
| `test_conviction_builder_d.py` | 4 | Carver normalisation + clip to [0, 10] | yes | — |
| `test_signal_reporter_d.py` | 6 | Full SignalCandidate with inherited fields from `first_episode_ref` | — | — |
| `test_engine_d_runtime.py` | 4 | End-to-end with fixtures | — | — |
| `test_realized_kernel_repro.py` | 1 | Fixed-seed realized-kernel benchmark recalculated on the current D re-entry window | — | yes |
| `test_ofi_repro.py` | 1 | OFI sign and persistence recalculated on the post-close window of `first_episode_ref` | — | yes |
| `test_kyle_lambda_repro.py` | 1 | Rolling `lambda_hat > 0` on informed-flow synthetic data for the current D window | — | yes |
| `test_vpin_repro.py` | 1 | VPIN tends to 1.0 under one-sided informed flow on the current D toxicity window | — | yes |
| **Total** | **≥ 54** | | | |

| Suite | Min tests | Focus |
|---|---|---|
| `test_realized_kernel_repro.py` | 1 | Paper repro: same fixed-seed realized-kernel benchmark, but recalculated on the current D re-entry window |
| `test_ofi_repro.py` | 1 | Paper repro: OFI sign and persistence recalculated on the post-close window of `first_episode_ref` |
| `test_kyle_lambda_repro.py` | 1 | Paper repro: rolling `lambda_hat > 0` on informed-flow synthetic data for the current D window |
| `test_vpin_repro.py` | 1 | Paper repro: VPIN tends to 1.0 under one-sided informed flow on the current D toxicity window |

These four suites raise the minimum D landing bar from `≥ 50` to `≥ 54` tests.

| Suite | Min tests | Focus |
|---|---|---|
| `test_first_episode_resolver_d.py` | 6 | No episode, one episode in window, multiple episodes (most recent wins), outside lookback |
| `test_historical_linkage_guard_d.py` | 10 | R-D-1 / R-D-2 / R-D-3 permutations |
| `test_structure_reformation_detector_d.py` | 8 | Reformation detected, no reformation, gap too small, gap OK |
| `test_marginal_value_estimator_d.py` | 6 | Positive EV, negative EV, revenge penalty scaling |
| `test_consecutive_stop_counter_d.py` | 6 | Counter increments, β reset on fresh A, failsafe arms after 72h |
| `test_anti_revenge_cooldown_d.py` | 4 | THR-X10 timer arms and releases |
| `test_conviction_builder_d.py` | 4 | Carver normalisation + clip to [0, 10] |
| `test_signal_reporter_d.py` | 6 | Full SignalCandidate with inherited fields from first_episode_ref |
| `test_engine_d_runtime.py` | 4 | End-to-end with fixtures |
| **Total** | **≥ 50** | |

Additional coordination tests in `tests/test_protocols/test_engine_coordination_rules/`:
- R-D-2 fires after 1 consecutive stop (default THR-X11=1).
- β resets on fresh A detection.
- R-D-3 failsafe releases exactly one emission after 72h + THR-X10.

## Annexe A — Formules microstructure — D-specific

Engine D does not invent a second microstructure math stack. It inherits the same rank-1 formulas as Engine C and changes only the evaluation window.

[Rang 1 + 2] No crypto-specific rank-1 paper threshold fixes `THR-C_VPIN_MAX = 0.5`; for D as for C, VPIN toxicity cutoffs remain `TBD_shadow_calibration` until shadow closes them.

### A.1 Shared rank-1 formulas reused by D

- **Realized kernel volatility**: Barndorff-Nielsen, Hansen, Lunde, Shephard (2008), eq.(3.1)–(3.7), DOI `10.3982/ECTA6495`
- **OFI**: Cont, Kukanov, Stoikov (2014), eq.(1)–(3), DOI `10.1093/jjfinec/nbt003`
- **Kyle λ**: Kyle (1985), eq.(1), DOI `10.2307/1913210`
- **VPIN**: Easley, Lopez de Prado, O'Hara (2012), eq.(2)–(4), DOI `10.1093/rfs/hhs053`

### A.2 D-specific operational rules

**OFI is re-evaluated, not inherited.**

```text
OFI_post_close(N) = sum e_n
```

using the same event-level `e_n` definition as Engine C, but on the post-close window that starts at `first_episode_ref.closed_at_ns` and ends at the candidate D decision time.

**Realized kernel is recalculated, not inherited.**

```text
RK_reentry = RK(current post-close window)
```

The volatility context is allowed to change between the original episode and the re-entry attempt; therefore D must recompute `RK_t` on the current window using `THR-C_RK_BANDWIDTH_C` and `THR-C_RK_BUCKET_SIZE`.

**Kyle λ is recalculated on the current window.**

```text
Delta m_t = lambda_hat * SignedVolume_t + epsilon_t
```

using the current re-entry window, not the first episode window.

**VPIN stays current-window only.**

```text
VPIN_n = (1 / (n * V_bucket)) * sum |V_tau^B - V_tau^S|
```

using the current D toxicity window; VPIN is not inherited from `first_episode_ref`.

## Annex B — `ClosedEpisodeJournal` / `EpisodeRef` contracts

`ClosedEpisodeJournal` is a frozen append-only replay/protocol artifact and is the canonical rank-2 landing surface for Engine D historical linkage evidence. `EpisodeRef` must:
- carry `episode_id`, `engine_id_of_origin ∈ {A, C}`, `pair`, `side`, `entry_level`, `exit_level`
- preserve `bet_structure`, `forecast_horizon_class`, `forecast_target_class`
- timestamp closure as `closed_at_ns` (UTC epoch nanoseconds)
- carry `close_reason ∈ {take_profit, structural_exit, time_stop, stop_out}`
- carry `realized_pnl_decimal` as `Decimal`

`ClosedEpisodeJournal` must:
- remain append-only
- support replay/backtest persistence and deterministic hashing
- expose D-eligible filtering (`close_reason != stop_out`) without deleting stop-out episodes from evidence
- keep stop-out episodes visible for audit, but exclude them from D re-entry eligibility

---

## 8. Prohibitions specific to Engine D

1. **No** emission without `first_episode_ref` (R-D-1). Hard-contract validation in Pydantic.
2. **No** consecutive emission ≥ THR-X11 without a fresh A detection (strategy β).
3. **No** full-size emission — sizing is hard-coded at `0.5 × N_first_episode_reference`.
4. **No** D on a (pair, direction) where the first episode closed with a stop-out (D must only re-engage valid-context exits: take-profit, structural exit, time-stop with non-adverse close).
5. **No** 1990s TA indicator as trigger (doc 23 §6).
6. **No** operator override of R-D-2 or R-D-3.
7. **No** override by ML enabler.
8. **No** live deployment before Engine C has been shadow-green ≥ 4 weeks (needed to populate `closed_episode_journal` with C episodes D can reference).

---

## 9. Promotion pipeline for D

`Replay → Shadow (≥ 6 weeks, universe ≥ 20 pairs) → Micro-live (tier T4+ only) → Live-Light (T4+)`

Promotion requires:
- Quadruple filter green (doc 20 §4.2).
- `engine_coordination_rules` audit: 0 R-D violations leaking through.
- Sharpe-deflated shadow Sharpe ≥ 1.2 (D carries a higher bar than A/B/C because it is structurally a marginal re-engagement), using Harvey-Liu-Zhu 2016 eq.(8) `SR_deflated = SR × √((N−k_HLZ)/(N−1))`; [Rang 1 + 2 + 4] current V5.3 `multiple_testing_guard.py` seam exposes two explicit modes: `k_HLZ = pairs_tested` in observed-shadow mode and `k_HLZ = max(pairs_tested, 20)` in promotion-floor mode. The current docs 21/22 default is the user-selected observed-shadow mode, so the current numeric default is `k_HLZ = pairs_tested` (currently `12` in the repo pair catalogue), while `promotion_floor` remains an explicit conservative non-default option (module blob `b2aafc74bd5abdefc8810e69f1562e9cc6881007`).
- `marginal_EV` tracking: realised marginal EV within 20% of expected.
- β reset rule verified fired correctly in shadow (at least one documented case).

---

## 10. Why D is higher-bar than A/B/C (rationale)

D is the engine most exposed to **revenge trading** (Taleb §obligations 2, 6) and to **fooled-by-randomness** (re-entries that work once look tempting). Therefore:
- Hard rule: 0.5× sizing (R-D-4).
- Hard rule: consecutive-stop strategy β (R-D-2).
- Higher Sharpe bar for promotion (1.2 vs 1.0).
- `marginal_value_estimator` is an explicit gate, not just a scoring layer.

This is aligned with Carver (no Kelly-full, prudence), Narang (explicit conditioning), Taleb (survival > performance).

---

**Status**: SPEC COMPLETE. Doctrinal deepening is blocked until Engine C is shadow-green ≥ 4 weeks + `closed_episode_journal` populated.
