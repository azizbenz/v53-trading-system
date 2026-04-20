# 02_SYSTEM_OVERVIEW_AND_GAPS

## Included Source Docs
- docs/production_deployment_plan/00_README.md
- docs/production_deployment_plan/01_VERDICT_V53_VS_V37.md
- docs/production_deployment_plan/02_V53_PRODUCTION_AUDIT.md
- docs/production_deployment_plan/03_GAPS_P0.md
- docs/production_deployment_plan/04_GAPS_P1.md
- docs/production_deployment_plan/05_V37_BRICKS_INCORPORATION.md
- docs/production_deployment_plan/06_BLIND_SPOTS_MULTIDISCIPLINARY.md
- docs/production_deployment_plan/07_PHASE_PLAN_0_TO_4.md
- docs/production_deployment_plan/08_RISK_REGISTER.md
- docs/production_deployment_plan/09_CODING_SLICES_FOR_IMPLEMENTING_AGENT.md
- docs/production_deployment_plan/10_DECISIONS_REQUIRED.md
- docs/production_deployment_plan/18_CODE_VS_PLAN_AUDIT_AND_WORK_PLAN.md

---

## Source: docs/production_deployment_plan/00_README.md

# Production Deployment Plan — V5.3 Trading System

> **Cible** : trading **spot halal** réel, capital **10 000 USD**, déploiement **single active VPS** (Hetzner CX43) avec option future de **vue flotte multi-VPS read-only**.
> **Statut** : plan d'action issu de l'audit S1→S4 (read-only) du 2026-04-08, patché 2026-04-09.
> **Auteur** : audit multidisciplinaire (trader senior + quant PhD + data science + dev fintech + compliance halal).

---

## 0. Workflow de production de ce dossier

> **Important** — Lire avant tout le reste. Définit les rôles et limite la portée de ces MD.

Ce dossier est produit par **Opus en mode planification**. Les rôles sont strictement séparés :

| Rôle | Acteur | Output | Portée |
|---|---|---|---|
| **Cadrage / planification / architecture** | Opus (cette session) | MD dans `production_deployment_plan/` | Plan, invariants, critères d'acceptation, ordre de réalisation |
| **Implémentation / refactor / tests** | Agent codeur (Sonnet/Code session local) | Code dans `src/`, tests dans `tests/` | Convergence doc/code, mise à jour mémoire et tracker |

**Règles dures** :
1. Les MD Opus servent de **plan et d'orientation**, pas de spec autoritaire.
2. **La vérité finale pour coder reste** : `code + tests + canon repo`.
3. Si un MD Opus contredit le repo réel, **le repo gagne**. L'agent codeur n'implémente pas un MD à l'aveugle.
4. Si un écart est détecté pendant l'implémentation, l'agent codeur le **remonte** plutôt que de le résoudre silencieusement.

**Format MD Opus standardisé** (chaque chantier P0/P1 dans 03/04 doit suivre ce gabarit) :
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

## 1. Pourquoi ce dossier existe

L'audit S1→S4 a établi que :

1. **V5.3 est une bien meilleure base de production que V3.7** (V3.7 = papier, V5.3 = ~30 modules production-grade codés et testés).
2. **V5.3 n'est pas prête telle quelle** pour faire tourner du capital réel : il manque des briques critiques (exchange adapter concret, halal compliance, fee-aware filter, regime awareness, gatekeeper central, alerting).
3. **V5.3 et V3.7 sont structurellement différents** (0 % d'architecture commune). Trois briques V3.7 méritent d'être incorporées comme **idées simplifiées**, pas comme imports directs.
4. **Aucun seuil ne doit être hardcodé** : tout seuil (edge minimum, drawdown, latence, etc.) doit être **calibré via backtest sur artefacts** et **validé via shadow avec approbation humaine**.

Ce dossier matérialise le **plan complet** pour passer de l'état actuel V5.3 à un système qui peut gérer 10 000 USD réels en spot halal sur VPS, sans perdre l'argent à cause d'une erreur d'ingénierie évitable.

---

## 2. Cible d'infrastructure : Hetzner CX43

Le VPS de référence pour ce plan est **Hetzner Cloud CX43** :

| Spec | Valeur |
|---|---|
| vCPU | 8 |
| RAM | 16 GB |
| Disk SSD | 160 GB |
| Trafic | 20 TB/mois |
| Localisation | EU (Falkenstein, Nuremberg, Helsinki) |
| Coût | **€12.49/mois** (~13.5 USD) |
| Source | https://www.hetzner.com/european-cloud |

**Implications pour le plan** :
- Coût annuel infra ≈ **162 USD/an = 1.6 % du capital** (vs 2.4-4.8 % pour la stack V3.7 Redis+Timescale+Docker).
- 16 GB RAM **suffisants** pour V5.3 file-based (V3.7 aurait demandé 32 GB).
- 160 GB SSD : large pour artefacts, logs, snapshots historiques (consommation estimée 20-40 GB/an).
- **Localisation EU** : meilleure latence vers Binance EU endpoints, conformité RGPD pour les logs personnels.
- **Single active VPS** : pas de multi-node, pas de Kubernetes, pas de load balancer pour le runtime trading.
- **Vue flotte optionnelle** : plusieurs VPS peuvent plus tard être résumées par une vue read-only `health/status/artifact`, sans orchestration active.

---

## 3. Comment lire ce dossier

Lecture séquentielle recommandée. Chaque fichier est self-contained mais s'appuie sur le contexte des précédents.

| # | Fichier | Pour qui | Temps lecture |
|---|---|---|---|
| 00 | [README.md](00_README.md) | Tout le monde, en premier | 5 min |
| 01 | [VERDICT_V53_VS_V37.md](01_VERDICT_V53_VS_V37.md) | Comprendre pourquoi on garde V5.3 | 5 min |
| 02 | [V53_PRODUCTION_AUDIT.md](02_V53_PRODUCTION_AUDIT.md) | Cartographie de ce qui existe déjà | 10 min |
| 03 | [GAPS_P0.md](03_GAPS_P0.md) | Trous critiques avant tout live trade | 15 min |
| 04 | [GAPS_P1.md](04_GAPS_P1.md) | Trous à combler avant de scaler | 10 min |
| 05 | [V37_BRICKS_INCORPORATION.md](05_V37_BRICKS_INCORPORATION.md) | 3 briques V3.7 retenues, et pourquoi pas les autres | 10 min |
| 06 | [BLIND_SPOTS_MULTIDISCIPLINARY.md](06_BLIND_SPOTS_MULTIDISCIPLINARY.md) | Ce qu'un humain seul ne voit pas (20 angles morts) | 15 min |
| 07 | [PHASE_PLAN_0_TO_4.md](07_PHASE_PLAN_0_TO_4.md) | Plan d'exécution Phase 0 → Phase 4 avec gates humains shadow 1m/2m/3m | 15 min |
| 08 | [RISK_REGISTER.md](08_RISK_REGISTER.md) | Registre des risques avec mitigations | 10 min |
| 09 | [CODING_SLICES_FOR_IMPLEMENTING_AGENT.md](09_CODING_SLICES_FOR_IMPLEMENTING_AGENT.md) | Découpage par tranches pour l'agent codeur | 10 min |
| 10 | [DECISIONS_REQUIRED.md](10_DECISIONS_REQUIRED.md) | Check-list des décisions avant chaque phase | 10 min |
| 11 | [DYNAMIC_THRESHOLDS_CATALOG.md](11_DYNAMIC_THRESHOLDS_CATALOG.md) | Catalogue exhaustif des seuils à calibrer (backtest + shadow) | 10 min |
| 11A | [DYNAMIC_THRESHOLDS_REPO_CROSSCHECK.md](11A_DYNAMIC_THRESHOLDS_REPO_CROSSCHECK.md) | Cross-check repo réel des consommateurs de seuils dynamiques | 10 min |
| 12 | [LOCAL_LAB_VS_VPS_SEPARATION.md](12_LOCAL_LAB_VS_VPS_SEPARATION.md) | Séparation Local IA Lab / VPS — qui fait quoi où | 15 min |
| 13 | [CALIBRATION_METHODS.md](13_CALIBRATION_METHODS.md) | Méthodes math de calibration des seuils dynamiques | 20 min |
| 14 | [SHADOW_GATE_MATH.md](14_SHADOW_GATE_MATH.md) | Math des gates Shadow 1m/2m/3m | 20 min |
| 30 | [PROMOTION_CALIBRATION_REGISTER.md](30_PROMOTION_CALIBRATION_REGISTER.md) | Registre durable : quoi calibrer ou prouver avant Shadow / Micro-live / Live | 10 min |

**Total : ~2h55 de lecture pour le dossier actuellement présent dans le repo.**

---

## 3bis. Statut réel du dossier au 2026-04-09

État constaté dans le repo :

- `00_README.md` à `14_SHADOW_GATE_MATH.md` sont présents.
- `12_LOCAL_LAB_VS_VPS_SEPARATION.md` est maintenant publié.
- Le dossier présent dans le repo contient actuellement `15` fichiers.

Conséquence opérationnelle :

- **Ce qui est déjà exploitable** :
  - le verdict V5.3 vs V3.7
  - la cartographie de l'existant
  - les gaps P0/P1
  - le plan de phases
  - le registre de risques
  - les slices de codage
  - le catalogue des seuils dynamiques (`11_...`)
- **Ce qui est maintenant arbitré par `12_LOCAL_LAB_VS_VPS_SEPARATION.md`** :
  - la séparation finale "qui vit où" entre Local IA Lab et VPS
  - le split fonctionnel des vues Local IA Lab / VPS
  - le statut de `src/calibration_loader/` comme shared core
  - le fait que le runtime reste `single active VPS`, avec seulement une **vue flotte multi-VPS read-only** possible plus tard

Travail autorisé après `12` :

1. Continuer le durcissement du rail réel déjà vérifié dans le repo :
   `local_replay_runtime -> governed export -> backtest_artifact_import -> VPS Shadow`
2. Brancher progressivement les seuils dynamiques via `src/calibration_loader/`.
3. Préparer les chantiers P0/P1 en s'appuyant sur `12`, `13` et `14`.
4. Documenter plus tard, si besoin, une **vue flotte multi-VPS** limitée aux statuts synthétiques, sans orchestration.

Travail toujours explicitement interdit :

1. Réorganiser le repo autour d'un nouveau package `local_ai_lab`
2. Créer un control plane multi-VPS **actif** dans `src/`
3. Introduire une orchestration ou un failover automatique multi-VPS non cadré
4. Prendre pour acquis qu'une vue flotte remplace le drill-down sur la VPS concernée

---

## 4. Glossaire express

| Terme | Signification |
|---|---|
| **V5.3** | Le système actuel codé dans `v53_trading_system/src/` (357 .py, 1026 tests) |
| **V3.7** | Spec doctrinale "THE IRON HUNTER" (`ia lab vps v5.3/v3.7/SPECIFICATION_TECHNIQUE_COMPLETE_V37.md`), papier uniquement, lignée parallèle abandonnée |
| **Engine A/B/C/D** | Les 4 stratégies codées en dur dans `src/engines/` |
| **LOCAL_REPLAY** | Phase 1 du protocole de promotion : rejeu historique |
| **SHADOW** | Phase 2 : paper trading temps réel sans soumettre d'ordres. Découpée en 3 sous-paliers : 1 mois → 2 mois → 3 mois, **chaque palier validé manuellement par l'humain** avant promotion |
| **MICRO_LIVE** | Phase 3 : ordres réels sur capital minimal (<5 % du total = 500 USD max) |
| **LIVE** | Phase 4 : capital cible (10 000 USD) |
| **P0** | Bloquant — sans ça, **pas de live trade possible** |
| **P1** | Bloquant pour scaler — sans ça, **pas de capital >5 % du target** |
| **P2** | Amélioration — sans ça, **dette technique acceptable à court terme** |
| **Halal** | Conforme charia : spot only, no leverage, no short, no margin, no riba, screening pairs |
| **Sharia layer** | Module à créer pour enforcer les règles halal de manière non-contournable |
| **Local IA Lab** | Environnement local de calibration / backtest / R&D / stress test, **pas exposé au capital réel** |
| **VPS** | Environnement de prod single-node (Hetzner CX43), uniquement runtime trading |
| **Artefact** | Fichier immuable produit par le pipeline (manifest, decisions, fills, snapshots) qui sert de source de vérité pour l'audit et la calibration |
| **Seuil dynamique** | Seuil qui n'est jamais hardcodé : sa valeur vient d'un fichier de calibration produit par le Local IA Lab et signé pour usage VPS |

---

## 5. Décisions clés (à valider avant de démarrer)

Décisions à prendre avant que l'agent codeur commence. Elles sont détaillées dans `10_DECISIONS_REQUIRED.md`. Court résumé :

1. **Exchange cible** : Binance Spot, Kraken, autre ?
2. **École fiqh / référence sharia** : doctrine arrêtée ou cadre par défaut à valider ?
3. **Juridiction fiscale** : pour décider d'inclure ou non un export tax CSV
4. **VPS confirmé** : Hetzner CX43 (proposé), ou autre ?
5. **Stablecoin policy** : USDT vs USDC vs autre, avec justification fatwa
6. **Limites de capital MICRO_LIVE** : 200 USD initial ? 500 USD ?
7. **Gates humains shadow** : qui valide les passages 1m → 2m → 3m, et avec quels critères ?
8. **Calibration des seuils dynamiques** : qui produit les fichiers de calibration et qui les signe ?

**Sans réponses à ces 8 questions, aucune tranche de code ne peut démarrer.**

---

## 6. Verdict de l'audit S1→S4 en une phrase

> V5.3 est sérieux mais pas prêt pour 10 k$ réels en halal — il manque ~10 briques (5 P0, 5 P1) qui représentent 8 à 12 tranches de code pour l'agent codeur (Sonnet), plus **minimum 3 mois de SHADOW validés humainement par paliers (1m → 2m → 3m)** avant tout passage en MICRO_LIVE, plus 1-2 mois MICRO_LIVE avant capital cible.

**Suite logique** : `01_VERDICT_V53_VS_V37.md`.


---

## Source: docs/production_deployment_plan/01_VERDICT_V53_VS_V37.md

# Verdict V5.3 vs V3.7 pour 10 k$ halal spot VPS

> **TL;DR** — V5.3 tient mieux le coup que V3.7. Pas de débat. Et ce serait vrai même si V3.7 était entièrement codé.

---

## 1. La question

Tu as deux corpus :
- **V5.3** : un système de trading codé en Python (357 .py, 1026 tests, dans `v53_trading_system/src/`).
- **V3.7** : une spec doctrinale "THE IRON HUNTER" datée 2026-01-17, mention "PROD" (`ia lab vps v5.3/v3.7/SPECIFICATION_TECHNIQUE_COMPLETE_V37.md`, 4830 lignes, 170 KB).

Ton use case est **non négociable** :
- Trading **spot** uniquement (pas de futures, pas de perpétuels, pas de margin)
- **Halal** : no leverage, no short, no riba, no funding rate income
- Capital **10 000 USD**
- Déploiement **VPS single-node**, 24/7 sans supervision permanente
- Tu vas commit **du vrai argent**, pas de paper trading indéfini

La question de fond : **lequel des deux est le bon point de départ ?**

---

## 2. Verdict en une phrase

> **V5.3 est le bon canon. V3.7 ne contribue pas un seul module utilisable, juste 3 idées conceptuelles à incorporer en version simplifiée.**

---

## 3. Pourquoi V5.3 gagne — la matrice non-négociable

### 3.1 Critères qui décident pour du capital réel

| Critère | V5.3 | V3.7 |
|---|---|---|
| **Code existant** | ✓ 357 .py, 1026 tests passing | ✗ papier uniquement, 0 ligne de code |
| **Auditabilité des décisions** | ✓ artifacts immuables, manifests, DAG validator, feature locks | ~ conçue, non vérifiable |
| **Discipline de déploiement** | ✓ pipeline LOCAL_REPLAY → SHADOW → MICRO_LIVE → LIVE codé | ~ Docker Compose décrit |
| **Résilience crash** | ✓ `smoke_bootstrap_recovery/` codé | ? assumé via Redis |
| **Coût d'infra à 10 k$** | ✓ ~0 USD/an (file-based, pas de Redis/DB) | ✗ ~240–480 USD/an (Redis + Timescale + Docker → VPS 8-16 GB RAM = **2.4 à 4.8 % du capital uniquement en infra**) |

### 3.2 Briques production-grade déjà codées dans V5.3

Liste exhaustive (cartographie en `02_V53_PRODUCTION_AUDIT.md`). Aucune n'existe dans V3.7 :

| Domaine | V5.3 | V3.7 |
|---|---|---|
| Kill switch persistant disque + flag externe | ✓ `risk_backbone/emergency_kill_switch/circuit_breaker.py` | ∅ |
| Reconciliation order/fill/position | ✓ 5 fichiers `execution_backbone/reconciliation_layer/` | ∅ |
| Loss budget + drawdown guard + projected loss | ✓ 5 fichiers `risk_backbone/loss_budgeter/` | ~ mentionné |
| Exposure budget + position cap | ✓ 4 fichiers `risk_backbone/exposure_budgeter/` | ~ mentionné |
| BTC factor guard (beta hedging) | ✓ 4 fichiers `risk_backbone/btc_factor_guard/` | ∅ |
| Correlation cluster guard | ✓ 5 fichiers `risk_backbone/correlation_cluster_guard/` | ∅ |
| Fee meter + adverse selection + ELW + partial fill | ✓ 5 fichiers `execution_backbone/execution_cost_meter/` | ∅ |
| Order state tracker + latency meter + fill aggregator | ✓ 5 fichiers `execution_backbone/fill_tracker/` | ∅ |
| Venue constraints | ✓ `execution_backbone/venue_constraints_provider.py` | ∅ |
| Phantom trade guard | ✓ `portfolio_minimal/allocation_router/phantom_trade_guard.py` | ∅ |
| Hard block gate | ✓ `scoring_backbone/hard_block_gate/` | ∅ |
| Data freshness + contradiction checker | ✓ `data_backbone/freshness_checker/`, `consistency_checker/` | ∅ |
| Local replay simulator | ✓ `local_replay_runtime/shadow_execution_simulator.py` | ∅ |

**Conclusion empirique** : V5.3 a déjà ~30 modules production-grade codés. V3.7 a 0. Pour du capital réel, le ratio code/papier est l'argument décisif.

### 3.3 Ce que V5.3 N'A PAS et qui devrait t'inquiéter

V5.3 gagne le match face à V3.7 mais **n'est pas pour autant prêt** pour 10 k$ réels. Trous identifiés :

| Trou | Sévérité | Détaillé dans |
|---|---|---|
| Pas d'exchange adapter concret (Binance/Kraken) — l'`execution_runtime` est abstrait | **P0** | `03_GAPS_P0.md` |
| Pas de halal compliance layer (`grep halal` → 0 fichier dans `src/`) | **P0** | `03_GAPS_P0.md` |
| Pas de fee-aware minimum-edge filter | **P0** | `03_GAPS_P0.md` |
| Pas de sealed secrets pour API keys | **P0** | `03_GAPS_P0.md` |
| Engine C et D sous-testés (ratio 1:10 vs A/B) | **P0/P1** | `03_GAPS_P0.md` |
| Pas de regime awareness (engines tournent identiquement en bull/bear/capitulation) | **P1** | `04_GAPS_P1.md` |
| Pas de gatekeeper central auditable (autorisation distribuée) | **P1** | `04_GAPS_P1.md` |
| Pas d'alerting externe (Telegram/email) | **P1** | `04_GAPS_P1.md` |
| Pas de disk monitor / log rotation | **P1** | `04_GAPS_P1.md` |
| Pas de reconciliation périodique forcée (existe mais déclenchement à vérifier) | **P1** | `04_GAPS_P1.md` |

---

## 4. Pourquoi V3.7 perd — au-delà de "c'est du papier"

Même si on ignore le fait que V3.7 n'est pas codé, sa philosophie architecturale est mauvaise pour ton use case :

### 4.1 Infrastructure surdimensionnée

V3.7 assume :
- Redis pub/sub
- TimescaleDB
- Docker Compose multi-services
- VPS 32 GB RAM minimum
- API REST FastAPI

**Coût annuel infra** ≈ 240–480 USD/an = 2.4 à 4.8 % du capital. Tu commences avec un drag de 2-5 % avant même d'avoir tradé.

V5.3 est file-based : 0 USD d'infra additionnelle, fit sur un VPS 4 GB RAM à 5-10 USD/mois = 60-120 USD/an = 0.6-1.2 %. **4x moins de drag.**

### 4.2 Complexité disproportionnée pour 10 k$

V3.7 décrit :
- 7 clusters de stratégies (P, C-1, C0, C1, C3, C4, C9)
- 7 régimes de marché (R1-R6 + R∅)
- OSCAE composite scoring 5-dimensions
- MAS Meta-Cognitive layer
- Strategy Registry + Shadow Trading Engine + StrategyManifest immuables
- Pipeline R&D SHG → SQL → SOE
- ExploitationDetector + StrategyRandomizer (anti-RL adverse)

**Surface de bugs énorme**. À 10 k$ avec 5-8 positions max concurrentes, **tu n'as pas besoin de 7 clusters**. Tu as besoin de 1 ou 2 stratégies qui marchent et qui ne perdent pas d'argent quand le régime change. La complexité V3.7 est dimensionnée pour un fonds avec 10+ stratégies actives et plusieurs millions d'AUM.

### 4.3 Anti-exploit sans cible

V3.7 prévoit `StrategyRandomizer` (randomisation déterministe des paramètres pour contrer le RL adverse) et `ExploitationDetector`. Ces briques font sens contre des HFT qui font du reverse engineering sur ton flow.

**À 10 k$ tu n'es pas une cible adverse. Tu es du bruit dans le book.** Aucun MM ne va dépenser de la compute pour reverse-engineer 5 trades par jour à 200 USD chacun. ROI de ces briques en V5.3 = quasi nul.

### 4.4 Pas de feature locks

V3.7 n'a aucun mécanisme équivalent au `feature_lock_contracts` de V5.3. C'est une **régression** par rapport à V5.3 :
- Sans feature locks, n'importe quelle modification d'une feature coule silencieusement dans la prod
- Risque de leakage temporel ou de drift de définition non détecté
- Audit post-mortem rendu beaucoup plus difficile

V5.3 a la bonne posture défensive ; V3.7 ne l'a pas pensée.

---

## 5. Ce qu'on garde de V3.7

Trois idées seulement, et **adaptées en version simplifiée**, pas importées telles quelles. Détaillées dans `05_V37_BRICKS_INCORPORATION.md` :

1. **Regime awareness** — version "lite" 3 états (calm / stressed / extreme), pas la version V3.7 à 7 régimes
2. **Execution Gatekeeper central** — wrapper `authorize()` autour des guards existants, pas une réécriture de l'autorisation
3. **Information Stress Monitor** — détecteur "le marché ment" temps réel, inspiré de MAS V3.7 mais 10x plus simple

**Ces trois idées représentent ~30 % d'une seule session Opus de code chacune**. Pas une réécriture, pas une migration, pas une dette doctrinale.

---

## 6. Ce qu'on rejette explicitement de V3.7

| Brique V3.7 | Raison du rejet |
|---|---|
| **OSCAE composite scoring** (5-dim E/C/M/L/S) | Le `scoring_backbone` de V5.3 fait déjà ce travail, intégré aux 4 engines. Réécrire = casser 1026 tests. ROI négatif. |
| **Strategy Registry + StrategyManifest** | Tes 4 engines sont des "stratégies de fait", pas besoin de registry dynamique. À 10 k$ tu valides ce que tu as, tu n'introduis pas de nouvelles stratégies. |
| **Shadow Trading Engine** (entité séparée) | Le pipeline V5.3 `protocols/shadow_runtime.py` couvre déjà ce besoin sous une forme différente. |
| **Pipeline R&D SHG → SQL → SOE** | Surdimensionné pour 10 k$. Le `meta_learning/` existant fait l'essentiel (apprentissage hyperparamètres). |
| **StrategyRandomizer anti-RL** | Aucune cible adverse à 10 k$. ROI quasi nul. |
| **ExploitationDetector** | Idem. |
| **Stack Redis + TimescaleDB + Docker Compose** | Coût > 2 % du capital. Stack file-based V5.3 plus appropriée pour single-node 10 k$. |
| **REST API FastAPI** | Aucun client externe. Inutile à 10 k$. |
| **7 clusters / 7 régimes** | Surdimensionné. Regime "lite" 3 états suffit. |

---

## 7. Conclusion opérationnelle

| Question | Réponse |
|---|---|
| On garde V5.3 ? | **Oui, c'est le canon.** |
| On migre vers V3.7 ? | **Non.** Aucune brique V3.7 ne justifie le coût de migration. |
| On ignore V3.7 totalement ? | **Non.** Trois idées simplifiées sont à incorporer (regime lite, gatekeeper central, info stress). |
| V5.3 est tradable telle quelle à 10 k$ ? | **Non.** ~10 briques manquantes (5 P0, 5 P1). |
| Combien de sessions Opus pour combler les manques ? | **7 à 10 sessions de code** + 1 session vérification, soit 8-11 au total. Voir `09_OPUS_CODING_SESSIONS.md`. |

**Suite logique** : `02_V53_PRODUCTION_AUDIT.md` pour cartographier précisément ce qui existe déjà.


---

## Source: docs/production_deployment_plan/02_V53_PRODUCTION_AUDIT.md

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


---

## Source: docs/production_deployment_plan/03_GAPS_P0.md

# Gaps P0 — Manques bloquants avant tout live trade

> **Définition P0** : sans cette brique, **aucun trade live n'est acceptable**. P0 = "no-go" absolu.
> Ces 5 manques doivent être tous comblés avant la phase MICRO_LIVE (ordre réel le plus petit).

> **Gabarit MD attendu pour chaque chantier ci-dessous** (rappel `00_README.md` § 0) :
> 1. Objectif — 2. Périmètre — 3. Invariants — 4. Modules touchés — 5. Interfaces I/O — 6. Ce qu'il ne faut PAS faire — 7. Critères d'acceptation — 8. Ordre de réalisation — 9. Preuves / tests attendus.
> Les sections ci-dessous fournissent le contenu utile pour ces 9 points. L'agent codeur Sonnet doit s'aligner sur ce gabarit avant chaque tranche.

> **Seuils dynamiques** (rappel) — Aucun seuil P0 ne doit être hardcodé. Chaque seuil candidat est listé dans `11_DYNAMIC_THRESHOLDS_CATALOG.md` avec sa source de calibration (artefact backtest) et son protocole de validation shadow.

---

## Vue d'ensemble

| # | Manque | Sévérité | LOC estimées | Tranches code (agent codeur) |
|---|---|---|---|---|
| P0-1 | Exchange adapter Binance Spot production-grade | **Critique** | 2500-4000 | 3-4 |
| P0-2 | Halal compliance layer | **Critique** | 800-1200 | 1-2 |
| P0-3 | Fee-aware minimum-edge filter | **Critique** | 150-300 | 0.5 |
| P0-4 | Sealed secrets / API key loader | **Critique** | 200-400 | 0.5 |
| P0-5 | Engine C / D rattrapage tests + audit | **Élevé** | 600-1500 | 1-3 |

**Total P0** : ~4250-7400 LOC, **6-10 tranches** pour l'agent codeur. Voir `09_CODING_SLICES_FOR_IMPLEMENTING_AGENT.md` pour le détail.

---

## P0-1 — Exchange adapter Binance Spot production-grade

### Pourquoi P0

Sans connecteur exchange concret, le système ne peut **littéralement pas** soumettre d'ordres réels. L'`execution_runtime.py` actuel semble abstrait (à confirmer S5a). Même s'il y a un stub, il n'a probablement pas la robustesse nécessaire pour 24/7 sur VPS avec capital réel.

### Risque si pas fait

| Risque | Impact |
|---|---|
| Pas de trade possible | 100 % blocage |
| Si stub utilisé en live | Bugs silencieux, ordres perdus, double-soumission, désync |

### Localisation cible

```
src/venue_adapters/
└── binance_spot/
    ├── __init__.py
    ├── rest_client.py              [HTTP signed REST, retry, rate limit]
    ├── ws_client.py                [WebSocket: account stream, market stream]
    ├── order_translator.py         [V5.3 OrderIntent → Binance API + return mapping]
    ├── account_snapshotter.py      [source of truth: balances, positions, open orders]
    ├── error_classifier.py         [retryable vs fatal vs ban-warning]
    ├── credential_loader.py        [sealed secrets, never plaintext]
    ├── time_sync.py                [serverTime check, NTP drift detect]
    ├── contracts.py                [pydantic models pour les payloads]
    └── tests/
        ├── test_rest_client.py
        ├── test_ws_client.py
        ├── test_order_translator.py
        ├── test_account_snapshotter.py
        ├── test_error_classifier.py
        ├── test_idempotency.py
        └── test_integration_testnet.py    [contre Binance testnet]
```

### Spécifications techniques détaillées

#### `rest_client.py`

**Responsabilités** :
- HMAC-SHA256 signing avec timestamp + recvWindow
- Rate limiter token bucket (Binance : 1200 req/min REST, 50 orders/10s, 160k orders/24h)
- Retry exponentiel sur erreurs réseau et 5xx, **PAS sur 4xx** (sauf 429 Rate Limit)
- Backoff sur 418 (IP banned warning) et 429 avec lecture du `Retry-After`
- Métriques exposées : latence p50/p95/p99, taux d'erreur, requests count
- **Idempotency** : tout POST `/api/v3/order` doit utiliser `newClientOrderId` déterministe (UUIDv5 sur intent_id)

**Endpoints minimum** :
- `GET /api/v3/exchangeInfo` (au boot, cache 24h)
- `GET /api/v3/account` (snapshot balances)
- `GET /api/v3/openOrders` (état réel)
- `POST /api/v3/order` (placement)
- `DELETE /api/v3/order` (cancel)
- `GET /api/v3/order` (lookup par clientOrderId)
- `GET /api/v3/myTrades` (historique fills pour reconciliation)

**Anti-pattern** : ne pas utiliser `python-binance` ou `ccxt` directement. Wrapper minimal si besoin, mais le code production doit avoir le contrôle total des erreurs.

#### `ws_client.py`

**Responsabilités** :
- 2 streams : `userDataStream` (account events) et `marketStream` (book + trades)
- Heartbeat : ping toutes les 3 min, pong attendu sous 10 min sinon reconnect
- **Gap detection** : sur reconnect, REST replay obligatoire des events manqués
- Session keepalive : `PUT /api/v3/userDataStream` toutes les 30 min (sinon disconnect après 60 min)
- Auto-reconnect avec backoff exponentiel (max 30 s)
- **Buffering** : pendant le reconnect, événements en queue avec timestamp pour reconstruction post-recovery

**Critique** : pendant un disconnect, le système doit refuser tout nouveau trade (état "stale") jusqu'à reconciliation complète.

#### `order_translator.py`

**Responsabilités** :
- Conversion `OrderIntent` (contrat V5.3 interne) → payload Binance
- Application des `venue_constraints` : minNotional, stepSize, lotSize, tickSize
- Truncation propre (PAS d'arrondi vers le haut qui pourrait dépasser balance)
- Mapping retour : Binance order response → `OrderState` interne
- **Validation pré-envoi** : refuse si quantity < minQty, notional < minNotional, prix > 5x mid (sécurité fat-finger)

**Cas d'erreur à gérer explicitement** :
- `INSUFFICIENT_BALANCE` → log + skip
- `LOT_SIZE` → recalcul après truncation
- `MIN_NOTIONAL` → skip avec raison loggée
- `PRICE_FILTER` → skip
- `MARKET_LOT_SIZE` → skip

#### `account_snapshotter.py`

**Responsabilités** :
- Snapshot complet du compte : balances par asset, open orders, positions (= balances non-zéro pour spot)
- **Source of truth** pour `position_reconciler.py` (V5.3 existant)
- Snapshot au boot OBLIGATOIRE
- Snapshot périodique (toutes les 5 min minimum)
- Persist snapshot dans artifact pour audit post-mortem

#### `error_classifier.py`

**Responsabilités** :
Classification de toute erreur Binance en 3 catégories :
- **RETRYABLE** : 5xx, network timeout, 429 → retry avec backoff
- **FATAL_LOCAL** : -2010 INSUFFICIENT_BALANCE, -2011 UNKNOWN_ORDER → log + skip ce trade
- **FATAL_GLOBAL** : -1003 TOO_MANY_REQUESTS si répété, 418 IP_BANNED, -2014 BAD_API_KEY → **trip kill switch immédiat**

#### `credential_loader.py`

**Responsabilités** :
- **Jamais** de plaintext en variable d'environnement ou fichier non chiffré
- Options de stockage (à choisir) :
  1. **OS keyring** (`keyring` package, intégré à libsecret/keychain)
  2. **Sealed secrets** (chiffrement local avec passphrase saisie au démarrage)
  3. **HashiCorp Vault** (overkill à 10 k$, écarter)
- Au démarrage, prompt passphrase si sealed secrets, ou unlock keyring
- Vérification API key permissions au boot : **trading uniquement, withdraw désactivé**, sinon refuse de démarrer

#### `time_sync.py`

**Responsabilités** :
- Au boot et toutes les heures, comparer `time.time()` avec `GET /api/v3/time`
- Si drift > 500 ms → warning
- Si drift > 1000 ms → kill switch trip (les ordres timestampés vont être rejetés par Binance)
- Recommandation : `chronyd` ou `ntpd` actif sur le VPS

### Coût en sessions Opus

| Sous-tâche | LOC | Sessions |
|---|---|---|
| `rest_client.py` + tests | 600-900 | 0.5 |
| `ws_client.py` + tests | 500-800 | 0.5 |
| `order_translator.py` + tests | 400-600 | 0.25 |
| `account_snapshotter.py` + tests | 300-400 | 0.25 |
| `error_classifier.py` + tests | 200-300 | 0.1 |
| `credential_loader.py` + tests | 200-400 | 0.1 |
| `time_sync.py` + tests | 100-200 | 0.05 |
| Integration testnet | — | 0.25 |
| **Total** | **2500-4000** | **2.0** |

### Dépendances

- Aucune dépendance interne avant. Premier chantier à attaquer.
- Intégration avec `execution_runtime.py` : à faire après que l'adapter passe les tests testnet.

### Critères d'acceptation

- [ ] 100 % des endpoints minimum implémentés
- [ ] Tests unitaires couverture > 80 %
- [ ] Tests d'intégration testnet passent (au moins 10 trades de cycle complet)
- [ ] Idempotency vérifiée (double soumission rejetée par clientOrderId)
- [ ] Reconnect WebSocket vérifié (kill manuel du process WS, recovery sous 30 s)
- [ ] Time drift simulation : drift > 1 s déclenche kill switch
- [ ] Aucun plaintext de clé API détectable dans le code, les logs, ou les artifacts

---

## P0-2 — Halal compliance layer

### Pourquoi P0

`grep halal\|sharia` dans `src/` → **0 fichier**. Le système peut actuellement trader **n'importe quoi** y compris des futures, perpétuels, margin, ou tokens explicitement non-halal. **Ce n'est pas négociable** : sans cette couche, la cible "halal" est fictive.

### Risque si pas fait

| Risque | Impact |
|---|---|
| Trader un asset non-halal par défaut | Drift sharia silencieux, gains à purifier |
| Soumettre un short par accident (bug futur) | Violation halal directe |
| Activer Binance Earn par erreur | Riba, violation totale |
| Pas d'audit trail des décisions sharia | Impossible de prouver la conformité |

### Localisation cible

```
src/sharia_compliance/
├── __init__.py
├── contracts.py                    [pydantic: AssetPolicy, TradePolicy, AuditEvent]
├── asset_whitelist.py              [liste de pairs autorisées + raison]
├── asset_blacklist.py              [exclusions explicites: gambling, riba, etc.]
├── stablecoin_policy.py            [USDT/USDC/FDUSD: décision documentée]
├── trade_type_guard.py             [HARD REJECT toute action non-spot, no-short, no-margin]
├── purification_calculator.py      [si dividend/staking accidentel: portion à purifier]
├── policy_audit_logger.py          [log immutable de toutes les décisions sharia]
├── sharia_runtime.py               [orchestrateur, exposé comme gate global]
└── tests/
    ├── test_asset_whitelist.py
    ├── test_trade_type_guard.py
    ├── test_stablecoin_policy.py
    ├── test_purification.py
    └── test_integration_with_scoring_backbone.py
```

### Spécifications techniques détaillées

#### `asset_whitelist.py`

**Format** :
```python
HALAL_WHITELIST: dict[str, AssetPolicy] = {
    "BTC": AssetPolicy(
        symbol="BTC",
        allowed=True,
        reason="Bitcoin is widely accepted as halal by major scholars (...)",
        scholar_references=["AAOIFI Standard 17", "Mufti Faraz Adam (2018)"],
        last_review_date="2026-04-01",
        review_period_days=180,
    ),
    "ETH": AssetPolicy(...),
    # ... 10-20 pairs maximum
}
```

**Règles** :
- Whitelist explicite, pas de "autorisé par défaut"
- Chaque entrée a une `reason` documentée et au moins une `scholar_reference`
- `last_review_date` + `review_period_days` : périodiquement, le système alerte si une review est due
- À la review, on vérifie si l'asset est toujours conforme (ex: un coin qui ajoute des features de lending devient non-conforme)

#### `asset_blacklist.py`

**Catégories** :
- Gambling (FUN, etc.)
- Lending protocols (AAVE, COMP, MKR — débat, prudence)
- Privacy coins (XMR, ZEC — débat AML, certains pays)
- Tokens explicitement riba (toute stablecoin non-asset-backed)
- Tokens d'exchanges non-conformes
- Tokens identifiés comme scam ou pump-and-dump

#### `stablecoin_policy.py`

**Décision à documenter explicitement** :
```python
STABLECOIN_POLICY = StablecoinPolicy(
    accepted=["USDT"],          # ou ["USDC"] ou ["FDUSD"] ou combinaison
    rejected=[],
    rationale="...",
    scholar_reference="...",
    review_date="2026-04-01",
)
```

USDT/USDC sont **débattus**. La décision doit être prise et **figée** dans le code, pas laissée au hasard.

#### `trade_type_guard.py`

**Hard reject** au niveau du `intent_builder` (V5.3 existant). Refuse :
- Tout `OrderIntent` avec `side=SHORT` ou `position_type=SHORT`
- Tout `OrderIntent` avec `leverage > 1.0` ou `margin_required=True`
- Tout `OrderIntent` sur une pair non-whitelist
- Tout `OrderIntent` sur un type de produit non-spot (futures, perp, swap)

**Code structure** :
```python
def authorize_trade_type(intent: OrderIntent) -> SharaiVerdict:
    if intent.side == Side.SHORT:
        return SharaiVerdict(
            allowed=False,
            reason="SHORT_FORBIDDEN",
            detail="Short selling is not permitted under spot halal policy",
        )
    if intent.leverage > 1.0:
        return SharaiVerdict(allowed=False, reason="LEVERAGE_FORBIDDEN", ...)
    if intent.pair not in HALAL_WHITELIST:
        return SharaiVerdict(allowed=False, reason="PAIR_NOT_WHITELISTED", ...)
    # ... etc
    return SharaiVerdict(allowed=True, ...)
```

**Intégration** : appelé **avant** `execution_guard.py` dans `execution_runtime.py`. Si refus → log + skip + audit.

#### `purification_calculator.py`

Cas d'usage : un airdrop, fork, ou staking accidentel a généré un revenu non-halal. Le module calcule la portion à purifier (à donner en charité).

**À 10 k$ ce n'est pas central** mais doit exister pour être complet. Implémentation minimale :
```python
def calculate_purification(
    asset_received: str,
    quantity: Decimal,
    source: SourceType,  # AIRDROP, FORK, STAKING, INTEREST
) -> PurificationAmount:
    ...
```

#### `policy_audit_logger.py`

**Log immutable** de toutes les décisions sharia :
- Format JSON Lines append-only
- Champs : timestamp, intent_id, decision (allow/reject), reason, policy_version
- Stockage dans artifact `sharia_audit_log/` rotaté quotidien
- Jamais effaçable depuis le code

### Coût en sessions Opus

| Sous-tâche | LOC | Sessions |
|---|---|---|
| `contracts.py` + `asset_whitelist.py` + `asset_blacklist.py` | 200-300 | 0.15 |
| `stablecoin_policy.py` | 50-100 | 0.05 |
| `trade_type_guard.py` + tests | 200-300 | 0.15 |
| `purification_calculator.py` + tests | 150-200 | 0.10 |
| `policy_audit_logger.py` + tests | 100-150 | 0.05 |
| `sharia_runtime.py` (orchestrateur) | 100-150 | 0.05 |
| Intégration avec `execution_runtime.py` + tests | — | 0.25 |
| **Total** | **800-1200** | **~0.8** |

### Dépendances

- Aucune dépendance externe.
- Décision préalable : choix de la doctrine fiqh + scholar references (voir `10_DECISIONS_REQUIRED.md`).

### Critères d'acceptation

- [ ] Whitelist contient 10-20 pairs validés avec scholar reference
- [ ] Stablecoin policy figée et documentée
- [ ] Tests démontrent que SHORT, LEVERAGE, MARGIN, FUTURES sont **impossibles à passer**
- [ ] Tests démontrent qu'une pair non-whitelist est rejetée avant `execution_guard`
- [ ] Audit log immutable vérifié (essai de modification rétro échoue)
- [ ] Au moins 1 review check : si `review_date + review_period_days < today`, warning au boot

---

## P0-3 — Fee-aware minimum-edge filter

### Pourquoi P0

À 10 k$ avec fees Binance ~0.10 % par leg, un round-trip coûte 0.20 %. Une stratégie qui ne bat pas **2× cette barre (= 0.40 %)** brûle de la valeur. Le `fee_meter.py` existant mesure ex-post mais **aucun gate ex-ante** n'empêche un trade à edge insuffisant.

### Risque si pas fait

| Risque | Impact |
|---|---|
| Trades à edge < fees | Saigne lente garantie. À 5 trades/jour ratant ce gate, **-30 à -50 USD/jour de drag pur** = **-9 000 à -15 000 USD/an**. |
| À 10 k$ → ruine annuelle si non corrigé | 100 % du capital |

### Localisation cible

Greffé dans `execution_backbone/order_decider/execution_guard.py` (existant) ou comme nouveau module :

```
src/execution_backbone/order_decider/
└── fee_aware_edge_gate.py    [nouveau]
```

### Spécifications techniques

```python
class FeeAwareEdgeGate:
    """
    Refuse un trade dont l'edge attendu est inférieur au seuil de couverture des fees.

    Règle : edge_expected_bps >= K * fees_round_trip_bps
    Default K = 2.0 (chaque trade doit théoriquement faire au moins 2x les fees)
    """

    def __init__(
        self,
        fee_provider: FeeProvider,
        edge_multiplier: float = 2.0,
        min_absolute_edge_bps: float = 30.0,  # absolu plancher
    ) -> None:
        ...

    def check(self, intent: OrderIntent, expected_edge_bps: float) -> EdgeGateVerdict:
        fees_round_trip = self.fee_provider.estimate_round_trip_bps(intent.pair)
        threshold = max(
            fees_round_trip * self.edge_multiplier,
            self.min_absolute_edge_bps,
        )
        if expected_edge_bps < threshold:
            return EdgeGateVerdict(
                allowed=False,
                reason="EDGE_INSUFFICIENT_VS_FEES",
                detail=f"edge={expected_edge_bps:.1f}bps < threshold={threshold:.1f}bps",
            )
        return EdgeGateVerdict(allowed=True, ...)
```

**Intégration** :
- Appelé après `sharia_runtime` (P0-2) et avant `execution_guard` (existant)
- L'`expected_edge_bps` doit être fourni par le scoring (ajouter le champ dans `OrderIntent` si absent)

### Coût

| Sous-tâche | LOC | Sessions |
|---|---|---|
| `fee_aware_edge_gate.py` + tests | 150-300 | 0.25 |

### Critères d'acceptation

- [ ] Gate refuse correctement les trades en dessous du seuil
- [ ] Configuration `edge_multiplier` exposée (pour tuning futur)
- [ ] `min_absolute_edge_bps` configurable
- [ ] Logs structurés contenant edge, threshold, fees calculés
- [ ] Tests unitaires couvrent les cas limites (edge = threshold, edge = 0, fees = 0)

---

## P0-4 — Sealed secrets / API key loader

### Pourquoi P0

Stocker les clés API exchange en variable d'environnement ou dans un fichier en clair sur le VPS = risque inacceptable. Une seule exfiltration (compromission SSH, log accidentel, backup non chiffré) = perte totale du capital si la clé a `withdraw=true`. Mais même avec `withdraw=false`, l'attaquant peut trader contre toi (wash trading, vendre tes positions à zéro).

### Risque si pas fait

| Risque | Impact |
|---|---|
| Compromission VPS → clés en clair | 100 % du capital |
| Clé API loggée accidentellement | 100 % du capital |
| Backup VPS non chiffré → clé exposée | 100 % du capital |

### Solution recommandée

**Option A — OS keyring** (recommandé pour single-VPS)
- Package Python `keyring`
- Backend : `SecretService` sur Linux (libsecret/gnome-keyring)
- Pro : standard OS, pas de gestion de passphrase
- Con : nécessite que le keyring soit déverrouillé au boot

**Option B — Sealed secrets avec passphrase**
- Chiffrement local avec `cryptography.fernet` + passphrase
- Au boot, le système prompte la passphrase (saisie SSH manuelle)
- Pro : indépendant du keyring OS, fonctionne en mode minimal
- Con : nécessite saisie manuelle au boot (incompatible avec restart automatique)

**Recommandation** : Option A en principal, Option B en fallback documenté.

### Localisation cible

Déjà couvert dans P0-1 sous `venue_adapters/binance_spot/credential_loader.py`. Ce gap est juste l'aspect "stockage" du problème.

### Coût

Compté dans P0-1 (200-400 LOC, 0.25 session).

### Critères d'acceptation

- [ ] Aucun plaintext de clé API détectable par grep dans `src/`, `tests/`, `logs/`, `artifacts/`
- [ ] Loader vérifie au boot que la clé a `enable_spot_trading=true` et `enable_withdrawals=false`
- [ ] Si keyring inaccessible → refuse de démarrer (pas de fallback silencieux vers env var)
- [ ] Test unitaire : tentative de log de la clé via `repr()` ou `str()` ne révèle rien

---

## P0-5 — Engine C / D rattrapage tests + audit

### Pourquoi P0 (ou P1, à arbitrer)

Audit S3 a identifié : engines C et D ont **~7 tests chacun** vs ~67-70 pour A et B. Ratio 1:10. À 10 k$ tu peux décider de :

**Option A** : démarrer LIVE avec **engine A seul** (le plus mature) → engines C/D restent à durcir mais ne bloquent pas le live → C/D rattrapés en P1
**Option B** : tu veux les 4 engines actifs en live → C/D doivent être rattrapés en P0

**Ma recommandation** : **Option A**. Démarre avec engine A seul, valide le pipeline complet (adapter + halal + fee gate + risk + reconciliation) sur une seule stratégie. Tu réduis la surface de bugs et tu apprends. Engines C/D arrivent en Phase 3 ou Phase 4.

### Risque si non rattrapé (Option B)

| Risque | Impact |
|---|---|
| Bug silencieux dans engine_c/d | Pertes non détectées |
| Désync entre engines | Décisions contradictoires |
| Pas d'edge réel mesuré | Trades aveugles |

### Localisation

Si Option B retenue :
```
tests/test_engines/test_engine_c/    [à étoffer de ~7 à ~70 tests]
tests/test_engines/test_engine_d/    [idem]
```

Et possiblement refactor de :
```
src/engines/engine_c/engine_c_runtime.py    [monolithe → modules]
src/engines/engine_c/engine_c_runner.py
```

### Spécifications

#### Si Option A (engine A seul en démarrage)

- Pas de code engine_c/d en P0
- Ajouter un **feature flag** dans `protocols/` qui permet d'activer engines selectivement : `engines_active = ["engine_a"]`
- Engines C/D restent dans le repo, marqués `experimental` en docstring
- Décision de les rattraper différée à Phase 3 ou Phase 4

#### Si Option B (rattrapage immédiat)

- Audit fonctionnel : que fait exactement engine_c et engine_d ? (S5a obligatoire)
- Décomposer le monolithe en modules (à l'image d'engine_b/) si nécessaire
- Couvrir au moins :
  - `test_engine_c_runtime.py` : runtime intégré
  - `test_engine_c_runner.py` : runner
  - `test_engine_c_scoring.py` : scoring spécifique
  - `test_engine_c_invalidation.py` : invalidation logic
  - `test_engine_c_edge_cases.py` : cas limites
  - + idem pour engine_d

### Coût

| Option | LOC | Sessions |
|---|---|---|
| **A** (feature flag) | 50-100 | 0.1 |
| **B** (refactor + tests) | 600-1500 | 0.5-1.5 |

### Critères d'acceptation

#### Option A
- [ ] Feature flag opérationnel
- [ ] Engines C/D désactivés par défaut en MICRO_LIVE et LIVE
- [ ] Documentation `BUILD_AUDIT_LOG.md` mise à jour avec décision

#### Option B
- [ ] Couverture test engines C/D ≥ 80 %
- [ ] Tests d'intégration runner ↔ runtime passent
- [ ] Tests cas limites (input vide, input invalide, dégradation gracieuse)
- [ ] 1026 tests existants ne régressent pas

---

## Synthèse P0

### Si Option A engine C/D (recommandée)

| Chantier | LOC | Sessions |
|---|---|---|
| P0-1 Exchange adapter Binance Spot | 2500-4000 | 2.0 |
| P0-2 Halal compliance | 800-1200 | 0.8 |
| P0-3 Fee-aware filter | 150-300 | 0.25 |
| P0-4 Sealed secrets (inclus dans P0-1) | — | — |
| P0-5 Feature flag engines C/D | 50-100 | 0.1 |
| **Total P0** | **3500-5600** | **3.15 sessions** |

### Si Option B engine C/D (max ambition)

| Chantier | LOC | Sessions |
|---|---|---|
| P0-1 Exchange adapter | 2500-4000 | 2.0 |
| P0-2 Halal compliance | 800-1200 | 0.8 |
| P0-3 Fee-aware filter | 150-300 | 0.25 |
| P0-4 Sealed secrets | — | — |
| P0-5 Refactor engines C/D | 600-1500 | 1.5 |
| **Total P0** | **4050-7000** | **4.55 sessions** |

---

## Ordre d'exécution recommandé

```
1. P0-1 (Exchange adapter)         [chantier le plus risqué, à attaquer en premier]
   ├── REST client + sealed secrets
   ├── Order translator
   ├── WebSocket client
   └── Tests testnet                [validation avant de continuer]

2. P0-2 (Halal compliance)
   ├── Whitelist + blacklist
   ├── Trade type guard
   └── Intégration scoring_backbone

3. P0-3 (Fee-aware filter)
   └── Greffe sur execution_guard

4. P0-5 (Décision A ou B sur engines C/D)
```

**Suite logique** : `04_GAPS_P1.md` — manques pour scaler après MICRO_LIVE.


---

## Source: docs/production_deployment_plan/04_GAPS_P1.md

# Gaps P1 — Manques bloquants pour scaler au-delà de MICRO_LIVE

> **Définition P1** : sans cette brique, la phase MICRO_LIVE peut tourner (capital ≤5 % du target = 500 USD), mais **pas LIVE** (capital cible 10 000 USD).
> Ces 5 manques doivent être tous comblés avant la fin de la phase MICRO_LIVE et avant le passage en LIVE.

---

## Vue d'ensemble

> **Rappel gabarit MD Opus** (`00_README.md` § 0) : chaque chantier P1 ci-dessous devrait, au moment de sa prise en charge par l'agent codeur, être vérifié contre le gabarit standardisé (objectif / périmètre / invariants / modules / interfaces / ce qu'il ne faut pas faire / critères d'acceptation / ordre / preuves). Le repo gagne contre le MD.

| # | Manque | Sévérité | LOC estimées | Tranches code (agent codeur) |
|---|---|---|---|---|
| P1-1 | Regime awareness lite (3 états) | Élevé | 400-600 | T9 |
| P1-2 | Reconciliation périodique + au boot | Élevé | 200-300 | T10 |
| P1-3 | Daily P&L circuit breaker câblé | Élevé | 100-200 | T10 |
| P1-4 | Alerting externe (Telegram/email) | Élevé | 200-300 | T11 |
| P1-5 | Disk monitor + log rotation | Moyen | 150-250 | T11 |

**Total P1** : ~1050-1650 LOC, **~3 tranches code** (T9, T10, T11 — voir `09_CODING_SLICES_FOR_IMPLEMENTING_AGENT.md`).

---

## P1-1 — Regime awareness lite (3 états)

### Pourquoi P1

V5.3 utilise actuellement "regime" comme un **simple tag string** passé en entrée aux engines (`engine_inputs.regime`). Aucun composant ne **détecte** le régime de marché. Les engines tournent identiquement en bull, range, capitulation.

**Conséquence quant** : la majorité des stratégies retail crypto ont une perf qui dépend du régime. Une stratégie qui fait +60 % en bull peut faire -40 % en bear. Sans détection de régime, **tu vas livrer de la perf 6 mois puis tout perdre quand le régime change**.

V3.7 a un `RegimeDetector` à 7 états (R1-R6 + R∅). C'est trop granulaire pour 10 k$. Une version **lite à 3 états** suffit largement.

### Risque si pas fait

| Risque | Impact |
|---|---|
| Stratégie qui marche en bull, meurt en bear | -30 à -50 % de drawdown sur changement de régime |
| Pas de désactivation conditionnelle d'engines | Décisions à contre-régime |
| Surface d'alpha non maximisée | Sharpe sous-optimal |

### Localisation cible

```
src/data_backbone/regime_lite/
├── __init__.py
├── contracts.py                    [RegimeState enum + RegimeSnapshot]
├── regime_calculator.py            [calcul des indicateurs et vote final]
├── regime_provider.py              [API publique consommée par les engines]
└── tests/
    ├── test_regime_calculator.py
    └── test_regime_transitions.py
```

### Spécifications techniques

#### États

```python
class RegimeState(StrEnum):
    CALM = "calm"           # vol modérée, spreads tight, range
    STRESSED = "stressed"   # vol élevée, spreads wide, mouvements directionnels
    EXTREME = "extreme"     # capitulation, flash crash, ou euphorie blow-off
```

3 états seulement. Critères :
- **CALM** : vol réalisée 24h BTC < 30 % annualisée, spread médian < 5 bps, drawdown 7j > -5 %
- **STRESSED** : vol réalisée 24h BTC entre 30 % et 80 %, ou spread médian entre 5 et 15 bps, ou DD 7j entre -5 et -15 %
- **EXTREME** : vol > 80 %, ou spread > 15 bps, ou DD 7j < -15 %, ou move > 8 σ en 1h

#### Sources des indicateurs

Pour rester pragmatique : utiliser uniquement les données BTC (proxy macro crypto).
- Vol réalisée 24h BTC : depuis `data_backbone/`
- Spread médian BTC/USDT : depuis order book stream
- Drawdown 7j BTC : compute interne sur klines

**Pas de dépendance externe** (pas de VIX, pas de news feed).

#### Calcul

```python
def calculate_regime(snapshot: MarketSnapshot) -> RegimeSnapshot:
    vol_24h = snapshot.btc_realized_vol_24h_annualized
    spread_med = snapshot.btc_spread_median_bps
    dd_7d = snapshot.btc_drawdown_7d_pct
    move_1h_sigma = snapshot.btc_move_1h_in_sigmas

    if (vol_24h > 0.80
        or spread_med > 15
        or dd_7d < -0.15
        or abs(move_1h_sigma) > 8):
        state = RegimeState.EXTREME
    elif (vol_24h > 0.30
          or spread_med > 5
          or dd_7d < -0.05):
        state = RegimeState.STRESSED
    else:
        state = RegimeState.CALM

    return RegimeSnapshot(
        state=state,
        timestamp=now(),
        vol_24h=vol_24h,
        spread_median_bps=spread_med,
        drawdown_7d=dd_7d,
        move_1h_sigma=move_1h_sigma,
    )
```

#### Hystérésis

**Important** : pour éviter les bascules rapides entre régimes (qui flapperaient les engines), implémenter une **hystérésis temporelle** :
- Pour passer de CALM → STRESSED, condition vraie pendant 15 min consécutives
- Pour passer de STRESSED → CALM, condition vraie pendant 60 min consécutives
- EXTREME est instantané dans les deux sens (sécurité)

#### Intégration avec les engines

Les engines V5.3 acceptent déjà un `regime` string en input. **Aucune modification des engines nécessaire**, juste alimenter ce champ depuis `regime_provider`.

Ajouter dans `protocols/{shadow,micro_live,live_light}_runtime.py` :
```python
regime = regime_provider.get_current_regime()
engine_input = EngineInput(..., regime=regime.state.value)
```

#### Désactivation conditionnelle d'engines

C'est le **vrai bénéfice** du régime : permettre à chaque engine de déclarer dans quels régimes il est actif.

Ajouter une config :
```python
ENGINE_REGIME_GATING = {
    "engine_a": ["calm", "stressed"],          # désactivé en EXTREME
    "engine_b": ["calm"],                      # actif en CALM uniquement
    "engine_c": ["stressed", "extreme"],       # actif en mode mouvant
    "engine_d": ["calm", "stressed", "extreme"],  # always-on
}
```

Le gating se fait dans `portfolio_minimal/opportunity_selector/candidate_pool_builder.py` (ou équivalent) : si engine X propose une opportunité dans un régime non autorisé → reject avec raison `REGIME_GATED`.

### Coût

| Sous-tâche | LOC | Sessions |
|---|---|---|
| `contracts.py` + `regime_calculator.py` + tests | 250-350 | 0.25 |
| `regime_provider.py` (API + cache + hystérésis) | 100-150 | 0.1 |
| Intégration engines + config gating | 50-100 | 0.1 |
| Tests transitions et hystérésis | 100-150 | 0.05 |
| **Total** | **400-600** | **0.5** |

### Critères d'acceptation

- [ ] Calculateur passe par les 3 états sur données historiques de référence (2020-03 = EXTREME, 2021-Q3 = CALM, 2022-05 = STRESSED, etc.)
- [ ] Hystérésis vérifiée : flapping bloqué
- [ ] Gating désactive les engines dans les régimes non autorisés
- [ ] Tests : 100 % couverture du `calculate_regime`
- [ ] Régime exposé dans le dashboard `monitoring/`
- [ ] Régime persisté dans les artifacts pour audit post-mortem

---

## P1-2 — Reconciliation périodique + au boot

### Pourquoi P1

V5.3 a une `reconciliation_layer/` complète (5 modules) mais **il faut vérifier qu'elle est appelée** :
1. **Au boot** du process (obligatoire avant tout trade)
2. **Périodiquement** pendant le runtime (toutes les 5-10 min)

Si la reconciliation n'est qu'**event-driven** (déclenchée par une discordance détectée par autre moyen), il y a un trou : un drift silencieux peut s'accumuler.

### Risque si pas fait

| Risque | Impact |
|---|---|
| Drift silencieux entre état local et exchange | Décisions sur fausse base, pertes |
| Crash récupéré sans reconciliation | Re-trade d'ordres déjà soumis |
| Position fantôme (ouverte côté exchange, fermée côté local) | Risque non géré |

### Localisation cible

Modification de `src/protocols/{shadow,micro_live,live_light}_runtime.py` pour ajouter :
1. Hook au démarrage qui invoque `reconciliation_layer/recovery_trigger.py`
2. Scheduler périodique (asyncio.create_task ou apscheduler) pour reconciliation toutes les N minutes

Ou nouveau module :
```
src/protocols/reconciliation_scheduler.py
```

### Spécifications

```python
class ReconciliationScheduler:
    def __init__(
        self,
        recovery_trigger: RecoveryTrigger,
        circuit_breaker: EmergencyCircuitBreaker,
        period_seconds: int = 300,  # 5 min
    ) -> None:
        ...

    async def boot_reconcile(self) -> ReconciliationResult:
        """Au démarrage. Bloquant. Refuse de continuer si divergence non résolue."""
        result = await self.recovery_trigger.full_recovery()
        if result.has_unresolved_divergences():
            self.circuit_breaker.trip(
                reason=KillSwitchReason.CRITICAL_DIVERGENCE,
                detail=f"boot reconciliation failed: {result.divergences}",
            )
        return result

    async def periodic_reconcile_loop(self) -> None:
        """Tourne en arrière-plan. Trip kill switch sur divergence critique."""
        while True:
            await asyncio.sleep(self.period_seconds)
            result = await self.recovery_trigger.full_recovery()
            if result.has_critical_divergences():
                self.circuit_breaker.trip(...)
```

### Coût

| Sous-tâche | LOC | Sessions |
|---|---|---|
| `reconciliation_scheduler.py` + tests | 200-300 | 0.25 |

### Critères d'acceptation

- [ ] Boot reconciliation obligatoire avant tout trade
- [ ] Période configurable (default 300 s)
- [ ] Trip kill switch sur divergence critique non résolue
- [ ] Tests : simulation de divergence → trip vérifié
- [ ] Logs structurés avec types de divergence

---

## P1-3 — Daily P&L circuit breaker câblé

### Pourquoi P1

`risk_backbone/loss_budgeter/drawdown_guard.py` existe mais à **vérifier** s'il déclenche automatiquement le `circuit_breaker.py`. Si c'est juste un module de reporting, il faut le câbler pour qu'il **trip le kill switch** automatiquement à des seuils prédéfinis.

### Seuils recommandés à 10 k$

| Seuil | Action |
|---|---|
| DD intraday > -2 % (200 USD) | Warning, alerte Telegram |
| DD intraday > -3 % (300 USD) | Halt nouveaux trades, attente fermeture positions |
| DD intraday > -5 % (500 USD) | Trip kill switch, fermeture forcée si possible |
| DD 7j > -10 % (1000 USD) | Trip kill switch, review humaine obligatoire avant restart |
| DD 30j > -15 % (1500 USD) | Trip kill switch + review du système entier |

Ces seuils sont **conservateurs**. À 10 k$ tu n'as pas le luxe de risque-tolérance "VC-style".

### Risque si pas fait

| Risque | Impact |
|---|---|
| Drawdown non borné | Perte > seuil tolérable, panique humaine |
| Pas de halt automatique | Le système continue de creuser |
| Recovery sans review | Restart immédiat sur même bug |

### Localisation cible

Modification ou ajout dans :
```
src/risk_backbone/loss_budgeter/
└── pnl_circuit_breaker_wiring.py    [nouveau ou ajout dans drawdown_guard]
```

### Spécifications

```python
class PnLCircuitBreakerWiring:
    """
    Surveille le P&L courant et trip le circuit breaker à seuils.

    Appelé après chaque fill (event-driven) et périodiquement (sécurité).
    """

    INTRADAY_WARNING = -0.02     # -2 %
    INTRADAY_HALT = -0.03        # -3 %
    INTRADAY_KILL = -0.05        # -5 %
    WEEK_KILL = -0.10            # -10 %
    MONTH_KILL = -0.15           # -15 %

    def __init__(
        self,
        circuit_breaker: EmergencyCircuitBreaker,
        alert_manager: AlertManager,
        pnl_provider: PnLProvider,
    ) -> None: ...

    def check(self) -> PnLCheckResult:
        intraday = self.pnl_provider.get_intraday_pnl_pct()
        week = self.pnl_provider.get_rolling_pnl_pct(days=7)
        month = self.pnl_provider.get_rolling_pnl_pct(days=30)

        if intraday < self.INTRADAY_KILL:
            self.circuit_breaker.trip(
                reason=KillSwitchReason.LOSS_BUDGET_BREACH,
                detail=f"intraday DD {intraday:.2%} < {self.INTRADAY_KILL:.2%}",
            )
            return PnLCheckResult(action="KILL", level="intraday")

        if week < self.WEEK_KILL:
            self.circuit_breaker.trip(...)
            return PnLCheckResult(action="KILL", level="week")

        if month < self.MONTH_KILL:
            self.circuit_breaker.trip(...)
            return PnLCheckResult(action="KILL", level="month")

        if intraday < self.INTRADAY_HALT:
            # halt nouveau trades sans tripper full kill
            return PnLCheckResult(action="HALT_NEW_TRADES", level="intraday")

        if intraday < self.INTRADAY_WARNING:
            self.alert_manager.send(
                level="WARNING",
                message=f"Intraday DD at {intraday:.2%}",
            )
            return PnLCheckResult(action="WARN", level="intraday")

        return PnLCheckResult(action="OK")
```

### Coût

| Sous-tâche | LOC | Sessions |
|---|---|---|
| Wiring + tests | 100-200 | 0.25 |

### Critères d'acceptation

- [ ] Trip kill switch effectif aux seuils définis
- [ ] HALT bloque nouveaux trades sans fermer les existants
- [ ] Alertes Telegram envoyées aux warnings
- [ ] Tests : simulation de chaque seuil, action vérifiée
- [ ] Reset manuel obligatoire après trip

---

## P1-4 — Alerting externe (Telegram/email)

### Pourquoi P1

`alert_manager.py` existe dans `monitoring/` mais à **vérifier** où il sort. Sans push externe, tu **ne sais pas** quand le système trip. Tu pourrais découvrir 12h plus tard que le kill switch a été activé pendant une réunion.

### Risque si pas fait

| Risque | Impact |
|---|---|
| Trip kill switch non détecté | Système halt, opportunité ratée OU bug non investigué |
| Crash VPS non détecté | Système down silencieusement |
| Drawdown progressif sans alerte | Pas de signal humain pour décision |

### Solution recommandée

**Telegram bot personnel** — gratuit, simple, push instantané sur smartphone.

Alternative : webhook Discord, ou ntfy.sh pour minimalisme.

**À éviter** : email (latence, spam folder), SMS (coût, complexité).

### Localisation cible

```
src/monitoring/alerters/
├── __init__.py
├── telegram_alerter.py
├── alerter_contracts.py
└── tests/
    └── test_telegram_alerter.py
```

Wire dans `alert_manager.py` existant.

### Spécifications

```python
class TelegramAlerter:
    """
    Push alerts to a personal Telegram bot.

    Pas de réponse, pas d'interaction. Send-only.
    Token et chat_id chargés via credential_loader (sealed secrets).
    """

    def __init__(self, bot_token: str, chat_id: str) -> None: ...

    def send(self, level: AlertLevel, message: str, context: dict = None) -> bool:
        """
        AlertLevel: INFO, WARNING, ERROR, CRITICAL.
        CRITICAL également envoie un sound notification.
        """
        formatted = self._format(level, message, context)
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": formatted,
                    "parse_mode": "Markdown",
                    "disable_notification": level not in (AlertLevel.ERROR, AlertLevel.CRITICAL),
                },
                timeout=5,
            )
            return response.status_code == 200
        except Exception as e:
            # FALLBACK: log local mais ne pas crasher
            logger.error(f"Telegram alert failed: {e}")
            return False
```

### Événements à alerter

| Event | Niveau |
|---|---|
| Boot OK | INFO |
| Boot KO (reconciliation failed, etc.) | CRITICAL |
| Kill switch trip | CRITICAL |
| Trade executed | INFO (configurable, peut être désactivé) |
| Trade rejected (sharia, fee gate, etc.) | INFO |
| Drawdown warning | WARNING |
| Drawdown halt | ERROR |
| Drawdown kill | CRITICAL |
| Reconciliation divergence détectée | ERROR |
| Reconciliation divergence non résolue | CRITICAL |
| Disk > 80 % | WARNING |
| Disk > 95 % | CRITICAL |
| Connectivity lost (WS/REST) > 5 min | ERROR |

### Coût

| Sous-tâche | LOC | Sessions |
|---|---|---|
| `telegram_alerter.py` + tests | 150-200 | 0.15 |
| Wiring dans `alert_manager.py` + 13 events | 50-100 | 0.10 |
| **Total** | **200-300** | **0.25** |

### Critères d'acceptation

- [ ] Bot Telegram configuré, message de boot reçu
- [ ] Tous les événements de la liste émettent une alerte
- [ ] Si Telegram down → log local + retry sur les events critiques
- [ ] Token + chat_id stockés via `credential_loader` (jamais en clair)
- [ ] Tests : mock du endpoint Telegram, vérification format Markdown

---

## P1-5 — Disk monitor + log rotation

### Pourquoi P1

V5.3 est file-based : artifacts + logs s'accumulent. Sur un VPS avec disque limité (typique 25-50 GB), **le disque va se remplir**. Sans monitoring + rotation, le système crashera silencieusement quand il n'y aura plus d'espace pour écrire un artifact.

### Risque si pas fait

| Risque | Impact |
|---|---|
| Disque plein → écriture artifact échoue | Crash, halte trading silencieuse |
| Logs non rotatés → fichier de plusieurs GB | Lecture impossible, espace gaspillé |
| Pas d'alerte préventive | Pas de fenêtre pour intervenir |

### Localisation cible

```
src/monitoring/
├── disk_monitor.py            [nouveau]
└── log_rotation_config.py     [nouveau ou config externe]

ops/
└── logrotate.conf             [config système si logs externes]
```

### Spécifications

#### `disk_monitor.py`

```python
class DiskMonitor:
    """
    Surveille l'usage disque et alerte / trip à seuils.
    """

    def __init__(
        self,
        paths_to_monitor: list[Path],
        alert_manager: AlertManager,
        circuit_breaker: EmergencyCircuitBreaker,
        warning_pct: float = 0.80,
        critical_pct: float = 0.95,
        check_interval_seconds: int = 300,
    ) -> None: ...

    def check_now(self) -> DiskUsageReport:
        for path in self.paths_to_monitor:
            usage = shutil.disk_usage(path)
            pct = usage.used / usage.total
            if pct > self.critical_pct:
                self.circuit_breaker.trip(
                    reason=KillSwitchReason.DATA_CORRUPTION,
                    detail=f"Disk {path} at {pct:.1%}",
                )
                self.alert_manager.send(AlertLevel.CRITICAL, ...)
            elif pct > self.warning_pct:
                self.alert_manager.send(AlertLevel.WARNING, ...)
        ...
```

#### Log rotation

Deux options :

**Option A — Python `RotatingFileHandler`** (intégré)
- Configuration dans le logger global
- Rotation par taille (ex: 100 MB par fichier, 10 fichiers max)
- Compression gzip des anciens fichiers

**Option B — `logrotate` système** (Linux)
- Config dans `/etc/logrotate.d/v53_trading.conf`
- Rotation quotidienne, retention 30 jours, compression
- Plus standard sur VPS Linux

**Recommandation** : Option A en interne, Option B en complément si logs vers fichier système.

#### Artifact TTL

Les artifacts produits par V5.3 vont s'accumuler. Ajouter un module de cleanup :
```python
class ArtifactRetentionManager:
    """
    Supprime les artifacts plus anciens que N jours.
    Conserve les artifacts marqués `keep_forever`.
    """

    def cleanup(self, retention_days: int = 90) -> CleanupReport:
        ...
```

### Coût

| Sous-tâche | LOC | Sessions |
|---|---|---|
| `disk_monitor.py` + tests | 100-150 | 0.15 |
| Log rotation config (Python ou system) | 50-100 | 0.05 |
| `ArtifactRetentionManager` + tests | — | 0.05 (couvert dans P2 si différé) |
| **Total** | **150-250** | **0.25** |

### Critères d'acceptation

- [ ] Disk monitor tourne en background
- [ ] Warning à 80 %, critical + kill à 95 %
- [ ] Logs rotatés automatiquement
- [ ] Tests : simulation disk full → trip vérifié

---

## Synthèse P1

| Chantier | LOC | Sessions |
|---|---|---|
| P1-1 Regime lite | 400-600 | 0.5 |
| P1-2 Reconciliation périodique | 200-300 | 0.25 |
| P1-3 Daily P&L circuit breaker | 100-200 | 0.25 |
| P1-4 Telegram alerting | 200-300 | 0.25 |
| P1-5 Disk monitor + log rotation | 150-250 | 0.25 |
| **Total P1** | **1050-1650** | **1.5 sessions** |

---

## Ordre d'exécution recommandé

**Tous les P1 sont indépendants entre eux**, l'ordre est libre. Suggestion :

```
1. P1-2 (Reconciliation) — fondation safety
2. P1-3 (P&L circuit breaker) — câble drawdown_guard sur kill switch existant
3. P1-4 (Telegram alerting) — visibilité externe
4. P1-5 (Disk monitor) — sécurité long-running
5. P1-1 (Regime lite) — alpha enabler, le plus créatif et le plus volumineux
```

**Suite logique** : `05_V37_BRICKS_INCORPORATION.md` — les 3 briques V3.7 retenues.


---

## Source: docs/production_deployment_plan/05_V37_BRICKS_INCORPORATION.md

# Briques V3.7 à incorporer dans V5.3 — sélection raisonnée

> **Principe** : on ne migre pas vers V3.7. On pioche **3 idées** doctrinales que V5.3 n'a pas, et on les implémente en version **simplifiée** alignée sur la philosophie V5.3 (file-based, artifact-governed, single-process).
> **Ce qu'on ne fait PAS** : importer du code V3.7 (il n'existe pas), reproduire la stack Redis/Timescale, ou recoder OSCAE.

---

## Vue d'ensemble

| # | Brique V3.7 | Statut V5.3 | Version retenue | LOC | Sessions |
|---|---|---|---|---|---|
| V37-1 | Regime awareness | Tag string passif | Regime lite 3 états (couvert en P1-1) | 400-600 | 0.5 |
| V37-2 | Execution Gatekeeper central | Distribué, non centralisé | Wrapper `authorize()` non destructif | 400-700 | 0.75-1 |
| V37-3 | Information Stress Monitor (MAS light) | Absent | Détecteur veto temps réel | 300-500 | 0.5 |

**Total V3.7 incorporé** : ~1100-1800 LOC, **~1.75-2 sessions Opus**.

> **Note** : V37-1 (regime lite) est déjà détaillé dans `04_GAPS_P1.md` sous P1-1. Ne pas double-compter dans le total global. Ce fichier le mentionne pour traçabilité doctrinale.

---

## V37-1 — Regime awareness lite

### Statut

**Couvert dans P1-1** (`04_GAPS_P1.md`). Voir là pour les détails techniques.

### Pourquoi c'est inspiré V3.7 (et pas reproduit)

V3.7 propose un `RegimeDetector` à 7 états :
- R1 TrendUp
- R2 TrendDown
- R3 Ranging
- R4 Volatile
- R5 Capitulation
- R6 Rotation
- R∅ Unknown

Avec une matrice de paramètres par régime et une liste de stratégies autorisées/interdites par régime.

**Pourquoi pas tel quel** :
1. **Surdimensionné** pour 4 engines + 10 k$
2. La matrice param × régime = 4 × 7 × N params → explosion combinatoire à calibrer
3. Calibrer les seuils de transition entre 7 états demande beaucoup de données labelisées
4. À 10 k$, le bénéfice marginal entre 3 états et 7 états est négligeable

**Version retenue** : 3 états (CALM / STRESSED / EXTREME) avec hystérésis. Suffit pour le bénéfice principal : **désactiver des engines dans les régimes inadaptés**.

### Ce qui passe au scope futur

Si plus tard tu scales à 100 k$+, l'upgrade vers 5-7 régimes devient pertinent. Le contrat `RegimeState` doit être conçu pour permettre cet upgrade sans casser l'API consommatrice.

---

## V37-2 — Execution Gatekeeper central

### Pourquoi cette brique

V5.3 a tout ce qu'il faut pour autoriser un trade — mais l'autorisation est **distribuée** sur plusieurs modules :
- `risk_backbone/risk_runtime.py`
- `risk_backbone/loss_budgeter/`
- `risk_backbone/exposure_budgeter/`
- `risk_backbone/correlation_cluster_guard/`
- `risk_backbone/btc_factor_guard/`
- `risk_backbone/emergency_kill_switch/circuit_breaker.py`
- `execution_backbone/order_decider/execution_guard.py`
- `scoring_backbone/hard_block_gate/`

Plus, en P0/P1 :
- `sharia_compliance/sharia_runtime.py` (P0-2)
- `fee_aware_edge_gate.py` (P0-3)
- `regime_provider` gating (P1-1)
- `pnl_circuit_breaker_wiring` (P1-3)

**Conséquence** : quand un trade est rejeté, **pour comprendre pourquoi il faut chercher dans 10+ modules**. C'est dur à auditer en post-mortem et c'est fragile (un module ajouté plus tard peut être oublié dans la chaîne).

V3.7 propose un `ExecutionGatekeeper` central qui exécute 6 checks séquentiels et retourne un `ExecutionPermit` avec la liste des checks passés. **C'est la bonne idée, pas la bonne implémentation** (V3.7 est papier).

### Version retenue : wrapper `authorize()` non destructif

**Principe non négociable** : ne pas réécrire la logique existante. **Wrapper** seulement.

```
src/execution_backbone/gatekeeper/
├── __init__.py
├── contracts.py                    [ExecutionPermit, GateCheck, GateResult]
├── gate_chain.py                   [chaîne de checks composable]
├── gate_definitions.py             [enregistre les guards V5.3 existants comme checks]
├── central_authorizer.py           [API publique: authorize(intent) -> ExecutionPermit]
└── tests/
    ├── test_gate_chain.py
    ├── test_central_authorizer.py
    └── test_audit_trail.py
```

### Spécifications techniques

#### `contracts.py`

```python
class GateResult(StrEnum):
    PASS = "pass"
    REJECT = "reject"
    SKIP = "skip"   # check non applicable

class GateCheck(BaseModel, frozen=True):
    name: str                      # "sharia_trade_type", "loss_budget", etc.
    result: GateResult
    reason: str = ""               # vide si PASS, raison de rejet sinon
    detail: str = ""               # détail debug
    duration_ms: float = 0.0

class ExecutionPermit(BaseModel, frozen=True):
    intent_id: str
    timestamp: float
    authorized: bool
    checks: list[GateCheck]
    reject_reason: str = ""        # vide si autorisé
    rejected_at_check: str = ""    # nom du check qui a rejeté

    def first_failure(self) -> GateCheck | None:
        return next((c for c in self.checks if c.result == GateResult.REJECT), None)
```

#### `gate_chain.py`

```python
class GateChain:
    """
    Chaîne ordonnée de checks. Premier check qui rejette stoppe la chaîne.
    """

    def __init__(self, checks: list[Callable[[OrderIntent], GateCheck]]) -> None:
        self._checks = checks

    def evaluate(self, intent: OrderIntent) -> ExecutionPermit:
        results: list[GateCheck] = []
        for check_fn in self._checks:
            start = time.perf_counter()
            check = check_fn(intent)
            check = check.model_copy(update={"duration_ms": (time.perf_counter() - start) * 1000})
            results.append(check)
            if check.result == GateResult.REJECT:
                return ExecutionPermit(
                    intent_id=intent.intent_id,
                    timestamp=time.time(),
                    authorized=False,
                    checks=results,
                    reject_reason=check.reason,
                    rejected_at_check=check.name,
                )
        return ExecutionPermit(
            intent_id=intent.intent_id,
            timestamp=time.time(),
            authorized=True,
            checks=results,
        )
```

#### `gate_definitions.py`

C'est ici que les guards V5.3 existants sont **enregistrés comme checks**. Chaque guard reste en place, on ne l'arrache pas. Le gatekeeper l'**appelle**.

```python
def make_default_chain(
    sharia_runtime: ShariaRuntime,
    fee_gate: FeeAwareEdgeGate,
    risk_runtime: RiskRuntime,
    regime_provider: RegimeProvider,
    circuit_breaker: EmergencyCircuitBreaker,
    pnl_breaker: PnLCircuitBreakerWiring,
) -> GateChain:
    return GateChain([
        # Ordre important : du moins coûteux et plus bloquant au plus coûteux
        lambda i: _check_circuit_breaker(circuit_breaker, i),
        lambda i: _check_pnl_state(pnl_breaker, i),
        lambda i: _check_sharia(sharia_runtime, i),
        lambda i: _check_regime_gating(regime_provider, i),
        lambda i: _check_fee_edge(fee_gate, i),
        lambda i: _check_risk_runtime(risk_runtime, i),
    ])

def _check_sharia(runtime: ShariaRuntime, intent: OrderIntent) -> GateCheck:
    verdict = runtime.evaluate(intent)
    return GateCheck(
        name="sharia",
        result=GateResult.PASS if verdict.allowed else GateResult.REJECT,
        reason=verdict.reason,
        detail=verdict.detail,
    )

# ... idem pour les autres
```

#### `central_authorizer.py`

```python
class CentralAuthorizer:
    """
    API publique unique pour autoriser un trade.

    Remplace la chaîne distribuée actuelle dans execution_runtime.py
    par un point d'entrée unique auditable.
    """

    def __init__(self, gate_chain: GateChain, audit_logger: AuditLogger) -> None:
        self._chain = gate_chain
        self._audit = audit_logger

    def authorize(self, intent: OrderIntent) -> ExecutionPermit:
        permit = self._chain.evaluate(intent)
        self._audit.log(permit)
        return permit
```

#### Intégration avec `execution_runtime.py`

**Modification minimale** dans `execution_runtime.py` :

```python
# AVANT (distribué)
def execute_intent(intent: OrderIntent) -> ExecutionResult:
    if circuit_breaker.is_tripped():
        return ExecutionResult.rejected("circuit_breaker")
    if not risk_runtime.allow(intent):
        return ExecutionResult.rejected("risk")
    if not sharia.allow(intent):
        return ExecutionResult.rejected("sharia")
    # ... etc
    return execute(intent)

# APRÈS (centralisé)
def execute_intent(intent: OrderIntent) -> ExecutionResult:
    permit = central_authorizer.authorize(intent)
    if not permit.authorized:
        return ExecutionResult.rejected(permit.reject_reason)
    return execute(intent)
```

### Bénéfices

1. **Audit post-mortem trivial** : `permit.checks` contient l'historique complet de la décision
2. **Ajout d'un nouveau check** : 1 ligne dans `gate_definitions.py`, jamais besoin de toucher `execution_runtime.py`
3. **Tests** : on teste la chaîne en isolation, mockable
4. **Métriques** : `permit.checks[i].duration_ms` permet de profiler quel check est lent
5. **Alertes** : sur n trades rejetés consécutifs avec même `rejected_at_check`, alerte pattern (peut-être un bug ou une dérive)

### Risques de cette refacto

| Risque | Mitigation |
|---|---|
| Casser des chemins d'autorisation existants | Tests d'intégration sur tous les chemins existants AVANT et APRÈS |
| Performance dégradée (overhead de la chaîne) | Bench : chaque check < 1 ms, total < 10 ms — négligeable |
| Régression dans `execution_runtime.py` | Conserver les guards en place, juste les **appeler** depuis la chaîne |

### Coût

| Sous-tâche | LOC | Sessions |
|---|---|---|
| `contracts.py` + `gate_chain.py` | 150-200 | 0.15 |
| `gate_definitions.py` (registration des 6+ guards) | 150-250 | 0.20 |
| `central_authorizer.py` + `audit_logger` | 100-150 | 0.15 |
| Refacto `execution_runtime.py` | 50-100 | 0.15 |
| Tests intégration (chemins avant/après) | 200-300 | 0.25 |
| **Total** | **650-1000** | **~0.9** |

### Critères d'acceptation

- [ ] Tous les guards V5.3 existants sont enregistrés dans la chaîne
- [ ] Les guards P0/P1 (sharia, fee, regime, pnl breaker) sont enregistrés
- [ ] `execution_runtime.py` n'appelle plus directement les guards individuellement
- [ ] Tests d'intégration : 1026 tests existants ne régressent pas
- [ ] Tests unitaires : chaque check testé en isolation (mock du guard sous-jacent)
- [ ] Audit log immutable : chaque permit persisté avec timestamp et chain version
- [ ] Tableau de bord : nombre de rejets par check sur 24h disponible

---

## V37-3 — Information Stress Monitor (MAS light)

### Pourquoi cette brique

V3.7 propose le **MAS** (Microstructure Anomaly Sentinel) : un détecteur en temps réel d'**anomalies microstructure** qui peut véto une décision de trading même si tous les autres guards sont OK. Le but : détecter quand "le marché ment" — c'est-à-dire quand les prix qu'on observe ne reflètent pas une réalité tradable.

**Cas typiques détectés** :
- Spread anormal (5-10x la médiane) → liquidity black hole
- Volume burst sans nouvelles connues → manipulation possible
- Liquidité divisée (book vide d'un côté) → wash trading possible
- Latence exchange anormale → l'exchange est sous stress
- Désync entre book et trades → flux toxique

V5.3 a `data_backbone/freshness_checker/stale_hard_guard.py` qui couvre une partie (data freshness), mais pas la dimension **anomalie active** du marché.

### Version retenue

**Pas le MAS V3.7 complet** (qui inclut beaucoup de calculs ML). Une version simple et réactive :

```
src/data_backbone/info_stress_monitor/
├── __init__.py
├── contracts.py                    [StressSnapshot, StressLevel]
├── stress_calculator.py            [calcul des indicateurs]
├── stress_veto_provider.py         [API: should_veto(pair) -> bool]
└── tests/
    ├── test_stress_calculator.py
    └── test_veto_logic.py
```

### Spécifications techniques

#### Indicateurs calculés (par pair)

| Indicateur | Source | Seuil veto |
|---|---|---|
| `spread_zscore_60min` | order book stream | > 5 σ |
| `volume_zscore_5min` | trade stream | > 6 σ |
| `book_imbalance_extreme` | order book L5 | < 0.05 ou > 0.95 |
| `latency_p95_ms` | REST/WS health | > 1000 ms |
| `book_trade_desync_ms` | book ts vs trade ts | > 5000 ms |

#### Logique veto

Chaque indicateur en alerte → 1 point. Total > 2 → veto temporaire (bloque nouveaux trades sur cette pair pendant N minutes).

```python
class StressLevel(StrEnum):
    NORMAL = "normal"           # 0 alerte
    ELEVATED = "elevated"       # 1 alerte
    HIGH = "high"               # 2 alertes — warning, pas de veto
    CRITICAL = "critical"       # 3+ alertes — veto temporaire

class StressVetoProvider:
    def __init__(self, calculator: StressCalculator, veto_duration_seconds: int = 600) -> None:
        ...

    def should_veto(self, pair: str) -> StressVetoResult:
        snapshot = self._calculator.snapshot(pair)
        level = self._classify(snapshot)
        if level == StressLevel.CRITICAL:
            self._mark_pair_vetoed(pair, until=time.time() + self._veto_duration)
            return StressVetoResult(veto=True, reason=snapshot.alerts, level=level)
        if self._is_pair_in_veto(pair):
            return StressVetoResult(veto=True, reason="cooldown", level=level)
        return StressVetoResult(veto=False, level=level)
```

#### Intégration

S'enregistre comme un check supplémentaire dans `gate_definitions.py` (V37-2) :

```python
def make_default_chain(...):
    return GateChain([
        ...
        lambda i: _check_info_stress(stress_veto_provider, i),
        ...
    ])
```

### Bénéfices

1. **Protection contre flash crashes** : pendant un flash crash, spread + book imbalance + latence explosent → veto automatique
2. **Protection contre wash trading** : volume burst + book imbalance détectés
3. **Protection contre exchange degradation** : latence + désync détectés → veto avant que l'exchange officialise un incident
4. **Aucun ML, aucun training** : seuils fixes basés sur statistiques rolling

### Coût

| Sous-tâche | LOC | Sessions |
|---|---|---|
| `contracts.py` + `stress_calculator.py` | 150-250 | 0.25 |
| `stress_veto_provider.py` | 100-150 | 0.15 |
| Tests + intégration gatekeeper | 50-100 | 0.10 |
| **Total** | **300-500** | **0.5** |

### Critères d'acceptation

- [ ] Calculateur produit un `StressSnapshot` par pair monitorée
- [ ] Veto déclenché à partir de 3 alertes simultanées
- [ ] Cooldown de 10 minutes après veto avant retry
- [ ] Tests : injection de données simulant flash crash → veto vérifié
- [ ] Métriques : nombre de vetos déclenchés / 24h dans le dashboard

---

## Briques V3.7 explicitement REJETÉES

Pour traçabilité, voici les briques V3.7 qu'on ne reprend **pas** et pourquoi.

| Brique V3.7 | Raison du rejet | Reconsidération possible si... |
|---|---|---|
| **OSCAE** (composite scoring 5-dim) | scoring_backbone V5.3 fait déjà ce travail. Réécrire = casser 1026 tests. ROI négatif. | Jamais. Le canon scoring V5.3 est différent et fonctionne. |
| **Strategy Registry + StrategyManifest** | Les 4 engines V5.3 sont les "stratégies de fait", hard-codées. Pas de besoin dynamique. | Si tu scales à 6+ stratégies, à reconsidérer. |
| **Shadow Trading Engine** (entité séparée) | `protocols/shadow_runtime.py` couvre déjà ce besoin sous une forme différente (protocole de promotion système, pas de stratégie). | Jamais — les deux sont orthogonaux. |
| **Pipeline R&D SHG → SQL → SOE** | Surdimensionné. `meta_learning/` couvre l'apprentissage hyperparamètres, suffisant à 10 k$. | Si tu scales et que tu veux un pipeline structuré pour générer/valider de nouvelles stratégies. |
| **StrategyRandomizer** | Anti-RL adverse, pertinent à 1 M$+. À 10 k$ tu n'es pas une cible. | Si tu scales à 100 k$+ et que tu détectes du toxic flow ciblé. |
| **ExploitationDetector** | Idem. | Idem. |
| **Stack Redis + TimescaleDB + Docker Compose** | Coût > 2 % du capital. File-based V5.3 plus appropriée pour single-node 10 k$. | Si tu passes à un cluster multi-node ou >100 k$. |
| **REST API FastAPI** | Aucun client externe. Inutile à 10 k$. | Si tu construis une UI web ou un mobile app. |
| **MAS complet** (avec ML) | Surdimensionné. La version "info stress monitor lite" suffit. | Si tu trades sur 50+ pairs et tu veux du detection ML. |
| **7 régimes (R1-R6 + R∅)** | Surdimensionné. 3 états (CALM/STRESSED/EXTREME) suffisent. | Si tu scales à 100 k$+ et tu veux un alpha matrix par régime. |

---

## Synthèse incorporation V3.7

| Brique | Prio | Sessions Opus |
|---|---|---|
| V37-1 Regime lite (= P1-1) | P1 | 0.5 |
| V37-2 Gatekeeper central | P2 | 0.9 |
| V37-3 Info stress monitor | P2 | 0.5 |
| **Total nouveau** (V37-2 + V37-3) | | **1.4 sessions** |
| **Total avec V37-1 déjà compté en P1** | | **1.4 sessions** (V37-1 est dans P1) |

> **Note importante** : V37-1 ne s'ajoute **pas** au total global parce qu'il est compté dans P1-1. V37-2 et V37-3 sont **nouveaux** et viennent s'ajouter au total global de sessions Opus.

---

## Ordre d'exécution recommandé

```
1. V37-2 (Gatekeeper central) — APRÈS que les P0 et P1 critiques sont en place
   parce qu'il enregistre les guards qui doivent exister
2. V37-3 (Info stress monitor) — peut être fait en parallèle de V37-2 si une autre session est dispo
```

Les briques V3.7 sont **non bloquantes pour MICRO_LIVE** mais **recommandées avant LIVE** pour la qualité d'audit (V37-2) et la robustesse marché (V37-3).

**Suite logique** : `06_BLIND_SPOTS_MULTIDISCIPLINARY.md` — les 12 angles morts.


---

## Source: docs/production_deployment_plan/06_BLIND_SPOTS_MULTIDISCIPLINARY.md

# Angles morts multidisciplinaires

> **Objectif** — Lister ce qu'un humain seul (toi) ne voit pas naturellement parce qu'il n'a pas simultanément les 5 chapeaux : trader senior, quant PhD, data scientist, dev fintech, conseil halal. Chaque angle mort = un piège qui te coûte de l'argent réel s'il n'est pas adressé avant la phase MICRO_LIVE.

> **Important** — Ce document n'est pas du FUD. Chaque angle est ranké par sévérité (P0 / P1 / P2) et accompagné d'une mitigation concrète chiffrée. Si la mitigation existe déjà dans V5.3, c'est noté.

---

## 1. Méthode

J'ai listé 12 angles morts répartis en 5 perspectives :
- **Trader senior** (4 angles, A1-A4) — réflexes terrain qu'on n'a pas si on n'a jamais perdu d'argent réel
- **Quant PhD** (4 angles, Q1-Q4) — pièges statistiques classiques que la littérature documente
- **Data scientist** (3 angles, D1-D3) — biais de pipeline ML appliqué au trading
- **Dev fintech** (5 angles, F1-F5) — réalités exchange/API/ops oubliées par les devs généralistes
- **Conseil halal** (4 angles, H1-H4) — zones grises charia que `grep halal` ne trouve pas

Chaque angle suit la même structure : **Le piège** → **Pourquoi tu ne le vois pas** → **Conséquence chiffrée** → **Mitigation concrète** → **Statut V5.3**.

---

## 2. Trader senior (A1-A4)

### A1 — La barrière des frais ne se franchit pas par optimisme

**Le piège** — Tu construis une stratégie qui a un edge théorique de 0.15 % par trade. Tu ouvres-fermes une position : 0.10 % maker × 2 = 0.20 % de frais round-trip (Binance Spot taker, sans VIP, sans BNB). Edge net = **−0.05 %**. Tu perds à chaque trade.

**Pourquoi tu ne le vois pas** — En backtest, on raisonne en bps "alpha brut" et on oublie que les fees sont *fixes* alors que l'edge est *probabiliste*. Tu vois 60 % de hit rate avec un edge moyen de 0.30 %, tu te dis "facile" — sauf que les 40 % de losers t'effacent l'avantage et les fees achèvent le compte.

**Conséquence chiffrée** — Sur 10 000 USD avec 5 trades/jour à 200 USD chaque, des fees de 0.20 % round-trip = 2 USD/trade × 5 = **10 USD/jour de drag**. Soit **3650 USD/an = 36.5 % du capital en frais purs**. Pour break-even, ton edge net doit être > 0.20 % par trade, ce qui en vrai veut dire ton edge brut doit être > 0.40 % (avec slippage).

**Mitigation concrète** :
1. **Edge multiplier ≥ 2** : ne pas trader si `expected_edge_bps < 2 × (fee_round_trip_bps + slippage_estimate_bps)`
2. **Maker first** : sur Binance, taker = 0.10 %, maker = 0.10 % aussi par défaut, mais avec **BNB discount** = 0.075 %. Décision à prendre : utiliser BNB pour discount ? (BNB ≠ USDT donc à intégrer dans halal screening)
3. **Trade frequency cap** : pas plus de 3-5 trades/jour totaux toute la flotte. Pas 30.
4. **Min position size** : pas de trade < 100 USD (à 0.20 % round-trip = 0.20 USD de fees, qui doivent être négligeables vs alpha attendu)

**Statut V5.3** — `execution_cost_meter/fee_meter.py` calcule les fees exactes mais **aucun gate `min_edge_after_fees`**. C'est le P0-3 (`03_GAPS_P0.md`).

---

### A2 — Drawdown psychologique > drawdown statistique

**Le piège** — Backtest dit max DD = 8 %. Tu te dis "OK je tolère 8 %". Le système touche 6 % de DD le 3ème jour de live. Tu paniques, tu kill, tu redémarres en mode dégradé, tu fais une bêtise. Le DD réel devient 15 % parce que tu as **toi-même cassé le système**.

**Pourquoi tu ne le vois pas** — En backtest, le DD est une stat passive : tu vois la courbe une fois, tu rationalises. En live, tu vis chaque tick, chaque perte est un événement émotionnel. Le cerveau humain n'est pas câblé pour observer un compte qui descend sans agir.

**Conséquence chiffrée** — Non quantifiable directement, mais **80 % des retail traders auto-sabotent leur edge** en intervenant manuellement après une perte. Tu es retail. Tu n'es pas immunisé.

**Mitigation concrète** :
1. **Pas de monitoring temps réel** : tu ne dois PAS regarder ton équity intraday. Une fois par jour à heure fixe (ex : 09:00 du matin avec ton café). Pas Telegram à chaque trade.
2. **Daily P&L circuit breaker** automatique (P1-3) : si DD intraday > −2 %, le système se met en SHADOW automatiquement et alerte. Tu ne peux pas le réactiver le jour même. Sauvegarde toi de toi-même.
3. **Cooldown post-perte** : après un trade losing, le système suspend les nouveaux trades pendant 30 min. Empêche le revenge trading même algorithmique (clusters de trades dans la même direction après un loser).
4. **Pré-engagement écrit** : tu écris dans un fichier `DECISION_PRE_LIVE.md` les conditions exactes auxquelles tu as le droit de toucher au système une fois en live. Tu te tiens à ces règles.

**Statut V5.3** — Kill switch existe, daily P&L breaker manquant (P1-3). Cooldown post-perte n'existe pas — à ajouter.

---

### A3 — Weekend et fériés US — l'illiquidité que tu n'as jamais ressentie

**Le piège** — Le marché crypto est 24/7. Tu te dis "ça ferme jamais, parfait". Faux. Le **vendredi soir UTC** vers 22:00, et le **dimanche après-midi UTC**, la liquidité s'effondre car les market makers institutionnels US (qui font 60 %+ du volume sur les paires majeures) sont absents. Spreads × 3-5, slippage × 2-4, flash crashes plus fréquents.

**Pourquoi tu ne le vois pas** — En backtest avec données 1m closes, tu vois des prix moyens. Tu ne vois pas la microstructure : profondeur de book, spread bid-ask, latence des updates. Le backtest ment par construction sur la liquidité weekend.

**Conséquence chiffrée** — Un trade exécuté samedi 14:00 UTC sur une mid-cap halal (genre AVAX, SOL) peut subir **10-30 bps de slippage en plus** vs un trade lundi 14:00 UTC. Sur 5 trades de 200 USD le weekend, slippage extra = 1.5-9 USD perdus pour rien.

**Mitigation concrète** :
1. **Halal weekend mode** : suspendre tous les nouveaux trades du **vendredi 22:00 UTC au dimanche 22:00 UTC**. Maintenir uniquement les exits (stops, take-profit). Pas de nouvelles entries.
2. **Black list horaires** : configurable dans `config/trading_hours.yml`, avec option par symbole.
3. **Spread guard** : refuser un trade si `(ask - bid) / mid > 30 bps` (configurable). Le spread élargit = signal de fuir.

**Statut V5.3** — Aucun mécanisme de trading hours. À ajouter en P1 (peut être greffé sur la regime lite : "weekend = STRESSED automatique").

---

### A4 — Position size minimum et "exchange minimums" tueurs

**Le piège** — Binance Spot a un `MIN_NOTIONAL` par symbole (typiquement 5-10 USDT) et un `LOT_SIZE` (step size sur la quantité). À 10 k$ avec 5 positions max, position = 2 k$. Tu veux take-profit 25 % → ordre de 500 USD, ça passe. Mais si tu fais des **partial fills** ou des **exits scalés** (3 niveaux à 33 %), tu te retrouves avec des ordres de 165 USD, et selon le pair tu peux te faire **rejeter par MIN_NOTIONAL** pour les altcoins.

**Pourquoi tu ne le vois pas** — Le code V5.3 (`venue_constraints_provider.py`) connaît théoriquement ces limites mais aucun test ne valide qu'un partial exit scaled est faisable sur tous les pairs cibles à 10 k$.

**Conséquence chiffrée** — Sur les altcoins moins liquides du whitelist halal (DOT, AVAX, ATOM), le `MIN_NOTIONAL` est ~10 USDT, donc OK. Mais le `LOT_SIZE` peut casser un exit : si tu veux vendre 3.7 unités d'un asset à `step_size=0.1`, tu vendras 3.7 (OK), mais si `step_size=1`, tu vendras 3, le reste reste bloqué. Sur 1 année, ça peut bloquer 50-100 USD en "dust" non-liquidable.

**Mitigation concrète** :
1. **Pre-trade simulation** : avant chaque trade, simuler les exits (TP1/TP2/SL) avec les constraints réels du venue. Refuser le trade si un exit est inviable.
2. **Dust auto-cleanup** : tâche hebdomadaire qui détecte les dust < 1 USD par asset et tente une conversion auto (Binance "Convert Small Balances to BNB" → puis BNB → USDT, mais BNB problème halal à clarifier).
3. **Tests d'intégration "min_notional"** : pour chaque symbole du whitelist, vérifier au boot que `position_size_min × price > min_notional × 1.5` (marge de sécurité).

**Statut V5.3** — `venue_constraints_provider.py` existe, l'utilisation effective dans le path d'exécution est à vérifier. Le pre-trade simulation des exits n'existe pas.

---

## 3. Quant PhD (Q1-Q4)

### Q1 — Sample size problem (le tueur silencieux des stratégies retail)

**Le piège** — Tu as 2 ans de données historiques, 5 trades/jour = ~3650 trades total. Sur une stratégie multi-engine avec routage, ces 3650 trades sont splittés en sous-populations : Engine A bull = 400, Engine A bear = 200, Engine B sideways = 600, etc. **Aucune sous-population n'a > 1000 trades**, donc **aucune n'a une significativité statistique acceptable**. Tu calibres sur du bruit.

**Pourquoi tu ne le vois pas** — On regarde la métrique globale (Sharpe global = 1.4, génial !) sans réaliser que le Sharpe global est une moyenne pondérée de 8 sous-stratégies dont 6 sont du bruit. Le Sharpe par sous-stratégie est ininterprétable.

**Conséquence chiffrée** — Variance de l'estimateur Sharpe sur 200 trades ≈ ±0.5 absolu. Donc un Sharpe estimé "1.2" sur 200 trades a un IC95% = [0.2, 2.2]. Tu ne sais pas si tu as une bonne stratégie ou une marche aléatoire.

**Mitigation concrète** :
1. **Pas plus de 2 stratégies actives en MICRO_LIVE** au début. Engine A (trend) et Engine B (mean-reversion) suffisent.
2. **Significativité minimale** : refuser de promouvoir une stratégie en LIVE si N_trades < 500 sur le sous-régime concerné. Un fast-fail explicite si pas atteint.
3. **Bootstrap des metrics** : recalculer Sharpe et max DD via bootstrap (5000 resamples) et reporter l'IC95%, pas la valeur ponctuelle.
4. **Walk-forward** : refuser de croire un backtest qui n'a pas survécu à un walk-forward sur 4-6 windows out-of-sample.

**Statut V5.3** — `meta_learning/` et `validation_runtime/` existent, à vérifier s'ils font du bootstrap ou du walk-forward réel ou juste du holdout single split. **Likely insuffisant** vu les standards retail.

---

### Q2 — Survivorship bias (les morts ne parlent pas)

**Le piège** — Ton univers de trading actuel = top 50 par market cap *aujourd'hui*. Tu backtest sur 2 ans avec ces 50 symboles. Mais en 2024-01, certains de ces symboles n'existaient pas, et certains qui existaient à l'époque ont **disparu** (FTT, LUNA, USTC, etc.). Tu testes uniquement les survivants → ton edge est artificiellement gonflé.

**Pourquoi tu ne le vois pas** — Sourcer les "morts" demande un dataset historique propre avec listings/delistings horodatés. Binance ne fournit pas ça facilement, CoinGecko non plus. Le retail builder utilise ce qu'il a, pas ce qu'il faut.

**Conséquence chiffrée** — Sur backtest crypto 2020-2024, le survivorship bias gonfle le Sharpe de **0.2-0.5** points en moyenne (papier Hougan & Lawant 2023). Ton vrai Sharpe est plus bas que ce que tu vois.

**Mitigation concrète** :
1. **Fixer l'univers à un instant T passé** : choisir le top 50 *au 2024-01-01*, pas *aujourd'hui*. Inclure les morts.
2. **Tracker les delistings** : quand un symbole de l'univers est delisted en backtest, le marquer comme "−100 % loss du jour" même si techniquement la position aurait été récupérée à 0 puis 0.001 puis hors-listing.
3. **Halal compliance dynamique** : un symbole peut devenir non-halal en cours de route (ex : un projet pivote vers funding / DeFi lending). Tracker cette évolution.
4. **Restriction de l'univers réel à du blue chip** : à 10 k$, trader uniquement BTC, ETH, et 5-10 large caps halal-compliant. Le survivorship bias devient marginal sur ces noms-là.

**Statut V5.3** — Univers de trading non audité dans cette session. À vérifier dans S5 ou en pré-phase 0. **Risque P1.**

---

### Q3 — Look-ahead bias via timestamp et lag de données

**Le piège** — Ton feature `volume_5min` calculée à 12:00 utilise les données de 11:55 à 12:00. Mais en réalité, à 12:00:00.000 tu n'as pas encore reçu la dernière barre 11:59 — il y a 200-2000 ms de lag réseau + parsing. Donc en backtest tu utilises de l'info que tu n'as pas en live. Edge backtest > edge live, parfois de manière dramatique sur des features hyper-court-terme.

**Pourquoi tu ne le vois pas** — Le code utilise des timestamps "barre fermée" sans modéliser la latence d'arrivée. C'est un biais systémique invisible si tu ne fais pas de comparaison shadow-vs-backtest sur les MÊMES features avec lag réel.

**Conséquence chiffrée** — Sur features de momentum 5m, le look-ahead par lag réseau gonfle le PnL backtest de **5-15 %** sur des stratégies HF. Sur swing-trade > 1h, l'effet est marginal (< 1 %).

**Mitigation concrète** :
1. **Feature lock contracts** : V5.3 a déjà ce système (`feature_lock_contracts`), à vérifier qu'il enregistre bien le `as_of_timestamp` ET le `arrival_timestamp` pour chaque feature.
2. **Shadow vs backtest delta monitoring** : durant la phase SHADOW, comparer chaque trade signal entre le simulé (sur données historiques) et le live (sur ticks réels). Tout delta > 1 bps moyen = symptôme de look-ahead.
3. **Buffer de sécurité explicite** : forcer toutes les features intra-day à avoir un `min_age_seconds = 1` avant utilisation. Coût : 1 seconde de retard. Bénéfice : plus de look-ahead par lag.

**Statut V5.3** — `feature_lock_contracts/` existe, à auditer pour `arrival_timestamp` tracking. **Probable gap.**

---

### Q4 — Regime dependency (tes engines n'ont jamais vu du vrai bear)

**Le piège** — Si tes données historiques sont 2023-2025, tu n'as jamais entraîné/validé les engines sur du **vrai bear capitulation** (mars 2020 COVID crash, mai 2021 Chine ban, novembre 2022 FTX collapse). Le système peut être bon en sideways/bull et **catastrophique** en capitulation. Tu ne le sauras qu'en perdant 30-50 % en 24h.

**Pourquoi tu ne le vois pas** — Le marché crypto a tendance à oublier vite. 2 ans de bull market efface la mémoire émotionnelle des bears précédents. Le builder amateur sur-fit naturellement au régime récent.

**Conséquence chiffrée** — En mars 2020, BTC a fait −50 % en 24h. Si ton système n'a pas de circuit breaker calibré pour ça, tu peux perdre ton stop loss (gap-down sous le SL), et te retrouver short le marché involontairement (pas en spot heureusement, mais avec une grosse moins-value latente).

**Mitigation concrète** :
1. **Stress test obligatoire** sur les 3 windows de capitulation historiques (mars 2020, mai 2021, novembre 2022). Si max DD > 25 % sur l'une des trois, **pas de promotion en LIVE**. Point.
2. **Regime aware avec circuit breaker à 3 états** (= V37-1 = P1-1) : EXTREME → toutes les positions exit, plus de nouvelles entries pendant 24h.
3. **BTC factor guard** déjà codé dans V5.3 (`risk_backbone/btc_factor_guard/`) : à câbler effectivement en blocking guard, pas juste en monitoring.

**Statut V5.3** — BTC factor guard codé mais pas validé qu'il blocque effectivement. Stress test capitulation historique non documenté. **À ajouter en P1.**

---

## 4. Data scientist (D1-D3)

### D1 — Feature drift silencieux

**Le piège** — Une feature `relative_volume_24h` calibrée sur 2023 (où le volume moyen BTC = 30 B/jour) devient inopérante en 2026 si le volume moyen passe à 60 B/jour. La feature renvoie des valeurs "anormalement basses" en permanence, et la stratégie ne trade plus jamais (ou trade tout le temps, selon le sens).

**Pourquoi tu ne le vois pas** — Une feature qui dérive ne casse rien visiblement : elle continue de produire un nombre. Tu ne vois la conséquence que via la baisse de fréquence de trading ou via un Sharpe live qui dévisse sans raison apparente.

**Conséquence chiffrée** — Sur des features de microstructure (depth ratio, taker imbalance), le drift annuel peut atteindre 30-50 % de la valeur moyenne. C'est énorme.

**Mitigation concrète** :
1. **Feature monitoring** : pour chaque feature critique, calculer la moyenne et l'écart-type sur fenêtre glissante 30j vs fenêtre de référence (calibration). Alerter si |mean_30d - mean_ref| > 2σ.
2. **Recalibration trimestrielle** : rebaseliner les features sur les 90 derniers jours, manuellement, après revue.
3. **Population stability index (PSI)** : standard finance/credit, à utiliser ici aussi. Si PSI > 0.2, drift significatif.

**Statut V5.3** — `meta_learning/` peut faire ça, à vérifier. Probablement absent.

---

### D2 — Outliers et règles `winsorize` cachées

**Le piège** — Un flash crash de −20 % sur une mid-cap en 1 minute génère un return outlier. En backtest, si tu n'as pas wisorisé, cet outlier domine ton calcul de Sharpe et de DD. En live, ce flash arrive parfois et **ton stop loss saute par gap** — tu prends tout le gap.

**Pourquoi tu ne le vois pas** — Backtest et live traitent les outliers différemment : backtest avec un `clip(-0.10, +0.10)` masque le risque réel, live ne masque rien.

**Conséquence chiffrée** — Sur une mid-cap, un gap-down de 5 % au-delà d'un SL est une perte de 5 % de la position en une fraction de seconde. Sur 5 positions de 2 k$, ça fait 100 USD de perte sur 1 trade, soit 1 % du capital sur 1 incident.

**Mitigation concrète** :
1. **Pas de wisorisation cachée** : si tu wisorises en backtest, tu wisorises *exactement pareil* en live (= tu rejettes les ticks avec gap > X comme "spurious"). Sinon backtest et live divergent.
2. **Stop loss "soft"** au lieu de hard : déclencher le SL via *check de la dernière bougie close*, pas via le tick instantané. Évite d'exécuter sur un wick spurious. Coût : un peu plus de slippage en cas de vrai mouvement.
3. **Position sizing conservateur** sur les mid-caps : facteur 0.5 vs blue chips.

**Statut V5.3** — Non audité. À vérifier dans `feature_lock_contracts/` et dans le code des engines.

---

### D3 — Look-ahead par CV mal partitionnée

**Le piège** — Si tu fais du k-fold standard sur une time series, tu mélanges passé et futur : ton modèle est entraîné sur 80 % de données qui incluent du futur par rapport aux 20 % de test. Look-ahead massif. Validation surévaluée de 20-50 %.

**Pourquoi tu ne le vois pas** — `sklearn.model_selection.KFold` ne te crie pas dessus. Tu lances, ça marche, tu fais confiance. Sauf que c'est faux pour de la time series.

**Conséquence chiffrée** — Sur les papers reproduits par Marcos López de Prado, ~70 % des stratégies retail "validées par CV standard" perdent leur edge en walk-forward purgé. **70 %.**

**Mitigation concrète** :
1. **Purged k-fold avec embargo** (López de Prado, *Advances in Financial Machine Learning*) : entre chaque fold train et test, supprimer une fenêtre `embargo_days = max(label_horizon, feature_lookback)`.
2. **Walk-forward** par défaut, pas de k-fold. Et walk-forward **expanding** (pas rolling) pour avoir un échantillon train qui grandit.
3. **Combinatorial Purged CV** pour les évaluations de modèles quand la quantité de données le permet (rare à 2 ans crypto).

**Statut V5.3** — `validation_runtime/` à auditer. Si k-fold standard, c'est rouge.

---

## 5. Dev fintech (F1-F5)

### F1 — Exchange adapter abstrait = bombe à retardement

**Le piège** — `execution_runtime/` est designed contre une interface abstraite. Aucun adapter Binance/Kraken/Coinbase concret n'existe. Tu vas écrire l'adapter en P0-1, et tu vas découvrir 50 cas particuliers Binance que tu ne soupçonnais pas : `MIN_NOTIONAL`, `PRICE_FILTER`, rate limiting par poids, error codes spécifiques (`-2010`, `-1013`, `-1021`), reconnect WebSocket avec snapshot REST, time sync (NTP), idempotency via clientOrderId 36 chars max, etc.

**Pourquoi tu ne le vois pas** — L'abstraction te rassure faussement. "L'interface est définie, donc l'implémentation suivra." En réalité, l'implémentation est où vivent 100 % des bugs de prod.

**Conséquence chiffrée** — Un bug de mauvais arrondi `LOT_SIZE` peut faire échouer 10 % de tes orders → tu rates des entries → ton edge baisse de 10-30 % vs backtest.

**Mitigation concrète** :
1. **2 sessions Opus** consacrées à l'adapter Binance (P0-1) avec **tests intégration sur testnet** Binance avant promotion.
2. **Conformance test suite** : 30+ scénarios qui exercent les error codes Binance documentés (rate limit, insufficient balance, lot size, etc.).
3. **Sandbox first** : déployer l'adapter sur Binance Testnet pendant 1 semaine avant de toucher au mainnet.

**Statut V5.3** — Non commencé. C'est le P0-1, le plus gros chantier.

---

### F2 — WebSocket gap recovery

**Le piège** — Ton WS Binance déconnecte (ça arrive 2-10 fois par jour selon la qualité réseau VPS). Tu reconnectes. **Mais tu as raté X messages pendant la déconnexion.** Si tu ne fais pas de **REST replay** pour combler le gap, tu as un trou dans ta vue marché et tu peux trader sur de la donnée stale.

**Pourquoi tu ne le vois pas** — Le code "ça marche" la plupart du temps, donc tu présumes que la reconnect WS suffit. Faux. Il faut un protocole : "à la reconnexion, snapshot REST + replay des deltas manqués via depth update."

**Conséquence chiffrée** — Trades sur orderbook stale = entries à des prix qui n'existent plus → slippage massif (50-200 bps), risk de fill partial à des prix défavorables.

**Mitigation concrète** :
1. **Reconnect protocol Binance officiel** : voir docs Binance "How to manage a local order book". Snapshot REST `/depth?limit=1000`, puis WS `depth@100ms`, puis appliquer les updates dont `U <= snapshot.lastUpdateId + 1 <= u`.
2. **Gap detector** : si gap > 5 secondes, refuser tout nouveau trade jusqu'à resynchronisation.
3. **Heartbeat monitoring** : si WS silent > 30s, force reconnect.

**Statut V5.3** — `data_backbone/freshness_checker/` existe (côté freshness), mais le WS adapter n'existe pas (P0-1).

---

### F3 — Idempotency : commande envoyée 2 fois

**Le piège** — Tu envoies un order, tu n'as pas la réponse (timeout réseau), tu retry. **L'order a été reçu et exécuté 2 fois.** Tu as 2× la position attendue. Si tu n'as pas un `clientOrderId` unique par tentative logique (pas par tentative réseau), c'est garanti d'arriver.

**Pourquoi tu ne le vois pas** — Les bibliothèques HTTP genre `requests` retry automatiquement parfois. Tu ne contrôles pas l'idempotency.

**Conséquence chiffrée** — Position double = exposition double = risque double. Si ça arrive sur un trade losing, tu prends 2× la perte. Sur 10 k$, c'est −2 % au lieu de −1 %.

**Mitigation concrète** :
1. **`clientOrderId` déterministe par "intention de trade"** : `f"{strategy_id}_{symbol}_{intent_id}"` où `intent_id` est généré une seule fois par décision logique.
2. **Pas de retry HTTP automatique** : retry explicite contrôlé par le code applicatif après vérif que l'order n'a pas été placé (via REST `/openOrders` query).
3. **Reconciliation post-trade** : `execution_backbone/reconciliation_layer/` doit fire après chaque order envoyé pour vérifier que le state local match l'exchange.

**Statut V5.3** — `reconciliation_layer/` existe ✓. `clientOrderId` strategy à définir dans P0-1.

---

### F4 — State recovery au reboot

**Le piège** — VPS reboot (panne, mise à jour kernel, oom kill). Ton process redémarre. **Tu as oublié quelles positions tu avais.** Tu commences "à zéro", tu prends des décisions sur la base d'un état faux. Tu peux double-buyer une position que tu avais déjà, ou pire, ne jamais sortir d'une position que tu pensais avoir liquidée.

**Pourquoi tu ne le vois pas** — Tu testes en local avec des sessions courtes. Le reboot inattendu n'arrive pas en dev.

**Conséquence chiffrée** — Catastrophique. Une position oubliée qui dévisse pendant 24h sans surveillance = drawdown qui peut excéder le DD max théorique.

**Mitigation concrète** :
1. **`smoke_bootstrap_recovery/` est codé en V5.3** ✓ — vérifier qu'il fait bien :
   - snapshot des positions exchange via REST `/account` au boot
   - reconciliation avec le state local persisté
   - refus de trader si divergence détectée (stuck en `RECOVERY_REQUIRED`)
2. **Force reconciliation au boot** : avant tout trade, query exchange et reconcilier (= P1-2).
3. **Persisted state** : positions, orders open, kill switch state, dernière équity = tout sur disque dans des fichiers atomiques.

**Statut V5.3** — `smoke_bootstrap_recovery/` existe, à vérifier le déclenchement effectif et le couverture du `RECOVERY_REQUIRED` state. **À auditer en S5.**

---

### F5 — Logs confidentiels et leak de credentials

**Le piège** — En debug, tu ajoutes un `logger.info(f"Order params: {order}")` qui sérialize l'order entier. **L'order contient parfois la clé API en header HTTP** (selon comment tu wrap). Ou pire, tu logs une réponse exchange qui contient ton balance complet. Si quelqu'un (ou un outil tiers genre Sentry, Datadog) accède à tes logs, il a tes positions et potentiellement tes clés.

**Pourquoi tu ne le vois pas** — Les loggers sont permissifs par défaut. Le pattern "log everything for debug" est culturel.

**Conséquence chiffrée** — Si tes API keys leak, vol potentiel de 100 % du capital sur l'exchange (même avec withdraw lock, un attaquant peut exécuter des trades pump-and-dump pour drainer via slippage).

**Mitigation concrète** :
1. **Allowlist de logs** : seuls les champs explicitement marqués `safe_to_log = True` dans les pydantic models sont sérialisés.
2. **Sanitization layer** dans le logger : regex sur `api_key`, `secret`, `signature`, `Authorization` → remplacer par `[REDACTED]`.
3. **Logs locaux only** : pas de Sentry, pas de Datadog, pas de cloud logging dans la phase 0-2. Plus tard si nécessaire avec sanitization stricte.
4. **Audit log rotation** : logs archivés gzippés, jamais transmis en clair sur le réseau.

**Statut V5.3** — Non audité. **À ajouter dans P0-1 (sealed secrets) et P1-5 (log rotation).**

---

## 6. Conseil halal (H1-H4)

### H1 — Stablecoins : le débat USDT vs USDC vs DAI

**Le piège** — Tu vas trader contre du stable. Mais quel stable ? **USDT (Tether)** est backed par un mix d'actifs dont **du papier commercial productif d'intérêts** = riba. **USDC** est backed à ~80 % par des **T-Bills US productives d'intérêts** = riba indirect. **DAI** est over-collateralisé avec des positions qui paient un *stability fee* = riba structurel. **PYUSD** est plus récent, similaire à USDC. **Aucun stablecoin majeur n'est 100 % halal selon les juristes les plus stricts.**

**Pourquoi tu ne le vois pas** — On suppose que "le stable est neutre" parce qu'il vaut 1 $. Mais la mécanique sous-jacente est interest-bearing.

**Conséquence chiffrée** — Si tu décides ex-post que USDT est haram, tu dois t'en débarrasser → tu liquides → spread + fees + opportunité ratée. Mieux vaut décider ex-ante.

**Mitigation concrète** :
1. **Décision documentée** dans `DECISIONS_REQUIRED.md` : choisir USDT, USDC, ou autre, avec **justification écrite + référence à une fatwa explicite** (par ex. AAOIFI, Mufti Taqi Usmani, ou Sheikh Joe Bradford pour le contexte crypto US).
2. **Purification policy** : si tu choisis un stablecoin marginalement non-conforme, tu calcules la part d'intérêt indirect attribuable à ton balance et tu la donnes en charity. Mécanisme : `purification_calculator.py` (P0-2).
3. **Minimiser le temps en stable** : ne pas rester > 90 % en stable plus de 24h (ce qui de toute façon n'est pas désirable pour une stratégie active).

**Statut V5.3** — Aucune mention de stablecoin policy. **Décision à prendre AVANT P0-2.**

---

### H2 — Airdrops, forks, dust : revenu non-sollicité

**Le piège** — Tu as 1 ETH. Un projet airdrop te donne 100 tokens X. Tu n'as rien fait pour les obtenir : c'est-à-dire **tu reçois un revenu sans contrepartie commerciale**. Selon plusieurs juristes, un airdrop peut être assimilé à un don si tu ne savais pas qu'il viendrait, ou à une promotion publicitaire (similaire à un cashback). **Statut halal = ambigu.**

**Pourquoi tu ne le vois pas** — Tu ne planifies pas les airdrops. Ils tombent dans ton wallet par surprise. Tu les vois 6 mois après, tu vends pour 50 USD, tu te dis "bonus". Tu ne réalises pas que tu as peut-être pollué ton P&L halal.

**Conséquence chiffrée** — Marginal financièrement (50-200 USD/an typique), mais pollue la pureté du capital.

**Mitigation concrète** :
1. **Airdrop policy explicite** : par défaut, tout token reçu en airdrop est marqué comme "purification candidate" et liquidé en USDT à la prochaine occasion, avec le proceeds donné en charity (purification).
2. **Forks de chains** : pareil. Si BTC fork en BCH, le BCH reçu = purification candidate.
3. **Dust < 1 USD** : ignoré par le système trading (pas tradable de toute façon), audit annuel pour purification.

**Statut V5.3** — Aucune logique. À ajouter dans `sharia_compliance/` (P0-2).

---

### H3 — Funding rates et lending accidentels (le piège Binance)

**Le piège** — Binance propose **automatiquement** des features comme :
- **Binance Earn / Simple Earn** : tes USDT inactives génèrent du yield
- **Binance Margin** : tu peux activer "auto-borrow" sans le savoir
- **Binance Futures** : avec funding rate (riba pure)
- **BNB Vault** : staking auto avec rewards

Si tu actives n'importe laquelle de ces features par mégarde (genre tu cliques sur "Enable Earn" en pensant que c'est un toggle anodin), **tu génères du riba sans t'en rendre compte.**

**Pourquoi tu ne le vois pas** — L'UI Binance est designed pour pousser ces produits. Tu peux activer Simple Earn en 1 clic. Tu peux ne pas savoir que c'est activé.

**Conséquence chiffrée** — Si Earn est activé sur 10 k$ USDT @ 2 % APY = 200 USD/an de revenus interest-bearing → **100 % de ton P&L peut devenir contaminé** si tu n'as pas la rigueur de séparer les sources de revenus.

**Mitigation concrète** :
1. **API key permissions strictes** : créer une API key qui n'a QUE `SPOT TRADING` et `READ`. Pas de `MARGIN`, pas de `FUTURES`, pas de `EARN`, pas de `WITHDRAW`.
2. **Audit hebdomadaire des features actives** : script qui query Binance et alerte si Earn / Margin / Futures sont activés sur le compte.
3. **Read-only du balance avec breakdown** : vérifier que `balance.staking == 0`, `balance.earn == 0`, `balance.margin == 0`. Toute déviation = alerte critique.
4. **Documentation visuelle** : screenshot du compte Binance dans l'état "tout désactivé" comme référence.

**Statut V5.3** — Aucune logique. **Critique. À ajouter dans P0-2.**

---

### H4 — Audit fatwa et accountability

**Le piège** — Tu construis un système "halal" selon ton interprétation personnelle. 5 ans plus tard, un juriste te dit "non, ton X était haram". Ton P&L cumulé est contaminé rétroactivement. Pas de mécanisme d'audit, pas de trace, pas de purification calculée.

**Pourquoi tu ne le vois pas** — La conformité halal est traitée comme un état binaire ("c'est halal ou pas") au lieu d'un processus continu qui inclut traçabilité et purification.

**Conséquence chiffrée** — Spirituelle d'abord (le but du halal). Pratique ensuite : la purification rétroactive sur 5 ans peut représenter des milliers de USD à donner.

**Mitigation concrète** :
1. **Audit log dédié** : `policy_audit_logger.py` (P0-2) loggue chaque décision halal prise par le système avec timestamp, pair, raison de l'autorisation/refus, version de la policy.
2. **Versioning des policies** : `sharia_policy_v1.yml`, `sharia_policy_v2.yml`, etc. Si tu changes d'avis, tu peux re-tracer ce qui a été tradé sous v1.
3. **Référence explicite à une fatwa** : pour chaque règle (whitelist/blacklist), un commentaire avec lien vers la source juridique. Pas de règle "parce que je l'ai décidé".
4. **Revue annuelle** : audit annuel par un tiers (ami juriste, ou consultation payante d'un mufti spécialisé crypto comme Joe Bradford ou Mufti Faraz Adam).

**Statut V5.3** — Inexistant. À construire from scratch en P0-2.

---

## 7. Tableau de synthèse — sévérité × statut V5.3

| # | Angle mort | Sévérité | Statut V5.3 actuel | Mitigation où |
|---|---|---|---|---|
| **A1** | Fees barrier | **P0** | ❌ pas de gate min-edge | P0-3 |
| **A2** | Drawdown psychologique | **P1** | ⚠ kill switch oui, daily breaker non | P1-3 |
| **A3** | Weekend illiquidity | **P1** | ❌ pas de trading hours | P1 (à intégrer regime lite) |
| **A4** | Min position size | **P1** | ⚠ venue_constraints existe, pas câblé | P1 |
| **Q1** | Sample size problem | **P0** | ⚠ validation_runtime existe, à auditer | Phase 0 |
| **Q2** | Survivorship bias | **P1** | ❓ univers non audité | Phase 0 |
| **Q3** | Look-ahead via timestamp | **P1** | ⚠ feature_lock_contracts à valider | Phase 0 / P1 |
| **Q4** | Regime dependency (capitulation) | **P0** | ⚠ btc_factor_guard codé non câblé | P1-1 + stress test |
| **D1** | Feature drift | **P1** | ❓ probable absent | P2 |
| **D2** | Outliers / wisorisation | **P2** | ❓ non audité | Phase 0 |
| **D3** | Look-ahead par CV | **P1** | ❓ validation à auditer | Phase 0 |
| **F1** | Exchange adapter abstrait | **P0** | ❌ inexistant | P0-1 |
| **F2** | WebSocket gap recovery | **P0** | ❌ inexistant | P0-1 |
| **F3** | Idempotency | **P0** | ⚠ reconciliation oui, clientOrderId à définir | P0-1 |
| **F4** | State recovery au reboot | **P1** | ✓ smoke_bootstrap_recovery existe, à valider | P1-2 |
| **F5** | Log leaks credentials | **P0** | ❓ non audité | P0-1 / P1-5 |
| **H1** | Stablecoin policy | **P0** | ❌ inexistant | Décision + P0-2 |
| **H2** | Airdrops / forks / dust | **P1** | ❌ inexistant | P0-2 |
| **H3** | Earn / Margin / Futures accidentels | **P0** | ❌ inexistant | P0-2 |
| **H4** | Audit fatwa | **P1** | ❌ inexistant | P0-2 |

**Comptage par sévérité** :
- P0 : **8 angles morts** (critique pour MICRO_LIVE)
- P1 : **10 angles morts** (à traiter avant LIVE)
- P2 : **2 angles morts** (à traiter en continu après LIVE)

---

## 8. Conclusion opérationnelle

Sur 20 angles morts identifiés :
- **5 sont déjà adressés** par des modules V5.3 codés (kill switch, BTC factor, reconciliation, smoke bootstrap, fee meter — ~25 %)
- **15 sont à compléter** (75 %), dont **8 critiques P0**.

**La bonne nouvelle** : tous les P0 sont adressés par les chantiers `03_GAPS_P0.md` (5 chantiers couvrent 7 des 8 P0). Le P0 manquant — **stress test capitulation historique (Q4)** — est ajouté à la phase 0 du `07_PHASE_PLAN_0_TO_4.md`.

**La moins bonne** : il y a 10 angles P1 qui ne sont **pas couverts par le plan actuel des P1** (`04_GAPS_P1.md`). À intégrer dans le phase plan.

**Suite logique** : `07_PHASE_PLAN_0_TO_4.md` — comment séquencer les chantiers en phases avec critères d'entrée/sortie.


---

## Source: docs/production_deployment_plan/07_PHASE_PLAN_0_TO_4.md

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


---

## Source: docs/production_deployment_plan/08_RISK_REGISTER.md

# Risk Register — V5.3 production halal spot 10 k$

> **Objectif** — Lister les risques identifiés, leur probabilité, leur impact, leur mitigation existante (si déjà couverte par V5.3) ou à coder, et le **trigger** qui déclenche une réponse.
>
> **Méthode** — Risques regroupés en 6 catégories : Technique, Marché, Halal, Opérationnel, Sécurité, Juridique. Chaque risque a un identifiant `R<cat>-<num>` pour traçabilité.
>
> **Échelle** : probabilité {Faible / Moyen / Élevé} × impact {Faible / Moyen / Élevé / Catastrophique}. Un risque "Élevé × Catastrophique" est un **kill criterion** : si non mitigé, **pas de Phase 3**.

---

## 1. Catégorie TECHNIQUE (RT)

### RT-1 — Bug d'arrondi LOT_SIZE / MIN_NOTIONAL

| Champ | Valeur |
|---|---|
| **Probabilité** | Élevé |
| **Impact** | Moyen |
| **Description** | Un order soumis ne respecte pas les contraintes Binance (`stepSize`, `minNotional`) → rejet exchange → trade raté |
| **Conséquence chiffrée** | Trade raté = perte de l'edge attendu (~5-30 bps de PnL latent) |
| **Mitigation V5.3** | `venue_constraints_provider.py` existe, à câbler dans le pre-trade check |
| **Mitigation à coder** | P0-1 : pre-trade simulation contre les contraintes Binance live |
| **Trigger** | 1 trade rejeté pour cette raison → alerte Telegram + investigation |
| **Test** | Conformance test suite Binance (P0-1) |

### RT-2 — WebSocket gap silencieux

| Champ | Valeur |
|---|---|
| **Probabilité** | Élevé (2-10 fois/jour réseau VPS standard) |
| **Impact** | Moyen→Élevé (selon timing et durée) |
| **Description** | WS Binance déconnecte, code reconnecte sans gap recovery → état marché stale → trades sur orderbook obsolète |
| **Conséquence chiffrée** | Slippage 50-200 bps, fills à des prix défavorables |
| **Mitigation V5.3** | `data_backbone/freshness_checker/` ✓ pour la freshness, mais le reconnect protocol Binance n'existe pas |
| **Mitigation à coder** | P0-1 : reconnect protocol officiel Binance + gap detector + freshness gate |
| **Trigger** | Gap > 5 secondes → blocage automatique des nouveaux trades + alerte |
| **Test** | Simulation de coupure WS sur testnet pendant 30s → vérifier comportement |

### RT-3 — Process crash / VPS reboot

| Champ | Valeur |
|---|---|
| **Probabilité** | Moyen (1-3 fois/an typique) |
| **Impact** | Catastrophique si pas de recovery |
| **Description** | Crash Python (OOM, exception non catchée) ou reboot VPS (kernel update) → état local en RAM perdu → décisions sur état faux au restart |
| **Conséquence chiffrée** | Position oubliée qui dévisse 24h sans surveillance = perte 5-20 % du capital |
| **Mitigation V5.3** | `smoke_bootstrap_recovery/` ✓ + kill switch persistant ✓ + reconciliation_layer ✓ |
| **Mitigation à coder** | P1-2 : forcer reconciliation au boot ET périodique. Vérifier le déclenchement effectif. |
| **Trigger** | Toute restart sans reconciliation OK → kill switch ARMED → refus de trader |
| **Test** | Tuer le process en plein trade → restart → vérifier que la position est récupérée |

### RT-4 — Double-soumission d'ordre (idempotency)

| Champ | Valeur |
|---|---|
| **Probabilité** | Moyen |
| **Impact** | Élevé |
| **Description** | Timeout réseau sur l'envoi d'order → retry → l'order a été reçu et exécuté 2 fois |
| **Conséquence chiffrée** | Position double = exposition double = perte ou gain × 2 |
| **Mitigation V5.3** | `reconciliation_layer/` ✓ détecte la divergence ex-post |
| **Mitigation à coder** | P0-1 : `clientOrderId` déterministe par intent, pas de retry HTTP automatique, vérification ex-ante via REST `/openOrders` avant tout retry |
| **Trigger** | Reconciliation détecte position > expected → kill switch + alerte |
| **Test** | Mock latence réseau intentionnelle → vérifier qu'aucun double n'arrive |

### RT-5 — Time sync drift

| Champ | Valeur |
|---|---|
| **Probabilité** | Faible (NTP par défaut OK) |
| **Impact** | Élevé si non détecté |
| **Description** | Horloge VPS dérive de > 1 seconde par rapport à Binance → erreur `-1021 Timestamp for this request was 1000ms ahead of the server's time` |
| **Conséquence chiffrée** | 100 % des orders rejetés tant que pas resynchronisé |
| **Mitigation à coder** | P0-1 : `time_sync.py` qui sync sur Binance `/api/v3/time` au boot et toutes les heures |
| **Trigger** | Erreur `-1021` → resync immédiat + retry. Si > 3 erreurs en 5 min → kill switch |
| **Test** | Forcer drift de 5 sec sur clock locale → vérifier auto-resync |

### RT-6 — Rate limiting Binance

| Champ | Valeur |
|---|---|
| **Probabilité** | Faible (limites larges pour spot retail) |
| **Impact** | Moyen |
| **Description** | Trop de calls REST → ban temporaire 1-5 min |
| **Conséquence chiffrée** | Décisions et reconciliations bloquées pendant la durée du ban |
| **Mitigation à coder** | P0-1 : rate limiter local avec tracking du `X-MBX-USED-WEIGHT` header, throttle préemptif à 80 % du quota |
| **Trigger** | `X-MBX-USED-WEIGHT > 800/1200` → throttle. `429` reçu → backoff exponentiel |
| **Test** | Stress test 100 calls/sec → vérifier throttle |

---

## 2. Catégorie MARCHÉ (RM)

### RM-1 — Flash crash / capitulation soudaine

| Champ | Valeur |
|---|---|
| **Probabilité** | Moyen (1-2 fois/an sur 24 mois historiques) |
| **Impact** | Catastrophique |
| **Description** | Mouvement de marché −20 % en 1h, gap-down sous le SL, exécution à des prix loin du SL prévu |
| **Conséquence chiffrée** | Perte d'une position entière (−2 % du capital) |
| **Mitigation V5.3** | `risk_backbone/btc_factor_guard/` codé mais pas câblé en blocking |
| **Mitigation à coder** | P1-1 : regime lite → état EXTREME → exit toutes positions + plus d'entries 24h. P0-3 : edge multiplier × 2 + spread guard. P1-3 : daily P&L breaker. |
| **Trigger** | BTC −5 % en 1h → état EXTREME automatique. DD intraday > 2 % → SHADOW automatique. |
| **Test** | Replay des 3 windows de capitulation historiques (mars 2020, mai 2021, novembre 2022). Max DD doit rester < 25 %. |

### RM-2 — Stratégie qui drift sans qu'on le voie

| Champ | Valeur |
|---|---|
| **Probabilité** | Élevé (toutes les stratégies drift à terme) |
| **Impact** | Moyen→Élevé selon vitesse |
| **Description** | Sharpe live qui dévisse silencieusement vs backtest, sans event évident |
| **Conséquence chiffrée** | DD progressif jusqu'à −10/15 % avant qu'on s'en rende compte |
| **Mitigation à coder** | P2 : feature drift monitoring (PSI < 0.2). Recalibration trimestrielle obligatoire. |
| **Trigger** | Sharpe rolling 30j live < 50 % du Sharpe backtest → revue humaine forcée. |
| **Test** | A/B sur fenêtre rolling : backtest reproduit sur les mêmes 30j que le live, comparaison |

### RM-3 — Exchange delisting d'un asset whitelisté

| Champ | Valeur |
|---|---|
| **Probabilité** | Faible (1-2 par an sur les majors) |
| **Impact** | Moyen |
| **Description** | Binance annonce delisting de XYZ. Les positions doivent être liquidées avant la deadline. |
| **Conséquence chiffrée** | Slippage forcé 50-500 bps + taxe potentielle |
| **Mitigation à coder** | Polling périodique de la liste des delistings annoncés (`exchangeInfo` + RSS Binance announcements). Auto-blacklist des assets en cours de delisting. |
| **Trigger** | Asset whitelist marqué `delisting_pending` → bloquer entries, déclencher exit progressif |
| **Test** | Mock annonce delisting → vérifier comportement |

### RM-4 — Liquidité weekend / fériés

| Champ | Valeur |
|---|---|
| **Probabilité** | Élevé (chaque weekend) |
| **Impact** | Moyen |
| **Description** | Spreads × 3-5, slippage × 2-4, flash moves plus fréquents |
| **Conséquence chiffrée** | Slippage moyen +10-30 bps sur les trades weekend |
| **Mitigation à coder** | Trading hours blacklist : pas de nouvelles entries vendredi 22:00 UTC → dimanche 22:00 UTC. Exits seulement. |
| **Trigger** | Heure dans la blacklist → refus d'entry, log `BLACKLIST_HOURS` |
| **Test** | Backtest avec et sans la blacklist → comparer métriques |

---

## 3. Catégorie HALAL (RH)

### RH-1 — Activation accidentelle d'une feature interest-bearing Binance

| Champ | Valeur |
|---|---|
| **Probabilité** | Moyen (UI Binance pousse activement Earn) |
| **Impact** | Catastrophique (pollue 100 % du P&L) |
| **Description** | Earn / Margin / Futures activé par mégarde → revenus interest-bearing automatiques |
| **Conséquence chiffrée** | 100 % du P&L contaminé tant que pas désactivé |
| **Mitigation à coder** | P0-2 : audit hebdomadaire du compte Binance, vérifier `balance.staking == 0`, `balance.earn == 0`, `balance.margin == 0`. API key sans permissions Margin/Futures/Earn. |
| **Trigger** | Détection d'un balance.earn > 0 → kill switch + alerte CRITICAL |
| **Test** | Activer Simple Earn manuellement → vérifier que l'audit script alerte en < 24h |

### RH-2 — Whitelist asset perd sa conformité

| Champ | Valeur |
|---|---|
| **Probabilité** | Faible (mais pas nul, projets pivotent) |
| **Impact** | Moyen |
| **Description** | Un asset whitelisté lance une feature DeFi/lending/staking interest-bearing → devient questionnable |
| **Conséquence chiffrée** | Positions ouvertes sur cet asset deviennent à purifier |
| **Mitigation à coder** | P0-2 : revue trimestrielle de la whitelist + `policy_audit_logger.py` versioning |
| **Trigger** | Annonce projet ou alerte communautaire → revue manuelle |
| **Test** | Mock changement de status → vérifier qu'on peut updater la whitelist sans casser le système |

### RH-3 — Stablecoin conformité ambiguë

| Champ | Valeur |
|---|---|
| **Probabilité** | Élevé (tous les stables ont des questionnements) |
| **Impact** | Moyen |
| **Description** | USDT, USDC, etc. ont des composantes interest-bearing dans leurs reserves |
| **Conséquence chiffrée** | Part du P&L à purifier (calculable) |
| **Mitigation à coder** | P0-2 : `purification_calculator.py` + décision documentée Phase 0 |
| **Trigger** | Calcul mensuel automatique → output dans le rapport mensuel |
| **Test** | Calcul manuel sur 1 mois de balance → vérifier cohérence |

### RH-4 — Airdrops / forks non sollicités

| Champ | Valeur |
|---|---|
| **Probabilité** | Moyen (1-3 par an) |
| **Impact** | Faible (financièrement) mais Élevé (pureté capital) |
| **Description** | Tokens reçus sans contrepartie → statut halal ambigu |
| **Conséquence chiffrée** | 50-200 USD/an typique |
| **Mitigation à coder** | P0-2 : détection automatique des assets reçus non whitelist → marquer `purification_candidate` → liquider → donate |
| **Trigger** | Balance d'un asset non whitelist > 0 → alerte + workflow de purification |
| **Test** | Mock reception d'airdrop → vérifier détection |

---

## 4. Catégorie OPÉRATIONNEL (RO)

### RO-1 — Disque saturé sur VPS

| Champ | Valeur |
|---|---|
| **Probabilité** | Moyen sans rotation, Faible avec |
| **Impact** | Élevé (write artefacts/logs échoue → état corrompu) |
| **Description** | Logs et artefacts s'accumulent jusqu'à remplir 160 GB |
| **Conséquence chiffrée** | Pannes silencieuses, écritures partielles, kill switch peut ne pas s'activer |
| **Mitigation à coder** | P1-5 : disk monitor avec alerte à 70 %, log rotation gzip avec retention 90j, snapshots compressés |
| **Trigger** | Free disk < 30 % → alerte. < 10 % → kill switch CRITIQUE. |
| **Test** | Remplir le disque manuellement → vérifier alerte et comportement |

### RO-2 — Humain panique et intervient manuellement

| Champ | Valeur |
|---|---|
| **Probabilité** | Élevé (humains paniquent) |
| **Impact** | Élevé (auto-sabotage) |
| **Description** | Voir A2 dans `06_BLIND_SPOTS_MULTIDISCIPLINARY.md` |
| **Conséquence chiffrée** | 80 % des retail traders auto-sabotent leur edge |
| **Mitigation à coder** | P1-3 : daily P&L breaker (auto-pause). Cooldown post-perte. **Pré-engagement écrit** par l'humain dans un fichier signé. |
| **Trigger** | Pré-engagement violé → revue post-incident obligatoire |
| **Test** | Pas testable techniquement. Discipline humaine. |

### RO-3 — Agent codeur introduit une régression silencieuse

| Champ | Valeur |
|---|---|
| **Probabilité** | Moyen (toutes les modifs ont un risque) |
| **Impact** | Moyen→Élevé selon module |
| **Description** | Une tranche code casse un comportement existant qui n'était pas testé |
| **Conséquence chiffrée** | Variable, peut être catastrophique sur execution_backbone |
| **Mitigation à coder** | Tests restent verts (1026+nouveau) après chaque tranche. Audit grep sur les changements. Pas de promotion sans `replay_p0_v1` validé. |
| **Trigger** | Test rouge → rollback immédiat |
| **Test** | CI complète après chaque tranche |

### RO-4 — Calibration obsolète

| Champ | Valeur |
|---|---|
| **Probabilité** | Élevé (à terme) |
| **Impact** | Moyen→Élevé |
| **Description** | Les seuils calibrés en Phase 0 deviennent inadaptés au régime de marché actuel |
| **Conséquence chiffrée** | Stratégie sur/sous-trade, Sharpe live dévisse |
| **Mitigation à coder** | Recalibration trimestrielle obligatoire via Local IA Lab. Versioning des artefacts (v1, v2, v3...). |
| **Trigger** | Délai > 90 jours depuis dernière calibration → alerte |
| **Test** | Workflow de recalibration testé en Phase 0 |

---

## 5. Catégorie SÉCURITÉ (RS)

### RS-1 — API key Binance compromise

| Champ | Valeur |
|---|---|
| **Probabilité** | Faible avec hygiène, Moyen sans |
| **Impact** | Catastrophique (vol potentiel via pump-and-dump même sans withdraw) |
| **Description** | Clé fuit (logs, repo, machine compromise) → attaquant exécute des trades à perte pour drainer via slippage |
| **Conséquence chiffrée** | Jusqu'à 100 % du capital |
| **Mitigation à coder** | P0-4 : sealed secrets (`age` ou `sops`), pas de clé en clair sur disque. Permissions API restreintes (SPOT TRADING + READ uniquement, pas de WITHDRAW, pas de MARGIN, pas de FUTURES). IP whitelist VPS. Logs sanitization. |
| **Trigger** | Détection d'orders non émis par le système → kill switch immédiat |
| **Test** | Audit grep credentials dans logs et repo |

### RS-2 — VPS compromis (root access)

| Champ | Valeur |
|---|---|
| **Probabilité** | Faible avec hardening |
| **Impact** | Catastrophique |
| **Description** | Attaquant root sur VPS → accès aux secrets sealed (déchiffrables si la clé de session est en RAM) |
| **Conséquence chiffrée** | 100 % du capital |
| **Mitigation à coder** | OS hardening (firewall, fail2ban, SSH key only, pas de password, port custom). Updates automatiques security. Audit logs. |
| **Trigger** | Login SSH non whitelist → alerte CRITICAL |
| **Test** | Audit SSH config + scan ports externe |

### RS-3 — Logs leak credentials

| Champ | Valeur |
|---|---|
| **Probabilité** | Élevé sans sanitization |
| **Impact** | Élevé (équivalent à RS-1) |
| **Description** | `logger.info(f"Order: {order}")` sérialise headers HTTP avec API key |
| **Conséquence chiffrée** | Idem RS-1 |
| **Mitigation à coder** | P0-1 / P1-5 : logger sanitization layer (regex sur `api_key`, `secret`, `signature`, `Authorization`). Allowlist de logs sur les pydantic models. |
| **Trigger** | Audit grep périodique sur les logs |
| **Test** | Test unitaire qui force un log et vérifie qu'aucun secret n'apparaît |

---

## 6. Catégorie JURIDIQUE (RJ)

### RJ-1 — Régulation crypto change dans la juridiction de l'humain

| Champ | Valeur |
|---|---|
| **Probabilité** | Moyen (la régulation crypto évolue vite en Europe avec MiCA) |
| **Impact** | Moyen→Élevé |
| **Description** | Nouvelle obligation déclarative, KYC, ou interdiction de certaines activités |
| **Mitigation** | Veille manuelle. Pause + revue si changement significatif. |
| **Trigger** | Annonce régulateur → revue manuelle |

### RJ-2 — Exchange (Binance) bloque l'accès à la juridiction

| Champ | Valeur |
|---|---|
| **Probabilité** | Faible (Binance EU OK pour MiCA-compliant) |
| **Impact** | Élevé (besoin de migrer vers un autre exchange) |
| **Description** | Binance se retire d'un pays → comptes restreints |
| **Mitigation** | Adapter design abstrait (P0-1) permet de switcher vers Kraken si nécessaire. Mais l'effort de migration reste 1-2 sessions code. |
| **Trigger** | Annonce Binance → migration Kraken planifiée |

### RJ-3 — Tax reporting

| Champ | Valeur |
|---|---|
| **Probabilité** | Certain (chaque année) |
| **Impact** | Moyen (temps + coût expert-comptable) |
| **Description** | Déclaration des plus-values crypto annuelle |
| **Mitigation à coder** | Export CSV trades + P&L par fiscal year (à décider en Phase 0 si on l'inclut ou pas). Si non inclus : export manuel via Binance interface annuelle. |

---

## 7. Tableau de synthèse — risques par catégorie et sévérité

| ID | Risque | Proba | Impact | Mitigation où | Statut |
|---|---|---|---|---|---|
| **RT-1** | Bug LOT_SIZE | E | M | P0-1 | À coder |
| **RT-2** | WS gap silencieux | E | M-E | P0-1 | À coder |
| **RT-3** | Process crash | M | **CAT** | P1-2 + V5.3 ✓ | À valider |
| **RT-4** | Double-soumission | M | E | P0-1 + V5.3 ✓ | À coder |
| **RT-5** | Time sync drift | F | E | P0-1 | À coder |
| **RT-6** | Rate limit Binance | F | M | P0-1 | À coder |
| **RM-1** | Flash crash | M | **CAT** | P1-1 + P0-3 + P1-3 + V5.3 ✓ | À coder + valider |
| **RM-2** | Stratégie drift | E | M-E | P2 | À coder plus tard |
| **RM-3** | Asset delisted | F | M | P0-2 (auto-blacklist) | À coder |
| **RM-4** | Liquidité weekend | E | M | P1 (trading hours) | À coder |
| **RH-1** | Earn activé par mégarde | M | **CAT** | P0-2 | À coder |
| **RH-2** | Whitelist drift halal | F | M | P0-2 + revue trim. | À coder |
| **RH-3** | Stablecoin ambiguïté | E | M | P0-2 + décision Phase 0 | À décider |
| **RH-4** | Airdrops non sollicités | M | F-M | P0-2 | À coder |
| **RO-1** | Disk saturé | M | E | P1-5 | À coder |
| **RO-2** | Humain panique | E | E | P1-3 + pré-engagement | À coder + discipline |
| **RO-3** | Régression code | M | M-E | Tests verts + replay validé | Process |
| **RO-4** | Calibration obsolète | E | M-E | Recalibration trimestrielle | Process |
| **RS-1** | API key compromise | F-M | **CAT** | P0-4 + permissions strictes | À coder |
| **RS-2** | VPS compromis root | F | **CAT** | OS hardening | Setup VPS |
| **RS-3** | Logs leak credentials | E | E | P0-1 + P1-5 sanitization | À coder |
| **RJ-1** | Régulation change | M | M-E | Veille manuelle | Process |
| **RJ-2** | Binance bloque juridiction | F | E | Adapter design abstrait | OK |
| **RJ-3** | Tax reporting | Certain | M | Export CSV ou manuel | À décider |

**Comptage** :
- **5 risques Catastrophique** (RT-3, RM-1, RH-1, RS-1, RS-2) → **tous bloquants** pour Phase 3
- **8 risques Élevé**
- **9 risques Moyen**
- **2 risques Faible**

**Tous les Catastrophique sont mitigés par les chantiers P0/P1.** Aucun n'est laissé sans mitigation. C'est la condition non-négociable pour passer en MICRO_LIVE.

---

## 8. Triggers globaux qui forcent une régression de phase

| Trigger | Action automatique | Action humaine |
|---|---|---|
| Drawdown live > 5 % en 1 jour | Daily P&L breaker → SHADOW automatique | Investigation 24h |
| Drawdown live > 10 % en 1 semaine | Kill switch ARMED | Retour Phase 2 SHADOW |
| Drawdown live > 15 % cumulé | Kill switch CRITICAL | Retour Phase 1 + revue complète |
| Reconciliation divergence critique | Kill switch | Investigation immédiate |
| Halal violation détectée | Kill switch + alerte CRITICAL | Audit policy + purification |
| API key suspecte (orders non émis) | Kill switch + révocation clé | Recréation environnement |
| 3 incidents techniques en 7 jours | Kill switch | Revue stabilité + retour Phase 2 |
| Sharpe rolling 30j < 0 (deux mois consécutifs) | Aucune (pas auto) | Recalibration + revue |
| Free disk < 10 % | Kill switch + alerte | Cleanup |

---

**Suite logique** : `09_CODING_SLICES_FOR_IMPLEMENTING_AGENT.md` — découpage des tranches de code pour l'agent codeur.


---

## Source: docs/production_deployment_plan/09_CODING_SLICES_FOR_IMPLEMENTING_AGENT.md

# Coding Slices — Découpage pour l'agent codeur

> **Important — recadrage du rôle Opus** :
> Ce dossier a été initialement nommé "Opus coding sessions". Après clarification du workflow (voir `00_README.md` § 0), **Opus ne code pas le projet**. Opus produit les MD de cadrage (= ce dossier). L'**agent codeur** (Sonnet en session locale dans le repo) lit ces MD et code les tranches.
>
> Ce fichier liste donc les **tranches de code à exécuter par l'agent codeur**, pas des "sessions Opus". Le découpage en tranches est conçu pour :
> 1. Tenir dans la fenêtre d'une session de code raisonnable
> 2. Produire un état mergeable (tests verts) à la fin de chaque tranche
> 3. Permettre rollback partiel si une tranche échoue

> **Règle d'or** : à chaque début de tranche, l'agent codeur **vérifie l'état réel du repo** (le repo gagne contre le MD). Toute contradiction est remontée, pas résolue silencieusement.

---

## 1. Découpage par phase

### Phase 1 (P0) — 6 à 10 tranches
### Phase 1bis (P1) — 3 tranches
### Phase 2 (V37 bricks) — 1 à 2 tranches

**Total** : **10 à 15 tranches code** pour atteindre le niveau de prêt-pour-MICRO_LIVE.

---

## 1bis. Tranches intermédiaires historiques `W1/W2/W3`, toujours valides après `12`

`12_LOCAL_LAB_VS_VPS_SEPARATION.md` est maintenant publié. Les tranches `W1/W2/W3` restent valides comme historique et comme base de travail, mais leur ownership n'est plus "à fixer plus tard" :
- `12_...` fixe la frontière Local IA Lab / VPS
- `13_...` fixe la méthode de calibration
- `14_...` fixe la math des gates Shadow

### Tranche W1 — Inventaire des consommateurs de seuils dynamiques

**Statut repo réel au 2026-04-09** — fait via `11A_DYNAMIC_THRESHOLDS_REPO_CROSSCHECK.md`.

**Objectif** — Mapper, depuis `11_DYNAMIC_THRESHOLDS_CATALOG.md`, tous les modules du repo qui devront consommer un seuil calibré.

**Périmètre** :
- lecture du catalogue `11_DYNAMIC_THRESHOLDS_CATALOG.md`
- cross-check contre le repo réel
- table de mapping `threshold_id -> source_module -> état réel du code`

**Invariants** :
- pas de changement de comportement runtime
- pas de hardcoding de valeurs issues du catalogue
- si un module du catalogue n'existe pas encore dans le repo, le tracer comme `future target`, pas comme bug du repo

**Critères d'acceptation** :
- [ ] chaque seuil du catalogue a un statut `exists / partial / future target`
- [ ] les contradictions doc/code sont tracées explicitement
- [ ] aucun code runtime modifié

### Tranche W2 — Contrat partagé de calibration dynamique

**Statut repo réel au 2026-04-09** — tranche codée en shared core via `src/calibration_loader/`.

**Objectif** — Préparer la couche shared core minimale pour lire des artefacts de calibration signés, avec ownership désormais fixé par `12_...`.

**Périmètre** :
- contrats typés de calibration
- loader/validator partagé
- tests de parsing/validation

**Invariants** :
- `src/calibration_loader/` reste shared core ; il ne doit être dupliqué ni côté VPS ni côté Local IA Lab
- pas de valeur seuil hardcodée en fallback silencieux
- le repo réel gagne si le catalogue pointe vers des modules encore absents

**Critères d'acceptation** :
- [x] format d'artefact de calibration lisible et validable
- [x] erreurs explicites si artefact manquant / invalide / non signé
- [x] tests ciblés verts

**Preuve repo** :
- `src/calibration_loader/contracts.py`
- `src/calibration_loader/loader.py`
- `tests/test_calibration_loader/test_contracts.py`
- `tests/test_calibration_loader/test_loader.py`
- `pytest tests/test_calibration_loader/test_contracts.py tests/test_calibration_loader/test_loader.py -q --basetemp=build/pytest-calibration-loader-proof`

### Tranche W3 — Durcissement du rail IA Lab réel déjà existant

**Statut repo réel au 2026-04-09** — en cours, avec nouvelles garanties sur la reprise metadata/chunk session et sur la cohérence sémantique des sidecars gouvernés.

**Objectif** — Continuer à sécuriser le rail déjà présent dans le repo :
`local_replay_runtime -> governed export -> backtest_artifact_import -> VPS Shadow`

**Périmètre** :
- persistance fail-safe
- reprise / resume metadata
- evidence stores
- supervision/monitoring de ce rail

**Invariants** :
- ne pas ouvrir de faux package `src/local_ai_lab`
- ne pas contourner `SHADOW`
- ne pas contredire la séparation fixée par `12_...`

**Critères d'acceptation** :
- [ ] slices bornés
- [ ] tests ciblés verts
- [ ] tracker + mémoire mis à jour

**Preuve repo déjà fermée sur le slice courant** :
- `src/local_replay_runtime/replay_orchestrator.py`
- `tests/test_local_replay_runtime/test_replay_orchestrator.py`
- `pytest tests/test_local_replay_runtime/test_replay_orchestrator.py tests/test_local_replay_runtime/test_local_replay_export_launcher.py -q --basetemp=build/pytest-local-replay-resume-proof`
- résultat: `20 passed`

**Comportement obtenu** :
- backup `.corrupted` + fail-close explicite si `replay_session_config.json` est corrompu
- backup `.corrupted` + fail-close explicite si `replay_run_manifest.json` est corrompu
- backup `.corrupted` + fail-close explicite si `replay_chunk_session.json` est corrompu
- même politique pour les sidecars relus pendant un resume (`performance_mode_guard`, `run_consistency_guard`, `replay_metrics`)
- `src/backtest_artifact_import/export_dir_bridge.py` applique désormais la même discipline sur le pont export→import
- `replay_run_manifest.json` et `feature_bridge.json` sont backupés en `.corrupted` puis rejetés explicitement si corrompus
- `parity_diagnostics.json`, `replay_metrics.json`, et `replay_dtr.jsonl` sont maintenant aussi validés explicitement sur le vrai chemin `export_dir`
- cette validation est maintenant typée quand le repo a déjà un contrat:
  - `parity_diagnostics.json` via un schéma minimal `ReplayParityDiagnosticsSummary`
  - `replay_metrics.json` via `ReplayMetricsSummary`
  - `replay_dtr.jsonl` / `replay_dtr.json` via `DTRRecord`
- la validation du vrai `export_dir` rejette maintenant aussi les contradictions sémantiques entre `replay_run_manifest` et les sidecars typés
  - `review_export.md` doit contenir une provenance cohérente avec le manifest et les sidecars
  - `run_id / strategy_id / strategy_version / lineage_version / profile_scope / runtime_mode / performance_mode` doivent matcher le manifest
  - `total_opportunities / total_records / dtr_coverage` doivent matcher `replay_metrics`
  - `status / decision_match_rate` doivent matcher `parity_diagnostics`
  - `feature_bridge.dataset_id` doit matcher `replay_run_manifest.dataset_manifest_id`
  - `feature_bridge.feature_set_version` doit matcher `replay_run_manifest.feature_set_version`
  - `feature_bridge.transform_set_version` doit matcher `replay_run_manifest.transform_set_version`
  - `feature_bridge.pairs` / `feature_bridge.engines` doivent matcher `tested_pairs` / `engine_scope`
  - `parity_diagnostics.dataset_id` doit matcher `replay_run_manifest.dataset_manifest_id`
  - `replay_metrics.total_records` doit matcher le nombre réel de `DTRRecord`
  - `pair_aggregates` et `engine_aggregates` doivent sommer à `total_records`
  - les pairs / engines portés par `replay_metrics` et `replay_dtr` doivent rester dans `tested_pairs` / `engine_scope`
  - les `DTRRecord.runtime_mode` doivent rester `local_replay`
  - les timestamps DTR doivent rester dans la fenêtre horloge du manifest
  - `replay_metrics` doit rester exactement recalculable depuis les `DTRRecord` exportés
  - aucun sidecar gouverné d'un vrai `export_dir` ne peut se résoudre hors de ce dossier, même via une référence détournée
  - un vrai `export_dir` ne peut plus contenir plusieurs fichiers candidats pour le même sidecar gouverné; l'ambiguïté est maintenant fail-close
  - un `ArtifactUploadRequest` gouverné est maintenant rejeté dès sa construction si `manifest.review_export_ref / feature_bridge_ref / parity_diagnostics_ref / replay_metrics_ref / replay_dtr_ref` divergent du `payload_bundle`
  - un `ArtifactPayloadRefBundle` gouverné est maintenant rejeté s'il contient des doublons, y compris via `supplementary_refs`
- preuve la plus récente:
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_local_replay_runtime/test_replay_executor.py tests/test_local_replay_runtime/test_replay_session_state.py tests/test_local_replay_runtime/test_artifact_exporter.py -q`
  - résultat: `104 passed`
- les refs symboliques non-file du chemin démo (`feature_bridge:<id>`) restent admises comme métadonnées non export-dir, sans desserrer la politique sur les vrais sidecars gouvernés

Ces tranches intermédiaires existent pour éviter un arrêt total du travail. Elles préparent Phase 0/1 et restent compatibles avec la séparation désormais figée par `12_...`.

### 1ter. Piste future optionnelle — vue flotte multi-VPS read-only

Cette piste n'est **pas** une tranche runtime immédiate. Elle est mémorisée ici pour multi-session, conformément à `12_...` :

- objectif : lister plusieurs VPS par `vps_id` avec seulement `health_status / runtime_mode / artifact_version / heartbeat_age / alert_state`
- invariant : aucun pilotage multi-VPS, aucun failover, aucune promotion croisée
- drill-down : pour le détail complet, l'opérateur se connecte à la VPS choisie
- statut : `M0` fermé sur contrats typés read-only dans `src/monitoring/contracts.py`; `M1/M2` restent futurs et non bloquants pour P0/P1
- preuve `M0` :
  - `tests/test_monitoring/test_monitoring_contracts.py`
  - `rtk pytest tests/test_monitoring/test_monitoring_contracts.py tests/test_monitoring/test_monitoring_backend.py tests/test_monitoring/test_monitoring_runtime.py tests/test_ui/test_technical_dashboard.py -q`
  - résultat : `73 passed`

---

## 2. Phase 1 — Tranches P0

### Tranche T1 — P0-1.A : Squelette adapter Binance + REST client read-only

**Statut repo réel au 2026-04-09** — tranche codée et prouvée localement.

- `src/interface_contracts/binance_contracts.py` existe
- `src/venue_adapters/binance_spot/{__init__,rest_client,time_sync,credential_loader}.py` existe
- `config/binance_adapter.yml` existe
- `tests/test_venue_adapters/test_binance_spot/test_*.py` existe
- preuve locale:
  - `PYTHONPATH=src python -m pytest tests/test_venue_adapters/test_binance_spot/test_credential_loader.py tests/test_venue_adapters/test_binance_spot/test_time_sync.py tests/test_venue_adapters/test_binance_spot/test_rest_client.py tests/test_execution_backbone/test_venue_constraints_provider.py -q`
  - résultat: `15 passed`
- résidu honnête:
  - le critère Binance Testnet reste `manuel / humain`
  - `credential_loader.py` reste un stub explicite jusqu'à `T2`

**Objectif** — Créer la structure du dossier `src/venue_adapters/binance_spot/` avec les modules vides + le REST client en read-only (account snapshot, exchange info, time sync).

**Périmètre** :
- Création du dossier `binance_spot/` et de ses modules vides
- `rest_client.py` : query `/api/v3/account`, `/api/v3/exchangeInfo`, `/api/v3/time` (read-only, pas de signed POST)
- `time_sync.py` : sync horloge locale vs Binance, alerter si drift > 500 ms
- Config loader pour les credentials (sealed via P0-4 — voir T2)

**Invariants** :
- Aucun code de soumission d'order dans cette tranche
- Aucun seuil hardcodé (les seuils de drift, retry, etc. viennent de `config/binance_adapter.yml` chargé via `calibration_loader/`)
- Tests unitaires pour chaque module

**Modules touchés** :
- Nouveau : `src/venue_adapters/binance_spot/{__init__,rest_client,time_sync,credential_loader}.py`
- Nouveau : `tests/test_venue_adapters/test_binance_spot/test_*.py`
- Config : `config/binance_adapter.yml` (template)

**Interfaces I/O** :
- Entrée : credentials sealed (P0-4) → `credential_loader.load()` → `BinanceCredentials` pydantic frozen
- Sortie : `AccountSnapshot`, `ExchangeInfo`, `ServerTime` (pydantic models avec frozen=True)

**Ce qu'il ne faut PAS faire** :
- Pas de POST/PUT/DELETE
- Pas d'utilisation de `requests` directement — utiliser `httpx` async
- Pas de retry automatique caché dans la lib HTTP
- Pas de logger qui sérialize les credentials

**Critères d'acceptation** :
- [ ] `rest_client.get_account_snapshot()` retourne un `AccountSnapshot` valide depuis Binance Testnet
- [ ] `time_sync.sync()` retourne le drift en ms, alerte si > 500ms
- [ ] `tests/` ≥ 80 % coverage sur les nouveaux modules
- [ ] Aucun secret loggé (vérifié via test unitaire)
- [ ] `pytest -xvs tests/venue_adapters/binance_spot/` vert

**Ordre de réalisation** :
1. Définir les pydantic models I/O dans `interface_contracts/binance_contracts.py`
2. Coder `time_sync.py` (le plus simple)
3. Coder `credential_loader.py` (avec stub pour P0-4)
4. Coder `rest_client.py` méthodes read-only
5. Tests unitaires
6. Test intégration testnet (manuel, à valider par humain)

**Preuves attendues** :
- Logs `rest_client_test_<date>.log` propres (pas de credential leak)
- Snapshot pydantic d'un account testnet avec balance ≠ 0
- Diff coverage tracker

**LOC estimées** : 600-900

---

### Tranche T2 — P0-4 : Sealed secrets

**Statut repo réel au 2026-04-09** — tranche codée en backend borné local/dev, avec résidu de portabilité VPS.

- `src/secrets_manager/{__init__,__main__,_dpapi,loader,sealer,cli}.py` existe
- `src/secrets_manager/README.md` existe
- `src/venue_adapters/binance_spot/credential_loader.py` sait maintenant charger un fichier scellé `.sealed.json`
- preuve locale:
  - `PYTHONPATH=src python -m pytest tests/test_secrets_manager/test_loader.py tests/test_venue_adapters/test_binance_spot/test_credential_loader.py tests/test_venue_adapters/test_binance_spot/test_time_sync.py tests/test_venue_adapters/test_binance_spot/test_rest_client.py -q`
  - résultat: `12 passed`
- résidu honnête:
  - backend implémenté: `windows_dpapi_user` + `master.key` comme entropie obligatoire
  - `age` / `sops` / backend Linux VPS ne sont pas encore codés
  - la tranche est donc fermée pour l'environnement local Windows actuel, pas comme story finale cross-platform

**Objectif** — Système de chargement des credentials sans clé en clair sur disque.

**Périmètre** :
- Choix de la primitive : `age` (recommandé pour la simplicité) ou `sops`
- `src/secrets_manager/` avec encrypt/decrypt
- CLI helper `python -m secrets_manager seal config/api.yml` → produit `config/api.yml.age`
- Loader runtime : `secrets_manager.load("config/api.yml.age", key_path="~/.config/v53/master.key")`
- Documentation `secrets_manager/README.md` pour le workflow humain

**Invariants** :
- Jamais de clé dans le repo, jamais en clair sur disque hors mémoire
- Master key chargée depuis `~/.config/v53/master.key` (mode 0600), pas dans le repo
- Permissions VPS : `chmod 600` sur tous les `.age`

**Modules touchés** :
- Nouveau : `src/secrets_manager/{__init__,sealer,loader,cli}.py`
- Nouveau : `tests/secrets_manager/test_*.py`
- Doc : `src/secrets_manager/README.md`

**Critères d'acceptation** :
- [ ] Encrypt/decrypt round-trip OK
- [ ] CLI fonctionnel
- [ ] Aucune clé en clair après seal
- [ ] Tests verts

**LOC estimées** : 200-400

---

### Tranche T3 — P0-1.B : WebSocket client + gap recovery

**Statut repo réel au 2026-04-09** — noyau borné codé et prouvé localement, mais tranche pas encore totalement terminée au sens live/testnet.

- `src/venue_adapters/binance_spot/ws_client.py` existe
- `src/venue_adapters/binance_spot/orderbook_manager.py` existe
- `src/venue_adapters/binance_spot/rest_client.py` sait maintenant produire un vrai `depth snapshot` REST typé
- `build_rest_depth_snapshot_provider()` existe pour brancher explicitement le bootstrap `snapshot REST -> WS deltas`
- `src/data_backbone/freshness_checker/venue_stream_freshness.py` existe
- `src/protocols/shadow_live_websocket.py` exporte maintenant aussi `first_update_id / final_update_id` sur les payloads depth
- preuve locale:
  - `PYTHONPATH=src python -m pytest tests/test_venue_adapters/test_binance_spot/test_rest_client.py tests/test_venue_adapters/test_binance_spot/test_orderbook_manager.py tests/test_venue_adapters/test_binance_spot/test_ws_client.py tests/test_venue_adapters/test_binance_spot/test_time_sync.py tests/test_protocols/test_shadow_live_websocket.py -q`
  - résultat: `19 passed`
- cross-check couplé `T1 + T2 + T3`:
  - `PYTHONPATH=src python -m pytest tests/test_secrets_manager/test_loader.py tests/test_venue_adapters/test_binance_spot/test_credential_loader.py tests/test_venue_adapters/test_binance_spot/test_time_sync.py tests/test_venue_adapters/test_binance_spot/test_rest_client.py tests/test_venue_adapters/test_binance_spot/test_orderbook_manager.py tests/test_venue_adapters/test_binance_spot/test_ws_client.py tests/test_execution_backbone/test_venue_constraints_provider.py tests/test_protocols/test_shadow_live_websocket.py -q`
  - résultat: `33 passed`
- résidu honnête:
  - pas encore de validation live Binance/testnet
  - pas encore de preuve 24h RAM leak
  - branchement live complet et soak-test restent à faire

**Objectif** — WebSocket Binance avec reconnect protocol officiel + gap recovery.

**Périmètre** :
- `ws_client.py` : connect / subscribe / handle / reconnect
- Application du protocole officiel Binance "How to manage a local order book" (snapshot REST + replay deltas)
- Gap detector : si gap > 5 secondes → blocage des nouveaux trades
- Heartbeat monitoring : si silent > 30 sec → force reconnect
- Intégration avec `data_backbone/freshness_checker/`

**Invariants** :
- Au boot : snapshot REST puis WS, jamais l'inverse
- En cas de reconnect : nouveau snapshot REST avant de reprendre
- En cas de gap détecté : refus de trader jusqu'à resync OK

**Modules touchés** :
- Nouveau : `src/venue_adapters/binance_spot/ws_client.py`
- Nouveau : `src/venue_adapters/binance_spot/orderbook_manager.py`
- Modifié : `src/data_backbone/freshness_checker/` (ajout d'un hook)

**Critères d'acceptation** :
- [ ] Reconnect automatique OK sur coupure simulée
- [ ] Gap > 5s → état `STALE`, refus de trader
- [ ] Snapshot REST + replay correct (testé via mock)
- [ ] Aucune RAM leak sur 24h de run continu

**Preuves attendues** :
- Test 24h en testnet sans crash mémoire
- Logs reconnects + gap detect

**LOC estimées** : 700-1000

---

### Tranche T4 — P0-1.C : Order translator + signed POST

**Statut repo réel au 2026-04-09** — socle borné codé et prouvé localement, mais tranche pas encore totalement terminée au sens live/testnet.

- `src/venue_adapters/binance_spot/order_translator.py` existe
- `src/venue_adapters/binance_spot/error_classifier.py` existe
- `src/venue_adapters/binance_spot/execution_adapter.py` existe
- `src/venue_adapters/binance_spot/user_data_events.py` existe
- `src/venue_adapters/binance_spot/user_data_ws_client.py` existe
- `src/venue_adapters/binance_spot/bootstrap.py` existe
- `src/protocols/execution_runtime_bootstrap.py` sait maintenant construire un `ExecutionRuntime` Binance via ce builder
- `scripts/run_build9_core_smoke.py` consomme maintenant ce bootstrap sur un smoke borné local
- `src/venue_adapters/binance_spot/rest_client.py` supporte maintenant le signed `POST /api/v3/order`
- `src/venue_adapters/binance_spot/rest_client.py` supporte maintenant le signed `GET /api/v3/openOrders`
- `src/venue_adapters/binance_spot/rest_client.py` supporte maintenant le signed `DELETE /api/v3/order`
- `BinanceSpotExecutionAdapter` satisfait maintenant le protocole `ExecutionVenueAdapter` avec :
  - submit borné
  - replace borné via cancel + submit
  - cancel borné
  - remote state minimal via `openOrders + account snapshot`
  - `poll_order_events()` draine maintenant une source user-data authentifiée bornée quand elle est injectée
  - le parser local couvre déjà `executionReport -> ACK/FILL/CANCELLED/EXPIRED/REJECTED`
  - un client websocket user-data borné sait maintenant faire `subscribe.signature -> poll payloads`
  - un builder borné sait maintenant construire l'adapter depuis `BinanceAdapterConfig + credentials`, avec injection optionnelle du user-data websocket
  - le bootstrap runtime sait maintenant consommer ce builder sur le rail `protocols`
  - un vrai script caller local existe maintenant via `run_build9_core_smoke.py`
- le `clientOrderId` déterministe est maintenant basé sur `engine_id + intent_id`, parce que le repo réel gouverné porte `engine_id` dans `ExecutionIntent`, pas `strategy_id`
- preuve locale ciblée:
  - `rtk pytest tests/test_execution_backbone/test_build9_core_smoke_script.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_venue_adapters/test_binance_spot/test_bootstrap.py tests/test_venue_adapters/test_binance_spot/test_user_data_ws_client.py tests/test_venue_adapters/test_binance_spot/test_execution_adapter.py tests/test_execution_backbone/test_execution_runtime.py -q`
  - résultat: `28 passed`
- cross-check plus large:
  - `rtk pytest tests/test_venue_adapters/test_binance_spot tests/test_execution_backbone tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_build9_core_smoke_script.py -q`
  - résultat: `193 passed`
- résidu honnête:
  - pas encore de soumission order testnet réelle
  - pas encore de fills/positions live complets via flux événementiel Binance

**Objectif** — Traduction des décisions internes en orders Binance + soumission signée.

**Périmètre** :
- `order_translator.py` : decision → BinanceOrder pydantic
- Validation contre `venue_constraints` (LOT_SIZE, MIN_NOTIONAL, PRICE_FILTER) **avant soumission**
- Signed POST `/api/v3/order` avec HMAC-SHA256
- `clientOrderId` déterministe : `f"v53_{engine_id}_{intent_id}"` (max 36 chars) dans le repo réel actuel
- Pas de retry HTTP : retry explicite après vérif `/openOrders`
- Error classifier (`error_classifier.py`) : mapper les codes Binance vers `OrderRejected`, `InsufficientBalance`, `InvalidLotSize`, etc.

**Invariants** :
- Pre-trade simulation : si `venue_constraints` rejette → pas de submit
- Idempotency : un `intent_id` ne peut produire qu'un seul order accepté
- En cas de timeout : pas de retry automatique, query `/openOrders` pour vérifier

**Modules touchés** :
- Nouveau : `src/venue_adapters/binance_spot/{order_translator,error_classifier}.py`
- Nouveau : signed POST handlers
- Modifié : `src/execution_backbone/` (point de connexion)

**Critères d'acceptation** :
- [ ] Soumission order testnet OK
- [ ] Rejet pré-soumission sur LOT_SIZE invalide
- [ ] Pas de double soumission lors d'un timeout simulé
- [ ] Tous les codes d'erreur Binance documentés sont mappés

**LOC estimées** : 800-1200

---

### Tranche T5 — P0-2 : Halal compliance layer

**Statut repo réel au 2026-04-09** — tranche bornée avancée et prouvée localement, mais pas encore totalement terminée.

- `src/sharia_compliance/contracts.py` existe
- `src/sharia_compliance/policy_loader.py` existe
- `src/sharia_compliance/asset_whitelist.py` existe
- `src/sharia_compliance/asset_blacklist.py` existe
- `src/sharia_compliance/stablecoin_policy.py` existe
- `src/sharia_compliance/trade_type_guard.py` existe
- `src/sharia_compliance/pair_screening.py` existe
- `src/sharia_compliance/pair_screening_registry.py` existe
- `src/sharia_compliance/pair_screening_audit.py` existe
- `src/sharia_compliance/purification_calculator.py` existe
- `src/sharia_compliance/policy_audit_logger.py` existe
- `src/sharia_compliance/account_features_audit.py` existe
- `src/sharia_compliance/sharia_runtime.py` existe
- `src/venue_adapters/binance_spot/account_feature_provider.py` existe
- `scripts/run_sharia_account_audit.py` existe
- `scripts/run_sharia_pair_screening_audit.py` existe
- `src/sharia_compliance/sharia_alerts.py` existe
- `config/sharia/policy_v1.yml` existe
- `src/execution_backbone/execution_runtime.py` appelle maintenant `sharia_trade_authorizer.authorize_trade()` avant toute soumission venue
- `NoTradeReason.SHARIA_BLOCKED` existe maintenant dans le runtime d'exécution
- preuves locales ciblées:
  - `rtk pytest tests/test_sharia_compliance/test_purification_calculator.py tests/test_sharia_compliance/test_account_features_audit.py -q`
  - résultat: `6 passed`
  - `rtk pytest tests/test_venue_adapters/test_binance_spot/test_rest_client.py tests/test_venue_adapters/test_binance_spot/test_account_feature_provider.py tests/test_sharia_compliance/test_account_features_audit.py tests/test_sharia_compliance/test_account_features_audit_launcher.py -q`
  - résultat: `13 passed`
  - `rtk pytest tests/test_sharia_compliance/test_sharia_alerts.py tests/test_sharia_compliance/test_account_features_audit_launcher.py tests/test_venue_adapters/test_binance_spot/test_account_feature_provider.py tests/test_venue_adapters/test_binance_spot/test_rest_client.py -q`
  - résultat: `11 passed`
  - `python -m pytest tests/test_sharia_compliance/test_pair_screening.py tests/test_sharia_compliance/test_trade_type_guard.py tests/test_execution_backbone/test_execution_runtime.py -q`
  - résultat: `31 passed`
  - `python -m pytest tests/test_sharia_compliance/test_pair_screening_registry.py tests/test_sharia_compliance/test_pair_screening_audit.py tests/test_sharia_compliance/test_pair_screening_audit_launcher.py tests/test_sharia_compliance/test_pair_screening.py tests/test_sharia_compliance/test_trade_type_guard.py tests/test_execution_backbone/test_execution_runtime.py -q`
  - résultat: `37 passed`
  - `rtk pytest tests/test_sharia_compliance tests/test_execution_backbone/test_execution_runtime.py -q`
  - résultat: `39 passed`
  - `rtk pytest tests/test_sharia_compliance tests/test_execution_backbone/test_execution_runtime.py -q`
  - résultat: `29 passed`
- cross-check élargi:
  - `rtk pytest tests/test_sharia_compliance tests/test_execution_backbone/test_execution_runtime.py tests/test_venue_adapters/test_binance_spot tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_build9_core_smoke_script.py -q`
  - résultat: `82 passed`
  - `rtk pytest tests/test_sharia_compliance tests/test_execution_backbone tests/test_venue_adapters/test_binance_spot tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_build9_core_smoke_script.py -q`
  - résultat: `208 passed`
- résidu honnête:
  - pas encore de preuve Testnet réelle du launcher d'audit hebdomadaire
  - pas encore de kill switch ou d'alerte externe branchés depuis ces `AlertRecord`
  - pas encore de provider live/externe branché pour alimenter automatiquement le pair screening AAOIFI
  - la version courante couvre le veto halal avant submit, le pair screening AAOIFI déterministe via metadata, le registre dataset local versionné, l'audit HC-4 des paires tradées, la purification bornée, le provider Binance read-only, le launcher d'audit hebdomadaire et la projection `AlertRecord` critique, pas encore toute la story complète T5

**Objectif** — Module `sharia_compliance/` qui enforce les règles halal de manière non-contournable.

**Périmètre** :
- `asset_whitelist.py` + `asset_blacklist.py` (chargés depuis YAML versionné)
- `stablecoin_policy.py` (selon décision Phase 0)
- `trade_type_guard.py` : refuse tout trade type ≠ SPOT (pas de margin, pas de futures, pas de borrow)
- `purification_calculator.py`
- `policy_audit_logger.py` : log de chaque autorisation/refus avec versioning
- `sharia_runtime.py` : façade `authorize_trade(decision) -> ShariaPermit | ShariaRejection`
- Audit hebdomadaire `account_features_audit.py` : query Binance et alerte si Earn/Margin/Futures détectés

**Invariants** :
- Aucun trade ne peut être soumis sans passer par `sharia_runtime.authorize_trade()`
- Refus loggué = trade jamais soumis
- Versioning des policies : si la policy change, on peut retracer les trades sous v1 vs v2

**Modules touchés** :
- Nouveau : `src/sharia_compliance/` (full module)
- Nouveau : `tests/sharia_compliance/`
- Config : `config/sharia/policy_v1.yml`
- Hook : `execution_backbone/order_decider/` doit appeler `sharia_runtime.authorize_trade()` avant tout submit

**Critères d'acceptation** :
- [ ] 100 % des décisions passent par sharia_runtime
- [ ] Tests : asset blacklisté → refus
- [ ] Tests : asset OK + stablecoin OK → permit
- [ ] Audit hebdomadaire détecte un Simple Earn activé en < 24h
- [ ] Policy versioning fonctionne

**LOC estimées** : 800-1200

---

### Tranche T6 — P0-3 : Fee-aware minimum-edge filter

**Statut repo réel au 2026-04-10** — tranche partiellement codée sur le vrai coeur Local IA Lab + shared core, avec premier consommateur runtime réel.

- `src/local_replay_runtime/edge_gate_calibration.py` existe
- `src/scoring_backbone/fee_aware_edge_gate.py` existe
- `tests/test_local_replay_runtime/test_edge_gate_calibration.py` existe
- `tests/test_scoring_backbone/test_fee_aware_edge_gate.py` existe
- preuve locale:
  - `rtk pytest tests/test_local_replay_runtime/test_edge_gate_calibration.py tests/test_scoring_backbone/test_fee_aware_edge_gate.py -q`
  - résultat: `6 passed`
  - `rtk pytest tests/test_calibration_loader/test_contracts.py tests/test_calibration_loader/test_loader.py tests/test_local_replay_runtime/test_replay_executor.py tests/test_scoring_backbone/test_scoring_runtime.py -q`
  - résultat: `22 passed`
- closure obtenue:
  - le premier producteur `13-A EDGE` existe maintenant côté Local IA Lab
  - `THR-E01` et `THR-E02` peuvent être calibrés depuis des `DTRRecord` replay exécutés
  - la publication est conservative: borne haute d'IC bootstrap + floor humain
  - un artefact partagé `CalibrationArtifact` peut maintenant être produit pour `THR-E01` / `THR-E02`
  - `scripts/run_edge_gate_calibration.py` lit maintenant soit un `replay_dtr.jsonl` gouverné, soit un `export_dir` gouverné complet, puis écrit un `edge_gate.yml` signé
  - le même launcher émet maintenant `edge_gate.input_summary.json` comme sortie future-facing d'audit / dashboard
  - `scripts/run_local_lab_analysis_bundle.py` peut maintenant enchaîner le même `export_dir` vers post-trade review + edge calibration avec une sortie unique `local_lab_analysis_summary.json`
  - `scripts/run_local_lab_post_trade_review.py` émet maintenant aussi `trade_loss_attribution.json` comme sidecar typé par trade
  - ce sidecar explique pourquoi un trade perd (`cost_drift / sterilization / edge_degraded / trace_coverage / unclassified_loss`) et propose une action préventive gouvernée
  - `scripts/run_local_lab_analysis_bundle.py` remonte maintenant aussi ce sidecar dans son résumé future-facing
  - `src/local_replay_runtime/walk_forward_review.py` existe maintenant comme gate humain typé pour anti-fuite / anti-overlap
  - `scripts/run_local_lab_analysis_bundle.py` émet désormais `walk_forward_review.template.json` et `walk_forward_review.summary.json`
  - par défaut, le walk-forward reste `pending`; il faut un review humain approuvé pour faire passer `walk_forward_pass`
  - `src/local_replay_runtime/artifact_proof_summary_builder.py` existe maintenant comme builder conservatif du `ArtifactProofSummary` canonique côté Local IA Lab
  - `scripts/run_local_lab_analysis_bundle.py` émet désormais aussi `artifact_proof_summary.json` et `artifact_proof_assessment.json`
  - doctrine now reflected in code:
    - les dimensions prouvables aujourd'hui sont dérivées depuis `MetaRuntimeResult`, `trade_loss_attribution.json`, et `walk_forward_review.summary.json`
    - les dimensions non encore closes par une vraie étude d'ablation restent fail-close, pas remplies par des valeurs flatteuses
    - en pratique, le bundle Lab sait maintenant dire explicitement `not ready for VPS import yet` au lieu d'échouer implicitement
  - `src/local_replay_runtime/artifact_ablation_study.py` existe maintenant comme étude baseline-vs-candidate gouvernée
  - `scripts/run_local_lab_analysis_bundle.py` accepte maintenant `--baseline-export-dir`
  - le bundle Lab émet désormais aussi `artifact_ablation_study.json`
  - si un baseline export gouverné aligné est fourni:
    - `ablation_delta_net_pnl`
    - `ablation_delta_ce`
    - `block_rate_delta`
    sont calculés à partir de DTR alignés par `dtr_id`, pas simulés
  - si aucun baseline n'est fourni, l'étude d'ablation reste explicitement `not ready`
  - `src/local_replay_runtime/local_lab_scope_matrix.py` existe maintenant comme projection multi-scope typée `pair x engine`
  - `scripts/run_local_lab_analysis_bundle.py` accepte maintenant `--all-scopes`
  - sur un export gouverné multi-scope, le bundle peut maintenant émettre une matrice `local_lab_scope_matrix.json` sans review manuelle scope par scope
  - chaque scope écrit désormais sous `output-root/scopes/<pair>__<engine>/`:
    - `post_trade_review/`
    - `artifact_ablation_study.json`
    - `artifact_proof_summary.json`
    - `artifact_proof_assessment.json`
  - la matrice future-facing expose par scope:
    - `artifact_ablation_ready`
    - `artifact_proof_ready`
    - `artifact_proof_validation_reasons`
    - les chemins de sidecars gouvernés
  - la preuve multi-scope reste fail-close:
    - `total_opportunities` est maintenant recalculé par scope, pas hérité silencieusement du manifest global
    - aucun scope ne passe en `ready` sans walk-forward humain approuvé et baseline aligné
  - `src/local_replay_runtime/artifact_release_candidate.py` existe maintenant comme sidecar de packaging Local IA Lab -> VPS
  - `scripts/run_local_lab_analysis_bundle.py` émet désormais aussi `artifact_release_candidate.json`
  - ce sidecar ne construit pas encore un `ArtifactImportRequest`; il borne le pré-packaging Lab avec:
    - `release_status`
    - `ready_for_shadow_import`
    - `blocking_reasons`
    - `release_scopes` quand une matrice multi-scope existe
  - `src/local_replay_runtime/artifact_upload_bridge_candidate.py` existe maintenant comme pont dry-run borné `release_candidate -> ArtifactUploadRequest / ArtifactImportRequest`
  - `scripts/run_local_lab_analysis_bundle.py` émet désormais aussi:
    - `artifact_import_dry_run_bridge.json`
    - `artifact_upload_request.dry_run.json`
    - `artifact_import_request.dry_run.json`
    - `artifact_import_decision.dry_run.json`
    - `artifact_upload_decision.dry_run.json`
  - ce pont reste strictement fail-close:
    - aucun `date.today()` caché pour la gouvernance
    - `artifact_class`, `artifact_scope`, `training_end`, `governance_reference_date`, `lifecycle`, `drift_score_threshold` doivent être explicites
    - sans preuve prête ou sans inputs de gouvernance explicites, le bridge reste bloqué avec raisons typées
  - ce pont expose maintenant explicitement la sémantique actuelle:
    - l'artefact source Local IA Lab reste l'artefact calibration (`edge_gate.yml`)
    - le handoff dry-run transporté aujourd'hui reste un packet gouverné dérivé du replay export (`review_packet`)
    - les sidecars n'assimilent plus implicitement ces deux identités
  - vérité importante:
    - le sidecar de release garde l'artefact Local IA Lab (`edge_gate.yml`)
    - le pont sec matérialise aujourd'hui le rail gouverné existant de `backtest_artifact_import` autour du replay/export packet
    - ce n'est pas encore un upload live ni une promotion VPS
  - `scripts/run_local_replay_export.py` peut maintenant aussi émettre cet artefact EDGE en option explicite au moment de l'export gouverné
  - le futur consommateur `src/scoring_backbone/fee_aware_edge_gate.py` existe maintenant comme helper pur résolvant `THR-E01` / `THR-E02` via `calibration_loader`
  - `src/execution_backbone/execution_runtime.py` peut maintenant bloquer un trade avant submit quand le gate fee-aware échoue
  - `src/protocols/execution_runtime_bootstrap.py` sait maintenant passer une `FeeAwareEdgeGateConfig` aux builders runtime d'exécution
  - `src/venue_adapters/binance_spot/time_sync.py` et `config/binance_adapter.yml` portent maintenant un enable flag gouverné `fee_aware_edge_gate_enabled`
  - `build_binance_execution_runtime(...)` peut maintenant dériver un config EDGE standard depuis `calibration_root/calibration_version` quand ce flag est activé
  - la sortie future-facing minimale existe maintenant aussi:
    - `NoTradeDecision.context`
    - `DecisionEvent.no_trade_reason`
    - `DecisionEvent.context`
  - le blocage fee-aware n'est donc plus seulement un `detail` texte; il expose aussi un payload structuré pour audit/monitoring futur
- résidu honnête:
  - pas encore de source standard unique injectant ce gate partout hors rail runtime Binance / builder borné
  - pas encore de consommation plus haute dans scoring / engines
  - pas encore de preuve replay réelle humaine sur un dataset de calibration signé
  - le mapping `walk_forward_review.summary.json -> ArtifactProofSummary` est maintenant ouvert et câblé côté Local IA Lab
  - le `ArtifactProofSummary` reste fail-close si aucun baseline export gouverné n'est fourni
  - le slice d'ablation baseline-vs-candidate est maintenant réellement ouvert et câblé
  - le prochain slice cœur Local IA Lab est maintenant explicite: faire évoluer ce pont sec en packaging plus complet vers le vrai handoff VPS, notamment sur la sémantique finale `artifact_id / artifact_kind`

**Objectif** — Refuser tout trade dont l'edge attendu n'est pas suffisamment supérieur aux fees + slippage.

**Périmètre** :
- `FeeAwareEdgeGate` dans `scoring_backbone/` ou `execution_backbone/`
- Formule : `accept ⇔ expected_edge_bps ≥ edge_multiplier × (fee_round_trip_bps + slippage_estimate_bps)`
- `edge_multiplier` chargé depuis l'artefact de calibration (typiquement 2.0)
- Intégration avec `execution_cost_meter/fee_meter.py` existant

**Invariants** :
- Aucun trade soumis ne peut violer cette règle
- `edge_multiplier` jamais hardcodé

**Critères d'acceptation** :
- [ ] Test : edge 10 bps, fee 5 bps, slippage 2 bps, multiplier 2 → refus (10 < 14)
- [ ] Test : edge 20 bps, fee 5 bps, slippage 2 bps, multiplier 2 → permit (20 ≥ 14)
- [ ] Hook dans le path d'exécution

**LOC estimées** : 150-300

---

### Tranche T7 — P0-5.A : Engine C tests rattrapage (Option A : feature flag)

**Objectif** — Option A simple : marquer Engine C comme `experimental` avec feature flag, ne le mettre actif que si `engines.c.enabled = True` (false par défaut). Engine C ne tournera donc PAS en MICRO_LIVE Phase 3.

**Périmètre** :
- Feature flag dans `config/engines.yml`
- Modification minimale du runtime pour skip Engine C si disabled
- Tests pour vérifier le skip

**Critères d'acceptation** :
- [ ] Engine C disabled par défaut
- [ ] Aucune décision Engine C en MICRO_LIVE
- [ ] Tests existants restent verts

**LOC estimées** : 50-100

> **Note** : Option B (refactor complet engine C) reportée à post-LIVE Phase 4. Décision à confirmer en Phase 0.

---

### Tranche T8 — P0-5.B : Engine D tests rattrapage (Option A : feature flag)

Identique à T7 mais pour Engine D.

**LOC estimées** : 50-100

---

## 3. Phase 1bis — Tranches P1

### Tranche T9 — P1-1 : Regime awareness lite (3 états)

**Objectif** — Détecteur de régime à 3 états (CALM / STRESSED / EXTREME) avec hystérésis, basé sur indicateurs simples (BTC realized vol 24h, dispersion rendements, gap-down counter).

**Périmètre** :
- `src/regime_classifier/regime_lite.py`
- Indicateurs : realized vol BTC 24h, max drawdown intraday, dispersion entre engines
- Hystérésis : remonter d'un état nécessite 2 heures de stabilité dans l'état inférieur
- Hooks dans `risk_backbone/` : EXTREME → exit toutes positions + plus d'entries 24h

**Invariants** :
- Seuils chargés depuis calibration artefact
- Pas de skip d'état (un passage CALM → EXTREME passe par STRESSED si lent, ou direct si event soudain avec trace explicite)

**Critères d'acceptation** :
- [ ] Replay sur mars 2020, mai 2021, novembre 2022 : état EXTREME détecté en < 2h après le début du crash
- [ ] Replay sur sideways 2024 : état CALM dominant
- [ ] Hooks dans `risk_backbone/exposure_budgeter/` actifs

**LOC estimées** : 400-600

---

### Tranche T10 — P1-2 + P1-3 : Reconciliation périodique + Daily P&L breaker

## 47. Regime lite typed core now exists

- `src/regime_classifier/regime_lite.py` now exists with typed `CALM / STRESSED / EXTREME` state, explicit thresholds, hysteresis, cooldown, and transition trace.
- The first cut stays intentionally bounded:
  - no hidden runtime activation
  - no direct engine wiring
  - no bypass of Shadow / Micro-live / Live gates
- The helper is now registered in the manifest/DAG as `regime_classifier`, so `src/regime_classifier/` is no longer a phantom package.
- Remaining work for T9 stays explicit:
  - threshold loading from real calibration artifacts
  - provider/runtime/risk hooks
  - replay proof on stress windows

## 48. First governed risk consumer for `regime_lite` now exists

- `src/risk_backbone/regime_lite_entry_gate.py` now exists as the first opt-in risk consumer built from `RegimeLiteAssessment`.
- `src/risk_backbone/risk_runtime.py` now exposes a typed `regime_precheck_hook`, following the same governance pattern as the existing micro-friction hook:
  - opt-in only
  - fail-open by default
  - no hidden live activation
- The first bounded behavior is intentionally narrow:
  - block new entries while `EXTREME` or while `EXTREME` cooldown is still active
  - no automatic exit-all wiring yet
  - no direct engine-specific regime veto yet

**Objectif** — Forcer une reconciliation au boot et toutes les 60 min. Câbler le daily P&L breaker au kill switch existant.

**Périmètre** :
- Schedule task `reconciliation_scheduler.py` (boot + 60 min)
- `daily_pnl_breaker.py` qui consomme l'équity tracker existant
- Seuils dynamiques : −2 % intraday → SHADOW automatique, −10 % week → kill switch (à calibrer)

**Critères d'acceptation** :
- [ ] Reconciliation au boot bloque le trading si divergence
- [ ] Daily breaker SHADOW automatique en cas de DD intraday > seuil
- [ ] Pas de réactivation automatique le jour même

**LOC estimées** : 300-500

---

### Tranche T11 — P1-4 + P1-5 : Telegram alerter + Disk monitor + Log rotation

**Objectif** — Push notifications pour les events critiques + monitoring disque + rotation logs.

**Périmètre** :
- `src/alerting/telegram_alerter.py` : send via bot token (sealed)
- `src/monitoring/disk_monitor.py` : check free space, alerte à 70 % et 90 %
- `src/monitoring/log_rotation.py` : gzip + retention 90j

**Critères d'acceptation** :
- [ ] Alerte Telegram reçue end-to-end pour un kill switch
- [ ] Disque monitor alerte au seuil
- [ ] Logs rotated et compressés

**LOC estimées** : 400-600

---

## 4. Phase 2 — Tranches V37 bricks (à incorporer en simplifié)

### Tranche T12 — V37-2 : Execution Gatekeeper central wrapper

**Objectif** — Wrapper non-destructif `authorize()` qui chaîne les guards V5.3 existants en une décision unique auditable.

**Périmètre** :
- `src/execution_backbone/gatekeeper/gatekeeper.py`
- `GateChain` qui itère sur les guards existants (sharia, fee_edge, regime, btc_factor, exposure, kill_switch, freshness, ...)
- `ExecutionPermit` ou `ExecutionRefusal` en sortie, avec trace de tous les gates traversés
- Le code existant continue de fonctionner — le gatekeeper est un point de convergence, pas un remplaçant

**Invariants** :
- Non-destructif : aucun guard existant n'est supprimé
- Audit trail : chaque permit/refusal logge les N gates traversés et leur verdict

**Critères d'acceptation** :
- [ ] Toutes les décisions de trade passent par `gatekeeper.authorize()`
- [ ] Trace audit complète dans `artifacts/gatekeeper/`
- [ ] Aucune régression : tests verts

**LOC estimées** : 400-700

---

### Tranche T13 — V37-3 : Information Stress Monitor (lite)

**Objectif** — Détecteur "le marché ment" en temps réel, 5 indicateurs simples, veto sur entries en cas de stress information.

**Périmètre** :
- `src/risk_backbone/info_stress_monitor.py`
- Indicateurs : spread bid-ask explosion, depth ratio collapse, order cancellation rate spike, taker imbalance saturation, micro-vol divergence
- Sortie : `InfoStressLevel` (NORMAL / ELEVATED / EXTREME)
- Hook : EXTREME → veto entries pendant cooldown

**Critères d'acceptation** :
- [ ] Replay sur les 3 windows de capitulation : ELEVATED ou EXTREME détecté
- [ ] Replay sur sideways : NORMAL dominant
- [ ] Veto fonctionnel

**LOC estimées** : 400-600

---

## 5. Tableau de synthèse — toutes les tranches

| # | Tranche | Phase | Nature | LOC | Bloque quoi si fail |
|---|---|---|---|---|---|
| T1 | P0-1.A REST + time sync | 1 | P0 | 600-900 | Tout |
| T2 | P0-4 sealed secrets | 1 | P0 | 200-400 | T1 |
| T3 | P0-1.B WS + gap recovery | 1 | P0 | 700-1000 | Live trading |
| T4 | P0-1.C Order translator | 1 | P0 | 800-1200 | Live trading |
| T5 | P0-2 Halal compliance | 1 | P0 | 800-1200 | Halal compliance |
| T6 | P0-3 Fee-aware edge gate | 1 | P0 | 150-300 | Profitabilité |
| T7 | P0-5.A Engine C feature flag | 1 | P0 | 50-100 | Risk MICRO_LIVE |
| T8 | P0-5.B Engine D feature flag | 1 | P0 | 50-100 | Risk MICRO_LIVE |
| T9 | P1-1 Regime lite | 1bis | P1 | 400-600 | Phase 4 LIVE |
| T10 | P1-2 + P1-3 Recon + Daily breaker | 1bis | P1 | 300-500 | Phase 4 LIVE |
| T11 | P1-4 + P1-5 Telegram + Disk | 1bis | P1 | 400-600 | Phase 4 LIVE |
| T12 | V37-2 Gatekeeper central | 2 | Optionnel | 400-700 | Audit / robustesse |
| T13 | V37-3 Info stress monitor | 2 | Optionnel | 400-600 | Phase 4 LIVE |
| **Total** | | | | **5250-8200** | |

**13 tranches** au total. Si on regroupe T7+T8 et T10+T11 et T12+T13 : **10 tranches effectives**.

---

## 5bis. Latest bounded bridge semantics

- the current Local IA Lab source artifact remains the calibration artifact `edge_gate.yml`
- the current dry-run transport artifact still remains the governed replay-derived `review_packet`
- `scripts/run_local_lab_analysis_bundle.py` now also emits `artifact_source_summary.json`
- this new sidecar exposes a stable future-dashboard summary of the real source artifact:
  - `artifact_id`
  - `artifact_family`
  - `schema_version`
  - `version`
  - `threshold_count`
- the dry-run transport packet now carries both:
  - the source artifact ref
  - the `artifact_source_summary.json` ref
  - via `ArtifactPayloadRefBundle.supplementary_refs`
- `src/local_replay_runtime/artifact_upload_bridge_candidate.py` now reports this explicitly as:
  - `semantic_status = transport_packet_with_source_artifact_refs`
- important invariant:
  - do not invent a new artifact kind or a parallel import rail for this slice

## 5ter. Latest bounded recalibration planning slice

- the Local IA Lab bundle now also emits `local_lab_recalibration_plan.json`
- this sidecar is the first bounded answer to:
  - what should be recalibrated locally from governed loss evidence
  - what must stay blocked before any new artifact is exported toward the VPS rail
- current inputs:
  - `trade_loss_attribution.json`
  - optional `local_lab_scope_matrix.json`
- current outputs:
  - `recommended_threshold_ids`
  - `calibration_candidate_ready`
  - `blocking_reasons`
  - typed recalibration actions such as:
    - `recalibrate_edge_gate`
    - `review_scope_sterilization`
    - `improve_trace_capture`
- important invariant:
  - this slice still plans recalibration locally; it does not mutate runtime or bypass the governed export/import rail

## 5quater. Latest bounded EDGE provenance slice

- `scripts/run_edge_gate_calibration.py` now accepts an optional `--recalibration-plan-path`
- `edge_gate.input_summary.json` can now carry:
  - `recalibration_plan_ref`
  - `recalibration_candidate_ready`
  - `recalibration_blocking_reasons`
  - `recalibration_recommended_threshold_ids`
- `scripts/run_local_lab_analysis_bundle.py` now builds the Local IA Lab recalibration plan first, then runs EDGE calibration with that plan attached
- important invariant:
  - this only enriches audit/provenance of the Local IA Lab artifact producer
  - it does not alter the governed VPS import rail or runtime mode semantics

## 5quinquies. Latest bounded packaging gate refinement

- `src/local_replay_runtime/artifact_release_candidate.py` now consumes the Local IA Lab recalibration plan explicitly
- a release candidate now requires:
  - `local_lab_recalibration_plan_path`
  - recalibration blockers that are coherent with the intended export
- current conservative rule:
  - `NO_LOSING_TRADES_TO_RECALIBRATE` is treated as benign
  - other recalibration blockers remain release blockers
- important invariant:
  - `shadow_candidate` can no longer emerge from proof sidecars alone without a coherent local recalibration plan

## 5sexies. Latest bounded release-gate projection refinement

- `src/local_replay_runtime/artifact_upload_bridge_candidate.py` now exposes the packaging verdict explicitly instead of forcing future tooling to re-derive it from multiple sidecars
- the dry-run bridge now carries:
  - `release_ready_for_shadow`
  - `release_artifact_proof_ready`
  - `release_artifact_proof_validation_reasons`
  - `release_recalibration_candidate_ready`
  - `release_recalibration_blocking_reasons`
  - `release_gate_status`
  - `release_gate_reasons`
- `scripts/run_local_lab_analysis_bundle.py` now forwards the same release-gate projection into `local_lab_analysis_summary.json`
- current bounded statuses:
  - `proof_and_recalibration_backed`
  - `proof_backed_no_recalibration_required`
  - `proof_gate_blocked`
  - `recalibration_gate_blocked`
  - `release_candidate_blocked`
- important invariant:
  - the handoff remains dry-run only
  - the projection must stay fail-close and must reflect the full proof blocker set, not a truncated reason list

## 5septies. Latest bounded release-gate sidecar transport refinement

- `scripts/run_local_lab_analysis_bundle.py` now emits `artifact_release_gate_summary.json`
- `src/local_replay_runtime/artifact_upload_bridge_candidate.py` now requires `release_gate_summary_ref` for a fully governed dry-run handoff
- the dry-run transport packet now carries, in `supplementary_refs`:
  - the source artifact ref
  - the source artifact summary ref
  - the release-gate summary ref
- important invariant:
  - the existing governed import rail is preserved
  - the transport packet becomes more audit-complete without inventing a new artifact kind or mutating VPS behavior

## 5octies. Latest bounded multi-scope release drill-down refinement

- `src/local_replay_runtime/artifact_release_candidate.py` now carries richer per-scope release rows
- each release scope now preserves drill-down refs already known to the Local IA Lab:
  - `review_bundle_path`
  - `trade_loss_attribution_path`
  - `artifact_proof_summary_path`
  - `artifact_proof_assessment_path`
  - `executed_records`
  - `losing_trade_count`
- `scripts/run_local_lab_analysis_bundle.py` now also exposes:
  - `release_ready_scope_slugs`
  - `release_blocked_scope_slugs`
- important invariant:
  - this is still a projection-only refinement
  - it improves future dashboard and operator drill-down without creating per-scope VPS mutation semantics

## 5novies. Latest bounded per-scope release-sidecar refinement

- `scripts/run_local_lab_analysis_bundle.py` now emits `artifact_release_scope_summary.json` under each `scopes/<slug>/` directory when multi-scope review is active
- each scope sidecar links:
  - the shared artifact path
  - the shared release-gate summary
  - the shared dry-run bridge
  - the scope-specific proof/review sidecars
- the top-level summary now also exposes:
  - `release_scope_summary_count`
  - `release_scope_summary_paths`
- important invariant:
  - these scope sidecars remain descriptive packaging/handoff views
  - they do not imply a separate per-scope upload or import protocol

## 5decies. Latest bounded scope-matrix packaging projection

- `src/local_replay_runtime/local_lab_scope_matrix.py` now distinguishes:
  - proof-ready scope counts
  - release-ready scope counts
- each `LocalLabScopeAnalysisRow` can now carry:
  - `release_ready`
  - `release_blocking_reasons`
  - `release_scope_summary_path`
- `scripts/run_local_lab_analysis_bundle.py` now rewrites `local_lab_scope_matrix.json` after packaging so the matrix reflects the later release-side truth, not only the earlier proof-side truth
- the top-level summary now also exposes:
  - `release_scope_ready_count`
  - `release_scope_blocked_count`
- important invariant:
  - the scope matrix remains descriptive and typed
  - no new per-scope import rail is introduced by this refinement

## 5undecies. Latest bounded promotion-readiness projection

- `src/local_replay_runtime/local_lab_promotion_readiness.py` now translates the Local IA Lab packaging/dry-run truth into canonical promotion vocabulary
- `scripts/run_local_lab_analysis_bundle.py` now emits `artifact_promotion_readiness_summary.json`
- this summary uses shared-core canonical values instead of inventing new labels:
  - `ArtifactActivationStage`
  - `PromotionState`
  - `ReviewState`
- current bounded readiness statuses:
  - `local_only`
  - `shadow_candidate_pending_dry_run`
  - `shadow_candidate_dry_run_ready`
- important invariant:
  - this remains descriptive packaging state only
  - no auto-promotion or live VPS mutation is introduced by this summary

## 5terdecies. Latest bounded Local IA Lab monitoring projection

- `src/local_replay_runtime/local_lab_monitoring_projection.py` now emits one compact future-dashboard-ready projection over the real Local IA Lab packaging rail
- `scripts/run_local_lab_analysis_bundle.py` now writes `local_lab_monitoring_projection.json`
- `local_lab_analysis_summary.json` now also exposes:
  - `local_lab_monitoring_projection_path`
  - `monitoring_projection_status`
  - `monitoring_projection_detail`
- this projection normalizes:
  - core Local IA Lab readiness (`review / trade_loss / walk_forward / ablation / proof / edge`)
  - packaging/handoff truth (`release_status`, `bridge_status`, `release_gate_status`, `semantic_status`)
  - canonical promotion truth already projected by `artifact_promotion_readiness_summary.json`
  - scope and release counts for future Local IA Lab dashboards
- bounded status mapping:
  - `healthy` only when the dry-run handoff is ready
  - `critical` only when core Local IA Lab outputs are incomplete
  - otherwise `warning/info` as descriptive audit state
- important invariant:
  - this is still projection only
  - no UI rail, no new runtime rail, and no promotion behavior are introduced

## 5quaterdecies. Latest bounded Local IA Lab observability export

- `src/local_replay_runtime/local_lab_observability.py` now emits a standard `ObservabilityExport` over the compact Local IA Lab monitoring projection
- `scripts/run_local_lab_analysis_bundle.py` now writes `local_lab_observability_export.json`
- the top-level summary now also exposes:
  - `local_lab_observability_export_path`
  - `local_lab_observability_sample_count`
- current export content:
  - stable metric samples for review/proof/recalibration/release/dry-run truth
  - scope and release counts
  - Prometheus-like `text_payload` for later monitoring ingestion
- important invariant:
  - this remains local, descriptive, and non-UI
  - it does not change any runtime or promotion semantics

## 5quindecies. Latest bounded Local IA Lab monitoring backend payload

- `src/local_replay_runtime/local_lab_monitoring_backend.py` now adapts the Local IA Lab monitoring projection plus the standard observability export into one backend-consumable typed payload
- `src/monitoring/contracts.py` now defines `LocalLabMonitoringBackendPayload`
- `scripts/run_local_lab_analysis_bundle.py` now writes `local_lab_monitoring_backend_payload.json`
- the top-level summary now also exposes:
  - `local_lab_monitoring_backend_payload_path`
  - `local_lab_monitoring_backend_status`
- current payload content is intentionally descriptive only:
  - normalized run/export/artifact identifiers
  - current review/proof/recalibration/release/dry-run truth
  - scope and release counts
  - refs back to the detailed sidecars and the observability export
- important invariant:
  - this is a future monitoring/backend surface only
  - it does not introduce a new runtime rail
  - it does not introduce UI coupling
  - it does not mutate VPS state or promotion behavior

## 5sexdecies. Latest bounded Local IA Lab monitoring ingestion summary

- `src/monitoring/local_lab_ingestion.py` now exists as the monitoring-side ingestion adapter for the Local IA Lab pair:
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- `src/monitoring/contracts.py` now defines `LocalLabMonitoringIngestionSummary`
- `scripts/run_local_lab_analysis_bundle.py` now writes `local_lab_monitoring_ingestion_summary.json`
- the top-level summary now also exposes:
  - `local_lab_monitoring_ingestion_summary_path`
  - `local_lab_monitoring_ingestion_ready`
- current builder behavior:
  - validates `correlation_id`
  - validates `profile`
  - validates `runtime_mode`
  - validates `timestamp_ms`
  - computes an ingestion-ready boolean plus a short detail
- important invariant:
  - this is still descriptive-only Local IA Lab plumbing
  - it does not create Build-10 runtime coupling
  - it does not create UI semantics
  - it does not modify promotion or VPS behavior

## 5septdecies. Latest bounded Local IA Lab monitoring bundle loader

- `src/monitoring/local_lab_bundle_loader.py` now exists as the file-based loader for the Local IA Lab monitoring trio:
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
  - `local_lab_monitoring_ingestion_summary.json`
- it returns a typed `LocalLabMonitoringBundle`
- current loader checks remain bounded:
  - all three files exist
  - all three files validate against typed contracts
  - `correlation_id/profile/runtime_mode/timestamp_ms` stay aligned across the trio
- important invariant:
  - this is still local, descriptive, future-backend plumbing only
  - it does not create Build-10 runtime coupling
  - it does not create new promotion or VPS behavior

## 5octodecies. Latest bounded Local IA Lab observability text export

- `src/monitoring/observability_io.py` now exists as a generic writer for persisted `ObservabilityExport.text_payload`
- `scripts/run_local_lab_analysis_bundle.py` now also writes `local_lab_observability.prom`
- the top-level bundle summary now also exposes:
  - `local_lab_observability_text_path`
- current behavior:
  - writes the exact `text_payload`
  - appends one trailing newline
  - stays generic, not Local-Lab-specific in implementation
- important invariant:
  - this remains descriptive export plumbing only
  - it does not introduce UI coupling
  - it does not introduce Prometheus runtime semantics by itself
  - it does not alter VPS behavior or promotion logic

## 6. Estimation effort agent codeur

**Hypothèse session agent codeur** : 1 session = 1500-2500 LOC, ~2-4 heures de coding focalisé, doit produire un état mergeable.

| Tranche | Sessions estimées |
|---|---|
| T1 | 0.5 |
| T2 | 0.25 |
| T3 | 0.75 |
| T4 | 0.5 |
| T5 | 0.75 |
| T6 | 0.25 |
| T7+T8 | 0.25 |
| T9 | 0.5 |
| T10 | 0.5 |
| T11 | 0.5 |
| T12 | 0.5 |
| T13 | 0.5 |
| **Total estimé** | **6 sessions code mergeables** |

**Avec marge pour debug, tests, integration testnet** : **8-12 sessions code agent**.

> **Important** : ces sessions sont des **sessions de l'agent codeur Sonnet**, pas des sessions Opus. Opus produit les MD (= ce qu'on est en train de faire). Le ratio attendu est ~1 session Opus pour ~3 sessions code agent.

---

## 7. Ordre de réalisation recommandé

```
T2 (sealed secrets) → bloquant pour T1
↓
T1 (REST + time sync) → bloquant pour T3, T4
↓
T6 (fee gate) → indépendant, peut être fait en parallèle
T7+T8 (engine feature flags) → indépendant, peut être fait en parallèle
↓
T3 (WS + gap) → bloquant pour T4
↓
T4 (Order translator) → bloquant pour le go-live MICRO_LIVE
↓
T5 (Halal compliance) → bloquant pour le go-live MICRO_LIVE
↓
═══ Fin Phase 1 (P0). LOCAL_REPLAY validé. Gate G1 humain. ═══
↓
T9 (Regime lite)
↓
T10 (Recon + Daily breaker)
↓
T11 (Telegram + Disk)
↓
═══ Fin Phase 1bis (P1). Prêt pour SHADOW. ═══
↓
T12 (Gatekeeper central) ← optionnel mais recommandé avant SHADOW
↓
T13 (Info stress monitor) ← optionnel mais recommandé avant SHADOW
↓
═══ Phase 2 (SHADOW) commence sur le VPS. ═══
```

---

## 8. Conditions pour qu'une tranche soit mergeable

Chaque tranche, à la fin :
1. **Tous les tests existants verts** (1026 + nouveaux tests de la tranche)
2. **Coverage des nouveaux fichiers ≥ 80 %**
3. **Aucun seuil hardcodé** (audit grep à faire)
4. **Aucun secret dans le repo** (audit grep avec `git diff`)
5. **Documentation à jour** : README du module modifié si pertinent
6. **Tracker mis à jour** : `2026-04-07_V53_MASTER_DEVELOPMENT_TRACKER.md`
7. **Mémoire mise à jour** si nouvelle convention introduite

Si un de ces critères échoue → la tranche n'est pas mergeable, on continue sur la même branche jusqu'à ce que ça passe.

---

**Suite logique** : `10_DECISIONS_REQUIRED.md` — décisions à prendre par l'humain avant de démarrer.
## 5novodecies. Latest bounded Local IA Lab research-priority scorer

- `src/local_replay_runtime/local_lab_research_priority.py` now exists as the first bounded research-model-style component inside the Local IA Lab core
- it remains intentionally transparent:
  - `model_family=interpretable_priority_model_v1`
  - `model_kind=transparent_weighted_score`
  - no hidden training
  - no runtime coupling
- current inputs:
  - `trade_loss_attribution` sidecars
  - `scope_matrix` when present
  - current proof/release readiness
- current outputs:
  - `local_lab_research_priority.json`
  - summary fields on `local_lab_analysis_summary.json`
  - compact propagation into the Local IA Lab monitoring projection/backend/observability surfaces
- current ranking intent:
  - identify which `pair x engine` scope should get the next replay/recalibration cycle
  - keep trace-quality problems separate from true recalibration candidates
- important invariant:
  - local-only
  - descriptive and audit-ready
  - no VPS mutation
  - no promotion semantics by itself

## 5vicies. Latest bounded Local IA Lab loss-surrogate scorer

- `src/local_replay_runtime/local_lab_loss_surrogate.py` now exists as the first truly trained but still transparent Local IA Lab component
- the model remains strictly bounded:
  - `model_family=transparent_linear_loss_surrogate_v1`
  - `model_kind=diagonal_lda_linear_score`
  - local-only
  - no runtime/VPS coupling
- training inputs are decision-time / no-lookahead only:
  - `raw_score`
  - `penalized_score`
  - `final_score`
  - `expected_cost`
  - `ce_expected`
  - `candidate_size`
  - `final_size`
  - `ranking_position`
- current outputs:
  - `local_lab_loss_surrogate_report.json`
  - summary fields on `local_lab_analysis_summary.json`
  - compact propagation into the Local IA Lab monitoring projection/backend/observability surfaces
- current role:
  - estimate which scopes show the highest modeled loss pressure
  - stay research-only and audit-ready
  - never mutate VPS runtime or promotion semantics directly

## 5unvicies. Latest bounded Local IA Lab surrogate-guided prioritization

- the trained Local IA Lab loss surrogate is now consumed by:
  - `src/local_replay_runtime/local_lab_research_priority.py`
  - `src/local_replay_runtime/local_lab_recalibration_plan.py`
- bounded consequences only:
  - influence research ranking for the next replay cycle
  - add a local `replay_surrogate_high_risk_scope` action when justified
  - keep recalibration/publication gates unchanged
- important invariant:
  - the surrogate remains advisory only
  - no promotion authority
  - no runtime/VPS mutation
  - no bypass of proof/recalibration/release gates

## 5duovicies. Latest bounded Local IA Lab replay candidate queue

- `src/local_replay_runtime/local_lab_replay_candidate_queue.py` now exists as the first bounded queue of next local replay/research steps
- the queue is built from:
  - `local_lab_research_priority`
  - `local_lab_recalibration_plan`
  - current surrogate-guided planning truth
- current outputs:
  - `local_lab_replay_candidate_queue.json`
  - summary fields on `local_lab_analysis_summary.json`
  - compact propagation into the Local IA Lab monitoring projection/backend/observability surfaces
- important invariant:
  - local-only
  - descriptive and audit-ready
  - no VPS mutation
  - no promotion semantics by itself

## 5tervicies. Latest bounded Local IA Lab replay ticket index

- `src/local_replay_runtime/local_lab_replay_ticket_index.py` now exists as the governed ticket index over the Local IA Lab replay queue
- it reuses the canonical `LocalReplayRequest` contract instead of inventing a parallel runtime request type
- current outputs:
  - `local_lab_replay_ticket_index.json`
  - summary fields on `local_lab_analysis_summary.json`
  - compact propagation into the Local IA Lab monitoring projection/backend/observability surfaces
- important invariant:
  - tickets are local-only planning artifacts
  - they do not execute anything by themselves
  - they do not mutate VPS/runtime or promotion state

## 5quattuorvicies. Latest bounded Local IA Lab replay dispatch plan

- `src/local_replay_runtime/local_lab_replay_dispatch_plan.py` now exists as the local-only dispatch surface over governed replay tickets
- current outputs:
  - `local_lab_replay_dispatch_plan.json`
  - summary fields on `local_lab_analysis_summary.json`
  - compact propagation into the Local IA Lab monitoring projection/backend/observability surfaces
- important invariant:
  - dispatch stays local-only
  - it does not execute tickets
  - it does not mutate VPS/runtime or promotion state

## 5quinvicies. Latest bounded Local IA Lab replay workflow + monitoring bundle manifests

- `src/local_replay_runtime/local_lab_replay_workflow_manifest.py` now exists as the typed manifest over:
  - `local_lab_replay_candidate_queue.json`
  - `local_lab_replay_ticket_index.json`
  - `local_lab_replay_dispatch_plan.json`
- `src/monitoring/local_lab_replay_workflow_loader.py` now exists as the file-based loader for that workflow bundle
- `src/monitoring/local_lab_monitoring_bundle_manifest.py` now exists as the typed manifest over:
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
  - `local_lab_monitoring_ingestion_summary.json`
  - optional `local_lab_replay_workflow_manifest.json`
- `src/monitoring/local_lab_bundle_loader.py` now discovers monitoring sidecars through the manifest instead of hardcoded filenames
- future-dashboard propagation is now explicit:
  - `local_lab_monitoring_bundle_manifest.json`
  - `local_lab_replay_workflow_manifest.json`
  - compact refs in monitoring projection/backend/summary
- important invariant:
  - local-only discovery surface
  - no UI coupling
  - no VPS/runtime mutation
  - no promotion authority by itself

## 5sexvicies. Latest bounded Local IA Lab monitoring bundle discovery

- `src/monitoring/local_lab_bundle_discovery.py` now exists as the manifest-driven discovery layer for Local IA Lab monitoring bundles
- it can now:
  - scan a root for `local_lab_monitoring_bundle_manifest.json`
  - sort bundles by latest `timestamp_ms`
  - load the newest bundle through the existing loader
- purpose:
  - prepare future backend/Prometheus/dashboard ingestion over multiple Local IA Lab outputs
  - keep discovery manifest-first instead of hardcoded directory knowledge
- important invariant:
  - descriptive only
  - no UI coupling
  - no VPS/runtime mutation
  - no promotion authority

## 5septemvicies. Latest bounded Local IA Lab monitoring feed

- `src/monitoring/local_lab_monitoring_feed.py` now exists as the compact feed over discovered Local IA Lab monitoring bundles
- it now summarizes:
  - latest bundle identity/status
  - ingestion-ready bundle count
  - bundle counts by backend status
- purpose:
  - prepare future backend/dashboard ingestion over multiple Local IA Lab bundles
  - keep the first multi-bundle surface compact and audit-ready
- important invariant:
  - descriptive only
  - no UI coupling
  - no VPS/runtime mutation
  - no promotion authority

## 5octovicies. Latest bounded Local IA Lab calibration-methods core (`13-A`)

- `src/calibration_methods/` now exists as the first shared Local IA Lab math-core package
- bounded modules landed:
  - `bootstrap.py`
  - `walkforward.py`
  - `dsr.py`
- current scope is intentionally local-only and pure:
  - stationary block bootstrap confidence intervals
  - purged walk-forward fold planning with embargo and label purging
  - Deflated Sharpe Ratio computation
- current proofs landed:
  - `tests/test_calibration_methods/test_bootstrap.py`
  - `tests/test_calibration_methods/test_walkforward.py`
  - `tests/test_calibration_methods/test_dsr.py`
- the first live consumer is now real:
  - `src/local_replay_runtime/edge_gate_calibration.py` now consumes the shared stationary bootstrap helper instead of a private i.i.d. resample helper
  - EDGE calibration notes now expose the effective bootstrap block length for auditability
- important invariant:
  - this slice stays Local IA Lab only
  - no VPS/runtime promotion behavior changes
  - walk-forward human approval remains a separate hard gate
  - DSR and walk-forward helpers are available for later consumers but are not silently wired into promotion logic yet

## 5novemvicies. Latest bounded Local IA Lab calibration-methods review sidecar

- `src/local_replay_runtime/local_lab_calibration_methods_review.py` now exists as the first Local IA Lab proof-side consumer of:
  - `src/calibration_methods/walkforward.py`
  - `src/calibration_methods/dsr.py`
- the Local IA Lab bundle now emits:
  - `local_lab_calibration_methods_review.json`
  - summary fields on `local_lab_analysis_summary.json`
  - compact propagation into:
    - `local_lab_monitoring_projection.json`
    - `local_lab_monitoring_backend_payload.json`
    - `local_lab_observability_export.json`
- current semantics are conservative:
  - valid DSR below floor blocks Local IA Lab proof locally
  - insufficient history stays explicit as `partial`, never silent
  - human walk-forward approval remains a separate gate from auto-generated walk-forward geometry
- current proofs landed:
  - `tests/test_local_replay_runtime/test_local_lab_calibration_methods_review.py`
  - `tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py`
  - `tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py`
- latest proofs:
  - `rtk pytest tests/test_local_replay_runtime/test_local_lab_calibration_methods_review.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_scope_matrix.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_local_lab_recalibration_plan.py tests/test_local_replay_runtime/test_local_lab_research_priority.py -q`
  - `25 passed`
  - `rtk pytest tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_observability.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_monitoring/test_monitoring_contracts.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `18 passed`
  - `rtk pytest tests/test_calibration_methods/test_bootstrap.py tests/test_calibration_methods/test_walkforward.py tests/test_calibration_methods/test_dsr.py tests/test_local_replay_runtime/test_edge_gate_calibration.py tests/test_local_replay_runtime/test_walk_forward_review.py tests/test_local_replay_runtime/test_artifact_ablation_study.py tests/test_local_replay_runtime/test_local_lab_calibration_methods_review.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_scoring_backbone/test_fee_aware_edge_gate.py tests/test_calibration_loader/test_contracts.py tests/test_calibration_loader/test_loader.py -q`
  - `37 passed`
  - `rtk pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `314 passed`

## 5tricies. Latest bounded Local IA Lab release/dry-run calibration-methods propagation

- `src/local_replay_runtime/artifact_release_candidate.py` now carries explicit calibration-methods state on the Local IA Lab release verdict:
  - `local_lab_calibration_methods_review_path`
  - `calibration_methods_review_status`
  - `calibration_methods_review_ready`
  - `calibration_methods_dsr_pass`
  - `calibration_methods_walk_forward_plan_ready`
- `src/local_replay_runtime/artifact_upload_bridge_candidate.py` now propagates the same truth into:
  - `artifact_release_gate_summary.json`
  - `artifact_import_dry_run_bridge.json`
- purpose:
  - make the dry-run handoff explicitly `calibration-methods-backed` or not
  - keep the handoff audit-ready without changing any VPS/runtime semantics
- latest proofs:
  - `rtk pytest tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_calibration_methods_review.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py -q`
  - `20 passed`
  - `rtk pytest tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_calibration_methods_review.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py tests/test_monitoring/test_monitoring_contracts.py -q`
  - `111 passed`

## 5untricies. Latest bounded Local IA Lab monitoring manifest/discovery/feed calibration-methods propagation

- `src/monitoring/local_lab_monitoring_bundle_manifest.py` now carries compact calibration-methods truth from the backend payload
- `src/monitoring/local_lab_bundle_discovery.py` now exposes the same fields per discovered bundle
- `src/monitoring/local_lab_monitoring_feed.py` now summarizes:
  - `calibration_ready_bundle_count`
  - `calibration_partial_bundle_count`
  - `calibration_blocked_bundle_count`
- purpose:
  - keep future multi-bundle backend ingestion manifest-first
  - make calibration-method readiness visible without opening every bundle manually
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_local_lab_monitoring_bundle_manifest.py tests/test_monitoring/test_local_lab_bundle_discovery.py tests/test_monitoring/test_local_lab_monitoring_feed.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py -q`
  - `18 passed`
  - `rtk pytest tests/test_monitoring tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_artifact_upload_bridge_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_calibration_methods_review.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py -q`
  - `203 passed`

## 5duotricies. Latest bounded Local IA Lab tail-risk review (`13-B`)

- `src/calibration_methods/pot_gpd.py` now exists as the bounded Local IA Lab POT-GPD helper:
  - method version stays explicit as `pot_gpd_mom_bootstrap_v1`
  - current scope is bounded to empirical-threshold POT-GPD + bootstrap CI, not a full opaque EVT stack
- `src/local_replay_runtime/local_lab_tail_risk_review.py` now exists as the first strategy-level tail-risk consumer of exported `DTRRecord` history
- `scripts/run_local_lab_analysis_bundle.py` now emits `local_lab_tail_risk_review.json`
- current breaker scope is intentionally top-level and local-only:
  - `THR-R01` over daily net-loss buckets
  - `THR-R02` over weekly net-loss buckets
  - `THR-R03` over monthly net-loss buckets
- current conservative semantics:
  - no positive-loss periods -> `partial`
  - insufficient exceedances -> `partial`
  - invalid fit or excessive bootstrap dispersion -> `blocked`
  - review becomes `ready` only when all three breakers are ready
- compact future-dashboard/backend truth now also propagates into:
  - `local_lab_analysis_summary.json`
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- important invariant:
  - still Local IA Lab only
  - still no UI coupling
  - still no VPS/runtime mutation
  - not yet part of release gating or dry-run import semantics
- latest proofs:
  - `rtk pytest tests/test_calibration_methods/test_pot_gpd.py tests/test_local_replay_runtime/test_local_lab_tail_risk_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py -q`
  - `16 passed`
  - `rtk pytest tests/test_calibration_methods tests/test_local_replay_runtime/test_local_lab_calibration_methods_review.py tests/test_local_replay_runtime/test_local_lab_tail_risk_review.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py -q`
  - `32 passed`
  - `rtk pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `317 passed`

## 5tertricies. Latest bounded Local IA Lab stationarity gate (`MI-9` extension over `13-A/13-E`)

- `src/calibration_methods/stationarity.py` now exists as the bounded dual stationarity helper:
  - ADF level test with intercept
  - KPSS level stationarity test with Bartlett/Newey-West long-run variance
  - explicit audit-ready dual verdict `passes_dual_test`
- `src/local_replay_runtime/local_lab_calibration_methods_review.py` now consumes this helper over executed replay returns:
  - `stationarity_status`
  - `stationarity_ready`
  - `stationarity_pass`
  - `stationarity_result`
- new conservative semantics:
  - insufficient history stays explicit as `partial`
  - failing MI-9 blocks the Local IA Lab calibration-methods review
  - proof-side propagation now emits:
    - `LOCAL_LAB_STATIONARITY_REQUIRED`
    - `LOCAL_LAB_STATIONARITY_INVALID`
- the same truth now also propagates into:
  - `local_lab_calibration_normalized_report.json`
  - `local_lab_analysis_summary.json`
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
- important invariant:
  - still Local IA Lab only
  - still no UI coupling
  - still no VPS/runtime mutation
  - dry-run/release semantics remain descriptive; this slice only hardens the local proof rail
- latest proofs:
  - `rtk pytest tests/test_calibration_methods/test_stationarity.py tests/test_local_replay_runtime/test_local_lab_calibration_methods_review.py tests/test_local_replay_runtime/test_local_lab_calibration_normalized_report.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `23 passed`
  - `rtk pytest tests/test_calibration_methods tests/test_local_replay_runtime/test_local_lab_calibration_methods_review.py tests/test_local_replay_runtime/test_local_lab_tail_risk_review.py tests/test_local_replay_runtime/test_local_lab_calibration_normalized_report.py tests/test_local_replay_runtime/test_edge_gate_calibration.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py -q`
  - `42 passed`
  - `rtk pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `320 passed`

## 5quatertricies. Latest bounded shared human hard-cap helper (`MI-7` clarification)

- `src/calibration_methods/hard_cap_floor.py` now exists as the shared Local IA Lab hard-bound publication helper:
  - `apply_human_minimum_floor(...)`
  - `apply_human_maximum_cap(...)`
- purpose:
  - stop duplicating ad hoc floor/cap publication logic across EDGE and RISK slices
  - make the semantics explicit:
    - `hard_cap_satisfied` = published value respects the human bound
    - `hard_cap_binding` = the human bound actually clipped/floored the raw candidate
- current consumers:
  - `src/local_replay_runtime/edge_gate_calibration.py`
  - `src/local_replay_runtime/local_lab_tail_risk_review.py`
  - `src/local_replay_runtime/local_lab_calibration_normalized_report.py`
- important invariant:
  - still Local IA Lab only
  - still no UI coupling
  - still no VPS/runtime mutation
  - this slice clarifies audit semantics; it does not open a new promotion authority
- latest proofs:
  - `rtk pytest tests/test_calibration_methods/test_hard_cap_floor.py tests/test_local_replay_runtime/test_edge_gate_calibration.py tests/test_local_replay_runtime/test_local_lab_tail_risk_review.py tests/test_local_replay_runtime/test_local_lab_calibration_normalized_report.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `16 passed`
  - `rtk pytest tests/test_calibration_methods tests/test_local_replay_runtime/test_local_lab_calibration_methods_review.py tests/test_local_replay_runtime/test_local_lab_tail_risk_review.py tests/test_local_replay_runtime/test_local_lab_calibration_normalized_report.py tests/test_local_replay_runtime/test_edge_gate_calibration.py tests/test_local_replay_runtime/test_edge_gate_calibration_launcher.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py -q`
  - `44 passed`
  - `rtk pytest tests/test_local_replay_runtime tests/test_meta_learning tests/test_meta_minimal -q`
  - `320 passed`

## 5quinquatracies. Latest bounded Local IA Lab multiple-testing review (`MI-12`)

- `src/calibration_methods/multiple_testing.py` now exists as the bounded shared MI-12 helper
  - current shared method: `holm_bonferroni_v1`
- `src/local_replay_runtime/local_lab_multiple_testing_review.py` now exists as the Local IA Lab MI-12 sidecar
- current conservative truth:
  - current EDGE and tail-risk publications are treated as `interval_publication`, not as simultaneous hypothesis-test promotion
  - therefore the current bounded MI-12 verdict is explicit `not_required_interval_publication`, not a fake corrected p-value pass
  - future hypothesis-test families can still consume the shared Holm-Bonferroni helper
- the same truth now propagates into:
  - `local_lab_calibration_normalized_report.json`
  - `artifact_proof_assessment.json`
  - `local_lab_analysis_summary.json`
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
  - `local_lab_monitoring_bundle_manifest.json`
  - `local_lab_monitoring_feed`
- important invariant:
  - still Local IA Lab only
  - still no UI coupling
  - still no VPS/runtime mutation
  - MI-12 remains honest: no hidden blocker when the current bounded artifact family is interval-publication only
- latest proofs:
  - `rtk pytest tests/test_calibration_methods/test_multiple_testing.py tests/test_local_replay_runtime/test_local_lab_multiple_testing_review.py tests/test_local_replay_runtime/test_local_lab_calibration_normalized_report.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py tests/test_monitoring/test_local_lab_monitoring_bundle_manifest.py tests/test_monitoring/test_local_lab_bundle_discovery.py tests/test_monitoring/test_local_lab_monitoring_feed.py -q`
  - `22 passed`
  - `rtk pytest tests/test_calibration_methods tests/test_local_replay_runtime tests/test_monitoring tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_meta_learning tests/test_meta_minimal -q`
  - `524 passed`

## 5sextracies. Latest bounded Local IA Lab execution review (`13-C` first slice)

- `src/calibration_methods/execution.py` now exists as the bounded shared EXECUTION helper rail for:
  - `THR-X01` via Hampel-filtered absolute offset quantile + margin + human hard cap
  - `THR-X02` via bounded empirical gap quantile + human hard cap
- `src/local_replay_runtime/local_lab_execution_review.py` now exists as the Local IA Lab EXECUTION sidecar for `THR-X01` / `THR-X02`
- current conservative truth:
  - the review is `partial` when no dedicated execution telemetry sidecar is supplied
  - this slice does not invent replay-derived execution telemetry that the export dir does not actually contain
  - this slice does not alter the current EDGE proof gate or release gate semantics
- `scripts/run_local_lab_analysis_bundle.py` now emits:
  - `local_lab_execution_review.json`
  - summary fields for `execution_review_status / execution_review_ready / execution_*_threshold_count`
  - optional input `--execution-telemetry-path`
- the same truth now propagates into:
  - `local_lab_analysis_summary.json`
  - `local_lab_monitoring_projection.json`
  - `local_lab_monitoring_backend_payload.json`
  - `local_lab_observability_export.json`
  - `local_lab_monitoring_bundle_manifest.json`
  - monitoring bundle discovery/feed
- important invariant:
  - still Local IA Lab only
  - still no UI coupling
  - still no VPS/runtime mutation
  - still no fake readiness when telemetry is absent
- latest proofs:
  - `rtk pytest tests/test_calibration_methods/test_execution.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_observability.py tests/test_monitoring/test_local_lab_monitoring_bundle_manifest.py tests/test_monitoring/test_local_lab_bundle_discovery.py tests/test_monitoring/test_local_lab_monitoring_feed.py -q`
  - `23 passed`
  - `rtk pytest tests/test_calibration_methods tests/test_local_replay_runtime tests/test_monitoring tests/test_backtest_artifact_import/test_export_dir_bridge.py tests/test_backtest_artifact_import/test_upload_bridge.py tests/test_backtest_artifact_import/test_validators.py tests/test_meta_learning tests/test_meta_minimal -q`
  - `529 passed`

## 5septentracies. Latest VPS -> local observability architecture anchor

- `16_VPS_LOCAL_OBSERVABILITY_ARCHITECTURE.md` now records the intended observability split:
  - VPS = runtime + lightweight collection + short retention
  - local PC = Prometheus + Grafana + heavy drill-down + long retention
- hard rule now explicit:
  - continuous export = compact typed metrics / summaries
  - on-demand retrieval = detailed logs / deep traces / incident bundles
  - no permanent raw-stream export from VPS to local
- immediate code consequence:
  - next observability coding should start with real VPS process metrics + stable app `.prom` export
  - not with richer UI work
- missing bounded code now explicitly tracked for future slices:
  - process/system metric producer on the real VPS path
  - VPS `.prom` writer on the live service path
  - `telegram_alerter`
  - `disk_monitor`
  - `daily_pnl_breaker`
  - `regime_classifier`
  - `gatekeeper`
  - `info_stress_monitor`
  - `spread_guard`
  - `slippage_model`
- current estimate of overall solution completion is now tracked as `~62%`

## 5octies. VPS process observability slice landed

- real Shadow VPS service-side observability is now wired on the canonical service rail:
  - `scripts/run_shadow_vps_service.py`
  - `src/monitoring/process_metrics.py`
  - `src/monitoring/shadow_vps_service_monitoring.py`
- new governed outputs written by the real service loop:
  - `shadow_vps_service_monitoring_backend_payload.json`
  - `shadow_vps_service_observability_export.json`
  - `shadow_vps_service_observability.prom`
- current scope of the slice:
  - real bounded process sampling without extra dependency install
  - real bounded disk usage sampling on the service volume
  - typed future-dashboard/backend payload for the Shadow VPS service
  - canonical `.prom` text export from real service state
- explicit residuals after this slice:
  - no `node_exporter` hookup yet
  - no bounded log retrieval path yet
  - execution telemetry for `13-C EXECUTION` is still missing on the VPS side
- latest proofs:
  - `python -m pytest tests/test_monitoring/test_process_metrics.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `9 passed`
  - `python -m pytest tests/test_monitoring/test_monitoring_runtime.py tests/test_monitoring/test_disk_monitor.py tests/test_monitoring/test_process_metrics.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `19 passed`

## 5novies. VPS bounded log retrieval slice landed

- real Shadow VPS durable event retrieval is now coded on the monitoring rail:
  - `src/monitoring/shadow_vps_service_log_retrieval.py`
  - `src/monitoring/contracts.py`
  - `src/monitoring/__init__.py`
  - `scripts/run_shadow_vps_service.py`
- new typed retrieval surfaces now exist:
  - `ShadowVpsServiceLogQuery`
  - `ShadowVpsServiceLogQueryResult`
  - `ShadowVpsServiceLogEventProjection`
- current scope of the slice:
  - bounded full-scan query over the durable `shadow_vps_service.events.jsonl`
  - bounded recent-tail summary for the real service path
  - no new raw streaming bus
  - no UI coupling
- new governed output written by the real service loop:
  - `shadow_vps_service_recent_events.json`
- preserve the doctrine:
  - VPS keeps only compact recent-summary materialized continuously
  - deeper log drill-down stays on-demand
  - typed/audit-ready retrieval replaces manual raw JSONL parsing in the monitored seam
- explicit residuals after this slice:
  - no `node_exporter` hookup yet
  - no local Prometheus/Grafana scrape hookup yet
  - no compressed incident-bundle retrieval path yet
  - execution telemetry for `13-C EXECUTION` is still missing on the VPS side
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_shadow_vps_service_log_retrieval.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `11 passed`
  - `rtk pytest tests/test_monitoring/test_monitoring_runtime.py tests/test_monitoring/test_disk_monitor.py tests/test_monitoring/test_process_metrics.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_monitoring/test_shadow_vps_service_log_retrieval.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `22 passed`

## 5decies. VPS node_exporter textfile collector hookup landed

- the real Shadow VPS service can now mirror its compact `.prom` export into a node_exporter textfile collector directory:
  - `src/monitoring/observability_io.py`
  - `src/monitoring/contracts.py`
  - `src/monitoring/shadow_vps_service_monitoring.py`
  - `scripts/run_shadow_vps_service.py`
- current scope of the slice:
  - optional service arg `--node-exporter-textfile-dir`
  - writes `v53_shadow_vps_service.prom` into the configured collector directory
  - preserves the canonical compact `ObservabilityExport` text payload; no second metrics format was introduced
- preserve the doctrine:
  - the VPS still only writes compact typed metrics
  - deployment of `node_exporter` and local Prometheus scraping remains a separate ops step
  - no UI coupling
- explicit residuals after this slice:
  - no actual `node_exporter` deployment in repo
  - no local Prometheus/Grafana scrape hookup yet
  - no compressed incident-bundle retrieval path yet
  - execution telemetry for `13-C EXECUTION` is still missing on the VPS side
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_observability_io.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `10 passed`
  - `rtk pytest tests/test_monitoring/test_monitoring_runtime.py tests/test_monitoring/test_observability_io.py tests/test_monitoring/test_disk_monitor.py tests/test_monitoring/test_process_metrics.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_monitoring/test_shadow_vps_service_log_retrieval.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `24 passed`

## 5undecies. Local Prometheus scrape bundle hookup landed

- the VPS/local observability rail now has a typed handoff and a local-PC aggregator:
  - per-VPS handoff on the real service rail:
    - `src/monitoring/shadow_vps_service_scrape_manifest.py`
    - `scripts/run_shadow_vps_service.py`
  - local-PC aggregation:
    - `src/monitoring/shadow_vps_scrape_discovery.py`
    - `scripts/run_local_prometheus_scrape_bundle.py`
- new current artifacts:
  - per-VPS:
    - `shadow_vps_service_scrape_manifest.json`
    - `shadow_vps_service_prometheus_file_sd.json`
  - local-PC aggregate:
    - `shadow_vps_scrape_discovery.json`
    - `shadow_vps_prometheus_file_sd.json`
- current scope of the slice:
  - explicit `--scrape-host` / `--vps-id` handoff on the service rail
  - optional Prometheus `file_sd` sidecar per VPS
  - local discovery and de-duplication by latest target
  - one aggregated local Prometheus `file_sd` bundle
- preserve the doctrine:
  - the VPS still exports only compact typed artifacts
  - local PC owns the aggregation and future Prometheus/Grafana consumption
  - no UI coupling
- explicit residuals after this slice:
  - no actual `node_exporter` deployment in repo
  - no checked-in local Prometheus config yet
  - no Grafana dashboards yet
  - no compressed incident-bundle retrieval path yet
  - execution telemetry for `13-C EXECUTION` is still missing on the VPS side
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_shadow_vps_service_scrape_manifest.py tests/test_monitoring/test_shadow_vps_scrape_discovery.py tests/test_monitoring/test_local_prometheus_scrape_bundle_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `11 passed`
  - `rtk pytest tests/test_monitoring/test_monitoring_runtime.py tests/test_monitoring/test_observability_io.py tests/test_monitoring/test_disk_monitor.py tests/test_monitoring/test_process_metrics.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_monitoring/test_shadow_vps_service_log_retrieval.py tests/test_monitoring/test_shadow_vps_service_scrape_manifest.py tests/test_monitoring/test_shadow_vps_scrape_discovery.py tests/test_monitoring/test_local_prometheus_scrape_bundle_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `29 passed`

## 5duodecies. Checked local Prometheus config generator landed

- the local-PC side now has a checked config generator above the aggregated file_sd bundle:
  - `src/monitoring/local_prometheus_config.py`
  - `scripts/run_local_prometheus_config.py`
- new current artifacts:
  - `prometheus.local.generated.yml`
  - `prometheus.local.config.summary.json`
- current scope of the slice:
  - consumes `shadow_vps_prometheus_file_sd.json`
  - generates a minimal checked local Prometheus config
  - optional local node_exporter target included by config generation for Unix-like hosts
  - optional local windows_exporter target included by config generation for Windows local PCs
- preserve the doctrine:
  - still no heavy UI coupling
  - still no direct mutation of VPS runtime
  - checked config generation stays local-PC side
- explicit residuals after this slice:
  - no actual Prometheus process launch/orchestration in repo
  - no Grafana dashboards yet
  - no compressed incident-bundle retrieval path yet
  - execution telemetry for `13-C EXECUTION` is still missing on the VPS side
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_local_prometheus_config.py tests/test_monitoring/test_local_prometheus_config_launcher.py tests/test_monitoring/test_shadow_vps_service_scrape_manifest.py tests/test_monitoring/test_shadow_vps_scrape_discovery.py tests/test_monitoring/test_local_prometheus_scrape_bundle_launcher.py -q`
  - `8 passed`
  - `rtk pytest tests/test_monitoring/test_monitoring_runtime.py tests/test_monitoring/test_observability_io.py tests/test_monitoring/test_disk_monitor.py tests/test_monitoring/test_process_metrics.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_monitoring/test_shadow_vps_service_log_retrieval.py tests/test_monitoring/test_shadow_vps_service_scrape_manifest.py tests/test_monitoring/test_shadow_vps_scrape_discovery.py tests/test_monitoring/test_local_prometheus_scrape_bundle_launcher.py tests/test_monitoring/test_local_prometheus_config.py tests/test_monitoring/test_local_prometheus_config_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `32 passed`

## 5terdecies. Windows local Prometheus exporter support landed

- the checked local Prometheus config generator now supports both local-PC exporter families explicitly:
  - `src/monitoring/local_prometheus_config.py`
  - `scripts/run_local_prometheus_config.py`
- current scope of the slice:
  - `--local-node-exporter-target` remains available for Unix-like local hosts
  - `--local-windows-exporter-target` is now available for Windows local PCs
  - default config generation no longer assumes a local exporter when none was requested
- preserve the doctrine:
  - no Unix-only exporter assumption on Windows
  - generated config stays typed and local-only
  - no direct mutation of VPS runtime
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_local_prometheus_config.py tests/test_monitoring/test_local_prometheus_config_launcher.py -q`
  - `6 passed`

## 5quaterdecies. Dual-role dev local Prometheus HTTP bridge landed

- the local-PC dev path now has a bounded HTTP bridge for the current `.prom` payload when no real local exporter exists:
  - `src/monitoring/local_prometheus_metrics_bridge.py`
  - `scripts/run_local_prometheus_metrics_bridge.py`
- current scope of the slice:
  - serves the current V5.3 `.prom` payload over `/metrics`
  - exposes `/-/ready`
  - writes `local_prometheus_metrics_bridge.summary.json`
  - preserves the real VPS scrape model; this bridge is dev-only for dual-role local runs
- preserve the doctrine:
  - no manual Prometheus YAML editing
  - no change to the real VPS `node_exporter` assumption
  - no UI coupling
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_local_prometheus_metrics_bridge.py tests/test_monitoring/test_local_prometheus_metrics_bridge_launcher.py tests/test_monitoring/test_local_prometheus_config.py tests/test_monitoring/test_local_prometheus_config_launcher.py -q`
  - `8 passed`

## 5quindecies. Local Grafana dashboard bundle and bootstrap landed

- the local dev observability rail now has an importable Grafana dashboard bundle and a local API bootstrap:
  - `src/monitoring/local_grafana_dashboard.py`
  - `scripts/run_local_grafana_dashboard.py`
  - `src/monitoring/local_grafana_api.py`
  - `scripts/run_local_grafana_bootstrap.py`
- current scope of the slice:
  - builds an importable dashboard JSON over the currently observed `v53_shadow_vps_*` metrics
  - writes a typed dashboard summary with observed metric inventory
  - can create the local Prometheus datasource in Grafana and import the dashboard through the local Grafana HTTP API
- preserve the doctrine:
  - dashboard queries are constrained to current metric reality
  - no runtime mutation
  - no deviation from the real VPS handoff model
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_local_grafana_dashboard.py tests/test_monitoring/test_local_grafana_dashboard_launcher.py tests/test_monitoring/test_local_grafana_api.py tests/test_monitoring/test_local_grafana_bootstrap_launcher.py tests/test_monitoring/test_local_prometheus_metrics_bridge.py tests/test_monitoring/test_local_prometheus_metrics_bridge_launcher.py tests/test_monitoring/test_local_prometheus_config.py tests/test_monitoring/test_local_prometheus_config_launcher.py -q`
  - `13 passed`

## 5sexdecies. Local IA Lab Grafana rail landed on the dual-role dev path

- the local observability rail now covers both the Shadow VPS bridge and the Local IA Lab bridge:
  - `src/monitoring/local_lab_grafana_dashboard.py`
  - `scripts/run_local_lab_grafana_dashboard.py`
  - `src/monitoring/local_prometheus_metrics_bridge.py`
  - `scripts/run_local_prometheus_metrics_bridge.py`
  - `src/monitoring/local_prometheus_config.py`
  - `scripts/run_local_prometheus_config.py`
- current scope of the slice:
  - the dev-only metrics bridge can now serve either a raw `.prom` file or an observability export JSON carrying `text_payload`
  - the local Prometheus config can now add a dedicated `v53_local_lab` scrape job via `--local-lab-target`
  - an importable Local IA Lab Grafana dashboard is now generated from the real observed `v53_local_lab_*` metric surface
  - the generated Local IA Lab dashboard is detailed but still constrained to current metric reality, not imagined future panels
- current dev artifacts:
  - `build/dev_dual_role_demo/local_lab_grafana_dashboard/v53_local_lab_grafana.dashboard.json`
  - `build/dev_dual_role_demo/local_lab_grafana_dashboard/v53_local_lab_grafana.summary.json`
  - `build/dev_dual_role_demo/local_prometheus_config_with_lab/prometheus.local.generated.yml`
  - `build/dev_dual_role_demo/local_prometheus_config_with_lab/prometheus.local.config.summary.json`
- preserve the doctrine:
  - no new runtime profile
  - no VPS runtime mutation
  - no heavy UI coupling on the VPS side
  - Local IA Lab remains local-only, surfaced through typed sidecars and compact metrics
- latest proofs:
  - `python -m pytest tests/test_monitoring/test_local_prometheus_metrics_bridge.py tests/test_monitoring/test_local_prometheus_metrics_bridge_launcher.py tests/test_monitoring/test_local_prometheus_config.py tests/test_monitoring/test_local_prometheus_config_launcher.py tests/test_monitoring/test_local_lab_grafana_dashboard.py tests/test_monitoring/test_local_lab_grafana_dashboard_launcher.py -q`
  - `19 passed`

## 5septdecies. `13-C EXECUTION` now has a real service-owned telemetry producer

- new code:
  - `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py`
  - `scripts/run_shadow_vps_service.py`
  - `scripts/run_local_lab_analysis_bundle.py`
- current slice truth:
  - the Shadow VPS service now writes a durable cumulative archive:
    - `shadow_vps_service_execution_telemetry.archive.json`
  - and a current service-owned handoff sidecar:
    - `shadow_vps_service_execution_telemetry.json`
  - the service sidecar is bindable by the Local IA Lab bundle without pre-baking a review `correlation_id`
  - `THR-X02` is now derived from real websocket timing sources already emitted by the service:
    - injected websocket stream -> inter-arrival series
    - native live capture snapshot batch -> accepted-event inter-arrival series
  - `THR-X01` stays explicit and optional through `--execution-time-sync-offsets-path`
  - the service state and monitoring payload now expose `last_execution_telemetry_ref` / `execution_telemetry_ref`
- preserve the doctrine:
  - no fake readiness
  - cumulative by `session_date`, not ad hoc per-run overwrite
  - service-owned artifact stays typed and audit-ready
  - Local IA Lab remains the consumer; the VPS service only collects and hands off
- latest proofs:
  - `python -m pytest tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `20 passed`

## 5octodecies. `13-C EXECUTION` now auto-harvests `THR-X01` from native live capture when available

- new code:
  - `src/protocols/shadow_live_websocket.py`
  - `src/protocols/shadow_vps_service.py`
  - `scripts/run_shadow_vps_service.py`
- current slice truth:
  - native live capture can now write a bounded passive sidecar:
    - `live_time_sync_offsets.json`
  - the sidecar is produced only when `time_sync_probe_enabled=true` on `ShadowLiveWebSocketConfig`
  - the Shadow VPS service now falls back to that service-owned sidecar for `THR-X01` when `--execution-time-sync-offsets-path` is not supplied
  - the ref is propagated through:
    - `ShadowLiveWebSocketCaptureResult`
    - `ShadowVpsServiceState.last_live_capture_time_sync_offsets_ref`
    - `ShadowVpsRuntimeEvidenceBundle.live_capture_time_sync_offsets_ref`
    - `ShadowVpsCampaignSummary.live_capture_time_sync_offsets_ref`
- preserve the doctrine:
  - passive only, no execution mutation
  - bounded probe, not an always-on heavy runtime loop
  - if the probe fails, live capture stays up and the sidecar remains honestly absent with explicit error text
- latest proofs:
  - `python -m pytest tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `26 passed`

## 5novemdecies. `13-C EXECUTION` now harvests service-owned `THR-X04/X05` samples and exposes a shared `THR-X04` calibrator

- new code:
  - `src/calibration_methods/execution.py`
  - `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py`
  - `src/local_replay_runtime/local_lab_execution_review.py`
- current slice truth:
  - the service-owned execution telemetry artifact now carries:
    - `spread_bps`
    - `spread_observation_days`
    - `spread_session_dates`
    - `spread_source_refs`
    - `slippage_bps`
    - `slippage_observation_days`
    - `slippage_session_dates`
    - `slippage_source_refs`
  - those samples are harvested from existing service-owned market evidence:
    - snapshot/depth spreads from injected websocket streams or native snapshot batches
    - slippage samples from route hints when present
  - `src/calibration_methods/execution.py` now exposes `calibrate_spread_guard_threshold_bps(...)` for `THR-X04`
  - the global execution review contract is extended to carry the new sample families, but the review gating logic remains intentionally focused on `THR-X01/X02` on this slice
- preserve the doctrine:
  - no fake `THR-X05` model claim yet
  - no `THR-X03` green verdict without true REST/quota telemetry
  - service-owned evidence first, review consumption later
- latest proofs:
  - `python -m pytest tests/test_calibration_methods/test_execution.py tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `30 passed`

## 20. `13-C EXECUTION` now makes `THR-X04` a real Local IA Lab review threshold

- new code:
  - `src/local_replay_runtime/local_lab_execution_review.py`
  - `src/calibration_methods/__init__.py`
- current slice truth:
  - `THR-X04` is now consumed by the Local IA Lab execution review with explicit doctrine:
    - requires `spread_bps`
    - requires `spread_observation_days >= 30`
    - calibrates via `calibrate_spread_guard_threshold_bps(...)`
    - keeps the human hard cap at `50 bps`
  - the review now covers:
    - `THR-X01`
    - `THR-X02`
    - `THR-X04`
  - bundle summaries now expose the updated execution threshold counts automatically
- preserve the doctrine:
  - `THR-X03` still has no green verdict without real service quota telemetry
  - `THR-X05` still has no green verdict without a real slippage model
  - no fake readiness was added for either missing threshold family
- latest proofs:
  - `python -m pytest tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_calibration_methods/test_execution.py -q`
  - `17 passed`
  - `python -m pytest tests/test_calibration_methods/test_execution.py tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `31 passed`

## 21. `13-C EXECUTION` now exposes explicit `THR-X03/X05` review gaps instead of silently omitting them

- new code:
  - `src/local_replay_runtime/local_lab_execution_review.py`
- current slice truth:
  - the Local IA Lab execution review now enumerates the full bounded execution threshold set:
    - `THR-X01`
    - `THR-X02`
    - `THR-X03`
    - `THR-X04`
    - `THR-X05`
  - current honest review status is now:
    - `THR-X01` ready when bounded time-sync evidence exists
    - `THR-X02` ready when bounded websocket evidence exists
    - `THR-X04` ready when bounded spread evidence exists
    - `THR-X03` partial with `THR-X03_SERVICE_RATE_LIMIT_TELEMETRY_MISSING`
    - `THR-X05` partial with either missing telemetry or `THR-X05_MODEL_NOT_IMPLEMENTED`
  - bundle summaries now surface:
    - `execution_ready_threshold_count = 3`
    - `execution_partial_threshold_count = 2`
    - `execution_review_status = partial`
- preserve the doctrine:
  - no fake green verdict for `X03`
  - no fake green verdict for `X05`
  - release/shadow gates were not weakened or bypassed
- latest proofs:
  - `python -m pytest tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_calibration_methods/test_execution.py -q`
  - `17 passed`
  - `python -m pytest tests/test_calibration_methods/test_execution.py tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `31 passed`

## 22. `13-C EXECUTION` now carries service-owned size traces for the future `THR-X05` model

- new code:
  - `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py`
  - `src/local_replay_runtime/local_lab_execution_review.py`
- current slice truth:
  - the service-owned execution telemetry artifact now also carries:
    - `candidate_sizes`
    - `candidate_size_observation_days`
    - `candidate_size_session_dates`
    - `candidate_size_source_refs`
    - `final_sizes`
    - `final_size_observation_days`
    - `final_size_session_dates`
    - `final_size_source_refs`
  - those traces are harvested directly from route hints already present in injected/live evidence
  - the review contract can now receive these future `X05` inputs without claiming a model exists
- preserve the doctrine:
  - no fake `THR-X05` model was introduced
  - this slice is evidence preparation only
  - release/shadow gates stay unchanged
- latest proofs:
  - `python -m pytest tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_calibration_methods/test_execution.py -q`
  - `17 passed`
  - `python -m pytest tests/test_calibration_methods/test_execution.py tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `31 passed`

## 23. `13-C EXECUTION` now persists service-owned `THR-X03` quota probe telemetry end-to-end

- new code:
  - `src/protocols/shadow_live_websocket.py`
  - `src/protocols/shadow_vps_service.py`
  - `src/local_replay_runtime/local_lab_execution_telemetry_artifact.py`
  - `src/local_replay_runtime/local_lab_execution_review.py`
- current slice truth:
  - the native live time-sync sidecar now also carries bounded quota probe metadata:
    - `rest_call_count`
    - `probe_duration_s`
    - `rest_quota_max_calls_per_minute`
    - `observed_calls_per_minute`
  - the service-owned execution telemetry artifact now preserves that metadata as:
    - `quota_call_counts`
    - `quota_probe_durations_s`
    - `quota_limit_calls_per_minute_values`
    - `quota_calls_per_minute_observed`
    - `quota_observation_days`
    - `quota_source_refs`
  - the Local IA Lab execution review now distinguishes:
    - telemetry missing -> `THR-X03_SERVICE_RATE_LIMIT_TELEMETRY_MISSING`
    - telemetry present but quota cap missing -> `THR-X03_SERVICE_RATE_LIMIT_CAP_MISSING`
    - telemetry present but `< 30d` -> `THR-X03_EXECUTION_HISTORY_LT_30D`
    - telemetry present and history sufficient -> still `partial` with `THR-X03_MODEL_NOT_IMPLEMENTED`
- preserve the doctrine:
  - no fake `THR-X03` green verdict was introduced
  - this slice adds evidence plumbing and honest review semantics only
  - release/shadow/live gates remain unchanged
- latest proofs:
  - `python -m pytest tests/test_protocols/test_shadow_live_websocket.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `20 passed`
  - `python -m pytest tests/test_calibration_methods/test_execution.py tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `32 passed`

## 24. `13-C EXECUTION` now has first bounded models for `THR-X03` and `THR-X05`

- new code:
  - `src/calibration_methods/execution.py`
  - `src/calibration_methods/__init__.py`
  - `src/local_replay_runtime/local_lab_execution_review.py`
- current slice truth:
  - `THR-X03` now calibrates a real throttle ratio from service-owned quota telemetry:
    - observed REST calls/minute
    - official quota cap
    - Little's-law-style burst margin
    - human hard cap at `0.80`
  - `THR-X05` now calibrates a first bounded slippage model from service-owned size/slippage evidence:
    - robust Huber linear fit on `sqrt(size)`
    - size proxy chosen from `final_size` first, else `candidate_size`
    - validation floor `R² >= 0.30`
    - reference prediction published at the `q95` observed size
  - on aligned 30d service-owned evidence, the Local IA Lab execution review can now become fully `ready`
- preserve the doctrine:
  - no live-runtime mutation was introduced
  - no opaque ML or hidden fallback was introduced
  - `THR-X05` is still a first bounded model, not the final execution backbone implementation
- latest proofs:
  - `python -m pytest tests/test_calibration_methods/test_execution.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py -q`
  - `21 passed`
  - `python -m pytest tests/test_calibration_methods/test_execution.py tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `35 passed`

## 25. `13-C EXECUTION` now projects `THR-X03/X05` into future runtime consumer contracts

- new code:
  - `src/local_replay_runtime/local_lab_execution_runtime_projection.py`
  - `src/local_replay_runtime/artifact_proof_summary_builder.py`
  - `src/local_replay_runtime/artifact_release_candidate.py`
  - `scripts/run_local_lab_analysis_bundle.py`
- current slice truth:
  - the Local IA Lab bundle now emits `local_lab_execution_runtime_projection.json`
  - the projection is typed and bounded for two future consumers only:
    - `rate_limiter` from `THR-X03`
    - `slippage_model` from `THR-X05`
  - proof assessment and release candidate now carry this projection as descriptive handoff evidence
  - no new runtime module was created and no Shadow/Micro-live/Live gate was bypassed
- preserve the doctrine:
  - projection is descriptive only
  - it does not mutate live runtime behavior
  - it does not become a new release blocker on this slice
- latest proofs:
  - `python -m pytest tests/test_local_replay_runtime/test_local_lab_execution_runtime_projection.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `18 passed`
  - `python -m pytest tests/test_calibration_methods/test_execution.py tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_local_replay_runtime/test_local_lab_execution_review.py tests/test_local_replay_runtime/test_local_lab_execution_runtime_projection.py tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `46 passed`

## 26. `13-C EXECUTION` now has first canonical runtime consumers for `THR-X03/X05`

- new runtime truth:
  - `src/execution_backbone/rate_limiter.py` now defines the bounded canonical consumer for `THR-X03`
  - `src/execution_backbone/slippage_model.py` now defines the bounded canonical consumer for `THR-X05`
  - `src/execution_backbone/execution_runtime.py` can now consume those models only when they are injected explicitly
- current slice behavior:
  - `THR-X05` augments `expected_cost` conservatively before order selection and carries audit metadata into the submitted intent
  - `THR-X03` can veto submission when live metadata already exposes `rest_quota_ratio_current`
  - if the models are absent, or if `THR-X03` telemetry is absent/invalid, the runtime stays fail-open and unchanged
- preserve the doctrine:
  - no bootstrap auto-wiring yet
  - no live/runtime mutation unless a caller injects the models explicitly
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `python -m pytest tests/test_execution_backbone/test_rate_limiter.py tests/test_execution_backbone/test_slippage_model.py tests/test_execution_backbone/test_execution_runtime.py -q`
  - `30 passed`
  - `python -m pytest tests/test_execution_backbone/test_execution_integration.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `17 passed`

## 27. `13-C EXECUTION` runtime consumers now have an explicit bootstrap bridge

- new bridge truth:
  - `src/protocols/execution_runtime_projection_bridge.py` now loads `local_lab_execution_runtime_projection.json` fail-open
  - `src/protocols/execution_runtime_bootstrap.py` now accepts `execution_runtime_projection_path`
  - `build_execution_runtime(...)` and `build_binance_execution_runtime(...)` can now recover:
    - `rate_limit_model` from `THR-X03`
    - `slippage_model` from `THR-X05`
- preserve the doctrine:
  - activation stays explicit; default behavior remains unchanged when no projection path is provided
  - missing / partial / invalid projection artifacts still fail open
  - no gate bypass and no hidden live mutation
- latest proofs:
  - `python -m pytest tests/test_protocols/test_execution_runtime_projection_bridge.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_execution_runtime.py -q`
  - `36 passed`
  - `python -m pytest tests/test_execution_backbone/test_rate_limiter.py tests/test_execution_backbone/test_slippage_model.py tests/test_execution_backbone/test_execution_integration.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `14 passed`

## 28. `13-C EXECUTION` runtime projection bridge is now visible in Build-10 monitoring

- new bridge truth:
  - `src/protocols/execution_runtime_dashboard.py` now projects the bounded `execution_runtime_projection_path` seam into typed monitoring truth
  - `src/monitoring/contracts.py`, `src/monitoring/technical_dashboard_backend.py`, `src/ui/technical_dashboard_view.py`, and `src/monitoring/observability.py` now expose that seam separately from the older compiled `execution_no_trade_bridge`
- preserve the doctrine:
  - no hidden runtime activation
  - no replacement of the existing no-trade bridge
  - the new surface is descriptive only and reports whether `THR-X03/X05` consumers are loadable
- latest proofs:
  - `rtk pytest tests/test_protocols/test_execution_runtime_dashboard.py tests/test_monitoring/test_monitoring_backend.py tests/test_monitoring/test_monitoring_runtime.py tests/test_monitoring/test_observability.py tests/test_ui/test_technical_dashboard.py -q`
  - `91 passed`
  - `python -m pytest tests/test_protocols/test_execution_runtime_projection_bridge.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_execution_runtime.py -q`
  - `36 passed`

## 29. `13-C EXECUTION` technical dashboard launcher now auto-discovers the runtime projection bridge

- new launcher truth:
  - `scripts/run_technical_dashboard.py` now auto-loads `local_lab_execution_runtime_projection.json` from the demo output directory when present
  - the launcher can also accept an explicit `--execution-runtime-projection-path`
  - demo payloads now surface the bounded `THR-X03/X05` consumer bridge without test-only manual injection
- preserve the doctrine:
  - demo/operator surface only
  - no runtime activation
  - no Shadow/Micro-live/Live bypass
- latest proofs:
  - `rtk pytest tests/test_ui/test_technical_dashboard_launcher.py tests/test_ui/test_technical_dashboard.py tests/test_monitoring/test_monitoring_backend.py tests/test_monitoring/test_observability.py tests/test_protocols/test_execution_runtime_dashboard.py -q`
  - `90 passed`
  - `python -m pytest tests/test_monitoring/test_monitoring_runtime.py tests/test_protocols/test_execution_runtime_projection_bridge.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_execution_runtime.py -q`
  - `46 passed`

## 30. `13-C EXECUTION` local replay shadow runner now surfaces the runtime projection bridge

- new runner truth:
  - `scripts/run_local_replay_shadow.py` now accepts an explicit `--execution-runtime-projection-path`
  - the same runner now auto-discovers `local_lab_execution_runtime_projection.json` from its output directory when present
  - baseline and candidate technical payloads now surface the bounded `THR-X03/X05` runtime projection bridge through the existing Build-10 dashboard contract
- preserve the doctrine:
  - runner/operator surface only
  - no hidden runtime activation
  - no replacement of Shadow gating or execution bootstrap
- latest proofs:
  - `python -m pytest tests/test_protocols/test_local_replay_shadow_runner.py tests/test_ui/test_technical_dashboard_launcher.py tests/test_protocols/test_execution_runtime_dashboard.py tests/test_monitoring/test_monitoring_backend.py tests/test_ui/test_technical_dashboard.py -q`
  - `95 passed`
  - `python -m pytest tests/test_protocols/test_execution_runtime_projection_bridge.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_execution_runtime.py -q`
  - `36 passed`

## 31. `13-C EXECUTION` Shadow orchestrator and VPS service now persist the runtime projection seam

- new service truth:
  - `scripts/run_shadow_daily_orchestrator.py` now accepts `--execution-runtime-projection-path` and persists the projection ref plus readiness counts in `shadow_daily_orchestrator.last_run.json`
  - `scripts/run_shadow_vps_service.py` now forwards that path, persists `last_execution_runtime_projection_ref`, and carries the same seam into the runtime evidence bundle and campaign summary
  - `src/monitoring/shadow_vps_service_monitoring.py` and `src/monitoring/contracts.py` now expose this seam in the Shadow VPS monitoring payload and observability export
- preserve the doctrine:
  - descriptive persistence only
  - no hidden runtime activation
  - no Shadow/Micro-live/Live bypass
- latest proofs:
  - `python -m pytest tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `24 passed`
  - `python -m pytest tests/test_protocols/test_execution_runtime_projection_bridge.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_execution_runtime.py tests/test_protocols/test_execution_runtime_dashboard.py tests/test_monitoring/test_monitoring_backend.py tests/test_ui/test_technical_dashboard.py -q`
  - `108 passed`

## 32. `13-C EXECUTION` Micro-live and Live-Light now carry the runtime projection seam through canonical contracts

- new protocol truth:
  - `src/protocols/contracts.py` now carries `execution_runtime_projection_*` fields in `MicroLiveInput`, `MicroLiveRunSummary`, `LiveLightInput`, and `LiveLightRunSummary`
  - `src/protocols/micro_live_runtime.py` now derives the seam from the governed `execution_runtime_projection_bridge` already present in the Shadow technical payload
  - `src/protocols/live_light_runtime.py` now propagates the same seam from governed Micro-live summaries into governed Live-Light inputs and summaries
  - `src/protocols/micro_live_dashboard.py`, `src/protocols/live_light_dashboard.py`, and `src/monitoring/contracts.py` now keep the normalized monitoring projections aligned with the canonical protocol chain
- preserve the doctrine:
  - descriptive seam propagation only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `python -m pytest tests/test_protocols/test_micro_live_runtime.py tests/test_protocols/test_live_light_runtime.py tests/test_protocols/test_micro_live_dashboard.py tests/test_protocols/test_live_light_dashboard.py -q`
  - `82 passed`
  - `python -m pytest tests/test_ui/test_technical_dashboard.py tests/test_monitoring/test_monitoring_backend.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `88 passed`

## 33. `13-C EXECUTION` Micro-live and Live dashboard cards now expose the runtime projection seam

- new operator truth:
  - `src/protocols/micro_live_dashboard.py` now exposes `exec_proj` status plus ready/partial/blocked consumer counts inside the Build-12 guardrails card detail
  - `src/protocols/live_light_dashboard.py` now exposes the same bounded seam inside the Build-13 readiness card detail
  - this makes the later-stage gate chain operator-visible without inventing a new card or changing gate semantics
- preserve the doctrine:
  - operator visibility only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `python -m pytest tests/test_protocols/test_micro_live_dashboard.py tests/test_protocols/test_live_light_dashboard.py tests/test_ui/test_technical_dashboard.py -q`
  - `33 passed`
  - `python -m pytest tests/test_protocols/test_micro_live_runtime.py tests/test_protocols/test_live_light_runtime.py -q`
  - `76 passed`

## 34. `13-C EXECUTION` Shadow live startup config can now carry the runtime projection seam

- new startup/config truth:
  - `src/protocols/shadow_vps_service.py` now lets `ShadowLiveWebSocketConfig` carry `execution_runtime_projection_path_ref`
  - `scripts/run_shadow_vps_service.py` now resolves that config-owned path at startup when the explicit CLI path is absent
  - explicit `--execution-runtime-projection-path` still wins over config and the seam remains descriptive only
- preserve the doctrine:
  - startup/config propagation only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `python -m pytest tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_protocols/test_shadow_live_websocket.py -q`
  - `12 passed`
  - `python -m pytest tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_local_replay_shadow_runner.py -q`
  - `18 passed`

## 35. `13-C EXECUTION` Shadow service now preserves runtime projection provenance

- new audit truth:
  - the Shadow service now persists `execution_runtime_projection_source` across state, runtime evidence bundle, campaign summary, and monitoring payloads
  - current governed values are `cli`, `live_websocket_config`, or `not_configured`
  - the existing `v53_shadow_vps_execution_runtime_projection_ready` metric now carries `projection_source` as a label
- preserve the doctrine:
  - provenance only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `python -m pytest tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `8 passed`
  - `python -m pytest tests/test_protocols/test_shadow_live_websocket.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_local_replay_shadow_runner.py -q`
  - `22 passed`

## 36. `13-C EXECUTION` Shadow local Grafana now renders the runtime projection seam

- new operator truth:
  - `src/monitoring/local_grafana_dashboard.py` now adds dedicated Shadow Grafana panels for `execution_runtime_projection_ready`, ready/partial/blocked consumer counts, and an instant label view exposing `projection_status` and `projection_source`
  - `scripts/run_local_grafana_dashboard.py` now generates a 12-panel Shadow dashboard bundle that can render the seam directly in Grafana, not only in the technical dashboard or raw Prometheus metrics
- preserve the doctrine:
  - observability only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `python -m pytest tests/test_monitoring/test_local_grafana_dashboard.py::test_build_local_shadow_vps_grafana_dashboard_contains_expected_queries tests/test_monitoring/test_local_grafana_dashboard_launcher.py::test_local_grafana_dashboard_launcher_writes_dashboard_and_summary -q`
  - `2 passed`

## 37. `13-C EXECUTION` Shadow service now keeps runtime projection observability on late telemetry failure

- new service truth:
  - `scripts/run_shadow_vps_service.py` now persists the written runtime evidence bundle ref plus the `execution_runtime_projection` seam into service state before attempting the durable execution telemetry sidecar write
  - if the later telemetry sidecar write fails, Build-10 monitoring and Prometheus still expose the already-produced runtime projection seam from the runtime evidence bundle instead of regressing to `not_configured`
- preserve the doctrine:
  - observability/persistence hardening only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `python -m pytest tests/test_protocols/test_shadow_vps_service_launcher.py::test_shadow_vps_service_preserves_execution_runtime_projection_when_telemetry_write_fails tests/test_protocols/test_shadow_vps_service_launcher.py::test_shadow_vps_service_captures_native_live_websocket_then_runs_shadow tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `4 passed`

## 38. `13-C EXECUTION` Shadow demo runs no longer degrade when telemetry sidecar has no governed export

- new service truth:
  - `scripts/run_shadow_vps_service.py` now recovers `last_run.export_dir_ref` from `auto_export_dir` when a governed auto-export exists but the orchestrator payload omitted the ref
  - true demo/replay runs with no governed export no longer degrade the whole Shadow service just because the Local IA Lab execution telemetry sidecar cannot be materialized
  - the service now emits `execution_telemetry_skipped` explicitly for that case, keeps `last_execution_telemetry_ref=""`, and still completes the governed Shadow day
- preserve the doctrine:
  - honest skip semantics only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `rtk pytest tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `10 passed`
  - `rtk pytest tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_local_replay_shadow_runner.py -q`
  - `16 passed`

## 39. `13-C EXECUTION` Shadow telemetry write/skip status is now observable in Build-10 and local Grafana

- new monitoring truth:
  - `src/protocols/shadow_vps_service.py` now persists `last_execution_telemetry_status`
  - `scripts/run_shadow_vps_service.py` now writes governed values `written`, `skipped`, and `failed` on the Shadow service state/campaign path
  - `src/monitoring/shadow_vps_service_monitoring.py` now projects `execution_telemetry_status` into the Build-10 payload detail string and emits bounded Prometheus metric `v53_shadow_vps_execution_telemetry_ready{telemetry_status=...}`
  - `src/monitoring/local_grafana_dashboard.py` now renders dedicated `Execution Telemetry Ready` and `Execution Telemetry Labels` panels in the local Shadow Grafana bundle
- preserve the doctrine:
  - observability only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `rtk pytest tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `10 passed`
  - `python -m pytest tests/test_monitoring/test_local_grafana_dashboard.py::test_build_local_shadow_vps_grafana_dashboard_contains_expected_queries tests/test_monitoring/test_local_grafana_dashboard_launcher.py::test_local_grafana_dashboard_launcher_writes_dashboard_and_summary -q`
  - `2 passed`

## 40. `13-C EXECUTION` Build-10 technical dashboard now exposes Shadow execution telemetry status

- new dashboard truth:
  - `ShadowProjection` now carries `execution_telemetry_ref` and `execution_telemetry_status`
  - `scripts/run_technical_dashboard.py` now projects those service-owned fields from `shadow_vps_service.campaign_summary.json` into the canonical Build-10 Shadow section
  - `src/ui/technical_dashboard_view.py` now renders an explicit `Execution Telemetry` card under `Build-11 Shadow`
- preserve the doctrine:
  - dashboard/normalization only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_monitoring_backend.py tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `74 passed`
  - `rtk pytest tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `10 passed`

## 41. `13-C EXECUTION` THR-X04 now lands as the third governed runtime consumer

- new runtime truth:
  - `src/execution_backbone/spread_guard.py` now defines the bounded runtime consumer for `THR-X04`
  - `src/local_replay_runtime/local_lab_execution_runtime_projection.py` now projects three consumers: `THR-X03 -> rate_limiter`, `THR-X04 -> spread_guard`, `THR-X05 -> slippage_model`
  - `src/protocols/execution_runtime_projection_bridge.py` and `src/protocols/execution_runtime_bootstrap.py` now load all three consumers in opt-in/fail-open mode
  - `src/execution_backbone/execution_runtime.py` now blocks on `spread_guard` only when the Lab projection explicitly loads that model
  - Build-10 monitoring, observability, technical dashboard, Shadow, Micro-live, and Live-light now all preserve the third consumer count and `spread_guard_model_loaded`
- preserve the doctrine:
  - opt-in only
  - no hidden live activation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `python -m pytest tests/test_execution_backbone/test_spread_guard.py tests/test_execution_backbone/test_execution_runtime.py tests/test_local_replay_runtime/test_local_lab_execution_runtime_projection.py tests/test_protocols/test_execution_runtime_projection_bridge.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_protocols/test_execution_runtime_dashboard.py -q`
  - `50 passed`
  - `python -m pytest tests/test_local_replay_runtime/test_artifact_proof_summary_builder.py tests/test_local_replay_runtime/test_artifact_release_candidate.py tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_monitoring/test_monitoring_backend.py tests/test_monitoring/test_monitoring_runtime.py tests/test_monitoring/test_observability.py tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_launcher.py tests/test_protocols/test_micro_live_runtime.py tests/test_protocols/test_micro_live_dashboard.py tests/test_protocols/test_live_light_runtime.py tests/test_protocols/test_live_light_dashboard.py -q`
  - `210 passed`

## 42. `13-C EXECUTION` Build-9 core smoke now accepts the governed execution projection seam

- new operated truth:
  - `scripts/run_build9_core_smoke.py` now accepts `--execution-runtime-projection-path`
  - the real non-test bootstrap path `_run_execution_bootstrap_smoke_with_projection(...)` now proves that `build_binance_execution_runtime(...)` can load the governed `THR-X03/X04/X05` consumer triplet on an operated launcher path
  - default smoke behavior stays unchanged when no projection is provided
- preserve the doctrine:
  - explicit opt-in only
  - no hidden live activation
  - no direct config bypass around the Lab projection
- latest proofs:
  - `python -m pytest tests/test_execution_backbone/test_build9_core_smoke_script.py tests/test_execution_backbone/test_spread_guard.py tests/test_execution_backbone/test_execution_runtime.py tests/test_protocols/test_execution_runtime_bootstrap.py -q`
  - `40 passed`

## 43. `13-C EXECUTION` the operated Shadow chain now preserves canonical bridge-load truth

- new operated truth:
  - `scripts/run_shadow_daily_orchestrator.py` no longer trusts only the top-level Lab artifact headline for `execution_runtime_projection`; it now derives the operated summary from the canonical bridge inspection
  - the Shadow daily last-run payload now persists whether the governed bridge is actually loadable plus the three model flags: `rate_limiter`, `spread_guard`, `slippage_model`
  - `scripts/run_shadow_vps_service.py`, `src/protocols/shadow_vps_service.py`, `src/monitoring/contracts.py`, and `src/monitoring/shadow_vps_service_monitoring.py` now carry that bridge truth through runtime-evidence, campaign summary, monitoring payload, and Prometheus export
  - `src/monitoring/local_grafana_dashboard.py` now exposes the same bridge-load truth in the local Shadow Grafana bundle through dedicated bridge/model-load panels
- preserve the doctrine:
  - no hidden runtime activation
  - no new launcher
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `rtk pytest tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `12 passed`
  - `rtk pytest tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `26 passed`
  - `python -m pytest tests/test_monitoring/test_local_grafana_dashboard.py::test_build_local_shadow_vps_grafana_dashboard_contains_expected_queries tests/test_monitoring/test_local_grafana_dashboard_launcher.py::test_local_grafana_dashboard_launcher_writes_dashboard_and_summary -q`
  - `2 passed`

## 44. `13-C EXECUTION` Build-10 Shadow cards now expose the operated projection bridge truth

- new operated truth:
  - `src/monitoring/contracts.py` now lets `ShadowProjection` carry the service-owned `execution_runtime_projection_*` bridge/load fields
  - `scripts/run_technical_dashboard.py` now projects those fields from `shadow_vps_service.campaign_summary.json` into the canonical Build-10 Shadow surface
  - `src/ui/technical_dashboard_view.py` now renders a dedicated `Execution Projection` card inside `Build-11 Shadow`, separate from the top-level bridge card and separate from `Execution Telemetry`
  - the local dev technical dashboard artifacts were regenerated under `build/dev_dual_role_demo/technical_dashboard`
- preserve the doctrine:
  - dashboard/normalization only
  - no hidden runtime activation
  - no shortcut around Shadow/Micro-live/Live gates
- latest proofs:
  - `rtk pytest tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_launcher.py tests/test_monitoring/test_monitoring_backend.py -q`
  - `74 passed`

## 45. `Build-14` bounded Opus entry-timing reader now exists on the governed enabler rail

- new code truth:
  - `src/complete_enablers/micro_edge_entry_timing_layer.py` now exists as the bounded Build-14 reader for the still-open Opus `entry timing` suggestion
  - it only uses existing `Build14ObservationInput` facts (`volume_support_ratio`, `adverse_obi_pressure`, `cra_sterilization_rate`, `queue_backlog`, `stale_pair_count`, `break_even_drift_alert`, `ce_net`)
  - `src/complete_enablers/limited_influence.py` now evaluates that reader beside the other Build-14 readers, so the entry-timing signal can appear in Shadow and post-Shadow bounded influence without opening a new runtime rail
  - `src/complete_enablers/__init__.py` now exports the new reader
- preserve the doctrine:
  - Build-14 enabler only
  - no autonomous trading behavior
  - no new runtime hook
  - no gate bypass around Shadow/Micro-live/Live
- latest proofs:
  - `rtk pytest tests/test_complete_enablers/test_contracts.py tests/test_protocols/test_live_light_runtime.py tests/test_protocols/test_shadow_runtime.py tests/test_smoke_bootstrap_recovery/test_shadow_readiness.py -q`
  - `97 passed`

## 46. `Build-14` bounded Opus exit-governor reader now exists on the governed enabler rail

- new code truth:
  - `src/complete_enablers/micro_edge_exit_governor.py` now exists as the bounded Build-14 reader for the still-open Opus `exit governor` suggestion
  - it only uses existing `Build14ObservationInput` facts (`break_even_drift_alert`, `cra_sterilization_rate`, `ce_net`, `dtr_loss_count`, `log_loss_count`, `breakout_failure_rate`, `ghost_liquidity_ratio`, `stale_pair_count`)
  - `src/complete_enablers/limited_influence.py` now evaluates that reader beside the other Build-14 readers, so the exit-quality signal can appear in Shadow and post-Shadow bounded influence without opening a new runtime rail
  - `src/complete_enablers/__init__.py` now exports the new reader
- preserve the doctrine:
  - Build-14 enabler only
  - no autonomous trading behavior
  - no new runtime hook
  - no gate bypass around Shadow/Micro-live/Live
- latest proofs:
  - `rtk pytest tests/test_complete_enablers/test_contracts.py tests/test_protocols/test_live_light_runtime.py tests/test_protocols/test_shadow_runtime.py tests/test_smoke_bootstrap_recovery/test_shadow_readiness.py -q`
  - `99 passed`

## 49. `T9 regime_lite` now loads the documented `THR-RG01..04` calibration seam

- new code truth:
  - `src/regime_classifier/regime_lite.py` now exposes `RegimeLiteCalibrationConfig` and `resolve_regime_lite_thresholds(...)`
  - the helper now consumes signed `calibration_loader` artifacts for `THR-RG01..04`
  - only the documented regime thresholds are artifact-governed in this slice; the secondary dimensions remain on bounded documented defaults until their own ids are promoted into the catalog
  - `calibration_loader` is now registered in the canonical manifest/build-order/dependency registry instead of remaining a shared-core ghost module
- preserve the doctrine:
  - opt-in loading only
  - no silent fallback when the artifact seam is requested
  - no hidden runtime activation
- latest proofs:
  - `rtk pytest tests/test_regime_classifier/test_regime_lite.py tests/test_manifest_registry/test_inventory.py tests/test_manifest_registry/test_build_order.py tests/test_manifest_registry/test_dependencies.py tests/test_dag_validator/test_layer_validator.py -q`
  - `128 passed`

## 50. `T9 regime_lite` now exposes an explicit governed `EXTREME -> safing recommendation` path

- new code truth:
  - `src/risk_backbone/regime_lite_safing.py` now exists
  - the helper emits a typed recommendation:
    - `ENTRY_BLOCK_ONLY` while cooldown is active
    - `HALT_RECOMMENDED` + `should_exit_all=True` while state=`EXTREME`
  - when explicitly requested, it can build a canonical `OperatorSafingRequest(action=set_halted)` using the existing governance dialect instead of inventing a new halt vocabulary
- preserve the doctrine:
  - recommendation only
  - no automatic kill switch trip
  - no hidden live activation
  - no gate bypass around Shadow/Micro-live/Live
- latest proofs:
  - `rtk pytest tests/test_risk_backbone/test_regime_lite_entry_gate.py tests/test_risk_backbone/test_regime_lite_safing.py tests/test_risk_backbone/test_risk_runtime.py -q`
  - `128 passed`

## 51. `T9 regime_lite` safing is now observable in canonical Build-10 supervision

- new code truth:
  - `src/monitoring/contracts.py` now exposes a typed `RegimeLiteSafingProjection` nested under `ShadowProjection`
  - `scripts/run_technical_dashboard.py` now hydrates this seam from `shadow_vps_service.campaign_summary.json` when the Shadow service emits it
  - `src/monitoring/technical_dashboard_backend.py` now elevates the Build-10 headline when the Shadow rail carries `entry_block_only` or `halt_recommended`
  - `src/ui/technical_dashboard_view.py` now renders an explicit `Build-11 Shadow -> Regime Safing` card
  - `src/monitoring/observability.py` now exports `v53_shadow_regime_lite_safing_status`
- preserve the doctrine:
  - recommendation only
  - no auto-`set_halted`
  - no hidden live activation
  - no dashboard-only raw seam
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_monitoring_backend.py tests/test_monitoring/test_observability.py tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `85 passed`

## 52. `T9 regime_lite` now propagates explicit governance truth through `Shadow -> Micro-live -> Live-Light`

- new code truth:
  - `src/protocols/contracts.py` now exposes `RegimeLiteGovernanceSummary` as a protocol-local summary contract
  - `src/protocols/shadow_runtime.py` can now materialize that summary when explicit typed `RegimeLiteAssessment` / `RegimeLiteSafingRecommendation` inputs are supplied
  - `src/protocols/micro_live_runtime.py` and `src/protocols/live_light_runtime.py` now preserve the seam end-to-end without inventing classifier inputs
- preserve the doctrine:
  - explicit producer only
  - no synthetic regime inference from unrelated payload fields
  - recommendation only
  - no hidden live activation
- latest proofs:
  - `rtk pytest tests/test_protocols/test_contracts.py tests/test_protocols/test_shadow_runtime.py tests/test_protocols/test_micro_live_runtime.py tests/test_protocols/test_live_light_runtime.py -q`
  - `142 passed`

## 53. `T9 regime_lite` governance is now persisted on the operated `Shadow VPS service` rail

- new code truth:
  - `scripts/run_shadow_daily_orchestrator.py` now flattens `shadow_summary.regime_lite_governance` into the typed `last_run` sidecar instead of dropping the operated seam
  - `src/protocols/shadow_vps_service.py` now lets `ShadowVpsRuntimeEvidenceBundle` and `ShadowVpsCampaignSummary` carry the persisted `regime_lite` governance and safing fields
  - `scripts/run_shadow_vps_service.py` now copies that truth through `last_run -> runtime_evidence_bundle -> campaign_summary`
  - `src/monitoring/shadow_vps_service_monitoring.py` now surfaces the seam in the service payload/detail and exports bounded Prometheus symbols:
    - `v53_shadow_vps_regime_lite_safing_status`
    - `v53_shadow_vps_regime_lite_entries_blocked`
    - `v53_shadow_vps_regime_lite_should_exit_all`
- preserve the doctrine:
  - copy operated `Shadow` truth only
  - no synthetic regime inference inside the service
  - recommendation only
  - no hidden auto-halt / no bypass of `Shadow -> Micro-live -> Live`
- latest proofs:
  - `rtk pytest tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `13 passed`

## 54. `T9 regime_lite` now has an explicit operated producer on `run_local_replay_shadow -> daily orchestrator -> Shadow VPS service`

- new code truth:
  - `scripts/run_local_replay_shadow.py` now accepts:
    - `--regime-lite-assessment-path`
    - `--regime-lite-safing-recommendation-path`
  - the governed Shadow runner now forwards those typed JSON artifacts into both `run_shadow_validation(...)` calls instead of leaving the seam protocol-only
  - `scripts/run_shadow_daily_orchestrator.py` and `scripts/run_shadow_vps_service.py` now pass the same opt-in seam through the operated rail
  - when supplied, the real `shadow_summary`, `last_run`, `runtime_evidence_bundle`, `campaign_summary`, and service monitoring payload all carry `regime_lite_governance_status=ready`
- preserve the doctrine:
  - explicit opt-in only
  - no synthetic classifier inputs
  - recommendation only
  - no hidden auto-halt / no bypass of `Shadow -> Micro-live -> Live`
- latest proofs:
  - `rtk pytest tests/test_protocols/test_local_replay_shadow_runner.py::test_export_local_replay_shadow_run_accepts_regime_lite_inputs tests/test_protocols/test_shadow_daily_orchestrator_launcher.py::test_shadow_daily_orchestrator_launcher_accepts_regime_lite_inputs tests/test_protocols/test_shadow_daily_orchestrator_launcher.py::test_read_regime_lite_governance_summary_projects_ready_shadow_summary tests/test_protocols/test_shadow_daily_orchestrator_launcher.py::test_shadow_daily_orchestrator_launcher_accepts_execution_runtime_projection_path tests/test_protocols/test_shadow_vps_service_launcher.py::test_shadow_vps_service_accepts_regime_lite_inputs tests/test_protocols/test_shadow_vps_service_launcher.py::test_shadow_vps_service_advances_to_next_dated_export_when_shadow_day_is_recorded tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `8 passed`

## 55. `T9 regime_lite` now auto-discovers governed sidecars on the `run_local_replay_shadow` rail

- new code truth:
  - `scripts/run_local_replay_shadow.py` now auto-discovers:
    - `regime_lite_assessment.json`
    - `regime_lite_safing_recommendation.json`
    in its governed `output_dir` when explicit CLI paths are omitted
  - this keeps the seam aligned with the existing `execution_runtime_projection` pattern instead of forcing manual CLI wiring on every run
  - the daily orchestrator can now pick up those sidecars automatically when they are staged inside the governed `shadow_output_dir`
- preserve the doctrine:
  - explicit path still wins
  - only typed sidecars are loaded
  - no synthetic classifier inputs
  - recommendation only / no hidden auto-halt
- latest proofs:
  - `python -m pytest tests/test_protocols/test_local_replay_shadow_runner.py::test_export_local_replay_shadow_run_autoloads_regime_lite_inputs tests/test_protocols/test_shadow_daily_orchestrator_launcher.py::test_shadow_daily_orchestrator_launcher_autoloads_regime_lite_inputs_from_shadow_output_dir -q`
  - `2 passed`

## 56. `T9 regime_lite` is now visible in the local Shadow Grafana dashboard

- new code truth:
  - `src/monitoring/local_grafana_dashboard.py` now includes dedicated Shadow panels for:
    - `Regime Lite Entries Blocked`
    - `Regime Lite Exit-All Recommended`
    - `Regime Lite Labels`
  - the dashboard now queries:
    - `v53_shadow_vps_regime_lite_entries_blocked`
    - `v53_shadow_vps_regime_lite_should_exit_all`
    - `v53_shadow_vps_regime_lite_safing_status`
  - the local dashboard summary/launcher tests no longer depend on the broken Windows `tmp_path` fixture on this machine
- preserve the doctrine:
  - dashboard reads only bounded Prometheus service metrics
  - no dashboard-only JSON seam
  - no hidden activation
- latest proofs:
  - `python -m pytest tests/test_monitoring/test_local_grafana_dashboard.py tests/test_monitoring/test_local_grafana_dashboard_launcher.py -q`
  - `4 passed`

## 57. `T9 regime_lite` now loads from `live_websocket_config` refs on the Shadow VPS service rail

- new code truth:
  - `src/protocols/shadow_vps_service.py` now lets `ShadowLiveWebSocketConfig` carry:
    - `regime_lite_assessment_path_ref`
    - `regime_lite_safing_recommendation_path_ref`
  - `scripts/run_shadow_vps_service.py` now resolves those refs with the same precedence as `execution_runtime_projection_path_ref`:
    - explicit CLI path wins
    - otherwise relative or absolute refs from `live_websocket_config` are loaded
  - the service now persists audit-ready provenance into state, runtime evidence bundle, campaign summary, and monitoring payload:
    - `regime_lite_assessment_ref/source`
    - `regime_lite_safing_recommendation_ref/source`
- preserve the doctrine:
  - no synthetic regime inference
  - no hidden auto-halt
  - typed artifact refs only
  - config loading stays recommendation-only
- latest proofs:
  - `python -m pytest tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `12 passed`

## 58. `T9 regime_lite` provenance is now observable in Prometheus labels

- new code truth:
  - `src/monitoring/shadow_vps_service_monitoring.py` now emits `assessment_source` and `safing_source` labels on:
    - `v53_shadow_vps_regime_lite_safing_status`
    - `v53_shadow_vps_regime_lite_entries_blocked`
    - `v53_shadow_vps_regime_lite_should_exit_all`
  - the monitoring detail line now carries:
    - `regime_lite=<severity>@<state>@<assessment_source>/<safing_source>`
  - this makes `cli` vs `live_websocket_config` visible without opening JSON sidecars
- preserve the doctrine:
  - bounded labels only
  - no new dashboard-only seam
  - no runtime behavior change
- latest proofs:
  - `python -m pytest tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `2 passed`

## 59. `T9 regime_lite` ref/source provenance now reaches the canonical Build-10 technical dashboard

- new code truth:
  - `scripts/run_technical_dashboard.py` now hydrates the operated Shadow service provenance fields:
    - `regime_lite_assessment_ref/source`
    - `regime_lite_safing_recommendation_ref/source`
  - `src/ui/technical_dashboard_view.py` now renders those refs/sources directly in the Build-11 Shadow `Regime Safing` card detail
  - Build-10 therefore exposes the same operated truth already persisted by the Shadow service, instead of dropping the ref/source seam at the dashboard boundary
- preserve the doctrine:
  - dashboard reads typed operated artifacts only
  - no dashboard-only inference
  - recommendation only
  - no hidden activation
- latest proofs:
  - `python -m pytest tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `37 passed`

## 60. PowerShell Binance Shadow bootstrap now installs API env and launches a bounded governed live campaign

- new code truth:
  - `scripts/Install-BinanceApiEnv.ps1` now installs:
    - `BINANCE_API_KEY`
    - `BINANCE_API_SECRET`
    - `V53_BINANCE_API_KEY`
    - `V53_BINANCE_SECRET_KEY`
    - `V53_BINANCE_LABEL`
    in process scope, and optionally in user scope
  - `scripts/Start-BinanceShadowLiveCampaign.ps1` now:
    - materializes `live_websocket_config.json`
    - preserves existing governed route hints/config
    - launches one bounded `run_shadow_vps_service.py` cycle
    - regenerates the canonical Build-10 HTML dashboard from the resulting campaign root
  - `docs/production_deployment_plan/17A_BINANCE_SHADOW_POWERSHELL_BOOTSTRAP.md` documents the operator flow
- preserve the doctrine:
  - Shadow only
  - typed config / typed artifact refs only
  - no secrets persisted into repo JSON
  - dashboard remains read-only
- latest proofs:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Install-BinanceApiEnv.ps1`
  - `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-BinanceShadowLiveCampaign.ps1 -CampaignRoot .\build\build11_live_websocket_campaign -EnableTimeSyncProbe -StopOnError`

## 61. Native Binance live connect failures now preserve endpoint and root cause instead of a generic string

- new code truth:
  - `src/protocols/shadow_live_websocket.py` now raises:
    - `Native live_websocket adapter failed to connect to <endpoint>: <root cause>`
    when the gateway runtime returns a failed connect status with an error message
  - the operated Shadow service artifacts therefore now keep the actionable socket failure instead of only `failed to connect`
  - the previous `WinError 10013` observation was confirmed to be a Codex sandbox network artifact, not a host firewall failure
  - the same bounded PowerShell live campaign now succeeds when launched outside the sandbox on the real Windows host
- preserve the doctrine:
  - no runtime behavior change beyond diagnostics
  - typed operated artifacts remain the source of truth
  - no hidden retry policy change
- latest proofs:
  - `python -m pytest tests/test_protocols/test_shadow_live_websocket.py tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `44 passed`

## 62. The bounded Binance Shadow live campaign now succeeds on the real Windows host and regenerates Build-10 artifacts

- new code truth:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-BinanceShadowLiveCampaign.ps1 -CampaignRoot .\build\build11_live_websocket_campaign -EnableTimeSyncProbe -StopOnError`
    now completes successfully when run outside the Codex sandbox
  - the current operated campaign artifacts now show:
    - `service_status=stopped`
    - `last_error=""`
    - `last_completed_session_date="2026-04-12"`
    - `execution_telemetry_status="written"`
    - live capture pairs `BTCUSDT, ETHUSDT`
    - `live_user_data_authenticated=true`
  - the canonical HTML dashboard has been regenerated from the successful operated campaign root
- preserve the doctrine:
  - bounded `Shadow` only
  - no live order path
  - dashboard remains a read-only consumer of operated artifacts
- latest proofs:
  - operated campaign root:
    - `build/build11_live_websocket_campaign/service/shadow_vps_service.state.json`
    - `build/build11_live_websocket_campaign/service/shadow_vps_service.campaign_summary.json`
    - `build/build11_live_websocket_campaign/technical_dashboard/technical_dashboard.html`

## 63. `daily_pnl_breaker` now exists and the first governed `THR-R01 -> risk_runtime` consumer is open

- new code truth:
  - `src/risk_backbone/loss_budgeter/daily_pnl_breaker.py` now exists as the typed persistent daily Shadow-lock seam for `THR-R01`
  - the breaker loads governed `THR-R01` via `calibration_loader`, enforces the documented hard cap `2%`, persists same-day Shadow lock state, and can optionally trip the canonical circuit breaker when explicitly asked
  - `src/risk_backbone/daily_pnl_breaker_entry_gate.py` now exists as the first bounded runtime consumer
  - `src/risk_backbone/risk_runtime.py` now accepts a typed opt-in `daily_pnl_precheck_hook`, so Build-4 can reject new entries when the breaker has already forced the session into Shadow
- preserve the doctrine:
  - opt-in only
  - fail-open by default
  - no hidden live activation
  - no automatic same-day reactivation after a breach
- latest proofs:
  - `python -m pytest tests/test_risk_backbone/test_daily_pnl_breaker.py tests/test_risk_backbone/test_daily_pnl_breaker_entry_gate.py tests/test_risk_backbone/test_risk_runtime.py -q`
  - `34 passed`
  - `python -m pytest tests/test_risk_backbone/test_risk_integration.py tests/test_engines/test_engine_a/test_engine_a_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_c/test_engine_c_runtime.py tests/test_engines/test_engine_d/test_engine_d_runtime.py -q`
  - `42 passed`

## 64. `reconciliation_scheduler` now exists as the first bounded `THR-I04` operated control seam

- new code truth:
  - `src/execution_backbone/reconciliation_layer/scheduler.py` now exists
  - the scheduler loads governed `THR-I04`, enforces bounded interval limits, and exposes typed `boot_reconcile(...)` + `run_periodic_if_due(...)`
  - boot reconciliation now has a canonical blocking seam for unresolved divergences
  - periodic reconciliation now has a canonical due/not-due seam and can trip the existing circuit breaker on critical divergence
- preserve the doctrine:
  - no daemon thread or hidden loop in this slice
  - explicit caller ownership of timing
  - reuse the canonical `EmergencyCircuitBreaker`
  - no bypass of the existing reconciliation runtime
- latest proofs:
  - `python -m pytest tests/test_execution_backbone/test_reconciliation_scheduler.py tests/test_execution_backbone/test_reconciliation_layer.py -q`
  - `35 passed`
  - `python -m pytest tests/test_execution_backbone/test_execution_runtime.py -q`
  - `28 passed`

## 65. `execution_runtime_bootstrap` now executes the first real operated `THR-I04` boot seam through Build-9 smoke

- new code truth:
  - `src/protocols/execution_runtime_bootstrap.py` now exposes typed bootstrap bundles:
    - `ExecutionRuntimeBootstrapBundle`
    - `build_execution_runtime_bootstrap_bundle(...)`
    - `build_binance_execution_runtime_bootstrap_bundle(...)`
  - the existing `build_execution_runtime(...)` and `build_binance_execution_runtime(...)` stay backward-compatible and still return only `ExecutionRuntime`
  - the new bundle can now expose:
    - the built runtime
    - the optional bounded `ReconciliationScheduler`
    - the optional boot reconcile result
  - stale-only first boot with zero divergences is now treated canonically as initial baseline establishment, not as a false trading block
  - `scripts/run_build9_core_smoke.py` now executes this seam explicitly and can also load governed `THR-I04` from an optional calibration root
- preserve the doctrine:
  - opt-in only
  - no hidden scheduler loop
  - no fake Shadow integration before a real runtime call site exists
  - Build-9 smoke remains the first operated caller on this rail
- latest proofs:
  - `rtk pytest tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_build9_core_smoke_script.py tests/test_execution_backbone/test_reconciliation_scheduler.py -q`
  - `20 passed`
  - `rtk pytest tests/test_execution_backbone/test_execution_runtime.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_build9_core_smoke_script.py tests/test_execution_backbone/test_reconciliation_scheduler.py -q`
  - `48 passed`

## 66. The standalone Build-9 smoke script now aligns with the canonical engine + portfolio facades

- new code truth:
  - `scripts/run_build9_core_smoke.py` now imports the canonical engine facades through:
    - `engines.engine_a`
    - `engines.engine_b`
    instead of the stale top-level aliases
  - the same script now bootstraps the Build-8 portfolio chain with an explicit `freshness_policy`, matching the current `OrchestratorConfig` contract
  - the direct script run therefore now reports:
    - Build-2..9 `PASS`
    - engine chain `PASS`
    - portfolio chain `PASS`
    - execution bootstrap `PASS`
  - the remaining direct-run failure is outside this slice: Build-1 still reports pre-existing DAG violations
- preserve the doctrine:
  - no new launcher
  - no compatibility alias package invented
  - smoke script updated to current canonical facades and typed config only
- latest proofs:
  - `rtk pytest tests/test_execution_backbone/test_build9_core_smoke_script.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_reconciliation_scheduler.py -q`
  - `21 passed`
  - `python scripts/run_build9_core_smoke.py`
  - direct report now shows Build-2..9 `PASS`; only Build-1 DAG remains `FAIL`

## 67. Build-1 DAG now reflects mostly real cycle debt instead of mixed registry drift

- new code truth:
  - `src/manifest_registry/module_inventory.py` now registers the real on-disk packages:
    - `calibration_methods`
    - `secrets_manager`
    - `sharia_compliance`
    - `venue_adapters`
  - `src/manifest_registry/build_order_registry.py` now gives those modules explicit build ownership without changing the Build-1 count:
    - `sharia_compliance` in Build-3
    - `calibration_methods` in Build-10
    - `secrets_manager` and `venue_adapters` in Build-11
  - `src/manifest_registry/dependency_registry.py` now authorizes the non-cyclic imports already present on disk for:
    - `execution_backbone -> calibration_loader, sharia_compliance`
    - `risk_backbone -> calibration_loader`
    - `scoring_backbone -> data_backbone`
    - `local_replay_runtime -> calibration_methods, data_backbone, meta_learning`
    - `backtest_artifact_import -> meta, monitoring`
    - `protocols -> engine_a, engine_b, regime_classifier, venue_adapters`
    - `venue_adapters -> interface_contracts, calibration_loader, data_backbone, execution_backbone, secrets_manager, sharia_compliance`
  - the missing-manifest bucket is now closed, and the Build-1 DAG report has been reduced from `47` errors to `27`
  - the remaining Build-1 failures are now the real debt:
    - cycle cluster around `local_replay_runtime`, `backtest_artifact_import`, `monitoring`, `protocols`, `ui`
    - forward/late imports:
      - `execution_backbone -> risk_backbone, scoring_backbone`
      - `monitoring -> complete_enablers, protocols, local_replay_runtime`
      - `protocols -> complete_enablers, engine_c, engine_d`
- preserve the doctrine:
  - no validator weakening
  - no cycle authorization to fake a green Build-1
  - no Build-1 module-count inflation
  - registry drift fixed first, real refactor debt left explicit
- latest proofs:
  - `rtk pytest tests/test_manifest_registry/test_inventory.py tests/test_manifest_registry/test_build_order.py tests/test_manifest_registry/test_dependencies.py -q`
  - `83 passed`
  - `python -c "import sys; sys.path.insert(0, 'src'); from dag_validator import validate_architecture; report = validate_architecture(); print(report.passed, report.error_count, report.warning_count)"`
  - `False 27 0`
  - `python scripts/run_build9_core_smoke.py`
  - direct report still shows Build-2..9 `PASS`; only Build-1 `dag_validator` remains `FAIL (27 error(s))`

## 68. Build-1 dropped the local_replay_runtime -> monitoring cycle cluster

- new code truth:
  - the Local IA Lab monitoring builders now live under `src/monitoring/`:
    - `local_lab_monitoring_projection.py`
    - `local_lab_monitoring_backend.py`
    - `local_lab_observability.py`
  - `scripts/run_local_lab_analysis_bundle.py` now feeds those builders with primitive release/bridge/promotion facts instead of passing `local_replay_runtime` typed objects across the boundary
  - the old `src/local_replay_runtime/local_lab_monitoring_*` files were removed instead of leaving compatibility wrappers that would preserve the reverse edge
  - the validator no longer reports the `local_replay_runtime -> monitoring` unauthorized imports, and the prior cycle cluster through those modules is gone
  - Build-1 real DAG debt is now down to `23` blocking errors:
    - `4` cycles
    - `19` unauthorized imports
- preserve the doctrine:
  - no validator weakening
  - no wrapper alias that keeps the same dependency alive
  - COMPLETE-only runtime doctrine remains unchanged; this slice does not reintroduce `LIGHT`
- latest proofs:
  - `rtk pytest tests/test_local_replay_runtime/test_local_lab_monitoring_projection.py tests/test_local_replay_runtime/test_local_lab_observability.py tests/test_local_replay_runtime/test_local_lab_monitoring_backend.py tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py tests/test_monitoring/test_local_lab_monitoring_feed.py tests/test_monitoring/test_local_lab_monitoring_bundle_manifest.py tests/test_monitoring/test_local_lab_ingestion.py tests/test_monitoring/test_local_lab_bundle_loader.py tests/test_monitoring/test_local_lab_bundle_discovery.py -q`
  - `23 passed`
  - direct `dag_validator` report now shows `23` blocking errors (`4` cycles + `19` unauthorized imports)
  - direct `python scripts/run_build9_core_smoke.py` still reaches Build-2..9 `PASS`; only Build-1 `dag_validator` remains `FAIL (23 error(s))`

## 69. Build-1 removed the replay-workflow loader and injected-stream back-edges

- new code truth:
  - `local_lab_replay_workflow_loader.py` now lives under `src/local_replay_runtime/`, not `src/monitoring/`
  - the old monitoring loader file was removed, so `monitoring -> local_replay_runtime` no longer exists through that replay workflow seam
  - shared injected stream loading now lives under `src/data_backbone/websocket_gateway/injected_stream_loader.py`
  - `protocols.shadow_websocket_ingest` and `local_replay_runtime.local_lab_execution_telemetry_artifact` both consume that lower loader instead of `local_replay_runtime -> protocols`
  - Build-1 blocking DAG debt is now down again to `19` real errors:
    - `3` cycles
    - `16` unauthorized imports
- preserve the doctrine:
  - no fake monitoring alias
  - no protocol wrapper kept only for Build-1 silence
  - COMPLETE-only runtime doctrine remains unchanged
- latest proofs:
  - `rtk pytest tests/test_monitoring/test_local_lab_replay_workflow_loader.py tests/test_protocols/test_shadow_websocket_ingest.py tests/test_local_replay_runtime/test_local_lab_execution_telemetry_artifact.py tests/test_protocols/test_contracts.py -q`
  - `36 passed`
  - direct `dag_validator` report now shows `19` blocking errors (`3` cycles + `16` unauthorized imports)
  - direct `python scripts/run_build9_core_smoke.py` still reaches Build-2..9 `PASS`; only Build-1 `dag_validator` remains `FAIL (19 error(s))`

## 70. Build-1 is now green after lowering the last execution-owned helpers

- new code truth:
  - `src/execution_backbone/execution_runtime.py` now imports its fee-aware edge gate from `src/execution_backbone/fee_aware_edge_gate.py`, not from `scoring_backbone`
  - `src/execution_backbone/reconciliation_layer/scheduler.py` now imports its circuit breaker from `src/execution_backbone/emergency_circuit_breaker.py`, not from `risk_backbone`
  - `src/scoring_backbone/fee_aware_edge_gate.py` is now a compatibility surface over the canonical execution-owned implementation
  - `src/risk_backbone/emergency_kill_switch/circuit_breaker.py` is now a compatibility surface over the canonical execution-owned implementation
  - `src/manifest_registry/dependency_registry.py` no longer grants the temporary upward allowances `execution_backbone -> risk_backbone` and `execution_backbone -> scoring_backbone`
  - instead, the higher modules keep explicit downward compatibility dependencies on `execution_backbone`
- preserve the doctrine:
  - no validator weakening
  - no fake Build-1 green through broad registry allowances
  - COMPLETE-only runtime doctrine unchanged
- latest proofs:
  - `rtk pytest tests/test_execution_backbone/test_execution_runtime.py tests/test_execution_backbone/test_reconciliation_scheduler.py tests/test_scoring_backbone tests/test_risk_backbone/test_circuit_breaker.py -q`
  - `168 passed`
  - `rtk pytest tests/test_manifest_registry/test_inventory.py tests/test_manifest_registry/test_build_order.py tests/test_manifest_registry/test_dependencies.py tests/test_dag_validator/test_layer_validator.py -q`
  - `96 passed`
  - direct `dag_validator` report now shows `0` blocking errors
  - direct `python scripts/run_build9_core_smoke.py` now reaches Build-1 `PASS` and Build-2..9 `PASS`

## 71. T12 now has a real canonical gatekeeper wrapper on the Build-3 execution rail

- new code truth:
  - `src/execution_backbone/gatekeeper/gatekeeper.py` now exists as the execution-owned convergence wrapper
  - `ExecutionRuntime.submit_opportunity(...)` now routes the pre-submit decision chain through `ExecutionGatekeeper.authorize(...)`
  - the existing execution guards stay intact; the gatekeeper is a convergence surface, not a replacement path
  - refusals now preserve the real `pair` and `engine_id` in the emitted `NoTradeDecision`
  - `ExecutionSubmission` now carries `gate_trace`, and the same trace is emitted in structured submission logs
  - `src/execution_backbone/__init__.py` now exports the typed gatekeeper surface
- deliberate limit of this slice:
  - no persisted `artifacts/gatekeeper/` audit store yet
  - no new runtime path outside the canonical Build-3 rail
  - COMPLETE-only doctrine unchanged
- latest proofs:
  - `rtk pytest tests/test_execution_backbone/test_gatekeeper.py tests/test_execution_backbone/test_execution_runtime.py tests/test_protocols/test_execution_runtime_bootstrap.py -q`
  - `41 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 72. T13 now has a first bounded info-stress precheck on the Build-4 risk rail

- new code truth:
  - `src/risk_backbone/info_stress_monitor.py` now exists as the bounded V37-3 detector
  - the monitor classifies `NORMAL / ELEVATED / EXTREME` from five simple signals:
    - spread explosion
    - depth ratio collapse
    - cancellation spike
    - taker imbalance saturation
    - micro-vol divergence
  - `build_info_stress_entry_gate(...)` now exposes that detector as a typed `RiskInfoStressPrecheckHook`
  - `src/risk_backbone/risk_runtime.py` now supports a dedicated `info_stress_precheck_hook` and explicit candidate-side indicator fields
  - EXTREME now blocks new entries through a governed cooldown on the real Build-4 risk runtime rail
- deliberate limit of this slice:
  - opt-in only
  - no Shadow/Micro-live/Live auto-wiring yet
  - no ML-heavy MAS implementation; this is the bounded lite seam only
- latest proofs:
  - `rtk pytest tests/test_risk_backbone/test_info_stress_monitor.py tests/test_risk_backbone/test_risk_runtime.py -q`
  - `29 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 73. T13 info_stress now propagates through the late-stage protocol rails

- new code truth:
  - `src/protocols/contracts.py` now defines `InfoStressGovernanceSummary`
  - `src/protocols/shadow_runtime.py` now accepts an optional `info_stress_assessment` and projects it into typed `shadow_summary.info_stress_governance`
  - `src/protocols/micro_live_runtime.py` now preserves that summary from Shadow into both `MicroLiveInput` and `MicroLiveRunSummary`
  - `src/protocols/live_light_runtime.py` now preserves the same summary from Micro-live into both `LiveLightInput` and `LiveLightRunSummary`
  - `src/protocols/__init__.py` now exports the summary type as canonical protocol surface
- deliberate limit of this slice:
  - no launcher/service/config auto-loading yet
  - no monitoring/dashboard projection yet
  - no second recommendation layer invented; this stays assessment-only for now
- latest proofs:
  - `rtk pytest tests/test_protocols/test_contracts.py tests/test_protocols/test_shadow_runtime.py tests/test_protocols/test_micro_live_runtime.py tests/test_protocols/test_live_light_runtime.py -q`
  - `147 passed`
  - `rtk pytest tests/test_risk_backbone/test_info_stress_monitor.py tests/test_risk_backbone/test_risk_runtime.py -q`
  - `29 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 74. T13 info_stress now propagates on the operated Shadow rail

- new code truth:
  - `scripts/run_local_replay_shadow.py` now accepts and auto-discovers `info_stress_assessment.json` and forwards the typed assessment into both provisional and final `run_shadow_validation(...)`
  - `scripts/run_shadow_daily_orchestrator.py` now projects `shadow_summary.info_stress_governance` into `shadow_daily_orchestrator.last_run.json`
  - `src/protocols/shadow_vps_service.py` now lets `ShadowLiveWebSocketConfig` carry `info_stress_assessment_path_ref`
  - `scripts/run_shadow_vps_service.py` now resolves `info_stress_assessment` with the same precedence as other governed refs (`cli` first, then `live_websocket_config`)
  - the service now persists `info_stress` ref/source plus governance truth into state, runtime evidence bundle, campaign summary, monitoring payload, and Prometheus export
  - `src/monitoring/shadow_vps_service_monitoring.py` now exports:
    - `v53_shadow_vps_info_stress_status`
    - `v53_shadow_vps_info_stress_alert_count`
    - `v53_shadow_vps_info_stress_entries_blocked`
- deliberate limit of this slice:
  - assessment-only seam remains intact
  - no fake recommendation layer
  - no new auto-halt or late-stage hidden activation
- latest proofs:
  - `rtk pytest tests/test_protocols/test_local_replay_shadow_runner.py tests/test_protocols/test_shadow_daily_orchestrator_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `39 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 75. T12 now persists a real append-only gatekeeper audit store on the canonical execution rail

- new code truth:
  - `src/execution_backbone/gatekeeper/audit_logger.py` now exists as the append-only JSONL audit logger for canonical gatekeeper decisions
  - `src/execution_backbone/execution_runtime.py` now accepts an optional `GatekeeperAuditLogger` and writes submitted / no-trade / blocked decisions on the existing `submit_opportunity(...)` path
  - `src/protocols/execution_runtime_bootstrap.py` now threads `gatekeeper_audit_path` through the canonical runtime bootstrap helpers
  - `scripts/run_build9_core_smoke.py` now accepts `--gatekeeper-audit-path` and can materialize a real `artifacts/gatekeeper/audit.jsonl` during the bounded bootstrap smoke
- deliberate limit of this slice:
  - no new runtime path outside the canonical Build-3 rail
  - no synthetic monitoring/dashboard layer added for this audit store
  - COMPLETE-only doctrine unchanged
- latest proofs:
  - `python -m pytest tests/test_execution_backbone/test_gatekeeper.py tests/test_execution_backbone/test_execution_runtime.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_build9_core_smoke_script.py -q`
  - `51 passed`
  - direct `python scripts/run_build9_core_smoke.py --gatekeeper-audit-path build/build9_core_smoke_run/artifacts/gatekeeper/audit.jsonl`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 76. T11 now has a bounded log rotation seam inside monitoring

- new code truth:
  - `src/monitoring/log_rotation.py` now exists as the bounded gzip + retention helper for operated logs
  - `rotate_log_file(...)` rotates one file into a timestamped `.gz`, truncates the active log, and prunes old archives by retention window
  - `src/monitoring/__init__.py` now exports `LogRotationResult` and `rotate_log_file`
- deliberate limit of this slice:
  - no Telegram integration yet
  - no automatic scheduler/daemon around rotation
  - no new package/profile semantics introduced
- latest proofs:
  - `python -m pytest tests/test_monitoring/test_log_rotation.py tests/test_monitoring/test_disk_monitor.py tests/test_execution_backbone/test_gatekeeper.py tests/test_execution_backbone/test_execution_runtime.py tests/test_protocols/test_execution_runtime_bootstrap.py tests/test_execution_backbone/test_build9_core_smoke_script.py -q`
  - `55 passed`

## 77. T11 now has a bounded `telegram_alerter` adapter over canonical `AlertRecord`

- new code truth:
  - `src/alerting/{__init__,telegram_alerter}.py` now exists as a bounded external delivery adapter package
  - `telegram_alerter.py` loads bot token + chat id from JSON/YAML or sealed mappings via `secrets_manager.load(...)`
  - the adapter stays typed on canonical `interface_contracts.AlertRecord`, with severity filtering and bounded urllib posting
  - `manifest_registry` now registers `alerting` as a canonical Build-11 module, so adding the package does not re-open Build-1 DAG drift
- deliberate limit of this slice:
  - no hidden `monitoring -> alerting` wiring yet
  - no daemon, retry loop, or background sender
  - COMPLETE-only doctrine unchanged
- latest proofs:
  - `$env:PYTHONPATH='src'; python -m pytest tests/test_alerting/test_telegram_alerter.py tests/test_manifest_registry/test_inventory.py tests/test_manifest_registry/test_build_order.py tests/test_manifest_registry/test_dependencies.py tests/test_manifest_registry/test_profiles.py tests/test_dag_validator/test_layer_validator.py -q`
  - `126 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 78. T11 now has an operated opt-in Telegram alert seam on `run_shadow_vps_service`

- new code truth:
  - `src/protocols/shadow_vps_service_telegram_alerting.py` now projects operated `ShadowVpsServiceEvent` values into canonical `AlertRecord`
  - `scripts/run_shadow_vps_service.py` now accepts `--telegram-alert-config-path` and `--telegram-alert-key-path`
  - when configured explicitly, the service sends bounded Telegram alerts for selected operated events (`service_started`, `shadow_day_completed`, `shadow_day_failed`, `service_stopped`)
  - every delivery attempt is audited in the existing `shadow_vps_service.events.jsonl` stream as `telegram_alert_sent` or `telegram_alert_failed`
- deliberate limit of this slice:
  - no hidden Build-10 `monitoring_runtime -> alerting` dependency
  - no daemon, retry loop, or background sender
  - Telegram failures do not crash the service
- latest proofs:
  - `$env:PYTHONPATH='src'; rtk pytest tests/test_protocols/test_shadow_vps_service_telegram_alerting.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_manifest_registry/test_dependencies.py tests/test_dag_validator/test_layer_validator.py -q`
  - `43 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 79. T11 now projects operated Telegram delivery truth into Shadow monitoring and Prometheus

- new code truth:
  - `ShadowVpsServiceState`, `ShadowVpsCampaignSummary`, and `ShadowVpsServiceMonitoringPayload` now carry the last Telegram delivery truth as `status / event_type / error`
  - `scripts/run_shadow_vps_service.py` now persists that truth on each bounded delivery attempt and rewrites the final campaign summary + monitoring artifacts after `service_stopped`
  - `src/monitoring/shadow_vps_service_monitoring.py` now exposes the same seam in payload detail and Prometheus via `v53_shadow_vps_telegram_alert_delivery_status`
- deliberate limit of this slice:
  - no Build-10 dashboard/UI wiring yet
  - no historical counter/time-series store beyond the last service-backed truth
  - no daemon/retry semantics added
- latest proofs:
  - `$env:PYTHONPATH='src'; rtk pytest tests/test_protocols/test_shadow_vps_service_telegram_alerting.py tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `17 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 80. T11 now projects Shadow Telegram delivery truth into the canonical Build-10 technical dashboard

- new code truth:
  - `scripts/run_technical_dashboard.py` now reads `telegram_alert_delivery_status / event_type / error` from `shadow_vps_service.campaign_summary.json`
  - `src/ui/technical_dashboard_view.py` now renders a dedicated Build-11 Shadow card `Telegram Alerts`
  - the rendered local artifact for `build11_live_websocket_campaign` now carries the same service-backed Telegram seam as monitoring/Prometheus
- deliberate limit of this slice:
  - no Grafana work here
  - no new alerting logic; Build-10 remains a pure projection surface
  - no historical aggregation beyond the last service-backed Telegram truth
- latest proofs:
  - `$env:PYTHONPATH='src'; rtk pytest tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_launcher.py tests/test_monitoring/test_monitoring_backend.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `77 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 81. T11 now exposes Telegram in local Shadow Grafana and persists Telegram config provenance on the operated service rail

- new code truth:
  - `src/monitoring/local_grafana_dashboard.py` now adds `Telegram Alerts` and `Telegram Alert Labels` to the local Shadow Grafana bundle
  - `ShadowLiveWebSocketConfig` now accepts `telegram_alert_config_path_ref` and `telegram_alert_key_path_ref`
  - `scripts/run_shadow_vps_service.py` now resolves Telegram config/key paths with the same precedence as other operated refs: CLI first, then `live_websocket_config`
  - `ShadowVpsServiceState`, `ShadowVpsRuntimeEvidenceBundle`, `ShadowVpsCampaignSummary`, and `ShadowVpsServiceMonitoringPayload` now carry Telegram config/key `ref/source`
  - `src/monitoring/shadow_vps_service_monitoring.py` now exposes `config_source` on `v53_shadow_vps_telegram_alert_delivery_status`
- deliberate limit of this slice:
  - no new Build-10 dashboard projection yet for Telegram config provenance
  - no hidden sender loop or retry daemon
  - local Grafana remains a Prometheus projection surface only
- latest proofs:
  - `$env:PYTHONPATH='src'; rtk pytest tests/test_monitoring/test_local_grafana_dashboard.py tests/test_monitoring/test_local_grafana_dashboard_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `21 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 82. T13 now projects the operated execution runtime bootstrap seam into canonical Shadow monitoring and Build-10

- new code truth:
  - `scripts/run_shadow_vps_service.py` now persists the useful bootstrap reconcile truth, not just `ref/status/source`: `user_data_stream_enabled`, `reconciliation_boot_executed`, `reconciliation_boot_trading_blocked`, `reconciliation_boot_circuit_breaker_tripped`, `reconciliation_boot_recovery_action`, and `reconciliation_boot_divergence_count`
  - `src/monitoring/shadow_vps_service_monitoring.py` now exposes that seam in the canonical Shadow payload and Prometheus via `v53_shadow_vps_execution_runtime_bootstrap_status`, `..._divergence_count`, and `..._trading_blocked`
  - `scripts/run_technical_dashboard.py` and `src/ui/technical_dashboard_view.py` now project the same service-backed seam into a dedicated Build-11 Shadow card `Execution Bootstrap`
- deliberate limit of this slice:
  - no new bootstrap runtime behavior
  - no daemon, retry loop, or order-submit path
  - Build-10 remains a projection surface over service truth
- latest proofs:
  - `$env:PYTHONPATH='src'; rtk pytest tests/test_monitoring/test_shadow_vps_service_monitoring.py tests/test_ui/test_technical_dashboard.py tests/test_ui/test_technical_dashboard_launcher.py tests/test_protocols/test_shadow_vps_service_launcher.py -q`
  - `56 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 83. Build-1 now enforces executable engineering guardrails with a baseline-aware repo-wide scan

- new code truth:
  - `src/smoke_bootstrap_recovery/engineering_guardrails.py` now materializes executable rules derived from `CODEX_PROMPT.md`: missing future annotations, file/function size, `print()`, bare `except`, missing annotations, and `Any`
  - `scripts/run_engineering_guardrails.py` now runs the repo-wide scan, writes an audit-ready report under `build/engineering_guardrails/`, and can refresh the accepted legacy baseline in `config/engineering_guardrails_baseline.json`
  - `run_build1_smoke()` now executes the guardrail scan as a real Build-1 sanity check through `smoke_bootstrap_recovery`, so new violations fail the foundation rail while existing legacy debt is grandfathered by baseline
- deliberate limit of this slice:
  - no repo-wide blind refactor
  - no fail-on-legacy without baseline
  - hotspots are reported, not auto-rewritten
- latest proofs:
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py --write-baseline`
  - repo-wide baseline generated over `826` Python files with `4363` accepted legacy violations
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
  - `$env:PYTHONPATH='src'; rtk pytest tests/test_smoke_bootstrap_recovery/test_engineering_guardrails.py tests/test_smoke_bootstrap_recovery/test_state_sanity.py tests/test_smoke_bootstrap_recovery/test_smoke_reporter.py -q`
  - `41 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 84. The first operated guardrail hotspot reduction now hardens `run_shadow_vps_service.py` without changing service semantics

- new code truth:
  - `scripts/run_shadow_vps_service.py` now annotates the previously untyped helpers `_append_service_event(...)` and `_write_campaign_summary(...)`
  - the dynamic script loaders now share a typed `_load_script_module(...) -> ModuleType` helper instead of duplicated untyped loader code
  - the service final CLI output is now built by `_build_service_output_lines(...)` and emitted through `_emit_output_lines(...)`, removing direct `print()` calls from the operated service script
  - `main(...)` is now decomposed into typed parser helpers `_build_argument_parser(...)`, `_add_*_arguments(...)`, and `_validate_input_root_selection(...)`
  - the previous bare `except Exception:` on execution telemetry artifact write is now explicit and re-raises with a precise runtime error
  - `_write_monitoring_artifacts(...)` now uses `_resolve_monitoring_artifact_paths(...)`, bringing that helper under the executable guardrail threshold
- deliberate limit of this slice:
  - no semantic change to the Shadow service loop
  - no decomposition yet of the three remaining large monoliths: `_write_runtime_evidence_bundle(...)`, `_write_campaign_summary(...)`, and `run_shadow_vps_service(...)`
  - file-level length debt remains open
- latest proofs:
  - focused `shadow service + monitoring` slice: `19 passed`
  - direct `python scripts/run_build9_core_smoke.py`: Build-1 `PASS`, Build-2..9 `PASS`
  - repo-wide guardrail total reduced from `4363` to `4341`
  - `scripts/run_shadow_vps_service.py` reduced from `26` guardrail violations to `4` residual violations (`FILE_TOO_LONG`, `_write_runtime_evidence_bundle`, `_write_campaign_summary`, `run_shadow_vps_service`)

## 85. The second operated hotspot reduction decomposes `campaign_summary` in `run_shadow_vps_service.py` without schema drift

- new code truth:
  - `scripts/run_shadow_vps_service.py` now builds the Shadow campaign summary through grouped typed helpers: core, live-capture, execution, regime, and info-stress fields
  - `_write_campaign_summary(...)` is now a thin orchestrator over those field-builders and no longer carries the full schema inline
  - the execution/regime/info builders were themselves split to stay below the executable guardrail threshold
- deliberate limit of this slice:
  - no change to `ShadowVpsCampaignSummary` field names, defaults, or persisted artifact paths
  - no change to service-loop control flow
  - `FILE_TOO_LONG`, `_write_runtime_evidence_bundle(...)`, and `run_shadow_vps_service(...)` remain explicit debt
- latest proofs:
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py`
  - `total_violations=4340`, `new_violations=0`
- `$env:PYTHONPATH='src'; rtk pytest tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
- `19 passed`
- direct `python scripts/run_build9_core_smoke.py`
- Build-1 `PASS`, Build-2..9 `PASS`

## 87. The fourth operated hotspot reduction collapses `run_shadow_vps_service(...)` under executable guardrails

- new code truth:
  - `scripts/run_shadow_vps_service.py` now routes the public service entrypoint through dedicated startup, loop, finalize, and output helpers instead of keeping the full operated loop inline
  - the remaining runtime-context builder debt was reduced with small extraction helpers only; no artifact schema or monitoring contract changed
  - `run_shadow_vps_service(...)` is now below the guardrail threshold and the repo is back to `new_violations=0`
- deliberate limit of this slice:
  - no service-loop semantic drift
  - no schema rename and no monitoring field loss
  - remaining debt on this file is now narrowed to `FILE_TOO_LONG`
- latest proofs:
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py`
  - `total_violations=4338`, `new_violations=0`
  - `$env:PYTHONPATH='src'; rtk pytest tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
  - `19 passed`
  - direct `python scripts/run_build9_core_smoke.py`
  - Build-1 `PASS`, Build-2..9 `PASS`

## 86. The third operated hotspot reduction decomposes `runtime_evidence_bundle` in `run_shadow_vps_service.py` without schema drift

- new code truth:
  - `scripts/run_shadow_vps_service.py` now materializes `ShadowVpsRuntimeEvidenceBundle` through grouped typed builders for `input`, `execution`, `projection`, `regime_lite`, `info_stress`, and durable artifact refs
  - the service script now centralizes `last_run` conversions through `_last_run_str/_bool/_int/_str_tuple`, removing the previous long inline field mapping
  - `_write_runtime_evidence_bundle(...)` is now a thin orchestrator and no longer carries the durable runtime schema inline
- deliberate limit of this slice:
  - no change to `ShadowVpsRuntimeEvidenceBundle` field names, defaults, or persisted artifact paths
  - no change to service-loop control flow
  - remaining explicit guardrail debt on this file is now only `FILE_TOO_LONG` and `run_shadow_vps_service(...)`
- latest proofs:
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py --write-baseline`
  - baseline refreshed to the reduced repo-wide debt level
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py`
  - `total_violations=4339`, `new_violations=0`
- `$env:PYTHONPATH='src'; rtk pytest tests/test_protocols/test_shadow_vps_service_launcher.py tests/test_monitoring/test_shadow_vps_service_monitoring.py -q`
- `19 passed`
- direct `python scripts/run_build9_core_smoke.py`
- Build-1 `PASS`, Build-2..9 `PASS`

## 88. The next operated hotspot reduction collapses `run_local_replay_shadow.py` under executable guardrails except for file split debt

- new code truth:
  - `scripts/run_local_replay_shadow.py` now routes `export_local_replay_shadow_run(...)` through typed import-context, import-bundle, runtime-bundle, day-recording, and session-materialization helpers instead of one monolithic runner body
  - the script now uses explicit typed helpers for `demo payload`, per-engine Shadow evaluations, and CLI artifact output, eliminating the prior inline `print()` and missing-annotation debt
  - the hotspot dropped from `22` file-local guardrail violations to `1`, with the only explicit residue now `FILE_TOO_LONG`
- deliberate limit of this slice:
  - no artifact schema rename
  - no LOCAL_REPLAY -> SHADOW control-flow drift
  - no change to governed sidecar names or session-summary contract
- latest proofs:
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py`
  - `total_violations=4316`, `new_violations=0`
- `$env:PYTHONPATH='src'; rtk pytest tests/test_protocols/test_local_replay_shadow_runner.py -q`
- `18 passed`
- direct `python scripts/run_build9_core_smoke.py`
- Build-1 `PASS`, Build-2..9 `PASS`

## 89. The next operated hotspot reduction fully splits `run_local_replay_shadow.py` into bounded support modules

- new code truth:
  - `scripts/run_local_replay_shadow.py` is now a thin public CLI/API facade over bounded support modules:
    - `scripts/local_replay_shadow_models.py`
    - `scripts/local_replay_shadow_engines.py`
    - `scripts/local_replay_shadow_payloads.py`
    - `scripts/local_replay_shadow_import_support.py`
    - `scripts/local_replay_shadow_session_support.py`
  - the governed `LOCAL_REPLAY -> VPS import -> SHADOW` flow kept the same exported API surface (`main`, `export_local_replay_shadow_run`, `LocalReplayShadowArtifacts`) while eliminating the last file-length debt on the original script
  - all six files are now at `0` local guardrail violations; the file-length debt is not merely moved elsewhere
- deliberate limit of this slice:
  - no artifact path rename
  - no contract drift on session summaries, runtime evidence, or upload/import sidecars
  - no behavior change on the governed Shadow rail
- latest proofs:
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py`
  - `total_violations=4315`, `new_violations=0`
- `$env:PYTHONPATH='src'; rtk pytest tests/test_protocols/test_local_replay_shadow_runner.py -q`
- `18 passed`
- direct `python scripts/run_build9_core_smoke.py`
- Build-1 `PASS`, Build-2..9 `PASS`

## 90. The next operated hotspot reduction removes CLI print debt from `run_local_lab_analysis_bundle.py`

- new code truth:
  - `scripts/run_local_lab_analysis_bundle.py` now routes all terminal emission through `_emit_local_lab_analysis_bundle_output(...)` and `_write_cli_output(...)` instead of inline `print()` calls
  - the change preserves the same operator-facing artifact paths and keeps the Local IA Lab bundle pipeline unchanged
  - file-local debt on this hotspot dropped from `30` to `2`; only `FILE_TOO_LONG` and `FUNCTION_TOO_LONG main` remain
- deliberate limit of this slice:
  - no change to Local IA Lab artifact schema
  - no change to the chained review/calibration/replay/monitoring pipeline
  - no broad refactor of the giant `main(...)` yet
- latest proofs:
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py`
  - `total_violations=4287`, `new_violations=0`
  - `$env:PYTHONPATH='src'; rtk pytest tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `7 passed`

## 91. The next operated hotspot reduction decomposes `run_local_lab_analysis_bundle.py` into bounded post-review phases

- new code truth:
  - `scripts/run_local_lab_analysis_bundle.py` no longer keeps the full Local IA Lab chain inside one giant `main(...)`
  - the launcher now orchestrates bounded helpers for review dispatch, secondary reviews, edge/proof, release/replay, monitoring, and summary emission
  - function-level guardrail debt on this hotspot is cleared; the remaining explicit debt is only `FILE_TOO_LONG`
- deliberate limit of this slice:
  - no Local IA Lab artifact/schema drift
  - no change to governed review/calibration/replay/monitoring outputs
  - no broad cleanup outside this launcher hotspot
- latest proofs:
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py`
  - `total_violations=4286`, `new_violations=0`
  - `$env:PYTHONPATH='src'; rtk pytest tests/test_local_replay_runtime/test_local_lab_analysis_bundle_launcher.py -q`
  - `7 passed`
- `python scripts/run_build9_core_smoke.py`
- Build-1 `PASS`, Build-2..9 `PASS`

## 92. The next operated hotspot reduction removes inline CLI print debt from `run_technical_dashboard.py`

- new code truth:
  - `scripts/run_technical_dashboard.py` now routes terminal output through `_emit_technical_dashboard_output(...)` instead of inline `print()` calls
  - the change preserves the same artifact paths and HTML payload outputs
- deliberate limit of this slice:
  - no dashboard schema change
  - no behavior change in the projection pipeline
  - no cleanup outside this launcher hotspot
- latest proofs:
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py`
  - `total_violations=4279`, `new_violations=0`
  - `$env:PYTHONPATH='src'; rtk pytest tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `10 passed`

## 93. The next operated hotspot reduction decomposes `_apply_shadow_service_metadata` in `run_technical_dashboard.py`

- new code truth:
  - `scripts/run_technical_dashboard.py` now routes the Shadow service metadata projection through bounded helpers (`_build_shadow_projection_*`)
  - no schema drift; the same `ShadowProjection` fields are populated
- deliberate limit of this slice:
  - no dashboard schema change
  - no behavior change in the projection pipeline
  - no cleanup outside this launcher hotspot
- latest proofs:
  - `$env:PYTHONPATH='src'; python scripts/run_engineering_guardrails.py`
  - `total_violations=4278`, `new_violations=0`
  - `$env:PYTHONPATH='src'; rtk pytest tests/test_ui/test_technical_dashboard_launcher.py -q`
  - `10 passed`

## 94. The next operated hotspot reduction splits `run_shadow_vps_service.py` into bounded support modules

- new code truth:
  - `scripts/shadow_vps_service_projection_support.py` now houses runtime evidence projection helpers
  - `scripts/shadow_vps_service_campaign_support.py` now houses campaign summary projection helpers
  - `scripts/shadow_vps_service_monitoring_support.py` now houses monitoring artifact helpers and file emission
  - `scripts/run_shadow_vps_service.py` now imports those helpers and adds `scripts/` to `sys.path`
- deliberate limit of this slice:
  - no service-loop semantic change
  - no artifact/schema drift
  - no cleanup outside this hotspot
- latest proofs:
  - `python scripts/run_engineering_guardrails.py`
  - `total_violations=4278`, `new_violations=0`

## 95. The next operated hotspot reduction extracts Shadow VPS service dataclass models

- new code truth:
  - `scripts/shadow_vps_service_models.py` now defines `ShadowVpsServiceMonitoringConfig`, `ShadowVpsServiceRuntimeContext`, and `ShadowVpsCycleSelection`
  - `scripts/run_shadow_vps_service.py` now imports those models
- deliberate limit of this slice:
  - no service-loop semantic change
  - no artifact/schema drift
  - no cleanup outside this hotspot
- latest proofs:
  - `python -m py_compile scripts/run_shadow_vps_service.py scripts/shadow_vps_service_projection_support.py scripts/shadow_vps_service_campaign_support.py scripts/shadow_vps_service_monitoring_support.py scripts/shadow_vps_service_models.py`

## 96. The next operated hotspot reduction extracts Shadow VPS runtime context helpers

- new code truth:
  - `scripts/shadow_vps_service_context_support.py` now hosts runtime dir resolution + context construction helpers
  - `scripts/run_shadow_vps_service.py` now imports those helpers and injects the launcher loader
- deliberate limit of this slice:
  - no service-loop semantic change
  - no artifact/schema drift
  - no cleanup outside this hotspot
- latest proofs:
  - `python -m py_compile scripts/run_shadow_vps_service.py scripts/shadow_vps_service_context_support.py`

## 97. The next operated hotspot reduction extracts Shadow VPS cycle selection helpers

- new code truth:
  - `scripts/shadow_vps_service_cycle_support.py` now hosts cycle selection + idle/prepare helpers
  - `scripts/run_shadow_vps_service.py` now imports those helpers and passes explicit hook callables
- deliberate limit of this slice:
  - no service-loop semantic change
  - no artifact/schema drift
  - no cleanup outside this hotspot
- latest proofs:
  - `python -m py_compile scripts/run_shadow_vps_service.py scripts/shadow_vps_service_cycle_support.py`

## 98. The next operated hotspot reduction extracts Shadow VPS execution helpers

- new code truth:
  - `scripts/shadow_vps_service_execution_support.py` now hosts daily orchestrator, state application, telemetry, success, and failure helpers
  - `scripts/run_shadow_vps_service.py` now imports those helpers and passes explicit hook callables
- deliberate limit of this slice:
  - no service-loop semantic change
  - no artifact/schema drift
  - no cleanup outside this hotspot
- latest proofs:
  - `python -m py_compile scripts/run_shadow_vps_service.py scripts/shadow_vps_service_execution_support.py`

## 99. The next operated hotspot reduction extracts Shadow VPS runtime loop helpers

- new code truth:
  - `scripts/shadow_vps_service_runtime_support.py` now hosts finalize + main loop helpers and output emission
  - `scripts/run_shadow_vps_service.py` now imports those helpers and injects callables
- deliberate limit of this slice:
  - no service-loop semantic change
  - no artifact/schema drift
  - no cleanup outside this hotspot
- latest proofs:
  - `python -m py_compile scripts/run_shadow_vps_service.py scripts/shadow_vps_service_runtime_support.py`


---

## Source: docs/production_deployment_plan/10_DECISIONS_REQUIRED.md

# Décisions humaines requises avant chaque phase

> **Objectif** — Lister toutes les décisions structurantes à prendre par l'humain **avant** que l'agent codeur démarre, et **avant chaque gate** de phase. Aucune décision implicite. Aucune décision laissée à l'agent codeur.
>
> **Format** — Chaque décision a : la question, les options, l'option par défaut recommandée, l'impact si on choisit autre chose, et l'endroit où la décision doit être tracée (fichier signé).

---

## 1. Décisions Phase 0 (avant tout code)

### D-01 — Exchange cible

**Question** : Sur quel exchange déployer en MICRO_LIVE et LIVE ?

**Options** :
- **A. Binance Spot** (recommandé)
- **B. Kraken Spot**
- **C. Coinbase Pro / Advanced Trade**
- **D. Multi-exchange (Binance + Kraken en parallèle)**

**Recommandation** : **A. Binance Spot**

**Justification** :
- Liquidité maximale sur les paires halal whitelistables (BTC, ETH, large caps spot)
- API et WebSocket les plus matures et documentés
- Fees compétitives (0.10 % par défaut, 0.075 % avec BNB discount, 0.05 % VIP)
- Testnet disponible pour validation P0-1
- Support de tous les types d'order utiles (LIMIT, MARKET, STOP_LOSS_LIMIT)

**Impact si autre choix** :
- Kraken : meilleur côté régulation EU, mais liquidité plus faible et fees plus élevées (0.16 % maker / 0.26 % taker base)
- Coinbase : régulation US-friendly mais fees très élevées (0.40 % retail) → kill l'edge à 10 k$
- Multi-exchange : double l'effort P0-1 (~2x sessions code), gain marginal à 10 k$

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § exchange

---

### D-02 — École fiqh / référence sharia

**Question** : Quelle école juridique / fatwa de référence utiliser pour les décisions halal ?

**Options** :
- **A. AAOIFI** (Accounting and Auditing Organization for Islamic Financial Institutions) — standard institutionnel
- **B. Fatwa Mufti Taqi Usmani** sur la crypto (la plus citée)
- **C. Sheikh Joe Bradford** (vulgarisation crypto US)
- **D. Mufti Faraz Adam** (spécialiste crypto/DeFi UK)
- **E. Ton propre conseil local + revue par tiers annuelle**

**Recommandation** : **B + E** — base AAOIFI/Usmani, validation tiers annuelle

**Justification** :
- AAOIFI/Usmani = base la plus défendable et documentée
- Revue annuelle par tiers crypto-spécialiste = défense en profondeur
- Pas besoin d'avoir un avis "définitif" sur tout — la posture conservative suffit pour 10 k$ à condition d'être documentée

**Impact** : la décision conditionne la whitelist d'assets, la stablecoin policy, le traitement des airdrops. À ne pas changer en cours de route sans purification rétroactive.

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § sharia + `config/sharia/policy_v1.yml` (référence en commentaire)

---

### D-03 — Stablecoin policy

**Question** : Quel stablecoin utiliser comme contrepartie principale et avec quel régime de purification ?

**Options** :
- **A. USDT** (Tether) — liquide, mais réserves opaques, papier commercial intérêt-bearing
- **B. USDC** (Circle) — backed T-Bills US (intérêt indirect), plus transparent
- **C. DAI** (MakerDAO) — over-collateralisé crypto, stability fee = riba structurel
- **D. PYUSD** (PayPal/Paxos) — récent, similaire USDC
- **E. USDT avec purification calculée mensuellement**
- **F. Pas de stablecoin — uniquement quote BTC** (sortie en BTC, pas en stable)

**Recommandation** : **E. USDT + purification mensuelle calculée**

**Justification** :
- Liquidité USDT > USDC sur Binance Spot
- Aucun stable n'est 100 % halal selon les juristes les plus stricts → choisir le plus liquide et purifier
- L'approche "purification calculée" est documentée par AAOIFI pour les zones grises
- Option F (BTC quote) éviterait le débat mais réduit drastiquement l'univers tradable et augmente la vol du portefeuille

**Impact** :
- Influence directement P0-2 (`stablecoin_policy.py` + `purification_calculator.py`)
- Détermine la base mensuelle à donner en charity
- Si tu changes plus tard, il faut re-purifier rétroactivement

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § stablecoin + `config/sharia/stablecoin_policy.yml`

---

### D-04 — VPS confirmé

**Question** : VPS Hetzner CX43 (proposé) ou autre ?

**Options** :
- **A. Hetzner CX43** (recommandé) : 8 vCPU, 16 GB RAM, 160 GB SSD, 20 TB traffic, €12.49/mois, EU
- **B. Hetzner CX42 ou plus petit** (économie marginale)
- **C. Contabo / Vultr / DigitalOcean** (alternatives EU/global)
- **D. Multi-VPS avec failover actif** (overkill à 10 k$, ~2x coût + complexité)
- **E. Single active VPS + vue flotte passive multi-VPS** (option future) : plusieurs VPS peuvent être résumées dans une vue `health/status/artifact`, mais le trading reste porté par une seule VPS active à la fois

**Recommandation** : **A. Hetzner CX43** aujourd'hui. `E` reste compatible plus tard si l'objectif est seulement une vue flotte read-only.

**Justification** :
- Marge confortable sur ressources (5x marge RAM, 4x marge disque vs estimation V5.3)
- Coût annuel = 1.6 % du capital, raisonnable
- Localisation EU = latence acceptable vers Binance + RGPD compliance pour logs personnels
- Single active VPS suffisant à 10 k$ : kill switch + reconciliation gèrent les pannes

**Impact** :
- CX42 (4 vCPU / 8 GB) : risque de saturation lors des calibrations locales si on les fait sur le VPS — mais on ne les fait PAS sur le VPS (cf. `12_LOCAL_LAB_VS_VPS_SEPARATION.md`). Donc OK marginalement, mais la marge est moins confortable.
- Multi-VPS avec failover actif : ne se justifie qu'à >100 k$ et avec un trader full-time
- Vue flotte passive multi-VPS : reste acceptable plus tôt si elle reste purement read-only et ne remplace pas le drill-down sur la VPS concernée

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § infra

---

### D-05 — Capital initial MICRO_LIVE

**Question** : Quel capital pour démarrer Phase 3 (MICRO_LIVE) ?

**Options** :
- **A. 200 USD** (2 % du target)
- **B. 500 USD** (5 % du target, recommandé)
- **C. 1000 USD** (10 % du target)

**Recommandation** : **B. 500 USD**

**Justification** :
- Suffisamment grand pour générer ≥ 30 trades en 30 jours sur des positions ≥ 100 USD (respectant min_notional Binance avec marge)
- Suffisamment petit pour qu'une perte totale (-100 % très improbable, -20 % vraiment plausible si bug) soit absorbée sans casser la trajectoire (= 100 USD perte = 1 % du target)
- 200 USD = trop faible : trades < 50 USD donc edge dilué par fees fixes
- 1000 USD = trop élevé : si bug, perte de 200 USD avant d'avoir validé la stabilité

**Impact** :
- Détermine la durée minimum MICRO_LIVE (besoin de 30+ trades)
- Influence le `capital_cap` dans la config runtime

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § microlive

---

### D-06 — Plan de scaling Phase 4 LIVE

**Question** : Comment monter en capital après MICRO_LIVE validé ?

**Options** :
- **A. Saut direct 500 → 10000** (rapide mais risqué)
- **B. Paliers 500 → 2000 → 5000 → 10000** avec 2 semaines minimum entre chaque
- **C. Paliers continus +20 % par semaine**

**Recommandation** : **B**

**Justification** : 4 paliers permettent de détecter les pathologies de scale (ex : impact orderbook qui apparaît à 5000 et n'existait pas à 2000) avant que tout le capital soit exposé.

**Impact** : prolonge le temps avant capital cible (4 × 2 semaines = ~2 mois après G3).

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § scaling

---

### D-07 — Qui valide les gates SHADOW (G2.1, G2.2, G2.3) ?

**Question** : Qui signe les gates humains ? Toi seul, ou peer-review obligatoire ?

**Options** :
- **A. Toi seul** (recommandé pour 10 k$ personnel)
- **B. Toi + 1 peer technique** (ami dev qui revoit la métriques)
- **C. Toi + audit charia** (pour les questions halal uniquement)

**Recommandation** : **A** pour les aspects techniques + **C** pour audit halal annuel

**Justification** :
- À 10 k$ personnel, le coût d'un peer review formel est disproportionné
- Mais l'audit halal annuel par un tiers spécialisé (mufti crypto) reste recommandé pour la pureté du capital

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § gates

---

### D-08 — Qui produit et signe les artefacts de calibration ?

**Question** : Le Local IA Lab produit les artefacts. Qui signe pour usage VPS ?

**Options** :
- **A. Signature humaine manuelle** : tu lis l'artefact, tu valides, tu signes (clé GPG ou simple `signed_by: <name> <date>` dans le YAML)
- **B. Signature automatique** si critères de validation atteints
- **C. Hybride** : auto-validation des seuils déjà connus, signature manuelle des nouveaux

**Recommandation** : **A** pour Phase 0/1, **C** pour les recalibrations trimestrielles

**Justification** : la première calibration doit être lue avec attention car elle conditionne toutes les phases suivantes. Les recalibrations ultérieures peuvent être plus automatisées tant que les critères sont stables.

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § calibration_signing

---

## 2. Décisions Phase 1 (avant code)

### D-09 — Engine C/D : Option A ou B ?

**Question** : Pour `P0-5`, on choisit l'Option A (feature flag, désactivés en MICRO_LIVE) ou Option B (refactor complet) ?

**Options** :
- **A. Feature flag** : 0.25 session code, Engine C/D off en MICRO_LIVE, refactor reporté à post-LIVE
- **B. Refactor complet** : 1-3 sessions code, Engine C/D actifs en MICRO_LIVE

**Recommandation** : **A. Feature flag**

**Justification** : à 10 k$, 2 engines (A + B) suffisent. Le refactor C/D peut attendre d'avoir des données live qui justifieraient l'investissement.

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § engines

---

### D-10 — V37 bricks : on les fait avant ou après SHADOW ?

**Question** : T12 (Gatekeeper central) et T13 (Info stress monitor) : avant SHADOW (Phase 2) ou après ?

**Options** :
- **A. Avant SHADOW** : tranches T12+T13 dans la fin de Phase 1bis
- **B. Après SHADOW** : seulement après G2.3 si on juge nécessaire
- **C. Skip totalement** si V5.3 suffit

**Recommandation** : **A. Avant SHADOW**

**Justification** :
- T12 (Gatekeeper) ajoute de l'audit trail = précieux pour la review SHADOW
- T13 (Info stress monitor) protège contre les flash crashes pendant SHADOW (et oui, on shadow contre du marché réel donc le risque existe... même sans capital exposé, un mauvais test révèle peu)

**Impact** : ajoute ~1 session code à Phase 1bis. Décale Phase 2 de ~1 semaine.

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § v37_bricks_timing

---

## 3. Décisions Phase 2 (avant SHADOW)

### D-11 — Métriques de validation SHADOW : valeurs cibles

**Question** : Quels seuils chiffrés pour valider chaque gate SHADOW ? (Phase 0 doit produire les valeurs calibrées, mais l'humain doit les valider.)

**Champs à définir** (valeurs proposées indicatives) :
- **Sharpe simulé minimum** pour passer chaque palier : 0.5 / 0.6 / 0.7 (S2.1 / S2.2 / S2.3) ?
- **Max DD simulé maximum** : 15 % / 13 % / 12 % ?
- **Nb décisions cumulées minimum** : 30 / 60 / 100 ?
- **Uptime minimum** : 99 % / 99 % / 99.5 % ?

**Recommandation** : commencer avec les chiffres ci-dessus, ajustables en Phase 0 selon ce que la calibration produit comme bornes réalistes.

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § shadow_thresholds (et `config/calibration_v1.yml` § shadow_gates)

---

### D-12 — Comportement humain pendant SHADOW

**Question** : Combien de temps tu t'engages à monitorer SHADOW chaque jour ?

**Options** :
- **A. 5 min/jour** (lecture rapide du résumé matin)
- **B. 15 min/jour** (incl. revue des décisions)
- **C. 30 min/jour ou plus**

**Recommandation** : **B**, avec 1h hebdomadaire pour la revue de fin de palier.

**Important** : l'engagement doit être réaliste. Si tu sais que tu ne pourras pas tenir 30 min/jour, choisis 5 min/jour et n'autorise pas plus de signaux/jour à générer.

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § human_engagement

---

## 4. Décisions Phase 3 (avant MICRO_LIVE)

### D-13 — Pré-engagement écrit "anti-panique"

**Question** : Quelles règles tu t'imposes par écrit pour éviter d'intervenir manuellement par panique ?

**Template** :
```
Je m'engage à NE PAS :
- Modifier le code en LIVE pendant un drawdown
- Liquider manuellement une position sans valider via le kill switch
- Augmenter le capital plus vite que le plan de scaling D-06
- Désactiver le daily P&L breaker pour "voir ce qui se passe"

Je m'engage à :
- Lire le résumé matinal chaque jour ouvré
- Respecter le plan de scaling D-06
- Convoquer une revue formelle si DD > 5 % en 1 jour
```

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § pre_engagement_personal (rédigé à la main, signé)

---

### D-14 — Plan d'urgence

**Question** : Que fais-tu si Hetzner tombe pendant 24h ?

**Options proposées** :
- **A. Rien** : le système est en pause naturelle, kill switch s'active au reboot
- **B. Migration manuelle** vers un VPS de backup déjà préparé
- **C. Liquidation manuelle** depuis l'interface web Binance

**Recommandation** : **A** par défaut, avec doc de B en backup au cas où la panne dure > 48h.

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § emergency_plan

---

## 5. Décisions Phase 4 (avant LIVE)

### D-15 — Fréquence de revue mensuelle

**Question** : Combien de temps par mois pour la revue obligatoire ?

**Options** : 30 min / 1h / 2h

**Recommandation** : **1h/mois minimum** + 1h supplémentaire en cas d'incident.

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § monthly_review

---

### D-16 — Recalibration trimestrielle : qui, comment ?

**Question** : Qui lance la recalibration et selon quel rythme ?

**Recommandation** :
- **Rythme** : tous les 90 jours en fixe + déclenchement exceptionnel si Sharpe rolling 30j divise par 2 vs backtest
- **Procédure** : Local IA Lab → nouveau backtest sur N+90j de données → nouvel artefact → revue humaine → signature → déploiement VPS via méthode prouvée
- **Versioning** : `calibration_v1.json`, `calibration_v2.json`, ... toujours conservés pour audit

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § recalibration

---

### D-17 — Tax export

**Question** : On code un module d'export tax CSV ou pas ?

**Options** :
- **A. Oui** : export annuel automatique au format de la juridiction (FR, DE, etc.)
- **B. Non** : export manuel via interface Binance une fois par an

**Recommandation** : **B** pour Phase 4 V1, **A** si jugé nécessaire après 1 an.

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § tax_export

---

### D-18 — Audit halal annuel

**Question** : Qui réalise l'audit halal annuel ?

**Options** :
- **A. Mufti spécialisé crypto** (Joe Bradford, Faraz Adam, ou équivalent local) — coût ~200-500 USD/an
- **B. Auto-audit basé sur policy versioning** — gratuit mais moins défendable
- **C. Skip jusqu'à ce que le capital justifie le coût (> 50 k$)**

**Recommandation** : **A** dès Phase 4 si le budget le permet, sinon **B** + **A** en Phase 4 V2.

**À tracer dans** : `DECISIONS_FROZEN_<date>.md` § halal_audit

---

## 6. Récapitulatif — toutes les décisions

| ID | Décision | Phase | Statut attendu avant phase |
|---|---|---|---|
| D-01 | Exchange cible | 0 | Prise et signée |
| D-02 | École fiqh | 0 | Prise et signée |
| D-03 | Stablecoin policy | 0 | Prise et signée |
| D-04 | VPS confirmé | 0 | Prise et signée |
| D-05 | Capital MICRO_LIVE | 0 | Prise et signée |
| D-06 | Plan scaling LIVE | 0 | Prise et signée |
| D-07 | Qui valide les gates | 0 | Prise et signée |
| D-08 | Qui signe calibrations | 0 | Prise et signée |
| D-09 | Engine C/D Option A/B | 1 | Prise avant T7/T8 |
| D-10 | V37 bricks timing | 1bis | Prise avant T12/T13 |
| D-11 | Seuils SHADOW | 2 | Prise avant SHADOW |
| D-12 | Engagement humain SHADOW | 2 | Prise avant SHADOW |
| D-13 | Pré-engagement anti-panique | 3 | Signée avant MICRO_LIVE |
| D-14 | Plan d'urgence | 3 | Documentée avant MICRO_LIVE |
| D-15 | Revue mensuelle | 4 | Engagement signé |
| D-16 | Recalibration trimestrielle | 4 | Procédure documentée |
| D-17 | Tax export | 4 | Décidée |
| D-18 | Audit halal annuel | 4 | Décidée |

**18 décisions** au total. **8 dès Phase 0** (avant tout code).

---

## 7. Format du fichier `DECISIONS_FROZEN_<date>.md`

Template attendu :

```markdown
# Decisions Frozen — V5.3 production deployment
**Date** : 2026-XX-XX
**Signé par** : <nom>
**Version** : 1

## Phase 0 — Décisions structurantes

### D-01 Exchange cible
Choix : Binance Spot
Justification : (brève)

### D-02 École fiqh
Choix : AAOIFI + Usmani, validation tiers annuelle
Justification : (brève)

[...etc pour D-01 à D-08...]

## Phase 1 — Décisions de code

[...]

## Phase 2 — Décisions SHADOW

[...]

## Phase 3 — Décisions MICRO_LIVE

[...]

## Phase 4 — Décisions LIVE

[...]

---

**Signature** : ___________ (date : ___________)
```

Ce fichier doit être committé dans le repo (`docs/decisions/`) avant le démarrage de chaque phase.

---

**Suite logique** : `11_DYNAMIC_THRESHOLDS_CATALOG.md` — catalogue exhaustif des seuils à calibrer.


---

## Source: docs/production_deployment_plan/18_CODE_VS_PLAN_AUDIT_AND_WORK_PLAN.md

# Code vs Plan Audit — Angles morts & Plan de travail critique

> **Date** : 2026-04-13. Auteur : Opus (planification) + Sonnet (audit code).
>
> **Niveau** : production-safe / quant PhD / trader senior PhD / PhD algebra / PhD fintech / PhD developer.
>
> **Méthode** : audit lecture seule de `src/` + `tests/` contre l'ensemble des MD `00 → 17A`.
> Le repo gagne contre le MD. Aucun code modifié par ce fichier.

---

## 0. Executive Summary

**Constat principal** : l'état réel du code est **bien plus avancé** que ce que les MD de planification décrivaient comme "future target" ou "partial". L'agent codeur a implémenté la majorité des P0/P1 entre les sessions. Le système est à **~70-75 % de prêt pour SHADOW**, pas 62 % comme estimé en `16_...`.

**Mais** : 5 catégories d'angles morts critiques ont été identifiés qui **ne sont pas dans le plan actuel** et qui peuvent compromettre la production.

### Verdict par pilier (état réel 2026-04-13)

| Pilier | Plan disait | Réalité code | Écart |
|---|---|---|---|
| `venue_adapters/binance_spot/` | future target | **13 fichiers complets** | +++ |
| `sharia_compliance/` | future target | **16 fichiers + 9 tests** | +++ |
| `calibration_methods/` | planifié (13-A→13-G) | **8 fichiers : DSR, POT/GPD, bootstrap, walkforward, stationarity, multiple_testing** | +++ |
| `calibration_loader/` | W2 (fermée) | **Complet + intégré fee gate + regime + daily breaker** | = |
| `fee_aware_edge_gate.py` | partial | **Complet (100L, calibration-aware)** | ++ |
| `regime_classifier/regime_lite.py` | partial | **Complet + calibration seam** | ++ |
| `risk_backbone/loss_budgeter/daily_pnl_breaker.py` | partial | **Complet + calibration seam** | ++ |
| `execution_backbone/gatekeeper/gatekeeper.py` | partial | **Complet (24 KB, intègre sharia)** | ++ |
| `spread_guard.py`, `slippage_model.py` | partial | **Complets** | ++ |
| `alerting/telegram_alerter.py` | partial | **Complet** | ++ |
| Engine C/D unit tests | "7+7 tests" | **Imports cassés** (3 fichiers) | --- |
| `rate_limiter.py` (THR-X03) | future target | **Toujours absent** | = |
| PSR / KS / Energy / Hansen SPA | planifiés dans 14 | **Non visibles dans calibration_methods/** | --- |
| Linux VPS deployment scripts | implicite dans plan | **Inexistants (tout en Windows PowerShell)** | --- |

---

## 1. Bugs bloquants immédiats

### BUG-1 — Engine C/D imports cassés (P0 pour la confiance en test)

**Fichiers** :
- `tests/test_engines/test_engine_c/test_engine_c.py:5`
- `tests/test_engines/test_engine_d/test_engine_d.py:5`
- `tests/test_engines/test_engine_d/test_engine_d_bs104_regression.py:11`

**Erreur** :
```python
from engine_c import EngineCDecision, EngineCInput, run_engine_c  # CASSÉ
from engine_d import EngineDDecision, EngineDInput, run_engine_d  # CASSÉ
```

**Correction** :
```python
from engines.engine_c import EngineCDecision, EngineCInput, run_engine_c
from engines.engine_d import EngineDDecision, EngineDInput, run_engine_d
```

**Impact** : les tests unitaires de C et D ne tournent pas. Seuls les runtime tests (`test_engine_c_runtime.py`, `test_engine_d_runtime.py`) fonctionnent car ils utilisent le bon préfixe.

**Acteur** : **Sonnet** — fix trivial (3 lignes), haute priorité.

---

## 2. Angles morts par dimension

### 2.1 Trading — 5 angles morts

#### AS-T1 — Rate limiter actif absent

**Constat** : `rest_client.py` **parse** les rate limits depuis `exchangeInfo` (ligne 260-266) mais il n'y a **pas d'enforcement actif** (pas de token bucket, pas de `rate_limiter.py`). Le plan identifiait `THR-X03` comme "future target" (11A) — toujours vrai.

**Risque production** : Binance interdit IP sur dépassement quota (1200 req/min, 50 orders/10s). Sans token bucket, le système peut se faire bannir en conditions de marché agitées (retry storm sur erreur, reconciliation urgente).

**Acteur** : **Sonnet** — créer `src/venue_adapters/binance_spot/rate_limiter.py`, token bucket simple, intégrer dans `rest_client.py`.

#### AS-T2 — Aucune preuve testnet réelle

**Constat** : `test_integration_testnet.py` planifié dans `03_GAPS_P0.md` n'existe pas. Le file 17A montre Shadow tournant sur réseau réel (authenticated) mais **sans test structuré** contre le testnet Binance.

**Risque** : le Binance adapter n'a jamais soumis un ordre réel au testnet. Les bugs de serialization, d'auth, de timing peuvent exister et ne se révèleront qu'en live.

**Acteur** : **Sonnet** — créer `tests/test_venue_adapters/test_integration_testnet.py` avec au moins : auth, order submit → cancel, balance query.

#### AS-T3 — Partial fill handling non spécifié

**Constat** : `order_translator.py` gère les ordres mais aucune trace de gestion des **partial fills** dans la chaîne execution_backbone → risk_backbone. Si Binance remplit 60 % d'un ordre :
- Le 40 % restant est-il annulé automatiquement ?
- Est-il géré comme une position partielle ?
- Le moteur engine est-il notifié ?

**Risque** : positions orphelines, capital bloqué, double comptage en reconciliation.

**Acteur** : **Opus** — spec dans un nouveau MD `19_PARTIAL_FILL_HANDLING.md` avant que Sonnet code. Décision humaine requise (D-19 à ajouter dans `10_...`).

#### AS-T4 — Ordre de démarrage du système non documenté

**Constat** : plusieurs composants dépendent l'un de l'autre au boot (calibration_loader → engine → gatekeeper → venue_adapter → execution_runtime). Aucun document ne spécifie l'**ordre de démarrage** ni les vérifications de prêt-à-trader ("readiness checks").

**Risque** : le système démarre mais un composant est en état invalide (calibration non chargée, WS non connecté), ce qui peut entraîner un trade avec des thresholds par défaut.

**Acteur** : **Opus** — ajouter spec readiness sequence dans `07_PHASE_PLAN_0_TO_4.md` ou nouveau MD.

#### AS-T5 — Idempotency UUIDv5 non standard

**Constat** : `order_translator.py:23-26` implémente `build_binance_client_order_id` via `f"v53_{engine_id}_{intent_id}"` (truncated, not UUIDv5). Le plan `03_GAPS_P0.md` spécifiait explicitement **"UUIDv5 sur intent_id"**. Si l'implémentation est juste une f-string tronquée, des collisions sont possibles.

**Acteur** : **Sonnet** — vérifier l'implémentation exacte de `build_binance_client_order_id` et corriger si non-UUIDv5.

---

### 2.2 Quant — 5 angles morts

#### AS-Q1 — `ce_min` et `delta_safe` absents du catalogue de calibration

**Constat** : chaque engine runner (A/B/C/D) a des valeurs hardcodées :
- Engine A : `ce_min=0.0001`, `delta_safe=0.0005`
- Engine B : `ce_min=0.0002`, `delta_safe=0.0008`
- Engine C : `ce_min=0.00015`, `delta_safe=0.0005`
- Engine D : `ce_min=0.00012`, `delta_safe=0.0005`

Ces valeurs **ne sont pas dans `11_DYNAMIC_THRESHOLDS_CATALOG.md`** (catalogue actuel : THR-E01 à THR-I04). Elles ne sont donc pas calibrées via backtest ni validées via shadow. Ce sont les seuils d'edge minimum **les plus critiques** du système — et ils ne sont pas dans le catalogue.

**Risque** : si les conditions de marché changent (fees augmentent, spread s'élargit), ces seuils seront sous-calibrés.

**Acteur** : **Opus** — ajouter `THR-E03` (ce_min par engine), `THR-E04` (delta_safe par engine) dans `11_DYNAMIC_THRESHOLDS_CATALOG.md`, avec méthode de calibration dans `13_CALIBRATION_METHODS.md`.

#### AS-Q2 — PSR, KS test, Energy distance, Hansen SPA absents du code

**Constat** : `14_SHADOW_GATE_MATH.md` spécifie des tests requis pour les gates :
- PSR (Probabilistic Sharpe Ratio) — **absent** de `calibration_methods/`
- KS 2-sample test — **absent**
- Energy distance (Székely-Rizzo) — **absent**
- Hansen SPA test — **absent**
- Mann-Kendall trend test — **absent**

`calibration_methods/` a : `dsr.py`, `pot_gpd.py`, `bootstrap.py`, `walkforward.py`, `stationarity.py`, `multiple_testing.py`. Mais pas les 5 tests gates.

**Risque** : quand le premier gate G2.1 (1m→2m) arrive, aucun code ne calcule les critères du rapport. Le gate ne peut pas être produit.

**Acteur** : **Sonnet** — implémenter `calibration_methods/psr.py`, `calibration_methods/ks_test.py`, `calibration_methods/energy_distance.py`, `calibration_methods/hansen_spa.py`, `calibration_methods/mann_kendall.py`. Spec fournie dans `14_...`.

#### AS-Q3 — `risk_runtime.py` drawdown thresholds hardcodés sans calibration seam

**Constat** : `src/risk_backbone/risk_runtime.py:57-58` :
```python
drawdown_warning_threshold_pct: float = 0.02
drawdown_observe_threshold_pct: float = 0.04
```
Ces valeurs ne sont reliées à **aucun `threshold_id`** du catalogue, et `risk_runtime.py` n'importe pas `calibration_loader`. Ce sont des `Field(default=...)` Pydantic qui seront utilisés si rien ne les écrase.

**Risque** : si le capital réel perd 2% en une journée, le système observe mais ne breake pas — parce que `daily_pnl_breaker.py` (qui a un seam) et `risk_runtime.py` (qui n'en a pas) peuvent avoir des seuils divergents.

**Acteur** : **Sonnet** — ajouter calibration seam dans `risk_runtime.py` pour `drawdown_warning` et `drawdown_observe`. Mapper vers `THR-R01`/`THR-R02` ou créer `THR-W01`/`THR-W02`.

#### AS-Q4 — DSR formula : vérification du terme d'ajustement multi-essais

**Constat** : `calibration_methods/dsr.py` utilise `from statistics import NormalDist` (stdlib Python). La formule DSR de Bailey-López de Prado 2014 nécessite :
$$\text{SR}^* = \sqrt{V[\widehat{\text{SR}}]} \cdot \left((1-\gamma_E)\Phi^{-1}(1-1/N) + \gamma_E\Phi^{-1}(1-1/(Ne))\right)$$
avec la constante d'Euler-Mascheroni $\gamma_E = 0.5772$.

**Vérification nécessaire** : est-ce que `dsr.py` implique ce terme $\text{SR}^*$ correctement ? Si N=1 (pas de multi-essais), la formule se simplifie, mais pour N>1 (multi-engine), l'ajustement est critique.

**Acteur** : **Sonnet** — ajouter un test `tests/test_calibration_methods/test_dsr_multiengine.py` qui valide le résultat DSR pour N=4 contre le résultat attendu du paper (Bailey-López de Prado 2014, Table 1).

#### AS-Q5 — `shadow_runtime.py` : `max_allowed_ce_net_drop: 0.0005` hardcodé

**Constat** : `src/protocols/shadow_runtime.py:554` a un seuil hardcodé non présent dans `11_...`.

**Acteur** : **Opus** — ajouter `THR-S06` (max_ce_net_drop_shadow) dans `11_...` et méthode de calibration dans `13_...`. **Sonnet** — ajouter calibration seam dans `shadow_runtime.py`.

---

### 2.3 Code — 5 angles morts

#### AS-C1 — Engine C/D imports cassés (déjà listé en BUG-1)

Cf. § 1. Fix immédiat Sonnet.

#### AS-C2 — `calibration_methods/` sans tests suffisants

**Constat** : les implémentations PhD-level dans `calibration_methods/` (`pot_gpd.py`, `dsr.py`, `bootstrap.py`, `walkforward.py`, `stationarity.py`) sont du code qui ne doit jamais échouer silencieusement — car il produit les artefacts qui pilotent le trading. Aucune trace de tests de validation mathématique (contre des exemples connus du paper).

**Risque** : une erreur de signe dans `dsr.py`, un mauvais sens de l'IC dans `pot_gpd.py` → calibration fausse → seuil mal calibré → perte.

**Acteur** : **Sonnet** — créer `tests/test_calibration_methods/` avec cas de validation vs valeurs connues des papers pour : DSR (Bailey-López de Prado table 1), POT/GPD (Coles 2001 exemple), bootstrap IC (série i.i.d. dont la distribution est connue).

#### AS-C3 — `rate_limiter.py` absent (déjà listé en AS-T1)

Cf. AS-T1.

#### AS-C4 — Tests coverage de `calibration_methods/` non mesurée

**Constat** : `calibration_methods/` a 8 modules mais aucun répertoire de tests ne lui correspond (pas de `tests/test_calibration_methods/` visible).

**Acteur** : **Sonnet** — créer `tests/test_calibration_methods/` avec au minimum : test DSR, test POT/GPD, test bootstrap IC.

#### AS-C5 — `shadow_runtime.py` hardcode non documenté

Cf. AS-Q5.

---

### 2.4 Math — 5 angles morts

#### AS-M1 — `ce_min`/`delta_safe` engines : méthode de calibration non définie

Cf. AS-Q1. Non seulement ils manquent dans le catalogue, mais la **méthode de calibration** de `ce_min` et `delta_safe` n'est pas dans `13_CALIBRATION_METHODS.md`.

`ce_min` est le seuil d'edge minimum net du coût. Il devrait être calibré comme `THR-E02` (plancher en bps) mais **par engine**, car chaque engine a un profile risque/fréquence différent.

**Acteur** : **Opus** — section dans `13_...` pour les seuils per-engine.

#### AS-M2 — Aucune méthode de calibration pour `drawdown_warning` / `drawdown_observe`

**Constat** : `THR-R01` à `THR-R03` couvrent les breakers (daily/weekly/monthly). Mais `drawdown_warning` et `drawdown_observe` (niveaux intermédiaires, pas des breakers) ne sont dans **aucune méthode de calibration**. Ce sont des niveaux d'alerte, pas de stop, mais leur calibration est aussi importante (sinon le système est en alerte permanente ou jamais).

**Acteur** : **Opus** — ajouter `THR-W01` (drawdown_warning) et `THR-W02` (drawdown_observe) dans `11_...` avec méthode dans `13_...` (ex: quantile 80-90% de la distribution DD historique).

#### AS-M3 — `POT/GPD` : vérification refus ξ > 1 implémentée ?

**Constat** : `13_CALIBRATION_METHODS.md §5.2.1` spécifie : "Refus si ξ̂ > 1 (variance infinie, GPD pas exploitable)". Cette condition est-elle dans `calibration_methods/pot_gpd.py` ?

**Acteur** : **Sonnet** — vérifier `pot_gpd.py` et ajouter si absent : `if xi_hat > 1: raise CalibrationRejectError("xi > 1")`.

#### AS-M4 — Bootstrap stationnaire (Politis-Romano) vs bootstrap i.i.d.

**Constat** : `calibration_methods/bootstrap.py` existe. Est-ce le bootstrap **stationnaire** (block bootstrap, Politis-Romano) ou le simple bootstrap i.i.d. ? Pour des séries temporelles financières, le bootstrap i.i.d. est **incorrect** (ignore l'autocorrélation).

**Acteur** : **Sonnet** — vérifier que `bootstrap.py` implémente bien un block bootstrap stationnaire. Si c'est i.i.d., corriger et ajouter test.

#### AS-M5 — `hard_cap_floor.py` : logique de safety floor

**Constat** : `calibration_methods/hard_cap_floor.py` existe (concept de MI-7 dans `13_...`). Est-ce que cette fonction est **appelée par le calibration_loader** avant de publier un artefact ? Ou est-ce un utilitaire standalone non intégré ?

**Acteur** : **Sonnet** — vérifier l'intégration de `hard_cap_floor.py` dans le pipeline calibration_loader → artefact. Si absent, ajouter.

---

### 2.5 Software Engineering — 5 angles morts

#### AS-SE1 — Aucun script de déploiement Linux VPS

**Constat** : Le plan cible Hetzner CX43 Linux. `17A_...` montre Windows PowerShell. Il n'existe **aucun** script Linux pour :
- installer Python 3.13 sur Ubuntu 24.04
- créer un service `systemd` pour `shadow_vps_service.py`
- déployer les secrets via `age/sops`
- configurer `node_exporter`
- configurer les cron jobs pour log rotation et disk monitoring

**Risque** : quand vient le moment de déployer sur le vrai VPS, le temps de mise en place sera sous-estimé et il y aura des surprises (différences Python version, permissions, paths).

**Acteur** : **Opus** — spec dans un nouveau MD `19_VPS_DEPLOYMENT_RUNBOOK.md`. **Sonnet** — scripts shell/Ansible/Makefile correspondants.

#### AS-SE2 — Log rotation non implémentée (P1-5 partiellement)

**Constat** : `disk_monitor.py` existe (partiel d'après `16_...`). Mais **log rotation** (P1-5) n'a pas de confirmation de code. Sans log rotation sur un VPS 160 GB avec Shadow tournant 24/7, les logs peuvent remplir le disque en quelques semaines.

**Acteur** : **Sonnet** — implémenter rotation des logs runtime (taille ou date), intégrer avec `THR-I03` (log retention).

#### AS-SE3 — Aucun processus de CI/CD documenté

**Constat** : aucune trace de `.github/workflows/`, `Jenkinsfile`, `Makefile` de CI. Les 1026+ tests tournent... comment ? Manuellement ? Ce n'est pas production-safe.

**Risque** : une regression se glisse sans être détectée.

**Acteur** : **Opus** — décision (D-19 ou D-20) sur le CI choisi. **Sonnet** — écrire `Makefile` ou script de test minimal pour `pytest src/ tests/ -q`.

#### AS-SE4 — Startup/readiness checks non formalisés

Cf. AS-T4.

#### AS-SE5 — Aucune procédure de rollback d'artefact de calibration

**Constat** : `12_LOCAL_LAB_VS_VPS_SEPARATION.md §6.2` décrit le flux artefact mais la règle F-3 dit "un rollback = nouvelle version vN+1". Comment concrètement déclencher un rollback en urgence à 3h du matin ? Aucun script, aucun runbook.

**Acteur** : **Opus** — spec dans `19_VPS_DEPLOYMENT_RUNBOOK.md`. Procédure : `rsync calibration_v2.json → VPS → restart service`.

---

## 3. Plan de travail critique

### Priorité P0 — Avant tout premier gate Shadow

| # | Action | Acteur | Taille | Urgence |
|---|---|---|---|---|
| **W-01** | Fix Engine C/D imports cassés (3 fichiers) | **Sonnet** | < 30 min | IMMÉDIAT |
| **W-02** | Implémenter `rate_limiter.py` (token bucket Binance) | **Sonnet** | 2-4h | AVANT shadow live |
| **W-03** | Vérifier `build_binance_client_order_id` = UUIDv5 (pas f-string) | **Sonnet** | 30 min | AVANT ordres réels |
| **W-04** | Vérifier `bootstrap.py` = stationnaire Politis-Romano (pas i.i.d.) | **Sonnet** | 1h | AVANT calibration |
| **W-05** | Vérifier `pot_gpd.py` inclut refus ξ > 1 | **Sonnet** | 30 min | AVANT calibration |
| **W-06** | Ajouter tests `tests/test_calibration_methods/` (DSR, GPD, bootstrap vs paper) | **Sonnet** | 4-8h | AVANT calibration signée |
| **W-07** | Spec `THR-E03`/`THR-E04` (ce_min/delta_safe par engine) dans `11_...` + méthode `13_...` | **Opus** | 2h | AVANT calibration v1 |
| **W-08** | Spec `THR-W01`/`THR-W02` (drawdown_warning, drawdown_observe) dans `11_...` + `13_...` | **Opus** | 1h | AVANT shadow |

### Priorité P1 — Avant gate G2.1 (fin du 1er mois Shadow)

| # | Action | Acteur | Taille | Urgence |
|---|---|---|---|---|
| **W-09** | Implémenter `calibration_methods/psr.py` (PSR formula) | **Sonnet** | 2h | AVANT G2.1 |
| **W-10** | Implémenter `calibration_methods/ks_test.py` | **Sonnet** | 1h | AVANT G2.1 |
| **W-11** | Implémenter `calibration_methods/energy_distance.py` | **Sonnet** | 2h | AVANT G2.1 |
| **W-12** | Implémenter `calibration_methods/mann_kendall.py` | **Sonnet** | 1h | AVANT G2.1 |
| **W-13** | Implémenter `calibration_methods/hansen_spa.py` | **Sonnet** | 4h | AVANT G2.2 (peut attendre) |
| **W-14** | Ajouter calibration seam `risk_runtime.py` (drawdown_warning/observe) | **Sonnet** | 1h | AVANT shadow |
| **W-15** | Implémenter `scripts/shadow_gate_check.py` (rapport JSON `14_...` §12) | **Sonnet** | 8h | AVANT G2.1 |
| **W-16** | Spec partial fill handling | **Opus** | 2h | AVANT MICRO_LIVE |
| **W-17** | Vérifier `hard_cap_floor.py` intégré dans pipeline calibration → artefact | **Sonnet** | 1h | AVANT calibration v1 |
| **W-18** | Test integration testnet Binance (`test_integration_testnet.py`) | **Sonnet** | 4h | AVANT MICRO_LIVE |

### Priorité P2 — Avant MICRO_LIVE

| # | Action | Acteur | Taille | Urgence |
|---|---|---|---|---|
| **W-19** | Spec + scripts déploiement Linux VPS (`19_VPS_DEPLOYMENT_RUNBOOK.md`) | **Opus + Sonnet** | 4h spec + 8h code | AVANT VPS |
| **W-20** | Log rotation + disk monitor wiring (THR-I01/I02/I03) | **Sonnet** | 3h | AVANT shadow long |
| **W-21** | DSR test multi-engine (N=4, valeur Bailey-López de Prado table 1) | **Sonnet** | 2h | AVANT calibration v1 |
| **W-22** | Spec D-19 (partial fill decision) + D-20 (CI/CD choice) dans `10_...` | **Opus** | 1h | AVANT implémentation |
| **W-23** | Makefile / script CI minimal (`pytest` complet en 1 commande) | **Sonnet** | 1h | AVANT shadow |
| **W-24** | Spec startup readiness sequence dans `07_...` | **Opus** | 1h | AVANT MICRO_LIVE |
| **W-25** | Spec + procédure rollback calibration artefact d'urgence | **Opus** | 1h | AVANT LIVE |

---

## 4. Tableau récapitulatif angles morts

| # | Dimension | Angle mort | Sévérité | Acteur |
|---|---|---|---|---|
| AS-T1 | Trading | Rate limiter actif absent | **P0** | Sonnet |
| AS-T2 | Trading | Aucune preuve testnet réelle | **P0** | Sonnet |
| AS-T3 | Trading | Partial fill handling non spécifié | **P1** | Opus |
| AS-T4 | Trading | Ordre de démarrage non documenté | **P1** | Opus |
| AS-T5 | Trading | Idempotency non-UUIDv5 à vérifier | **P0** | Sonnet |
| AS-Q1 | Quant | `ce_min`/`delta_safe` absents du catalogue | **P1** | Opus |
| AS-Q2 | Quant | PSR/KS/Energy/Hansen SPA absents du code | **P1** | Sonnet |
| AS-Q3 | Quant | `risk_runtime.py` drawdown sans calibration seam | **P1** | Sonnet |
| AS-Q4 | Quant | DSR multi-engine non validé contre paper | **P1** | Sonnet |
| AS-Q5 | Quant | `shadow_runtime.py` hardcode non catalogué | **P2** | Opus+Sonnet |
| AS-C1 | Code | Engine C/D imports cassés | **P0** | Sonnet |
| AS-C2 | Code | `calibration_methods/` sans tests paper | **P0** | Sonnet |
| AS-C3 | Code | `rate_limiter.py` absent | **P0** | Sonnet |
| AS-C4 | Code | Pas de `tests/test_calibration_methods/` | **P0** | Sonnet |
| AS-C5 | Code | `shadow_runtime.py` hardcode | **P2** | Sonnet |
| AS-M1 | Math | Méthode calibration `ce_min`/`delta_safe` absente | **P1** | Opus |
| AS-M2 | Math | Méthode calibration `drawdown_warning/observe` absente | **P1** | Opus |
| AS-M3 | Math | Refus ξ>1 dans `pot_gpd.py` à vérifier | **P0** | Sonnet |
| AS-M4 | Math | Bootstrap i.i.d. vs stationnaire à vérifier | **P0** | Sonnet |
| AS-M5 | Math | `hard_cap_floor.py` intégration pipeline à vérifier | **P1** | Sonnet |
| AS-SE1 | SWE | Aucun script déploiement Linux VPS | **P1** | Opus+Sonnet |
| AS-SE2 | SWE | Log rotation non confirmée | **P1** | Sonnet |
| AS-SE3 | SWE | Aucun CI/CD | **P2** | Opus+Sonnet |
| AS-SE4 | SWE | Startup readiness checks absents | **P1** | Opus |
| AS-SE5 | SWE | Procédure rollback artefact absente | **P1** | Opus |

---

## 5. Ce qui est plus avancé que prévu (positif)

**Ne pas re-coder ce qui existe** :

| Ce qu'on croyait manquer | Réalité |
|---|---|
| `venue_adapters/binance_spot/` | **Complet** (13 fichiers, idempotency via `build_binance_client_order_id`) |
| `sharia_compliance/` | **Complet** (16 fichiers, 9 tests, intégré gatekeeper) |
| `calibration_methods/` | **8 modules** (DSR, POT/GPD, bootstrap, walkforward, stationarity, multiple_testing) |
| `fee_aware_edge_gate.py` | **100L, calibration-aware** |
| `telegram_alerter.py` | **Présent** dans `alerting/` |
| `gatekeeper.py` | **24 KB, intègre sharia + risk + edge** |
| `spread_guard.py`, `slippage_model.py` | **Présents** |

---

## 6. Qui fait quoi : règle de répartition

| Type de travail | Acteur |
|---|---|
| Spec math nouvelle (nouveaux threshold_id, méthodes calibration) | **Opus** |
| Mise à jour catalogue `11_...` et méthodes `13_...` | **Opus** |
| Spec architecture, décisions humaines, runbooks | **Opus** |
| Fix bugs simples (imports cassés, refus manquant) | **Sonnet** |
| Implémentation nouvelles fonctions math (PSR, KS, Hansen SPA) | **Sonnet** |
| Tests de validation vs papers | **Sonnet** |
| Scripts déploiement Linux (systemd, Makefile, log rotation) | **Sonnet** |
| Vérification `bootstrap.py` stationnaire vs i.i.d. | **Sonnet** |
| Arbitrage "doit-on implémenter ça maintenant ?" | **Humain** |

---

## 7. Prochaine session recommandée

**Session Sonnet (code)** — priorité immédiate :
1. W-01 : fix Engine C/D imports (< 30 min)
2. W-04 : vérifier bootstrap stationnaire
3. W-05 : vérifier POT/GPD refus ξ > 1
4. W-06 : créer `tests/test_calibration_methods/` (DSR + GPD + bootstrap)
5. W-03 : vérifier `build_binance_client_order_id`

**Session Opus (spec)** — en parallèle ou après :
1. W-07 : spec `THR-E03`/`THR-E04` (ce_min/delta_safe engines)
2. W-08 : spec `THR-W01`/`THR-W02` (drawdown_warning/observe)
3. W-16 : spec partial fill handling
4. W-19 : runbook déploiement VPS Linux

**Avant de lancer shadow long (>2 semaines)** :
- W-02 (rate limiter), W-09→W-12 (PSR, KS, Energy, Mann-Kendall), W-15 (shadow_gate_check.py), W-18 (testnet)

---

## 8. Suite logique dans le dossier

Le dossier `production_deployment_plan/` a maintenant besoin de :
- `19_VPS_DEPLOYMENT_RUNBOOK.md` — déploiement Linux VPS pas à pas
- ~~Une mise à jour `11_DYNAMIC_THRESHOLDS_CATALOG.md` avec THR-E03/E04/W01/W02/S06~~ **FAIT** (2026-04-13)
- Une mise à jour `13_CALIBRATION_METHODS.md` avec méthodes pour ces nouveaux seuils

---

## 9. Corrections appliquées — Deep audit code (2026-04-13)

> Cette section trace les corrections réellement appliquées suite à l'audit profond du code source.

### 9.1 Corrections code appliquées

| # | Fichier | Fix appliqué | Statut |
|---|---|---|---|
| FIX-1 | `src/calibration_methods/pot_gpd.py:152` | Ajout `if xi_hat >= 1.0: raise PotGpdError(...)` avec ref Coles 2001 §4.3.2 | **DONE** |
| FIX-2a | `tests/test_engines/test_engine_c/test_engine_c.py:5` | `from engine_c` → `from engines.engine_c` | **DONE** |
| FIX-2b | `tests/test_engines/test_engine_d/test_engine_d.py:5` | `from engine_d` → `from engines.engine_d` | **DONE** |
| FIX-2c | `tests/test_engines/test_engine_d/test_engine_d_bs104_regression.py:11` | `from engine_d` → `from engines.engine_d` | **DONE** |

### 9.2 Corrections spec appliquées

| # | Fichier | Fix appliqué | Statut |
|---|---|---|---|
| W-07 | `11_DYNAMIC_THRESHOLDS_CATALOG.md` | Ajout THR-E03 (ce_min per engine) + THR-E04 (delta_safe per engine) | **DONE** |
| W-08 | `11_DYNAMIC_THRESHOLDS_CATALOG.md` | Ajout THR-W01 (drawdown warning 2%) + THR-W02 (drawdown observe 4%) | **DONE** |
| W-08bis | `11_DYNAMIC_THRESHOLDS_CATALOG.md` | Ajout THR-S06 (max_allowed_ce_net_drop 0.0005) | **DONE** |
| W-08ter | `11_DYNAMIC_THRESHOLDS_CATALOG.md` | Correction THR-X03 source_module (`execution_backbone/rate_limiter.py`, pas `venue_adapters`) + notes token bucket | **DONE** |
| — | `11_DYNAMIC_THRESHOLDS_CATALOG.md` | Tableau synthèse mis à jour : 32 → **37 seuils**, 22 → **27 avec signature humaine** | **DONE** |

### 9.3 False positives corrigées (audit 1 → audit 2)

| Claim audit 1 | Réalité vérifiée en audit 2 | Impact |
|---|---|---|
| AS-T1 `rate_limiter.py` absent | **EXISTS** : `execution_backbone/rate_limiter.py` (quota ratio THR-X03, 66 LOC, intégré dans execution_runtime). **Mais** : pas de token bucket Binance API weight tracker — W-02 reste valide pour le tracking de poids API. | AS-T1 downgrade P0→P1, renommé : "Binance API weight tracker manquant" |
| AS-C2 "sans tests suffisants" | **8 fichiers** dans `tests/test_calibration_methods/` : `test_bootstrap.py`, `test_dsr.py`, `test_pot_gpd.py`, `test_hard_cap_floor.py`, `test_walkforward.py`, `test_stationarity.py`, `test_multiple_testing.py`, `test_execution.py` | AS-C2 downgrade, tests existent mais validation vs paper manque (W-06 reste) |
| AS-C3 `rate_limiter.py` absent | Idem AS-T1 — **existe** | AS-C3 fermé |
| AS-C4 "pas de `tests/test_calibration_methods/`" | **FAUX** — répertoire existe avec 8 fichiers | AS-C4 fermé |
| AS-M4 "bootstrap possiblement i.i.d." | **FAUX** — `bootstrap.py` IS stationary block bootstrap (Politis-Romano), `restart_probability = 1.0 / float(expected_block_length)` + `infer_stationary_block_length()` via autocorrélation | AS-M4 fermé, W-04 fermé |
| AS-M5 "`hard_cap_floor.py` non intégré" | **FAUX** — intégré et utilisé par `execution.py`, `local_lab_tail_risk_review.py`, `edge_gate_calibration.py` (grep confirmé) | AS-M5 fermé, W-17 fermé |
| AS-T5 "idempotency non-UUIDv5" | **ACCEPTABLE** — SHA1 truncation (8 chars hex), déterministe, collision-résistant pour l'échelle V5.3 (< 1000 ordres/jour). Binance max 36 chars. UUIDv5 serait plus pur mais l'implémentation actuelle est fonctionnelle. | AS-T5 fermé, W-03 fermé |

### 9.4 Work plan mis à jour post-audit 2

| # | Action | Statut post-audit 2 | Notes |
|---|---|---|---|
| W-01 | Fix Engine C/D imports | **FERMÉ** — appliqué | FIX-2a/2b/2c |
| W-02 | Token bucket Binance API | **OUVERT** — mais scope réduit | `execution_backbone/rate_limiter.py` couvre le quota applicatif. Il faut un `venue_adapters/binance_spot/api_weight_tracker.py` (token bucket pour les poids HTTP). |
| W-03 | Vérifier UUIDv5 | **FERMÉ** — acceptable | SHA1 truncation déterministe |
| W-04 | Vérifier bootstrap stationnaire | **FERMÉ** — confirmé Politis-Romano | Code correct |
| W-05 | Vérifier POT/GPD ξ>1 | **FERMÉ** — fix appliqué | FIX-1, `if xi_hat >= 1.0: raise PotGpdError(...)` |
| W-06 | Tests paper validation | **OUVERT** — tests existent mais pas de validation vs valeurs connues papers | Priority downgrade P0→P1 |
| W-07 | Spec THR-E03/E04 | **FERMÉ** — ajouté dans `11_...` | 2 entrées catalogue + méthode calibration |
| W-08 | Spec THR-W01/W02/S06 | **FERMÉ** — ajouté dans `11_...` | 3 entrées catalogue |
| W-09→W-13 | PSR, KS, Energy, Mann-Kendall, Hansen SPA | **OUVERT** | Sonnet — avant G2.1 |
| W-14 | Calibration seam risk_runtime | **RE-QUALIFIÉ** — `RiskLimits` est déjà un modèle injectable (Pydantic), le seam existe. Fix = câbler au bootstrap. | Sonnet — wiring task, pas refactor |
| W-15 | shadow_gate_check.py | **OUVERT** | Sonnet — avant G2.1 |
| W-16 | Spec partial fill | **OUVERT** | Opus |
| W-17 | Vérifier hard_cap_floor intégration | **FERMÉ** — confirmé intégré | — |
| W-18 | Test testnet Binance | **OUVERT** | Sonnet — avant MICRO_LIVE |
| W-19→W-25 | Déploiement, CI, rollback, etc. | **OUVERT** | Opus+Sonnet |

### 9.5 Bilan quantitatif

```
Angles morts initiaux :     25
Fermés (faux positifs) :     7  (AS-T5, AS-C3, AS-C4, AS-M4, AS-M5, W-03, W-04)
Fermés (corrigés)      :     6  (W-01, W-05, W-07, W-08, W-17, THR-X03)
Restants ouverts       :    12
  - P0 Sonnet :              1  (W-02 scope réduit)
  - P1 Sonnet :              7  (W-06, W-09→W-13, W-14, W-15)
  - P1 Opus   :              1  (W-16)
  - P2 mix    :              3  (W-19→W-25 regroupés)
```

**Progression** : 25 → **12 ouverts** (52% de réduction en une session d'audit + corrections).


