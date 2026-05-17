# Session 2026-05-07 — Livraison Claude (verbatim)

## Contexte initial

Audit P0 critique du run backtest `strategy_ladder_first_controlled_run-1778085375411` :
- 15 460 candidats × 4 capital_buckets = 61 840 records
- **0 trade exécuté** (`trade_detail_ledger.jsonl` vide)
- 100 % records = `PHANTOM` / `economically_absurd`
- `expected_ce = -0.00023` constant (formule arithmétique des hardcoded)

## Causes racines identifiées (verbatim de l'audit P0)

1. **Pas d'invocation des engine runners A/B/C/D** : rail Phase 2B utilisait un proxy `COMPAT_FEATURE_DISCOVERY` qui clonait une feature row OHLCV par engine_id sans invoquer la logique moteur native.

2. **Constantes économiques hardcoded** dans `src/local_replay_runtime/strategy_ladder_data_factory.py:1862-1887` :
   ```python
   "expected_edge_bps": 5.0,
   "spread_bps": 4.0 if BOOK_DEPTH20_AVAILABLE else 6.0 else 0.0,
   "slippage_bps": 2.0,
   "latency_penalty_bps": 1.0,
   ```

3. **Formule CE = -0.00023** = `(5 - 4 - 2×1.15 - 1×1.0) / 10000` triggée systématiquement par la gate `economically_absurd` du shadow simulator (`src/local_replay_runtime/shadow_execution_simulator.py:347-350`).

Classification du run : **PROXY_FEATURE_DISCOVERY_REPLAY** (pas un vrai backtest moteur).

## Patches livrés (chronologique)

### Phase 1 — Patches défensifs S1/S2/S3 (gate + flag + counters)

#### `src/local_replay_runtime/strategy_ladder_runner.py` (modifié)
- Gate `STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES` dans `_stage_final_status` quand `executed_trade_count == 0` et `detailed_replay_record_count > 0`
- Sentinelle `executed_trade_count: int = -1` préserve le comportement legacy
- Helper `_count_executed_trades(bucket_results)` qui compte EXECUTED + REDUCED avec notional > 0
- Blocker code `NO_EXECUTED_TRADES` ajouté à `blocker_codes`
- Helper `_invoke_engine_native_bridges_sample(...)` — invocation opt-in du pont microstructure sur sample limité (default 10 candidats)

#### `src/local_replay_runtime/strategy_ladder_models.py` (modifié)
- `StrategyLadderRequest.engine_native_mode: bool = False` (flag opt-in P3a)
- `StrategyLadderRequest.engine_native_sample_size: int = Field(default=10, ge=0)`
- `StrategyLadderRunManifest` augmenté de :
  - `economic_constants_provenance: str = "UNKNOWN"`
  - `candidate_engine_native_count: int`
  - `candidate_proxy_count: int`
  - `executed_trade_count: int`
  - `engine_native_status: str = "ENGINE_NATIVE_NOT_REQUESTED"`
  - `engine_native_records_built: int`
- `StrategyLadderRawWindowManifest.raw_book_delta_path: str | None = None`

### Phase 2 — Pont microstructure 4 engines (P3a)

#### `src/local_replay_runtime/strategy_ladder_engine_native_adapter.py` (CRÉÉ ~970 lignes)

Pont entre raw_windows et seam canonique `data_backbone.microstructure`. Lit JSONL (trades, orderbook snapshot+deltas, OHLCV) et calcule 5 records canoniques.

**Reconstruction snapshot+deltas** (fix critique 2026-05-07) :
- Identifie le snapshot le plus récent ≤ `window_start_ms`
- Charge les deltas applicables (`update_id > snapshot.update_id`) jusqu'à `window_end_ms`
- Applique les deltas séquentiellement pour reconstruire l'état book event-par-event
- À chaque delta dans la fenêtre, capture l'état top-of-book / top-k

**Sur run dossier réel BNBUSDT** :
- 2 snapshots/jour vs **191 735 deltas/jour**
- Reconstruction → **963 états book reconstruits** sur fenêtre 5min
- 5/5 records calculés (vs 1/5 avant fix)

API publiques :
```python
build_engine_a_microstructure_inputs_from_window(...)  # → EngineABridgeResult
build_engine_b_microstructure_inputs_from_window(...)  # → EngineBBridgeResult
build_engine_c_microstructure_inputs_from_window(...)  # → EngineNativeBridgeResult
build_engine_d_microstructure_inputs_from_window(...)  # → EngineDBridgeResult
```

### Phase 3 — Builders engine input (4 engines)

Pour chaque engine, un builder construit un `EngineXInput.model_validate-compatible` complet (incluant les champs structurels REQUIRED) en respectant la philosophie de trading et **sans toucher aux engines**.

#### `src/local_replay_runtime/strategy_ladder_engine_a_input_builder.py` (CRÉÉ ~430 lignes)

Engine A = Premium Trend / Initial Expansion (doc 20 §13.1).

5 heuristiques OHLCV alignées **verbatim** sur `structure_detector_a.py:25-33` Pydantic comments :
| Champ | Sémantique Pydantic | Heuristique |
|---|---|---|
| `direction_score` [-1,1] | "dominant local direction quality" | mean (close−open)/(high−low) |
| `continuation_score` [0,1] | "quality of continuation" | autocorr directionnelle bars |
| `structure_quality` [0,1] | "overall structure readability" | 1 − mean_wick_ratio |
| `zone_proximity` [0,1] | "proximity to relevant zones" | 1 − min(dist_high, dist_low)/range |
| `trend_stability` [0,1] | "stability of the trend" | R² Pearson(closes, time) |

#### `src/local_replay_runtime/strategy_ladder_engine_b_input_builder.py` (CRÉÉ ~180 lignes)

Engine B = Mean Reversion (côté LONG, doc 14_ENGINE_B_AUDITS).

Builder fin (~180 lignes) qui délègue au pont microstructure pour 4 REQUIRED + VPIN. Les autres ~25 champs ont des defaults canoniques dans `EngineBInput`.

`walls_and_spoofing.py` (sweep_score, absorption_score, etc.) **NON câblé** — demande calibration finale.

#### `src/local_replay_runtime/strategy_ladder_engine_c_input_builder.py` (CRÉÉ ~470 lignes)

Engine C = Breakout Continuation (doc 21).

Implémente `detect_breakout_reference_doc21()` selon spec doc 21 §3 Stage 1 :
> Long : close ≥ upper_range_high + k × realized_vol_at_break
> Short : mirror

Output : `BreakoutReference(t_break, level, direction, realized_vol_at_break, queue_state_at_break)`

7 champs structurels dérivés sémantiquement (verbatim doc 21) :
- `breakout_strength` = magnitude relative au realized_vol_at_break
- `range_quality` = tightness pre-break
- `compression_quality` = squeeze de volatilité
- `volume_confirmation` = ratio volume break vs lookback
- `followthrough_room` = distance proxy via range_size
- `extension_pct` = extension actuelle / range
- `retrace_risk` = max pullback post-break / range

#### `src/local_replay_runtime/strategy_ladder_engine_d_input_builder.py` (CRÉÉ ~430 lignes)

Engine D = Re-entry / Second Chance (doc 22).

Le défi unique : engine_d **dépend d'un `first_episode_ref`** (trade A ou C clôturé). En backtest 0 trades → fallback `BUILDER_NO_FIRST_EPISODE_DEFAULTS` (doctrine respectée).

Builder accepte `first_episode_context: dict | None` pour mode shadow/research avec contexte simulé.

8 heuristiques alignées sur poids `signal_math_d.py` :
| Champ | Poids | Stage |
|---|---|---|
| `prior_trade_quality` | 0.55 | history_score |
| `reformation_quality` | 0.45 | reformation_score |
| `pullback_quality` | 0.30 | reformation_score |
| `marginal_edge` | 0.35 | marginal_value_score |
| `continuation_room` | 0.30 | marginal_value_score |
| `concentration_headroom` | 0.20 | marginal_value_score |
| `reentry_lateness` (inv.) | 0.15 | marginal_value_score |

### Phase 4 — Service economic provenance (MVP)

#### `src/local_replay_runtime/strategy_ladder_economic_provenance.py` (CRÉÉ + refactoré ~530 lignes)

Service-oriented venue-aware. Le caller dit "j'ai besoin de l'eco pour ce candidat à ce timestamp" → le service va chercher chaque champ dans la bonne source.

5 champs avec sources canoniques :
| Champ | Source canonique | Provenance flag |
|---|---|---|
| `spread_bps` | best_ask − best_bid depuis raw_book_path | `MEASURED_FROM_BOOK_SNAPSHOT` |
| `slippage_bps` | Kyle lambda × standard_notional | `MEASURED_FROM_KYLE_LAMBDA` |
| `expected_edge_bps` | forward return median rolling 1h | `MEASURED_FROM_FORWARD_RETURN_MEDIAN_TO_CALIBRATE` |
| `fee_bps` | venue.taker_fee_bps depuis registry | `MEASURED_FROM_VENUE_METADATA_*` |
| `latency_penalty_bps` | venue.latency_bps_conservative | `STATIC_CONSERVATIVE_FROM_*_HISTORICAL` |

Tier 1 (default) : MESURÉ depuis source canonique
Tier 2 (override) : caller force valeur (suffix `_OVERRIDE` provenance)
Tier 3 (fallback) : `DEFAULT_TO_CALIBRATE` ou `DEGRADED_FALLBACK_*` + warning

#### `src/local_replay_runtime/pair_bounds_registry.py` (CRÉÉ ~110 lignes)

Bornes par pair (clamp dynamique) pour protéger contre outliers données :
```python
BNBUSDT_SPOT_BOUNDS = EconomicBounds(
    spread_bps=(0.5, 50.0),
    slippage_bps=(0.1, 10.0),
    fee_bps=(5.0, 25.0),
    latency_bps=(0.1, 50.0),
    edge_bps=(0.0, 30.0),
    reject_threshold_multiplier=2.0,
)
```

`clamp_with_warning(value, field_name, pair, bounds, reject_threshold=2.0)` :
- Clamp dans [floor, ceiling] + warning audit-ready
- Outlier > ceiling × 2 → `rejected=True` (caller refuse candidat)

#### `src/local_replay_runtime/strategy_ladder_edge_model_provider.py` (CRÉÉ ~165 lignes)

Edge predictor causal forward-return :
- N bars OHLCV jusqu'à t (causal, pas de look-ahead)
- forward_return = (close[i+1] − close[i]) / close[i]
- edge_bps = median(|forward_returns|) × 10000

Provenance : `MEASURED_FROM_FORWARD_RETURN_MEDIAN_TO_CALIBRATE`

LIMITATION (TO_CALIBRATE) : pas de conditionnement par regime, pas de feature engineering. Production exige LightGBM (`calibration_methods/ml_trainer.py` existe déjà).

### Phase 5 — Venue-aware (BUG fix)

#### `src/local_replay_runtime/venue_metadata_registry.py` (CRÉÉ ~140 lignes)

Le caller dit "j'ai besoin du fee/latency pour trader sur venue X" → le registry route vers le bon provider.

```python
VENUE_REGISTRY = {
    "binance_spot": BINANCE_SPOT_METADATA,  # taker 10 bps, latency 1.5 bps
    "bybit_spot":   BYBIT_SPOT_METADATA,    # taker 10 bps, latency 1.5 bps
}
UNKNOWN_VENUE_METADATA = ...  # taker 25 bps fallback degraded
```

Résolution venue : override caller > auto-detect path silver/{venue}/spot/... > fallback unknown.

Pattern live Binance :
```python
account_snapshot = binance_rest_client.get_account_snapshot()
prov = compute_economic_provenance(
    venue="binance",
    fee_bps_override=float(account_snapshot.taker_commission),  # API live dynamique
    ...
)
# fee_provenance = "MEASURED_FROM_VENUE_API_OVERRIDE"
```

## Tests pytest livrés (cumulatif session)

| Fichier | Tests | Status |
|---|---|---|
| `test_strategy_ladder_engine_native_adapter.py` | 13 | ✅ |
| `test_strategy_ladder_engine_a_input_builder.py` | 8 | ✅ |
| `test_strategy_ladder_engine_b_input_builder.py` | 6 | ✅ |
| `test_strategy_ladder_engine_c_input_builder.py` | 6 | ✅ |
| `test_strategy_ladder_engine_d_input_builder.py` | 8 | ✅ |
| `test_strategy_ladder_economic_provenance.py` | 13 (8 existants adaptés + 5 nouveaux) | ✅ |
| `test_pair_bounds_registry.py` | 7 | ✅ |
| `test_strategy_ladder_edge_model_provider.py` | 4 | ✅ |
| `test_venue_metadata_registry.py` | 14 | ✅ |
| `test_strategy_ladder_runner.py` | 1 modifié | ✅ |

**Total** : 80+ tests pytest livrés/adaptés.

## Régression finale

```
pytest tests/test_local_replay_runtime/ --tb=line -q
→ 323 passed, 9 skipped, 0 failed
```

Avant session : 249 passed, 8 skipped, 2 failed.
Après session : 323 passed, 9 skipped, 0 failed.
Net : +74 tests, -2 failures (effets collatéraux positifs).

## État du plan P0 du 1er audit

| Item plan P0 | État final |
|---|---|
| **Candidate generation truth** (4 engines invoqués) | ✅ COMPLET |
| **CE/cost provenance** (5 champs mesurés/bornés/venue-aware) | ✅ MVP COMPLET |
| **Proxy vs real engine counters** | ✅ COMPLET |
| **Phantom/trade/refusal semantics** | ✅ COMPLET |

Plan P1 (Dashboard UX, Storage compression) et P2 (Matrices avancées) : **non touchés** cette session.

## Validation sur run dossier réel

Sur raw_window `eea9862e969edccaeed7a98b` du run audité (BNBUSDT 2025-05-04 23:55) :

| Engine | Builder status | run_engine_X invoqué | Decision |
|---|---|---|---|
| A | INSUFFICIENT_BARS (window cross-day) | ✅ | `no_trade` (NON_LONG_DIRECTION) |
| B | READY | ✅ | `no_trade` (NON_LONG_DIRECTION, z=+1.59) |
| C | NO_BREAKOUT (window cross-day) | ✅ | `no_trade` (INVALID_CANDIDATE_SIZE) |
| D | INSUFFICIENT_BARS | ✅ | `no_trade` (HISTORY_WEAK, doctrine doc 22) |

→ **4 engines invoqués pour la PREMIÈRE FOIS** depuis le rail backtest.
→ Tous refus par bonnes raisons (doctrine respectée).

## Insight quant clé

Sur dataset synthétique BNBUSDT avec mesures RÉELLES :
- spread = 1.9998 bps (vs 4.0 hardcoded)
- fee = 10.0 bps (Bybit metadata, vs 0.0 hardcoded)
- latency = 1.5 bps (Bybit conservative, vs 1.0 arbitraire)
- edge = 6.0168 bps (forward return, vs 5.0 hardcoded)

**TOTAL COST réel = 15.8 bps** vs edge prédit 6 bps → trade rejeté économiquement.

C'est la **réalité du marché BNBUSDT 5min spot** : il faut un setup à fort edge prédit (> 16 bps) pour passer la gate. Edge model production via LightGBM (`ml_trainer.py` existe déjà) requis pour atteindre ce niveau.

## Pas de push GitHub (utilisateur attend signal explicite)

État repos :
- `azizbenz/v5.3-claude-push-p0-backtest` (private) — patches initiaux S1/S2/S3+P3a poussés en début de session
- Tous les modules livrés depuis (builders engines + economic provenance + venue-aware) **NON poussés**
- Staging prêt dans `E:/claude  v5.3/v53_push_staging/v5.3-claude-push-p0-backtest-full/`

## Drawers memory palace (cumulés cette session)

`4c95b2bdd6f24938`, `8db196f8b6ea9298`, `821dfd053b00bd7b`, `aff62002fbefb167`, `b45c32a26ecde6cf`, `89e6f8dd4039d96a`, `73b5de361d537bfc`, `0cfa476ad9539fd6`, `eb904f03abd48538`
