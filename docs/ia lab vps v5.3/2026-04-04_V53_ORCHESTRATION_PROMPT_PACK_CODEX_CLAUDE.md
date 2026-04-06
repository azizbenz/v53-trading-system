# V5.3 — ORCHESTRATION PROMPT PACK
## Ordre exact des prompts Codex / Claude par bloc
### Date : 2026-04-04
### Statut : EXECUTION PACK
### Objet : lancer le chantier VPS + Local AI Lab sans collision, sans fork logique, sans dérive de scope

---

# 0. Objet

Ce document dit exactement :

- dans quel ordre lancer les blocs
- quel outil utiliser en premier
- quel prompt donner à Codex
- quel prompt donner à Claude
- quel résultat exiger
- quel gate vérifier avant de passer au bloc suivant

Il est conçu pour un workflow réel :

1. **Codex** lit / structure / propose le plan d’implémentation précis
2. **Claude Code** code
3. **ChatGPT** audite la cohérence quant / risk / doctrine / prod-safety
4. **Claude Code** corrige
5. tests
6. merge si vert

---

# 1. Règles non négociables pour tous les prompts

## 1.1 Règles de scope
Toujours dire à Codex et Claude :

- ne pas sortir du bloc demandé
- ne pas modifier des fichiers hors scope sans nécessité absolue
- ne pas introduire de nouveau document canonique concurrent
- ne pas inventer de hooks, enums ou schemas non définis dans les MD fournis
- ne pas créer de fork logique local/VPS
- ne pas exécuter de code arbitraire injecté
- ne pas “améliorer” le projet hors demande

## 1.2 Règles de sortie
À chaque bloc, exiger :

- liste des fichiers créés / modifiés
- résumé du scope traité
- points non traités
- tests ajoutés
- résultats de tests
- risques résiduels
- verdict :
  - `MERGEABLE`
  - `NOT MERGEABLE`
  - `PARTIAL`

## 1.3 Règle de discipline
Aucun bloc suivant ne commence si le bloc courant n’a pas :

- scope traité
- tests verts
- audit logique
- corrections appliquées

---

# 2. Documents à charger avant le chantier

Avant de lancer les prompts, donner à Codex / Claude les documents suivants dans cet ordre :

1. `2026-04-04_V53_NEW_TARGET_CANONICAL_VPS_LOCAL_AI_LAB.md`
2. `2026-04-04_V53_PROD_SAFE_VPS_MIGRATION_PLAN.md`
3. `2026-04-04_V53_LOCAL_AI_LAB_PROD_SAFE_BUILD_PLAN.md`
4. `2026-04-04_V53_VPS_ANNEXE_MATH_RUNTIME_MARKET_PHYSICS.md`
5. `2026-04-04_V53_LOCAL_AI_LAB_ANNEXE_MATH_AND_BUILD_PLAN.md`
6. `2026-04-04_V53_PATCH_COLD_PATH_SAFE_RULE_COMPILATION.md`
7. `2026-04-04_V53_VPS_LAB_SYNC_MATRIX.md`

---

# 3. Bloc 1 — Freeze commun et langage partagé

## 3.1 But
Figer le langage commun :
- hooks
- action units
- lifecycle states
- taxonomy artifacts
- runtime modes
- profile scope
- shared enums

## 3.2 Utiliser d’abord
**Codex**

## 3.3 Prompt Codex

```text
Lis uniquement les documents canoniques et de synchronisation fournis pour V5.3 VPS + Local AI Lab.

Mission :
1. extraire le langage commun partagé à figer immédiatement :
   - runtime modes
   - profile scopes
   - artifact classes
   - action units
   - lifecycle states
   - hook scope vocabulary
   - reason code prefix conventions
2. identifier les collisions ou ambiguïtés éventuelles entre documents
3. proposer un fichier source-of-truth technique minimal à créer pour ces enums / vocabulaires
4. proposer l’emplacement exact dans le repo
5. ne code rien hors de ce scope

Sortie attendue :
- tableau des enums / vocabulaires
- collisions détectées
- fichiers exacts à créer
- ordre de création
- verdict MERGEABLE / NOT MERGEABLE
```

## 3.4 Puis utiliser
**Claude Code**

## 3.5 Prompt Claude

```text
À partir du plan validé pour le Bloc 1, code uniquement le freeze commun du langage partagé.

Scope autorisé :
- shared enums
- shared constants
- shared artifact taxonomy
- shared lifecycle states
- shared runtime modes
- shared hook/action vocabularies
- tests associés

Interdictions :
- ne pas coder de logique métier
- ne pas coder d’API
- ne pas coder de runtime hooks
- ne pas modifier les moteurs
- ne pas inventer de nouveaux termes

Résultat attendu :
- fichiers créés/modifiés
- tests unitaires
- résumé du scope traité
- risques résiduels
- verdict MERGEABLE / NOT MERGEABLE
```

## 3.6 Gate avant bloc 2
- enums figés
- aucune ambiguïté hook/action/lifecycle
- tests verts

---

# 4. Bloc 2 — VPS fondation runtime d’enrichissement

## 4.1 But
Préparer la VPS à recevoir la nouvelle doctrine sans casser le runtime :
- instrumentation
- protocols
- monitoring
- hook policy
- base artifact governance

## 4.2 Utiliser d’abord
**Codex**

## 4.3 Prompt Codex

```text
Mission :
proposer le plan d’implémentation exact du bloc VPS fondation pour la nouvelle doctrine V5.3.

Scope :
- meta/protocols/monitoring nécessaires à la nouvelle chaîne de preuve
- préparation artifact governance
- hook scope policy
- runtime snapshot typing (pas encore toute la logique finale)
- aucun enrichissement moteur direct hors cadre

Contraintes :
- ne pas réécrire les 17 builds
- ne pas casser la Light existante
- Build-14 reste d’abord READ_ONLY / SHADOW / LIMITED_INFLUENCE
- la VPS reste souveraine
- aucun code injecté

Sortie :
- fichiers exacts à créer/modifier
- ordre précis
- dépendances sur blocs précédents
- tests minimums
- risques de régression
```

## 4.4 Prompt Claude

```text
Code uniquement le bloc VPS fondation validé.

Scope autorisé :
- instrumentation/protocols/meta nécessaires
- hook scope policy
- premiers contrats artifact governance
- snapshots typés préparatoires
- monitoring minimal lié à ces nouvelles briques

Interdictions :
- ne pas activer C/D
- ne pas introduire de logique ML
- ne pas changer la logique A/B de production
- ne pas écrire de parsing JSON hot path
- ne pas ajouter de code injecté

Livrable :
- code
- tests
- résumé
- risques
- verdict MERGEABLE / NOT MERGEABLE
```

## 4.5 Gate avant bloc 3
- monitoring et protocols enrichis
- hook policy lisible
- aucun impact live non borné
- tests verts

---

# 5. Bloc 3 — Local AI Lab fondation

## 5.1 But
Construire le socle du Lab :
- locks
- datasets
- acquisition
- replay skeleton
- feature factory skeleton

## 5.2 Utiliser d’abord
**Codex**

## 5.3 Prompt Codex

```text
Mission :
planifier précisément le bloc de fondation du Local AI Lab.

Scope :
- Build-L0
- Build-L1
- Build-L2
- Build-L3 skeleton
- Build-L4 skeleton minimum

Objectif :
- verrouiller doctrine Lab
- construire dataset registry
- acquisition data
- base de replay sans fork logique
- feature factory conforme aux locks

Contraintes :
- shared core unique
- pas de logique de trading parallèle
- pas de feature hors Physics Lock
- pas de transform hors whitelist
- pas de LLM critique

Sortie attendue :
- arborescence fichiers
- ordre exact
- dépendances
- tests minimums
- points à geler avant replay parity
```

## 5.4 Prompt Claude

```text
Code uniquement le bloc de fondation du Local AI Lab validé.

Scope :
- doctrine locks
- dataset registry
- integrity checker
- data acquisition
- parquet partitioning
- replay skeleton
- feature factory skeleton

Interdictions :
- pas de micro-models avancés
- pas de distillation
- pas de closed-loop
- pas d’API upload VPS
- pas de fork logique de V5.3

Résultat attendu :
- fichiers créés/modifiés
- tests
- résumé du scope
- limitations actuelles
- verdict MERGEABLE / NOT MERGEABLE
```

## 5.5 Gate avant bloc 4
- locks fonctionnels
- datasets versionnés
- data acquisition saine
- replay skeleton en place
- tests verts

---

# 6. Bloc 4 — Parité replay + reason codes + explicabilité

## 6.1 But
Faire converger :
- replay local
- outputs VPS
- reason codes
- états décisionnels
- auditabilité

## 6.2 Utiliser d’abord
**Codex**

## 6.3 Prompt Codex

```text
Mission :
définir le chantier de convergence entre la VPS et le Lab sur :
- replay parity
- reason codes
- decision states
- evidence bundles
- outputs meta/protocol utiles au Lab

Tu dois :
1. identifier les contrats exacts à stabiliser
2. dire ce qui doit être modifié côté VPS
3. dire ce qui doit être modifié côté Lab
4. minimiser la surface de changement
5. préserver le shared core unique

Sortie :
- matrice de fichiers VPS / Lab
- dépendances exactes
- tests de parité à ajouter
- risques si reason codes instables
```

## 6.4 Prompt Claude

```text
Code uniquement le bloc de convergence replay / reason codes / explicabilité validé.

Scope autorisé :
- contrats nécessaires à la parité
- export de reason codes / decision states
- evidence bundles
- adaptation du replay bridge
- tests de parité

Interdictions :
- pas de nouvelle logique moteur
- pas de micro-models
- pas de distillation
- pas de closed-loop complet

Livrable :
- code
- tests de parité
- divergences restantes
- verdict MERGEABLE / NOT MERGEABLE
```

## 6.5 Gate avant bloc 5
- reason codes stables
- decision states stables
- evidence bundles exportables
- replay parity testable

---

# 7. Bloc 5 — Build-14 READ_ONLY + Lab calibration / micro-models

## 7.1 But
Faire entrer les readers Build-14 en lecture seule côté VPS et permettre au Lab de calibrer / diagnostiquer / modéliser sur des features réelles.

## 7.2 Utiliser d’abord
**Codex**

## 7.3 Prompt Codex

```text
Mission :
planifier le bloc de convergence suivant :
- Build-14 READ_ONLY côté VPS
- threshold calibration côté Lab
- micro-model lab V1 côté Lab

Objectif :
- les readers VPS existent vraiment
- le Lab les consomme proprement
- aucun enrichissement live non borné n’est activé

Tu dois proposer :
- quels readers introduire en premier
- quels outputs exporter
- quels seuils calibrer en priorité
- quels modèles autoriser en V1
- quels tests de non-régression ajouter
```

## 7.4 Prompt Claude

```text
Code uniquement ce bloc :
- readers Build-14 READ_ONLY côté VPS
- calibration V1 côté Lab
- micro-model trainer V1 côté Lab

Contraintes :
- aucune influence live non bornée
- pas de hard block nouveau en production
- pas de code injecté
- pas de deep learning lourd
- modèles tabulaires compacts uniquement

Résultat attendu :
- fichiers modifiés/créés
- tests
- métriques disponibles
- verdict MERGEABLE / NOT MERGEABLE
```

## 7.5 Gate avant bloc 6
- readers Build-14 présents
- outputs observables
- calibration fonctionnelle
- micro-models V1 utilisables
- tests verts

---

# 8. Bloc 6 — Distillation + compilation froide VPS

## 8.1 But
Raccorder :
- la distillation du Lab
- le schéma artifact final
- la compilation froide côté VPS
- les hooks bornés

## 8.2 Utiliser d’abord
**Codex**

## 8.3 Prompt Codex

```text
Mission :
définir le chantier de raccord entre :
- Build-L8 distillation du Lab
- schéma artifact final
- patch Cold-Path Safe Rule Compilation côté VPS
- runtime hook snapshots
- action units / caps / floors

Tu dois fournir :
- ordre exact de codage VPS vs Lab
- fichiers précis à créer de part et d’autre
- tests minimums
- points de collision possibles
- ce qui doit être figé avant d’aller plus loin
```

## 8.4 Prompt Claude

```text
Code uniquement le bloc :
- distillation Lab
- schéma artifact final
- compiled feature accessor / condition / action / rule / hook plan côté VPS
- compiled artifact registry
- tests associés

Interdictions :
- aucun parsing JSON hot path
- aucun eval/exec
- aucun code artifact injecté
- aucun hook hors scope
- aucune action sans unité explicite

Livrable :
- code
- tests unitaires compilation/runtime/lifecycle
- résumé
- verdict MERGEABLE / NOT MERGEABLE
```

## 8.5 Gate avant bloc 7
- artifact schema stable
- distillation stable
- compilation froide testée
- runtime hooks bornés
- tests verts

---

# 9. Bloc 7 — Proof protocol final + packaging + upload dry-run

## 9.1 But
Terminer la chaîne :
- preuve
- packaging
- signature
- upload dry-run VPS

## 9.2 Utiliser d’abord
**Codex**

## 9.3 Prompt Codex

```text
Mission :
définir le bloc de finalisation artifact :
- proof protocol final
- artifact packer & signer
- artifact governance API dry-run
- lifecycle validation
- tests dry-run end-to-end

Tu dois proposer :
- ordre exact
- fichiers
- dépendances
- dry-run scenarios
- failure cases à couvrir
```

## 9.4 Prompt Claude

```text
Code uniquement :
- Build-L9 proof protocol final
- Build-L10 artifact packer & signer
- artifact governance API dry-run côté VPS
- validation end-to-end sans activation live

Interdictions :
- aucun live direct
- aucun limited influence automatique
- aucun bypass lifecycle

Résultat attendu :
- code
- tests
- scénarios succès/échec
- verdict MERGEABLE / NOT MERGEABLE
```

## 9.5 Gate avant bloc 8
- artifacts signés
- upload dry-run validé
- lifecycle dry-run valide
- preuves présentes

---

# 10. Bloc 8 — Closed-loop + limited influence + multi-VPS

## 10.1 But
Mettre en place :
- batch closed-loop
- client closed-loop Lab
- limited influence réel gouverné
- control plane / multi-VPS awareness

## 10.2 Utiliser d’abord
**Codex**

## 10.3 Prompt Codex

```text
Mission :
planifier le dernier grand bloc :
- closed-loop batch VPS
- client closed-loop Lab
- limited influence réel gouverné
- control plane / multi-VPS

Tu dois imposer :
- batch only
- aucun streaming critique
- aucune dérive de souveraineté du Lab
- limited influence bornée
- monitoring obligatoire

Sortie :
- ordre exact
- fichiers
- tests
- gates avant activation
```

## 10.4 Prompt Claude

```text
Code uniquement :
- closed-loop batch export VPS
- fetch client Lab
- retrain dataset builder
- drift feedback builder
- limited influence bornée côté VPS
- control plane minimal + awareness multi-VPS côté Lab

Interdictions :
- aucun streaming critique
- aucun contrôle live direct par le Lab
- aucune activation illimitée d’artifacts
- aucun contournement de la souveraineté VPS

Résultat attendu :
- code
- tests
- métriques de monitoring
- verdict MERGEABLE / NOT MERGEABLE
```

## 10.5 Gate final
- batch closed-loop stable
- limited influence monitorée
- rollback disponible
- multi-VPS visible
- aucun fork logique

---

# 11. Prompt d’audit ChatGPT à utiliser après chaque bloc

Après chaque bloc, utilise ce prompt avec le diff / fichiers modifiés :

```text
Audit ce bloc en tant que :
- quant senior
- risk architect
- fintech infra architect
- dev python prod-safe
- reviewer anti-régression

Je veux :
1. verdict MERGEABLE / NOT MERGEABLE
2. P0 / P1 / P2
3. dérives doctrinales éventuelles
4. risques cachés
5. oublis de tests
6. incohérences avec :
   - canon cible
   - migration VPS
   - Local AI Lab
   - annexe math VPS
   - annexe math Lab
   - patch cold-path rule compilation
   - sync matrix
7. corrections minimales à faire avant merge
```

---

# 12. Prompt de correction Claude après audit

```text
Corrige uniquement les points P0 et P1 signalés par l’audit précédent.

Contraintes :
- ne touche pas au scope du bloc au-delà des corrections nécessaires
- ne rajoute pas de nouvelles fonctionnalités
- ne change pas les enums/schemas sans nécessité absolue
- ajoute ou corrige les tests nécessaires

Sortie :
- fichiers modifiés
- corrections appliquées
- tests mis à jour
- verdict final MERGEABLE / NOT MERGEABLE
```

---

# 13. Règle finale d’orchestration

L’ordre correct est :

1. Codex planifie le bloc
2. Claude code le bloc
3. ChatGPT audite le bloc
4. Claude corrige le bloc
5. tests
6. merge si vert
7. seulement ensuite bloc suivant

Si Codex ou Claude commencent à :
- élargir le scope
- inventer des concepts non canoniques
- créer un fork logique
- mélanger local et VPS
- rajouter du “smart” non demandé

alors il faut arrêter immédiatement et revenir au bloc.

---

# 14. Conclusion

Ce document n’est pas un plan théorique.

C’est le **pack d’orchestration réel** pour lancer le chantier sans collision entre :

- nouvelle VPS V5.3
- Local AI Lab
- patch runtime hooks
- artifact governance
- multi-VPS
- closed-loop

Le principe final est simple :

> un bloc à la fois
>
> scope strict
>
> audit systématique
>
> aucun fork logique
>
> aucune sophistication hors gate
