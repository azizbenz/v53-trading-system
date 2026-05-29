# White Book — Nouveau rail backbone du backtest V5.3

**Date** : 2026-05-27
**Auteur** : Opus 4.7 (session Aziz)
**Audience** : opérateur V5.3, futur toi qui revient sur le projet après une pause
**Statut** : livré ET câblé sur disque, validation cockpit pending

---

## 1. Contexte — pourquoi un "nouveau rail" ?

### 1.1 Le problème historique

Le backtest V5.3 (B2 = strategy ladder backtest) utilisait `local_replay_runtime` comme rail unique : un ensemble de modules dédiés au replay historique qui **dupliquaient** la logique métier des modules backbone canoniques (`execution_backbone`, `risk_backbone`, `scoring_backbone`, `portfolio_minimal`, `regime_classifier`, …).

Conséquence : ce que le backtest validait n'était **pas exactement** ce que shadow/live utiliseraient en production. Risque opérationnel : la PnL backtestée pouvait diverger de la PnL réelle simplement parce que les implémentations étaient différentes.

Quote utilisateur déclenchante :

> *« on a trouvé que le backtest n utiliser pas tt les module backbone de la solution on avait local replay qui n utiliser pas tte les cocuhe »*
>
> *« il y a deux rail le vieux local replay et il ya un nouveau ( surment il n est pas encore bronche a a1 ni b1 ni b2 ni...) »*

### 1.2 L'objectif du nouveau rail

Faire **converger** le backtest et shadow/live en remplaçant, surface après surface, les implémentations `local_replay_runtime` par les modules backbone canoniques. À la fin de la convergence, ce qui passe en backtest passera identiquement en shadow puis en live, et ce qui échoue ne traverse aucun gate.

### 1.3 Ce qui ne change PAS

- **La doctrine V5.3** : profils LIGHT/COMPLETE, engines A/B/C/D, gates Shadow→Micro-live→Live, fail-closed everywhere.
- **La philosophie de trading** : long-only crypto, indicateurs microstructure (OFI, VPIN, Kyle's lambda, queue pressure), pas de TA 1990s.
- **Le pipeline A1→A2→B1→B2→B_ML→IA Lab** : aucun module amont (silver/gold/training) n'est touché par les patches backbone.

---

## 2. Anatomie du nouveau rail

### 2.1 Vue d'ensemble

```
┌──────────────────────────────────────────────────────────────────┐
│  RUN B2 BACKTEST                                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  strategy_ladder_runner.py                                       │
│    │                                                             │
│    ▼                                                             │
│  strategy_ladder_detailed_replay.py  (per-row)                   │
│    │                                                             │
│    ▼                                                             │
│  replay_execution_runtime.py                                     │
│    │                                                             │
│    ▼                                                             │
│  shadow_execution_simulator.py                                   │
│    │                                                             │
│    │  ─── Per row, évalue 21 surfaces ──                         │
│    │                                                             │
│    ▼                                                             │
│  Chaque surface appelle le module BACKBONE canonique :           │
│    fee_aware_edge_gate   → execution_backbone/...                │
│    hard_block_gate       → scoring_backbone/hard_block_gate      │
│    scoring_ranking       → scoring_backbone/ranking_router       │
│    risk_filter           → risk_backbone/risk_runtime            │
│    portfolio_state       → portfolio_minimal/allocation_router   │
│    regime_classification → regime_classifier/regime_lite         │
│    … (15 autres)                                                 │
│                                                                  │
│  Pour chaque surface :                                           │
│    - Si module canonical invocable + données dispo → CANONICAL   │
│    - Si module canonical pas invocable → LOCAL_REPLAY_FALLBACK   │
│    - Si rien dispo → NO_SURFACE_RESULT_AVAILABLE                 │
│                                                                  │
│    Le résultat va dans `backbone_surface_report` du bucket       │
│    (PAS dans la décision trading — report-only).                 │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Les 4 modules clés

| Module | Rôle | Path |
|---|---|---|
| **Adapter** | Choix de la source (canonical vs local_replay) par surface, sans modifier la décision | `src/local_replay_runtime/backbone_parity_adapter.py` |
| **Audit** | Génère 14 reports JSON + 3 MD à la fin du run B2 | `src/local_replay_runtime/backtest_backbone_parity_audit.py` |
| **Simulator** | Évalue les 21 surfaces per-row pendant la simulation shadow | `src/local_replay_runtime/shadow_execution_simulator.py` |
| **Cockpit support** | Hydratation des champs pour le dashboard | `src/cockpit/runtime_support.py` |

### 2.3 Les 21 surfaces — taxonomie

| Catégorie | Surfaces |
|---|---|
| **Execution** | `fee_measurement`, `spread_measurement`, `slippage_measurement`, `cost_aggregation`, `partial_fill_cost`, `adverse_selection`, `fee_aware_edge_gate`, `fill_terminal_state`, `execution_intent`, `order_type_selection`, `order_decision_reporting`, `venue_constraints` |
| **Risk** | `risk_filter`, `portfolio_state`, `hard_block_gate` |
| **Scoring** | `scoring_ranking`, `meta_learning_expected_edge` |
| **Régime** | `regime_classification`, `data_backbone_market_microstructure` |
| **Build-14** | `protocol_contracts`, `complete_enablers_build14` |

---

## 3. Ce qui a été livré (2026-05-27)

### 3.1 Patches P0 — wiring + cockpit (livrés tôt dans la journée)

| Patch | Description | Fichiers |
|---|---|---|
| **BACKBONE-PARITY-WIRING-1** | Câbler le module audit (qui était présent mais non appelé) au runner B2 | `strategy_ladder_runner.py` |
| **BACKBONE-PARITY-COCKPIT-1** | Hydratation des champs dans `runtime_support.py` + carte dans `backtest.html` | `runtime_support.py`, `backtest.html` |
| **BACKBONE-PARITY-COCKPIT-2** | Tableau granulaire 21 surfaces dans la carte (livré juste après la demande utilisateur "il faut que ça remonte") | `runtime_support.py`, `backtest.html` |

### 3.2 Patches P1 — surfaces canonical S1 à S5

Pour chaque surface, on a remplacé le défaut `Field(default=None)` par un défaut canonical neutre. Tous les patches sont **report-only** au runtime — `evaluation.action` / `entries_blocked` / `capped.final_size` ne sont jamais propagés à la décision trading, ils ne sont que dans le `backbone_surface_report`.

| # | Surface | Défaut canonical | Impact trading | Tests cassés |
|---:|---|---|:---:|:---:|
| 1 | `hard_block_gate` | `BlockerCondition()` (tous flags False) | 🟢 nul | 3 |
| 2 | `scoring_ranking` | `RankingWeights()` (poids opérationnels) | 🟢 nul | 3 |
| 3 | `regime_classification` | `RegimeLiteThresholds.from_documented_defaults()` = doctrine THR-RG01..04 | 🟢 nul | 1 |
| 4 | `portfolio_state` | `PortfolioSnapshot(remaining_*_capacity=inf)` | 🟢 nul | 1 |
| 5 | `risk_filter` | `RiskLimits(*_cap=1_000_000)` | 🟢 nul | 3 |

**Régression cumulative** : 137 PASS après chaque patch (sur 6 fichiers : `test_shadow_execution_simulator.py`, `test_replay_execution_runtime.py`, `test_strategy_ladder_detailed_replay_fee_rates.py`, `test_backbone_parity_adapter.py`, `test_backtest_backbone_parity_audit.py`, `test_strategy_ladder_runner.py`).

### 3.3 Méthode safe validée

Pour chaque surface S_i :

1. Identifier le module canonical + sa classe de config (ex : `RiskLimits` dans `risk_backbone/risk_runtime_models.py`)
2. Vérifier que `_resolve_<surface>_resolution()` est **report-only** (= ne propage rien à la décision trading)
3. Choisir un défaut **neutre** :
   - Classmethod `from_documented_defaults()` si elle existe (cas S3)
   - Capacities `inf` si la classe a des sémantiques "capacity 0 = bloquer tout" (cas S4)
   - Caps neutres élevés (`1_000_000`) si la classe attend des seuils opérationnels (cas S5)
4. Patch `replay_execution_contracts.py` : `Field(default_factory=...)` avec un commentaire explicatif
5. Run pytest sur la suite des 6 fichiers
6. Updater 1 à 3 tests "old behavior" (assertions `LOCAL_REPLAY_FALLBACK_USED` → `CANONICAL_BACKBONE_USED`, ajustement `status_counts`)
7. Re-run pytest → 137 PASS retrouvé
8. Mémoriser le patch + son impact dans `memory/project_backbone_parity_post_codex_audit_2026-05-27.md`

### 3.4 État de la parité après S1-S5

Sur 21 surfaces × N records par run :

- **Pre-Codex audit** : 43.2% CANONICAL / 52.1% LOCAL_REPLAY_FALLBACK / 4.8% NO_SURFACE_RESULT
- **Après S1+S2** : 52.4% / 42.9% / 4.8%
- **Après S3** : ~57% / ~38% / 0-5% (selon dispo features upstream)
- **Après S4** : ~57% / ~38% / 0-5% (reason code shifted seulement)
- **Après S5** : ~62-67% / ~33-38% / 0-5% (risk_filter flippe CANONICAL sur rows avec execution_intent)

Le pourcentage exact dépend du run réel : Surface S3 (`regime_classification`) et S5 (`risk_filter`) flippent **conditionnellement** selon la disponibilité de données upstream (features microstructure pour S3, execution_intent non-None pour S5).

---

## 4. Ce qui reste (S6 + reste)

### 4.1 Surface #6 — `fee_aware_edge_gate` (bloquée)

**Statut** : NON branchée. Volontairement reportée.

**Raison** : la configuration `FeeAwareEdgeGateConfig()` pointe vers les calibrations `THR-E01` (edge multiplier) et `THR-E02` (min absolute edge bps), qui sont **absentes** de `config/calibration/v1/thresholds.yml`. Si on activait le défaut canonical maintenant, le simulator crasherait au premier row (`CalibrationArtifactValidationError` non catché par le try/except actuel qui ne catche que `ValueError`).

**Pre-requis pour brancher S6** :

| Étape | Détail | Bloqueur |
|---|---|---|
| 1 | Produire un governed B2 run avec ≥ 200 trades positifs exécutés | Engines A/B/C/D génèrent actuellement trop peu de trades (calibration P0-B pas finie) |
| 2 | Lancer `calibrate_edge_gate_thresholds(records)` ([edge_gate_calibration.py:111](src/local_replay_runtime/edge_gate_calibration.py:111)) | Méthode stationary block bootstrap, conservative upper CI bound |
| 3 | Écrire l'artifact YAML signé dans `config/calibration/v1/edge_gate.yml` | Pattern `signed_by` aligned avec `thresholds.yml` |
| 4 | Patch `replay_execution_contracts.py` : `fee_aware_edge_gate_config = Field(default_factory=FeeAwareEdgeGateConfig)` | Couplé à validation cockpit run |
| 5 | (Optionnel) Étendre le `try/except` ligne 2074 pour catcher aussi `CalibrationArtifactValidationError` | Défensif |

### 4.2 Surfaces encore 100% local_replay (post S1-S5)

| Surface | Module backbone cible | Pré-requis |
|---|---|---|
| `adverse_selection` | `protocols.adverse_selection_meter` | Book reconstruction temps réel |
| `partial_fill_cost` | `execution_backbone.partial_fill_cost_meter` | Fill model trained |
| `fill_terminal_state` | `execution_backbone.fill_state_machine` | Order lifecycle tracker |
| `meta_learning_expected_edge` | `meta_learning.expected_edge_model_loader` | Artifact ML loaded (lien F16) |

Ces surfaces dépendent de **données runtime** (book, fills, modèles ML), pas seulement d'une config — donc on ne peut pas les brancher avec un simple `default_factory`.

---

## 5. Guide de lecture du dashboard

### 5.1 Où la parité backbone apparaît dans le cockpit

**Page** : `http://127.0.0.1:8080/backtest`

**Card** : `#backtest-backbone-parity-card` (juste sous la card "Backtest Decision Report")

### 5.2 Anatomie de la card (post BACKBONE-PARITY-COCKPIT-2)

```
┌──────────────────────────────────────────────────────────────┐
│ Backbone Parity            [Badge: PARITY_CONFLICT ▼]        │
├──────────────────────────────────────────────────────────────┤
│ Overall verdict          | PARITY_CONFLICT                    │
│ Shadow/live parity       | B2_PARTIAL_BACKBONE_ADAPTER…       │
│ Total surface evals      | 7560                              │
│ Canonical                | 4536 (60.0%)                      │
│ Local replay fallback    | 3024 (40.0%)                      │
│ No surface result        | 0 (0.0%)                          │
├──────────────────────────────────────────────────────────────┤
│ Surfaces still using local_replay or proxy:                  │
│   - adverse_selection                                        │
│   - partial_fill_cost                                        │
│   - fill_terminal_state                                      │
│   - meta_learning_expected_edge                              │
├──────────────────────────────────────────────────────────────┤
│ ▼ Per-surface breakdown (21 surfaces)                        │
│                                                              │
│ Surface              | Status  | Cov. | Records | Reason     │
│ adverse_selection    | F       | 0%   | 0/360/0/360 | ADV_SEL_NOT_PROVEN
│ complete_enablers    | C       | 100% | 360/0/0/360 | CANONICAL_BACKBONE_USED
│ cost_aggregation     | C       | 100% | 360/0/0/360 | CANONICAL_BACKBONE_USED
│ data_backbone_market | F       | 51%  | 184/176/0/360 | DATA_BACKBONE_…
│ execution_intent     | C       | 53%  | 192/168/0/360 | CANONICAL_BACKBONE_USED
│ fee_aware_edge_gate  | F       | 0%   | 0/360/0/360 | FEE_AWARE_THR_NOT_CONFIGURED  ← S6 attendu
│ fee_measurement      | C       | 100% | 360/0/0/360 | CANONICAL_BACKBONE_USED
│ hard_block_gate      | C       | 100% | 360/0/0/360 | CANONICAL_BACKBONE_USED  ← S1
│ portfolio_state      | F       | 0%   | 0/360/0/360 | PORTFOLIO_CLUSTER_CAPACITY_MISSING  ← S4
│ regime_classification| ? cond. | ?%   | ?/?/0/360 | REGIME_CLASSIFIER_INPUTS_MISSING or CANONICAL  ← S3
│ risk_filter          | C       | 80%  | 288/72/0/360 | CANONICAL_BACKBONE_USED  ← S5
│ scoring_ranking      | C       | 100% | 360/0/0/360 | CANONICAL_BACKBONE_USED  ← S2
│ … (21 lignes au total)                                       │
│                                                              │
│ Legend: C=CANONICAL, F=FALLBACK, M=MISSING, Σ=total          │
├──────────────────────────────────────────────────────────────┤
│ ▼ Reports links (10)                                         │
│ - backbone_parity_audit: L:/output/.../backbone_…json        │
│ - backbone_parity_final_report: …                            │
│ - backbone_module_usage_matrix: …                            │
│ - … (7 autres)                                               │
└──────────────────────────────────────────────────────────────┘
```

### 5.3 Comment lire le badge "Dominant status" par surface

| Badge | Signification | Action |
|---|---|---|
| **CANONICAL_BACKBONE_USED** 🟢 | Le module backbone canonique a tourné, son résultat est dans le report. C'est ce qu'on veut. | Rien — la surface est ce qu'elle sera en shadow/live. |
| **LOCAL_REPLAY_FALLBACK_USED** 🟡 | Le canonical n'a pas pu tourner (config manquante, inputs manquants), local_replay a fourni un payload de fallback. | Lire `dominant_reason_code` pour savoir pourquoi. |
| **NO_SURFACE_RESULT_AVAILABLE** 🔴 | Ni canonical ni local_replay n'ont produit quelque chose. | Investiguer — donnée corrompue ou pipeline cassé. |
| **BACKBONE_LOCAL_REPLAY_PARITY_CONFLICT** ⚠️ | Les deux ont tourné mais ont produit des résultats différents. | Bug de convergence — ouvrir un ticket. |

### 5.4 Comment lire la coverage canonical (`Cov.`)

C'est le `%` de records pour lesquels la surface a réussi à utiliser le canonical. Cible doctrinale : **100% pour chaque surface activement convergée**.

Une coverage `< 100%` sur une surface canonical (statut `CANONICAL_BACKBONE_USED` dominant) signifie que sur certains records le canonical a échoué pour cause de données upstream manquantes. C'est normal pour `regime_classification` (features microstructure pas toujours fournies), c'est anormal pour `hard_block_gate` (config statique).

### 5.5 Comment lire le `dominant_reason_code`

Le reason code est la raison principale du statut dominant. Lexique :

| Code | Contexte | Signification |
|---|---|---|
| `CANONICAL_BACKBONE_USED` | status=CANONICAL | Le canonical a tourné, payload OK |
| `BACKBONE_CONTRACT_INCOMPLETE` | status=FALLBACK | Le canonical refuse de répondre car son contrat n'est pas satisfait |
| `REGIME_CLASSIFIER_INPUTS_MISSING` | regime_classification=FALLBACK | Les 4 metrics required ne sont pas dans les feature_values |
| `PORTFOLIO_CLUSTER_CAPACITY_MISSING` | portfolio_state=FALLBACK | Le mapping cluster_id → capacity n'est pas dans la snapshot |
| `RISK_FILTER_NOT_EVALUATED_WITHOUT_EXECUTION_INTENT` | risk_filter=FALLBACK | Le row n'a pas généré d'ordre, le risk filter n'a rien à évaluer |
| `FEE_AWARE_THR_NOT_CONFIGURED` (à venir post-S6) | fee_aware_edge_gate=FALLBACK | THR-E01/THR-E02 absents de la calibration |

---

## 6. Workflow d'opération — que faire à chaque run

### 6.1 Avant le run

1. Vérifier que tu es sur la branche `codex/full-solution-runtime-2026-05-17`
2. `python scripts/run_cockpit.py` → http://127.0.0.1:8080/lab pour configurer ML training si besoin
3. Lancer le backtest depuis http://127.0.0.1:8080/backtest

### 6.2 Pendant le run (≈ 15-20 min wall pour 1-2j BTCUSDT 15m)

Surveiller les cards :
- `Backtest Runner Coverage` — progression A1/A2/B1/B2
- `Backtest Decision Report` — apparaît quand B2 finit

### 6.3 Après le run

1. **Vérifier le badge global** de la card `Backbone Parity` :
   - 🟢 `BACKBONE_PARITY_OK` → tout est canonical → on est en convergence parfaite
   - 🟡 `PARITY_CONFLICT` → encore des surfaces fallback ou conflit → normal aujourd'hui (S6 pas branché)
   - 🔴 `BACKBONE_PARITY_NOT_AUDITED` → l'audit n'a pas tourné → pipeline cassé, voir logs

2. **Lire les compteurs agrégés** :
   - Target post-S1-S5 : Canonical ≥ 60%
   - Si < 50% : régression, ouvrir un ticket

3. **Lire le tableau par surface** (le nouveau, post-COCKPIT-2) :
   - Chercher chaque surface S1-S5 et vérifier `dominant_status == CANONICAL_BACKBONE_USED`
   - Les surfaces hors S1-S5 peuvent être FALLBACK — c'est attendu
   - Si une S1-S5 est passée FALLBACK : régression de config, voir `dominant_reason_code` pour la cause

4. **Vérifier la liste `Surfaces still using local_replay or proxy`** :
   - Attendu post-S1-S5 : `adverse_selection`, `partial_fill_cost`, `fill_terminal_state`, `meta_learning_expected_edge`, `fee_aware_edge_gate` (jusqu'à S6)
   - Si une autre apparaît : régression

5. **Vérifier le nombre de trades exécutés** (card `Backtest Decision Report`) :
   - Doit rester **identique** au run de référence pré-S1-S5 (≈4 sur le run `33a8593aca39312f`)
   - Si différent : impact trading non-anticipé d'un patch backbone, immédiatement investiguer

6. **Cliquer les 10 liens** "Reports links" pour explorer en détail si besoin :
   - `backbone_parity_audit.json` — résumé opérateur
   - `backbone_parity_final_report.json` — verdict + surfaces still local
   - `engine_native_runner_invocation_audit.json` — diagnostic engines
   - … etc.

### 6.4 Sanity checks doctrine (post Bailey-LdP / Talab)

À chaque run "production-ready" :
- ✓ Aucun secret committé (`.env`, credentials)
- ✓ Aucun threshold hardcodé (THR-* dans `config/calibration/v1/`)
- ✓ Quadruple filtre Talab respecté (sample size, multiple testing, capacity, regime)
- ✓ PSR/DSR Bailey-LdP ≥ doctrine (0.95)
- ✓ Refusal journal complet
- ✓ Run "BACKTEST_PROOF_RESEARCH_ONLY" jusqu'à shadow validé

---

## 7. Validation manuelle — checklist post-déploiement

### 7.1 Test 1 — pytest régression

```powershell
python -m pytest tests/test_local_replay_runtime/test_shadow_execution_simulator.py `
                 tests/test_local_replay_runtime/test_replay_execution_runtime.py `
                 tests/test_local_replay_runtime/test_strategy_ladder_detailed_replay_fee_rates.py `
                 tests/test_local_replay_runtime/test_backbone_parity_adapter.py `
                 tests/test_local_replay_runtime/test_backtest_backbone_parity_audit.py `
                 tests/test_local_replay_runtime/test_strategy_ladder_runner.py
```

Attendu : **137 PASS**.

### 7.2 Test 2 — pytest cockpit

```powershell
python -m pytest tests/cockpit/test_cockpit_server_routes.py `
                 tests/cockpit/test_backtest_decision_report_links.py
```

Attendu : **149 PASS, 1 FAIL** (le FAIL est `test_strategy_ladder_summary_separates_current_job_from_last_successful_b2`, dette technique pré-existante non liée).

### 7.3 Test 3 — visuel cockpit

1. `python scripts/run_cockpit.py`
2. Ouvrir http://127.0.0.1:8080/backtest dans le navigateur
3. Sans run B2 actuel, la card doit afficher `BACKBONE_PARITY_NOT_AUDITED` (pas crashé)
4. Lancer un B2 test (ex : 1j BTCUSDT 15m)
5. À la fin du B2, la card doit hydrater automatiquement (status_chip + 6 lignes du tableau agrégé + `Per-surface breakdown` avec 21 lignes)
6. Cliquer `Per-surface breakdown` pour expand/collapse — comportement HTML `<details>`

### 7.4 Test 4 — sanity check report disque

```powershell
$run_dir = "L:\output backtest\runs\strategy_ladder_workflow-<HASH>"
ls $run_dir\reports\backtest_backbone_parity_audit.json
ls $run_dir\reports\backtest_backbone_parity_final_report.json
ls $run_dir\detailed_replay\by_bucket\
```

Attendu : 14 JSON `*audit*.json` + bucket records avec `parity_payload.backbone_surface_report`.

---

## 8. Glossaire

| Terme | Signification |
|---|---|
| **Backbone canonical** | Le module "source de vérité" V5.3 qui sera utilisé en shadow/live. Doit converger avec backtest. |
| **Local_replay (vieux rail)** | Modules historiques dédiés au replay, qui dupliquaient la logique backbone. À retirer progressivement. |
| **Surface** | Une unité de logique (fee, risk, regime, …) évaluée per-row pendant la simulation. 21 surfaces dans V5.3. |
| **CANONICAL_BACKBONE_USED** | Statut "le canonical a tourné, son payload est dans le report". |
| **LOCAL_REPLAY_FALLBACK_USED** | Statut "le canonical n'a pas pu tourner, le local_replay payload remplit". |
| **NO_SURFACE_RESULT_AVAILABLE** | Statut "ni l'un ni l'autre n'a produit quelque chose". |
| **`promotion_allowed`** | Booléen : ce row peut-il participer à une promotion shadow→live ? Faux dès qu'une surface est en FALLBACK. |
| **`coverage_canonical_pct`** | % de records pour lesquels une surface donnée a réussi à utiliser le canonical. |
| **`dominant_reason_code`** | Le reason code le plus fréquent pour le statut dominant d'une surface. |
| **THR-E01 / THR-E02** | Seuils calibrés du fee-aware edge gate. Pas encore dans `config/calibration/v1/`. |
| **DTR record** | Decision Trade Record. Unité de log B2 utilisée pour calibrer les seuils. |

---

## 9. Roadmap court terme

| Priorité | Item | Effort |
|:---:|---|---|
| **P0** | Valider visuellement la card backbone parity sur un B2 réel (Test 3 + 4) | 1 run B2 + lecture cockpit |
| **P1** | Débloquer P0-B engines (`structure_unfavorable`, `no_excess`, calibration A/B/D) pour produire ≥ 200 trades | 3-5j chantier calibration |
| **P2** | Calibrer THR-E01 / THR-E02 via `calibrate_edge_gate_thresholds` une fois P1 fait | 1-2h |
| **P3** | Brancher S6 fee_aware_edge_gate + étendre try/except `CalibrationArtifactValidationError` | 1-2h après P2 |
| **P4** | Brancher les 4 surfaces restantes (adverse_selection, partial_fill_cost, fill_terminal_state, meta_learning_expected_edge) | Multi-session, dépend de données runtime |

---

## 10. Références code (à jour 2026-05-27)

| Fichier | Lignes-clés | Rôle |
|---|---|---|
| `src/local_replay_runtime/replay_execution_contracts.py` | 38-92 | `ShadowExecutionSimulatorConfig` avec tous les default_factory S1-S5 |
| `src/local_replay_runtime/shadow_execution_simulator.py` | 1290-1481, 2065-2192 | Résolveurs par surface + chaîne d'évaluation per-row |
| `src/local_replay_runtime/backbone_parity_adapter.py` | tout le fichier | `resolve_backbone_surface()` + statuts |
| `src/local_replay_runtime/backtest_backbone_parity_audit.py` | tout le fichier | Génération des 14 JSON + 3 MD |
| `src/local_replay_runtime/edge_gate_calibration.py` | 111-188 | Calibrateur THR-E01 / THR-E02 (prêt, en attente de données) |
| `src/cockpit/runtime_support.py` | 534-548, 2540-2670 | Hydratation cockpit + nouveau `per_surface_breakdown` |
| `src/cockpit/templates/pages/backtest.html` | 700-820 | Card "Backbone Parity" + tableau granulaire |

---

**Fin du white book.**

Pour toute question : relire d'abord la section pertinente, puis `memory/project_backbone_parity_post_codex_audit_2026-05-27.md` qui contient les détails verbatim de la session.
