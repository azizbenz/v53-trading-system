# 05_MODERNIZATION_AND_DOC20_TARGET

## Included Source Docs
- docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md
- docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md
- docs/production_deployment_plan/29_SPRINT_FINAL_CODEX_BEFORE_MONDAY.md
- docs/production_deployment_plan/30_PROMOTION_CALIBRATION_REGISTER.md

---

## Source: docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md

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
| **P3-10.5** | **(opened by doc 27 / dispute D-2026-04-16-002)** `closed_episode_journal.py` with frozen append-only `EpisodeRef` / `ClosedEpisodeJournal` contracts for Engine D historical linkage and replay/backtest evidence. Must stay under `src/protocols/` (protocol-layer artifact, not a meta-engine surface). | `src/protocols/closed_episode_journal.py` | unit: append-only invariant + stop-out filtering + most-recent eligible episode resolution + deterministic persistence hash |
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


---

## Source: docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md

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

Current code truth: the canonical runtime contract still lives in `src/interface_contracts/decision_contracts.py`, and engines A/B/C/D build it directly. Therefore the Narang-grade contract must land additively first (`forecast_contracts.py` + adapters), then migrate progressively. The integration is a backward-compatible extension: optional fields are added first, then per-engine migration proceeds on a staged schedule — it is **not** a one-shot contract swap.

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

Every engine emission carries in `conditioning_state` the evaluation trace. Blocked paths append a HARD_BLOCK `ConditioningRecord` and a `RefusalRecord(category=HARD_BLOCK, reason_codes=(…,))` to `RefusalJournal`. Blocked paths do **not** emit a canonical `SignalCandidate`; this avoids inventing a fake neutral/no-direction side that does not exist in the runtime `Side` enum (which admits only LONG and SHORT).

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


---

## Source: docs/production_deployment_plan/29_SPRINT_FINAL_CODEX_BEFORE_MONDAY.md

# 29 — Sprint final Codex : fermer les 3% restants avant lundi

**Date** : 2026-04-16
**Auteur** : Opus
**Destinataire** : Codex
**Deadline** : dimanche 2026-04-20 23h59 UTC
**Gouvernance** : doc 28 (arbitration) + doc 25 (audit protocol) + doc 26 (template)
**Règle prioritaire** : **R-QUANT-FIRST** (doc 28 §2bis) — formule complète avant code

---

## 0. État actuel — ce qui est FAIT vs ce qui RESTE

### FAIT (97%)

| ID | Livrable | Statut | Preuve |
|---|---|---|---|
| P0-1 | `revenge_risk_penalty` → user option C (observability, pas de continuous penalty) | ✅ COMPLETE | Engine D anti-revenge fields in validation rail |
| P0-2 | `ClosedEpisodeJournal` + `EpisodeRef` contracts | ✅ COMPLETE | `src/protocols/closed_episode_journal.py`, 26 tests passed |
| P0-3 | Helpers REQUIRED/OPTIONAL tranchés | ✅ COMPLETE | docs 21/22 §2 mis à jour |
| P0-4 | `k_HLZ` explicite + `multiple_testing_guard.py` | ✅ COMPLETE | module blob `b2aafc74…`, 8 tests passed |
| Doc 21 | Engine C spec — doctrinal deepening | ✅ SPEC | Cohérent avec doc 20 §11, doc 24 |
| Doc 22 | Engine D spec — doctrinal deepening | ✅ SPEC | Strategy β, R-D rules, sizing R-D-4 |
| Doc 23 | Microstructure Feature Dictionary | ✅ SPEC | Features + prohibitions + HLZ |
| Doc 27 | Opus→Codex audit brief | ✅ rev-3 | 4 disputes résolues, journal clean |
| Doc 28 | Arbitration protocol | ✅ RULE | 4 rangs, R-QUANT-FIRST, registre |

### RESTE (3%) — 9 tâches ordonnées

| # | Tâche | Priorité | Effort estimé | Dépendances |
|---|---|---|---|---|
| T1 | P0-5a : Annexe A formules quant — doc 21 | **P0 BLOQUANT** | 45 min | Aucune |
| T2 | P0-5b : Annexe A formules quant — doc 22 | **P0 BLOQUANT** | 15 min | T1 (copie + adaptations D-spécifiques) |
| T3 | P0-5c : 4 tests `paper_repro` | **P0 BLOQUANT** | 60 min | T1, T2 |
| T4 | P1-7 : Table "D-sur-A vs D-sur-C" | P1 | 20 min | T2 |
| T5 | P1-8 : Colonne `calibration_module` dans tables §5/§6 | P1 | 10 min | T1, T2 |
| T6 | P1-9 : Version-pin doc 23 | P1 | 5 min | Aucune |
| T7 | P1-10 : Source VPIN threshold crypto | P1 | 15 min | Aucune |
| T8 | §5 : 4 corrections docs 19/20 | P1 | 30 min | Aucune |
| T9 | Verification pass final + guardrails | **GATE** | 20 min | Tout |

**Total estimé** : ~3h30 de travail concentré.

---

## 1. T1 — P0-5a : Annexe A formules quant — doc 21

### Quoi faire

Ajouter à `21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md` une section **§Annexe A — Formules microstructure : spécification complète** contenant les 4 formules ci-dessous. Chaque formule est `CONSTRAINT_DOCTRINAL` (rang 1).

### Formule 1 : Realized Kernel Volatility

```
σ_RK = Σ_{h=-H}^{H} k(h/H) · γ(h)

Définitions :
  γ(h) = Σ_j r_j · r_{j+h}              # autocovariance réalisée d'ordre h
  r_j  = log(P_j) - log(P_{j-1})         # log-return sur bucket
  k(x) = Parzen kernel :
         k(x) = 1 - 6x² + 6|x|³         si |x| ≤ 0.5
         k(x) = 2(1 - |x|)³             si 0.5 < |x| ≤ 1
         k(x) = 0                         sinon
  H    = ⌈c · n^(3/5)⌉                   # bandwidth optimale
  c    = THR-C_RK_BANDWIDTH_C            # default 0.4, cap 1.0
  n    = nombre de buckets dans la fenêtre d'estimation
  bucket_size = THR-C_RK_BUCKET_SIZE     # default 5 min, cap 15 min

Source : Barndorff-Nielsen, Hansen, Lunde, Shephard (2008)
         "Designing Realized Kernels to Measure the Ex-Post Variation
          of Equity Prices in the Presence of Noise"
         Econometrica, Vol. 76, No. 6, eq.(3.1)–(3.7)
         DOI: 10.3982/ECTA6495
```

**Comment vérifier** :
1. Ouvrir le paper (DOI ci-dessus), aller à eq.(3.1) et (3.7)
2. Confirmer que le kernel Parzen correspond exactement à eq.(3.5) du paper
3. Confirmer que la règle de bandwidth `H = c · n^(3/5)` correspond à Theorem 2 du paper
4. Si Codex ne peut pas accéder au paper → ouvrir Dispute `D-2026-04-17-001`, ne pas inventer

### Formule 2 : Order Flow Imbalance (OFI)

```
OFI_t = Σ_{i=t-N+1}^{t} Δe_i

où l'event contribution à chaque update i du LOB est :
  Δe_i = ΔQ^b_i · 𝟙(P^b_i ≥ P^b_{i-1}) − ΔQ^a_i · 𝟙(P^a_i ≤ P^a_{i-1})

Définitions :
  P^b_i  = meilleur bid prix à l'event i
  P^a_i  = meilleur ask prix à l'event i
  ΔQ^b_i = Q^b_i − Q^b_{i-1}  (changement de quantité au meilleur bid)
  ΔQ^a_i = Q^a_i − Q^a_{i-1}  (changement de quantité au meilleur ask)
  𝟙()    = indicatrice
  N      = THR-C_OFI_WINDOW    # default 500 events, cap 2000

Interprétation :
  OFI > 0  → pression acheteuse nette (bid queue croît / ask queue décroît)
  OFI < 0  → pression vendeuse nette
  OFI ≈ 0  → équilibre

Source : Cont, Kukanov, Stoikov (2014)
         "The Price Impact of Order Book Events"
         Journal of Financial Econometrics, Vol. 12, No. 1, eq.(1)–(3)
         DOI: 10.1016/j.finmar.2013.06.001
```

**Comment vérifier** :
1. Paper eq.(1) : vérifier que `Δe_i` correspond exactement (attention au signe des termes ask)
2. Paper §3 Proposition 1 : confirmer que OFI prédit la direction du price change
3. Si ambiguïté sur les indicatrices (certaines versions simplifient) → utiliser la version complète eq.(3)

### Formule 3 : Kyle Lambda (λ)

```
Modèle de régression :
  ΔP_t = λ · SignedVolume_t + ε_t

Définitions :
  ΔP_t          = P_t − P_{t-1}  (changement de prix mid)
  SignedVolume_t = Σ_k volume_k · sign(direction_k)
                   sur tous les trades du bucket t
  direction_k   = +1 (buy) ou −1 (sell), classifié par :
                   - Lee-Ready rule (comparaison au mid) si L2 disponible
                   - Tick rule (comparaison au trade précédent) sinon
  λ              = coefficient OLS (price impact par unité de volume signé)
  fenêtre        = THR-C_KYLE_WINDOW  # default 1h rolling, cap 4h
  bucket         = 1 min (agrégation des trades avant régression)

Propriétés attendues :
  λ > 0 toujours (prix monte quand buy pressure, baisse quand sell pressure)
  λ élevé → marché illiquide (fort impact par unité de volume)
  λ faible → marché liquide

Source : Kyle (1985)
         "Continuous Auctions and Insider Trading"
         Econometrica, Vol. 53, No. 6, eq.(1)
         DOI: 10.2307/1913210
```

**Comment vérifier** :
1. Kyle 1985 est un modèle théorique ; l'estimation OLS est standard (Hasbrouck 1991 pour la version empirique)
2. Vérifier que `λ > 0` sur toute donnée réelle (sinon bug d'implémentation ou de classification trade direction)
3. Si classification Lee-Ready non disponible sur Binance (pas de quote data synchrone) → utiliser tick rule et documenter

### Formule 4 : VPIN

```
VPIN = (1/n) · Σ_{τ=1}^{n} |V^S_τ − V^B_τ| / V_bucket

Définitions :
  V_bucket = DailyVolume / THR-C_VPIN_BUCKETS  # default 50 buckets/jour, cap 100
  τ        = index du volume bucket (chaque bucket contient exactement V_bucket de volume total)
  V^B_τ    = volume classifié "buy" dans le bucket τ
  V^S_τ    = volume classifié "sell" dans le bucket τ
  n        = THR-C_VPIN_N_BUCKETS_WINDOW  # default 50 buckets, rolling

Classification Bulk Volume (BVC) — méthode Easley-López :
  Pour chaque trade de volume v au prix P :
    V^B = v · Φ((P − P̄) / σ_ΔP)
    V^S = v · (1 − Φ((P − P̄) / σ_ΔP))
  où :
    Φ()    = CDF normale standard
    P̄      = prix moyen du bucket courant
    σ_ΔP   = écart-type des changements de prix dans le bucket

Domaine :
  VPIN ∈ [0, 1]
  VPIN → 0 : flux équilibré (non toxique)
  VPIN → 1 : flux 100% unilatéral (toxique)
  Seuil toxic : THR-C_VPIN_MAX  # default 0.35, cap 0.5, TBD_shadow_calibration pour crypto

Source : Easley, López de Prado, O'Hara (2012)
         "Flow Toxicity and Liquidity in a High-Frequency World"
         Review of Financial Studies, Vol. 25, No. 5, eq.(2)–(4)
         DOI: 10.1093/rfs/hhs053
```

**Comment vérifier** :
1. Paper eq.(2) : bucket par volume, pas par temps — c'est la distinction clé
2. Paper eq.(3) : BVC classification — vérifier que Φ est bien la CDF normale
3. Boundary test : si tous les trades sont du même côté → VPIN = 1.0 exactement
4. Le default `THR-C_VPIN_MAX = 0.35` est plus conservateur que 0.5 ; ce choix vient de Abad-Yagüe 2012 sur equities, **pas** d'une étude crypto → marquer `TBD_shadow_calibration`

### Nouveaux thresholds à ajouter dans doc 21 §5

| ID | Meaning | Default | Hard cap | Module | Calibration seam |
|---|---|---|---|---|---|
| THR-C_RK_BANDWIDTH_C | Realized kernel bandwidth constant c | 0.4 | 1.0 | `structure_detector_c` | `risk_runtime_drawdown_calibration.py` |
| THR-C_RK_BUCKET_SIZE | Realized kernel bucket duration | 5 min | 15 min | `structure_detector_c` | `risk_runtime_drawdown_calibration.py` |
| THR-C_OFI_WINDOW | OFI cumulation window (L2 events) | 500 | 2000 | `continuation_validator_c` | `risk_runtime_drawdown_calibration.py` |
| THR-C_KYLE_WINDOW | Kyle λ OLS regression window | 1h | 4h | `continuation_validator_c` | `risk_runtime_drawdown_calibration.py` |
| THR-C_VPIN_BUCKETS | VPIN volume-bucket count per day | 50 | 100 | `continuation_validator_c` | `risk_runtime_drawdown_calibration.py` |
| THR-C_VPIN_N_BUCKETS_WINDOW | VPIN rolling window (# buckets) | 50 | 200 | `continuation_validator_c` | `risk_runtime_drawdown_calibration.py` |

### Acceptance criteria T1

- [ ] §Annexe A existe dans doc 21
- [ ] 4 formules complètes avec toutes les variables définies
- [ ] 4 DOI + eq. numbers cités
- [ ] 6 nouveaux THR-C_* dans table §5 avec default + cap + calibration_module
- [ ] Aucune variable laissée indéfinie (grep "calibrated" sans valeur → 0 match)
- [ ] Chaque formule a un bloc "Comment vérifier"

---

## 2. T2 — P0-5b : Annexe A formules quant — doc 22

### Quoi faire

Ajouter à `22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md` une section **§Annexe A — Formules microstructure : précisions D-spécifiques** :

```markdown
## Annexe A — Formules microstructure : précisions D-spécifiques

Engine D utilise les mêmes formules microstructure que C (voir doc 21 Annexe A
pour les équations complètes). Les différences D-spécifiques sont :

### Realized kernel volatility
**Recalculé** sur la fenêtre courante (post first_episode_ref.closed_at).
Raison : le contexte de vol a changé entre l'épisode original et le re-entry.
Ne PAS hériter σ_RK du first_episode_ref.

### OFI
**Recalculé** sur la fenêtre [first_episode_ref.closed_at, now].
Vérifie la persistance du flow dans la direction du re-entry APRÈS
la fermeture de l'épisode original.
THR-D_OFI_WINDOW = THR-C_OFI_WINDOW (default 500, même seam).

### Kyle λ
**Recalculé** sur la fenêtre courante.
Si λ_current > 2 × λ_at_first_episode → marché devenu plus illiquide
→ facteur de pénalisation sur le score de conviction.

### VPIN
**Recalculé** sur la fenêtre courante.
Si VPIN_current > THR-C_VPIN_MAX → skip (même règle que C).
```

### Acceptance criteria T2

- [ ] §Annexe A existe dans doc 22
- [ ] Chaque formule dit explicitement "recalculé" (pas "hérité") avec justification
- [ ] Pas de duplication des équations complètes (renvoi à doc 21 Annexe A)
- [ ] La pénalisation Kyle λ pour D est documentée (2× threshold)

---

## 3. T3 — P0-5c : 4 tests paper_repro

### Quoi faire

Créer 4 fichiers de test (ou un seul regroupé `tests/test_microstructure/test_paper_repro.py`) :

### Test 1 : `test_realized_kernel_parzen`

```python
"""Reproduce Barndorff-Nielsen 2008 Parzen kernel shape properties.
Source: DOI 10.3982/ECTA6495, eq.(3.5)
"""
def test_parzen_kernel_at_zero_is_one():
    """k(0) = 1 (centre du kernel)"""
    assert parzen_kernel(0.0) == 1.0

def test_parzen_kernel_at_boundary_is_zero():
    """k(±1) = 0 (bords du kernel)"""
    assert parzen_kernel(1.0) == 0.0
    assert parzen_kernel(-1.0) == 0.0

def test_parzen_kernel_symmetry():
    """k(x) = k(-x) pour tout x"""
    for x in [0.1, 0.25, 0.5, 0.75, 0.99]:
        assert parzen_kernel(x) == parzen_kernel(-x)

def test_parzen_kernel_nonnegative():
    """k(x) ≥ 0 pour tout x ∈ [-1, 1]"""
    for x in [i/100 for i in range(-100, 101)]:
        assert parzen_kernel(x) >= 0.0

def test_bandwidth_scaling():
    """H = ⌈c · n^(3/5)⌉ avec c=0.4, n=1000 → H = ⌈0.4 × 63.1⌉ = 26"""
    import math
    c, n = 0.4, 1000
    H = math.ceil(c * n ** 0.6)
    assert H == 26  # valeur de référence hardcodée
```

### Test 2 : `test_ofi_direction`

```python
"""Reproduce Cont-Kukanov 2014 §3 Proposition 1: OFI predicts price direction.
Source: DOI 10.1016/j.finmar.2013.06.001
"""
def test_ofi_positive_when_bid_grows_ask_shrinks():
    """Bid queue +100, ask queue -50 → OFI > 0"""
    events = [
        LOBEvent(bid_price=100.0, bid_qty=1000, ask_price=100.1, ask_qty=500),   # t=0
        LOBEvent(bid_price=100.0, bid_qty=1100, ask_price=100.1, ask_qty=450),   # t=1, bid+100 ask-50
    ]
    assert compute_ofi(events) > 0

def test_ofi_negative_when_ask_grows_bid_shrinks():
    """Bid queue -80, ask queue +120 → OFI < 0"""
    events = [
        LOBEvent(bid_price=100.0, bid_qty=1000, ask_price=100.1, ask_qty=500),
        LOBEvent(bid_price=100.0, bid_qty=920,  ask_price=100.1, ask_qty=620),
    ]
    assert compute_ofi(events) < 0

def test_ofi_zero_when_symmetric():
    """Bid +50, ask -50 puis bid -50, ask +50 → OFI ≈ 0"""
    events = [
        LOBEvent(bid_price=100.0, bid_qty=1000, ask_price=100.1, ask_qty=500),
        LOBEvent(bid_price=100.0, bid_qty=1050, ask_price=100.1, ask_qty=450),
        LOBEvent(bid_price=100.0, bid_qty=1000, ask_price=100.1, ask_qty=500),
    ]
    assert abs(compute_ofi(events)) < 1e-10
```

### Test 3 : `test_kyle_lambda_positive`

```python
"""Reproduce Kyle 1985 basic prediction: λ > 0.
Source: DOI 10.2307/1913210, eq.(1)
"""
def test_lambda_positive_with_informed_trader(seed=42):
    """Synthetic market: informed buyer drives price up → λ > 0"""
    import numpy as np
    rng = np.random.default_rng(seed)
    n = 500
    # informed: always buys → SignedVolume > 0 → price drifts up
    signed_volume = rng.exponential(100, n)
    noise = rng.normal(0, 0.5, n)
    true_lambda = 0.001
    delta_p = true_lambda * signed_volume + noise
    # OLS
    lambda_hat = np.cov(delta_p, signed_volume)[0,1] / np.var(signed_volume)
    assert lambda_hat > 0, f"λ should be positive, got {lambda_hat}"
    assert abs(lambda_hat - true_lambda) < 0.0005, f"λ should be ≈ {true_lambda}"
```

### Test 4 : `test_vpin_boundary`

```python
"""Reproduce Easley-López-O'Hara 2012 boundary case: 100% informed → VPIN=1.
Source: DOI 10.1093/rfs/hhs053
"""
def test_vpin_one_when_all_same_side():
    """All trades classified as buys → V^S=0 in every bucket → VPIN=1.0"""
    trades = [Trade(price=100.0 + i*0.01, volume=10, direction="buy") for i in range(1000)]
    daily_volume = sum(t.volume for t in trades)
    vpin = compute_vpin(trades, n_buckets_per_day=50, window=50, daily_volume=daily_volume)
    assert abs(vpin - 1.0) < 1e-6

def test_vpin_zero_when_perfectly_balanced():
    """Alternating buy/sell of equal volume → VPIN ≈ 0"""
    trades = []
    for i in range(1000):
        direction = "buy" if i % 2 == 0 else "sell"
        trades.append(Trade(price=100.0, volume=10, direction=direction))
    daily_volume = sum(t.volume for t in trades)
    vpin = compute_vpin(trades, n_buckets_per_day=50, window=50, daily_volume=daily_volume)
    assert vpin < 0.05  # not exactly 0 due to BVC approximation but close
```

### Acceptance criteria T3

- [ ] 4 fichiers de test (ou 1 regroupé) créés
- [ ] Chaque test cite DOI + eq/fig en docstring
- [ ] Chaque test utilise seed fixe pour reproductibilité
- [ ] `rtk pytest -q tests/test_microstructure/test_paper_repro.py` → all passed
- [ ] Aucun test n'importe un module microstructure qui n'existe pas encore — les tests vérifient les PROPRIÉTÉS MATHÉMATIQUES, pas l'intégration. Si le module n'existe pas encore, le test est écrit avec des fonctions helper locales (et un TODO pour wirer au module réel plus tard)

---

## 4. T4 — P1-7 : Table "D-sur-A vs D-sur-C"

### Quoi faire

Ajouter à doc 22 §3 Stage 8 (avant le bloc `SignalCandidate`) :

```markdown
### Comportement de D selon l'engine d'origine du first_episode_ref

| Dimension | D-sur-A (first_episode vient de A) | D-sur-C (first_episode vient de C) |
|---|---|---|
| bet_structure hérité | DIRECTIONAL_LONG ou DIRECTIONAL_SHORT | BREAKOUT (continuation variant) |
| forecast_strength clip | [0, 10] (identique) | [0, 10] (identique) |
| conviction profile | Structure reformation dans direction trend A | Structure reformation post-breakout continuation |
| invalidation | first_episode_ref.invalidation tightened 0.5× | first_episode_ref.invalidation tightened 0.5× |
| sizing | 0.5 × N_first_episode (R-D-4) | 0.5 × N_first_episode (R-D-4) |
| risque spécifique | Réversion contre le trend si momentum épuisé | Faux breakout continuation (fade setup) |
| OFI requis | Dans la direction du trend A original | Dans la direction de la continuation C originale |
```

### Acceptance criteria T4

- [ ] Table ajoutée à doc 22 §3
- [ ] Les deux cas (D-sur-A, D-sur-C) couverts
- [ ] Pas de nouvelle formule introduite (les formules sont celles de l'Annexe A)

---

## 5. T5 — P1-8 : Colonne calibration_module dans tables thresholds

### Quoi faire

Dans doc 21 §5 et doc 22 §6, ajouter une colonne `Calibration seam` à chaque table de thresholds pointant vers le module de calibration :

- Les THR-X* (X08, X09, X10, X11) → `engine_coordination_rules.py` via `risk_runtime_drawdown_calibration.py`
- Les THR-C_* (lookback, OFI, queue, VPIN, invalidation) → `risk_runtime_drawdown_calibration.py`
- Les THR-D_* (lookback, min_gap, marginal_ev) → `risk_runtime_drawdown_calibration.py`
- THR-W01, THR-T01, THR-D01 → renvoi doc 19 §threshold table

### Acceptance criteria T5

- [ ] Chaque threshold pointe vers un module de calibration existant ou à créer
- [ ] Aucun "calibrated" orphelin (sans module pointé)

---

## 6. T6 — P1-9 : Version-pin doc 23

### Quoi faire

Dans le header de doc 21 et doc 22, remplacer :
```
companion: docs 19, 20, 22, 23
```
par :
```
companion: docs 19, 20, 22, 23 (pinned: doc_23@<git_hash_of_23_MICROSTRUCTURE_FEATURE_DICTIONARY.md>)
```

Obtenir le hash via :
```bash
rtk git log --format="%H" -1 -- docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md
```

### Acceptance criteria T6

- [ ] Hash réel (pas placeholder) dans headers docs 21 et 22

---

## 7. T7 — P1-10 : Source VPIN threshold crypto

### Quoi faire

Doc 21 §5 dit `THR-C_VPIN_MAX ≤ 0.5` sans source crypto.

Action :
1. Chercher (timebox 15 min) une étude VPIN sur crypto. Candidats :
   - Abad-Yagüe et al. (2018) "Does VPIN predict cryptocurrency crashes?"
   - Wei-Wang (2020) "Liquidity and Market Efficiency in Cryptocurrencies"
   - Ardia-Bluteau-Rüede (2019) "Regime changes in Bitcoin GARCH volatility dynamics" (mentionne VPIN comme feature)
2. Si trouvé → citer DOI + valeur seuil observée dans la table §5
3. Si non trouvé → marquer explicitement dans la table :
   ```
   THR-C_VPIN_MAX | Max VPIN before toxic skip | 0.35 | 0.5 | continuation_validator_c |
   Note: default 0.35 from Abad-Yagüe 2012 (equities); crypto-specific calibration TBD_shadow_calibration
   ```

### Acceptance criteria T7

- [ ] Soit DOI crypto citée, soit mention explicite "TBD_shadow_calibration" + source equities transitoire

---

## 8. T8 — §5 : 4 corrections docs 19 et 20

### Quoi faire

4 corrections chirurgicales. Pour chaque correction, je donne le grep pour trouver l'occurrence et le remplacement exact.

### Correction 1 : `src/meta_engine/` → paths corrects

```bash
rtk grep -n "meta_engine" docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md
rtk grep -n "meta_engine" docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md
```

Remplacer selon contexte :
- `src/meta_engine/<runtime>` → `src/meta_minimal/<runtime>`
- `src/meta_engine/<governance>` → `src/meta_learning/<governance>`
- `src/meta_engine/<coordination>` → `src/protocols/<coordination>`
- `tests/test_meta_engine/` → `tests/test_protocols/` ou `tests/test_meta_minimal/` selon le module testé

### Correction 2 : `side="flat"` résiduel

```bash
rtk grep -n 'side.*flat\|flat.*side\|"flat"' docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md
```

Si trouvé → remplacer par le pattern standard :
> "append `ConditioningRecord(family=HARD_BLOCK)` + `RefusalRecord(category=HARD_BLOCK)`, emit no canonical `SignalCandidate`"

### Correction 3 : "drop-in replacement"

```bash
rtk grep -n "drop-in\|drop.in" docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md
```

Remplacer par :
> "backward-compatible extension: optional fields added first, then per-engine migration on a staged schedule"

### Correction 4 : "A/B only coded"

```bash
rtk grep -n "A/B only\|A.B only\|seulement A.B\|only A and B" docs/production_deployment_plan/19_MULTIPAIR_MODERNIZATION_PLAN.md
```

Remplacer par :
> "A/B/C/D codés ; C et D requièrent doctrinal deepening (voir docs 21, 22)"

### Acceptance criteria T8

- [ ] `grep "meta_engine" docs/production_deployment_plan/19_*.md docs/production_deployment_plan/20_*.md` → 0 occurrences
- [ ] `grep '"flat"' docs/production_deployment_plan/20_*.md` → 0 occurrences
- [ ] `grep "drop-in" docs/production_deployment_plan/20_*.md` → 0 occurrences
- [ ] `grep "only.*coded\|A/B only" docs/production_deployment_plan/19_*.md` → 0 occurrences

---

## 9. T9 — Verification pass final

### Quoi faire (dans cet ordre exact)

```bash
# 1. Guardrails — zéro nouvelle violation
python scripts/run_engineering_guardrails.py
# Vérifier: new_violations=0

# 2. Tests paper_repro
rtk pytest -q tests/test_microstructure/test_paper_repro.py
# Vérifier: all passed

# 3. Tests existants engine C/D — pas de régression
rtk pytest -q tests/test_engines/test_engine_c/ tests/test_engines/test_engine_d/
# Vérifier: no failures

# 4. Tests protocoles — pas de régression
rtk pytest -q tests/test_protocols/
# Vérifier: no failures

# 5. Tests calibration — pas de régression
rtk pytest -q tests/test_calibration_methods/
# Vérifier: no failures

# 6. Cohérence inter-docs — vérification manuelle
rtk grep -n "meta_engine" docs/production_deployment_plan/*.md
# Vérifier: 0 résultats (ou seulement dans contexte historique "was meta_engine, now...")

rtk grep -n '"flat"' docs/production_deployment_plan/*.md
# Vérifier: 0 résultats dans un contexte d'émission SignalCandidate

# 7. Checklist R-QUANT-FIRST pour chaque formule en Annexe A
# Pour chaque formule, vérifier:
#   [ ] Équation complète
#   [ ] DOI + eq. number
#   [ ] Paramètres avec THR-* default + cap
#   [ ] Test paper_repro référencé
```

### Acceptance criteria T9

- [ ] `new_violations=0`
- [ ] Tous les tests passent (paper_repro + engine C/D + protocols + calibration)
- [ ] 0 `meta_engine` résiduel dans les docs
- [ ] 0 `side="flat"` résiduel dans contexte d'émission
- [ ] Checklist R-QUANT-FIRST verte pour les 4 formules

---

## 10. Rapport de complétion Codex

Après T9, Codex produit un **bloc de complétion** dans le format suivant :

```
SPRINT FINAL COMPLETION REPORT
===============================
Date: YYYY-MM-DD
Branch: <branch name>

T1 P0-5a (Annexe A doc 21):
  status: COMPLETE | PARTIAL | BLOCKED
  files: <list>
  formulas: 4/4 with DOI
  thresholds_added: <count>

T2 P0-5b (Annexe A doc 22):
  status: COMPLETE | PARTIAL | BLOCKED
  files: <list>

T3 P0-5c (paper_repro tests):
  status: COMPLETE | PARTIAL | BLOCKED
  tests_passed: <n>/<total>

T4 P1-7 (D-sur-A vs D-sur-C):
  status: COMPLETE | PARTIAL | BLOCKED

T5 P1-8 (calibration_module column):
  status: COMPLETE | PARTIAL | BLOCKED

T6 P1-9 (version-pin doc 23):
  hash: <actual git hash>

T7 P1-10 (VPIN crypto source):
  status: COMPLETE (DOI found) | COMPLETE (TBD_shadow marked)

T8 §5 (corrections docs 19/20):
  meta_engine_remaining: 0
  flat_remaining: 0
  drop_in_remaining: 0
  ab_only_remaining: 0

T9 Verification:
  guardrails: new_violations=<n>
  paper_repro_tests: <passed>/<total>
  engine_cd_tests: <passed>/<total>
  protocol_tests: <passed>/<total>
  calibration_tests: <passed>/<total>

OVERALL: COMPLETE | PARTIAL | BLOCKED
BLOCKED_BY: <if partial/blocked, what's missing>
DISPUTES_OPENED: <list or "none">
```

Ce rapport est ajouté à `docs/production_deployment_plan/update_audit/2026-04-16_docs21_22_opus_audit.md` section "Tests and Proof".

---

## 11. Après le sprint — handback Opus

Quand Codex envoie le rapport de complétion :
1. Opus exécute le re-audit final sous protocole 25
2. Cible verdict : ≥ 9.0/10 (le seuil monte de 8.5 à 9.0 parce que P0-5 comble le trou quant)
3. Si ≥ 9.0 → docs 21/22 passent de `SPEC` à `APPROVED SPEC` → merge autorisé
4. Si < 9.0 → Opus liste les écarts restants dans un nouveau doc 27 §addendum

---

## 12. Timeline recommandée

| Jour | Tâches | Heures estimées |
|---|---|---|
| Jeudi 17 avril | T1 + T2 (formules) | 1h |
| Vendredi 18 avril | T3 (tests paper_repro) + T4 (D-sur-A/C) | 1h30 |
| Samedi 19 avril | T5 + T6 + T7 + T8 (corrections P1) | 1h |
| Dimanche 20 avril matin | T9 (verification pass) + rapport de complétion | 30 min |
| Dimanche 20 avril après-midi | Handback Opus → re-audit | Opus side |

---

**Fin du brief. Codex : commencer par T1 (formules Annexe A doc 21). Ne pas coder de feature microstructure avant que T1 et T2 soient COMPLETE.**


---

## Source: docs/production_deployment_plan/30_PROMOTION_CALIBRATION_REGISTER.md

# 30 - Promotion Calibration Register

> Status: living governance register for what must be calibrated, frozen, or proven before promotion through Shadow, Micro-live, and Live.
>
> Date: 2026-04-17.
>
> Hard rule: this file does not override the repo, docs `12`, `13`, `14`, or engine specs. It is an operational register that says what is still missing before a promotion decision is defensible.

---

## 0. Objective

Keep one durable place that answers a simple question:

- what must still be calibrated before an engine or shared rail is promotable in Shadow,
- what must still be proven before `G2.3 -> MICRO_LIVE`,
- what must still be re-calibrated or re-validated before Live scaling.

This file exists because the real repo now contains many engine-level hardening slices and audit packs, but the remaining promotion blockers were spread across:

- `12_LOCAL_LAB_VS_VPS_SEPARATION.md`
- `13_CALIBRATION_METHODS.md`
- `14_SHADOW_GATE_MATH.md`
- engine-specific audit packs in `docs/production_deployment_plan/update_audit/`

This register compresses those blockers into one promotion-oriented view.

---

## 1. Scope

Included:

- Engine A / B / C / D promotion blockers
- shared microstructure blockers that still matter for promotion
- shared calibration / signed-artifact blockers
- stage-specific blockers for:
  - Shadow sign-off
  - Micro-live promotion
  - Live scaling

Excluded:

- full re-explanation of calibration math from `13_...`
- full re-explanation of gate math from `14_...`
- implementation detail inventories already captured in engine audit packs

---

## 2. Reading Rules

1. Current code remains the operational source of truth.
2. `12_...` decides where calibration lives and who signs it.
3. `13_...` decides how thresholds are calibrated.
4. `14_...` decides what statistical evidence is required at promotion gates.
5. A surface can be:
   - `READY_FOR_SHADOW`
   - `NEEDS_MORE_CALIBRATION`
   - `RESEARCH_ONLY`
   - `DO_NOT_PROMOTE`
6. "Before Shadow sign-off" means before treating the rail as a governed Shadow candidate or before advancing a Shadow palier with confidence.
7. "Before Micro-live" means before `G2.3 -> MICRO_LIVE`.
8. "Before Live scaling" means before `G3 -> target live capital`.

---

## 3. Non-Calibrated Surfaces

The following are not statistical-calibration targets:

- halal prohibitions and forbidden account-feature checks
- hard caps that humans declared as absolute floors/caps
- Local IA Lab vs VPS topology
- signature requirement for calibration or promotion artifacts

These surfaces still require proof and enforcement, but not statistical threshold fitting.

---

## 4. Register Summary

| Surface | Type | Current verdict | Before Shadow sign-off | Before Micro-live | Before Live scaling | Evidence |
|---|---|---|---|---|---|---|
| Engine A | hybrid | `NEEDS_MORE_CALIBRATION` | Freeze governed A-specific cost and conviction thresholds; replace ad hoc seam injection with signed OFI/Kyle/RK upstream evidence | Pass `G2.3` evidence on real Shadow fills; prove drift and DD remain inside gate math | Recalibration cadence + Micro-live evidence before capital increase | `20`, `23`, `24`, `13`, `14`, audit pack `2026-04-17_engine_a_prompt_correction_hardening.md` |
| Engine B | hybrid | `NEEDS_MORE_CALIBRATION` | Calibrate excess/fade/conviction thresholds, especially VPIN toxic-flow fade and cost posture | Pass `G2.3` evidence on real Shadow fills; keep anti-breakout and cost rails stable under live-like noise | Recalibration cadence + Micro-live evidence before capital increase | `20`, `23`, `24`, `13`, `14`, audit packs `2026-04-17_engine_b_*` |
| Engine C | hybrid | `NEEDS_MORE_CALIBRATION` | Govern `THR-C_VPIN_MAX`; if `kyle_lambda_max` is used, source it from calibration; wire one canonical upstream assembler | Pass `G2.3` evidence on Shadow fills with final microstructure thresholds, not TBD values | Recalibration cadence + Micro-live evidence before capital increase | `21`, `23`, `24`, `29`, `13`, `14`, audit pack `2026-04-16_engine_c_continuation_microstructure_wiring.md` |
| Engine D | hybrid | `NEEDS_MORE_CALIBRATION` | Freeze anti-revenge/re-entry governance (`THR-X10`, `THR-X11`) with replay/shadow evidence; confirm option C does not leave a blind spot | Pass `G2.3` evidence on Shadow fills; maintain first-episode lineage and anti-revenge observability at promotion time | Recalibration cadence + Micro-live evidence before capital increase | `22`, `24`, `29`, `13`, `14`, `2026-04-16_docs21_22_opus_audit.md`, current `engine_d` code/tests |
| Canonical microstructure calculators | statistical | `READY_FOR_SHADOW` | No new formula calibration required at calculator level; only consumer thresholds remain to freeze | Keep the consumer-facing thresholds signed and versioned | Recalibrate thresholds by consumer, not formulas | `23`, `13`, audit packs `2026-04-16_*.md` |
| Calibration artifact / loader rail | governance_only | `READY_FOR_SHADOW` | Signed artifact required; no unsigned fallback | Same | Same | `12`, `13`, `src/calibration_loader/` |
| Shadow gate report / promotion artifact rail | governance_plus_stats | `NEEDS_MORE_CALIBRATION` | Shadow metrics may be computed, but promotion-ready signed gate artifacts still need one durable governed report path | Mandatory before `G2.3 -> MICRO_LIVE` | Mandatory before `G3` | `14`, `25`, `26`, `src/protocols/` |
| Halal / forbidden account-feature rails | deterministic | `READY_FOR_SHADOW` | No statistical calibration; only zero-violation proof | Mandatory zero-violation proof | Mandatory zero-violation proof | `12`, `13`, `14`, halal/account audit rails |
| Runtime hard caps / breakers | deterministic_plus_tightening | `READY_FOR_SHADOW` | Can only be tightened by calibration, never loosened | Same | Same | `10`, `12`, `13`, runtime risk rails |

---

## 5. Detailed Register

### 5.1 Engine A

**Current verdict**: `NEEDS_MORE_CALIBRATION`

Engine A is now materially hardened in code, but its newly explicit local semantic seams are still only halfway to governed promotion readiness.

#### Before Shadow sign-off

- Freeze `ce_min_A` and `delta_safe_A` through the signed calibration rail defined in `11_...` and `13_...`.
- Stop treating:
  - `ofi_flow_score`
  - `kyle_lambda_cost_uplift`
  - `realized_kernel_vol_scale`
  as merely injectible normalized values.
- Replace free-form injection with one governed upstream evidence path from canonical microstructure outputs into Engine A inputs.
- Keep `CostVerdict.MARGINAL` non-emittable and do not weaken the current guards.

#### Before Micro-live

- Pass the gate battery from `14_SHADOW_GATE_MATH.md` on real Shadow fills.
- Demonstrate that A's OFI/Kyle/RK seams remain additive and do not silently alter the primary A semantics.
- Confirm that cost drift between backtest, Shadow, and pre-live conditions remains inside the signed tolerance.

#### Before Live scaling

- Re-run calibration on the documented cadence.
- Re-check drawdown, CE, PSR/DSR, and drift after Micro-live evidence exists.

#### Evidence

- `docs/production_deployment_plan/update_audit/2026-04-17_engine_a_prompt_correction_hardening.md`
- `docs/production_deployment_plan/update_audit/2026-04-17_engine_a_ofi_first_local_conviction_seam.md`
- `docs/production_deployment_plan/update_audit/2026-04-17_engine_a_kyle_lambda_cost_seam.md`
- `docs/production_deployment_plan/update_audit/2026-04-17_engine_a_realized_kernel_structure_seam.md`

---

### 5.2 Engine B

**Current verdict**: `NEEDS_MORE_CALIBRATION`

Engine B is auditably stronger than before, but its trading thresholds remain mostly heuristic and still need governed Shadow evidence.

#### Before Shadow sign-off

- Freeze B-specific cost thresholds:
  - `ce_min_B`
  - `delta_safe_B`
- Freeze B-specific excess / fade thresholds, especially the toxic-flow fade branch:
  - `vpin_current >= 0.35`
  - `toxic_flow_correlation > 0.7`
- Freeze conviction and anti-breakout thresholds under the same signed artifact discipline.
- Keep B as a local semantic reservoir; do not flatten its mean-reversion / fade logic into C/D-style semantics.

#### Before Micro-live

- Pass the gate battery from `14_SHADOW_GATE_MATH.md` on real Shadow fills.
- Prove that the toxic-flow fade branch improves or at least does not degrade CE net under real Shadow conditions.
- Prove that richer reason codes and runtime risk statuses stay coherent under repeated Shadow runs.

#### Before Live scaling

- Re-run the B-local calibration cadence and compare Micro-live evidence against Shadow evidence before increasing capital.

#### Evidence

- `docs/production_deployment_plan/update_audit/2026-04-17_engine_b_hardening_from_cartography_audit.md`
- `docs/production_deployment_plan/update_audit/2026-04-17_engine_b_reaudit_residual_fixes.md`
- `docs/production_deployment_plan/update_audit/2026-04-17_engine_b_prompt1_explicit_status_and_forecast_proofs.md`
- `docs/production_deployment_plan/update_audit/2026-04-17_engine_b_toxic_flow_fade_local_subsignal.md`

---

### 5.3 Engine C

**Current verdict**: `NEEDS_MORE_CALIBRATION`

Engine C is already a rich and shadow-capable rail, but promotion still depends on final governed thresholds for the new microstructure gates.

#### Before Shadow sign-off

- `THR-C_VPIN_MAX` is still `TBD_shadow_calibration` in doc 21 and must be frozen before VPIN becomes a durable promotion dependency.
- If `continuation_kyle_lambda_max` is supplied, it must come from a governed calibration artifact rather than an inline one-off number.
- Wire one canonical upstream assembler into `EngineCInput` so the runtime does not accumulate duplicate calculation paths.
- Confirm `ce_min_C` and `delta_safe_C` remain governed by signed calibration, not ad hoc tuning.

#### Before Micro-live

- Pass the gate battery from `14_SHADOW_GATE_MATH.md` on real Shadow fills using the final, signed microstructure thresholds.
- Confirm that the microstructure vetoes do not create an unintended sample-size collapse that invalidates the gate math.

#### Before Live scaling

- Re-run the consumer thresholds on the documented cadence and compare Micro-live against Shadow.

#### Evidence

- `docs/production_deployment_plan/21_ENGINE_C_SPEC_BREAKOUT_CONTINUATION.md`
- `docs/production_deployment_plan/update_audit/2026-04-16_engine_c_continuation_microstructure_wiring.md`
- current `src/engines/engine_c/` code and tests

---

### 5.4 Engine D

**Current verdict**: `NEEDS_MORE_CALIBRATION`

Engine D is rich and shadow-capable, but promotion remains sensitive because the user-selected option `C` explicitly refused a continuous revenge-penalty formula. That keeps the anti-revenge rail observable and governed, but still in need of replay/shadow proof.

#### Before Shadow sign-off

- Freeze operational governance around:
  - `THR-X10` anti-revenge cooldown failsafe
  - `THR-X11` max consecutive re-entries before reset
- Confirm through replay/backtest evidence that option `C` (observability, no continuous penalty) does not create a blind spot.
- Keep `first_episode_ref`, `closed_episode_journal`, and `anti_revenge_state` auditable through the current protocol rails.
- Confirm `ce_min_D` and `delta_safe_D` remain governed by signed calibration, not local heuristics.

#### Before Micro-live

- Pass the gate battery from `14_SHADOW_GATE_MATH.md` on real Shadow fills.
- Confirm that D's anti-revenge observability fields remain populated and useful at gate time, not merely logged.
- Confirm that duplication / marginal portfolio gain decisions remain explicit and stable under Shadow.

#### Before Live scaling

- Re-run calibration cadence on D-local economics and re-entry governance after Micro-live evidence exists.

#### Evidence

- `docs/production_deployment_plan/22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md`
- `docs/production_deployment_plan/update_audit/2026-04-16_docs21_22_opus_audit.md`
- current `src/engines/engine_d/` code and tests

---

### 5.5 Canonical Microstructure Package

**Current verdict**: `READY_FOR_SHADOW`

The calculator layer itself is no longer the main blocker.

#### Before Shadow sign-off

- Do not recalibrate or mutate the canonical formulas silently.
- Freeze consumer thresholds and normalization seams, not calculator formulas.
- Keep window/hash/quality flags traceable in the current package.

#### Before Micro-live

- Confirm that every microstructure feature used by A/B/C/D comes from one canonical record path, not duplicate inline calculations.

#### Before Live scaling

- Recalibrate only the consumer thresholds and acceptance bands, not the core formulas.

#### Evidence

- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `docs/production_deployment_plan/update_audit/2026-04-16_*.md`

---

### 5.6 Shared Calibration / Promotion Rail

**Current verdict**: `NEEDS_MORE_CALIBRATION`

#### Before Shadow sign-off

- Calibration artifacts must remain:
  - produced in Local IA Lab
  - human-signed
  - immutable after signature
  - verified by `calibration_loader`

#### Before Micro-live

- Promotion to Micro-live requires one governed, signed gate-evidence artifact that proves the checks in `14_...`.
- No engine should be promoted from chat history or scattered audit packs alone.

#### Before Live scaling

- The same signed-artifact discipline must apply to the Micro-live -> Live decision.

#### Evidence

- `docs/production_deployment_plan/12_LOCAL_LAB_VS_VPS_SEPARATION.md`
- `docs/production_deployment_plan/13_CALIBRATION_METHODS.md`
- `docs/production_deployment_plan/14_SHADOW_GATE_MATH.md`
- `src/calibration_loader/`
- `src/protocols/`

---

## 6. Operational Use

Use this register in the following order:

1. read the current engine or shared-rail audit pack
2. check this register for stage-specific blockers
3. verify whether the blocker is:
   - statistical calibration
   - deterministic governance proof
   - missing signed artifact
   - missing promotion evidence
4. only then decide whether the next slice is:
   - code hardening
   - calibration production in Local IA Lab
   - gate report production
   - user arbitration

---

## 7. What This Register Forbids

- Do not say "ready for promotion" only because tests are green.
- Do not say "needs calibration" without naming the stage:
  - Shadow
  - Micro-live
  - Live scaling
- Do not treat deterministic halal or hard-cap rules as statistical thresholds.
- Do not create a second promotion register elsewhere unless this one is formally replaced.

---

## 8. Next Safe Step

Keep this file updated whenever an engine or shared promotion surface changes status on:

- current verdict
- Shadow blockers
- Micro-live blockers
- Live-scaling blockers

Any future slice that claims promotion progress should update this register or explicitly justify why it does not change it.


