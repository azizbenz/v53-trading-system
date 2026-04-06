# V5.3 — PATCH P1 TRANSVERSE POLICIES
## Schema Versioning / Runtime Error Policy / Key Management / Interim Math Hygiene
### Date : 2026-04-05
### Statut : PATCH NORMATIF COMPLÉMENTAIRE AU FREEZE P0
### Portée : Local AI Lab / VPS Governance / Runtime Hooks / Artifact Lifecycle / Signature Path

---

# 0. Objet

Ce document complète le **freeze P0 du corpus**.

Il ne rouvre pas la doctrine centrale.
Il ne modifie pas les hooks, les action units, ni la hiérarchie documentaire déjà gelés.

Son rôle est plus ciblé :

1. définir une **Schema Versioning Policy**
2. définir une **Runtime Error Policy**
3. définir une **Key Management Policy** pour Ed25519
4. définir une **hygiène mathématique intérimaire** pour éviter le flottement documentaire avant nettoyage complet

Ce document doit être lu comme un **patch transversal P1** :
- après le freeze P0
- avant les implémentations artifact upload / lifecycle réel / limited influence réel
- avant toute accélération Codex sur les blocs artifact-governance

---

# 1. Position dans la séquence de chantier

## 1.1 Place correcte

Ce patch intervient :

- après le document de freeze P0 du corpus
- après le gel des hooks, enums et axes de lifecycle
- avant :
  - `schema validator`
  - `upload route`
  - `signature verifier`
  - `lifecycle route`
  - `TTL manager`
  - `circuit breaker`
  - `cold-path activation` réelle
  - `artifact upload dry-run`
  - `LIMITED_INFLUENCE` réel

## 1.2 But opérationnel

Le but n’est pas d’ajouter du “smart”.

Le but est d’éviter quatre dérives très concrètes :

1. qu’un dev invente sa propre logique de compatibilité de schéma
2. qu’un runtime hook plante sans politique claire de repli
3. qu’une clé Ed25519 soit gérée de manière artisanale
4. qu’une formule incomplète soit codée “au feeling” dans le runtime

---

# 2. Schema Versioning Policy

## 2.1 Principe général

Un artifact n’est pas seulement un bundle signé.

C’est aussi un objet gouverné par des **versions de langage**.
La VPS ne doit jamais interpréter un artifact dans une grammaire qu’elle ne connaît pas.

Donc :

- la **version de schéma** est obligatoire
- la **version du feature set** est obligatoire
- la **version du transform set** est obligatoire
- la compatibilité est décidée par la **VPS**
- le Lab peut produire un artifact
- le Lab ne décide jamais seul de la compatibilité finale

## 2.2 Trois familles de versions à distinguer

### A. `artifact_schema_version`
Décrit la structure du bundle artifact :
- champs obligatoires
- contrats JSON
- objets imbriqués
- enums supportés
- formats de payload

### B. `feature_set_version`
Décrit le dictionnaire de features autorisées :
- noms de features
- sémantique
- unités
- availability par hook
- lineage attendu

### C. `transform_set_version`
Décrit la whitelist des transformations autorisées :
- normalisations
- agrégations
- rolling transforms
- winsorisation
- clipping
- tout autre transform officiellement supporté

## 2.3 Format canonique

Le format canonique recommandé est :

`MAJOR.MINOR.PATCH`

Exemples :
- `1.0.0`
- `1.2.0`
- `2.0.0`

Règle :
- `MAJOR` = breaking change
- `MINOR` = extension rétro-compatible
- `PATCH` = correction documentaire / validation / bugfix sans changement de structure métier

## 2.4 Autorité de version

### Le Lab
Le Lab :
- produit l’artifact
- renseigne les versions
- signe le bundle
- ne décide pas de l’acceptation finale

### La VPS
La VPS :
- maintient la table de compatibilité
- accepte ou rejette
- peut refuser un artifact parfaitement signé si la version est inconnue ou incompatible

### Le corpus canonique
Le corpus :
- définit la signification des versions
- définit les règles de changement
- interdit les conversions implicites non tracées

## 2.5 Règles de compatibilité

### Cas 1 — `artifact_schema_version` inconnue
Action :
- **rejet immédiat**
- aucun import actif
- aucun dry-run “success”
- log explicite : `ARTIFACT_SCHEMA_UNKNOWN`

### Cas 2 — `artifact_schema_version` connue mais `MAJOR` incompatible
Action :
- **rejet immédiat**
- raison : `ARTIFACT_SCHEMA_MAJOR_INCOMPATIBLE`

### Cas 3 — même `MAJOR`, `MINOR` plus récente mais non enregistrée
Action :
- rejet par défaut en V1
- pas de “best effort parsing”
- pas d’acceptation partielle silencieuse

### Cas 4 — même `MAJOR.MINOR`, `PATCH` différent
Action :
- acceptable seulement si la VPS a explicitement déclaré ce `PATCH` supporté
- à défaut : rejet conservateur

## 2.6 Politique V1 de sécurité

En V1, la politique canonique est volontairement stricte :

> **pas d’auto-migration côté VPS**
>
> **pas de parsing permissif**
>
> **pas d’interprétation “approximative”**

Donc :

- la VPS valide
- ou rejette
- mais ne réécrit jamais un artifact entrant à la volée

## 2.7 Migration de schéma

La migration de schéma doit se faire :

- dans le Lab ou dans un outil offline gouverné
- jamais dans le hot path
- jamais dans la route d’activation runtime
- toujours avec traçabilité explicite

Sortie attendue :
- ancien artifact
- nouvelle version produite
- mapping de migration
- hash avant / après
- re-signature
- nouvelle preuve si la structure métier a changé

## 2.8 Quand une re-signature est obligatoire

La re-signature est obligatoire si change :
- `artifact_schema_version`
- contenu métier
- règles
- features utilisées
- transforms utilisées
- hooks autorisés
- thresholds / caps / floors / action values
- lifecycle policy
- tout champ participant au payload signé

## 2.9 Table minimale de compatibilité à exposer

La VPS doit maintenir une table ou registry équivalent contenant au minimum :

- `artifact_schema_version`
- `feature_set_version`
- `transform_set_version`
- statut :
  - `SUPPORTED`
  - `DEPRECATED`
  - `REJECTED`
- date d’activation
- date éventuelle de fin de support
- note de migration

## 2.10 Politique de dépréciation

Une version dépréciée peut encore être :
- lisible
- vérifiable
- monitorable

Mais elle ne doit pas nécessairement rester :
- uploadable
- activable
- promouvable

La VPS peut donc :
- accepter lecture / audit
- refuser activation
- exiger migration puis re-signature

## 2.11 Erreurs minimales à normaliser

Codes recommandés :

- `ARTIFACT_SCHEMA_UNKNOWN`
- `ARTIFACT_SCHEMA_MAJOR_INCOMPATIBLE`
- `ARTIFACT_SCHEMA_MINOR_UNSUPPORTED`
- `FEATURE_SET_UNKNOWN`
- `FEATURE_SET_INCOMPATIBLE`
- `TRANSFORM_SET_UNKNOWN`
- `TRANSFORM_SET_INCOMPATIBLE`
- `ARTIFACT_REQUIRES_MIGRATION`

## 2.12 Règle finale

En cas de doute de compatibilité :

> la VPS rejette

et n’essaie jamais d’“aider” en interprétant un schéma qu’elle ne maîtrise pas.

---

# 3. Runtime Error Policy

## 3.1 Principe général

Le runtime V5.3 ne doit pas devenir fragile à cause d’un artifact.

Un artifact doit être :

- déclaratif
- compilé à froid
- borné
- monitorable
- désactivable

Donc si un `CompiledHookPlan` échoue au runtime :

- le système protège d’abord le runtime
- puis isole l’artifact
- puis journalise
- puis retire ou dégrade si nécessaire

## 3.2 Règle de souveraineté runtime

La logique artifact est **subordonnée** à la logique métier baseline V5.3.

Donc en cas d’exception artifact locale :

- on ne casse pas le process principal
- on ne laisse pas une exception non gérée remonter aveuglément
- on ne continue pas à appliquer un artifact instable comme si de rien n’était

## 3.3 Politique canonique de repli

### Cas A — exception localisée sur un artifact / hook / snapshot
Action immédiate :
1. ne pas appliquer l’influence de cet artifact pour l’événement courant
2. revenir au comportement baseline du moteur / risk / scoring / portfolio concerné
3. journaliser l’erreur
4. incrémenter les métriques d’erreur
5. marquer l’artifact comme “sous surveillance”

Formulation correcte :

> fail-open vers la baseline V5.3  
> fail-closed vis-à-vis de l’influence artifact

### Cas B — erreurs répétées mais non systémiques
Action :
- passage en `REVIEW_REQUIRED` si seuil de fréquence dépassé
- possible retrait de l’influence runtime
- alerte opérateur
- blocage de promotion

### Cas C — erreur grave ou corruption probable
Exemples :
- compiled registry incohérent
- accessor typé invalide
- hook plan introuvable alors qu’annoncé actif
- crash répété immédiat sur chargement
- violation d’invariant de sécurité

Action :
- passage direct à `DORMANT`
- retrait du `CompiledHookPlan`
- rollback vers version précédente si disponible
- alerte de sévérité haute

## 3.4 Ce qu’il ne faut jamais faire

Interdit :

- laisser une exception artifact tuer silencieusement le hot path
- réessayer indéfiniment dans la boucle critique
- reconstruire dynamiquement un plan compilé dans le hot path
- convertir une erreur de sécurité en warning inoffensif
- promouvoir un artifact ayant généré des exceptions runtime non élucidées

## 3.5 Classification minimale des erreurs runtime

### Classe R1 — input invalide local
Exemples :
- `None`
- `NaN`
- feature absente localement
- type inattendu mais non structurel

Réponse :
- influence ignorée pour l’événement
- log
- compteur

### Classe R2 — erreur d’évaluation de règle
Exemples :
- comparaison impossible
- accessor compilé incohérent
- condition corrompue

Réponse :
- influence ignorée
- log erreur
- compteur
- possible `REVIEW_REQUIRED`

### Classe R3 — erreur d’intégrité de plan compilé
Exemples :
- plan incomplet
- action compilée invalide
- mismatch hook <-> action

Réponse :
- retrait immédiat du plan
- `DORMANT`
- rollback si possible

### Classe R4 — erreur systémique d’infrastructure artifact
Exemples :
- registry compilé indisponible
- corruption mémoire / cache du plan
- invariants lifecycle violés

Réponse :
- désactivation de l’influence artifact du hook concerné
- mode dégradé
- alerte haute priorité

## 3.6 Seuils de réaction

Les seuils exacts peuvent être configurables.
La politique canonique impose au minimum :

- un seuil de comptage absolu
- un seuil de fréquence par fenêtre temporelle
- un seuil “panic” conduisant à `DORMANT`

Exemple de logique acceptable :
- événement isolé : log + métrique
- répétition sur fenêtre courte : `REVIEW_REQUIRED`
- répétition sévère ou erreur R3/R4 : `DORMANT`

## 3.7 Métriques obligatoires

Le monitoring doit au minimum exposer :

- `artifact_hook_runtime_exceptions_total`
- `artifact_hook_runtime_exceptions_by_artifact`
- `artifact_auto_review_required_total`
- `artifact_auto_dormant_total`
- `compiled_plan_lookup_failures_total`
- `compiled_plan_rollbacks_total`
- `hook_eval_latency_p95`
- `hook_eval_latency_p99`

## 3.8 Logs obligatoires

Pour toute erreur runtime artifact, logger au minimum :

- `artifact_id`
- `artifact_version`
- `key_id`
- `hook_id`
- `runtime_mode`
- `pair`
- `timestamp`
- `error_class`
- `reason_code`
- `activation_stage`
- `health_state`
- `fallback_applied`
- `rollback_triggered`

## 3.9 Règle de promotion

Aucun artifact ne peut passer vers un stade plus élevé si, sur la fenêtre considérée, il présente :

- des erreurs R3
- des erreurs R4
- ou une fréquence d’erreurs R2 supérieure au seuil admis

## 3.10 Règle finale

En cas d’erreur runtime :

> la priorité est la continuité sûre du runtime baseline  
> jamais la préservation coûte que coûte de l’influence artifact

---

# 4. Key Management Policy — Ed25519

## 4.1 Principe général

La signature artifact n’a de valeur que si la gestion de clé est disciplinée.

La règle canonique est :

- la **clé privée** reste côté Lab ou environnement de signature contrôlé
- la **clé publique** est distribuée à la VPS et au control plane
- la VPS vérifie
- la VPS ne signe pas à la place du Lab

## 4.2 Génération de clé

La paire Ed25519 doit être générée :

- hors VPS
- dans un environnement local maîtrisé
- avec un générateur cryptographique standard du système ou de bibliothèque reconnue
- jamais dans un script ad hoc improvisé dans le repo

## 4.3 Identité de clé

Chaque clé doit avoir un identifiant stable :

`key_id`

Exemples :
- `lab_ed25519_2026_q2_k1`
- `lab_ed25519_2026_q3_k2`

Tout artifact signé doit embarquer :
- `key_id`
- signature
- payload hash

## 4.4 Stockage de la clé privée

La clé privée ne doit jamais :

- être commitée dans Git
- être copiée dans les configs versionnées
- être envoyée à la VPS
- être stockée en clair dans un dossier partagé de travail

Stockage acceptable V1 :
- fichier local chiffré
- secret store OS
- coffre-fort local
- support offline chiffré

## 4.5 Sauvegarde minimale

Il doit exister au minimum :

- une copie primaire chiffrée
- une copie de secours chiffrée
- une procédure écrite de récupération

Les copies de secours ne doivent pas être sur le même support unique.
La perte d’un PC ne doit pas faire perdre irréversiblement la capacité de signer.

## 4.6 Rotation de clé

La rotation doit être supportée nativement.

Procédure canonique :

1. générer nouvelle paire
2. publier nouvelle clé publique + `key_id`
3. ajouter la nouvelle clé au trust store VPS / control plane
4. conserver l’ancienne clé publique tant que des artifacts valides historiques y référencent encore
5. commencer à signer les nouveaux artifacts avec la nouvelle clé
6. déprécier l’ancienne clé selon politique

## 4.7 Révocation

Une clé doit pouvoir être marquée :

- `ACTIVE`
- `DEPRECATED`
- `REVOKED`

### Clé `DEPRECATED`
- encore vérifiable
- non recommandée pour nouveaux artifacts

### Clé `REVOKED`
- plus aucun nouvel artifact accepté
- tout artifact futur signé avec cette clé doit être rejeté

## 4.8 Compromission suspectée

Si compromission de clé privée suspectée :

1. marquer la clé `REVOKED`
2. alerter le control plane
3. refuser tout nouvel artifact signé avec cette clé
4. revoir les artifacts actifs signés avec cette clé
5. selon gravité :
   - `REVIEW_REQUIRED`
   - ou `DORMANT`
6. re-signer les artifacts encore légitimes avec une nouvelle clé si nécessaire

## 4.9 Perte de la clé privée sans compromission connue

Si la clé privée est perdue mais non compromise :

- les anciens artifacts restent vérifiables via la clé publique
- il devient impossible de signer de nouveaux artifacts avec cette clé
- il faut générer une nouvelle paire
- mettre à jour le trust store
- reprendre la signature avec le nouveau `key_id`

Ce cas ne justifie pas automatiquement la mise à `DORMANT` des artifacts historiques.

## 4.10 Multi-signature

En V1 :
- **non obligatoire**
- optionnelle plus tard
- ne pas compliquer le pipeline initial

La règle V1 est :
- une signature valide
- un `key_id` traçable
- un trust store explicite
- une révocation explicite

## 4.11 Trust store VPS / Control Plane

Le trust store doit contenir au minimum :

- `key_id`
- clé publique
- statut (`ACTIVE`, `DEPRECATED`, `REVOKED`)
- date d’entrée en service
- date éventuelle de révocation
- commentaire opératoire

## 4.12 Erreurs minimales à normaliser

- `SIGNATURE_INVALID`
- `KEY_ID_UNKNOWN`
- `KEY_REVOKED`
- `PAYLOAD_HASH_MISMATCH`
- `TRUST_STORE_UNAVAILABLE`

## 4.13 Règle finale

La signature ne doit jamais être traitée comme un simple détail technique.

Elle fait partie de la souveraineté runtime.

---

# 5. Interim Math Hygiene Policy

## 5.1 Objet

Ce document ne remplace pas le nettoyage mathématique complet.
Mais il impose des règles minimales pour empêcher le codage arbitraire.

## 5.2 Coefficients non définis

Tout coefficient non défini explicitement dans le corpus doit être traité comme :

`TO_CALIBRATE`

et non comme :
- valeur inventée par le dev
- constante sortie d’un notebook
- paramètre implicite durci sans trace

Cela concerne notamment les familles de coefficients du type :
- `w1, w2, w3`
- `d1, d2, d3, d4`
- `c1, c2, c3, ...`

## 5.3 Règle de codage

Tant qu’un coefficient n’est pas figé :

- pas d’usage live implicite
- pas de hardcode silencieux
- pas de promotion runtime finale
- seulement :
  - placeholder typé
  - config explicitée
  - calibration documentée
  - valeur par défaut officiellement approuvée si elle existe

## 5.4 Deux versions de delta proxy

La lecture canonique intérimaire est :

### Version par défaut
`(C - O) / max(H - L, epsilon) * V`

Usage :
- Lab
- replay
- diagnostics
- calibration
- distillation

### Version fallback
`sign(C - O) * V`

Usage :
- validation croisée
- fallback robuste
- cas de données plus pauvres

Aucun développeur ne doit laisser ces deux versions coexister sans nommage explicite.

## 5.5 Variables non définies à neutraliser

Si une grandeur apparaît dans une équation mais n’est pas définie de façon opérationnelle dans le corpus, alors :

- elle ne doit pas être codée comme variable runtime canonique
- elle peut rester :
  - en note de recherche
  - en placeholder documenté
  - en candidat de futur addendum mathématique

Cela vise explicitement, tant qu’aucun addendum formel ne les définit :
- `Fragility_t`
- `ReformationScore_t`

## 5.6 Conséquence runtime

Aucune logique de production ne doit dépendre d’une variable non définie formellement.

Si une formule y fait référence :
- soit la variable est remplacée par une grandeur déjà canonique
- soit la formule reste en statut recherche / shadow only
- soit elle est suspendue jusqu’au correctif math dédié

## 5.7 Règle finale

Le math runtime V5.3 doit rester :

- utile
- traçable
- calibrable
- auditable

Jamais décoratif.
Jamais implicite.

---

# 6. Impacts documentaires à propager

Les décisions de ce patch doivent être propagées au minimum dans :

- `2026-04-04_V53_LOCAL_AI_LAB_FINAL_UNIQUE_CANON.md`
- `2026-04-04_V53_LOCAL_AI_LAB_IMPLEMENTATION_BLUEPRINT.md`
- `2026-04-04_V53_PATCH_COLD_PATH_SAFE_RULE_COMPILATION.md`
- `2026-04-04_V53_ORCHESTRATION_PROMPT_PACK_CODEX_CLAUDE.md`

Propagation attendue :

## Dans le canon final
- politique de versionnement
- politique de gestion de clés
- rappel de politique d’erreur runtime

## Dans le blueprint
- `schema validator`
- trust store
- lifecycle manager
- error counters / error metrics
- contrats `key_id`, version fields, trust policy

## Dans le patch cold-path
- politique de repli runtime
- classes d’erreurs
- retrait à `DORMANT`
- rollback / quarantine policy

## Dans l’orchestration
- lecture correcte : P0 puis ce patch P1 avant accélération artifact-governance

---

# 7. Ordre recommandé après ce patch

1. appliquer le freeze P0 au corpus
2. intégrer ce patch P1 transversal
3. seulement ensuite :
   - bloc VPS artifact governance
   - bloc Lab artifact packer & signer
   - upload dry-run
   - lifecycle réel
   - limited influence réel

---

# 8. Conclusion finale

Le freeze P0 règle le langage partagé.

Ce patch P1 règle les **politiques transverses minimales** sans lesquelles le langage partagé resterait encore vulnérable à :

- des schémas interprétés au hasard
- des erreurs runtime mal gérées
- des signatures mal gouvernées
- des équations codées sans discipline

La formule correcte est donc :

> **P0 gèle le vocabulaire**
>
> **P1 gèle les politiques critiques**
>
> **et seulement ensuite on accélère l’implémentation artifact-governance**
