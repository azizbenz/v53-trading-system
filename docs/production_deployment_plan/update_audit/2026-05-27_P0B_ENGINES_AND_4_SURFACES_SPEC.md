# P0-B engines déblocage + branchement 4 surfaces restantes — Spec

**Date** : 2026-05-27
**Auteur** : Opus 4.7 (session Aziz)
**Statut** : Hand-off pour pilote Codex ou prochaine session Opus
**Bloque** : génération de THR-E01/E02 (donc S6 fee_aware_edge_gate) + montée à ~85-95% canonical sur 21 surfaces

---

## Contexte

À l'issue de la session 2026-05-27 :

| Item | Status |
|---|:---:|
| P0-WIRING-1 (runner B2 → audit reports) | ✅ |
| P0-COCKPIT-1 (card backbone parity) | ✅ |
| P0-COCKPIT-2 (per-surface breakdown + 6 metrics card) | ✅ |
| BACKTEST-RUN-PIN (selector Recent Jobs) | ✅ |
| P1 S1-S5 (5 surfaces canonical) | ✅ 137 PASS x5 |
| P0-RENAME-1 (ENGINE_NATIVE_RUNNER_NOT_INVOKED → B2_ENGINE_NATIVE_DECISION_REUSED_FROM_B1) | ✅ 130 PASS |
| P0-SPLIT-1 (B2_COST_MEASUREMENT_BLOCKED → 3 split variants) | ✅ 130 PASS |
| **P0-B engines déblocage** | ⏳ ce doc |
| **4 surfaces runtime data branchement** | ⏳ ce doc |
| S6 fee_aware_edge_gate (calibration THR-E01/E02) | ⏳ après P0-B |

Le run actuel `2df91d9d5c48dfbf` (388 records) montre :
- 100% hard_blocked
- 4 "exécutés" = 1 candidat × 4 buckets capital (bucket expansion)
- 1980 candidats × 1 = 0 trades vraiment générés

Pour produire **≥ 200 trades positifs** (pré-requis calibration THR-E01/E02), il faut débloquer le pipeline engines.

---

## Partie A — P0-B engines déblocage (chantier 3-5 jours)

### A.1 Engine A — `structure_unfavorable` (refuse 84.7% des candidates)

**Module** : [src/engines/engine_a/structure_detector_a.py:67-130](src/engines/engine_a/structure_detector_a.py:67)

**Formule actuelle** :
```python
score = (
    0.30 * abs(direction_strength)
    + 0.25 * continuation_score
    + 0.20 * quality_score
    + 0.10 * zone_score
    + 0.15 * stability_score
)
```

**Refus si** : `direction_strength < 0.20` OR `score < 0.30`

**Seuils** : tous marqués `ENGINE_A_STRUCTURE_CALIBRATION_STATUS="TO_CALIBRATE"`

#### Plan calibration A.1

1. **Diagnostic upstream** (1 jour)
   - Extraire la distribution de `direction_strength` sur les 1980 candidats du run
   - Si la majorité est < 0.20, le problème est **upstream** (features mal calculées, pas le seuil)
   - Si la distribution est saine mais le seuil 0.20 est trop strict, c'est un problème de calibration

2. **Calibration formelle Bailey-LdP** (1-2 jours)
   - Si distribution saine : utiliser le pattern `edge_gate_calibration.py:111` (stationary block bootstrap)
   - Cible : `direction_strength_p15` (15e percentile) avec floor humain `0.10` minimum
   - Produire artifact signé `config/calibration/v1/engine_a_structure.yml` avec `THR-EA01` (direction_strength_threshold) et `THR-EA02` (score_threshold)

3. **Câblage** (0.5 jour)
   - Modifier `structure_detector_a.py` pour lire via `CalibrationLoader`
   - Statut `ENGINE_A_STRUCTURE_CALIBRATION_STATUS="CALIBRATED_FROM_THR_EA01_EA02"`

4. **Validation** (0.5 jour)
   - Re-run B2 court (1j BTCUSDT 15m)
   - Cible : `structure_unfavorable` rate < 40% (vs 84.7%)
   - Aucune régression tests

#### Risques A.1

- ⚠️ Si la distribution réelle est dégradée (`direction_strength` toujours faible) → le problème est **dans le calcul des features**, pas le seuil
- ⚠️ Détendre le seuil sans calibration formelle = magic number → viole doctrine V5.3

---

### A.2 Engine B — `no_excess` (refuse 39% des candidates)

**Module** : [src/engines/engine_b/excess_detector_b.py:105-201](src/engines/engine_b/excess_detector_b.py:105)

**Logique actuelle** :
- `|z| > z_max` (4.0) → breakout → refus
- `|z| < z_marginal` (1.0) → insufficient → refus
- `z_marginal ≤ |z| ≤ z_star` (1.5) → faible signal → refus
- `z_star ≤ |z| ≤ z_max` → accepté

**Seuils** : `z_marginal=1.0`, `z_star=1.5`, `z_max=4.0` tous `TO_CALIBRATE`

#### Plan calibration A.2

1. **Diagnostic distribution `z`** (0.5 jour)
   - Extraire la distribution de `|z|` sur tous les candidats
   - Identifier modes : majorité < 1.0 (insufficient) OU majorité > 4.0 (breakout) ?

2. **Calibration formelle** (1-2 jours)
   - Pattern stationary bootstrap, percentiles cibles :
     - `THR-EB01` (z_marginal) = `p35` du `|z|`
     - `THR-EB02` (z_star) = `p55`
     - `THR-EB03` (z_max) = `p95`
   - Artifact `config/calibration/v1/engine_b_excess.yml`

3. **Câblage + Validation** (1 jour)
   - Cible : `no_excess` rate < 20% (vs 39%)
   - Tests régression verts

---

### A.3 Engine D — `closed_episode_count=0` (refuse 100%)

**Doctrine explicite** : Engine D **NEVER A PRIMARY ENTRY** — dépend `first_episode_ref` d'un trade A/C **exécuté**.

**Statut** : ce n'est PAS un bug — c'est la conception. Tant que A/C ne produisent pas de trades exécutés, D ne peut pas démarrer.

#### Plan A.3

Pas de calibration directe. Le déblocage de D est **automatique** dès que :
- Engine A passe ≥ 50 trades exécutés (A.1 livré)
- Engine C passe ≥ 50 trades exécutés (déjà 250 candidats sharia-rejetés, vérifier rate post-A.1)

#### Validation A.3

Re-run B2 post-A.1 + A.2 → vérifier `closed_episode_count > 0` apparaît sur D.

---

### A.4 `sample_cap_per_engine` (biais temporel — audit 2026-05-18)

**Documentation** : `memory/project_candidate_cap_temporal_bias_2026-05-18.md`

**Issue** : le sampling cap est `first-N post-tri` → biais chronologique vers le début de la fenêtre.

**Plan** (Option C du memory, 2 phases) :

1. **P0 fail-closed + métriques couverture** (0.5 jour)
   - Ajouter `sample_cap_temporal_coverage_pct` au manifest
   - Fail-closed si coverage < seuil

2. **P1 mode `TEMPORAL_STRATIFIED`** (1-2 jours)
   - Density 2 par jour/engine (couvre PSR ≥ 0.95 sur 30j evidence-grounded)
   - Floor 1, cap dur 5000

#### Validation A.4

Cible : couverture temporelle uniforme sur la fenêtre du run.

---

### Total A — effort + ordre

| Étape | Effort | Bloque |
|---|:---:|---|
| A.1 Engine A | 3 jours | A.3 (D), THR-E01/E02 |
| A.2 Engine B | 2.5 jours | THR-E01/E02 |
| A.3 Engine D | 0 (gratuit post A.1) | THR-E01/E02 |
| A.4 sample_cap | 2 jours | Robustness statistique |

**Total ~7-8 jours** pour atteindre ≥ 200 trades positifs et débloquer S6 calibration.

---

## Partie B — Branchement 4 surfaces runtime data

Ces 4 surfaces nécessitent **données runtime** (book, fill model, ML artifact). Pas un simple `default_factory` comme S1-S5.

### B.1 `adverse_selection`

**Module canonical** : `protocols.adverse_selection_meter`

**Dépendance** : book reconstruction temps réel (depth20 snapshots à intervalles courts)

**Source dans bucket** : déjà présent comme `adverse_selection_source` dans `parity_payload` (vu sur run 2df91d9d = `ADVERSE_SELECTION_CANONICAL_METER_BLOCKED_BY_DEPENDENCY`).

#### Plan B.1

1. **Diagnostic dépendance** (0.5 jour)
   - Identifier la dépendance bloquante (probablement `book_depth20_status != BOOK_DEPTH_AVAILABLE`)
   - Mapper le flow de données upstream

2. **Câblage** (1-2 jours)
   - Si la dépendance est book reconstruction → utiliser `book_depth_snapshot_count` + `book_depth_event_count` du parity_payload existant
   - Sinon → identifier le seam manquant

3. **Test** (0.5 jour)
   - Pattern S1-S5 : 137 PASS attendu

---

### B.2 `partial_fill_cost`

**Module canonical** : `execution_backbone.partial_fill_cost_meter`

**Statut actuel sur run** : `partial_fill_model_source = CANONICAL_PARTIAL_FILL_COST_METER` (déjà canonical à 100% !)

**Vérification nécessaire** : si déjà canonical au niveau source, pourquoi la surface est-elle FALLBACK ?

#### Plan B.2

1. Lire la résolution surface pour comprendre l'écart entre `partial_fill_model_source` (canonical) et `partial_fill_cost` surface (fallback)
2. Probable : la surface attend un payload spécifique non fourni par le meter
3. Câblage du payload manquant

**Estimation** : 1 jour.

---

### B.3 `fill_terminal_state`

**Module canonical** : `execution_backbone.fill_state_machine`

**Dépendance** : order lifecycle tracker (besoin du tracker B2)

**Statut** : `fill_realism_status = FILL_REALISM_BLOCKED_BY_MISSING_MEASUREMENT` (49.5% des records sur run actuel).

#### Plan B.3

1. **Diagnostic** : qu'est-ce que le state machine attend en input ?
2. **Câblage** : connecter le state machine au lifecycle existant
3. **Test** : 137 PASS

**Estimation** : 2-3 jours.

---

### B.4 `meta_learning_expected_edge`

**Module canonical** : `meta_learning.expected_edge_model_loader`

**Dépendance** : artifact ML produit par Lab (`F16-C` deliverable)

**Statut** : `expected_edge_model_status = EXPECTED_EDGE_ARTIFACT_NOT_DECLARED` (defaults).

#### Plan B.4

1. **Pré-requis** : Lab doit produire un artifact `.lgb` (training pipeline F16-C confirmé livré 2026-05-23)
2. **Loader path** : pointer `ShadowExecutionSimulatorConfig.expected_edge_training_artifact_ref` vers le path Lab
3. **Test** : artifact loadé, surface flippe CANONICAL

**Estimation** : 1-2 jours (dépend de la dispo d'un artifact Lab).

---

### Total B — effort + ordre

| Surface | Effort | Pré-requis |
|---|:---:|---|
| B.1 adverse_selection | 2-3 jours | book reconstruction OK |
| B.2 partial_fill_cost | 1 jour | (déjà canonical au niveau source) |
| B.3 fill_terminal_state | 2-3 jours | lifecycle tracker |
| B.4 meta_learning_expected_edge | 1-2 jours | artifact Lab dispo |

**Total ~6-9 jours** pour les 4 surfaces.

---

## Partie C — S6 fee_aware_edge_gate (dépend P0-B)

Une fois A.1 + A.2 + A.4 livrés (≥ 200 trades positifs) :

1. **Génération THR-E01/E02** (2-3h)
   ```python
   from local_replay_runtime.edge_gate_calibration import (
       calibrate_edge_gate_thresholds,
       build_edge_gate_calibration_artifact,
   )
   # records = load DTRRecord[] from run with ≥200 trades positifs
   report = calibrate_edge_gate_thresholds(records)
   artifact = build_edge_gate_calibration_artifact(
       report, signed_by="aziz.benz@gmail.com"
   )
   # Write to config/calibration/v1/edge_gate.yml
   ```

2. **Brancher S6** (30 min)
   - `replay_execution_contracts.py` : `fee_aware_edge_gate_config = Field(default_factory=FeeAwareEdgeGateConfig)`
   - Étendre `try/except` ligne 2074 de `shadow_execution_simulator.py` pour catcher `CalibrationArtifactValidationError` (défensif)
   - Test 137 PASS

3. **Validation** (1 run cockpit)
   - Cible : fee_aware_edge_gate canonical_pct = 100%

---

## Ordre d'exécution recommandé

```
Phase 1 (immédiat) :
├── A.1 Engine A diagnostic + calibration (3 jours)
├── A.2 Engine B diagnostic + calibration (2.5 jours)  ← peut paralléliser
└── A.4 sample_cap fail-closed P0 (0.5 jour)            ← peut paralléliser

Phase 2 (après run B2 avec ≥ 200 trades) :
├── C. THR-E01/E02 calibration (0.5 jour)
└── C. Brancher S6 fee_aware_edge_gate (0.5 jour)

Phase 3 (parallélisable avec 1 ou 2) :
├── B.2 partial_fill_cost (1 jour)         ← le plus simple
├── B.4 meta_learning (1-2 jours)
├── B.1 adverse_selection (2-3 jours)
└── B.3 fill_terminal_state (2-3 jours)

Phase 4 (validation finale) :
└── Run cockpit complet : cible 85-95% canonical sur 21 surfaces
```

**Total chantier** : ~15-20 jours de travail effectif (peut être réparti sur 3-4 semaines avec runs intermédiaires).

---

## Validation finale attendue

Sur un run B2 post-Phase 4 :

| Surface | Cible |
|---|:---:|
| fee_measurement | 100% canonical |
| cost_aggregation | 100% canonical |
| order_decision_reporting | 100% canonical |
| order_type_selection | 100% canonical |
| protocol_contracts | 100% canonical |
| venue_constraints | 100% canonical |
| complete_enablers_build14 | 100% canonical |
| hard_block_gate (S1) | 100% canonical |
| scoring_ranking (S2) | 100% canonical |
| regime_classification (S3) | 100% canonical |
| portfolio_state (S4) | partiel (besoin cluster_capacity) |
| risk_filter (S5) | 100% canonical sur rows avec execution_intent |
| **fee_aware_edge_gate (S6, post-Phase 2)** | **100% canonical** |
| **adverse_selection (B.1)** | **100% canonical** |
| **partial_fill_cost (B.2)** | **100% canonical** |
| **fill_terminal_state (B.3)** | **100% canonical** |
| **meta_learning_expected_edge (B.4)** | **100% canonical** |
| spread_measurement | conditionnel sur book |
| slippage_measurement | conditionnel sur book |
| execution_intent | conditionnel sur trade decision |
| data_backbone_market_microstructure | conditionnel sur book |

**Cible globale** : ≥ 17/21 surfaces 100% canonical sur les rows applicables = **~85-95% global**.

---

## Hors scope ce doc

- Migration shadow → micro-live → live (Gates Bailey-LdP/Talab)
- Multi-pair extension (single-pair BTCUSDT actuel)
- VPS deployment

---

## Références code

| Fichier | Rôle |
|---|---|
| `src/engines/engine_a/structure_detector_a.py:67-130` | A.1 formule + seuils TO_CALIBRATE |
| `src/engines/engine_b/excess_detector_b.py:105-201` | A.2 z thresholds TO_CALIBRATE |
| `src/local_replay_runtime/edge_gate_calibration.py:111-188` | Calibrator THR-E01/E02 (prêt) |
| `src/local_replay_runtime/shadow_execution_simulator.py:1428-1481` | Résolveurs surface |
| `src/local_replay_runtime/replay_execution_contracts.py:38-92` | ShadowExecutionSimulatorConfig (où brancher S6 et 4 surfaces) |
| `memory/project_candidate_cap_temporal_bias_2026-05-18.md` | A.4 analyse complète |
| `memory/project_p0b_engines_a_b_root_cause_2026-05-21.md` | A.1 + A.2 audit racine |
| `docs/white_book_FR_NOUVEAU_RAIL_BACKBONE_2026-05-27.md` | Vue d'ensemble nouveau rail |

---

**Fin du spec.**

Une fois ce chantier livré, le système V5.3 est prêt pour la transition Shadow → Micro-live → Live avec une convergence backtest/shadow/live > 95%.
