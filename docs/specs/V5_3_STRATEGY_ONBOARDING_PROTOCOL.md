# V5.3 — STRATEGY ONBOARDING PROTOCOL
## Protocole canonique d’ajout, d’évaluation et de promotion d’une stratégie
### Document dérivé du canon V5.3
### Sans code — prod-safe

---

# 0. Statut du document

- Statut : PROTOCOL V1
- Portée : définir le chemin officiel d’introduction d’une idée stratégie dans V5.3
- Nature : protocole de gouvernance, pas preuve de runtime déjà codé
- Statut d’implémentation : **documentaire avec premiers scaffolds codés ; pas de runtime onboarding complet**

## 0.1 Réalité d’implémentation à respecter

- le **core Build-1 à Build-9** est la base aujourd’hui réellement exécutable / gelable
- Build-10 dispose désormais d’une première implémentation codée côté monitoring / UI backend
- Build-9X est désormais présent dans une première implémentation codée gouvernée
- `LOCAL_REPLAY`, l’export d’artifact et l’import VPS disposent de scaffolds minimaux codés, sans runtime complet ni promotion implicite

---

# 1. Invariants canoniques

## 1.1 Moteurs cibles

La V5.3 reste structurée autour de :

- Moteur A
- Moteur B
- Moteur C
- Moteur D

## 1.2 Profils métier

Les seuls profils métier autorisés sont :

- `LIGHT`
- `COMPLETE`

## 1.3 Runtime modes

Les seuls `runtime_mode` autorisés sont :

- `LOCAL_REPLAY`
- `SHADOW`
- `MICRO_LIVE`
- `LIVE`

## 1.4 Interdictions

Interdiction de :

- créer `BACKTEST_PROFILE`
- créer une seconde V5.3 locale ou VPS
- créer un fork local / VPS
- charger un plugin stratégie arbitraire côté VPS
- exécuter du code stratégie importé via artifact
- promouvoir une stratégie depuis un backtest local seul

---

# 2. Pipeline officiel

Toute nouvelle stratégie suit le pipeline :

`classification -> versioning -> shared core -> LOCAL_REPLAY -> export artifact -> import VPS -> revue de valeur marginale -> candidature contrôlée -> Shadow -> Micro-live -> Live`

---

# 3. Taxonomie officielle

Chaque stratégie candidate doit entrer dans une seule catégorie :

- `A_variant`
- `B_variant`
- `Build14_enabler`
- `C_candidate`
- `D_candidate`
- `out_of_scope_for_V5_3`

## 3.1 Règle de lecture

- `A_variant` et `B_variant` restent des variantes de moteurs existants
- `Build14_enabler` reste un enrichissement, jamais un moteur autonome
- `C_candidate` et `D_candidate` suivent respectivement les trajectoires Build-15 et Build-16
- `out_of_scope_for_V5_3` n’entre pas dans le canon V5.3

---

# 4. Fiche de classification minimale

Toute proposition doit produire :

- `proposal_id`
- `proposal_name`
- `classification`
- `strategy_version`
- `feature_set_version`
- `formula_set_version`
- `source_version`
- `economic_hypothesis`
- `portfolio_hypothesis`
- `promotion_target`

---

# 5. Règles de versioning et de shared core

Une stratégie candidate doit être :

- intégrée au shared core
- versionnée explicitement
- couverte par contrats et tests
- traçable en local comme en VPS

Interdiction de laisser vivre :

- une feature seulement locale
- une formule seulement notebook
- un HMM seulement PC
- un seuil critique non versionné

---

# 6. Relation avec Build-14 et Build-9X

## 6.1 Build-14

Un `Build14_enabler` :

- est **activé à 100% en Shadow** (`SHADOW_ENABLED`) : pleinement utilisé, tracé, auditable
- sa promotion live est conditionnelle au verdict post-Shadow (`SHADOW_VALIDATED` ou `DORMANT`)
- ne devient jamais un moteur autonome
- ne bypass jamais A/B/C/D, le risk backbone, le portfolio ni les gates de promotion

## 6.2 Build-9X

Build-9X peut plus tard consommer les sorties de ce protocole pour produire :

- diagnostics
- breakdown reports
- checklists
- improvement candidates
- replay bundles

Mais Build-9X ne peut jamais :

- muter le live
- auto-promouvoir une hypothèse
- ouvrir un nouveau profil métier

---

# 7. Gate minimale avant promotion

Refus automatique si :

- classification absente
- versioning absent
- intégration shared core absente
- replay local non traçable
- artifact non versionné
- import VPS non lecture seule
- bypass de `SHADOW`, `MICRO_LIVE` ou `LIVE`

---

## Fin du document
