# 04_LOCAL_LAB_VPS_ARCHITECTURE

## Included Source Docs
- docs/production_deployment_plan/12_LOCAL_LAB_VS_VPS_SEPARATION.md
- docs/production_deployment_plan/15_LOCAL_LAB_INGESTION_DIAGNOSTIC.md
- docs/production_deployment_plan/16_VPS_LOCAL_OBSERVABILITY_ARCHITECTURE.md
- docs/production_deployment_plan/17A_BINANCE_SHADOW_POWERSHELL_BOOTSTRAP.md

---

## Source: docs/production_deployment_plan/12_LOCAL_LAB_VS_VPS_SEPARATION.md

# Local IA Lab vs VPS — Séparation des responsabilités

> **Statut** : fichier `12` du dossier `production_deployment_plan/`. Sa raison d'être est de **lever les blocages** explicitement listés dans :
> - `00_README.md` § 3bis
> - `07_PHASE_PLAN_0_TO_4.md` § 1.0
> - `09_CODING_SLICES_FOR_IMPLEMENTING_AGENT.md` § 1bis
> - `11A_DYNAMIC_THRESHOLDS_REPO_CROSSCHECK.md` § 5
>
> **Date** : 2026-04-09. Auteur : Opus en mode planification, suite à `local ia labs vps pour terminer la production plan de oupus.docx`.
>
> **Règle dure rappelée** : ce MD est un cadrage, pas une spec autoritaire. Le repo gagne contre le MD. L'agent codeur (Sonnet local) ne réorganise pas le repo à l'aveugle pour matcher ce fichier.

---

## 0. Format MD standardisé

Ce fichier suit le gabarit Opus défini en `00_README.md` § 0 :
- Objectif
- Périmètre
- Invariants
- Modules touchés
- Interfaces d'entrée/sortie
- Ce qu'il ne faut **pas** faire
- Critères d'acceptation
- Ordre de réalisation
- Preuves / tests attendus

---

## 1. Objectif

Définir, **sans inventer une nouvelle architecture**, la séparation entre :

1. **Local IA Lab** — environnement local de l'utilisateur (machine de R&D), où vivent : calibration, backtest, replay historique, stress test, production d'artefacts, signature humaine.
2. **VPS** — environnement Hetzner CX43 single-node, où vit **uniquement** le runtime trading (Shadow → Micro-live → Live), qui **consomme** des artefacts produits ailleurs.

Ce MD admet aussi un **concept futur borné** :
- plusieurs VPS peuvent exister comme **fleet passive**
- la vue flotte ne montre que des résumés `health / runtime_mode / artifact_version / alert_status / heartbeat`
- pour le détail complet, l'opérateur se **connecte à la VPS X** concernée ; la vue flotte ne remplace pas ce drill-down
- cette vue flotte reste **read-only** et n'orchestre pas les runtimes

Cette séparation est la précondition opérationnelle pour :

- pouvoir signer humainement les passages de phase (G2.1 → G2.2 → G2.3 → G3 → G4)
- pouvoir calibrer les seuils dynamiques sans toucher au runtime VPS
- pouvoir reproduire un run historiquement sans altérer la prod
- garder un coût infra borné (cf. `00_README.md` § 2 : 1.6 % du capital)

---

## 2. Périmètre

**Inclus** :
- la frontière logique Local IA Lab / VPS
- le flux d'artefacts entre les deux
- l'ownership des fichiers de calibration
- le partage `dashboards` entre les deux côtés
- le concept d'une **vue flotte multi-VPS read-only** limitée aux statuts synthétiques
- l'effet de cette séparation sur les MDs `00 → 11A` et sur les tranches `T1 → T13` + `W1 → W3` de `09_...`

**Hors périmètre** :
- toute topologie **multi-VPS active** (failover automatique, réplication, orchestration distribuée)
- toute création d'un package top-level `src/local_ai_lab` (interdit, voir § 7)
- toute création d'un control plane multi-VPS dans `src/` (interdit, voir § 7)
- toute refonte du rail existant `local_replay_runtime → governed export → backtest_artifact_import → VPS Shadow` (déjà vivant dans le repo)

---

## 3. Invariants

Ces invariants sont **non négociables** :

| # | Invariant | Pourquoi |
|---|---|---|
| INV-1 | Le VPS ne calibre rien. Le VPS ne fait que **consommer** des artefacts signés. | Sépare R&D et exécution ; protège le capital de toute boucle de calibration auto. |
| INV-2 | Aucun seuil n'est hardcodé dans le code VPS. Tout seuil vient d'un fichier de calibration signé. | Cohérent avec `11_DYNAMIC_THRESHOLDS_CATALOG.md`. |
| INV-3 | La signature humaine d'un artefact de calibration est **obligatoire** pour qu'il soit accepté côté VPS. | Bloque toute promotion silencieuse d'un seuil. |
| INV-4 | Le rail `local_replay_runtime → governed export → backtest_artifact_import → VPS Shadow` existe déjà et reste **canonique**. Ce MD ne le remplace pas. | Le repo gagne contre le MD. |
| INV-5 | Le runtime trading reste **single active VPS** dans ce plan. Une éventuelle vue flotte multi-VPS reste observatoire et read-only. | Évite la dérive vers une orchestration non cadrée. |
| INV-6 | Aucune création de package `src/local_ai_lab` ou de control plane multi-VPS **actif** dans `src/`. | Interdit explicitement par les system reminders et par `00_README.md` § 3bis. |
| INV-7 | Le passage Shadow → Micro-live → Live se fait via gates humains (`07_PHASE_PLAN_0_TO_4.md`), pas via promotion automatique. | Protège le capital. |
| INV-8 | Les artefacts de calibration sont **immuables** après signature. Toute modification = nouvelle version `calibration_vN+1.json`. | Audit-ready, pas de rewrite silencieux. |
| INV-9 | Une vue flotte multi-VPS ne montre que des statuts synthétiques. Le détail complet se consulte en se connectant à la VPS concernée. | Garde une frontière claire entre overview et diagnostic profond. |

---

## 4. Modules touchés

Aucun nouveau package n'est créé par ce MD. Les modules listés ci-dessous sont :
- soit **déjà présents** dans le repo et restent canoniques
- soit **déjà planifiés** dans `09_CODING_SLICES` (tranches T1→T13 + W1→W3)

| Côté | Module | État | Référence |
|---|---|---|---|
| Local IA Lab | `src/local_replay_runtime/` | exists | `09_...` W3 |
| Local IA Lab | `src/backtest_artifact_import/` | exists | `09_...` W3 |
| Partagé (shared core) | `src/calibration_loader/` | exists (W2 fermée) | `11A_...` § 6, `09_...` W2 |
| VPS | `src/venue_adapters/binance_spot/` | future target | `09_...` T1, T3, T4 |
| VPS | `src/sharia_compliance/` | future target | `09_...` T5 |
| VPS | `src/scoring_backbone/fee_aware_edge_gate.py` | exists | `09_...` T6 |
| VPS | `src/risk_backbone/loss_budgeter/*_breaker.py` | partial | `09_...` T10 |
| VPS | `src/regime_classifier/regime_lite.py` | partial | `09_...` T9 |
| VPS | `src/monitoring/disk_monitor.py` | partial | `09_...` T11 |
| VPS | `src/execution_backbone/reconciliation_layer/scheduler.py` | partial | `09_...` T10 |

**Point clé** : `src/calibration_loader/` est **shared core**, pas un package "Local IA Lab" ni un package "VPS". Il vit dans `src/` une seule fois et est utilisable des deux côtés. C'est cohérent avec `11A_...` § 6 et avec INV-6.

---

## 5. Frontière logique : qui fait quoi, où

### 5.1 Tableau de séparation

| Responsabilité | Local IA Lab | VPS |
|---|---|---|
| Replay historique de marché | OUI | NON |
| Backtest engines A/B/C/D | OUI | NON |
| Stress test (vol, gap, pannes WS, fees) | OUI | NON |
| Calibration des seuils dynamiques (`11_...`) | OUI | NON |
| Production d'artefacts `calibration_vN.json` | OUI | NON |
| Signature humaine d'un artefact | OUI (humain devant son terminal) | NON |
| Stockage long-terme d'artefacts (Git ou archive) | OUI | NON |
| Lecture d'un artefact signé | OUI (pour validation) | OUI (au boot) |
| Connexion live à Binance Spot | NON | OUI |
| Soumission d'ordres réels | NON | OUI |
| Réception WS / REST temps réel | NON | OUI |
| Reconciliation balances/positions | NON | OUI |
| Daily breaker / weekly breaker / monthly breaker | NON | OUI |
| Sharia compliance enforcement | NON | OUI |
| Telegram alerting | NON | OUI |
| Persistence des fills/decisions runtime | NON | OUI |
| Dashboards live (P&L, latence, fills) | NON | OUI |
| Dashboards calibration / R&D | OUI | NON |

### 5.2 Lecture en une phrase

- **Local IA Lab** : tout ce qui touche à la décision de **comment** trader (calibration, R&D, validation).
- **VPS** : tout ce qui touche à l'acte de **trader** maintenant (exécution, garde-fous, observabilité runtime).

---

## 6. Flux d'artefacts (Local IA Lab → VPS)

Le flux est **unidirectionnel** : Local IA Lab pousse, VPS tire et valide.

### 6.1 Pipeline standard

```
[Local IA Lab]
  1. local_replay_runtime  ──>  rejoue données historiques
  2. backtest produit     ──>  calibration_proposal_vN.json  (non signé)
  3. humain inspecte       ──>  diff vs calibration_v(N-1)
  4. humain signe          ──>  calibration_vN.json + calibration_vN.sig
  5. archivage Git/local   ──>  immuable
                         │
                         ▼ rsync/scp manuel ou pull cron
[VPS Hetzner CX43]
  6. calibration_loader    ──>  read + verify_signature
  7. fail-close si échec   ──>  pas de seuil, pas de trading
  8. runtime               ──>  consomme seuils via threshold_id
```

### 6.2 Règles du flux

| # | Règle | Conséquence |
|---|---|---|
| F-1 | Le VPS ne fait jamais de pull "best effort". Si la signature échoue, le runtime refuse de démarrer. | fail-close explicite |
| F-2 | Une calibration non signée ne **peut pas** être chargée sur le VPS, même en mode shadow. | bloque les régressions |
| F-3 | Un rollback de calibration = nouvelle version `vN+1` qui re-signe les anciennes valeurs. Pas de "git revert" silencieux. | audit trail propre |
| F-4 | La signature est **humaine** (pas une CI auto). Cela matérialise la décision en `10_DECISIONS_REQUIRED.md` D-08. | gate humain réel |
| F-5 | Le transport (rsync/scp/git pull) est **out-of-scope** de ce MD. Tout transport sain qui préserve l'octet-pour-octet et la signature convient. | évite la sur-spécification |
| F-6 | Le VPS garde l'historique des artefacts chargés (pas seulement le dernier) pour permettre l'audit post-incident. | requis par `08_RISK_REGISTER.md` |

### 6.3 Format minimal d'un artefact (rappel `11_...`)

```jsonc
{
  "artefact_version": "calibration_v3",
  "produced_at": "2026-04-09T14:33:00Z",
  "produced_by": "local_ia_lab/azizbez",
  "data_window": {"start": "...", "end": "..."},
  "thresholds": {
    "THR-E01": { "value": 2.1, "unit": "multiplier", "source": "backtest_run_id_42" },
    "THR-R01": { "value": -0.018, "unit": "ratio_of_equity", "source": "backtest_run_id_42" },
    ...
  },
  "signature": {
    "algorithm": "ed25519 | age | gpg",
    "signed_by": "human_operator",
    "signed_at": "2026-04-09T15:00:00Z",
    "signature": "..."
  }
}
```

Le **schéma exact** sera fixé par la tranche W2 (`src/calibration_loader/contracts.py`), pas par ce MD.

---

## 7. Ce qu'il ne faut **pas** faire

Ces interdictions sont reprises littéralement de `00_README.md` § 3bis et des system reminders. Elles restent valables après publication de ce MD `12`.

| # | Interdiction | Pourquoi |
|---|---|---|
| NO-1 | **Ne pas** créer de package top-level `src/local_ai_lab/`. | Le rail Local IA Lab vit déjà dans `src/local_replay_runtime/` et `src/backtest_artifact_import/`. Inventer un nouveau package éparpille la vérité. |
| NO-2 | **Ne pas** créer de control plane multi-VPS **actif** dans `src/`. | La vue flotte éventuelle doit rester read-only, sans piloter les runtimes. |
| NO-3 | **Ne pas** dupliquer `calibration_loader` côté Local IA Lab et côté VPS. Il vit une fois en shared core. | Cohérent avec INV-6 et `11A_...` § 6. |
| NO-4 | **Ne pas** coder un dashboard "final Local IA Lab" séparé du dashboard VPS dans le même repo runtime. Les deux dashboards peuvent exister, mais pas comme deux moteurs concurrents. | Évite la divergence Local/VPS. |
| NO-5 | **Ne pas** introduire de boucle automatique de re-calibration sur le VPS, même "soft". Toute re-calibration passe par Local IA Lab + signature. | INV-1, INV-3. |
| NO-6 | **Ne pas** assouplir un seuil sans nouvelle signature, même temporairement. Pas de "bypass d'urgence" silencieux. | Les bypass d'urgence sont décrits dans `10_DECISIONS_REQUIRED.md` D-14 et restent humains. |
| NO-7 | **Ne pas** interpréter ce MD comme l'autorisation de réécrire le rail `local_replay_runtime → governed export → backtest_artifact_import`. Ce rail existe et reste canonique. | INV-4. Le repo gagne. |
| NO-8 | **Ne pas** utiliser ce MD pour justifier un nouveau cycle de refactor du repo. Ce MD ne demande **aucun déplacement de fichier**. | Évite le churn. |

---

## 8. Dashboards : split fonctionnel sans split d'architecture

Ce MD ne prescrit **pas** deux moteurs de dashboard distincts. Il prescrit deux **vues** :

### 8.1 Vue VPS — "live monitoring"

- consommée pendant Shadow / Micro-live / Live
- montre P&L runtime, fills, latence WS, breakers, sharia status, regime label
- vit physiquement sur le VPS (HTTP local ou Telegram pour exposition externe)
- consomme uniquement les artefacts runtime (`fills`, `decisions`, `manifest`)

### 8.2 Vue Local IA Lab — "calibration / R&D"

- consommée par l'humain devant sa machine locale
- montre les diffs `calibration_v(N-1)` vs `calibration_vN`
- montre les distributions des seuils calibrés
- montre les résultats de backtest
- consomme les artefacts produits par `local_replay_runtime` et `backtest_artifact_import`
- vit sur la machine locale, pas sur le VPS

### 8.3 Vue flotte optionnelle — "health / status board"

- optionnelle, future, et **non bloquante** pour le plan courant
- peut lister plusieurs VPS par `vps_id`
- n'affiche que :
  - `health_status`
  - `runtime_mode`
  - `artifact_version`
  - `heartbeat_age`
  - `alert_state`
- ne montre pas les détails fins d'exécution, de fills ou de calibration
- pour le détail, l'opérateur ouvre la VPS concernée et consulte ses vues locales
- ne pousse aucun ordre, aucune calibration, aucune promotion

### 8.4 Règle de partage

Si la même librairie de rendu (par exemple un module `src/dashboards/`) est utilisée des deux côtés, c'est **acceptable**. Le critère est : aucune des deux vues ne doit pouvoir **piloter** l'autre. Le dashboard Local IA Lab ne pousse pas de seuils sur le VPS. Le dashboard VPS ne déclenche pas de re-calibration sur Local IA Lab.

---

## 9. Critères d'acceptation

Cette séparation est considérée comme "appliquée" quand :

- [ ] AC-1 : un artefact `calibration_vN.json` produit sur Local IA Lab peut être chargé par `src/calibration_loader/` côté VPS, signature vérifiée
- [ ] AC-2 : un artefact non signé est **rejeté** par `calibration_loader` avec une erreur explicite (fail-close)
- [ ] AC-3 : un artefact dont la signature ne correspond pas à la liste des signataires autorisés est **rejeté**
- [ ] AC-4 : aucun module sous `src/` n'a de seuil hardcodé issu de `11_...` (vérifié par `W1` cross-check + grep direct)
- [ ] AC-5 : `src/local_ai_lab/` n'existe pas (vérifié par `ls src/`)
- [ ] AC-6 : aucun module sous `src/` ne fait d'orchestration multi-VPS active ; toute vue flotte éventuelle reste read-only et synthétique
- [ ] AC-7 : le rail `local_replay_runtime → governed export → backtest_artifact_import → VPS Shadow` n'a **pas** été altéré pour appliquer ce MD
- [ ] AC-8 : les tranches `T1 → T13` et `W1 → W3` peuvent toutes citer ce MD `12_...` comme référence d'ownership des seuils, sans contradiction

**Aucune des AC ci-dessus ne demande un nouveau package, un nouveau service, ou un déplacement de fichier.**

---

## 10. Ordre de réalisation

Cet ordre est **logique** (dépendances), pas calendaire.

1. **Préalable déjà fait** : `W1` (cross-check) → `11A_...` publié.
2. **Préalable déjà fait** : `W2` (calibration_loader shared core) → fermé selon `09_...` § 1bis.
3. **Étape `12-A` — gel de la frontière documentaire** : ce fichier `12_...` est publié. À partir de maintenant, les autres MD peuvent y référer comme source d'ownership.
4. **Étape `12-B` — propagation dans `09_...`** : retirer la mention "interdit tant que `12_...` n'est pas publié" dans `09_...` § 1bis et `07_...` § 1.0. Les tranches `T1 → T13` peuvent citer `12_...` au lieu de "ownership à fixer plus tard".
5. **Étape `12-C` — validation par grep côté repo** : exécuter les checks d'AC-4, AC-5, AC-6 sur le repo réel. Tracer les éventuels écarts.
6. **Étape `12-D` — première utilisation réelle** : la première tranche P0 qui consomme un seuil dynamique (cible `T1` ou `T6`) charge un `calibration_v1.json` minimal signé.
7. **Étape `12-E` — gate humain Shadow 1m (G2.1)** : la signature de `calibration_v1.json` devient un prérequis explicite du gate.

**Étapes `12-A` à `12-C` ne sont pas du code runtime**. Ce sont du travail documentaire et des vérifications. Elles peuvent être faites par l'agent codeur sans toucher à `src/` (sauf pour le grep de contrôle).

---

## 11. Décisions humaines requises (rappel `10_...`)

Ce MD ne crée pas de nouvelle décision. Il **ancre** les décisions existantes dans une frontière physique :

| Décision | Localisation | Effet de ce MD |
|---|---|---|
| D-01 Exchange | `10_...` | confirme que la **connexion** vit côté VPS |
| D-04 VPS Hetzner CX43 | `10_...` | confirmé comme cible single-node |
| D-07 Validateurs des gates Shadow | `10_...` | les gates sont signés humainement, depuis Local IA Lab |
| D-08 Signataires des calibrations | `10_...` | la signature `calibration_vN.sig` matérialise D-08 |
| D-14 Plan d'urgence | `10_...` | aucun bypass automatique du flux d'artefacts, même en urgence |

---

## 12. Effets sur les autres MDs

Ce MD `12_...` **n'invalide** aucun MD précédent. Il **ferme** les notes d'attente.

| Fichier | Note d'attente concernée | Action après publication de `12_...` |
|---|---|---|
| `00_README.md` | § 3bis "ce qui reste bloqué jusqu'à `12_...`" | retirer le bullet `12_LOCAL_LAB_VS_VPS_SEPARATION.md` est encore absent et basculer la liste `Travail explicitement interdit` en "déjà arbitré dans `12_...`" |
| `07_PHASE_PLAN_0_TO_4.md` | § 1.0 contraintes intérimaires | renvoyer vers `12_...` § 7 (interdictions) au lieu de re-spécifier |
| `09_CODING_SLICES_FOR_IMPLEMENTING_AGENT.md` | § 1bis tranches `W1/W2/W3` autorisées en attendant `12_...` | conserver `W1/W2/W3` comme historique, mais le `tant que 12 n'est pas livré` peut être retiré |
| `11_DYNAMIC_THRESHOLDS_CATALOG.md` | "seuils calibrés où" implicite | référencer ce MD `12_...` comme la source d'ownership : "produit sur Local IA Lab, signé, consommé sur VPS via `calibration_loader`" |
| `11A_DYNAMIC_THRESHOLDS_REPO_CROSSCHECK.md` | § 5 "Ce cross-check n'autorise toujours pas..." | les 4 interdictions de `11A_...` § 5 sont **remplacées** par les `NO-1 → NO-8` de ce MD. `11A` peut renvoyer vers `12_...` § 7. |

**Important** : ces ajustements sont des **patches doc**, pas du code. Ils sont à appliquer en bloc cohérent quand `12-A` est validé.

---

## 13. Preuves / tests attendus

Aucun test runtime n'est demandé par ce MD seul. Les tests existent déjà ou existeront via les tranches référencées :

| Preuve | Source | Tranche |
|---|---|---|
| `calibration_loader` lit un artefact valide | `tests/test_calibration_loader/test_loader.py` | W2 (déjà fermée) |
| `calibration_loader` rejette un artefact corrompu | `tests/test_calibration_loader/test_loader.py` | W2 (déjà fermée) |
| `calibration_loader` rejette un artefact non signé | à ajouter dans W2 si manquant | W2 |
| `calibration_loader` rejette une signature inconnue | à ajouter dans W2 si manquant | W2 |
| Rail `local_replay_runtime` reste fonctionnel | `tests/test_local_replay_runtime/...` | W3 (en cours) |
| Aucune valeur seuil hardcodée dans `src/` | grep de contrôle (manuel ou CI) | `12-C` |
| `src/local_ai_lab/` n'existe pas | `ls src/` | `12-C` |

---

## 14. Suite logique

Une fois `12_...` publié et `12-A → 12-C` validés :

1. les tranches `T1` (Binance REST + time sync) et `T6` (fee-aware edge gate) peuvent démarrer en s'appuyant sur `calibration_loader` au lieu de hardcoder
2. la signature humaine de la première `calibration_v1.json` devient prérequis du gate `G2.1` (Shadow 1 mois) défini dans `07_PHASE_PLAN_0_TO_4.md`
3. la note d'attente `04_GAPS_P1.md` (patch encore en attente côté Opus) peut être appliquée puisqu'elle ne dépend plus de l'incertitude d'ownership

**Suite logique fichier** : pas de fichier `13_...` prévu pour l'instant. Le dossier `production_deployment_plan/` est **complet** côté plan, à l'exception des décisions humaines en attente listées dans `10_DECISIONS_REQUIRED.md`.


---

## Source: docs/production_deployment_plan/15_LOCAL_LAB_INGESTION_DIAGNOSTIC.md

# Local IA Lab Ingestion Diagnostic

> Status: diagnostic addendum to the production plan, based on the real repo as of 2026-04-10.
>
> Rule of truth: current code wins over planning docs.

---

## 1. Objective

Establish what the Local IA Lab already ingests from V5.3 today, what form that ingestion takes, and what is still missing before the loop becomes:

`post-trade diagnostic -> local recalibration -> signed artifact -> VPS import`

This file is diagnostic and planning-oriented. It does not authorize a new architecture.

---

## 2. Short answer

Yes, the Local IA Lab already ingests V5.3 evidence, but not as a raw live bidirectional VPS stream.

What exists today is a governed ingestion of:
- historical market snapshots for replay/backtest
- post-trade structured traces (`DTRRecord`)
- strategy/review bundles (`TradeLearningInput`, `LearningReviewExport`, `ReplayExportBundle`)
- governed replay sidecars (`review_export`, `parity_diagnostics`, `replay_metrics`, `replay_dtr`)

What does not exist today is:
- a live always-on VPS -> Lab raw snapshot feed
- an automatic recalibration loop running on the VPS
- a separate top-level `src/local_ai_lab` package

---

## 3. Code-confirmed ingestion surfaces

### 3.1 Historical snapshot ingestion

Confirmed in:
- `src/local_replay_runtime/historical_snapshot_loader.py`
- `src/local_replay_runtime/replay_event_router.py`

What this means:
- the Lab can already load raw historical market events from `.json`, `.jsonl`, and `.csv`
- those events are typed into `HistoricalSnapshotBatch`
- those batches are routed into normalized replay datasets for backtest/replay

This is the current historical market data ingress for the Lab.

### 3.2 Post-trade trade-level ingestion

Confirmed in:
- `src/interface_contracts/meta_contracts.py`
- `src/meta_learning/post_trade_diagnostic_engine.py`
- `src/meta_minimal/meta_runtime.py`
- `scripts/run_local_lab_post_trade_review.py`

What this means:
- the Lab already has a governed trade-level trace object: `DTRRecord`
- post-trade diagnostics are built from structured evidence, not from ad hoc logs
- the current diagnostic engine combines:
  - `TradeLearningInput`
  - `DTRSummary`
  - `CRAReport`
  - `BreakEvenReport`
  - `EdgeReport`
- the Lab now also has a bounded launcher that can ingest governed `replay_dtr.json/.jsonl`
  and rebuild:
  - `meta_runtime_result.json`
  - `meta_learning_review.bundle.json`
  - `meta_learning_review.md`
  - `meta_learning_projection.json`

This is already a real post-trade analysis path.

### 3.3 Strategy / review bundle ingestion

Confirmed in:
- `src/meta_learning/contracts.py`
- `src/meta_learning/review_orchestrator.py`
- `src/meta_learning/replay_bundle_builder.py`
- `src/meta_learning/facade.py`

What this means:
- the Lab already ingests a governed `TradeLearningInput`
- it already produces and manipulates `LearningReviewExport`
- it already produces `MetaLearningReviewBundle`
- it already prepares replay handoff bundles for candidate changes

So the Lab already has a strategy-level / review-level ingestion and analysis path.

### 3.4 Governed replay artifact ingestion

Confirmed in:
- `src/local_replay_runtime/replay_executor.py`
- `src/backtest_artifact_import/export_dir_bridge.py`

What this means:
- V5.3 already exports governed replay evidence:
  - `review_export.md`
  - `parity_diagnostics.json`
  - `replay_metrics.json`
  - `replay_dtr.jsonl`
- the bridge already reloads and validates those sidecars with typed contracts

So the Lab/VPS rail is already evidence-aware, not just file-copy based.

---

## 4. Correct interpretation

The current code supports this:

1. historical snapshots enter the Lab
2. replay/backtest produces structured evidence
3. meta-learning / post-trade diagnostics analyze that evidence
4. local calibration jobs can produce signed artifacts
5. VPS imports those artifacts and consumes them on the governed runtime rail

The current code does not support this:

1. VPS streams all live runtime snapshots back to the Lab continuously
2. the Lab auto-recalibrates the VPS in real time
3. a hidden control plane silently mutates runtime thresholds

So the current loop is governed and mostly one-way:

`historical/replay evidence -> Local IA Lab -> signed artifact -> VPS`

not:

`VPS live runtime -> raw continuous feedback -> automatic Lab control loop`

---

## 5. Implications for the plan

### 5.1 What should be strengthened next

The next Lab-centered slices should reinforce:
- post-trade diagnostic completeness
- replay/review bundle completeness
- local calibration producers
- signed artifact production
- governed artifact import on the VPS side

### 5.2 What should not be invented

The plan must not drift into:
- a fake live Lab/VPS message bus
- a second runtime hidden inside the Lab
- automatic VPS-side recalibration
- a new top-level `src/local_ai_lab`

---

## 6. Actionable next steps

### A. Planning

Keep this diagnostic as a truth anchor for future slices involving:
- meta-learning
- replay/backtest
- calibration
- artifact flow

### B. Coding

Prioritize slices that improve the real loop:

1. stronger post-trade diagnostics
2. stronger local calibration artifacts
3. runtime consumers of signed calibration artifacts
4. proof that the loop remains governed from Local IA Lab to VPS

Latest closure on point 1:
- `src/meta_minimal/meta_runtime.py` now exposes a public `DTR records -> MetaRuntimeResult` rebuild path
- `scripts/run_local_lab_post_trade_review.py` now provides a governed Local IA Lab entrypoint for post-trade review from exported replay DTR evidence
- the same launcher now also accepts a governed `export_dir` and recovers sidecar provenance through `discover_local_replay_export(...)`
- the launcher now emits a future-facing ingestion sidecar `governed_input_summary.json`
- the launcher now also emits `trade_loss_attribution.json` as the bounded per-trade explanation/suggestion surface
- this sidecar is the current Local IA Lab answer to:
  - why this trade lost
  - what should prevent the next similar loss
- `scripts/run_local_lab_analysis_bundle.py` now chains one governed `export_dir` into post-trade review + EDGE calibration + a single `local_lab_analysis_summary.json`
- the same chain now also emits a governed walk-forward human-review template/summary pair
- the same chain now also emits:
  - `artifact_proof_summary.json`
  - `artifact_proof_assessment.json`
- the same chain now also emits `artifact_ablation_study.json`
- with `--baseline-export-dir`, the Lab can now compare candidate vs baseline on aligned governed `DTRRecord` ids
- the proof layer can therefore consume real:
  - `ablation_delta_net_pnl`
  - `ablation_delta_ce`
  - `block_rate_delta`
  instead of keeping those dimensions permanently empty
- the same chain now also supports governed multi-scope analysis from one export:
  - `scripts/run_local_lab_analysis_bundle.py --all-scopes`
  - `src/local_replay_runtime/local_lab_scope_matrix.py`
  - `local_lab_scope_matrix.json`
- this lets the Lab analyze one multi-scope export as a bounded `pair x engine` matrix instead of forcing manual reruns scope by scope
- each scope now materializes its own governed sidecars under `output-root/scopes/<pair>__<engine>/`
- the matrix exposes future-dashboard-ready status per scope:
  - `artifact_ablation_ready`
  - `artifact_proof_ready`
  - `artifact_proof_validation_reasons`
- proof remains conservative in the multi-scope path:
  - scope-level `total_opportunities` is recomputed from scope evidence
  - walk-forward approval stays global/human-gated
  - no scope becomes `ready` without aligned baseline evidence
- the same chain now also emits `artifact_release_candidate.json`
- this is the current Local IA Lab packaging-side answer to:
  - is the current artifact still `local_only`
  - or can it become a governed `shadow_candidate`
  - and, if blocked, by which typed reasons
- this sidecar also projects per-scope release readiness when a multi-scope matrix exists
- the same chain now also emits a bounded governed dry-run bridge:
  - `artifact_import_dry_run_bridge.json`
  - `artifact_upload_request.dry_run.json`
  - `artifact_import_request.dry_run.json`
  - `artifact_import_decision.dry_run.json`
  - `artifact_upload_decision.dry_run.json`
- this new bridge reuses the existing `backtest_artifact_import` rail instead of inventing a parallel handoff path
- the bridge now makes the source/transport semantics explicit:
  - the Local IA Lab source artifact remains the calibration artifact (`edge_gate.yml`)
  - the current governed dry-run handoff still rides on a replay-derived transport packet of kind `review_packet`
  - the sidecar now exposes that duality instead of pretending both ids/kinds are the same artifact
- it stays fail-close:
  - no hidden governance date default
  - no silent artifact class/scope defaults
  - no dry-run payloads are materialized unless the release candidate is ready and the governance inputs are explicit
- important current limitation:
  - the bridge is still a dry-run/proof-packet handoff around the governed replay/import rail
  - it is not yet the final live packaging semantics for every future Lab-produced artifact
- this new proof layer is conservative by design:
  - it computes what the repo can already justify from current Local IA Lab evidence
  - it keeps non-proven dimensions fail-close instead of fabricating a passing proof
- doctrine now reflected in code:
  - walk-forward/backtest computation can stay automated
  - approval against leakage/overlap must remain human
  - `walk_forward_pass` must stay false until that human gate is approved

### C. Explicit non-goal

Do not build a live bidirectional Local IA Lab / VPS synchronization layer in the current perimeter.

---

## 7bis. Latest bounded handoff refinement

- the Local IA Lab chain now also emits `artifact_source_summary.json`
- this gives the future dashboard and audit tooling a stable source-artifact projection without changing the governed import rail
- the dry-run handoff still rides on a replay-derived `review_packet`
- but that transport packet now also carries:
  - the real Local IA Lab source artifact ref
  - the source summary ref
  - through `ArtifactPayloadRefBundle.supplementary_refs`
- this is the current truthful answer to:
  - how the Lab artifact relates to the current VPS import packet

---

## 7ter. Latest execution ingestion closure

The Local IA Lab execution-ingestion rail now goes beyond evidence transport and supports first bounded execution models on service-owned telemetry:
- `THR-X03` from quota probe telemetry + official quota cap
- `THR-X05` from service-owned `size/slippage` traces

Current truthful boundary:
- the bounded models exist on the Lab side
- the evidence remains service-owned and typed
- this still does not authorize any automatic VPS-side recalibration or live mutation
  - how future tooling can inspect that relation without inventing a new rail

## 7ter. Latest bounded recalibration planning refinement

- the same Local IA Lab chain now also emits `local_lab_recalibration_plan.json`
- this is the current Local IA Lab answer to:
  - which threshold families are recommended for recalibration from governed loss evidence
  - which cases must remain blocked because evidence is weak or scopes are not ready
- it stays local-only:
  - no VPS mutation
  - no direct artifact promotion
  - no bypass of replay/backtest/human review

## 7quater. Latest bounded provenance connection

- the EDGE producer now carries `local_lab_recalibration_plan.json` provenance through `edge_gate.input_summary.json`
- this means the Local IA Lab can now show, on the artifact producer itself:
  - which local plan triggered the refresh
  - whether recalibration was actually judged ready
  - which threshold ids were implicated
- this remains a local audit/provenance refinement, not a VPS-side mutation

## 7quinquies. Latest bounded release-gate projection

- the Local IA Lab handoff now projects its own release verdict explicitly in the dry-run bridge
- future tooling no longer needs to infer from separate sidecars whether a candidate is:
  - proof-backed
  - recalibration-backed
  - proof-backed with recalibration not required
- the current bridge now reports:
  - `release_gate_status`
  - `release_gate_reasons`
  - proof and recalibration readiness mirrors copied from the packaging verdict
- important invariant:
  - this is still a dry-run bridge over the current governed import rail
  - no VPS-side mutation or new artifact kind is introduced by this slice

## 7sexies. Latest bounded release-gate sidecar transport

- the same Local IA Lab handoff now also emits `artifact_release_gate_summary.json`
- that sidecar is now carried by the dry-run transport packet itself through `supplementary_refs`
- future tooling can now inspect, from the packet perimeter alone:
  - source artifact relation
  - source artifact summary
  - release-gate verdict summary
- important invariant:
  - this still does not create a live Lab -> VPS channel
  - it only makes the current dry-run handoff more self-describing and audit-ready

## 7septies. Latest bounded multi-scope release drill-down

- the Local IA Lab packaging verdict is now more self-contained for multi-scope exports
- `artifact_release_candidate.json` now carries per-scope drill-down refs and counts instead of only `pair/engine/release_ready`
- the top-level Local IA Lab summary now also exposes:
  - ready scope slugs
  - blocked scope slugs
- important invariant:
  - scope drill-down remains descriptive
  - it does not imply a new per-scope VPS import rail or per-scope live mutation path

## 7octies. Latest bounded per-scope release-sidecar transport

- multi-scope Local IA Lab runs now also emit one `artifact_release_scope_summary.json` per scope
- each sidecar binds together:
  - scope proof/review evidence
  - shared release verdict
  - shared dry-run handoff bridge
- important invariant:
  - this is still Local IA Lab packaging metadata
  - it does not create a new VPS-side import object per scope

## 7novies. Latest bounded scope-matrix packaging projection

- the Local IA Lab scope matrix now reflects both proof and release packaging status
- future tooling can now read from the same matrix:
  - proof-ready scope counts
  - release-ready scope counts
  - per-scope release blockers
  - per-scope release summary refs
- important invariant:
  - this is still a projection layer over the same Local IA Lab run
  - it does not introduce a second source of truth separate from the packaging sidecars

## 7decies. Latest bounded promotion-readiness summary

- the Local IA Lab handoff now also emits one top-level `artifact_promotion_readiness_summary.json`
- this summary bridges Local IA Lab packaging truth to canonical VPS-facing vocabulary:
  - activation stage
  - normalized promotion state
  - review state
- important invariant:
  - this is still not a promotion action
  - it is only an audit-ready summary over the same dry-run handoff rail

## 7undecies. Latest bounded Local IA Lab monitoring projection

- the same Local IA Lab handoff now also emits one compact `local_lab_monitoring_projection.json`
- this projection is intended as the stable future dashboard/monitoring surface over the same run
- it does not replace the detailed sidecars; it summarizes them
- current normalized fields include:
  - core analysis readiness
  - packaging / dry-run bridge truth
  - canonical promotion vocabulary already computed upstream
  - scope and release counts
- important invariant:
  - this remains a descriptive Local IA Lab sidecar only
  - it does not create UI coupling or any new VPS mutation path

## 7duodecies. Latest bounded Local IA Lab observability export

- the same Local IA Lab chain now also emits `local_lab_observability_export.json`
- this export reuses the repo standard `ObservabilityExport` shape instead of inventing a bespoke metrics file
- it provides:
  - numeric metric samples
  - a text-export payload for later ingestion
  - no UI coupling
- important invariant:
  - this stays descriptive over the Local IA Lab run
  - it is not a control plane and does not affect promotion/runtime behavior

## 7terdecies. Latest bounded Local IA Lab monitoring backend payload

- the same Local IA Lab chain now also emits `local_lab_monitoring_backend_payload.json`
- this payload is built from:
  - the compact `local_lab_monitoring_projection.json`
  - the standard `local_lab_observability_export.json`
- it is intended as the future backend-facing summary for detailed Local IA Lab monitoring
- current normalized content includes:
  - run/export/artifact identifiers
  - core review/proof/recalibration readiness
  - packaging and dry-run handoff truth
  - scope/release counts
  - refs back to detailed sidecars
- important invariant:
  - this remains descriptive only
  - it does not create a second source of truth
  - it does not introduce UI or VPS mutation semantics

## 7quaterdecies. Latest bounded Local IA Lab monitoring ingestion summary

- the same Local IA Lab chain now also emits `local_lab_monitoring_ingestion_summary.json`
- this summary is built from:
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- it is intended as the first monitoring-side ingestion verdict for future backend/Prometheus pipelines
- current checks are intentionally bounded:
  - payload/export `correlation_id` alignment
  - payload/export `profile` alignment
  - payload/export `runtime_mode` alignment
  - payload/export `timestamp_ms` alignment
  - non-empty metrics/text export presence
- important invariant:
  - this remains descriptive ingestion plumbing only
  - it does not create runtime coupling with Build-10
  - it does not change the governed Local IA Lab -> VPS rail

## 7quindecies. Latest bounded Local IA Lab monitoring bundle loader

- a future backend can now reload the Local IA Lab monitoring trio from disk through `src/monitoring/local_lab_bundle_loader.py`
- the loader validates:
  - file presence
  - typed JSON validity
  - alignment of `correlation_id/profile/runtime_mode/timestamp_ms`
- this is the first file-based backend ingestion path over the Local IA Lab monitoring sidecars
- important invariant:
  - it stays descriptive only
  - it does not import anything into VPS
  - it does not couple the Local IA Lab bundle to Build-10 runtime orchestration

## 7sexdecies. Latest bounded Local IA Lab observability text export

- the same Local IA Lab chain now also emits `local_lab_observability.prom`
- this file is derived directly from the standard `ObservabilityExport.text_payload`
- it is the first scrape-friendly text export over the Local IA Lab monitoring truth
- important invariant:
  - it stays descriptive only
  - it does not create a new runtime
  - it does not change any governed handoff or promotion semantics

## 7. Acceptance criteria

- [x] the current repo truth is mapped, not guessed
- [x] historical snapshot ingestion is identified
- [x] post-trade structured ingestion is identified
- [x] strategy/review bundle ingestion is identified
- [x] governed replay sidecar ingestion is identified
- [x] the missing live bidirectional loop is stated explicitly

## 7septdecies. Latest bounded Local IA Lab research-priority scorer

- the same Local IA Lab chain now also emits `local_lab_research_priority.json`
- this sidecar is built from governed Local IA Lab evidence already produced by the chain:
  - per-trade loss attribution
  - scope matrix when available
  - proof/release readiness
- its purpose is bounded:
  - rank which `pair x engine` scope deserves the next replay/recalibration cycle
  - separate `trace_capture` work from true recalibration work
  - expose a future-monitoring-ready summary without creating UI coupling
- important invariant:
  - this is not a runtime model
  - this does not mutate VPS behavior
  - this does not create promotion authority

## 7octodecies. Latest bounded Local IA Lab loss-surrogate scorer

- the same Local IA Lab chain now also emits `local_lab_loss_surrogate_report.json`
- this sidecar is the first truly trained but still transparent Local IA Lab model:
  - `model_family=transparent_linear_loss_surrogate_v1`
  - `model_kind=diagonal_lda_linear_score`
  - local-only only
  - research-only only
- training inputs remain no-lookahead and decision-time only:
  - `raw_score`
  - `penalized_score`
  - `final_score`
  - `expected_cost`
  - `ce_expected`
  - `candidate_size`
  - `final_size`
  - `ranking_position`
- its purpose is bounded:
  - estimate which scopes currently carry the highest modeled loss pressure
  - surface a compact future-monitoring-ready signal
  - not replace detailed per-trade attribution or proof sidecars
- important invariant:
  - this is not a VPS/runtime model
  - this does not mutate promotion state
  - this does not authorize artifact import by itself

## 7novodecies. Latest bounded Local IA Lab surrogate-guided planning

- the same Local IA Lab chain now also feeds the trained loss surrogate into:
  - `local_lab_research_priority`
  - `local_lab_recalibration_plan`
- the integration stays bounded:
  - it can elevate research priority for a scope
  - it can add a local replay recommendation for a high-risk scope
  - it cannot by itself authorize recalibration publication or VPS import
- important invariant:
  - the surrogate remains advisory only
  - proof/release/promotion semantics stay governed elsewhere
  - no VPS/runtime coupling is introduced

## 7vicies. Latest bounded Local IA Lab replay candidate queue

- the same Local IA Lab chain now also emits `local_lab_replay_candidate_queue.json`
- this queue is derived from current local-only planning truth:
  - research priority
  - recalibration plan
  - surrogate-guided evidence already emitted by the bundle
- its purpose is bounded:
  - identify the next replay/research scopes the Lab should process
  - keep blocked work visible (`trace_capture`, `human_scope_review`, `manual_loss_review`)
  - expose a compact future-monitoring-ready workflow surface without UI coupling
- important invariant:
  - this is not a runtime scheduler
  - this does not mutate VPS behavior
  - this does not create promotion authority

## 7unvicies. Latest bounded Local IA Lab replay ticket index

- the same Local IA Lab chain now also emits `local_lab_replay_ticket_index.json`
- this index is derived from the local replay candidate queue and reuses the canonical `LocalReplayRequest` contract
- its purpose is bounded:
  - prepare governed local replay tickets for future automation or operator review
  - keep blocked tickets explicit when the queue is not truly replay-ready
  - expose a compact future-monitoring-ready work surface without UI coupling
- important invariant:
  - this is not an execution surface
  - this does not mutate VPS behavior
  - this does not create promotion authority

## 7duovicies. Latest bounded Local IA Lab replay dispatch plan

- the same Local IA Lab chain now also emits `local_lab_replay_dispatch_plan.json`
- this plan is derived from the governed replay ticket index and stays explicitly non-executing
- its purpose is bounded:
  - separate ready local replay work from blocked local replay work
  - prepare a future automation/loader surface without running anything
  - expose a compact future-monitoring-ready dispatch truth without UI coupling
- important invariant:
  - this is not an execution surface
  - this does not mutate VPS behavior
  - this does not create promotion authority

## 7tervicies. Latest bounded Local IA Lab workflow/monitoring discovery manifests

- the same Local IA Lab chain now also emits `local_lab_replay_workflow_manifest.json`
- this manifest binds together the current local replay workflow sidecars:
  - replay candidate queue
  - replay ticket index
  - replay dispatch plan
- on the monitoring side, the chain now also emits `local_lab_monitoring_bundle_manifest.json`
- this manifest binds together the current monitoring ingestion sidecars:
  - monitoring backend payload
  - observability export
  - monitoring ingestion summary
  - optional replay workflow manifest ref
- purpose:
  - future backend/Prometheus/dashboard ingestion should discover one manifest first, not hardcode sidecar names
  - keep the bundle self-describing and audit-ready
- important invariant:
  - local-only discovery surface
  - no UI coupling
  - no VPS/runtime mutation
  - no promotion authority

## 7quattuorvicies. Latest bounded Local IA Lab monitoring bundle discovery

- `src/monitoring/local_lab_bundle_discovery.py` now exists as the next bounded backend step over the monitoring bundle manifest
- purpose:
  - scan a root for Local IA Lab monitoring bundle manifests
  - order bundles by latest governed timestamp
  - load the latest valid monitoring bundle without hardcoded directory knowledge
- important invariant:
  - still local/backend only
  - still no UI coupling
  - still no VPS/runtime mutation
  - still no promotion authority

## 7quinvicies. Latest bounded Local IA Lab monitoring feed

- `src/monitoring/local_lab_monitoring_feed.py` now exists over discovered monitoring bundles
- purpose:
  - summarize latest bundle truth plus bundle counts by backend status/ingestion readiness
  - prepare the first compact multi-bundle backend surface without opening every bundle in detail
- important invariant:
  - still local/backend only
  - still no UI coupling
  - still no VPS/runtime mutation
  - still no promotion authority

## 7sexvicies. Latest bounded Local IA Lab calibration-methods review

- the same Local IA Lab chain now also emits `local_lab_calibration_methods_review.json`
- this review is the first direct proof-side consumer of the shared calibration-methods core:
  - purged walk-forward geometry
  - Deflated Sharpe Ratio
- its purpose is bounded:
  - make Local IA Lab calibration-method evidence explicit on the proof rail
  - keep insufficient history visible as `partial`
  - block local proof when DSR is truly computed and fails floor
- the same truth now also propagates into:
  - `local_lab_analysis_summary.json`
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- important invariant:
  - still local-only
  - still no UI coupling
  - still no VPS/runtime mutation
  - human walk-forward approval remains a separate hard gate

## 7septemvicies. Latest bounded Local IA Lab release/dry-run calibration-methods propagation

- the same Local IA Lab chain now also carries calibration-methods truth into:
  - `artifact_release_candidate.json`
  - `artifact_release_gate_summary.json`
  - `artifact_import_dry_run_bridge.json`
- purpose:
  - make the handoff explicitly say whether the candidate is calibration-methods-backed
  - keep proof-backed vs calibration-backed truth readable before any future VPS import
- important invariant:
  - still local-only
  - still no UI coupling
  - still no VPS/runtime mutation

## 7octovicies. Latest bounded Local IA Lab monitoring manifest/discovery/feed calibration-methods propagation

- the monitoring bundle manifest now carries compact calibration-methods truth
- discovery and compact feed now propagate it across multiple Local IA Lab bundles
- purpose:
  - let future backend ingestion count ready vs partial vs blocked calibration-methods bundles without opening every sidecar manually
  - keep discovery manifest-first and audit-ready
- important invariant:
  - still local/backend only
  - still no UI coupling
  - still no VPS/runtime mutation

## 7novemvicies. Latest bounded Local IA Lab tail-risk review

- the same Local IA Lab chain now also consumes exported governed `DTRRecord` history for strategy-level tail-risk evidence
- `src/calibration_methods/pot_gpd.py` now provides the bounded POT-GPD helper used by:
  - `src/local_replay_runtime/local_lab_tail_risk_review.py`
- `scripts/run_local_lab_analysis_bundle.py` now emits `local_lab_tail_risk_review.json`
- current scope is intentionally top-level, not pair-engine scope:
  - daily breaker `THR-R01`
  - weekly breaker `THR-R02`
  - monthly breaker `THR-R03`
- purpose:
  - make exported replay/post-trade history usable for bounded EVT-style Local IA Lab review
  - expose compact future-dashboard/backend truth without changing release semantics
- important invariant:
  - still local-only
  - still no UI coupling
  - still no VPS/runtime mutation
  - not yet a release gate by itself

## 7tricies. Latest bounded Local IA Lab stationarity gate

- the same Local IA Lab chain now also emits explicit MI-9 evidence from `src/calibration_methods/stationarity.py`
- `local_lab_calibration_methods_review.json` now carries:
  - `stationarity_status`
  - `stationarity_ready`
  - `stationarity_pass`
  - dual ADF + KPSS result
- purpose:
  - make no-lookahead calibration evidence stricter before any artifact is considered locally proof-backed
  - keep insufficient history explicit as `partial`
  - block local proof when stationarity truly fails, not only when DSR fails
- compact future-dashboard/backend truth now also propagates into:
  - `local_lab_calibration_normalized_report.json`
  - `local_lab_analysis_summary.json`
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- important invariant:
  - still local-only
  - still no UI coupling
  - still no VPS/runtime mutation

## 7untricies. Latest bounded shared human hard-cap helper

- the same Local IA Lab chain now also uses `src/calibration_methods/hard_cap_floor.py`
- purpose:
  - centralize conservative publication against human floors/caps
  - keep audit semantics explicit with:
    - `hard_cap_satisfied`
    - `hard_cap_binding`
- current bounded consumers:
  - `edge_gate_calibration`
  - `local_lab_tail_risk_review`
  - `local_lab_calibration_normalized_report`
- important invariant:
  - still local-only
  - still no UI coupling
  - still no VPS/runtime mutation

## 7duotricies. Latest bounded Local IA Lab multiple-testing review

- the same Local IA Lab chain now also emits explicit MI-12 evidence from:
  - `src/calibration_methods/multiple_testing.py`
  - `src/local_replay_runtime/local_lab_multiple_testing_review.py`
- current truth:
  - the bounded Local IA Lab calibration families are still conservative interval-publication outputs
  - therefore MI-12 is currently explicit `not_required_interval_publication`, not a fake p-value correction pass
  - future hypothesis-test families can still consume the shared Holm-Bonferroni helper when real comparable p-values exist
- this same truth now also propagates into:
  - normalized calibration report
  - proof assessment
  - Local IA Lab analysis summary
  - monitoring/backend/observability bundle sidecars
- important invariant:
  - still local-only
  - still no UI coupling
  - still no VPS/runtime mutation

## 7tertricies. Latest bounded Local IA Lab execution review

- the same Local IA Lab chain now also emits explicit EXECUTION evidence from:
  - `src/calibration_methods/execution.py`
  - `src/local_replay_runtime/local_lab_execution_review.py`
- current truth:
  - `THR-X01` and `THR-X02` can now be reviewed locally when dedicated execution telemetry is provided
  - the default bundle remains explicit `partial` when no execution telemetry sidecar exists
  - no replay export sidecar is silently reinterpreted as venue telemetry
- this same truth now also propagates into:
  - analysis summary
  - monitoring projection/backend/observability
  - monitoring bundle manifest/discovery/feed
- important invariant:
  - still local-only
  - still no UI coupling
  - still no VPS/runtime mutation
  - not yet a proof or release gate by itself

## 7quatertricies. Latest execution runtime projection handoff

- the same Local IA Lab chain now also emits typed future-runtime handoff evidence from:
  - `src/local_replay_runtime/local_lab_execution_runtime_projection.py`
- current truth:
  - `THR-X03` is now projected into a future `rate_limiter` contract
  - `THR-X05` is now projected into a future `slippage_model` contract
  - the projection is service-owned/review-owned handoff metadata only; it is not a runtime mutation
- this same truth now also propagates into:
  - artifact proof assessment
  - artifact release candidate
  - top-level Local IA Lab analysis summary
- important invariant:
  - still local-only
  - still no UI coupling
  - still no VPS/runtime mutation
  - still no gate bypass

## 7quinquetricies. Latest canonical runtime consumer seam

- new current truth:
  - the future-runtime handoff is no longer projection-only
  - `src/execution_backbone/rate_limiter.py` and `src/execution_backbone/slippage_model.py` now exist as bounded canonical consumers for:
    - `THR-X03 -> rate_limiter`
    - `THR-X05 -> slippage_model`
- current bounded behavior:
  - `ExecutionRuntime` only consumes them when they are injected explicitly
  - `THR-X05` is applied conservatively as extra expected-cost friction with audit metadata
  - `THR-X03` remains fail-open unless live metadata already provides `rest_quota_ratio_current`
- invariant preserved:
  - still no automatic VPS bootstrap wiring
  - still no gate bypass
  - still no hidden runtime activation

## 7sexquinquagies. Latest runtime projection bootstrap bridge

- new current truth:
  - `execution_runtime_projection_bridge.py` now loads the Lab-side runtime projection artifact fail-open
  - `execution_runtime_bootstrap.py` now accepts `execution_runtime_projection_path`
  - the canonical runtime can therefore recover `THR-X03/X05` consumers from the same handoff JSON, without manual constructor assembly
- invariant preserved:
  - still explicit opt-in only
  - still no bootstrap activation unless the path is provided
  - still no gate bypass

## 7septsexquinquagies. Latest Build-10 visibility for the runtime projection bridge

- new current truth:
  - Build-10 now exposes the Local IA Lab `execution_runtime_projection_path` seam as a typed monitoring/dashboard/observability surface
  - this surface is separate from the older compiled `execution_no_trade_bridge`, so the operator can distinguish:
    - bounded compiled hook status
    - bounded `THR-X03/X05` runtime-consumer loadability
- invariant preserved:
  - still no hidden runtime activation
  - still descriptive only; no gate or runtime behavior is changed by monitoring projection
  - still no gate bypass


---

## Source: docs/production_deployment_plan/16_VPS_LOCAL_OBSERVABILITY_ARCHITECTURE.md

# VPS -> Local Observability Architecture

> Status: planning and execution anchor, based on the real repo as of 2026-04-11.
>
> Rule of truth: current code wins over planning docs.

---

## 1. Objective

Define the correct observability split for V5.3:

- the VPS runs trading and lightweight collection
- the local PC hosts heavy monitoring, analysis, and long-retention tooling
- the VPS must not be saturated by raw-stream export, heavy dashboards, or uncontrolled log shipping

This file does not authorize a new runtime architecture. It only defines the observability rail that fits the already chosen `Local IA Lab / VPS` separation.

---

## 2. Short answer

Yes, the VPS should expose enough metrics and logs for the local PC to monitor and analyze everything important.

But the transport must stay bounded:

- continuous: compact summaries and typed metrics
- on demand: detailed logs and deep diagnostics
- never: full raw event streams in continuous export if they can burden the VPS

Recommended posture:

- VPS = runtime + lightweight exporters + short retention
- local PC = Prometheus + Grafana + detailed drill-down + long retention

---

## 3. Target topology

```text
[VPS]
  trading runtime
  monitoring snapshot builder
  app observability export (.prom)
  node_exporter
  structured logs + rotation
  optional alert-forward path
        |
        | scrape / pull / targeted fetch
        v
[Local PC]
  Prometheus
  Grafana
  Local IA Lab detailed monitoring
  optional Loki / log archive
  deep drill-down and replay analysis
```

### 3.1 Hard rule

The VPS must export:

- health
- runtime stage
- compact execution/risk/infra aggregates
- typed import/proof/promotion state

The VPS must not continuously stream:

- full raw runtime logs
- raw market snapshots
- every event tick-by-tick
- full replay artifacts

---

## 4. Continuous export vs on-demand detail

### 4.1 Continuous export from VPS

Send continuously:

- `runtime_mode`
- deployment stage
- heartbeat age
- queue backlog
- stale pair count
- reconnect count
- kill switch state
- alert counts
- expected cost vs realized cost
- partial fill count
- fill latency P95
- CPU / RAM / disk summary
- import artifact id / lineage / review state

### 4.2 On-demand retrieval from VPS

Fetch only when needed:

- detailed structured logs
- run-specific JSON sidecars
- reconciliation incident bundles
- deep order / fill traces
- long operator event history

### 4.3 Why this split

- keeps the VPS light
- keeps local analysis rich
- avoids turning the VPS into a logging warehouse
- preserves auditability without permanent heavy transport

---

## 5. Current code anchors already present

### 5.1 VPS monitoring contracts and payloads

Already present:

- `src/monitoring/contracts.py`
- `src/monitoring/metrics_collector.py`
- `src/monitoring/monitoring_runtime.py`
- `src/monitoring/health_dashboard_backend.py`
- `src/monitoring/technical_dashboard_backend.py`
- `src/monitoring/observability.py`
- `src/monitoring/observability_io.py`

Important current truth:

- `TechnicalDashboardPayload` already exists as a rich typed VPS/backend payload
- `ObservabilityExport` already exists as the app-metrics export contract
- the code can already emit Prometheus-style text payloads

### 5.2 Local IA Lab monitoring contracts and payloads

Already present:

- `src/local_replay_runtime/local_lab_monitoring_projection.py`
- `src/local_replay_runtime/local_lab_monitoring_backend.py`
- `src/local_replay_runtime/local_lab_observability.py`
- `src/monitoring/local_lab_monitoring_bundle_manifest.py`
- `src/monitoring/local_lab_bundle_loader.py`
- `src/monitoring/local_lab_bundle_discovery.py`
- `src/monitoring/local_lab_monitoring_feed.py`

Important current truth:

- Local IA Lab already emits a compact backend payload
- Local IA Lab already emits a Prometheus-style `.prom` text export
- Local IA Lab monitoring is already much closer to Grafana-ready than VPS process observability is

---

## 6. What is still missing in code

### 6.1 Missing or incomplete on the VPS side

#### A. Process/system metric producers

Current reality:

- contracts already have `cpu_pct` and `ram_pct`
- some scripts still inject demo/static values
- there is no verified process/system sampler wired on the real VPS runtime path

Missing bounded code:

- process sampler for:
  - process up
  - heartbeat age
  - `cpu_pct`
  - RSS / memory
  - thread count
  - optional FD count
- disk/free-space sampler
- stable periodic write of VPS `.prom` text export

#### B. Ops alerting pieces

Still missing in repo:

- `src/alerting/telegram_alerter.py`

#### C. Runtime/risk slices still missing

Still missing in repo:

- `src/regime_classifier/`
- `src/risk_backbone/loss_budgeter/daily_pnl_breaker.py`
- `src/execution_backbone/gatekeeper/gatekeeper.py`
- `src/risk_backbone/info_stress_monitor.py`
- `src/execution_backbone/spread_guard.py`
- `src/execution_backbone/slippage_model.py`

#### D. Venue/runtime proof still missing

Still incomplete:

- real Binance Testnet/live proof
- long-run soak proof on websocket/execution surfaces
- final execution telemetry producer for Local IA Lab `13-C`

### 6.2 Missing or incomplete on the local side

#### A. Monitoring stack integration

Not yet implemented in repo:

- Grafana dashboards consuming the current payloads
- optional Loki/log archive integration

Partially implemented in repo:

- typed per-VPS scrape handoff artifacts
- local aggregation into Prometheus `file_sd` JSON
- checked local Prometheus config generator

#### B. Log retrieval strategy

Partially implemented in repo:

- bounded durable JSONL retrieval now exists for the Shadow VPS service rail
- bounded recent-tail summary now exists for cheap continuous export

Still missing in repo:

- richer bounded log-pull tooling for:
  - time-window fetch
  - run-id fetch
  - severity-filtered fetch
- explicit compressed handoff bundles for incident drill-down

---

## 7. Recommended implementation plan

### O1. VPS process metrics producer

Goal:

- make real `cpu_pct`, `ram_pct`, process heartbeat, and runtime liveness observable from the live VPS path

Likely code targets:

- `src/monitoring/metrics_collector.py`
- `src/monitoring/monitoring_runtime.py`
- `src/protocols/shadow_vps_service.py`

Deliverables:

- typed process metrics gathered on the real service path
- no demo-only injected values on the live path

### O2. VPS application Prometheus text export

Goal:

- materialize one stable `.prom` export on the VPS from the existing `ObservabilityExport`

Likely code targets:

- `src/monitoring/observability.py`
- `src/monitoring/observability_io.py`
- bounded launcher/service write path

Recommended pattern:

- write a textfile collector file periodically
- avoid opening a custom heavy HTTP metrics server first

Current code truth:

- the Shadow VPS service already writes its own compact `.prom`
- the service can now also mirror that payload into a node_exporter textfile collector directory when configured
- deployment of node_exporter itself remains outside the repo

### O3. VPS host/system observability

Goal:

- add host metrics without bloating app code

Out-of-repo runtime component:

- `node_exporter` on the VPS

What it covers:

- CPU host
- RAM host
- filesystem
- disk IO
- network
- load

### O4. Local Prometheus + Grafana

Goal:

- keep heavy monitoring on the local PC

Recommended local stack:

- Prometheus on the local PC
- Grafana on the local PC
- optional Loki later for logs

Scrape targets:

- VPS `node_exporter`
- VPS app `.prom` exporter path or bounded scrape endpoint
- Local IA Lab `.prom` exports / ingestion feed

Current code truth:

- per-VPS scrape handoff can now be emitted from the real Shadow VPS service rail
- local-PC aggregation into Prometheus `file_sd` JSON now exists
- checked local Prometheus config generation now exists
- Grafana dashboards still remain to be added

### O5. VPS log transport strategy

Goal:

- get the important logs locally without saturating the VPS

Recommended rule:

- immediate:
  - `CRITICAL`
  - `ERROR`
  - selected `WARNING`
- batched or on-demand:
  - `INFO`
  - `DEBUG`
  - large structured traces

Recommended bounded capabilities:

- fetch by time range
- fetch by `correlation_id`
- fetch by `run_id`
- fetch by severity

### O6. UI hookup

Goal:

- keep the VPS UI minimal and the local UI rich

VPS minimal UI should consume:

- `HealthDashboardPayload`
- `TechnicalDashboardPayload`
- `ObservabilityExport`

Local IA Lab detailed UI should consume:

- `LocalLabMonitoringBackendPayload`
- `LocalLabMonitoringIngestionSummary`
- `local_lab_monitoring_feed`
- Local IA Lab sidecars/manifests for drill-down

---

## 8. Process UI for the VPS

The VPS process UI should remain minimal and operator-oriented.

It should show:

- service up/down
- runtime mode
- last heartbeat
- websocket health
- user-data health
- queue backlog
- stale pair count
- reconnect count
- kill switch state
- import artifact id / lineage
- promotion stage
- CPU / RAM / disk
- latest alerts

It should not try to become the heavy diagnostics UI.

The detailed diagnostics should stay on the local PC.

---

## 9. Recommended frequencies and load discipline

### 9.1 VPS export frequencies

- heartbeat / liveness: every 5s to 15s
- execution/risk/app gauges: every 10s to 30s
- CPU / RAM / disk: every 30s to 60s
- log batch shipping: coarse interval or on demand

### 9.2 Cardinality discipline

Never use high-cardinality labels for Prometheus such as:

- `order_id`
- `trade_id`
- dynamic free-text reasons
- unbounded file names

Prefer labels such as:

- `runtime_mode`
- `engine_id`
- `pair`
- `status`
- `deployment_stage`

### 9.3 Retention discipline

- short retention on the VPS
- long retention on the local PC
- compressed bundles for incidents

---

## 10. What should start now

Yes, observability plumbing should start now.

But in this order:

1. `node_exporter` deployment and scrape hookup
2. Grafana dashboards on stable payloads
3. compressed incident-bundle retrieval
4. only then richer UI wiring

This means:

- start backend observability now
- do not start by polishing dashboards

---

## 11. Estimated progress of the whole solution

This is an estimate, not a measured KPI.

### 11.1 Estimated progress by pillar

| Pillar | Estimate |
|---|---:|
| Governed replay/import rail | 85% |
| Local IA Lab core (diagnostic/proof/release dry-run) | 78% |
| Local IA Lab math/calibration stack | 62% |
| VPS runtime + venue + execution backbone | 55% |
| VPS ops/risk missing slices | 30% |
| Monitoring/UI/observability integration end-to-end | 42% |

### 11.2 Estimated overall progress

Estimated total solution progress:

- **~62%**

Interpretation:

- the foundations and Lab core are strong
- the governed handoff rail is strong
- the VPS runtime exists
- the missing work is no longer “everything”; it is concentrated in:
  - live/Testnet proof
  - missing VPS ops/risk modules
  - observability plumbing end-to-end
  - final UI integration

---

## 12. Immediate next coding order

1. VPS process metrics producer on the real service path
2. VPS app `.prom` writer
3. `13-C EXECUTION` continuation with real execution telemetry producer
4. `T9/T10/T11/T12/T13` missing VPS code slices
5. local Prometheus/Grafana hookup
6. UI hookup on already-stable payloads

---

## 13. Acceptance criteria for this architecture direction

- [x] Local IA Lab remains the heavy analysis side
- [x] VPS remains the light execution + collection side
- [x] no continuous raw-stream burden is imposed on the VPS
- [x] existing typed monitoring contracts are reused
- [x] Prometheus/Grafana start at backend/export level, not at UI level
- [x] missing code areas are explicitly identified
- [x] an explicit overall progress estimate is recorded


---

## Source: docs/production_deployment_plan/17A_BINANCE_SHADOW_POWERSHELL_BOOTSTRAP.md

# Binance Shadow PowerShell Bootstrap

## Scope

- Install or persist the Binance API environment variables used by the live Shadow VPS service.
- Materialize the governed `live_websocket_config.json` under `build/build11_live_websocket_campaign`.
- Launch one bounded Shadow service cycle on native Binance streaming.
- Regenerate the canonical Build-10 HTML dashboard from the resulting runtime artifacts.

## PowerShell env bootstrap

Use the workspace-local script:

```powershell
Set-Location "E:\claude  v5.3\v53_trading_system"

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Install-BinanceApiEnv.ps1 `
  -ApiKey "<BINANCE_API_KEY>" `
  -ApiSecret "<BINANCE_API_SECRET>" `
  -PersistUser
```

Notes:

- This sets:
  - `BINANCE_API_KEY`
  - `BINANCE_API_SECRET`
  - `V53_BINANCE_API_KEY`
  - `V53_BINANCE_SECRET_KEY`
  - `V53_BINANCE_LABEL`
- The script never prints secret values.

## Live Shadow launch

```powershell
Set-Location "E:\claude  v5.3\v53_trading_system"

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-BinanceShadowLiveCampaign.ps1 `
  -PersistUserEnv `
  -EnableTimeSyncProbe
```

Optional governed artifact refs:

```powershell
Set-Location "E:\claude  v5.3\v53_trading_system"

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-BinanceShadowLiveCampaign.ps1 `
  -PersistUserEnv `
  -EnableTimeSyncProbe `
  -ExecutionRuntimeProjectionPath ".\build\dev_dual_role_demo\local_lab_projection_demo\direct_runtime_projection\local_lab_execution_runtime_projection.json" `
  -RegimeLiteAssessmentPath ".\build\governed\regime_lite_assessment.json" `
  -RegimeLiteSafingRecommendationPath ".\build\governed\regime_lite_safing_recommendation.json"
```

## Public-only fallback

When no Binance API env vars are available, the launcher keeps the market-data stream and disables authenticated user-data automatically:

```powershell
Set-Location "E:\claude  v5.3\v53_trading_system"

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-BinanceShadowLiveCampaign.ps1 `
  -PublicOnly `
  -EnableTimeSyncProbe
```

## Produced artifacts

- `build/build11_live_websocket_campaign/live_websocket_config.json`
- `build/build11_live_websocket_campaign/service/...`
- `build/build11_live_websocket_campaign/live_captures/...`
- `build/build11_live_websocket_campaign/technical_dashboard/technical_dashboard.html`

## Current operator status on this Windows machine

- The PowerShell bootstrap now works end-to-end for:
  - env installation
  - governed campaign materialization
  - bounded Shadow service launch
  - Build-10 HTML dashboard regeneration
- The earlier `WinError 10013` observation was caused by the Codex sandbox network restriction, not by the host Windows firewall or missing API env.
- The same bounded launcher now succeeds when executed outside the sandbox on the real host.
- Current operated campaign artifacts show:
  - `last_completed_session_date=2026-04-12`
  - `last_error=""`
  - `execution_telemetry_status=written`
  - `live_user_data_authenticated=true`
  - `live_capture_pair_scope=[BTCUSDT, ETHUSDT]`

## Doctrine

- `Shadow` only, no live order path.
- Typed config and typed governed artifact refs only.
- No secret storage in repo JSON files.
- Dashboard remains a read-only consumer of runtime artifacts.


