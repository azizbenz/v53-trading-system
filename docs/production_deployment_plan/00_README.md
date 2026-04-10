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
