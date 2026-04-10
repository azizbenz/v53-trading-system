# Phase Plan 0 → 4 — De l'audit à 10 k$ live

> **Objectif** — Définir une trajectoire opérationnelle de l'état actuel (audit terminé, code intact, capital à 0) jusqu'à 10 000 USD en LIVE halal spot sur VPS Hetzner CX43.
>
> **Principe directeur** — Aucune phase n'est franchie sans **critères d'entrée vérifiés** ET **critères de sortie vérifiés**. Aucune décision n'est implicite. Aucun seuil n'est hardcodé : tout seuil critique passe par calibration backtest + approbation shadow humaine.
>
> **Gates humains** — Le passage SHADOW utilise 3 paliers (1 mois → 2 mois → 3 mois) avec une **approbation humaine explicite** entre chaque palier. Aucun automatisme ne franchit ces gates seul.

---

## 0. Vue d'ensemble des phases

| Phase | Nom | Capital exposé | Durée min | Output principal |
|---|---|---|---|---|
| **Phase 0** | Décisions & calibration locale | 0 USD | 1-2 semaines | Décisions signées + artefacts de calibration |
| **Phase 1** | Implémentation P0 + LOCAL_REPLAY | 0 USD | 2-4 semaines | Code P0 mergé + tests verts + replay artefact validé |
| **Phase 2** | SHADOW (3 sous-paliers) | 0 USD | **3 mois minimum** | Approbation humaine 1m / 2m / 3m signée |
| **Phase 3** | MICRO_LIVE | 200-500 USD | 1-2 mois | P&L réel + reconciliation continue + 0 incident critique |
| **Phase 4** | LIVE | 10 000 USD | Continu | Trading en production avec monitoring permanent |

**Durée totale plancher** : ~5-7 mois entre la décision de démarrer et le capital cible. Aucun raccourci possible sans dégrader le risque.

---

## 1. Phase 0 — Décisions & calibration locale

> **But** — Avant de toucher à une seule ligne de code, **figer toutes les décisions structurantes** et **produire les artefacts de calibration** qui serviront de source de vérité aux phases suivantes.

### 1.0 Règle active après publication de `12_LOCAL_LAB_VS_VPS_SEPARATION.md`

La séparation finale **Local IA Lab vs VPS** est désormais fixée par `12_LOCAL_LAB_VS_VPS_SEPARATION.md`.

Donc, à partir de maintenant, le travail doit rester borné ainsi :

- **Autorisé** :
  - durcissement du rail réel déjà présent dans le repo (`LOCAL_REPLAY -> export gouverné -> import -> SHADOW`)
  - branchement progressif des seuils dynamiques via le shared core `src/calibration_loader/`
  - préparation des chantiers P0/P1 en cohérence avec `12`, `13` et `14`
  - éventuelle préparation documentaire d'une **vue flotte multi-VPS read-only**
- **Interdit** :
  - figer en code la séparation finale Local IA Lab / VPS
  - créer un package `src/local_ai_lab`
  - créer un control plane multi-VPS **actif** dans `src/`
  - faire d'une vue flotte multi-VPS autre chose qu'un résumé `health/status/artifact` avec drill-down vers la VPS choisie

Cette règle ne bloque donc **pas tout le travail**, mais elle maintient une frontière dure entre :
- runtime trading sur **single active VPS**
- vue flotte multi-VPS éventuelle, strictement read-only

### 1.1 Critères d'entrée

- [ ] Audit S1→S5 terminé (`production_deployment_plan/00_README.md` à jour)
- [ ] L'humain a lu tous les fichiers actuellement présents du dossier `production_deployment_plan/` (`15` présents au 2026-04-09, `12`, `13`, `14` inclus)
- [ ] L'humain a accepté les arbitrages de l'audit (V5.3 = canon, V3.7 = 3 idées seulement)
- [ ] Aucun engagement de capital pris

### 1.2 Activités

1. **Décisions structurantes** (`10_DECISIONS_REQUIRED.md`) :
   - Exchange (Binance vs Kraken vs autre)
   - École fiqh / référence sharia
   - Stablecoin policy
   - VPS confirmé (Hetzner CX43)
   - Limites de capital MICRO_LIVE
   - Qui valide les gates SHADOW
   - Qui signe les calibrations
2. **Calibration locale via Local IA Lab** (`12_LOCAL_LAB_VS_VPS_SEPARATION.md`) :
   - Backtest exhaustif des 4 engines sur 24 mois historiques
   - Stress test sur les 3 windows de capitulation (mars 2020, mai 2021, novembre 2022)
   - Production des artefacts de calibration pour tous les seuils dynamiques (`11_DYNAMIC_THRESHOLDS_CATALOG.md`)
   - Validation walk-forward (4-6 windows out-of-sample, purged k-fold avec embargo)
   - Vérification univers de trading (pas de survivorship bias)
3. **Documentation pré-flight** :
   - Fichier `DECISIONS_FROZEN_<date>.md` signé par l'humain
   - Fichier `CALIBRATION_ARTEFACT_<date>.json` produit par le Local IA Lab et signé

### 1.3 Critères de sortie

- [ ] Toutes les décisions du `10_DECISIONS_REQUIRED.md` sont **prises et écrites**
- [ ] Artefact de calibration produit, signé, et placé dans `artifacts/calibration/v1/`
- [ ] Tous les seuils du `11_DYNAMIC_THRESHOLDS_CATALOG.md` ont une **valeur calibrée + IC95% + N_observations**
- [ ] Stress test capitulation passé : aucun engine n'affiche un DD > 25 % sur les 3 windows
- [ ] Walk-forward passé : Sharpe out-of-sample > 0.5 sur au moins 2 engines
- [ ] L'humain a relu et signé `DECISIONS_FROZEN_<date>.md`

**Si un de ces critères n'est pas atteint** : pas de passage en Phase 1. **On retravaille jusqu'à ce qu'ils le soient.**

---

## 2. Phase 1 — Implémentation P0 + LOCAL_REPLAY

> **But** — Coder les 5 manques P0 (`03_GAPS_P0.md`), brancher les seuils dynamiques sur l'artefact de calibration, et valider via LOCAL_REPLAY que le système prend les bonnes décisions sur des données historiques connues.

### 2.1 Critères d'entrée

- [ ] Phase 0 sortie validée
- [ ] Artefact de calibration V1 disponible et signé
- [ ] Decisions frozen disponibles
- [ ] L'humain a alloué le temps nécessaire à la Phase 1 (estimation : 2-4 semaines selon disponibilité de l'agent codeur)

### 2.2 Activités (côté agent codeur Sonnet)

1. **Tranches P0-1 à P0-5** dans l'ordre prescrit par `09_CODING_SLICES_FOR_IMPLEMENTING_AGENT.md`
2. **Pour chaque tranche** :
   - L'agent codeur lit le MD Opus correspondant
   - Vérifie contre le repo réel (le repo gagne en cas de contradiction)
   - Code la tranche bornée
   - Lance les tests cibles
   - Met à jour le tracker `2026-04-07_V53_MASTER_DEVELOPMENT_TRACKER.md`
   - Met à jour la mémoire si nécessaire
3. **Aucun seuil hardcodé** : tout chargement de seuil passe par le module `calibration_loader/` qui lit l'artefact V1
4. **LOCAL_REPLAY exhaustif** : chaque engine repassé sur 24 mois historiques avec les nouveaux modules P0 actifs

### 2.3 Critères de sortie

- [ ] **Tous les P0 mergés** dans `src/` avec tests verts
- [ ] **Tests existants restent verts** (1026 + nouveaux). Aucune régression tolérée.
- [ ] **Couverture P0** : aucun module P0 sous 80 % de coverage
- [ ] **Aucun seuil hardcodé** dans les modules P0 (audit grep `\b(0\.\d+|1\.\d+|2\.\d+)\b` dans les nouveaux fichiers)
- [ ] **LOCAL_REPLAY** : artefact `replay_p0_v1.json` produit avec :
  - PnL replay cohérent avec backtest (delta < 5 %)
  - Aucun trade halal-violant détecté
  - Aucun trade fee-negative détecté
  - Toutes les reconciliations OK
- [ ] **Signoff humain** sur `replay_p0_v1.json`

**Tranches P0 attendues** : voir `09_CODING_SLICES_FOR_IMPLEMENTING_AGENT.md` pour le découpage exact (6-10 tranches code).

---

## 3. Phase 2 — SHADOW avec 3 paliers à validation humaine

> **But critique** — Faire tourner le système **24/7 sur le VPS contre le marché réel** sans soumettre aucun ordre. Détecter les écarts entre LOCAL_REPLAY et live (= bugs latents) avant que de l'argent réel soit en jeu.
>
> **Principe non-négociable** — La phase SHADOW dure **minimum 3 mois calendaires**, segmentée en 3 paliers de validation humaine. Chaque palier produit un dossier de revue, lu et signé par l'humain. **Aucun automatisme** ne fait passer un palier au suivant.

### 3.1 Critères d'entrée

- [ ] Phase 1 sortie validée
- [ ] VPS Hetzner CX43 provisionné, OS hardened, secrets sealed
- [ ] Code déployé sur VPS via méthode prouvée (rsync + signature, ou git tag immuable)
- [ ] WS Binance connecté en read-only avec API key restreinte (`SPOT READ` seulement, pas de TRADING)
- [ ] Telegram alerter testé end-to-end
- [ ] Disk monitor + log rotation actifs

### 3.2 Architecture SHADOW

- **Mode** : `runtime_mode=SHADOW`
- **Exchange API** : read-only (pas de clé TRADING)
- **Décisions** : produites comme en LIVE, mais **aucun ordre soumis**
- **Artefacts** : tous les artefacts produits (manifests, decisions, simulated fills) sont conservés
- **Métriques** : équity simulée, P&L simulé, fees simulés, slippage simulé (estimé via orderbook depth)
- **Comparaisons** : delta entre décision SHADOW et décision LOCAL_REPLAY sur les mêmes timestamps

### 3.3 Palier S2.1 — SHADOW Mois 1

**Durée minimum** : 30 jours calendaires consécutifs **sans interruption non-planifiée**.

**Critères de sortie palier 1** :
- [ ] Uptime ≥ 99 % (≤ 7h de downtime non-planifié sur 30 jours)
- [ ] **Zéro divergence critique** entre l'état local persisté et l'état exchange (via reconciliation périodique)
- [ ] **Zéro feature drift** détecté (PSI < 0.2 sur toutes les features critiques)
- [ ] **Zéro halal violation** simulée (aucune décision aurait violé le whitelist/blacklist/policy)
- [ ] Au moins 30 décisions de trade simulées produites (sinon échantillon trop faible)
- [ ] Reconciliation OK à chaque boot
- [ ] Kill switch jamais auto-tripped (sinon investigate)
- [ ] **Production d'un dossier de revue** `shadow_review_S2.1_<date>.md` :
  - Métriques aggregées (Sharpe simulé, max DD simulé, hit rate, edge moyen)
  - Liste des incidents techniques + RCA
  - Top 5 trades simulés gagnants + perdants
  - Comparaison décisions SHADOW vs LOCAL_REPLAY (delta moyen)
  - Recommandation de l'agent codeur : GO / NO-GO

**Gate humain S2.1 → S2.2** :
> L'humain lit le dossier de revue, vérifie les métriques, et **signe explicitement** un fichier `gate_S2.1_to_S2.2_<date>_signed.md` avec la décision : `GO` ou `NO-GO + raison + actions correctives`.
>
> **Si NO-GO** : on revient en Phase 1, on corrige, on relance un palier S2.1 complet (pas de raccourci).

### 3.4 Palier S2.2 — SHADOW Mois 2

**Durée minimum** : 30 jours calendaires supplémentaires.

**Critères de sortie palier 2** (cumulatifs avec S2.1) :
- [ ] Tous les critères S2.1 toujours respectés
- [ ] **Stabilité métriques** : delta Sharpe simulé entre S2.1 et S2.2 < 30 % (sinon = signal d'instabilité)
- [ ] **Au moins 1 régime de marché différent** vu entre S2.1 et S2.2 (e.g. bull→sideways, ou un événement de stress micro-vu)
- [ ] Si l'événement de stress n'est pas survenu naturellement : **stress test forcé** sur les données historiques de capitulation (re-run mars 2020 par-dessus le pipeline live, en mode "simulation injectée")
- [ ] Au moins 60 décisions simulées cumulées
- [ ] **Production d'un dossier de revue** `shadow_review_S2.2_<date>.md` :
  - Comparaison S2.1 vs S2.2 (stabilité des métriques)
  - Inventaire des incidents (zéro tolérance pour les criticals)
  - Vérification de la calibration : les seuils dynamiques sont-ils toujours pertinents ? Faut-il les recalibrer ?
  - Recommandation : GO / NO-GO

**Gate humain S2.2 → S2.3** : signature `gate_S2.2_to_S2.3_<date>_signed.md`.

### 3.5 Palier S2.3 — SHADOW Mois 3

**Durée minimum** : 30 jours calendaires supplémentaires (= 90 jours cumulés).

**Critères de sortie palier 3** (cumulatifs) :
- [ ] Tous les critères S2.1 + S2.2 toujours respectés
- [ ] **Au moins 100 décisions simulées cumulées**
- [ ] **Sharpe simulé out-of-sample > 0.7** (seuil arbitraire, peut être ajusté en Phase 0)
- [ ] **Max DD simulé < 12 %** (à calibrer en Phase 0)
- [ ] **Win rate ou ratio P&L** cohérent avec backtest
- [ ] **Recalibration des seuils dynamiques** : nouveaux artefacts `calibration_v2.json` produits avec données SHADOW intégrées
- [ ] **Production du dossier final SHADOW** `shadow_review_FINAL_<date>.md` :
  - Synthèse 3 mois : tous les KPIs
  - Comparaison décisions cumulées SHADOW vs backtest (delta global)
  - Liste exhaustive des incidents et résolutions
  - Recommandation finale : GO MICRO_LIVE / NO-GO + actions

**Gate humain S2.3 → Phase 3** :
- L'humain lit `shadow_review_FINAL_<date>.md`
- Décision **explicite et écrite** dans `gate_SHADOW_to_MICROLIVE_<date>_signed.md`
- **Si GO** : la decision inclut le capital initial MICRO_LIVE (200-500 USD) et la durée minimum MICRO_LIVE
- **Si NO-GO** : retour Phase 1 ou Phase 2 selon la nature du blocage

### 3.6 Critères de sortie globaux Phase 2

| Critère | Valeur cible | Source |
|---|---|---|
| Durée cumulée | ≥ 90 jours | Calendrier |
| Uptime cumulé | ≥ 99 % | Monitoring VPS |
| Décisions simulées | ≥ 100 | Logs SHADOW |
| Halal violations | 0 | `sharia_compliance/policy_audit_logger.py` |
| Reconciliation divergences critiques | 0 | `reconciliation_layer/` |
| Sharpe simulé | ≥ 0.7 (à calibrer Phase 0) | Calcul out-of-sample |
| Max DD simulé | ≤ 12 % (à calibrer Phase 0) | Calcul out-of-sample |
| Gates humains signés | 3/3 (S2.1, S2.2, S2.3) | Fichiers signés |

---

## 4. Phase 3 — MICRO_LIVE (capital minimal réel)

> **But** — Premier contact avec de l'argent réel, sur **un capital volontairement faible** (200-500 USD = 2-5 % du target). Détecter ce que SHADOW ne peut pas voir : impact réel des fees, slippage réel, comportement humain face à la première perte réelle.

### 4.1 Critères d'entrée

- [ ] Phase 2 sortie validée + gate signé
- [ ] Capital initial MICRO_LIVE défini et alloué (séparé physiquement du capital cible)
- [ ] API key Binance recréée avec **TRADING activé**, withdraw désactivé, IP whitelist VPS
- [ ] Calibration V2 (post-SHADOW) déployée
- [ ] **Plan de réaction** : ce que l'humain fait si MICRO_LIVE perd plus de X % (cf. cooldowns post-perte, daily P&L circuit breaker)

### 4.2 Activités

1. **Activation MICRO_LIVE** : `runtime_mode=MICRO_LIVE`, capital_cap = 500 USD (configurable)
2. **Limites strictes** :
   - Position size max : 100 USD par trade
   - Nb positions concurrentes max : 3
   - Trades max par jour : 5
   - Daily P&L circuit breaker actif : −2 % intraday → SHADOW automatique
3. **Monitoring quotidien** : revue chaque matin par l'humain (pas en temps réel)
4. **Reconciliation forcée** au boot et toutes les 60 minutes
5. **Production d'un journal** `microlive_journal_<week>.md` chaque semaine

### 4.3 Critères de sortie Phase 3 → Phase 4

**Durée minimum** : 30 jours, idéalement 60 jours.

| Critère | Cible |
|---|---|
| Durée | ≥ 30 jours |
| Trades exécutés | ≥ 30 |
| Fee meter live cohérent avec backtest | delta < 10 % |
| Slippage live cohérent avec estimation | delta < 50 % |
| Reconciliation : 0 divergence critique | obligatoire |
| P&L net (après fees) > 0 | obligatoire (ou justifier la perte) |
| Drawdown réel < 8 % | obligatoire |
| Daily breaker jamais tripped | sinon investigate avant scaling |
| Halal violations = 0 | obligatoire |
| Aucun incident critique | obligatoire |
| **Gate humain signé** | `gate_MICROLIVE_to_LIVE_<date>_signed.md` |

**Si P&L net ≤ 0 mais autres critères OK** : décision humaine explicite — soit prolonger MICRO_LIVE, soit retourner en Phase 1 pour ajuster les engines, soit accepter la perte structurelle et abandonner.

---

## 5. Phase 4 — LIVE (capital cible)

> **But** — Trading en production avec le capital cible 10 000 USD, monitoring permanent, opérations stables.

### 5.1 Critères d'entrée

- [ ] Phase 3 sortie validée + gate signé
- [ ] Allocation capital cible disponible
- [ ] **Plan de scaling** défini : 500 USD → 2000 → 5000 → 10000 par paliers, avec validation entre chaque palier ?
- [ ] Plan de revue mensuelle défini (humain s'engage à 1h/mois minimum)

### 5.2 Modes opérationnels recommandés

- **Scaling progressif** : 500 → 2000 → 5000 → 10000 par étapes de 2 semaines minimum
- **Revue mensuelle** obligatoire : l'humain lit les artefacts du mois et signe `monthly_review_<month>.md`
- **Recalibration trimestrielle** des seuils dynamiques via Local IA Lab → nouveau `calibration_v3.json` etc.
- **Audit annuel halal** : revue par tiers (mufti spécialisé) avec accès aux logs

### 5.3 Triggers de retour à une phase antérieure

- **Drawdown > 15 %** : auto-tripping kill switch + retour Phase 2 (SHADOW) pour investigation
- **3 mois consécutifs Sharpe < 0** : retour Phase 0 (recalibration complète)
- **Incident sécurité (clé compromise, etc.)** : kill switch immédiat + recréation de l'environnement
- **Changement réglementaire** (e.g. exchange delisté, nouvelle régulation) : pause + revue

---

## 6. Tableau de synthèse — durées et capitaux

| Phase | Capital exposé | Durée plancher | Durée réaliste | Sortie obligatoire |
|---|---|---|---|---|
| 0 — Décisions & calibration | 0 USD | 1 sem. | 2-4 sem. | Decisions frozen + Calibration V1 signés |
| 1 — Implémentation P0 + replay | 0 USD | 2 sem. | 4-8 sem. | P0 mergés + replay V1 signé |
| 2 — SHADOW (3 paliers) | 0 USD | **90 jours** | 90-120 jours | 3 gates humains signés |
| 3 — MICRO_LIVE | 200-500 USD | 30 jours | 30-60 jours | Gate humain signé |
| 4 — LIVE | 10 000 USD | continu | continu | Revues mensuelles + audit annuel |
| **Total Phase 0 → premier dollar Phase 4** | — | **~5.5 mois** | **~7-9 mois** | — |

**Le chiffre clé** : entre la signature du `DECISIONS_FROZEN_<date>.md` et le premier dollar exposé en LIVE, **il y a 5.5 mois minimum**, plus probablement 7-9 mois en réaliste. **Aucun raccourci** sans dégrader le risque.

---

## 7. Gates humains — récapitulatif

| Gate | Quand | Quoi signer | Conséquence si NO-GO |
|---|---|---|---|
| **G0** | Sortie Phase 0 | `DECISIONS_FROZEN_<date>.md` | Pas de code |
| **G1** | Sortie Phase 1 | `replay_p0_v1_signed.md` | Code à corriger |
| **G2.1** | Fin SHADOW M1 | `gate_S2.1_to_S2.2_signed.md` | Retour Phase 1 |
| **G2.2** | Fin SHADOW M2 | `gate_S2.2_to_S2.3_signed.md` | Retour Phase 1 ou 2 |
| **G2.3** | Fin SHADOW M3 | `gate_SHADOW_to_MICROLIVE_signed.md` | Retour Phase 1 ou 2 |
| **G3** | Sortie MICRO_LIVE | `gate_MICROLIVE_to_LIVE_signed.md` | Prolongation ou retour |
| **G4 (récurrent)** | Mensuel en LIVE | `monthly_review_<month>.md` | Trigger pause / scaling reverse |

**7 gates humains obligatoires** entre l'audit et le premier dollar LIVE, plus une revue mensuelle récurrente.

---

**Suite logique** : `08_RISK_REGISTER.md` — registre des risques avec mitigations et triggers.
