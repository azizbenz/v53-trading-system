# V5.3 — BUILD-1 SPECS MODULES
## Dependency Architecture Pack
### Specs détaillées module par module
### Point de départ officiel du développement
### Sans code — prod-safe

---

# 0. Objet du document

Ce document couvre **Build-1** du plan officiel V5.3.

Build-1 a une mission unique :

> verrouiller l’architecture logicielle avant tout développement métier.

Les modules couverts ici sont :

1. `interface_contracts`
2. `manifest_registry`
3. `dag_validator`
4. `contract_test_suite`
5. `smoke_bootstrap_recovery`

Aucun autre développement ne doit commencer tant que ces cinq modules ne sont pas correctement spécifiés, testés et gelés.

---

# 1. Principes Build-1

## 1.1 Objectif stratégique

Build-1 ne produit pas de PnL.  
Il produit quelque chose de plus important :

- une base stable
- une architecture non ambigüe
- un langage commun pour Claude Pro et ChatGPT Pro
- un socle qui empêche la dette technique de contaminer tout le projet

## 1.2 Critère de réussite

Build-1 est réussi si :

- tous les modules futurs ont des interfaces explicites
- l’ordre des dépendances est contrôlé
- les imports interdits sont détectés
- les tests de contrat sont industrialisables
- un bootstrap / restart propre est démontrable

## 1.3 Critère d’échec

Build-1 échoue si :

- des modules peuvent encore importer ce qu’ils veulent
- les formats d’input/output restent implicites
- les smoke tests sont absents
- le manifest n’est pas la vraie source d’inventaire
- un redémarrage peut casser silencieusement l’état

---

# 2. Vocabulaire officiel Build-1

## 2.1 Contrat
Définition minimale, stable, testable d’une interface :
- inputs
- outputs
- invariants
- types métier
- erreurs attendues

## 2.2 Manifest
Registre versionné décrivant :
- les modules
- leur couche
- leur ownership
- leurs dépendances autorisées
- leur ordre de build
- leur profil d’activation

## 2.3 DAG
Graphe orienté acyclique des dépendances entre modules.

## 2.4 Smoke test
Test minimal de démarrage / reprise destiné à vérifier qu’un module ou un build peut :
- démarrer
- initialiser ses ressources
- redémarrer proprement
- échouer explicitement si conditions non remplies

---

# 3. MODULE 1 — INTERFACE_CONTRACTS

## 3.1 Nom canonique
`interface_contracts`

## 3.2 Mission

Fournir le langage officiel de communication entre modules.

Ce module doit empêcher :
- les formats implicites
- les dictionnaires libres sans validation
- les ambiguïtés de structure
- les entrées/sorties changeantes selon le contexte

## 3.3 Responsabilités exactes

- définir les interfaces publiques des modules
- définir les types métier stables
- définir les structures minimales d’événements, signaux, décisions, ordres, métriques
- exposer les invariants contractuels à tester
- servir de référence commune aux développeurs et aux IA

## 3.4 Ce que ce module ne doit pas faire

- contenir la logique métier
- importer des implémentations concrètes
- effectuer des calculs d’edge
- gérer le runtime
- servir de “sac à types” sans hiérarchie

## 3.5 Sous-composants

### 3.5.1 domain_types
Rôle :
- définir les types métier élémentaires

Exemples attendus :
- PairId
- EngineId
- RegimeId
- ProfileId
- DeploymentState
- TradeId
- OrderId
- RunId

### 3.5.2 market_event_contracts
Rôle :
- définir les structures de données de marché

Exemples attendus :
- TradeEvent
- DepthEvent
- KlineEvent
- HeartbeatEvent
- SnapshotEvent

### 3.5.3 decision_contracts
Rôle :
- définir les structures de décision

Exemples attendus :
- SignalCandidate
- ScorePayload
- RiskDecision
- ExecutionIntent
- PortfolioDecision

### 3.5.4 meta_contracts
Rôle :
- définir les objets d’observabilité

Exemples attendus :
- DTRRecord
- PairHealthStatus
- CostRecord
- EdgeEstimate
- AlertRecord

### 3.5.5 error_contracts
Rôle :
- définir les erreurs métier standardisées

Exemples :
- DataStaleError
- DependencyViolationError
- PairSuspendedError
- RiskBudgetExceededError
- InvalidProfileActivationError

## 3.6 Inputs

Aucun input runtime externe.  
Le module est une base déclarative.

## 3.7 Outputs

Des objets de contrat stables et versionnés.

## 3.8 État interne

Aucun état mutable live.  
Le module doit rester quasi statique.

## 3.9 Invariants obligatoires

Chaque contrat exposé doit définir :
- champs obligatoires
- champs optionnels
- unités attendues
- bornes de validité
- sémantique explicite
- version minimale

## 3.10 Exigences de design

- pas de dictionnaires anonymes comme API publique
- pas de surcharge polymorphe opaque
- pas de types ambigus selon le moteur
- nomenclature unifiée
- documentation inline des champs

## 3.11 Dépendances autorisées

- bibliothèque standard
- outils de typing / validation légers si retenus officiellement

## 3.12 Dépendances interdites

- tout module concret de production
- tout import runtime vers signal/risk/execution/data
- toute dépendance lourde inutile

## 3.13 Logs attendus

Ce module ne log pas en production.  
Il peut fournir des métadonnées de version de contrat.

## 3.14 Tests obligatoires

- validation présence des champs
- validation types
- validation bornes métier
- validation rétrocompatibilité simple
- validation erreurs attendues

## 3.15 Dérives possibles à ne pas faire

- utiliser de simples `dict`
- multiplier les variantes d’un même contrat
- changer un champ sans versionner
- définir des contrats trop généraux pour “aller plus vite”
- mélanger types de marché et types d’exécution

## 3.16 Priorité
P0 absolue

## 3.17 Verdict
**Implémenter maintenant**

---

# 4. MODULE 2 — MANIFEST_REGISTRY

## 4.1 Nom canonique
`manifest_registry`

## 4.2 Mission

Être le registre unique des modules et de leur place officielle dans l’architecture.

## 4.3 Responsabilités exactes

- lister tous les modules autorisés
- lister leur couche
- lister leur ownership
- lister leurs dépendances autorisées
- lister leur profil d’activation (Light / Complete / commun)
- définir l’ordre officiel de build
- définir le statut de chaque module :
  - active
  - planned
  - archived
  - forbidden

## 4.4 Ce que ce module ne doit pas faire

- faire de la logique métier
- devenir un second master textuel flou
- autoriser des exceptions ad hoc non journalisées
- se désynchroniser du build réel

## 4.5 Sous-composants

### 4.5.1 module_inventory
Rôle :
- table canonique de tous les modules

Champs minimums :
- module_name
- module_layer
- owner
- status
- priority
- profile_scope
- build_stage

### 4.5.2 dependency_registry
Rôle :
- liste blanche des dépendances autorisées par module

### 4.5.3 profile_registry
Rôle :
- cartographier Light / Complete / commun

### 4.5.4 build_order_registry
Rôle :
- exprimer l’ordre officiel d’implémentation

### 4.5.5 version_registry
Rôle :
- versionner les changements manifest

## 4.6 Inputs

- définition canonique des modules
- conventions architecturales gelées

## 4.7 Outputs

- manifest exploitable par :
  - dag_validator
  - build pipeline
  - audit tools
  - UI admin read-only

## 4.8 État interne

Version manifest actuelle + historique minimal.

## 4.9 Invariants obligatoires

- chaque module a un owner
- chaque module a une couche
- chaque module a une priorité
- chaque module a un statut
- aucune dépendance non déclarée
- aucun module “fantôme”

## 4.10 Exigences de design

- manifeste lisible humainement
- manifeste lisible machine
- pas de champs décoratifs
- pas de doublon de module
- champ de statut obligatoire

## 4.11 Dépendances autorisées

- interface_contracts
- bibliothèque standard
- parseur structuré léger

## 4.12 Dépendances interdites

- imports vers les modules concrets business
- logique de validation complexe enfouie ailleurs

## 4.13 Logs attendus

- version active du manifest
- changements de version
- ajout/suppression de module
- changement de statut
- changement de build_stage

## 4.14 Tests obligatoires

- module list unique
- couche obligatoire
- owner obligatoire
- dépendances bien formées
- profil valide
- build order cohérent
- diff de manifest détectable

## 4.15 Dérives possibles à ne pas faire

- manifest décoratif jamais utilisé
- informations en double entre master et manifest
- module ajouté dans le code mais absent du manifest
- build order implicite
- champ “misc” fourre-tout

## 4.16 Priorité
P0 absolue

## 4.17 Verdict
**Implémenter maintenant**

---

# 5. MODULE 3 — DAG_VALIDATOR

## 5.1 Nom canonique
`dag_validator`

## 5.2 Mission

Empêcher les dépendances interdites et les cycles d’architecture.

## 5.3 Responsabilités exactes

- analyser les imports des modules
- comparer les imports réels aux dépendances autorisées du manifest
- détecter les cycles
- signaler les violations de couche
- produire un rapport exploitable par le pipeline CI

## 5.4 Ce que ce module ne doit pas faire

- remplacer les tests runtime
- ignorer les imports dynamiques
- servir uniquement “en théorie”
- tolérer des exceptions tacites

## 5.5 Sous-composants

### 5.5.1 import_scanner
Rôle :
- scanner les imports du repo

### 5.5.2 dependency_matcher
Rôle :
- comparer imports observés vs manifest autorisé

### 5.5.3 cycle_detector
Rôle :
- détecter les cycles dans le DAG

### 5.5.4 layer_validator
Rôle :
- vérifier que les couches respectent la hiérarchie

### 5.5.5 report_builder
Rôle :
- produire un rapport humain + machine exploitable

## 5.6 Inputs

- arborescence du code
- manifest_registry
- conventions de package

## 5.7 Outputs

- statut pass/fail
- liste de violations
- liste de cycles
- liste d’imports suspects
- rapport versionné

## 5.8 État interne

Aucun état critique runtime, seulement résultats de scan.

## 5.9 Invariants obligatoires

- aucun cycle autorisé
- aucun import non déclaré
- aucune dépendance interdite entre couches
- toute violation doit être explicite

## 5.10 Exigences de design

- scan reproductible
- rapport déterministe
- sorties exploitables par CI
- distinction claire entre erreur et warning
- impossible de passer silencieusement une violation critique

## 5.11 Dépendances autorisées

- manifest_registry
- interface_contracts
- outils AST / parsing standard

## 5.12 Dépendances interdites

- logique métier
- exécution de modules business
- heuristiques non documentées

## 5.13 Logs attendus

- timestamp du scan
- version manifest
- hash repo / commit
- violations critiques
- warnings
- résultat global

## 5.14 Tests obligatoires

- cycle simple
- cycle indirect
- import autorisé
- import interdit
- import manquant du manifest
- build fail sur violation critique

## 5.15 Dérives possibles à ne pas faire

- ignorer `TYPE_CHECKING`
- ignorer imports relatifs
- scanner seulement une partie du repo
- tolérer un cycle “temporaire”
- produire un rapport illisible

## 5.16 Priorité
P0 absolue

## 5.17 Verdict
**Implémenter maintenant**

---

# 6. MODULE 4 — CONTRACT_TEST_SUITE

## 6.1 Nom canonique
`contract_test_suite`

## 6.2 Mission

Garantir que chaque module respecte réellement ses contrats, pas seulement sur le papier.

## 6.3 Responsabilités exactes

- exécuter les tests de contrat par module
- vérifier inputs / outputs / invariants
- standardiser la structure de tests
- rendre les tests de contrat obligatoires dans le pipeline

## 6.4 Ce que ce module ne doit pas faire

- se limiter aux happy paths
- devenir un pseudo test unitaire générique sans logique contractuelle
- ignorer les erreurs attendues
- dépendre de l’exécution du système complet

## 6.5 Sous-composants

### 6.5.1 contract_test_runner
Rôle :
- exécuter les suites de contrat

### 6.5.2 schema_assertions
Rôle :
- vérifier présence / absence de champs
- type
- bornes
- unités
- statuts

### 6.5.3 negative_case_runner
Rôle :
- tester les cas invalides attendus

### 6.5.4 compatibility_checker
Rôle :
- vérifier qu’un changement ne casse pas un consommateur existant

### 6.5.5 contract_reporter
Rôle :
- produire un rapport explicite des contrats passés / cassés

## 6.6 Inputs

- interface_contracts
- modules concrets
- fixtures de test
- cas de test négatifs

## 6.7 Outputs

- statut pass/fail
- rapport par module
- détails de contrat cassé
- historique minimal

## 6.8 État interne

Aucun état productif, seulement artefacts de tests.

## 6.9 Invariants obligatoires

- tout module P0 doit avoir des contract tests
- un contrat cassé doit faire échouer le build
- les cas négatifs critiques doivent être présents

## 6.10 Exigences de design

- testabilité isolée
- nomenclature uniforme
- tests lisibles
- peu de magie
- pas de dépendance forte à l’environnement runtime complet

## 6.11 Dépendances autorisées

- interface_contracts
- manifest_registry
- framework de test standard léger

## 6.12 Dépendances interdites

- services externes non mockés
- appels réseau
- logique d’infra non contrôlée

## 6.13 Logs attendus

- module testé
- contrat testé
- statut
- temps d’exécution
- raison de failure

## 6.14 Tests obligatoires pour le module lui-même

- exécution d’un contrat simple valide
- échec sur type invalide
- échec sur champ manquant
- échec sur borne invalide
- rapport généré

## 6.15 Dérives possibles à ne pas faire

- écrire des contract tests après le code
- tester uniquement les cas heureux
- ne pas tester les erreurs attendues
- cacher l’échec derrière des warnings
- considérer que typing statique suffit

## 6.16 Priorité
P0 absolue

## 6.17 Verdict
**Implémenter maintenant**

---

# 7. MODULE 5 — SMOKE_BOOTSTRAP_RECOVERY

## 7.1 Nom canonique
`smoke_bootstrap_recovery`

## 7.2 Mission

Vérifier qu’un module ou un build peut :

- démarrer proprement
- initialiser ses ressources
- charger sa configuration valide
- échouer explicitement si les préconditions ne sont pas là
- redémarrer sans corrompre l’état

## 7.3 Responsabilités exactes

- tester bootstrap minimal de chaque module stateful
- tester restart simple
- tester recovery après interruption contrôlée
- signaler immédiatement les modules qui ne supportent pas un cycle de vie réaliste

## 7.4 Ce que ce module ne doit pas faire

- simuler toute la production
- masquer les erreurs d’initialisation
- “réparer” silencieusement un état incohérent
- devenir un test d’intégration flou

## 7.5 Sous-composants

### 7.5.1 bootstrap_runner
Rôle :
- lancer les séquences minimales de démarrage

### 7.5.2 config_validator
Rôle :
- vérifier que les config nécessaires sont présentes et cohérentes

### 7.5.3 recovery_runner
Rôle :
- provoquer un arrêt / relancer / vérifier état propre

### 7.5.4 state_sanity_checker
Rôle :
- vérifier que l’état redémarré est cohérent

### 7.5.5 smoke_reporter
Rôle :
- rapport bootstrap / recovery

## 7.6 Inputs

- config du module
- fixtures runtime minimales
- état initial synthétique si nécessaire

## 7.7 Outputs

- statut pass/fail
- temps de bootstrap
- temps de recovery
- rapport d’état
- anomalies détectées

## 7.8 État interne

Seulement les artefacts de test ; aucun état live permanent.

## 7.9 Invariants obligatoires

- un module stateful doit avoir un smoke bootstrap
- un module critique doit avoir un smoke recovery
- toute erreur de démarrage doit être explicite
- aucun état partiellement initialisé ne doit être considéré comme “OK”

## 7.10 Exigences de design

- tests simples, rapides, déterministes
- exécution CI possible
- rapports lisibles
- réplicabilité

## 7.11 Dépendances autorisées

- manifest_registry
- interface_contracts
- contract_test_suite
- outillage test minimal

## 7.12 Dépendances interdites

- logique métier lourde
- services externes non simulés
- récupération implicite non vérifiée

## 7.13 Logs attendus

- module ciblé
- bootstrap start/end
- recovery start/end
- config verdict
- état final
- anomalies

## 7.14 Tests obligatoires

- bootstrap OK module minimal
- bootstrap FAIL si config manquante
- recovery après arrêt contrôlé
- recovery après état partiel
- rapport lisible

## 7.15 Dérives possibles à ne pas faire

- considérer qu’un import réussi = bootstrap réussi
- ne pas tester le restart
- ignorer l’état partiel
- traiter les pannes d’initialisation comme warnings

## 7.16 Priorité
P0 absolue

## 7.17 Verdict
**Implémenter maintenant**

---

# 8. Interfaces entre modules Build-1

## 8.1 interface_contracts → manifest_registry
- fournit les types et objets de contrat utilisés dans le manifest si nécessaire

## 8.2 manifest_registry → dag_validator
- fournit la liste canonique des dépendances autorisées

## 8.3 interface_contracts → contract_test_suite
- fournit la définition des contrats à tester

## 8.4 manifest_registry → smoke_bootstrap_recovery
- fournit les modules ciblés, leur statut et leurs préconditions de bootstrap

## 8.5 contract_test_suite + smoke_bootstrap_recovery → pipeline CI
- fournissent les verdicts de merge Build-1

---

# 9. Ordre précis d’implémentation Build-1

## Étape 1
`interface_contracts`

Pourquoi :
- rien d’autre ne peut être propre sans types et contrats stables

## Étape 2
`manifest_registry`

Pourquoi :
- le projet doit connaître officiellement ses modules et dépendances

## Étape 3
`dag_validator`

Pourquoi :
- les violations d’architecture doivent être bloquées avant que le code prolifère

## Étape 4
`contract_test_suite`

Pourquoi :
- les modules futurs devront immédiatement passer leurs tests de contrat

## Étape 5
`smoke_bootstrap_recovery`

Pourquoi :
- un module sans démarrage / redémarrage propres n’est pas mergeable

---

# 10. Table synthétique Build-1

| Module | Ordre | Priorité | Gate critique | Sortie attendue |
|---|---:|---:|---|---|
| interface_contracts | 1 | P0 | contrats clairs | langage commun stable |
| manifest_registry | 2 | P0 | inventaire valide | vérité des modules |
| dag_validator | 3 | P0 | pas de cycles | architecture protégée |
| contract_test_suite | 4 | P0 | contrats testables | merges contrôlés |
| smoke_bootstrap_recovery | 5 | P0 | restart propre | modules stateful sûrs |

---

# 11. Conditions de sortie de Build-1

Build-1 est terminé si :

- les 5 modules existent
- leurs interfaces sont gelées
- leurs tests passent
- le pipeline CI peut les exécuter
- aucun module critique futur ne peut être mergé sans eux
- le repo est prêt à accueillir Build-2 sans dette structurelle

---

# 12. Critères de refus de sortie

Refuser Build-1 si :

- `interface_contracts` reste flou
- `manifest_registry` ne couvre pas tous les modules prévus
- `dag_validator` ne détecte pas vraiment les violations
- `contract_test_suite` n’échoue pas sur contrat cassé
- `smoke_bootstrap_recovery` ne teste pas réellement le restart

---

# 13. Dérives globales Build-1 à ne pas faire

- vouloir “aller plus vite” en commençant data_engine avant Build-1 terminé
- écrire le manifest après le code
- considérer les interfaces comme documentation facultative
- faire des smoke tests manuels non reproductibles
- laisser les IA inventer leurs propres contrats implicites

---

# 14. Verdict final Build-1

Build-1 est la condition de possibilité d’une V5.3 prod-safe.

Il ne rapporte pas d’argent directement.  
Mais sans lui :
- le code dérive
- les modules deviennent incompatibles
- les audits deviennent impossibles
- les bugs d’état se multiplient
- la prod devient fragile

Donc :

> Build-1 doit être traité comme un **build bloquant**, pas comme une formalité.

---

## Fin du document
