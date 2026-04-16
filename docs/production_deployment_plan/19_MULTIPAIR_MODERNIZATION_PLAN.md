# 19 — Multi-Pair Modernization Plan (7 crypto pairs, +profitability, +reactivity)

**Status**: EXECUTION-READY for Sonnet
**Date**: 2026-04-14
**Source**: Synthesis of codex audit (`E:/claude v5.3/modernisation de v5.3/`) + z2 architecture PDF + Opus review
**Scope**: Integrate ~40% of z2's proposal as Build-14/15 addenda, reject engine demolition, preserve canonical A/B/C/D, add multi-pair support for 7 pairs.

> **ADDENDUM (v2, 2026-04-15)**: see companion docs:
> - `20_CARVER_NARANG_TALEB_INTEGRATION.md` — Carver math discipline + Narang grammar + Taleb governance + **§11 Engine Coordination Rules (mutual exclusion + historical linkage)** + **§12 Local/VPS resource allocation** + **§13 Engine Canon (A/B/C/D user doctrine)**.
> - `21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md` — Narang-grade complete spec for Engine C.
> - `22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md` — Engine D (re-entry / second chance) spec with historical linkage + anti-revenge cooldown.
> - `23_MICROSTRUCTURE_FEATURE_DICTIONARY.md` — formal formulas for OFI, VPIN, Kyle λ, Amihud, Roll, Corwin-Schultz, realized kernel (Barndorff-Nielsen), Hawkes intensity, PIN; formal 1990s TA prohibition.
>
> Read all five before executing. **Capital reality** (doc 20 §12): real start **€300–€400 / 3 pairs (T1)**, $4K is the **ceiling headroom**, not the start.

---

## 0. Verdict on z2 proposal

**Accept (integrate as Build-14/15 enablers, NOT replacements)**:
1. Microstructure L2 features (OFI, VPIN, queue pressure) — real edge vs RSI/MACD.
2. LightGBM multi-pair classifier **as a new scoring-backbone soft-penalty enabler** (Build-14 pattern), not as engine replacement.
3. Vol-targeting position sizing replacing fixed exposure.
4. Feature promotion pipeline (Discovery → Validation → Candidate → Shadow → Live).
5. Regime-Change Detector as 10th risk layer.
6. Capital gradation ladder $100 → $200 → $500 → $2K → $4K with per-tier promotion gate.
7. Walk-forward + SHAP + OOS Sharpe ≥ 80% backtest as promotion criterion.

**Reject (with reason)**:
- Venue switch to Bybit → contradicts existing `binance_spot/` stack; massive rework uncosted.
- Demolish engines A/B/C/D → violates CLAUDE.md explicit rule.
- Maker-only dogma → unfilled in fast moves (exactly when ML edge exists); use hybrid maker→taker fallback.
- Decoy orders / RandomFactor sizing → theatre, degrades vol-targeting precision.
- Daily retrain on 90d window → chases regime noise; use weekly retrain on 180d + drift-gated.
- 8-pair diagram → normalize to **7 pairs**: BTC, ETH, SOL, XRP, LINK, BNB, ADA.

**Clarify**:
- z2's "shared core unique" = v5.3's existing LIGHT/COMPLETE profiles. Reframe, don't rebuild.
- Correlation filter 0.7 will reduce effective positions to ~1 on USDT pairs; raise to 0.85 or use residualized corr.
- Break-even at 51.2% WR + $0.30/trade is tight; design for 53% WR target with kill-switch at rolling 30-trade WR < 49%.

---

## 1. Target state (measurable)

| Metric | Current v5.3 | Target (12 weeks) |
|---|---|---|
| Pairs traded (T1 start → T5 ceiling) | 1 (BTC/USDT) | **3 (T1: BTC/ETH/SOL) → 7 core → 16 (T5 ceiling)**. Shadow universe always ≥ 20 (doc 20 §12). |
| Trades/week (universe) | 5–10 | 25–40 (maker+taker hybrid) |
| Expected monthly PnL / $4K | −$30 to −$60 | +$40 to +$200 (1–5%) |
| Feature count | ~15 (TA) | ~15 TA + ~20 microstructure |
| Decision layers | 4 engines (**A/B/C/D coded**; C/D require doctrinal deepening, not greenfield) | 4 engines (A premium trend, B MR intraday, **C breakout-continuation**, **D re-entry/second-chance**) + 1 ML enabler (Build-14) + `engine_coordination_rules` (doc 20 §11) |
| Risk layers | 9 | 10 (+ Regime-Change Detector) |
| Retrain cadence | manual | weekly walk-forward, auto-gated |
| Fee/trade (avg) | ~$0.50 | ~$0.35 (TWAP + maker-first hybrid) |

Opus note: the +$40 to +$200/mo range is deliberately more conservative than z2's +$90 to +$360. If after Phase 3 (weeks 7–9) shadow shows < +1%/mo median, **stop and recalibrate — do not push to Live**.

---

## 2. Phased execution (Sonnet will execute phases in order; each phase ends with a hard gate)

### Phase 0 — Clean baseline (week 1)
**Goal**: zero-debt base before adding features.

| ID | Task | Files | Test gate |
|---|---|---|---|
| P0-01 | Fix `scripts/shadow_vps_service_monitoring_support.py:10` import (`ShadowVpsServiceStore` → `from protocols`) | that file only | `rtk pytest tests/test_monitoring/test_shadow_vps_service_monitoring.py` green |
| P0-02 | Add `ScorePenaltyItem` import in `src/engines/engine_b/engine_b_runtime_support.py:381` | that file only | `rtk pytest tests/test_engines/test_engine_b/` green |
| P0-03 | Add 6 missing exports to `src/meta/__init__.py` (see 18_CODE_VS_PLAN…) | `src/meta/__init__.py` | `rtk pytest tests/test_meta/` green |
| P0-04 | Fix PYTHONPATH in `technical_dashboard_demo_support` launcher | script only | `rtk pytest tests/test_ui/` green |
| P0-05 | Debug meta_learning lifecycle failures (FIX-6/7) | `src/meta_learning/lifecycle*` | `rtk pytest tests/test_meta_learning/` green |
| P0-06 | Protocols test_live_light_runtime (31 fail) + test_shadow_vps_service_launcher (17 fail) | identify root cause first; likely single fixture | `rtk pytest tests/test_protocols/` green |
| P0-07 | **DELIVERED IN CODE** — W-02 `src/venue_adapters/binance_spot/rate_limiter.py` exists and is wired in `rest_client.py`; keep here only as audit trace, not active backlog | verify existing file + tests | no active action unless regression appears |

**Gate to Phase 1**: `rtk pytest tests/` returns 2888/2888 passing, 0 DAG violations, no skipped-critical.

### Phase 1 — Multi-pair data plumbing (weeks 2–3)
**Goal**: 7 WS streams, 7 L1/L2 caches, per-pair manifests.

| ID | Task | Files | Test gate |
|---|---|---|---|
| P1-01 | Extend `src/venue_adapters/binance_spot/ws_client.py` for 7-symbol multiplexed WS (combined stream `wss://stream.binance.com/stream?streams=btcusdt@...`) | add `MultiSymbolWsClient` class | unit test with replay of 7-pair trace |
| P1-02 | Extend `src/data_backbone/` book cache to per-pair dict keyed by `Symbol` enum | ripple through `OrderbookSnapshot.pair_id` | existing snapshot tests pass per pair |
| P1-03 | **DELIVERED IN CODE** — `interface_contracts/pair_catalog.py` already exists; keep here only as audit trace, not active backlog | verify existing file + contract tests | no active action unless regression appears |
| P1-04 | Extend `BinanceOrderRequest` and `build_binance_client_order_id` to carry `pair_id` in UUIDv5 namespace (already partially done) | `order_translator.py` | test 7 pairs produce distinct deterministic IDs |
| P1-05 | Per-pair manifest entries in `manifest_registry`: `runtime_surface` lists 7 symbols, DAG unchanged | `manifest_registry/runtime_surface.py` | test_manifest_registry green |
| P1-06 | Per-pair rate-limiter accounting (one token bucket shared across pairs; Binance limits are account-wide not per-symbol) | tie to P0-07 | integration test: 7-pair simultaneous order bursts respect 50 orders / 10s |

| P1-07 | **(addendum doc 20)** `RefusalRecord` + `RefusalJournal` (anti-survivorship-bias logger, Taleb §4.3) | `src/interface_contracts/refusal_records.py` + `src/meta_minimal/refusal_journal/` | unit: every refusal category writes valid frozen record; journal rejects mutation |

**Gate to Phase 2**: 48-hour local replay with 7-pair WS trace completes with zero stream disconnects, zero manifest mismatches, **and** every no-trade/no-fill/phantom is observed in `RefusalJournal`.

### Phase 2 — Microstructure feature pack (weeks 3–4)
**Goal**: add L2-derived features as LAB-side discovery, shadow-deployable.

| ID | Task | Files | Test gate |
|---|---|---|---|
| P2-01 | New package `src/data_backbone/microstructure/`: `order_flow_imbalance.py` (Cont-Kukanov OFI), `vpin.py` (Easley-Lopez-O'Hara 2012), `queue_pressure.py`, `spread_dynamics.py`, `realized_vol.py` (Andersen-Bollerslev) | new files | each file: unit tests with synthetic book + published-paper check values |
| P2-02 | Add `MicrostructureFeatureVector` frozen Pydantic model to `interface_contracts/` | new file | contract test |
| P2-03 | Wire features into `calibration_methods/feature_store.py` (LAB-only output); add SHAP importance computation using `shap` lib | new file | test that SHAP returns vector matching feature count |
| P2-04 | Feature promotion state machine in `complete_enablers/feature_promotion.py`: enum `DISCOVERED → VALIDATED → CANDIDATE_VPS → SHADOW_VPS → LIVE_VPS`; Pydantic record per feature | new file | unit tests for each transition + illegal transition rejection |
| P2-05 | Gate: feature moves from VALIDATED→CANDIDATE only if replay-vs-live correlation ≥ 0.95 on 7-day window | calibration job | test with synthetic drift |

| P2-06 | **(addendum doc 20)** Enriched `SignalCandidate` contract per Narang §3.1 — additive backward-compatible migration seam, not a one-shot replacement; engines A/B migrated via adapters first | `src/interface_contracts/forecast_contracts.py` + engine adapters | every existing engine test green; new contract tests ≥ 20 |
| P2-07 | **(addendum doc 20)** `forecast_normalizer.py` Carver `F ∝ E[r]/σ`, `ForecastScalar = 10/E[\|F\|]` learned offline per engine | `src/scoring_backbone/forecast_normalizer.py` + calibration seam | unit: `E[\|F_normalised\|] ≈ 10` after scaling |
| P2-08 | **(addendum doc 20)** `break_even_filter.py` gates emission on `EV^net > THR-W01_floor` (Carver §7) | `src/scoring_backbone/break_even_filter.py` + calibration | unit: cost ≥ gain → no emit |
| P2-09 | **(addendum doc 20)** `cost_drift_monitor` ex-ante vs ex-post; alert if bias > THR-D01 | `src/meta_minimal/cost_drift_monitor/` | unit: 30%-bias synthetic stream → alert fires |
| **P2-09.5** | **(delivered 2026-04-16 from doc 27 / dispute D-2026-04-16-004)** `multiple_testing_guard.py` now provides the explicit Harvey-Liu-Zhu deflation seam with declared V5.3 pair-count composition: `k_HLZ = pairs_tested` in observed mode, `k_HLZ = max(pairs_tested, 20)` in promotion-floor mode. | `src/calibration_methods/multiple_testing_guard.py` | unit: `SR_deflated` parity against HLZ eq.(8) + explicit `k_HLZ` composition regression |
| **P3-10.5** | **(opened by doc 27 / dispute D-2026-04-16-002)** `closed_episode_journal.py` with frozen append-only `EpisodeRef` / `ClosedEpisodeJournal` contracts for Engine D historical linkage and replay/backtest evidence. Must stay under `src/protocols/`, not `src/meta_engine/`. | `src/protocols/closed_episode_journal.py` | unit: append-only invariant + stop-out filtering + most-recent eligible episode resolution + deterministic persistence hash |
| **P2-10** | **(addendum doc 20)** S1 VPIN-fade as **B sub-signal** (not new engine): `toxic_flow_fade` feature feeding `engine_b.excess_detector_b`; ruled out if intra-B correlation > THR-F01 (default 0.7) | `src/engines/engine_b/sub_signals/toxic_flow_fade.py` + feature seam | unit: high-VPIN + extreme price dislocation → B emits with `reason_codes=("b.toxic_flow_fade",)`; corr > 0.7 → feature suppressed |

**Gate to Phase 3**: 20+ microstructure features computed locally, SHAP ranking stable across 3 retrains, top-10 features promoted to CANDIDATE, **and** all `SignalCandidate` instances satisfy enriched contract.

### Phase 3 — ML enabler as Build-14 addendum (weeks 5–7)
**Goal**: LightGBM model as scoring-backbone **soft penalty** (not new engine).

| ID | Task | Files | Test gate |
|---|---|---|---|
| P3-01 | New `src/complete_enablers/ml_confidence_enabler.py` implementing `ScoringSoftPenaltyLayerHook` protocol. Output: `ml_confidence ∈ [0,1]` + `ml_direction ∈ {long, short, flat}` per (pair, timestamp) | new file | contract test: hook protocol satisfied |
| P3-02 | LightGBM training driver `src/calibration_methods/ml_trainer.py` (LAB_ONLY): walk-forward 180d train / 30d test, 5-fold bagging, Optuna ≤100 trials, `early_stopping=50`, `max_depth=6` | new file | reproducibility test: fixed seed → identical model hash |
| P3-03 | Model artefact contract: frozen Pydantic `MlModelArtifact` with `feature_hash`, `pair_universe`, `train_window`, `oos_sharpe`, `backtest_sharpe`, `promotion_state`. Persisted via `backtest_artifact_import` transport | new contract | artefact round-trip test |
| P3-04 | Promotion gate `src/complete_enablers/ml_model_promotion_gate.py`: require `oos_sharpe ≥ 0.80 × backtest_sharpe` AND `ks_test_features pvalue > 0.05` AND `shadow_diff_pct < 0.1%` | new file | unit tests + integration with shadow runtime |
| P3-05 | Score fusion: engines A/B/C/D output `score_abcd`; ML enabler outputs `ml_score`; fused score = `score_abcd × (1 + α × (ml_confidence − 0.5))` with α ∈ [0, 0.3] **calibrated** not hardcoded (new threshold ID `THR-M01`, hard cap α ≤ 0.5). Add calibration seam following pattern of `risk_runtime_drawdown_calibration.py` | `scoring_backbone/ml_fusion.py` + calibration file | tests: α=0 → score_abcd unchanged; α=0.3, ml=1.0 → +15% boost; α=0.3, ml=0.0 → −15% |
| P3-06 | Per-pair conviction adjustment: ml_confidence feeds `engine_a.conviction_stage` and `engine_b.conviction_layer` as **side input**, not overrider | adapter file | integration test: engine decision unchanged if ml_confidence=0.5 |
| P3-07 | Weekly retrain cron hook (LAB-side; VPS consumes artefact only) | `scripts/lab_weekly_retrain.py` | dry-run test |

| P3-08 | **(addendum doc 20)** `model_risk_registry`: track `train_window`, `oos_sharpe`, `feature_hash`, replay→shadow→live drift | `src/meta_learning/model_risk_registry/` | drift simulator → registry blocks promotion |
| P3-09 | **(addendum doc 20)** `strategy_drift_monitor` per-engine forecast/WR/CE drift; emit `RefusalRecord` on halt | `src/meta_learning/strategy_drift_monitor/` | synthetic drift → engine paused, refusal logged |
| **P3-10** | **(addendum doc 20 §11)** `engine_coordination_rules.py` — Narang-grade **mutual exclusion (A↔C)** + **historical linkage (D requires prior A/C episode)** conditioning layer. **NOT** Carver FDM family. Emits HARD_BLOCK `ConditioningRecord` when violated. | `src/protocols/engine_coordination_rules.py` + typed contracts in `src/interface_contracts/` | unit: A long BTC → C long BTC emission blocked for THR-X08 (2h); D without `first_episode_ref` → HARD_BLOCK; D after 2 consecutive stops → blocked until fresh A detection (strategy β) |
| **P3-11** | **(addendum doc 20)** S2 residualized cross-pair momentum as **Build-14 feature** (not engine trigger): feeds `ml_confidence_enabler` input vector; cross-sectional z-score with BTC/ETH factor residualization; **forbidden** as C or D emission trigger (different `bet_structure`). | `src/data_backbone/cross_sectional/residualized_momentum.py` | unit: pure BTC beta → feature ≈ 0; idiosyncratic alt move → feature > threshold |

**Hard rule (Carver+Narang)**: ML enabler **cannot** override A/B/C/D output or set side. Modulation only via THR-M01 with `α ≤ 0.5`.

**Gate to Phase 4**: 2-week shadow run with ML enabler active; fused score produces ≥ 5% uplift in shadow PnL vs baseline engines-only, zero contract violations, zero DAG violations, **and** quadruple filter (doc 20 §4.2) green.

### Phase 4 — Vol-targeting sizing + Regime-Change Detector (week 8)

| ID | Task | Files | Test gate |
|---|---|---|---|
| P4-01 | **REVISED per addendum doc 20** — Carver-canonical sizing chain: `instrument_value_vol = price × pct_vol × point_value`; `vol_scalar = capital × annual_target / sqrt(252) / instrument_value_vol`; `N = (forecast_normalised / 10) × vol_scalar` then clip with CE / cluster / BTC / cap filters. Requires P2-07 normalised forecast. THR-S07 (hard cap 2%). | `src/portfolio_minimal/allocation_router/vol_target_sizer.py` + calibration | tests: F=10, vol=1% → full position; F=5, vol=2% → quarter position; clip to caps |
| P4-02 | New risk layer `src/risk_backbone/regime_change_detector/`: halts trading if `realized_vol_5min ≥ 3 × realized_vol_60min_trailing`. Threshold `THR-R04` (hard cap 5×) | new package | tests: 2× → allow, 3× → halt, 5× → halt |
| P4-03 | Wire regime-change into `risk_runtime.py` gate chain **before** execution dispatch | runtime file | integration test: simulated vol spike → all 7 pairs halted |
| P4-04 | Cross-pair correlation filter at 0.85 (not 0.70) using residualized rolling corr (regress out BTC) | `risk_backbone/correlation_cluster_guard/` (extend existing) | test: 3 pairs with raw corr 0.9 but residual 0.3 → all allowed |

| P4-05 | **(addendum doc 20)** `tail_risk_meter` rolling 500-event 5%-tail loss; halt engine if `tail_loss_5pct > THR-T01 × median_loss` | `src/risk_backbone/tail_risk_meter/` + calibration | unit: heavy-tailed synthetic stream → halt fires |
| P4-06 | **(addendum doc 20)** `crowding_suspicion_monitor` alert if engine A & B trade overlap > THR-C01 over rolling 100 trades | `src/meta_learning/crowding_suspicion_monitor/` | unit: overlapping streams → alert |
| P4-07 | **(addendum doc 20)** `regime_shift_watcher` 3 vol buckets, CE-stability check feeding P4-02 | `src/risk_backbone/regime_shift_watcher/` | unit: regime swap → bucket transition reported |

**Gate to Phase 5**: 4-week shadow with new sizing + regime detector + tail-risk meter; max drawdown < 5%, zero post-halt trades, **and** no engine flagged by crowding monitor.

### Phase 5 — Hybrid execution (week 9)

| ID | Task | Files | Test gate |
|---|---|---|---|
| P5-01 | Hybrid maker-first, taker-fallback router: post limit at mid+offset; if unfilled after `THR-X06` (hard cap 60s) and `ml_confidence ≥ 0.7`, market-taker. Calibration file mirrors pattern. | `execution_backbone/order_decider/hybrid_router.py` | tests: filled-before-timeout → maker path; stale + high confidence → taker path |
| P5-02 | TWAP decomposer for orders > 25% of top-of-book: split into 3 slices over `THR-X07` seconds (hard cap 300s) | `execution_backbone/twap_decomposer.py` | test: $500 order, thin book → 3 slices ~$167 each |

| P5-03 | **(addendum doc 20)** `PortfolioArbitrationRecord` per Narang §3.4 — every promoted intent answers the 5 portfolio questions; refused candidates get `PORTFOLIO_REJECTED` `RefusalRecord` | `src/portfolio_minimal/arbitration_record.py` + extend `src/portfolio_minimal/portfolio_orchestrator.py` / `allocation_router` | unit: 5-candidate batch → 1 promoted with full record, 4 refused with codes |

**Gate to Phase 6**: Shadow fill rate ≥ 85%, realized slippage ≤ 4 bps, **and** every promoted intent carries a complete `PortfolioArbitrationRecord`.

### Phase 6 — Capital gradation + Live ramp (weeks 10–12)

Operator action, gated by shadow metrics. **REVISED ladder (doc 20 §12 capital reality)** — real start = €300–€400 on 3 pairs; $4K = ceiling headroom:

| Tier | Capital | Pairs live | Hold duration | Engine gates (min shadow record) |
|---|---|---|---|---|
| T1 | €300–€400 | 3 (BTC, ETH, SOL) | 3 weeks | A only live; B/C/D shadow-only. Sharpe ≥ 0.5, max DD ≤ 3% |
| T2 | €800 | 5 (+XRP, LINK) | 3 weeks | A+B live. Sharpe ≥ 0.8, 50 trades min, WR ≥ 50% |
| T3 | €1,500 | 7 (+BNB, ADA) | 4 weeks | A+B+C live (C requires doc 21 spec green). Sharpe ≥ 1.0, WR ≥ 52% |
| T4 | €2,500 | 10–12 | 4 weeks | A+B+C+D live (D requires doc 22 spec + β reset rule green). Sharpe ≥ 1.2, WR ≥ 53% |
| T5 | $4K (ceiling) | up to 16 | ongoing | Quarterly review. Shadow universe ≥ 20 always (doc 20 §12). |

Each tier transition goes through existing `shadow_gate_check` (W-15) + new `capital_ramp_gate.py` (Phase 6 task) + **mandatory quadruple filter from doc 20 §4.2** (real cost ✔ + queue risk ✔ + parity local/shadow/live ✔ + cross-regime robustness ✔) + **engine_coordination_rules audit** (doc 20 §11: no A↔C overlap violations, no D without historical linkage, no D past consecutive-stop threshold). **Operator cannot override the quadruple filter.**

---

## 3. What Sonnet must NOT do

1. Do **not** rename/remove engines A/B/C/D or their tests.
2. Do **not** hardcode thresholds — every new numeric constant goes through a calibration seam (pattern: `src/risk_backbone/risk_runtime_drawdown_calibration.py`).
3. Do **not** switch venues. All work stays on `binance_spot`.
4. Do **not** bypass LIGHT/COMPLETE profile separation; new modules must be classified (LAB_ONLY / VPS_ONLY / SHARED / TRANSPORT).
5. Do **not** introduce circular imports; run `rtk python -m dag_validator` after each phase.
6. Do **not** add Python deps without updating `pyproject.toml` AND `09_1.9_dependances_externes.md` reconciliation. New deps expected: `lightgbm`, `shap`, `optuna`.
7. Do **not** commit model binaries to git; artefacts go through `backtest_artifact_import` with hash-pinned references.
8. Do **not** skip RTK on shell-inspection commands.
9. Do **not** emit a `SignalCandidate` without `forecast_horizon_class`, `bet_structure`, `expected_cost`, `expected_ce`, `reason_codes` (Narang §3.1 — see doc 20).
10. Do **not** let the ML enabler set side or override engine emission (Carver+Narang).
11. Do **not** promote any feature/model/engine without the four quadruple-filter checks green (Taleb §4.2).
12. Do **not** use Kelly-full sizing or Kelly fraction > 0.5 (Carver §4.3).
13. Do **not** skip `RefusalRecord` writing on any rejected candidate, no-fill, phantom, or version invalidation (Taleb §3.3).
14. Do **not** tune any threshold purely on backtest PnL improvement (Taleb + Carver anti-overfitting).
15. Do **not** implement Forecast/Instrument Diversification Multiplier or full portfolio variance optimisation in Light (Carver: those are Complete-only).
16. Do **not** emit from Engine C while Engine A holds an open position on the same (pair, direction) within THR-X08 (doc 20 §11 mutual exclusion; 2h default, 12h hard cap). HARD_BLOCK, not soft penalty.
17. Do **not** emit from Engine D without a valid `first_episode_ref` (reference to a prior A or C completed episode on the same (pair, direction); doc 20 §11 historical linkage). D is *never* a primary entry.
18. Do **not** emit more than THR-X11 consecutive D re-entries per (pair, direction) (default 1, hard cap 3). After one consecutive stop, D is blocked on that (pair, direction) until a **fresh A detection** resets the structural context (strategy β). Failsafe: THR-X10 parametric cooldown (24h default) applies if no A detection arrives within 72h.
19. Do **not** use any 1990s TA indicator (RSI, MACD, Stochastic, Bollinger Bands, Williams %R, CCI, DMI/ADX, parabolic SAR) as an emission **trigger**, `forecast_direction`, or `forecast_strength` input for engines A/B/C/D. Documentary ref: doc 23 §6 — formal prohibition. They may appear only as informational overlay in the Complete UI.
20. Do **not** treat S2 (residualized cross-pair momentum) as an engine trigger — it is a **Build-14 feature** feeding `ml_confidence_enabler` (different `bet_structure`; doc 20 §13 rationale).
21. Do **not** add S1 (VPIN toxic-flow fade) as a new engine — it is a **B sub-signal** (mean-reversion family, contrarian bet on toxicity dislocation); doc 19 P2-10.

---

## 4. Threshold IDs introduced

| ID | Meaning | Hard cap | Default |
|---|---|---|---|
| THR-M01 | ML fusion coefficient α | ≤ 0.5 | 0.15 |
| THR-S07 | Vol target per trade | ≤ 2% | 1% |
| THR-R04 | Regime-change vol spike multiplier | ≤ 5× | 3× |
| THR-X06 | Maker-to-taker timeout | ≤ 60s | 20s |
| THR-X07 | TWAP total duration | ≤ 300s | 120s |
| **THR-W01** | Min `EV^net` floor for SignalCandidate emission (doc 20) | 0.0 (cannot disable) | $0.05/event |
| **THR-T01** | Tail-loss multiplier vs median triggering engine halt (doc 20) | ≤ 5× | 3× |
| **THR-D01** | Cost-drift bias % triggering alert (doc 20) | ≤ 50% | 20% |
| **THR-D02** | Strategy drift KS p-value triggering pause (doc 20) | ≥ 0.001 | 0.01 |
| **THR-C01** | Engine-overlap % triggering crowding alert (doc 20) | ≤ 90% | 70% |
| **THR-Q01** | Quadruple-filter parity tolerance (doc 20) | ≤ 25% | 10% |
| **THR-X08** | A↔C mutual-exclusion window same (pair, direction) (doc 20 §11) | ≤ 12h | 2h |
| **THR-X09** | A recent-fire suppression of C on same setup (doc 20 §11) | ≤ 24h | 4h |
| **THR-X10** | D anti-revenge parametric cooldown failsafe (doc 20 §11 + doc 22) | ≤ 48h | 24h |
| **THR-X11** | D max consecutive re-entries per (pair, direction) (doc 20 §11 + doc 22) | ≤ 3 | 1 |
| **THR-F01** | B sub-signal max intra-family correlation (doc 19 P2-10) | ≤ 0.9 | 0.7 |

Each gets a calibration file, unit tests, and an entry in `11_DYNAMIC_THRESHOLDS_CATALOG.md`.

---

## 5. Test matrix after completion

| Suite | Expected passing |
|---|---|
| `tests/test_data_backbone/microstructure/` | ≥ 40 new |
| `tests/test_complete_enablers/test_ml_confidence_enabler.py` | ≥ 15 |
| `tests/test_complete_enablers/test_ml_model_promotion_gate.py` | ≥ 10 |
| `tests/test_scoring_backbone/test_ml_fusion.py` | ≥ 12 |
| `tests/test_risk_backbone/test_regime_change_detector.py` | ≥ 10 |
| `tests/test_portfolio_minimal/test_vol_target_sizing.py` | ≥ 8 |
| `tests/test_execution_backbone/test_hybrid_router.py` | ≥ 12 |
| `tests/test_execution_backbone/test_twap_decomposer.py` | ≥ 8 |
| Existing suites | unchanged, all still green |

Final (doc 19 only): `rtk pytest tests/` → ~2990+ passing, 0 failing, 0 DAG violations.

**With doc 20 addendum applied** (≥ 125 additional tests across `forecast_contracts`, `refusal_records`, `model_risk_registry`, `forecast_normalizer`, `break_even_filter`, `tail_risk_meter`, `cost_drift_monitor`, `crowding_suspicion_monitor`, `regime_shift_watcher`, `arbitration_record`):
**`rtk pytest tests/` → ~3115+ passing.**

**With docs 21 / 22 / 23 applied** (Engine C spec, Engine D spec, microstructure dictionary):
- `tests/test_engines/test_engine_c/` ≥ 40 new (structure detector, continuation validator, A-exclusion guard, cost feasibility, invalidation, runtime)
- `tests/test_engines/test_engine_d/` ≥ 35 new (first_episode_ref resolver, historical linkage guard, anti-revenge cooldown, consecutive-stop counter, β reset rule)
- `tests/test_protocols/test_engine_coordination_rules/` ≥ 20 new
- `tests/test_data_backbone/microstructure/` ≥ 30 new (OFI, VPIN, Kyle λ, Amihud, Corwin-Schultz, realized kernel, Hawkes)

**Final target: `rtk pytest tests/` → ~3240+ passing.**

---

## 6. Rollback plan

Every phase produces an idempotent PR. Each PR:
- adds additive seams where possible; if touching canonical engines C/D, evolves existing files surgically rather than replacing them
- gates new logic behind a calibration flag that defaults to `disabled=True`
- ships with its own test suite

If any shadow metric regresses at a gate, the feature flag is flipped off and the previous phase is the stable state. No DB migrations, no data loss.

---

## 7. Execution order checklist for Sonnet

```
[ ] Phase 0 (week 1)       — baseline clean, 2888/2888 green
[ ] Phase 1 (weeks 2–3)    — 7-pair WS + catalogs
[ ] Phase 2 (weeks 3–4)    — microstructure features + SHAP
[ ] Phase 3 (weeks 5–7)    — LightGBM enabler + fusion
[ ] Phase 4 (week 8)       — vol-target sizing + regime detector
[ ] Phase 5 (week 9)       — hybrid execution + TWAP
[ ] Phase 6 (weeks 10–12)  — capital gradation + Live ramp
```

Each phase closes with: PR, updated audit doc (`18_CODE_VS_PLAN…`), test report, DAG validation, calibration catalog delta.

Each phase **must also** close with the doc 20 quadruple filter green where applicable (Phases 3+ onward).

---

**Status**: PLAN RECONCILED AGAINST DOC 24 — execute against current code truth, not the older literal wording of every backlog row.
**Next immediate action**: Sonnet reads this doc + `20_CARVER_NARANG_TALEB_INTEGRATION.md` + `21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md` + `22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md` + `23_MICROSTRUCTURE_FEATURE_DICTIONARY.md` + `18_CODE_VS_PLAN…` and begins:

```
P0 remaining baseline items (with P0-07 already delivered) → P1-07 (RefusalJournal) → P2-06 (enriched SignalCandidate additive seam) → P2-07 (Carver normaliser) → P2-08 (break-even filter) → P2-09 (cost drift) → P2-10 (S1 VPIN fade as B sub-signal) → P3-10 (engine_coordination_rules) → P3-11 (S2 residualized momentum as Build-14 feature) → Engine C doctrinal deepening (doc 21) gated by P3-10 green → Engine D doctrinal deepening (doc 22) gated by Engine C live on shadow ≥ 4 weeks.
```

Engine C doctrinal deepening cannot land before `engine_coordination_rules` is green (A↔C exclusion must exist before C is deepened). Engine D doctrinal deepening cannot land before Engine C is running live in shadow long enough to produce valid `first_episode_ref` history (min 4 weeks). This ordering is a **hard constraint**, not a suggestion.
