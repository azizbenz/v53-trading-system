# P0-A — Décisions Verrouillées (Spec Finale)

**Date :** 2026-05-20
**Statut :** ✅ SPEC LOCKED — exécution prête à démarrer
**Documents parents :**
- [`2026-05-20_P0A_EXECUTION_PLAN.md`](2026-05-20_P0A_EXECUTION_PLAN.md) — méta-plan + 5 livrables
- [`2026-05-20_P0A_PHASES_DETAIL.md`](2026-05-20_P0A_PHASES_DETAIL.md) — détail phases

---

## RÉCAP DÉCISIONS (au 2026-05-20)

### Phase 1 — Préalables data
| Item | Choix verrouillé |
|---|---|
| Window | **δ — 6 mois** (`2025-02-01 → 2025-07-31`) |
| Pair scope | BTCUSDT (multi-pair = Phase future P3) |
| Effort | ~2-3h run A2 |

### Phase 2 — Build datasets training (4 timeframes)
| Item | Choix verrouillé |
|---|---|
| Target horizon | **15 min** (doc 21 §5 V5.3) |
| Walk-forward train days | **180** |
| Walk-forward validation days | **30** |
| Purge window | **= horizon** (15 min, Bailey-LdP anti-leakage) |
| Embargo window | **= horizon** (15 min, Bailey-LdP) |
| **Feature set** | **🔥 ENRICHI** : close_return, high_low_range, volume + VPIN + OFI + queue_pressure + spread_bps |
| Sample stride | **= horizon** (évite over-sampling séquences corrélées) |
| Timeframes | **1m, 5m, 10m, 15m** |
| Effort | ~1h |

### Phase 3 — Train 4 LightGBM models
| Item | Choix verrouillé |
|---|---|
| `max_optuna_trials` | **50** (~10-30min par tf) |
| Métrique Optuna | **RMSE default** (MAE robust outliers en fallback si distribution skewed) |
| Bagging folds | **5** |
| Early stopping rounds | **50** |
| Re-train train+val final | **Non** (best val checkpoint) |
| Seed | **42** (reproductibilité audit) |
| Effort | ~1-2h training total |

### Phase 4 — Wire models dans expected_edge_model_provider
| Item | Choix verrouillé |
|---|---|
| Cache booster | **LRU 10** (~500 MB max RAM) |
| Si model missing | **Fallback proxy** (continuité service) |
| Si feature mismatch | **Fail-closed + reason code `EXPECTED_EDGE_FEATURE_MISMATCH`** |
| Provenance chain ordering | **GOVERNED > MEDIAN > NAIVE > DEFAULT** (Patch 3) |
| Effort | ~1.3j code + tests |

### Phase 5 — Re-run B2 avec governed model
| Item | Choix verrouillé |
|---|---|
| Timeframes lancés | **4 (1m, 5m, 10m, 15m)** — pour livrable Comparison |
| Capital buckets | **[400, 500, 1500, 4000]** (default V5.3) |
| `candidate_discovery_mode` | **TEMPORAL_STRATIFIED** |
| `sample_cap_per_engine` | **2000** (sur 6 mois ≈ 333/jour/engine, large pour MinTRL) |
| Tagger evidence_class final | **AUDIT_VALIDATED** si tout OK |
| Effort | ~3-6h selon parallélisme |

### Phase 6 — Verdict + Comparison + Shadow plan
| Item | Choix verrouillé |
|---|---|
| `target_sharpe` doctrinal | **1.5** (modeste défendable crypto) |
| DSR trial_count | **mesuré depuis le run** (typiquement 3-12) |
| Verdict criteria | **PSR ≥ 0.95 ET DSR ≥ 0.95 (G2.3)** |
| Format verdict | **3-niveaux** (POSITIVE / NEGATIVE / INCONCLUSIVE) |
| Si INCONCLUSIVE (window) | **Re-lancer Phase 1 avec α (1 an)** — modèles entraînés réutilisables |
| Effort | ~1.5j code + synthèse |

---

## PRÉ-REQUIS A-F (verrouillés)

| Item | Décision | Détail |
|---|---|---|
| **A** | `sample_cap_per_engine` = **2000** | Sur 6 mois × 4 engines = 8000 candidats max ; cap réel selon TEMPORAL_STRATIFIED |
| **B** | P0-B **en parallèle** avec P0-A | Sinon `executed_count=0` garanti (Co-P0 doctrine Codex 2026-05-19) |
| **C** | F2 bronze gaps fix **AVANT** Phase 1 | Sur 6 mois bronze gaps risquent d'exploser → features contaminées |
| **D** | F4 metadata historique mode switch **AVANT** Phase 1 | Sinon fees 2026 appliquées sur replay 2025 = drift biais |
| **E** | Venue doctrine **Q1 — Bybit native pour P0-A + Binance shadow 30j post-promotion** | Continuer Bybit pour valider science, shadow Binance obligatoire avant live |
| **F** | F1 fingerprints **différé après P0-A** | Non bloquant, peut être fait en P1 cleanup |

---

## CHANTIERS COLLATÉRAUX VALIDÉS

### F16 — Validator features unlock (ACCEPTÉ)

**Décision :** débloquer F16 pour permettre feature set ENRICHI en Phase 2.

**Travail nécessaire :**
1. Identifier le validator V5.3 qui verrouille à 3 features (probablement dans `strategy_ladder_data_factory.py` ou `feature_threshold_manifest.py`)
2. L'étendre pour accepter `book_liquidity_features` + `flow_microstructure_features` groups
3. Tests régression sur features enrichies
4. Documenter décision doctrinale (raison du verrouillage P6 + raison du déblocage P0-A)

**Effort :** ~3-5 jours

**Risque :** le verrouillage à 3 features existait pour une raison doctrinale (P6 mémoire). Le déblocage doit être audit-trail explicite.

### F2 — Bronze gaps severity classifier (PRÉ-REQUIS Phase 1)

**Décision :** appliquer Patch 2 du plan de correction chirurgicale AVANT Phase 1.

**Travail :**
- [`silver_market_synchronizer.py`](../src/local_replay_runtime/silver_market_synchronizer.py) — ajouter `classify_bronze_gap_severity`
- [`data_science_quality_gates.py`](../src/local_replay_runtime/data_science_quality_gates.py) — consommer severity
- `config/calibration/v1/thresholds.yml` — seuils doctrinaux
- Tests

**Seuils verrouillés :**
- `bronze_gap_max_ms_research = 60_000` (1 min)
- `bronze_gap_max_ms_promotion = 5_000` (5 sec)
- `bronze_gap_count_max_per_day = 5`
- `stale_book_count_max = 0` pour promotion, illimité research

**Effort :** ~1j

### F4 — Metadata historique date-by-date (PRÉ-REQUIS Phase 1)

**Décision :** mode switch `LOCAL_METADATA_CACHE` → `BYBIT_PUBLIC_METADATA_FETCH` avec date résolution AVANT Phase 1.

**Travail :**
- Module [`bybit_historical_metadata.py`](../src/local_replay_runtime/bybit_historical_metadata.py) existe déjà
- Ajouter résolution date-by-date pour la fenêtre δ (6 mois 2025-02-01 → 2025-07-31)
- Cache local pour ne pas re-fetch à chaque run
- Tests

**Effort :** ~0.5j (module existe, juste mode switch + date param)

### P0-B — Fermer blockers ENGINE_NATIVE_NO_TRADE (PARALLÈLE Phase 1-5)

**Décision :** lancer P0-B en parallèle de P0-A.

**Sub-tasks P0-B :**
1. **engine_d `closed_episode_journal`** : générer journal valide (1000/1972 records bloqués sur ce blocker)
   - Option : cold-start synthétique OU bootstrap depuis runs précédents
   - Effort : ~1-2j
2. **engine_b `no_excess` (208/528)** : audit root cause — threshold trop strict ?
   - Effort : ~1j investigation
3. **engine_a `structure_unfavorable` (376/444)** : audit root cause — seuil structurel ?
   - Effort : ~1j investigation

**Effort total P0-B :** ~3-4j

---

## EFFORT TOTAL RÉVISÉ

| Catégorie | Effort |
|---|---|
| P0-A core (6 phases) | 6-7j |
| F16 unlock validator | +3-5j |
| F2 bronze classifier (pré-requis) | +1j |
| F4 metadata switch (pré-requis) | +0.5j |
| P0-B (parallèle) | +3-4j |
| **TOTAL** | **~13-17.5j** |

Note : parallélisme P0-B avec P0-A peut réduire ~3-4j sur le chemin critique.

---

## ORDRE D'EXÉCUTION (timeline)

```
J1      F2 bronze classifier (1j)              ─┐
J1.5    F4 metadata mode switch (0.5j)         ─┤── pré-requis Phase 1
J2-J6   F16 validator unlock (3-5j)            ─┘

[En parallèle :]
J1-J4   P0-B sub-tasks (3-4j)                  ── exécuté pendant que F16 tourne

────────── pré-requis clos ──────────

J6      PHASE 1 — A2 run 6 mois (2-3h)
J6      PHASE 2 — build 4 datasets (1h)
J6-J7   PHASE 3 — train 4 LightGBM (1-2h)
J7-J8   PHASE 4 — wire models (1.3j code + tests)
J8-J9   PHASE 5 — re-run 4 B2 governed (3-6h)
J9-J10  PHASE 6 — verdict + comparison + shadow plan (1.5j)

────────── 5 LIVRABLES PRODUITS ──────────
J10     Final delivery
```

**Total chemin critique : ~10 jours ouvrés** (avec P0-B en parallèle).

---

## LES 5 LIVRABLES FINAUX (chemins futurs)

| # | Livrable | Chemin futur |
|---|---|---|
| 1 | Final verdict | `docs/2026-06-XX_P0A_FINAL_VERDICT.md` |
| 2 | Comparaison 4 tf | `docs/2026-06-XX_P0A_TIMEFRAME_COMPARISON.md` |
| 3 | 4 modèles `.lgb` + manifests | `artifacts/expected_edge_models/expected_edge_<tf>.lgb` × 4 |
| 4 | Run audit-ready | `K:/v5.3 backtest/output2/runs/strategy_ladder_workflow-<P0A_ID>/` |
| 5 | Shadow 30j plan | `docs/2026-06-XX_P0A_SHADOW_30J_PROMOTION_PLAN.md` |

Schémas obligatoires de chacun : cf. [`2026-05-20_P0A_EXECUTION_PLAN.md`](2026-05-20_P0A_EXECUTION_PLAN.md) §2.

---

## CRITÈRES D'ACCEPTATION GLOBAUX

P0-A est COMPLET si et seulement si :

- [ ] Les 5 livrables existent sur disque
- [ ] `evidence_class: AUDIT_VALIDATED` ou `PROMOTION_GRADE` sur tous les artifacts du run
- [ ] PSR ET DSR ≥ 0.95 sur au moins 1 timeframe **OU** verdict explicite `INCONCLUSIVE` avec raison documentée
- [ ] Tous les hashes citables (run_id, dataset_hash, model_artifact_hash, git_commit)
- [ ] Reproductibilité : re-run du script verdict produit même résultat
- [ ] Shadow 30j plan exécutable sans questions ouvertes
- [ ] Si verdict POSITIVE : préparation Binance shadow plan activée (Q1 doctrine)
- [ ] Si verdict NEGATIVE : pas de bypass — V5.3 perd réellement, à investiguer
- [ ] Si verdict INCONCLUSIVE : décision explicite re-Phase 1 avec α (1 an)

---

## RISQUES IDENTIFIÉS

| Risque | Probabilité | Impact | Mitigation prévue |
|---|---|---|---|
| F16 unlock plus long que 5j | Moyenne | Décale tout le timeline | Buffer +2j dans estimation, fallback re-locker à 3 features |
| P0-B engine_d sans journal valide | Élevée | engine_d toujours bloqué | Cold-start synthétique fallback |
| Bronze gaps sur 6 mois explosent au-delà du seuil | Moyenne | Phase 1 fail-closed | Patch 2 thresholds ajustés OU revenir à fenêtre plus courte γ |
| Modèles ML overfit val sur 6 mois | Moyenne | Verdict positif faussé | Bagging 5 + early stopping + DSR final post-train |
| Co-P0 reste bloquant après P0-A + P0-B | Faible | Verdict INCONCLUSIVE | Diagnostic root cause supplémentaire requis |
| Disque K: insuffisant pour 6 mois data | Faible | Phase 1 échoue mid-run | Pré-vérification `df -h K:` ≥ 8 GB libre |

---

## STATUT ACTUEL (au 2026-05-20)

- ✅ Décisions verrouillées : toutes (25 décisions Phase 1-6 + 6 pré-requis A-F + F16)
- ✅ Spec écrite : ce document
- ❌ Code modifié : 0
- ❌ Runs lancés : 0
- ❌ 5 livrables produits : 0/5

---

## NEXT STEP IMMÉDIAT

**Démarrer en parallèle :**
1. **Patch 2 (F2 bronze classifier)** — 1j — pré-requis Phase 1
2. **Mode switch F4 (metadata historique)** — 0.5j — pré-requis Phase 1
3. **F16 validator unlock** — 3-5j — pré-requis Phase 2
4. **P0-B sub-tasks** — 3-4j — parallèle, débloque ENGINE_NATIVE_NO_TRADE

**Une fois F2 + F4 fermés (J1.5), Phase 1 (A2 run 6 mois) peut démarrer immédiatement.**

**Une fois F16 fermé (J6), Phase 2 peut démarrer avec feature set ENRICHI.**

---

## Citations utilisateur lors du verrouillage

- *« je choisis tes recomendation et je valides les 6 items A-F + tu confirmes que tu acceptes l'effort F16 (~3-5j de plus) pour bénéficier du feature set enrichi »*
- *« il faut tout garder sur md pour ne pas oublier »*

---

## Décision modèle (verrouillée 2026-05-20)

**✅ OPUS MAX pour TOUT P0-A** (chemin critique ~10j ouvrés).

**Justification :** 9 erreurs subtiles attrapées cette session par raisonnement profond (Codex Co-P0 correction, math SR=0.15 erreur, folklore industrie refuté, venue split caché, bronze gaps masqués, engine_c fausse alarme, expected_ce_net artefact mécanique, run_manifest zombie, F16 contrainte cachée). V5.3 = trading system production, coût erreur subtile asymétrique vs coût modèle.

Quote user verrouillage : *« max »*

---

**Document statut :** VERROUILLÉ 2026-05-20
**Modifications futures :** uniquement par re-décision utilisateur explicite, jamais par dérive silencieuse
