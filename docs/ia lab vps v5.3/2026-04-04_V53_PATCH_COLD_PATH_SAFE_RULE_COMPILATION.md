# V5.3 — PATCH CANONIQUE
## Cold-Path Safe Rule Compilation for VPS Runtime Hooks
### Date : 2026-04-04
### Statut : PATCH CANONIQUE À INTÉGRER AU CORPUS
### Portée : VPS Governance / Runtime Hooks / Build-14 limited influence / Artifact execution path

---

# 0. Objet

Ce patch formalise la mécanique canonique d’exécution des artifacts côté VPS dans le **hot path runtime**.

Il répond au problème suivant :

- un artifact doit rester **inerte et déclaratif**
- la VPS ne doit **jamais exécuter de code injecté**
- le hot path moteur / risk / scoring ne doit **pas parser du JSON** ni interpréter des chaînes à chaque passage
- la logique artifact doit rester :
  - sûre
  - bornée
  - monitorable
  - rapide
  - rollbackable

La solution retenue est :

> **Cold-Path Safe Rule Compilation**

Autrement dit :

- l’artifact reste un `THRESHOLD_JSON`, `LOOKUP_JSON` ou `RULE_AST_JSON`
- la VPS valide et compile cet artifact **au chargement**
- la VPS produit un **plan d’exécution compilé, sûr, pré-validé, pré-lié**
- le hot path exécute uniquement ce plan compilé

---

# 1. Pourquoi ce patch est nécessaire

## 1.1 Le problème CPU / latence

Si Engine B, Risk ou Scoring doivent, à chaque tick ou à chaque snapshot :

- parser du JSON
- résoudre des chaînes d’opérateurs
- vérifier des noms de features
- construire dynamiquement des actions
- interpréter du texte

alors le coût CPU devient non négligeable, ce qui dégrade directement :

- la latence utile
- la stabilité runtime
- la survivabilité d’exécution

## 1.2 Le problème sécurité

La doctrine V5.3 interdit :

- `eval`
- `exec`
- code Python injecté
- modèles opaques importés en runtime V1/V2
- ONNX runtime en V1/V2
- toute logique arbitraire exécutée depuis l’artifact

## 1.3 Le problème d’architecture

Le système doit concilier :

- **sécurité maximale**
- **hot path minimal**
- **artifacts gouvernés**
- **influence limitée Build-14**
- **rollback propre**

---

# 2. Décision canonique

## 2.1 Décision retenue

La VPS adopte un mécanisme de :

> **Cold-Path Safe Rule Compilation**

Ce mécanisme n’est pas un JIT au sens machine-code ou compilation native lourde.

Il s’agit de :

- validation stricte d’un artifact déclaratif
- compilation froide en objets d’exécution internes
- dispatch pré-lié d’opérateurs et d’actions
- exécution hot path sans parsing de schéma

## 2.2 Terminologie correcte

Termes recommandés :
- `cold-path compilation`
- `safe compiled hook plan`
- `precompiled dispatch plan`

Termes à éviter :
- “JIT” au sens fort
- “code runtime généré”
- “dynamic strategy execution”

---

# 3. Position dans l’architecture V5.3

Ce patch s’intègre à :

- `vps_governance`
- `runtime_hooks`
- `artifact lifecycle`
- `Build-14 limited influence`
- plus tard :
  - `Build-15`
  - `Build-16`
  - `Build-17`

Il ne modifie pas la doctrine centrale :

- l’artifact reste déclaratif
- la VPS reste souveraine
- aucun code n’est injecté
- le hook reste borné par scope
- la promotion reste gouvernée

---

# 4. Pipeline canonique

## 4.1 Étape A — Import

À l’import, la VPS effectue :

1. validation de schéma
2. validation de signature
3. validation du `artifact_scope`
4. validation des `allowed_hook_ids`
5. validation des `feature_id`
6. validation des `action_unit`
7. validation des caps / floors / unités

Sortie :
- artifact accepté ou rejeté

## 4.2 Étape B — Activation lifecycle

Quand l’artifact passe vers un état activable (`SHADOW_READY`, `LIMITED_INFLUENCE`, etc.) :

1. compilation des conditions
2. compilation des actions
3. compilation des extracteurs de features
4. génération d’un `CompiledHookPlan`
5. enregistrement dans le `compiled_artifact_registry`

## 4.3 Étape C — Hot path

Au runtime :

- le hook reçoit un snapshot typé
- il récupère le `CompiledHookPlan` du hook courant
- il évalue les règles précompilées
- il applique les actions précompilées
- il retourne score / adjustments / reason codes / debug minimal

Aucun parsing JSON ne doit avoir lieu dans le hot path.

---

# 5. Invariants non négociables

1. L’artifact importé reste **inerte**.
2. Aucun code Python ne peut être injecté.
3. Aucun opérateur hors liste blanche n’est autorisé.
4. Aucun `feature_id` hors snapshot de hook n’est autorisé.
5. Toute action doit avoir une unité explicite.
6. Toute action doit être bornée par cap/floor si applicable.
7. Toute compilation doit être versionnée.
8. Toute règle hot path doit être rollbackable.
9. Toute règle doit rester traçable jusqu’à son artifact d’origine.
10. Le hot path ne doit jamais dépendre d’une interprétation textuelle libre.

---

# 6. Mapping des opérateurs autorisés

## 6.1 Principe

Les opérateurs ne viennent jamais de l’utilisateur ou de l’artifact sous forme exécutable.

Ils sont mappés dans le code figé de la VPS.

## 6.2 Liste minimale V1

Opérateurs autorisés :

- `>`
- `>=`
- `<`
- `<=`
- `==`

Optionnel plus tard :
- `IN_RANGE`

## 6.3 Interdictions

Interdits :
- opérateurs arbitraires
- fonctions fournies par artifact
- expressions composées en texte libre
- lambdas injectées
- expressions Python sérialisées

---

# 7. Compilation des features

## 7.1 Règle canonique

Le hot path ne doit pas faire un `getattr()` naïf non contrôlé depuis un nom arbitraire.

Au cold path, la VPS doit :

1. vérifier que `feature_id` est autorisé pour le hook
2. vérifier qu’il existe dans le snapshot typé
3. construire un **feature accessor pré-validé**
4. enregistrer le type attendu

## 7.2 Objet recommandé

### `CompiledFeatureAccessor`

Contenu minimal :
- `feature_id`
- `hook_id`
- `accessor_fn`
- `expected_python_type`
- `null_policy`
- `nan_policy`

## 7.3 Politique de valeurs manquantes

En V1, règle prudente :

- `missing` -> condition `False`
- `None` -> condition `False`
- `NaN` -> condition `False`

avec possibilité de log debug / metrics.

Aucune exception runtime ne doit remonter au hot path pour un `None` ou `NaN` inattendu.

---

# 8. Compilation des conditions

## 8.1 Objet recommandé

### `CompiledCondition`

Contenu minimal :
- `condition_id`
- `feature_accessor`
- `operator_fn`
- `threshold`
- `lower_threshold` / `upper_threshold` si range
- `null_policy`
- `nan_policy`

## 8.2 Règle

Une condition compilée doit être :

- pure
- déterministe
- sans effet de bord
- exécutable sans allocation inutile
- limitée à la lecture du snapshot et à la comparaison

## 8.3 Évaluation

L’évaluation d’une condition doit retourner :
- `True`
- `False`

Elle ne doit pas muter le snapshot ni appeler d’autres sous-systèmes.

---

# 9. Compilation des actions

## 9.1 Principe

Le hot path ne doit pas faire de dispatch textuel d’action à chaque évaluation.

Les actions doivent elles aussi être compilées à l’activation.

## 9.2 Objet recommandé

### `CompiledAction`

Contenu minimal :
- `action_type`
- `action_value`
- `action_unit`
- `apply_fn`
- `max_raw_score_cap`
- `min_floor`
- `max_abs_delta`
- `reason_code`

## 9.3 Unités obligatoires

Au runtime, les actions doivent toujours porter une unité explicite :

- `RAW_SCORE_MULTIPLIER`
- `RAW_SCORE_ADD`
- `CONVICTION_ADD`
- `SIZE_FACTOR`
- `RANK_DELTA`
- `TIMEOUT_FACTOR`

## 9.4 Bornes obligatoires

Pour éviter les explosions de score ou de taille, les actions doivent pouvoir embarquer :

- `max_raw_score_cap`
- `min_floor`
- `max_abs_delta`

Aucune action multiplicative ou additive non bornée ne doit être acceptée en hot path.

---

# 10. Compilation des règles

## 10.1 Objet recommandé

### `CompiledRule`

Contenu minimal :
- `rule_id`
- `conditions`
- `logical_op`
- `compiled_action`
- `support_count`
- `fragility_score`
- `artifact_id`
- `artifact_version`

## 10.2 Évaluation canonique

La règle compilée doit utiliser :

- `all()` pour `AND`
- `any()` pour `OR`

avec short-circuit naturel.

## 10.3 Règle de complexité

Le complexity budget du Lab et de la VPS reste applicable :

- peu de features
- peu de conditions
- peu de branches
- règles compréhensibles
- pas de logique combinatoire cachée

---

# 11. Plan compilé par hook

## 11.1 Objet recommandé

### `CompiledHookPlan`

Contenu minimal :
- `hook_id`
- `artifact_id`
- `artifact_version`
- `lifecycle_state`
- `compiled_rules`
- `schema_version`
- `compiled_at`
- `payload_hash_sha256`

## 11.2 Principe

Chaque hook runtime ne doit exécuter **que** les règles compilées qui lui appartiennent.

Exemples :
- `ENGINE_B_SWEEP_VALIDATION`
- `RISK_MICRO_FRICTION_PRECHECK`
- `SCORING_SOFT_PENALTY_LAYER`

Aucune liste hétérogène de règles ne doit être parcourue dans un hook moteur donné.

---

# 12. Registry de compilation

## 12.1 Objet recommandé

### `CompiledArtifactRegistry`

Mission :
- stocker les plans compilés actifs
- les indexer par hook
- les invalider au changement de version
- les reconstruire au redémarrage
- exposer un état de compilation au monitoring

## 12.2 Clés minimales

Clé logique :
- `artifact_id`
- `artifact_version`
- `hook_id`
- `schema_version`

## 12.3 Règle de lifecycle

Quand un artifact passe :
- en `DORMANT`
- en `EXPIRED`
- ou est rollbacké

alors son `CompiledHookPlan` doit être retiré ou désactivé du registry actif.

---

# 13. Politique hot path

## 13.1 Ce qui est autorisé

Le hot path peut :
- lire un snapshot typé
- exécuter des conditions précompilées
- appliquer des actions précompilées
- produire des reason codes
- accumuler des ajustements bornés

## 13.2 Ce qui est interdit

Le hot path ne doit jamais :
- parser du JSON
- faire du dispatch textuel libre
- appeler `eval`
- appeler `exec`
- charger du code
- résoudre dynamiquement des modules
- reconstruire des règles depuis le payload brut

## 13.3 Vocabulaire de performance

Le but est :
- overhead minimal
- temps constant raisonnable
- micro-overhead borné

Le canon ne doit pas promettre des “nanosecondes”.
Il doit promettre :
- **pas de parsing**
- **pas d’interprétation libre**
- **plan précompilé**
- **coût borné**

---

# 14. Intégration recommandée dans le code

## 14.1 Emplacements recommandés

```text
src/vps_governance/
├── runtime_hooks/
│   ├── compiled_feature_accessor.py
│   ├── compiled_condition.py
│   ├── compiled_action.py
│   ├── compiled_rule.py
│   ├── compiled_hook_plan.py
│   ├── engine_a_hooks.py
│   ├── engine_b_hooks.py
│   ├── engine_c_hooks.py
│   ├── engine_d_hooks.py
│   ├── scoring_hooks.py
│   ├── risk_hooks.py
│   └── portfolio_hooks.py
│
├── services/
│   ├── hook_plan_compiler.py
│   ├── compiled_artifact_registry.py
│   ├── signature_verifier.py
│   ├── artifact_schema_validator.py
│   ├── lifecycle_manager.py
│   └── hook_injector_service.py
```

## 14.2 Snapshot typing

Chaque hook doit posséder son snapshot typé :

- `EngineBHookSnapshot`
- `RiskHookSnapshot`
- `ScoringHookSnapshot`
- etc.

Une règle ne peut référencer qu’une feature présente dans le snapshot du hook.

---

# 15. Monitoring et observabilité

## 15.1 Le système doit exposer

- nombre de plans compilés actifs
- plans compilés par hook
- dernière compilation
- compilation failed count
- règles actives par artifact
- invalid feature reference count
- runtime evaluation count
- runtime match count
- action application count

## 15.2 But

Permettre de répondre à :
- quel artifact influence quel hook ?
- depuis quand ?
- combien de fois ?
- avec quel reason code dominant ?
- quel coût CPU supplémentaire ?

---

# 16. Tests obligatoires

## 16.1 Tests de compilation
- opérateur autorisé compilé correctement
- opérateur interdit rejeté
- feature hors hook rejetée
- feature manquante rejetée au cold path
- action unit absente rejetée
- cap/floor invalides rejetés

## 16.2 Tests de runtime
- `AND` short-circuit correct
- `OR` short-circuit correct
- `None` -> false
- `NaN` -> false
- action bornée correctement
- score cap respecté
- floor respecté
- reason code propagé

## 16.3 Tests lifecycle
- compilation à activation
- retrait à `DORMANT`
- retrait à `EXPIRED`
- recompilation à nouvelle version
- rollback vers version précédente

## 16.4 Tests de non-régression perf
- pas de parsing JSON hot path
- plan récupéré depuis registry
- coût de hook borné
- absence d’allocation inutile évidente dans boucle critique

---

# 17. Relation avec Build-14

## 17.1 Principe

Ce patch n’autorise pas une explosion d’influence artifact.

Il donne simplement une mécanique sûre pour exécuter ce qui a été gouverné.

## 17.2 Rappel doctrine Build-14

Build-14 doit rester :
- lecture
- shadow
- influence limitée

Ce patch sert à exécuter cette influence limitée correctement, pas à contourner la gouvernance.

---

# 18. Relation avec le Local AI Lab

Le Lab ne produit pas du code.
Le Lab produit :
- conditions
- actions
- thresholds
- caps
- reason codes
- scope

La VPS :
- valide
- compile
- active
- désactive
- surveille

La souveraineté reste du côté VPS.

---

# 19. Règles finales à intégrer au canon

1. Tout artifact runtime reste déclaratif.
2. Toute exécution runtime artifact passe par une compilation froide.
3. Toute condition runtime doit utiliser des accessors pré-validés.
4. Toute action runtime doit être précompilée et bornée.
5. Aucun parsing JSON n’est autorisé dans le hot path.
6. Aucun code injecté n’est autorisé.
7. Tout hook ne voit que ses règles autorisées.
8. Toute compilation est versionnée et traçable.
9. Toute règle runtime est monitorable.
10. Toute désactivation lifecycle retire le plan compilé actif.

---

# 20. Conclusion

Ce patch ajoute au corpus V5.3 la mécanique opérationnelle manquante entre :

- **artifact déclaratif sécurisé**
- **et runtime hook exécutable à faible overhead**

La formulation correcte à retenir est :

> **Cold-Path Safe Rule Compilation**
>  
> et non :
>  
> “code dynamique exécuté en runtime”.

C’est ce mécanisme qui permet de concilier :

- sécurité
- gouvernance
- latence bornée
- influence limitée
- et survivabilité d’exécution.
