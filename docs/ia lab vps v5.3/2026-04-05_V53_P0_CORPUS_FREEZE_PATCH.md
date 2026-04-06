# V5.3 — PATCH P0 DE FREEZE DOCUMENTAIRE
## Corpus Local AI Lab + VPS Runtime
### Date : 2026-04-05
### Statut : PATCH P0 NORMATIF AVANT BLOC 1
### Portée : langage partagé, hiérarchie documentaire, lifecycle, hooks, numérotation

---

# 0. Objet

Ce patch corrige les ambiguïtés documentaires qui bloquent un démarrage propre du chantier Codex / Claude.

Il ne cherche pas à compléter toute l’architecture.
Il fige seulement ce qui doit être figé avant de lancer le **Bloc 1 — Freeze commun et langage partagé**.

Ce patch est **normatif** pour :
- la hiérarchie des documents
- le vocabulaire partagé minimal
- la sémantique des états lifecycle
- la sémantique des hooks runtime
- la lecture correcte des différentes numérotations

Ce patch ne rouvre pas :
- la mathématique détaillée des readers
- la politique complète de versionnement de schéma
- la politique complète de rotation de clés
- la politique complète d’erreur runtime

Ces sujets restent obligatoires, mais sont traités en patchs ultérieurs.

---

# 1. Hiérarchie normative des documents

## 1.1 Source d’autorité principale

Le document suivant devient la **source d’autorité canonique principale** du corpus :

- `2026-04-04_V53_LOCAL_AI_LAB_FINAL_UNIQUE_CANON.md`

Quand un autre document entre en conflit avec lui sur :
- doctrine
- topologie finale
- taxonomie artifact
- states runtime
- invariants
- gouvernance

alors le **FINAL_UNIQUE_CANON** prévaut.

## 1.2 Documents normatifs secondaires

Les documents suivants restent normatifs, mais seulement dans leur domaine propre et **sans contredire** le canon principal :

1. `2026-04-04_V53_PATCH_COLD_PATH_SAFE_RULE_COMPILATION.md`
   - autorité sur l’exécution runtime sécurisée des artifacts
   - autorité sur le cold-path compilation model
   - autorité sur les invariants hot-path / no parsing / no code injection

2. `2026-04-04_V53_PROD_SAFE_VPS_MIGRATION_PLAN.md`
   - autorité sur l’ordre de migration de la VPS existante
   - autorité sur les vagues d’ouverture contrôlée
   - autorité sur la doctrine Build-14 READ_ONLY -> SHADOW -> LIMITED_INFLUENCE

3. `2026-04-04_V53_LOCAL_AI_LAB_ANNEXE_MATH_AND_BUILD_PLAN.md`
   - autorité sur l’annexe math du Lab
   - autorité sur l’ordre canonique des builds Lab `L0 -> L12`
   - non autorité si collision avec vocabulaire partagé gelé par le présent patch

4. `2026-04-04_V53_VPS_ANNEXE_MATH_RUNTIME_MARKET_PHYSICS.md`
   - autorité sur l’annexe math VPS
   - non autorité si collision avec les enums / hooks / lifecycle gelés par le présent patch

## 1.3 Documents dérivés ou non normatifs

Les documents suivants ne doivent plus être lus comme autorités concurrentes :

1. `2026-04-04_V53_NEW_TARGET_CANONICAL_VPS_LOCAL_AI_LAB.md`
   - statut corrigé : **VISION CIBLE / DOCUMENT D’ORIENTATION**
   - ce document fixe la destination, pas le détail canonique final
   - en cas de conflit, il ne prévaut pas sur `FINAL_UNIQUE_CANON`

2. `2026-04-04_V53_LOCAL_AI_LAB_PROD_SAFE_BUILD_PLAN.md`
   - statut corrigé : **SYNTHÈSE EXÉCUTIVE NON NORMATIVE**
   - il résume et simplifie
   - il ne crée aucune règle canonique nouvelle

3. `2026-04-04_V53_LOCAL_AI_LAB_IMPLEMENTATION_BLUEPRINT.md`
   - statut : **document d’implémentation dérivé**
   - il doit refléter le canon
   - il ne peut pas inventer ou modifier seul les enums, states, hooks ou actions

4. `2026-04-04_V53_ORCHESTRATION_PROMPT_PACK_CODEX_CLAUDE.md`
   - statut : **document d’orchestration**
   - il décrit l’ordre pratique d’exécution
   - il n’a pas autorité pour redéfinir les concepts du canon

---

# 2. Règle de lecture correcte du corpus

L’ordre correct de lecture n’est pas arbitraire.

Il doit être compris ainsi :

1. **destination**
   - `NEW_TARGET_CANONICAL`
2. **canon final de référence**
   - `FINAL_UNIQUE_CANON`
3. **migration VPS**
   - `PROD_SAFE_VPS_MIGRATION_PLAN`
4. **construction Lab**
   - `LOCAL_AI_LAB_ANNEXE_MATH_AND_BUILD_PLAN`
5. **math VPS**
   - `VPS_ANNEXE_MATH_RUNTIME_MARKET_PHYSICS`
6. **patch runtime artifact**
   - `PATCH_COLD_PATH_SAFE_RULE_COMPILATION`
7. **synchronisation des deux rails**
   - `VPS_LAB_SYNC_MATRIX`
8. **implémentation détaillée**
   - `IMPLEMENTATION_BLUEPRINT`
9. **orchestration opératoire**
   - `ORCHESTRATION_PROMPT_PACK`

Le blueprint et l’orchestration arrivent **après** le canon, parce qu’ils dérivent du canon.

---

# 3. Décision canonique sur les numérotations

## 3.1 Principe général

Le corpus utilise plusieurs séquences de numérotation.

Cela n’est pas une erreur en soi.
L’erreur serait de les traiter comme une seule chronologie.

À partir de ce patch, les séquences suivantes sont officiellement distinguées.

## 3.2 Numérotation canonique VPS existante

La VPS historique conserve sa numérotation existante :
- `Build-1` à `Build-17`
- avec `Build-9X` comme extension spécifique

Cette numérotation est réservée au **shared core V5.3 historique** et à sa migration.

## 3.3 Numérotation canonique Lab

Le Local AI Lab adopte comme séquence canonique unique :
- `Build-L0` à `Build-L12`

Quand un document parle du **Lab**, cette séquence est la seule séquence canonique à utiliser dans les titres, sections, tableaux de suivi et prompts de développement.

## 3.4 Phases de migration VPS

La migration VPS conserve sa propre séquence de pilotage :
- `PHASE 0`, `PHASE 1`, etc.

Ces phases décrivent un **ordre de transformation opérationnel**.
Elles ne remplacent ni les builds VPS historiques ni les builds Lab.

## 3.5 Blocs d’orchestration

L’orchestration conserve ses propres blocs :
- `Bloc 1`, `Bloc 2`, etc.

Ces blocs décrivent un **ordre de travail Codex / Claude / audit**.
Ils ne remplacent ni les phases VPS ni les builds Lab.

## 3.6 Aliases A -> N du blueprint

Les labels `Build A -> Build N` présents dans le blueprint sont désormais déclarés **aliases d’implémentation internes au blueprint**.

Ils ne doivent plus être utilisés comme numérotation documentaire principale.

Règle obligatoire :
- tout usage futur de `Build A -> N` doit afficher en face le build canonique Lab correspondant `Build-Lx`
- le suivi projet et les audits doivent parler en priorité en `Build-Lx`

## 3.7 Règle de rédaction

À partir de ce patch :
- **VPS existante / migration** -> parler en `Build-1..17` et `PHASE n`
- **Lab** -> parler en `Build-L0..L12`
- **workflow de chantier** -> parler en `Bloc n`
- **blueprint détaillé** -> peut garder `A..N` mais seulement comme alias secondaire

---

# 4. Décision canonique sur le lifecycle

## 4.1 Problème corrigé

Le corpus mélangeait deux axes sémantiques différents sous le mot `lifecycle_state` :

1. un axe de **promotion / activation runtime**
2. un axe de **santé / dérive / retrait**

Cette fusion est désormais interdite.

## 4.2 Décision

Le système adopte **deux enums distincts**.

### A. `ArtifactActivationStage`
Il décrit **où l’artifact est autorisé à exister fonctionnellement** dans la chaîne runtime.

Valeurs canoniques :
- `REPLAY_ONLY`
- `SHADOW_READY`
- `LIMITED_INFLUENCE`
- `MICRO_LIVE_CANDIDATE`
- `LIVE_APPROVED`

### B. `ArtifactHealthState`
Il décrit **l’état de santé / dérive / retrait** de l’artifact.

Valeurs canoniques :
- `ACTIVE`
- `DECAYING`
- `REVIEW_REQUIRED`
- `DORMANT`
- `EXPIRED`

## 4.3 Sémantique exacte

### `ArtifactActivationStage`
- `REPLAY_ONLY` : utilisable en replay / étude, non activable runtime VPS
- `SHADOW_READY` : activable en shadow seulement
- `LIMITED_INFLUENCE` : activable avec influence bornée et monitorée
- `MICRO_LIVE_CANDIDATE` : candidat à un micro-live gouverné
- `LIVE_APPROVED` : approuvé pour une activation live selon les gates supérieurs

### `ArtifactHealthState`
- `ACTIVE` : artifact sain dans son domaine déclaré
- `DECAYING` : dérive détectée mais pas encore retrait obligatoire
- `REVIEW_REQUIRED` : divergence suffisante pour exiger revue humaine / revalidation
- `DORMANT` : artifact retiré de l’activité runtime
- `EXPIRED` : artifact expiré et non activable

## 4.4 Règle d’activation réelle

Un artifact ne peut posséder un plan compilé actif que si :

1. `ArtifactActivationStage` appartient à :
   - `SHADOW_READY`
   - `LIMITED_INFLUENCE`
   - `MICRO_LIVE_CANDIDATE`
   - `LIVE_APPROVED`

et

2. `ArtifactHealthState` n’appartient pas à :
   - `DORMANT`
   - `EXPIRED`

Conséquence :
- `DORMANT` et `EXPIRED` retirent le plan compilé actif
- les tests lifecycle du patch cold-path restent valides

## 4.5 Règle de projection documentaire

Le terme générique `lifecycle_state` ne doit plus apparaître seul dans le corpus s’il peut créer une ambiguïté.

Les documents doivent désormais employer explicitement :
- `activation_stage`
- ou `health_state`

Si un payload historique garde temporairement un champ `lifecycle_state`, ce champ doit être considéré comme **legacy / transitional** et remplacé au plus tôt par les deux champs séparés.

---

# 5. Runtime modes canoniques

Les modes runtime explicitement reconnus par le corpus restent :
- `LOCAL_REPLAY`
- `SHADOW`
- `MICRO_LIVE`
- `LIVE`

Aucun document ne doit introduire un autre mode runtime sans patch canonique dédié.

Le Lab n’introduit pas un runtime live parallèle.

---

# 6. Hook vocabulary canonique

## 6.1 Enum canonique `HookId`

Les hooks runtime autorisés et nommés canoniquement sont :
- `ENGINE_A_PRE_ENTRY_CONFIRMATION`
- `ENGINE_B_SWEEP_VALIDATION`
- `ENGINE_C_VOID_VALIDATION`
- `ENGINE_D_REENTRY_VALIDATION`
- `RISK_MICRO_FRICTION_PRECHECK`
- `SCORING_SOFT_PENALTY_LAYER`
- `PORTFOLIO_RELATIVE_RANK_ADJUSTMENT`
- `EXECUTION_NO_TRADE_FILTER`

Aucun autre hook ne peut être inventé par Codex, Claude ou le blueprint sans patch canonique dédié.

## 6.2 Mapping canonique `HookId -> module`

Le mapping canonique minimal est :

- `ENGINE_A_PRE_ENTRY_CONFIRMATION` -> `engine_a_hooks.py`
- `ENGINE_B_SWEEP_VALIDATION` -> `engine_b_hooks.py`
- `ENGINE_C_VOID_VALIDATION` -> `engine_c_hooks.py`
- `ENGINE_D_REENTRY_VALIDATION` -> `engine_d_hooks.py`
- `RISK_MICRO_FRICTION_PRECHECK` -> `risk_hooks.py`
- `SCORING_SOFT_PENALTY_LAYER` -> `scoring_hooks.py`
- `PORTFOLIO_RELATIVE_RANK_ADJUSTMENT` -> `portfolio_hooks.py`
- `EXECUTION_NO_TRADE_FILTER` -> `execution_hooks.py`

## 6.3 Règle de snapshot

Chaque `HookId` doit être lié à un snapshot typé propre.

Une règle artifact :
- ne peut lire qu’une feature exposée par le snapshot du hook ciblé
- ne peut pas référencer une feature hors snapshot
- ne peut pas contourner `risk_backbone`, `scoring_backbone` ou `protocols`

---

# 7. Actions runtime et vocabulaire d’influence

## 7.1 Formes d’influence autorisées en canon minimal

Les formes d’influence canoniques de base sont :
- `SOFT_BOOST`
- `SOFT_REDUCE`
- `NO_TRADE`
- `SIZE_REDUCE`
- `RANK_ADJUST`

Ces formes couvrent la doctrine de `LIMITED_INFLUENCE` décrite dans la migration VPS.

## 7.2 Correspondance avec les unités d’action

Les correspondances minimales autorisées sont :

- `SOFT_BOOST` -> `RAW_SCORE_MULTIPLIER` ou `RAW_SCORE_ADD`
- `SOFT_REDUCE` -> `RAW_SCORE_MULTIPLIER` ou `RAW_SCORE_ADD`
- `NO_TRADE` -> action bornée par hook autorisé, avec monitoring explicite
- `SIZE_REDUCE` -> `SIZE_FACTOR`
- `RANK_ADJUST` -> `RANK_DELTA`

## 7.3 Statut de `reason enrichment`

`reason enrichment` n’est pas une action runtime autonome.

C’est un **effet d’observabilité / explicabilité** attaché à une action autorisée via :
- `reason_code`
- éventuellement `CONVICTION_ADD` si le canon l’emploie explicitement dans un payload structuré

Mais il ne doit pas être traité comme un `action` autonome séparé.

## 7.4 Statut de `TIMEOUT_ADJUST`

`TIMEOUT_ADJUST` reste **réservé / non activé en canon minimal Bloc 1**.

Il peut exister dans un blueprint comme capacité potentielle, mais :
- il n’entre pas dans les formes canoniques d’influence Build-14 de base
- il ne doit pas être activé ni utilisé en runtime sans patch canonique explicite ultérieur

---

# 8. Règles de rédaction à appliquer immédiatement

Les documents du corpus doivent être corrigés selon les règles suivantes :

1. ne plus employer `NEW_TARGET_CANONICAL` comme canon principal
2. marquer `PROD_SAFE_BUILD_PLAN` comme synthèse non normative
3. remplacer les ambiguïtés `lifecycle_state` par `activation_stage` et `health_state`
4. remplacer tout langage laissant croire que `A -> N` est la séquence canonique du Lab
5. insérer le mapping `HookId -> module`
6. clarifier que `reason enrichment` n’est pas une action autonome
7. clarifier que `TIMEOUT_ADJUST` est réservé tant qu’aucun patch dédié ne l’ouvre

---

# 9. Ce que ce patch ne décide pas encore

Restent à traiter dans des patches ultérieurs :

1. `Schema Versioning Policy`
2. `Runtime Error Policy`
3. `Key Management Policy`
4. nettoyage mathématique de `Fragility`, `ReformationScore` et coefficients `TO_CALIBRATE`
5. fusion finale ou normalisation complète du Physics Feature Dictionary
6. alignement complet JSON exemple <-> Pydantic imbriqué pour les règles distillées

Ces sujets sont obligatoires pour la maturité finale, mais ne bloquent plus le **freeze documentaire P0** une fois le présent patch intégré.

---

# 10. Décision finale

Avant tout démarrage effectif du **Bloc 1**, le corpus doit être considéré comme figé sur les points suivants :

- hiérarchie documentaire
- lecture correcte des numérotations
- séparation `ArtifactActivationStage` / `ArtifactHealthState`
- runtime modes canoniques
- enum `HookId`
- mapping `HookId -> module`
- formes d’influence runtime canoniques de base

Aucun chantier de code ne doit redéfinir ces objets en parallèle.

Le principe obligatoire reste :

> un seul shared core
>
> un seul langage partagé
>
> un seul canon principal
>
> aucun fork logique

