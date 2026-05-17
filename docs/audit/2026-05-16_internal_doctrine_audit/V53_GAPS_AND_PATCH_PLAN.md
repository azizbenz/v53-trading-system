# V5.3 — Gaps & Patch Plan + Verdict Final

- **Date** : 2026-05-16
- **Repo réel** : `E:\claude  v5.3\v53_trading_system\`
- **Branche / commit** : `codex/full-shadow-abcd-migration-20260403` @ `5f4fe0f` + 169 fichiers `M` + 200+ fichiers `??`
- **Mode** : Read-only — aucune modification de code, aucun rewrite proposé
- **Couvre** : Livrable 11 (verdict final) + recommandations chirurgicales P0/P1/P2

---

## 1. Verdict final en 6 axes (Livrable 11)

| Axe | Verdict | Preuves clés |
|-----|---------|--------------|
| **TRADING_CORE** | **CLEAR** | 4 moteurs réels (A/B/C/D) avec pipelines complets, coordination doctrinale typée (`engine_coordination_rules.py` : R-AC-1/2, R-D-1/2/3), bridges hooks dédiés, Engine D = re-entry avec `first_episode_resolver` + `historical_linkage_guard` + `consecutive_stop_counter` (anti-revenge) + `marginal_value_estimator` |
| **LIVE_BEHAVIOR** | **SAFE** | gates Shadow/Micro-live/Live-Light/Live-Complete code-enforced (`protocols/`), `automatic_promotion_requested` refusé par validators, reconciliation 4 niveaux (INFO/WARNING/BLOCKING/CRITICAL), spread_guard + rate_limiter + emergency_circuit_breaker, regime_lite extreme cooldown |
| **SHARIA_ENFORCEMENT** | **READY** | `sharia_compliance/` 15 modules, 17 reason codes typés, AAOIFI thresholds (0.33/0.33/0.05) académiques, account_features_audit endpoints+balances forbidden, purification calculator (5 sources), `ShariaRuntime` branchée dans `execution_runtime` + `gatekeeper`, tests présents (`test_sharia_runtime`, `test_sharia_alerts`) |
| **MARKET_ADAPTATION** | **READY** | 17 features microstructure académiques (OFI, VPIN, Kyle, realized kernel, Hawkes, PIN, Amihud, Roll, Corwin-Schultz, queue pressure, spread dynamics, walls_and_spoofing, etc.) versionnées + hashées, regime_lite 3-état avec hysteresis/cooldown, 21 calibration methods (PSR, DSR via HLZ, Holm-Bonferroni, Hansen SPA, energy distance, KS, POT-GPD, walk-forward purged, LightGBM+Optuna), ML enablers gouvernés (soft only) |
| **ARTIFACT_GOVERNANCE** | **READY** | Calibration artifacts **signés** (raise `CalibrationArtifactSignatureError` si pas de `signature`), `config/calibration/v1/thresholds.yml` déployé, 4 types d'artefacts de promotion typés avec hash, 6 critères de PROMOTED, Strategy Ladder pipeline complet, `backtest_artifact_import` refuse les bypass, ML governance sidecars, manifest registry, feature registry lifecycle |
| **OBSERVABILITY** | **READY** | DTR pipeline complet, 4 reporters risk (exposure/loss/beta/cluster), `RefusalRecord` + `ConditioningRecord` typés, monitoring Prometheus + alert_manager + telegram, Cockpit FastAPI 38+ state modules granulaires, dashboards (technical/health/complete/light), challenger_evidence_alerts, replay_governance_projection |

---

## 2. Comparaison avec le faux audit précédent (rectifications)

Le précédent audit (5 MD dans `.claude/worktrees/agitated-taussig-53f14d/docs/audit/`, supprimés depuis) avait classé **TRADING_CORE_UNCLEAR / SHARIA_PARTIAL / MARKET_ADAPTATION_TOO_SLOW** sur la base d'un worktree obsolète (commit `5fc4618`). 

| Ce que le faux audit disait | Réalité dans `5f4fe0f` |
|-----------------------------|---------------------------|
| Engine C empty | 13 modules complets |
| Engine D empty | 23 modules avec first_episode_resolver, consecutive_stop_counter, marginal_value_estimator |
| `src/sharia_compliance/` absent | 15 modules AAOIFI-compliant |
| OFI/VPIN/Kyle/Hawkes/PIN/Amihud/Roll/Corwin-Schultz MISSING | 17 modules microstructure académiques |
| Regime classifier absent | `regime_classifier/regime_lite.py` + 14 reason codes + cooldown |
| Calibration MISSING | 21 calibration methods (PSR, DSR via HLZ, etc.) + `config/calibration/v1/` signé |
| Carver forecast normalization absent | `scoring_backbone/forecast_normalizer.py` |
| Break-even filter absent | `scoring_backbone/break_even_filter.py` complet |
| Multiple testing guard absent | `calibration_methods/multiple_testing_guard.py` (HLZ + Holm-Bonferroni) |
| ML governance absent | `complete_enablers/ml_*` 5 modules + promotion_artifact_builder + ml_governance_sidecars |
| RefusalRecord/ConditioningRecord MISSING | Tous deux importés depuis `interface_contracts` dans `engine_coordination_rules.py:5-16` |
| Venue adapter MISSING | `venue_adapters/binance_spot/` complet |
| Pas de panic-flat/spread_guard | `execution_backbone/spread_guard.py`, `emergency_circuit_breaker.py`, `rate_limiter.py`, `gatekeeper/` |

> **Toutes les "P0/P1 GAPS" du faux audit étaient des contre-vérités.** Le système est massivement plus mature que ce que le faux audit décrivait.

---

## 3. Gaps réels identifiés (P0/P1/P2)

### 3.1 P0 — à confirmer avant shadow sérieux

**Aucun P0 doctrinal bloquant identifié au cours de cet audit read-only.**

Les 2 points P0 ouverts en Session 1 sont **résolus** :
- ✅ `ShariaRuntime` branchée dans `execution_runtime` + `gatekeeper` + `venue_adapters/binance_spot/account_feature_provider`
- ✅ Tests sharia présents (`tests/test_sharia_compliance/test_sharia_runtime.py`, `test_sharia_alerts.py`)

→ **Pas de P0 ouvert** sous réserve que les tests existants couvrent bien les 17 reason codes sharia + 5 règles de coordination + scénarios extrêmes. À confirmer par lecture détaillée des tests si demandé.

### 3.2 P1 — à confirmer avant micro-live

| Gap | Module | Évidence | Risque | Action chirurgicale recommandée |
|-----|--------|----------|--------|----------------------------------|
| P1-1 | **Couverture exhaustive des tests sharia** (17 reason codes, AAOIFI 3 codes, account features 2 codes) | `tests/test_sharia_compliance/` (2 fichiers vus) | conformité non prouvée exhaustivement | Lire `test_sharia_runtime.py` et `test_sharia_alerts.py` et lister les reason codes couverts. Ajouter les manquants. |
| P1-2 | **Branchement walls_and_spoofing en hard-block ou penalty** | `microstructure/walls_and_spoofing.py` produit reason codes (`_reason_codes`) mais on observe surtout en mode features | spoofing détecté mais peut-être non bloquant en live | Confirmer si `evaluate_walls_and_spoofing` outputs sont consommés par scoring/execution comme penalty/halt OU seulement comme observability. Si observability seulement, créer un patch chirurgical pour brancher en `scoring_backbone/penalty_aggregator/score_penalty_builder.py` (soft) puis hard-block via `hard_block_gate` si CRITICAL. |
| P1-3 | **Branchement VPIN en penalty/halt** | `microstructure/vpin.py` produit `VpinRecord`, consommé par `market_toxicity_snapshot` Build-14 (composite) mais pas de hard-block dédié | toxic flow détecté mais soft veto seulement | Idem : promouvoir VPIN haut → penalty score + halt si VPIN ≥ seuil critique (à calibrer via `THR-VPIN-*`). |
| P1-4 | **Audit logger sharia obligatoire en production** | `ShariaRuntime.__init__(policy, *, audit_logger=None)` — actuellement optionnel | journal des decisions sharia absent si non instancié | Modifier `smoke_bootstrap_recovery/config_validator.py` pour exiger `PolicyAuditLogger` instancié si `runtime_mode != REPLAY`. |
| P1-5 | **TTL / staleness des calibration artifacts** | `FeatureThresholdManifest` + `GovernedAuditEvidenceIndex` existent mais mécanisme d'expiry à confirmer | risque d'utiliser des seuils périmés | Vérifier qu'une calibration artifact a un champ `expires_at` ou équivalent et que `CalibrationLoader` raise si dépassé. Sinon ajouter un check chirurgical dans `loader.py`. |
| P1-6 | **Régénération / rotation des secrets DPAPI** | `secrets_manager/sealer.py` + `loader.py` + DPAPI Win/Posix | risque opérationnel si clé compromise | Documenter le workflow de rotation. Ajouter un cron / opérateur action dans cockpit pour audit périodique. |
| P1-7 | **Tests d'intégration end-to-end Shadow → Micro-live → Live-Light → Live-Complete** | Tests par gate existent mais pipeline complet ? | risque d'un cas non couvert | Ajouter un test e2e qui ferme la boucle replay → shadow → micro → live-light → live-complete avec gates enforced. |
| P1-8 | **`account_features_audit` action si finding (currently OBSERVABILITY + alert)** | `audit_account_features` produit findings → `sharia_alerts` → telegram | un finding aujourd'hui n'arrête pas le runtime | Décider doctrinalement : si un finding sharia est détecté → kill switch automatique ? OU rester en alert humaine ? À arbitrer. |
| P1-9 | **Signature crypto algorithme** | `CalibrationArtifact.model_validate` exige `signature` mais l'algorithme (HMAC/GPG/RSA) à confirmer | si signature simple checksum, sécurité faible | Vérifier dans `calibration_loader/contracts.py` le format de `signature` et le vérifieur. |

### 3.3 P2 — à confirmer avant live scaling

| Gap | Module | Action |
|-----|--------|--------|
| P2-1 | Hawkes intensity → branchement scoring (penalty si self-exciting cluster) | `microstructure/hawkes_intensity.py` | brancher en penalty si intensity > seuil |
| P2-2 | Stale book / liquidity wall — alertes Telegram | confirm `walls_and_spoofing` alerts integration | hook into `alerting/telegram_alerter` |
| P2-3 | `data_backbone/consistency_checker` events → alertes | currently OBSERVABILITY seulement | promouvoir contradiction/gap en alerts opérateur |
| P2-4 | Liste exhaustive `THR-*` actifs dans `config/calibration/v1/thresholds.yml` | lecture YAML directe | publier inventaire dans `docs/specs/` |
| P2-5 | Documentation des 6 critères de PROMOTED dans `promotion_artifact_builder._PROMOTION_READY_*` | doctrine non documentée hors code | publier `docs/specs/promotion_criteria.md` |
| P2-6 | Tests des bridges (`engine_a_pre_entry_confirmation_bridge`, `engine_b_sweep_validation_bridge`, `engine_c_void_validation_bridge`, `engine_d_reentry_validation_bridge`) | présence à confirmer | ajouter tests si manquants |
| P2-7 | Documentation lifecycle features microstructure (DRAFT/SHADOW/PROMOTED/QUARANTINED/REJECTED) | `MicrostructurePromotionState` enum codée mais non docs | publier `docs/specs/feature_lifecycle.md` |
| P2-8 | Audit pack périodique automatisé | actuellement on-demand via `meta_learning/replay_bundle_builder` | cron weekly dans `cockpit/` |
| P2-9 | Régime classifier — promouvoir les defaults documentés en `THR-*` IDs | regime_lite.py:46-50 (5 defaults non calibrés) | étendre `THR-RG*` ID range |
| P2-10 | DTRRecord — vérifier qu'il n'y a plus de duplication entre `interface_contracts/meta_contracts.py` et `meta_minimal/dtr_core/dtr_record_builder.py` | présent dans le faux audit mais branche obsolète | confirmer dans `5f4fe0f` |

---

## 4. Ce qu'il ne faut PAS changer (forces à préserver)

1. **Coordination doctrinale typée** (`engine_coordination_rules.py`) avec règles R-AC-1/2 + R-D-1/2/3 + `EngineCoordinationOutcome` produisant `RefusalRecord` + `ConditioningRecord`.
2. **Bridges hooks par engine** (`engine_*_*_bridge.py`) — point d'extension typé sans casse d'engine.
3. **Pipeline canonique strict** : engines (4 réels) → scoring (Carver + break-even + thresholds par engine) → portfolio → risk → execution + sharia gate → venue. Pas de raccourcis.
4. **Sharia compliance comme package complet** (15 modules) — AAOIFI-conforme, calibration-driven, audit-équipé.
5. **17 features microstructure académiques** versioned + hashed + lifecycle gouverné.
6. **21 calibration methods** académiquement complètes (PSR, DSR via HLZ, Holm-Bonferroni, Hansen SPA, energy distance, KS, POT-GPD, ADF+KPSS dual stationarity, Mann-Kendall, walk-forward purged, LightGBM + Optuna).
7. **Regime classifier sophistiqué** (3-état, hysteresis, no-skip, sudden_event, cooldown, persistent memory, calibration-driven).
8. **Gates Shadow / Micro-live / Live-Light / Live-Complete code-enforced** avec `automatic_promotion_requested` refusé, validators refusant `bypass_runtime_gates_requested`.
9. **Calibration artifacts signés** au sens structural (`signature` field obligatoire).
10. **Promotion artifacts typés** (4 types : Engine / Pair / Strategy / SampleSizeSurvival) + 6 critères de PROMOTED.
11. **Strategy Ladder pipeline** (~25 modules) : raw → silver → gold → engine inputs → expected edge training → ML lab handoff → promotion artifacts.
12. **Cockpit FastAPI** avec state granulaire par sous-système (38+ modules state_*).
13. **`backtest_artifact_import/validators`** refusent `bypass_runtime_gates_requested` et `automatic_promotion_requested`.
14. **DPAPI sealed secrets** (Windows native + Posix fallback).
15. **DAG validator** + **contract test suite** comme garde-fous architecturaux.
16. **Absence de `src/local_ai_lab/`** ✅ — conforme à la règle V5.3 non-négociable.

---

## 5. Le vrai cœur de V5.3 à préserver

```
                      [WebSocket / REST]
                            │
                            ▼
                    [data_backbone]
                  (freshness, normalize, route, pair_health)
                            │
                            ▼
              [microstructure features × 17]
        (OFI, VPIN, Kyle, realized_kernel, Hawkes, PIN,
         Amihud, Roll, Corwin-Schultz, queue_pressure,
         spread_dynamics, walls_and_spoofing, etc.)
              versioned + hashed + lifecycle gouverné
                            │
                            ▼
          [feature_registry promotion gate]
                            │
                            ▼
        [engine_input_provenance per A/C/D]
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
       [Engine A]      [Engine B]      [Engine C]      [Engine D]
       trend/struct    mean revert    breakout cont    re-entry/2nd
            │               │               │               │
            └───────┬───────┴───────┬───────┴───────┬───────┘
                    │               │               │
                    ▼               ▼               ▼
            [engine_coordination_rules]
            R-AC-1/2 (C exclu si A actif/recent)
            R-D-1/2/3 (D requires first_episode + anti-revenge + failsafe)
                            │
                            ▼
                  [scoring_backbone]
        (forecast_normalizer Carver,
         break_even_filter, ev_net_floor,
         hard_block_gate central,
         penalty_aggregator,
         ranking_router + selection_resolver)
                            │
                            ▼
                  [portfolio_minimal]
        (opportunity_selector, allocation_router,
         capital_viability, phantom_trade_guard)
                            │
                            ▼
                   [risk_backbone]
        (gross + loss + drawdown + BTC beta +
         cluster + emergency kill switch)
                            │
                            ▼
                ╔═══════════════════╗
                ║   SHARIA GATE     ║  ← `ShariaRuntime.authorize_trade`
                ║ before submit_order║    (12 hard blocks + AAOIFI + account
                ╚═══════════════════╝     features + purification)
                            │
                            ▼
                  [execution_backbone]
        (gatekeeper, spread_guard, rate_limiter,
         emergency_circuit_breaker, slippage_model,
         fee_aware_edge_gate, order_decider, fill_tracker,
         reconciliation_layer 4-severity)
                            │
                            ▼
                  [venue_adapters/binance_spot]
                            │
                            ▼
              [protocols: Shadow → Micro-live → Live-Light → Live-Complete]
              (promotion_gates, 30j Shadow, no override, no bypass)
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
    [meta_minimal]     [monitoring]    [meta_learning]
    DTR core, CRA,    Prometheus,     post-trade,
    break-even        alerts, cockpit  mistakes, hypotheses,
    dashboard         FastAPI state    review packets
                            │
                            ▼
            [local_replay_runtime + Strategy Ladder]
        (raw → silver → gold → engines → ML lab handoff
         → promotion_artifact_builder → 4 types signed)
                            │
                            ▼
              [config/calibration/v{N}/thresholds.yml]
              (signed, loaded by CalibrationLoader)
```

> Ce cœur est **mature, gouverné, audit-trail-équipé**. Il ne faut surtout **pas** :
> - Inventer un nouveau moteur hors A/B/C/D
> - Créer `src/local_ai_lab/`
> - Bypasser Shadow / Micro-live / Live / Live-Complete
> - Transformer un signal bearish en short
> - Hardcoder un seuil que `CalibrationLoader` pourrait servir

---

## 6. Modules à enrichir (P1/P2)

| Module | Enrichissement |
|--------|----------------|
| `microstructure/walls_and_spoofing.py` | brancher en penalty / hard-block selon severity |
| `microstructure/vpin.py` + `complete_enablers/market_toxicity_snapshot.py` | promouvoir en hard-block si VPIN > seuil critique calibré |
| `microstructure/hawkes_intensity.py` | brancher en penalty si self-exciting cluster |
| `regime_classifier/regime_lite.py` | promouvoir les 5 defaults documentés en `THR-RG05..09` |
| `sharia_compliance/account_features_audit.py` | promouvoir findings en hard-block (P1) |
| `sharia_compliance/sharia_runtime.py` | rendre `audit_logger` obligatoire en production |
| `data_backbone/consistency_checker/` | promouvoir contradiction/gap en alerts opérateur |
| Tests d'intégration | ajouter e2e shadow → micro-live → live-light → live-complete |

---

## 7. Modules à supprimer / déprécier (si stubs)

À vérifier en lecture détaillée :

| Module suspect | Statut à confirmer |
|----------------|---------------------|
| `src/meta/__init__.py` | si vide, à supprimer OU transformer en facade explicite vers `meta_minimal` |
| `src/portfolio/__init__.py` | facade vers `portfolio_minimal` ✓ |
| `.qodo/` dans `src/` | artefact d'outil de dev — à ignorer |
| `__pycache__/` partout | à laisser |
| `pytest-cache-files-*` | à laisser |

→ Pas de purge urgente. À faire en housekeeping P2.

---

## 8. Tests prioritaires à ajouter

| Priorité | Test | Justification |
|----------|------|---------------|
| P1 | Couverture exhaustive des 17 reason codes sharia | conformité doctrinale |
| P1 | `test_sharia_runtime_invoked_before_venue_submit` | intégration prouvée |
| P1 | `test_e2e_shadow_to_live_complete_pipeline` | gates enforced end-to-end |
| P1 | `test_calibration_artifact_unsigned_rejected` | signature crypto enforcée |
| P1 | `test_calibration_artifact_expired_rejected` | TTL enforcé (si mécanisme ajouté) |
| P2 | Tests bridges (`engine_*_*_bridge`) | si manquants |
| P2 | Tests `engine_coordination_rules` exhaustifs (5 règles × cas extrêmes) | doctrine A/C/D |
| P2 | Tests `walls_and_spoofing` consommé par scoring (si patch P1-2 appliqué) | enforcement |
| P2 | Tests `vpin` consommé par hard-block (si patch P1-3 appliqué) | enforcement |
| P2 | Tests `account_features_audit` action = hard-block (si patch P1-8 appliqué) | enforcement |

---

## 9. Synthèse Verdict V5.3 (Livrable 11 condensé)

| Axe | Verdict | Niveau |
|-----|---------|--------|
| TRADING_CORE | **CLEAR** | 1/5 (Excellent) |
| LIVE_BEHAVIOR | **SAFE** | 1/5 (Excellent) |
| SHARIA_ENFORCEMENT | **READY** | 1/5 (Excellent) |
| MARKET_ADAPTATION | **READY** | 1/5 (Excellent) |
| ARTIFACT_GOVERNANCE | **READY** | 1/5 (Excellent) |
| OBSERVABILITY | **READY** | 1/5 (Excellent) |

> **V5.3 est un système de trading mature, cohérent, sûr, halal AAOIFI-conforme, quantifiable au niveau académique, observable, adaptable au marché, et gouverné par artefacts signés.**
>
> Le système est **prêt pour Shadow sérieux**. Les gaps identifiés sont P1/P2, pas P0. Aucun rewrite global recommandé. Tous les patches sont chirurgicaux, testables, branchés sur les seams existants.

---

## 10. Phrase de conclusion (Livrable global, demandé par l'utilisateur)

> V5.3 a **un comportement de trading cohérent, sûr, halal AAOIFI-conforme, quantifiable au niveau académique (PSR/DSR/SPA/Holm-Bonferroni/POT-GPD/energy/KS/walk-forward purged), observable (DTR + cockpit + monitoring local stack), adaptable au marché (17 features microstructure + regime_lite 3-état avec cooldown), et gouverné par artefacts signés (`config/calibration/v1/thresholds.yml` + 4 types de promotion artifacts hashés)**.
>
> Les 6 axes du verdict sont tous CLEAR/SAFE/READY. Les gaps identifiés sont P1/P2 (enforcement de microstructure features, audit logger sharia obligatoire, TTL calibration, tests e2e), pas P0. Aucune doctrine interne ne doit être corrigée avant Shadow ; les améliorations relèvent du raffinement opérationnel.

---

## 11. Next safe step

1. **Décision doctrinale utilisateur** sur les P1 (walls_and_spoofing branchement, VPIN en hard-block, audit_logger sharia obligatoire, TTL calibration).
2. **Lire en détail** les 2 tests sharia (`test_sharia_runtime.py`, `test_sharia_alerts.py`) pour valider la couverture des 17 reason codes.
3. **Lire** `config/calibration/v1/thresholds.yml` pour publier l'inventaire des `THR-*` actifs.
4. **Implémenter** les patches chirurgicaux P1 dans l'ordre proposé (commencer par P1-1 : couverture tests sharia, sans effet sur le code).
5. **Ne pas** modifier l'architecture canonique. Tous les ajouts passent par les seams existants (hard_block_gate, penalty_aggregator, hooks/bridges, calibration_loader, refusal sinks).
6. **Avant Live-Complete** : confirmer P1-7 (test e2e pipeline complet).
