# V5.3 — UNIFIED LOCAL/VPS BACKTEST ARCHITECTURE PLAN — V2
## Plan unifié d’architecture locale / VPS pour replay, import d’artifact et gouvernance
### Document dérivé du canon V5.3
### Sans code — prod-safe

---

# 0. Statut du document

- Statut : PLAN D’ARCHITECTURE V2
- Portée : unifier la V5.3 locale et la V5.3 VPS sans divergence de logique
- Nature : plan d’implémentation et de gouvernance, pas preuve de runtime déjà codé

## 0.1 Règle de hiérarchie

En cas de conflit :

1. `V5_3_MASTER_FINAL_UNIQUE.md`
2. `V5_3_MASTER_FINAL_CANONICAL.md`
3. `V5_3_BUILD_PLAN_MODULE_PAR_MODULE.md`
4. les specs de build officielles
5. le présent document

## 0.2 Réalité d’implémentation à respecter

- le **core Build-1 à Build-9** reste la base aujourd’hui réellement exécutable / gelable
- une première implémentation codée existe désormais pour Build-10 et Build-9X
- `LOCAL_REPLAY` dispose d’un scaffold minimal codé, sans constituer encore un runtime complet opéré
- l’import d’artifact VPS dispose d’un scaffold minimal codé et reste une passerelle de revue / observabilité, jamais un chemin de promotion implicite

---

# 1. Décision d’architecture centrale

La décision retenue est :

> le local replay doit être **la même V5.3** que la VPS, exécutée en `runtime_mode = LOCAL_REPLAY`

et non :

- une seconde V5.3 locale
- un fork PC
- un ancien moteur séparé
- une architecture parallèle de recherche

---

# 2. Invariants non négociables

## 2.1 Profils métier

La V5.3 n’a que deux profils métier :

- `LIGHT`
- `COMPLETE`

## 2.2 Runtime modes

Les seuls `runtime_mode` autorisés sont :

- `LOCAL_REPLAY`
- `SHADOW`
- `MICRO_LIVE`
- `LIVE`

## 2.3 Interdictions

Interdiction de créer :

- `BACKTEST_PROFILE`
- `LOCAL_PROFILE`
- `PC_PROFILE`
- toute seconde V5.3 locale ou VPS

---

# 3. Shared core obligatoire

Le local et la VPS doivent partager la même logique métier :

- mêmes contrats
- mêmes versions
- mêmes features
- mêmes équations
- mêmes hard blockers
- mêmes règles de coût prudent
- mêmes sorties de décision

Ce qui peut différer :

- source de données
- horloge
- simulateur d’exécution vs exécution réelle
- densité d’observabilité

---

# 4. Pipeline officiel

Le pipeline canonique reste :

`classification -> versioning -> shared core -> LOCAL_REPLAY -> export artifact -> import VPS -> candidature contrôlée -> SHADOW -> MICRO_LIVE -> LIVE`

Conséquences :

- aucun bon replay local ne vaut promotion directe
- aucun artifact n’exécute du code stratégie sur la VPS
- aucun artifact n’ouvre un profil ou un moteur
- aucun bypass de Build-11 / Build-12 / Build-13

---

# 5. Relation avec Build-9X

Build-9X est :

- une extension méta post-Build-9
- dépendante de Build-9
- dépendante opératoirement de Build-10
- consommatrice future de `LOCAL_REPLAY`
- documentairement prête via la V2 de référence
- déjà présente dans une première implémentation codée gouvernée

Build-9X peut produire :

- diagnostics
- breakdown reports
- checklists
- hypothesis registry
- improvement candidates
- replay bundles

Build-9X ne peut pas :

- muter le live
- créer un fork local / VPS
- créer un nouveau profil métier
- auto-promouvoir une hypothèse

---

# 6. Import d’artifact côté VPS

L’import VPS est :

- versionné
- horodaté
- corrélé
- en lecture seule
- observable dans les logs et les projections UI

Il n’est jamais :

- un chargeur de code stratégie
- un moteur autonome
- une voie de promotion implicite

---

# 7. Verdict documentaire

Ce plan fixe une seule doctrine :

- une seule V5.3 commune local + VPS
- deux profils métier seulement
- quatre runtime modes seulement
- promotion toujours gouvernée
- aucun fork local / VPS

---

## Fin du document
