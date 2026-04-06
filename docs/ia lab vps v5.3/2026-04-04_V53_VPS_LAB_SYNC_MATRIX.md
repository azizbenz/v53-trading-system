# V5.3 — MATRICE DE SYNCHRONISATION VPS ↔ LOCAL AI LAB
## Ordre de développement croisé, dépendances, parallélisation, gates
### Date : 2026-04-04
### Statut : SYNC MATRIX FOR CODEX

---

# 0. Objet

Ce document complète :
- le canon cible
- le plan de migration prod-safe de la VPS
- le plan de construction prod-safe du Local AI Lab
- l’annexe mathématique VPS
- l’annexe mathématique + build-by-build du Lab

Il répond à une question opérationnelle unique :

> comment synchroniser le développement de la nouvelle VPS V5.3 et du Local AI Lab sans double travail, sans incohérence, et sans créer une seconde V5.3 cachée ?

---

# 1. Décision centrale

Le projet doit être conduit selon deux rails synchronisés :

## Rail A — VPS V5.3
Migration de la VPS existante vers la nouvelle doctrine :
- liquidité
- résilience
- toxicité
- fragmentation
- survivabilité d’exécution

## Rail B — Local AI Lab
Construction du laboratoire local :
- datasets
- replay
- features lockées
- diagnostic
- calibration
- micro-models
- distillation
- preuve
- artifacts
- closed-loop

## Règle absolue
Les deux rails partagent :
- un seul shared core V5.3
- une seule doctrine
- un seul langage de contrats
- une seule gouvernance artifact

---

# 2. Typologie des dépendances

## D0 — Indépendance réelle
Le build peut être codé sans attendre l’autre rail.

## D1 — Dépendance documentaire
Le build peut être codé si le canon, les enums et les schémas sont figés.

## D2 — Dépendance de contrat
Le build dépend d’interfaces, schémas, hooks ou payloads déjà stabilisés.

## D3 — Dépendance de preuve
Le build dépend d’une brique de monitoring/protocol/meta pour être utile.

## D4 — Dépendance runtime
Le build dépend d’une implémentation VPS réelle ou d’un état lifecycle réel.

## D5 — Dépendance de validation finale
Le build peut être codé, mais ne peut pas être considéré merge-ready ou activable avant validation de l’autre rail.

---

# 3. Vue synthétique

| Ordre | VPS Phase / Build | Lab Build | Dépendance | Peut être codé en parallèle ? | Gate réel |
|---|---|---|---|---|---|
| 1 | Canon / doctrine / locks | Canon / doctrine / locks | D1 | Oui | doctrine figée |
| 2 | Shared contracts / manifests / DAG | Feature locks / artifact enums | D1 | Oui | nomenclature stable |
| 3 | Data/runtime invariants VPS | Dataset registry / acquisition | D1 | Oui | timeframes/pairs/schema validés |
| 4 | Replay/protocol/meta instrumentation | Local replay bridge | D2/D3 | Partiellement | parité shared core |
| 5 | Risk/scoring explicables | Feature factory / diagnostic | D2/D3 | Oui | reason codes stables |
| 6 | Build-14 readers READ_ONLY | Diagnostic / calibration / micro-models | D2/D3 | Oui | readers disponibles en sortie |
| 7 | Runtime hook policy | Distillation | D2 | Oui | hooks + action units figés |
| 8 | Artifact governance API | Artifact packer & signer | D2/D4 | Oui | schéma artifact final |
| 9 | Lifecycle / drift / registry | Closed-loop client | D4 | Partiellement | batchs exportables VPS |
| 10 | Shadow/Limited Influence | Proof protocol enrichi | D3/D5 | Oui | métriques réelles disponibles |
| 11 | Multi-VPS control plane | Multi-VPS aware lab | D4/D5 | Oui | APIs flotte disponibles |

---

# 4. Matrice détaillée

## PHASE S0 — Fondation commune

### VPS côté A
- canon cible
- migration plan
- patch runtime hooks
- hook scope policy
- schéma artifact final
- enums de lifecycle

### Lab côté B
- canon Lab
- annexe math
- build plan Lab
- taxonomy A/B/C/D
- feature lock
- transform lock

### Dépendance
- D1 documentaire

### Parallélisation
- oui totale

### Gate
Aucun code tant que :
- noms de hooks
- action units
- classes artifact
- lifecycle states
- runtime modes
ne sont pas figés.

---

## PHASE S1 — Shared core & contrats

### VPS côté A
- Build-1 confirmé / gelé
- interface_contracts
- manifest_registry
- dag_validator
- contract tests
- smoke bootstrap/recovery

### Lab côté B
- Build-L0 doctrine locks
- enums
- feature dictionaries
- transform whitelist
- complexity guard

### Dépendance
- D1 -> D2

### Parallélisation
- oui, mais le Lab ne doit pas définir de types incompatibles avec interface_contracts

### Gate
Merge Lab impossible si les enums artifact/hook scope divergent du shared core.

---

## PHASE S2 — Données

### VPS côté A
- Build-2 déjà existant / confirmé
- data_backbone
- data_quality_engine
- pair health stable
- timestamps / freshness / consistency stables

### Lab côté B
- Build-L1 dataset registry
- Build-L2 data acquisition

### Dépendance
- D1

### Parallélisation
- oui totale

### Gate
Le Lab doit adopter les mêmes conventions de paires, timeframes, timestamps et quality semantics que la VPS.

---

## PHASE S3 — Parité replay

### VPS côté A
- local_replay_runtime
- meta_learning
- protocols
- monitoring
- bundles comparatifs
- shared runtime semantics

### Lab côté B
- Build-L3 Local Replay Bridge

### Dépendance
- D2 + D3

### Parallélisation
- partielle

### Ce qui peut commencer
- structure du replay bridge
- session manifests
- replay clock
- loaders historiques
- shadow execution simulator

### Ce qui doit attendre
- validation finale de parité logique
- export des evidence bundles
- rapports de divergence

### Gate
Le Build-L3 n’est pas validable tant que :
- les contrats replay/protocols côté VPS ne sont pas stables
- les mêmes reason codes et états décisionnels ne sont pas exportés

---

## PHASE S4 — Explicabilité cœur

### VPS côté A
- Build-4 risk backbone explicable
- Build-5 scoring backbone explicable
- reason codes stables
- hard/soft/rank lisibles
- no-trade explicite
- compatibilité portefeuille visible

### Lab côté B
- Build-L4 feature factory
- Build-L5 diagnostic engine

### Dépendance
- D2 + D3

### Parallélisation
- oui forte

### Gate
Build-L5 ne doit pas être considéré done tant que les reason codes VPS sont encore instables.

---

## PHASE S5 — Build-14 lecture seule

### VPS côté A
- Build-14 readers en READ_ONLY
- snapshots evidence
- monitoring des readers
- impact CPU / latence / activation observés

### Lab côté B
- Build-L6 threshold calibrator
- Build-L7 micro-model lab

### Dépendance
- D2 + D3

### Parallélisation
- oui

### Gate
Les micro-models utiles ne deviennent intéressants que si les readers VPS existent vraiment.

---

## PHASE S6 — Hook policy & distillation

### VPS côté A
- hook scope policy figée
- Cold-Path Safe Rule Compilation
- CompiledHookPlan
- runtime hook snapshots typés
- action units
- caps/floors
- registry compilé

### Lab côté B
- Build-L8 rule distillation

### Dépendance
- D2 critique

### Parallélisation
- oui, mais sous forte dépendance de contrat

### Gate
Le Build-L8 du Lab n’est pas canonique tant que la forme exacte des hooks runtime n’est pas figée côté VPS.

### Règle absolue
La distillation dépend du langage d’exécution de la VPS, pas l’inverse.

---

## PHASE S7 — Proof protocol

### VPS côté A
- meta/protocols/monitoring suffisamment riches
- shadow comparatif
- limited influence metrics
- burden metrics
- drift metrics

### Lab côté B
- Build-L9 proof protocol

### Dépendance
- D3 + D5

### Parallélisation
- oui partielle

### Ce que le Lab peut coder sans attendre
- ablation runner
- anti-cowardice
- friction regret
- walk-forward
- burden test
- capital efficiency test

### Ce qui dépend de la VPS
- preuve finale sur données closed-loop
- métriques de drift runtime
- operational burden réel côté VPS

---

## PHASE S8 — Artifact packaging & upload

### VPS côté A
- artifact governance API
- schema validator
- signature verifier
- lifecycle manager
- registry artifact
- status projection

### Lab côté B
- Build-L10 artifact packer & signer

### Dépendance
- D2 + D4

### Parallélisation
- oui

### Gate
Aucun upload réel vers la VPS sans :
- signature valide
- schema stable
- hook scope stable
- lifecycle states stables

---

## PHASE S9 — Closed-loop

### VPS côté A
- batch export
- Parquet batch index
- fetch API
- runtime state export
- log query plane
- artifact status export

### Lab côté B
- Build-L11 closed-loop client

### Dépendance
- D4

### Parallélisation
- partielle

### Ce que le Lab peut préparer avant
- lecteur Parquet
- joiner
- retrain dataset builder
- drift feedback builder

### Ce qui doit attendre
- API finale de fetch
- schéma final de batch closed-loop
- vraies données runtime exportées

---

## PHASE S10 — Multi-VPS

### VPS côté A
- agent léger
- status endpoints
- fleet status
- alert aggregation
- log query fédérée

### Lab côté B
- Build-L12 control-plane aware integration

### Dépendance
- D4 + D5

### Parallélisation
- oui

### Ce que le Lab peut coder en avance
- interface de client control plane
- abstractions multi-VPS
- comparateurs de runs
- structure de rapports

---

# 5. Ce qui peut être codé en parallèle sans danger

## Oui, en parallèle tôt
- doctrine locks Lab
- dataset registry
- data acquisition
- feature locks
- parquet partitioning
- integrity checker
- threshold calibrator structure
- micro-model trainer skeleton
- proof protocol skeleton
- artifact packer skeleton

## Oui, en parallèle mais avec contrat figé
- replay bridge
- distillation
- packaging artifact
- lifecycle-aware upload client
- control-plane aware integration

## Non, à ne pas coder au hasard
- distillation finale avant hook policy
- closed-loop final avant batch export VPS
- proof final avant meta/protocol metrics réelles
- artifact runtime JSON sans schema VPS figé
- replay parity verdict avant shared runtime stable

---

# 6. Ce qui doit être gelé avant de laisser Codex avancer vite

## 6.1 Langage artifact
- classes A/B/C/D
- action units
- hook ids
- lifecycle states
- caps/floors
- schema versions

## 6.2 Langage replay
- reason codes
- decision states
- runtime modes
- profile scope
- evidence bundles

## 6.3 Langage closed-loop
- batch schema
- log query schema
- runtime health schema
- artifact status schema

---

# 7. Ordre réel recommandé à donner à Codex

## Bloc 1 — commun
1. doctrine locks
2. shared enums
3. shared artifact schema
4. shared hook scope vocabulary

## Bloc 2 — VPS fondation
5. patchs Build-1/4/5 si nécessaires
6. instrumentation/protocols/meta
7. hook policy
8. runtime compilation froide

## Bloc 3 — Lab fondation
9. Build-L0
10. Build-L1
11. Build-L2
12. Build-L3 skeleton
13. Build-L4
14. Build-L5

## Bloc 4 — convergence
15. Build-14 READ_ONLY côté VPS
16. Build-L6
17. Build-L7
18. Build-L8
19. Build-L9

## Bloc 5 — artifacts
20. VPS artifact governance API
21. Build-L10
22. dry-run artifact upload
23. LIMITED_INFLUENCE côté VPS

## Bloc 6 — réalité
24. closed-loop batch côté VPS
25. Build-L11
26. feedback / retrain datasets
27. control plane côté VPS
28. Build-L12

---

# 8. Gates de synchronisation obligatoires

## Gate G1 — Doctrine freeze
Aucun chantier avancé avant :
- hook names figés
- artifact taxonomy figée
- action units figées

## Gate G2 — Shared core parity
Aucun verdict replay avant :
- reason codes figés
- shared core stable
- protocols exportables

## Gate G3 — Distillation readiness
Aucune distillation finale avant :
- hook snapshots typés
- cold-path compiler design figé
- schema artifact figé

## Gate G4 — Artifact readiness
Aucun upload réel avant :
- signature
- schema validator
- lifecycle manager
- rollback

## Gate G5 — Closed-loop readiness
Aucun retraining closed-loop réel avant :
- batch export stable
- schema batch stable
- log query stable

---

# 9. Ce qu’il ne faut surtout pas faire

1. Coder tout le Lab jusqu’au bout sans figer le langage artifact.
2. Laisser Codex inventer des hooks non validés.
3. Laisser le Lab créer des features qui n’existent pas côté VPS.
4. Attendre la fin complète de la VPS pour commencer le Lab.
5. Tenter un closed-loop avant d’avoir une vraie exportation batch.
6. Distiller des règles avant d’avoir fixé action_unit, caps, hooks.
7. Créer un fork logique local par praticité.

---

# 10. Verdict final

## Oui
La nouvelle doctrine V5.3 et le Local AI Lab peuvent être développés avec la même discipline build par build que la V5.3 historique.

## Mais
Ils ne doivent pas être développés comme deux systèmes symétriques.

## La forme correcte est :
- un canon unique
- un rail VPS
- un rail Lab
- une matrice de synchronisation

## Lecture correcte pour Codex
1. cible
2. migration VPS
3. build plan Lab
4. annexe math VPS
5. annexe math Lab
6. patch runtime hooks
7. cette matrice de synchronisation

---

# 11. Conclusion opérationnelle

Ce document doit servir à décider :
- quoi coder maintenant
- quoi coder plus tard
- quoi coder en parallèle
- ce qui doit être gelé
- ce qui doit attendre
- et quels gates franchir avant d’annoncer qu’un build est done

Le principe final est :

> la VPS et le Lab avancent ensemble
>
> mais pas n’importe comment
>
> et jamais au prix d’un fork logique ou d’une incohérence documentaire
