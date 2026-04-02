# V5.3 — REGISTRE CONSOLIDÉ DES GAPS BUILD-1 À BUILD-14
## Date : 2026-04-02
## Statut : ACTIF

---

# 0. Objet

Ce document consolide l'audit `Build-1 -> Build-14` afin de :

- figer un état des lieux unique
- prioriser les écarts réellement critiques
- définir un ordre de correction prod-safe

---

# 1. Statut consolidé par build

- Build-1 : `STILL PARTIAL`
- Build-2 : `ALIGNED`
- Build-3 : `ALIGNED`
- Build-4 : `STILL PARTIAL`
- Build-5 : `ALIGNED`
- Build-6 : `ALIGNED`
- Build-7 : `ALIGNED`
- Build-8 : `ALIGNED`
- Build-9 : `ALIGNED`
- Build-10 : `ALIGNED`
- Build-11 : `STILL PARTIAL`
- Build-12 : `NOT READY`
- Build-13 : `NOT READY`
- Build-14 : `STILL PARTIAL`

Lecture courte :

- le coeur Light `Build-2 -> Build-10` est globalement vert
- les deux zones encore critiques sont :
  - le garde-fou d'architecture global Build-1
  - la fermeture réelle de la chaîne Shadow / Micro-live / Live-Light avec Build-14

---

# 2. Gaps priorisés

## GAP-A — P0 — Dérive architecturale Build-1

Constat :

- le DAG global du dépôt ne passe plus
- le smoke Build-1 hérite de cet échec

Impact :

- on perd le garde-fou principal contre la dérive inter-modules

Owner probable :

- `dependency_registry`
- dépendances réelles récentes entre `local_replay_runtime`, `meta` et `protocols`

## GAP-B — P0 — Fermeture Shadow Build-11 non terminée

Constat :

- le canon exige une vérité système complète sur `30 jours`
- les gates sont strictes
- mais la fermeture honnête du cycle n'est pas démontrée

Impact :

- toute promotion vers Build-12 / Build-13 reste structurellement fragile

Sous-facteurs :

- `engine_c` et `engine_d` encore non opérables à l'entrée de package
- preuve runtime réelle Shadow VPS / `live_websocket` non close

## GAP-C — P1 — Exposition Build-14 incohérente

Constat :

- le coeur Build-14 parle `shadow_enabled`
- certaines surfaces monitoring / UI / protocol gardent `read_only` ou un mapping mixte

Impact :

- risque de diagnostic opérateur trompeur
- difficulté à auditer proprement l'état réel des enablers

## GAP-D — P1 — Build-12 et Build-13 bloqués par l'amont

Constat :

- les gates sont codées
- les préconditions système réelles ne sont pas toutes closes

Impact :

- faux positif possible si on confond `gates vertes` avec `système prêt`

## GAP-E — P2 — Vérification Build-4 perturbée par l'environnement de test

Constat :

- `test_circuit_breaker` échoue sur `PermissionError` lié à `tmp_path`

Impact :

- le verdict Build-4 reste partiel tant qu'on ne distingue pas proprement problème environnemental et problème suite

---

# 3. Ordre de correction recommandé

## Lot 1 — Architecture

Traiter d'abord le `GAP-A` :

- auditer précisément `manifest_registry`
- décider si le DAG doit être élargi ou si les dépendances doivent être recoupées
- rétablir un Build-1 propre avant d'élargir les changements fonctionnels

## Lot 2 — Fermeture Shadow réelle

Traiter ensuite le `GAP-B` :

- clarifier le statut réel de `engine_c` et `engine_d`
- décider ce qui relève d'une implémentation manquante, d'un stub assumé ou d'une doctrine mal reflétée
- produire ou cadrer explicitement la preuve runtime Shadow utile

## Lot 3 — Normalisation Build-14

Traiter le `GAP-C` :

- normaliser le vocabulaire exposé dans monitoring / protocol / UI
- éviter les résidus `read_only` quand le canon attend `shadow_enabled`

## Lot 4 — Requalification Build-12 / Build-13

Traiter le `GAP-D` seulement après les lots amont :

- revalider Micro-live
- revalider Live-Light
- vérifier qu'aucun test ou contrat ne conserve une sémantique trop faible

## Lot 5 — Nettoyage environnemental Build-4

Traiter le `GAP-E` en fin de vague :

- rendre les tests `risk_backbone` propres dans cet environnement
- ou documenter explicitement qu'il s'agit d'un problème de fixture / OS hors logique métier

---

# 4. Règles de conduite

- ne pas réécrire le canon global sans preuve
- ne pas déclarer `ALIGNED` un build faute de mieux
- ne pas mélanger `tests vertes`, `runtime réel` et `fermeture doctrinale`
- corriger par lots petits et traçables
- mettre à jour la mémoire projet après chaque vague

---

# 5. Décision de pilotage

Ordre retenu pour la suite :

1. Build-1 DAG
2. Build-11 fermeture Shadow
3. Build-14 exposition
4. Requalification Build-12 / Build-13
5. Nettoyage Build-4 environnement
