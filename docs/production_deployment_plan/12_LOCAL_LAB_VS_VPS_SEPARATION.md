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
