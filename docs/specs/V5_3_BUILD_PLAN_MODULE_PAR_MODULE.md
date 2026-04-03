# V5.3 BUILD PLAN — MODULE PAR MODULE
## Plan exécutable dérivé du master officiel unique
### Version développeur / chef de projet / orchestration IA
### Sans code

---

# 0. Objet

Ce document convertit le master final unique en **séquence de travail exécutable**.

Il répond à trois questions :
1. quoi construire
2. dans quel ordre
3. avec quels critères de sortie

Le plan suit une règle simple :

> aucune sophistication métier avant d’avoir verrouillé l’infrastructure, les tests, les coûts et la gouvernance de risque.

## 0.1 Statut documentaire vs réalité d’implémentation

Ce plan décrit la cible complète V5.3.

Pour l’état documentaire actuel :

- le **core Build-1 à Build-9** constitue la base réellement exécutable / gelable
- **Build-10** dispose maintenant d’une première implémentation codée exploitable côté monitoring/backend UI
- **Build-9X** dispose maintenant d’une première implémentation codée gouvernée
- `LOCAL_REPLAY` et l’import d’artifact disposent de scaffolds minimaux codés, sans runtime complet opéré
- **Build-11 à Build-17** restent des étapes canoniques de validation et
  d'extension du rollout, et ne doivent pas être lues comme déjà validées

## 0.2 Invariant local / VPS

Le plan s’appuie sur une seule V5.3 commune local + VPS :

- deux profils métier uniquement : `LIGHT`, `COMPLETE`
- quatre `runtime_mode` uniquement : `LOCAL_REPLAY`, `SHADOW`, `MICRO_LIVE`, `LIVE`
- aucun `BACKTEST_PROFILE`
- `Shadow intégral` désigne le Shadow du profil `LIGHT` avec A/B/C/D et
  Build-14 activés à 100% en observation ; ce n'est pas le profil `COMPLETE`
- aucun fork local / VPS
- pipeline officiel : `classification -> versioning -> shared core -> LOCAL_REPLAY -> export artifact -> import VPS -> candidature contrôlée`

Matrice canonique des états :

- `profil=LIGHT`, `runtime_mode=SHADOW` : Build-11 / `Shadow intégral`
- `profil=LIGHT`, `runtime_mode=MICRO_LIVE` : Build-12
- `profil=LIGHT`, `runtime_mode=LIVE` : Build-13 / `Live-Light`
- `profil=COMPLETE`, `runtime_mode=SHADOW` : Shadow Complete
- `profil=COMPLETE`, `runtime_mode=LIVE` : Live-Complete

---

# 1. Principes de build

## 1.1 Règles non négociables
- un seul module critique mergeable à la fois
- aucun code sans tests
- aucun merge sans audit croisé
- aucun passage de phase sans critères go/no-go
- aucune extension de rollout COMPLETE tant que le rollout LIGHT n’est pas
  validé et que les gates d'extension ne sont pas passés

## 1.2 Pipeline IA officiel
1. ChatGPT : spec du module  
2. Claude : code du module  
3. ChatGPT : audit quant / risk / logique  
4. Claude : correction  
5. tests  
6. merge si gates passés  

---

# 2. Vue d’ensemble des builds

| Build | Nom | Profil ciblé | Priorité | But |
|---|---|---|---:|---|
| 0 | Foundations Freeze | commun | P0 | geler la vérité documentaire |
| 1 | Dependency Architecture | commun | P0 | empêcher la dette technique |
| 2 | Data Backbone | commun | P0 | ingestion et qualité data |
| 3 | Execution Backbone | commun | P0 | exécution et coûts |
| 4 | Risk Backbone | commun | P0 | budgets risque |
| 5 | Scoring Backbone | commun | P0 | hard/soft/rank |
| 6 | Moteur A | LIGHT rollout | P0 | cœur premium du rollout initial |
| 7 | Moteur B | LIGHT rollout | P0 | fréquence utile du rollout initial |
| 8 | Portfolio Minimal | LIGHT rollout | P0 | arbitrage gouverné sur 6 paires |
| 9 | Meta Minimal | LIGHT rollout | P0 | DTR, CRA, break-even |
| 9X | Meta Learning Governed Layer | documentaire | P1/P2 | diagnostics, hypothèses, replay bundles, sans effet live direct |
| 10 | Monitoring + UI Light | LIGHT rollout | P0/P1 | supervision verrouillée du système complet |
| 11 | Shadow Light (`Shadow intégral`) | LIGHT rollout | P0 | validation sans capital |
| 12 | Micro-live Light | LIGHT rollout | P0 | coûts réels |
| 13 | Live-Light | LIGHT rollout | P0 | premier rollout réel borné |
| 14 | Complete Enablers | architecture complète | P1/P2 | enablers prod-safe et angles morts |
| 15 | Moteur C | architecture complète | P1 | breakout continuation gouverné |
| 16 | Moteur D | architecture complète | P1 | re-entry gouverné |
| 17 | UI Complete + Live-Complete | COMPLETE rollout | P1 | extension gouvernée du rollout |

---

# 3. Build-0 — Foundations Freeze

## Objectif
Geler :
- master final unique
- nomenclature modules
- nomenclature moteurs
- profils Light/Complete
- conventions logs
- conventions tests
- merge gates
- états UI

## Livrables
- master final unique
- build plan
- conventions tests
- conventions logs
- manifest initial

## Refus si
- plusieurs docs actifs restent en concurrence
- noms de modules encore mouvants
- profil Light/Complete non verrouillé

---

## Phase Audit Integration Pass (post Build-0, pre-qualification)

### Objectif
Intégrer les enseignements des audits tiers dans le corpus documentaire sans modifier le code.

### Étapes
1. **Freeze documentaire** — gel du corpus canonique avant modifications
2. **Triage des findings** — classification NOW_P0 / NOW_LIGHT / NEXT_BUILD14 / RESEARCH_LOCAL / REJECT
3. **Patch des specs** — injection des invariants P0 dans les builds concernés
4. **Réalignement docs → code** — plan de vérification que le code respecte les docs patchées
5. **Interdiction de promotion implicite** — aucun build ne change de statut par le seul fait du patch
6. **Requalification des builds 1→14** — chaque build déjà codé est requalifié selon le nouveau corpus

### Livrables
- `V5_3_AUDIT_INTEGRATION_DECISIONS.md` (rapport de triage)
- `V5_3_DOC_TO_CODE_ALIGNMENT_PLAN.md` (plan de réalignement)
- Patches dans chaque spec de build concernée
- Changelog documentaire

### Règles
- ne pas modifier le code dans cette phase
- ne pas activer Complete implicitement
- ne pas promouvoir Build-14
- ne pas créer d'architecture concurrente
- un audit tiers n'est jamais une source de vérité active

### Go/No-Go
- rapport de triage complet
- tous les fichiers MD patchés
- aucune contradiction introduite
- plan d'alignement code prêt

---

# 4. Build-1 — Dependency Architecture

## Modules
- interface_contracts
- manifest_registry
- dag_validator
- contract_test_suite
- smoke_bootstrap_recovery

## Objectif
Empêcher que le projet ne se déforme avant d’avoir commencé.

## Tests obligatoires
- validation imports
- validation build order
- bootstrap clean
- recovery smoke
- interfaces cohérentes

## Go si
- aucun cycle
- manifest cohérent
- contract tests exécutables
- smoke tests verts

## No-go si
- dépendances cachées
- dicts libres partout
- manifest non maintenable

---

# 5. Build-2 — Data Backbone

## Modules
- websocket_gateway
- rest_bootstrap
- event_normalizer
- internal_router
- freshness_checker
- consistency_checker
- pair_health_scorer

## Objectif
Créer une couche data stable, testable, suspendable par paire.

## Tests obligatoires
- reconnexion WS
- heartbeat loss
- disorder
- duplication
- stale detection
- suspension / reprise paire
- backlog visible

## Go si
- une paire peut tomber sans casser les autres
- backlog et stale metrics visibles
- pair health fiable

## No-go si
- état global contaminé par une paire
- ordre des événements non fiable
- REST utilisé comme temps réel

---

# 6. Build-3 — Execution Backbone

## Modules
- order_decider
- fill_tracker
- execution_cost_meter
- reconciliation_layer

## Objectif
Mesurer et maîtriser l’économie réelle de l’exécution.

## Tests obligatoires
- ACK
- partial fill
- timeout
- cancel / replace
- reconciliation
- coût loggé

## Go si
- coût attendu vs coût réalisé visible
- divergence état local / réel gérée
- fill latency mesurée

## No-go si
- coûts réduits aux seuls fees
- reconciliation instable

---

# 7. Build-4 — Risk Backbone

## Modules
- exposure_budgeter
- loss_budgeter
- btc_factor_guard
- correlation_cluster_guard

## Objectif
Empêcher les erreurs de concentration et la fausse diversification.

## Tests obligatoires
- caps exposition
- caps perte
- caps cluster
- beta BTC
- refus sur-exposition

## Go si
- impossible de dépasser les caps
- budgets visibles dans UI / logs
- beta BTC exploitable

## No-go si
- notionnel sans budget perte
- cluster risk absent
- facteur BTC ignoré

---

# 8. Build-5 — Scoring Backbone

## Modules
- raw_score_builder
- penalty_aggregator
- hard_block_gate
- ranking_router

## Objectif
Rendre hard / soft / rank réellement opérationnel.

## Tests obligatoires
- hard blocks
- soft penalties
- ranking stable
- décision reproductible
- compatibilité portefeuille

## Go si
- soft ≠ hard
- ranking tient compte coût et risque
- chaque décision explicable

## No-go si
- sur-filtrage recréé
- décisions non reproductibles

---

# 9. Build-6 — Moteur A

## Objectif
Rendre le moteur premium opérationnel sans rebasculer vers la stérilité.

## Paires autorisées
- BTC
- ETH
- BNB
- SOL
- XRP
- LINK

## Tests obligatoires
- déclenchement correct
- non déclenchement hors contexte
- coût prudent respecté
- logs A complets

## Go si
- fréquence utile non nulle
- coût supportable
- CE plausible

## No-go si
- trop rare
- trop cher
- trop de veto non fatals

---

# 10. Build-7 — Moteur B

## Objectif
Ajouter fréquence utile et rotation du capital.

## Paires autorisées
- BTC
- ETH
- SOL
- XRP
- ADA
- LINK

## Tests obligatoires
- calcul z-score
- signal reversion cohérent
- sortie cohérente
- coût supportable
- pas de trade en cassure évidente

## Go si
- CE correcte
- durée courte utile
- coût sous contrôle

## No-go si
- moteur “volume pour volume”
- trop de pertes contre cassure

---

# 11. Build-8 — Portfolio Minimal

## Modules
- opportunity_selector
- allocation_router

## Objectif
Arbitrer les opportunités du rollout initial sur 6 paires sans casser
l'extensibilité de l'architecture complète.

## Tests obligatoires
- arbitrage simultané
- respect caps risque
- respect budget BTC / clusters
- sélection par score + coût + CE

## Go si
- pas d’allocation naïve
- pas de sur-exposition corrélée
- logique portefeuille lisible

## No-go si
- score brut seul
- pas de conscience corrélation

---

# 12. Build-9 — Meta Minimal

## Modules
- dtr_core
- cra_monitor
- break_even_dashboard
- edge_tracker_prudent minimal

## Objectif
Ne jamais piloter à l’aveugle.

## Tests obligatoires
- DTR complets
- pas de perte silencieuse
- phantom trades visibles
- coût réel et break-even visibles

## Go si
- diagnostic possible
- stérilisation mesurable
- DTR reproductibles

## No-go si
- DTR incomplets
- break-even absent
- phantom trades invisibles

---

## Extension documentaire post-Build-9 — Build-9X

## Mission
Ajouter une couche méta gouvernée qui produit :

- `diagnostics`
- `breakdown reports`
- `checklists`
- `hypothesis registry`
- `improvement candidates`
- `replay bundles`

## Dépendances
- dépendance logique : Build-9
- dépendance opératoire forte : Build-10
- consommateur futur de `LOCAL_REPLAY`
- export / import d’artifact versionné et en lecture seule

## Interdictions
- aucun impact live direct
- aucune auto-modification live
- aucun nouveau profil métier
- aucun fork local / VPS
- aucune promotion implicite depuis un bon replay local

## Gates minimales avant implémentation réelle
- Build-9 stable et traçabilité meta propre
- Build-10 opérable et UI de supervision disponible
- règles `LOCAL_REPLAY` / export artifact / import VPS documentées
- IDs de corrélation, logs structurés, contrats internes et budgets définis

## Statut
- **référence documentaire active** : `V5_3_BUILD9X_SPEC_META_LEARNING_GOVERNED_LAYER_V2_FREEZE_READY.md`
- **première implémentation codée, non finale**

---

# 13. Build-10 — Monitoring + UI Light

## Modules
- metrics_collector
- alert_manager
- dashboards backend
- UI Light verrouillée

## Objectif
Rendre le système gouvernable sans le rendre permissif.

## Tests obligatoires
- profils et états de rollout visibles
- état système
- overview portefeuille
- paires / moteurs / risque / coûts / infra
- impossibilité d'activer un moteur, une paire ou un budget au-dela des gates
  et de la borne de rollout

## Go si
- UI actionnable
- aucune action interdite possible
- métriques critiques visibles

## No-go si
- UI décorative
- override critique possible

---

# 14. Build-11 — Shadow Light

## Objectif
Valider la logique sans capital réel.

## État canonique
- `profil=LIGHT`
- `runtime_mode=SHADOW`
- nom de phase lisible : `Shadow intégral`

## HARD STATEMENT — Shadow intégral = phase de vérité système (30 jours)
- La version Light doit trader en mode SHADOW pendant **30 jours calendaires consécutifs minimum**
- Données réelles obligatoires (WebSocket ou replay réaliste)
- Pipeline complet : data → engine → scoring → portfolio → execution simulée
- **Build-14 et tous les enrichissements du rollout Light activés à 100% pendant le Shadow intégral**
- Moteurs A/B/C/D actifs, scorés, classés, arbitrés et observés
- Build-14 enablers pleinement utilisés dans les décisions Shadow
- DTR complet produit pendant les 30 jours
- Interruption > 24h = compteur reprend à zéro
- Rapport shadow exploitable obligatoire (CE, coûts estimés, edge, drawdown, stale rate, **comparaison inter-moteurs A/B/C/D, contribution Build-14**)
- **Aucune activation Micro-live ni Live-Light avant l'expiration de cette période**
- **Activation intégrale en Shadow ≠ promotion Live** : chaque composant sera jugé individuellement au verdict post-Shadow

## KPI obligatoires
- fréquence brute et utile par moteur (A/B/C/D)
- coût simulé prudent par moteur
- DTR complets
- pass-rate économique
- pair health
- backlog stable
- comparaison inter-moteurs (non-duplication, edge marginal)
- contribution Build-14 (microstructure, régime, covariance, risk contribution, edge diversity)
- interactions et conflits A/B

## Go si
- **HARD : 30 jours de shadow consécutifs atteints**
- décisions reproductibles
- infra stable
- coût simulé crédible
- rapport shadow produit et approuvé
- verdict composant par composant rendu (chaque moteur/enabler : `SHADOW_VALIDATED` ou `DORMANT`)

## No-go si
- 30 jours non atteints
- signaux non explicables
- DTR incomplets
- saturation latente
- verdict post-Shadow non rendu

---

# 15. Build-12 — Micro-live Light

## Objectif
Valider coûts réels, fills, stale rate, reconciliation.

## État canonique
- `profil=LIGHT`
- `runtime_mode=MICRO_LIVE`
- nom de phase lisible : `Micro-live Light`

## Prérequis
- **Verdict post-Shadow rendu** : seuls les composants `SHADOW_VALIDATED` passent en Micro-live
- L'activation intégrale en Shadow ne signifie pas activation Micro-live automatique de tous les composants
- Les moteurs/enablers marqués `DORMANT` au verdict restent inactifs en Micro-live

## Contraintes
- petit notional
- zéro Tier 3
- budget perte très faible

## KPI obligatoires
- coût réel vs attendu
- fill latency
- partial fill rate
- CE live
- stale rate
- divergence shadow/live

## Go si
- coûts acceptables
- reconciliation stable
- CE mesurable

## No-go si
- coûts détruisent l’edge
- stale decisions
- divergence d’état

---

# 16. Build-13 — Live-Light

## Objectif
Première production réelle disciplinée.

## État canonique
- `profil=LIGHT`
- `runtime_mode=LIVE`
- nom de phase lisible : `Live-Light`

## Prérequis HARD
- **HARD : 30 jours de Shadow intégral consécutifs atteints et rapport approuvé**
- **HARD : Verdict post-Shadow rendu composant par composant**
- **HARD : Micro-live stable (minimum 7 jours)**

## Conditions go
- 30 jours de Shadow intégral validés
- fréquence utile > V5.2
- edge net > 0 ou crédible
- CE > V5.2
- composants promus stables
- verdict Build-14 disponible ; C/D peuvent être observés en Shadow mais restent hors rollout live tant qu’ils n’ont pas reçu `SHADOW_VALIDATED` et passé leurs gates de mise en service
- budgets risque respectés
- beta BTC maîtrisé
- logs + DTR fiables
- notification opérateur fonctionnelle
- kill switch externe testé

## Conditions no-go
- 30 jours shadow non atteints
- coût trop élevé
- moteur B dégrade la CE
- moteur A trop rare
- cluster risk non maîtrisé
- infra instable

---

# 17. Build-14 — Complete Enablers

## Modules potentiels
- microstructure enrichie
- regime enrichi
- covariance plus robuste
- risk contribution monitor
- K_eff enrichi

## Objectif
Renforcer la solution complete deja assumee sans casser le rollout LIGHT et
sans ouvrir d'activation reelle non gouvernee.

## Gouvernance obligatoire
- **activé à 100% en Shadow** : pleinement utilisé dans les décisions, tracé, comparé, auditable
- promotion live non automatique : soumis au verdict post-Shadow
- jamais moteur autonome
- jamais bypass des moteurs A/B dans le rollout Light, du risk backbone, du portfolio ni des protocoles de promotion
- intégration des candidats classés `Build14_enabler` via le protocole d’onboarding officiel
- Hard State : `CODED` → `SHADOW_ENABLED` → verdict → `SHADOW_VALIDATED` ou `DORMANT`

## Go si
- aucune régression Light
- coût infra acceptable

## No-go si
- surcharge CPU/queues
- complexité non monétisable

---

# 18. Build-15 — Moteur C

## Objectif
Documenter et valider le moteur C comme moteur natif de la solution complete.
C est **activé à 100% en Shadow** dès le début des 30 jours, scoré et comparé à A/B.
Sa promotion live reste strictement gouvernée par le verdict post-Shadow.

## KPI
- alpha net C
- coût C
- CE C
- faux breakout rate
- corrélation A/C
- gain marginal portefeuille

## Go si
- non-duplication
- coût soutenable
- CE utile

## No-go si
- A rebaptisé C
- faux breakout trop fréquents

---

# 19. Build-16 — Moteur D

## Objectif
Documenter et valider le moteur D comme moteur natif de la solution complete.
D est **activé à 100% en Shadow** dès le début des 30 jours, scoré et comparé à A/B/C.
Sa promotion live reste strictement gouvernée par le verdict post-Shadow et la preuve de contribution marginale positive.

## KPI
- alpha marginal D
- coût marginal D
- CE marginale D
- concentration induite
- corrélation A/D

## Go si
- vraie valeur marginale
- concentration supportable

## No-go si
- revenge trading automatisé
- surconcentration
- pas d’alpha additionnel

---

# 20. Build-17 — UI Complete + Live-Complete

## Objectif
Formaliser l'extension gouvernee du rollout de la meme architecture complete :
6 -> 8/10 -> 12 paires, UI complete pleinement exploitable, et activation
runtime sous budgets, gates et rollback.

## Prérequis HARD
- **HARD : Complete a tradé en shadow 30 jours calendaires consécutifs minimum**
- **HARD : Non-régression Light démontrée pendant ces 30 jours**
- **HARD : Rapport comparatif Light vs Complete produit et approuvé par l’opérateur**
- **HARD : Light live stable au moment du passage**

## Conditions go
- 30 jours shadow Complete validés
- Live-Light stable
- A/B validés
- C/D validés
- K_eff augmente
- CE portefeuille augmente ou reste acceptable
- coût des 6 paires additionnelles sous contrôle
- infra stable
- rapport comparatif approuvé

## Conditions no-go
- 30 jours shadow Complete non atteints
- fréquence brute seule augmente
- CE baisse trop
- C/D n’ajoutent rien
- saturation infra ou DTR loss
- non-régression Light non démontrée

---

# 21. Checklists de sortie par phase

## 21.1 Sortie Build-0
- master gelé
- nomenclature gelée
- conventions tests/logs gelées

## 21.2 Sortie Build-1
- interfaces stables
- DAG propre
- manifest fonctionnel

## 21.3 Sortie Build-2
- data backbone stable
- quality stable
- pair health fonctionnel

## 21.4 Sortie Build-3
- coût réel loggé
- reconciliation stable

## 21.5 Sortie Build-4
- caps risque réels
- beta BTC visible

## 21.6 Sortie Build-5
- hard/soft/rank fonctionnels

## 21.7 Sortie Build-6/7
- moteurs A/B utilisables en shadow

## 21.8 Sortie Build-8/9/10
- portefeuille Light gouvernable
- UI Light verrouillée

## 21.8 bis Sortie documentaire Build-9X
- V2 gelée comme référence documentaire
- outputs attendus explicités
- anti-live-mutation explicitée
- anti-fork local/VPS explicité
- non-promouvable tant que non validé par les gates normales

## 21.9 Sortie Build-11/12/13
- rollout LIGHT valide sur 6 paires, sans confusion avec une architecture A/B-only

## 21.10 Sortie Build-14/15/16/17
- extension COMPLETE autorisable seulement si gain reel, angles morts traites
  et gouvernance runtime non contournable

---

# 22. Ce qu’il ne faut pas faire pendant le build

- ouvrir 4 chantiers critiques en parallèle
- merger du code non testé “temporairement”
- recoder l’architecture en plein milieu
- déduire la validité d’un moteur d’un seul backtest
- promouvoir Complete pour des raisons psychologiques ou esthétiques
- confondre build technique terminé et edge validé

---

# 23. Résultat attendu

À l’issue de ce plan :
- vous avez un chemin de build clair
- Claude Pro et ChatGPT Pro peuvent être orchestrés proprement
- le projet avance sans perdre sa cohérence
- la V5.3 LIGHT devient le premier rollout rentable, prudent et credible
- la V5.3 COMPLETE reste l'extension gouvernee de la meme architecture, pas
  un saut de foi ni une architecture concurrente

---

## Règle transversale — Distinction codé / validé / promu

Pour tous les builds :
- **codé** = le code existe dans le dépôt
- **validé** = tests passent, gates vertes, code audité
- **promu** = build activable en production dans le profil autorisé

Un build codé n'est PAS automatiquement validé ni promu.
Build-14 codé ≠ Build-14 promu.
Complete enablers codés ≠ activation Complete.

---

## Fin du plan de build
