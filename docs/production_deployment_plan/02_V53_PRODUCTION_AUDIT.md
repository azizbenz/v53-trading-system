# V5.3 Production Audit — Cartographie de ce qui existe déjà

> **Pourquoi ce fichier** : avant de proposer des manques à combler, il faut savoir précisément ce qui est **déjà codé et testé** dans V5.3. Cette carte évite de réinventer ou de croire qu'un module manque alors qu'il existe.
> **Méthodologie** : grep + Glob exhaustifs sur `v53_trading_system/src/` + lecture ciblée des fichiers clés.
> **Date** : 2026-04-08, post-audit S2/S3 + cross-checks S4.

---

## 1. Vue d'ensemble

| Métrique | Valeur |
|---|---|
| Fichiers `.py` dans `src/` | 357 |
| Tests passing | 1026 |
| Modules production-grade identifiés | ~30 |
| Stubs / vides identifiés | 2 (`portfolio/`, `meta/`) |
| Couverture engines A/B | ~10x supérieure à C/D (S3 finding) |

---

## 2. Risk backbone — couverture 5 dimensions ✓

Localisation : `src/risk_backbone/`

### 2.1 `emergency_kill_switch/`

```
emergency_kill_switch/
├── __init__.py
└── circuit_breaker.py    [persistent kill switch]
```

**`circuit_breaker.py`** (vérifié L1-80) :
- Classe `EmergencyCircuitBreaker` avec persistence disque atomique
- États : `ARMED` / `TRIPPED` / `DISARMED`
- 5 raisons trippables : `CRITICAL_DIVERGENCE`, `LOSS_BUDGET_BREACH`, `DATA_CORRUPTION`, `EXTERNAL_FILE_FLAG`, `OPERATOR_MANUAL`
- Flag externe `KILL_SWITCH_ACTIVE` (touch d'un fichier suffit à tripper)
- Reset manuel obligatoire après trip
- **Invariant doctrinal** : "if process crashes while active, restart MUST find the persisted flag and refuse to trade"
- Utilise `interface_contracts/atomic_io.py` pour write atomique

**Verdict** : production-grade. Rare en crypto retail. Aucune action requise sauf vérifier qu'il est appelé au démarrage et après chaque cycle d'erreur.

### 2.2 `loss_budgeter/`

```
loss_budgeter/
├── __init__.py
├── aggregate_loss_budgeter.py
├── drawdown_guard.py
├── loss_cap_guard.py
├── loss_reporter.py
├── position_loss_estimator.py
└── projected_loss_checker.py
```

5 modules + reporter. Les rôles présumés (à vérifier en S5a) :
- `aggregate_loss_budgeter` : budget total de pertes (period-based ?)
- `drawdown_guard` : surveillance DD courant
- `loss_cap_guard` : cap par position ou par cluster
- `position_loss_estimator` : estimation ex-ante
- `projected_loss_checker` : projection si trade exécuté
- `loss_reporter` : output structuré

**À vérifier en S5a** : le `drawdown_guard` est-il câblé au `circuit_breaker` (trip automatique à seuil DD) ou juste reporting ?

### 2.3 `exposure_budgeter/`

```
exposure_budgeter/
├── __init__.py
├── exposure_reporter.py
├── gross_cap_guard.py
├── gross_exposure_calculator.py
├── position_cap_guard.py
└── projected_exposure_checker.py
```

4 modules + reporter. Couvre exposition brute, cap par position, projection ex-ante.

### 2.4 `btc_factor_guard/`

```
btc_factor_guard/
├── __init__.py
├── beta_cap_guard.py
├── beta_reporter.py
├── pair_beta_registry.py
├── portfolio_beta_calculator.py
└── projected_beta_checker.py
```

Excellent : gestion du facteur BTC pour éviter de prendre 5 positions "diversifiées" qui sont en fait toutes du long beta BTC. **Critique en crypto où la corrélation à BTC monte à 0.8+ en stress.**

### 2.5 `correlation_cluster_guard/`

```
correlation_cluster_guard/
├── __init__.py
├── cluster_cap_guard.py
├── cluster_exposure_calculator.py
├── cluster_registry.py
├── cluster_reporter.py
└── projected_cluster_checker.py
```

5 modules : registry, calculateur d'exposition, cap, projection, reporter. **C'est le guard contre le risque de cluster** (au-delà du beta BTC seul).

> **NOTE faux-ami** : dans V5.3, "cluster" = **cluster de corrélation** (groupes d'assets corrélés). Dans V3.7, "cluster" = taxonomie de stratégies. Concepts orthogonaux.

### 2.6 Orchestrateur

`risk_runtime.py` — orchestre les 5 guards précédents.

**Verdict global risk backbone** : ★★★★☆. Couverture rare. Manque : daily P&L circuit breaker câblé au circuit_breaker (P1 — voir `04_GAPS_P1.md`).

---

## 3. Execution backbone — couverture order lifecycle complet ✓

Localisation : `src/execution_backbone/`

### 3.1 `order_decider/`

```
order_decider/
├── __init__.py
├── decision_reporter.py
├── execution_guard.py
├── intent_builder.py
├── order_type_selector.py
└── timeout_policy_selector.py
```

5 modules. `intent_builder` construit l'intention (pair, side, qty, type), `order_type_selector` choisit market/limit, `execution_guard` est le gate final, `timeout_policy_selector` gère les timeouts.

**À vérifier en S5a** :
- `intent_builder` génère-t-il un `clientOrderId` déterministe persisté **avant** l'envoi réseau ? Sans ça, pas d'idempotency, donc risque de double soumission sur retry.
- `execution_guard` a-t-il un check fee-aware ? (= rejeter si edge attendu < 2× fees round-trip)

### 3.2 `fill_tracker/`

```
fill_tracker/
├── __init__.py
├── fill_aggregator.py
├── fill_reporter.py
├── latency_meter.py
├── order_state_tracker.py
└── order_terminal_state_resolver.py
```

5 modules. **State machine complète** sur le cycle de vie d'un ordre : tracking, agrégation des fills (partial fills), résolution de l'état terminal, mesure de latence.

**À vérifier en S5a** :
- `order_state_tracker` persiste-t-il son état sur disque (résilience crash) ?
- `latency_meter` mesure le RTT exchange ou juste interne ?

### 3.3 `execution_cost_meter/`

```
execution_cost_meter/
├── __init__.py
├── adverse_selection_meter.py
├── cost_aggregator.py
├── elw_meter.py                  [Effective Liquidity Width]
├── fee_meter.py
└── partial_fill_cost_meter.py
```

5 modules. **Très complet** :
- `fee_meter.py` (vérifié L1-73) : `compute_fee()` calcule le breakdown exact (gross, fee_amount, fee_rate, maker/taker, fee_asset) avec arithmétique decimal exacte. Default 10 bps si pas d'override.
- `adverse_selection_meter` : mesure si nos ordres sont systématiquement remplis dans le mauvais sens (toxic flow detector partiel)
- `elw_meter` : Effective Liquidity Width — mesure de la liquidité effective consommée
- `partial_fill_cost_meter` : coût des fills partiels
- `cost_aggregator` : agrégation totale

**Verdict** : très bon. Manque : un **fee-aware ex-ante gate** (= refuser un trade si edge attendu < 2× fees round-trip). À ajouter en P0 — voir `03_GAPS_P0.md`.

### 3.4 `reconciliation_layer/`

```
reconciliation_layer/
├── __init__.py
├── divergence_classifier.py
├── fill_reconciler.py
├── order_reconciler.py
├── position_reconciler.py
└── recovery_trigger.py
```

5 modules. **C'est rare en crypto retail.** La plupart des projets n'ont aucune couche de reconciliation et confondent état local avec état exchange.
- `order_reconciler` : compare ordres locaux vs ordres exchange
- `fill_reconciler` : compare fills locaux vs fills exchange
- `position_reconciler` : compare positions locales vs positions exchange (la **source of truth**)
- `divergence_classifier` : classe les divergences (timing, amount, missing, extra)
- `recovery_trigger` : déclenche les actions de recovery

**À vérifier en S5a** :
- Cette couche est-elle appelée **au boot** du process (obligatoire) ?
- Est-elle appelée **périodiquement** (ex: toutes les 5 min) ou seulement réactivement ?
- Si elle ne tourne qu'en réactif, c'est un trou (P1).

### 3.5 Autres modules execution

- `venue_constraints_provider.py` — contraintes par venue (minNotional, stepSize, lotSize, max orders/sec)
- `execution_runtime.py` — orchestrateur

**À vérifier en S5a** : `execution_runtime.py` invoque-t-il un adapter exchange concret quelque part, ou est-ce purement abstrait ? Si abstrait, **l'adapter Binance Spot reste à coder en P0** — voir `03_GAPS_P0.md`.

---

## 4. Engines — 4 stratégies, 2 niveaux de maturité

Localisation : `src/engines/`

```
engines/
├── engine_a/    [legacy profile label: LIGHT, mature]
├── engine_b/    [legacy profile label: LIGHT, mature]
├── engine_c/    [legacy profile label: COMPLETE, monolithique, sous-testé]
└── engine_d/    [legacy profile label: COMPLETE, monolithique, sous-testé]
```

### Engine A (mature)

Modules visibles :
- `engine_a_runtime.py`
- `engine_a_runner.py`
- `invalidation_mapper_a.py`
- + scoring_router, conviction_builder, etc.

**~67 tests** d'après audit S2/S3.

### Engine B (mature)

Modules visibles :
- `engine_b_runtime.py`
- `engine_b_runner.py`
- `conviction_builder_b.py` (vérifié : utilise `absorption_score`, `book_imbalance`, etc.)
- `invalidation_mapper_b.py`
- `excess_detector_b.py`
- `cost_feasibility_b.py`
- `anti_breakout_filter_b.py`

**~70+ tests**.

### Engine C (sous-testé)

- `engine_c_runtime.py`
- `engine_c_runner.py`

**~7 tests** d'après audit S3. Ratio 1:10 vs A/B. **Risque P0/P1 — voir `03_GAPS_P0.md`.**

### Engine D (sous-testé)

- `engine_d_runtime.py`
- `engine_d_runner.py`

**~7 tests**. Même problème qu'engine_c.

> **NOTE doctrinale** : la convention V5.3 distingue encore des labels de profil **LIGHT** et **COMPLETE** pour certaines surfaces moteur et artefact. Il ne faut pas lire ces labels comme les étapes du rail runtime. Le rail gouverné reste `LOCAL_REPLAY -> SHADOW -> MICRO_LIVE -> LIVE`, et `live_light_runtime.py` est un nom de fichier legacy pour la phase `LIVE`.

**Verdict engines** : ★★★☆☆. A et B sont solides. C et D sont à durcir avant tout live (P0). Voir `03_GAPS_P0.md` section "Engine C/D rattrapage".

---

## 5. Scoring backbone

Localisation : `src/scoring_backbone/`

Modules notables vus en grep :
- `scoring_runtime.py`
- `hard_block_gate/blocker_evaluator.py`
- `hard_block_gate/blocker_registry.py`
- `ranking_router/portfolio_compatibility_checker.py`

**Hard block gate** : fait des blocages durs avant que le scoring final s'applique. C'est le bon endroit pour brancher un futur **sharia hard block** (refus pair non-halal avant scoring) — voir `03_GAPS_P0.md`.

---

## 6. Portfolio + Meta

### `portfolio_minimal/`

```
portfolio_minimal/
├── allocation_router/
│   ├── phantom_trade_guard.py     [protection anti-fantôme]
│   └── portfolio_cap_applier.py
├── opportunity_selector/
│   ├── candidate_pool_builder.py
│   ├── comparative_ranker.py
│   └── correlation_conflict_checker.py
└── portfolio_orchestrator.py
```

**Existe et fonctionne**. C'est le canon V5.3.

### `portfolio/` (STUB)

⚠ S2 finding : ce dossier existe mais est vide ou stub. **À supprimer ou clairement marquer comme deprecated** pour éviter la confusion avec `portfolio_minimal/`. P2.

### `meta_minimal/`

```
meta_minimal/
└── meta_runtime.py
```

Existe.

### `meta/` (STUB)

⚠ Même problème que `portfolio/`. À supprimer ou clarifier. P2.

### `meta_learning/` (~25 fichiers)

Fonctionnel. Modules notables :
- `facade.py`
- `merge_gates.py`
- `persistence_store.py`
- `contracts.py`

**À vérifier en S5a** : utilise-t-il **purged k-fold** ou un CV standard (qui a un look-ahead bias en séries temporelles) ?

---

## 7. Data backbone

Localisation : `src/data_backbone/`

Modules notables :
- `freshness_checker/stale_hard_guard.py` — refuse de trader sur de la donnée stale
- `consistency_checker/contradiction_checker.py` — détecte les contradictions inter-sources
- `rest_bootstrap/gap_fill_controller.py` — fill des gaps au démarrage
- `market_physics_math.py` — math features physiques

**Verdict** : ★★★★☆. Solide. Manque : alignement timestamp UTC strict + check anti-look-ahead. À vérifier en S5a.

---

## 8. Protocols — pipeline de promotion ✓

Localisation : `src/protocols/`

```
protocols/
├── shadow_runtime.py                [phase SHADOW]
├── micro_live_runtime.py            [phase MICRO_LIVE]
├── live_light_runtime.py            [phase LIVE, legacy filename]
├── shadow_day_counter.py
├── shadow_daily_orchestrator.py
├── shadow_report_builder.py
├── shadow_live_websocket.py         [WebSocket pour shadow]
├── shadow_websocket_ingest.py
├── shadow_vps_service.py
├── execution_runtime_bootstrap.py
├── engine_judgment_dashboard.py
├── contracts.py
└── ...
```

**~35 fichiers**. Pipeline 4-stages **codé**. C'est rare et c'est précieux.

**À vérifier en S5a** :
- `shadow_websocket_ingest.py` a-t-il une logique de **gap detection + REST replay** sur déconnexion ?
- Comment passe-t-on automatiquement de SHADOW à MICRO_LIVE (critères codés ou décision humaine ?)

---

## 9. Local replay runtime

Localisation : `src/local_replay_runtime/`

Modules notables :
- `replay_orchestrator.py`
- `replay_executor.py`
- `replay_metrics_collector.py`
- `historical_data_gateway.py`
- `shadow_execution_simulator.py`

**Pipeline backtest existant**. À vérifier en S5a : couvre-t-il les coins delisted (sinon survivorship bias).

---

## 10. Backtest artifact import

Localisation : `src/backtest_artifact_import/`

Modules :
- `export_dir_bridge.py`
- `upload_bridge.py`
- `migration` plus

**Pont entre artifacts produits localement et le système live**. À vérifier en S5a quels formats sont supportés.

---

## 11. Monitoring + Observability

Localisation : `src/monitoring/`

Modules notables :
- `metrics_collector.py`
- `monitoring_runtime.py`
- `alert_manager.py`
- `observability.py`
- `health_dashboard_backend.py`
- `technical_dashboard_backend.py`
- `build14_observation.py`
- `contracts.py`

**Verdict** : ★★★☆☆. La structure existe. **À vérifier en S5a** : `alert_manager.py` envoie où ? Webhook ? Telegram ? Stdout ? Sans push externe, tu ne sais pas quand le système trip → P1 (voir `04_GAPS_P1.md`).

---

## 12. UI

Localisation : `src/ui/`

Modules notables :
- `complete_dashboard_view.py`
- `technical_dashboard_view.py`
- `technical_dashboard_html.py`
- `ui_light_locked.py`

Dashboards techniques. À 10 k$ sur VPS sans desktop, l'UI est secondaire — un `health_dashboard` accessible par SSH tunnel suffit.

---

## 13. Smoke bootstrap recovery

Localisation : `src/smoke_bootstrap_recovery/`

Modules :
- `state_sanity_checker.py`
- + autres

**Recovery sur crash**. Critique pour VPS. Existe.

---

## 14. Complete enablers (Build-14)

Localisation : `src/complete_enablers/`

Modules notables :
- `lob_deep_filter_vwa.py` (vérifié : weak absorption component)
- + autres (Hurst, toxicity, etc.)

**Features microstructure avancées** consommées par les engines C/D.

---

## 15. Interface contracts — fondations

Localisation : `src/interface_contracts/`

Modules notables :
- `feature_lock_contracts.py` — **clé** : verrouille les features pour éviter le drift
- `artifact_contracts.py`
- `decision_contracts.py`
- `meta_contracts.py`
- `error_contracts.py`
- `numeric_contracts.py`
- `atomic_io.py` — write atomique disque

**Verdict** : ★★★★★. Fondations rares. C'est ce qui donne à V5.3 son auditabilité.

---

## 16. Manifest registry + DAG validator

Localisation : `src/manifest_registry/`, `src/dag_validator/` (présumé)

Modules notables :
- `build_order_registry.py`

**Gouvernance des artifacts et des manifests**. C'est ça qui permet au système de tracer "qui a produit quoi à partir de quoi".

---

## 17. Synthèse — score par dimension

| Dimension | Score | Commentaire |
|---|---|---|
| **Risk backbone** | ★★★★☆ | 5 dimensions de garde codées. Manque : DD daily wired au circuit_breaker. |
| **Execution backbone** | ★★★★☆ | Order lifecycle complet, reconciliation, fee meter. Manque : adapter exchange concret + fee-aware ex-ante gate. |
| **Engines** | ★★★☆☆ | A/B mature, C/D sous-testés. Risque P0/P1. |
| **Scoring backbone** | ★★★★☆ | Hard block gate codé. Bon point d'insertion sharia layer. |
| **Portfolio** | ★★★☆☆ | `portfolio_minimal/` OK, `portfolio/` stub à nettoyer. |
| **Meta learning** | ★★★☆☆ | Existe. Vérifier purged k-fold. |
| **Data backbone** | ★★★★☆ | Freshness + consistency + gap fill. Manque : check timestamp UTC strict. |
| **Protocols** | ★★★★★ | Pipeline 4-stages codé. Rare. |
| **Local replay** | ★★★☆☆ | Existe. Vérifier survivorship bias. |
| **Monitoring** | ★★★☆☆ | Structure OK. Manque : push alerting externe (Telegram). |
| **Smoke recovery** | ★★★★☆ | Codé. Critique pour VPS. |
| **Interface contracts** | ★★★★★ | Feature locks rares. C'est l'arme secrète de V5.3. |
| **Halal compliance** | ☆☆☆☆☆ | **Zéro fichier.** À écrire from scratch en P0. |
| **Exchange adapter concret** | ?☆☆☆☆ | Probablement zéro fichier. À vérifier en S5a + écrire en P0. |

### Score global production-readiness pour 10 k$ halal spot VPS

| Aspect | Score |
|---|---|
| Infra production (kill switch, recon, risk guards, fee meter, etc.) | **7.5 / 10** |
| Alpha-readiness (engines, scoring, meta) | **5 / 10** |
| Halal-readiness | **0 / 10** |
| 10 k$ -fitness (calibration small account) | **4 / 10** |

**Score global pondéré** : ~5/10. Bon socle, mais **non tradable telle quelle**.

---

## 18. Compatibilité avec la cible VPS Hetzner CX43

| Ressource VPS | Estimation V5.3 | Marge |
|---|---|---|
| **CPU 8 vCPU** | 1-2 vCPU effectif (engines + WS + reconciliation), pics à 4 lors de calibration locale | ✓ large |
| **RAM 16 GB** | ~1-3 GB stable (Python + WS buffers + dataframes en RAM) | ✓ large (5x marge) |
| **Disk 160 GB** | Artefacts + logs + snapshots ≈ 20-40 GB/an | ✓ ~4 ans avant compaction |
| **Trafic 20 TB/mois** | WS Binance ≈ 1-5 GB/jour = 30-150 GB/mois | ✓ très large |
| **Localisation EU** | Latence vers Binance ≈ 30-80 ms (Falkenstein → Tokyo via AWS) | ⚠ acceptable spot, KO pour HF |

**Conclusion** : V5.3 stack file-based fit largement sur CX43. Le seul point d'attention est la **latence Binance** (~50 ms moyenne EU→Tokyo). Pour du spot swing-trade c'est non-bloquant ; pour du HF/scalping ça serait disqualifiant — mais on ne fait pas de HF.

**Décision implicite** : on accepte une latence ≥ 30 ms et donc on **bannit toute stratégie qui dépend du tick-by-tick sub-second** (à confirmer dans `10_DECISIONS_REQUIRED.md`).

**Multi-VPS / failover** : pas dans ce plan. Single CX43 = single point of failure assumé. Mitigation : kill switch persistant + reconciliation au reboot + alerting externe (Telegram). Si Hetzner tombe complètement, le système se met en pause naturelle (pas de connexion exchange = pas de trades).

---

**Suite logique** : `03_GAPS_P0.md` — les 5 manques bloquants avant tout live trade.
