# V5.3 BUILD PLAN — MODULE PAR MODULE
## Plan exécutable dérivé du master canonique
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

---

# 1. Principes de build

## 1.1 Règles non négociables
- un seul module critique mergeable à la fois
- aucun code sans tests
- aucun merge sans audit croisé
- aucun passage de phase sans critères go/no-go
- aucun développement Complete tant que Light n’est pas validé

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
| 6 | Moteur A | Light | P0 | cœur premium |
| 7 | Moteur B | Light | P0 | fréquence utile |
| 8 | Portfolio Minimal | Light | P0 | arbitrage A/B |
| 9 | Meta Minimal | Light | P0 | DTR, CRA, break-even |
| 10 | Monitoring + UI Light | Light | P0/P1 | supervision verrouillée |
| 11 | Shadow Light | Light | P0 | validation sans capital |
| 12 | Micro-live Light | Light | P0 | coûts réels |
| 13 | Live-Light | Light | P0 | première prod |
| 14 | Complete Enablers | Complete | P1/P2 | enrichissements non bloquants |
| 15 | Moteur C | Complete | P1 | breakout continuation |
| 16 | Moteur D | Complete | P1 | re-entry |
| 17 | UI Complete + Live-Complete | Complete | P1 | extension finale |

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
Arbitrer les opportunités A/B sur 6 paires.

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

# 13. Build-10 — Monitoring + UI Light

## Modules
- metrics_collector
- alert_manager
- dashboards backend
- UI Light verrouillée

## Objectif
Rendre le système gouvernable sans le rendre permissif.

## Tests obligatoires
- profils Light visibles
- état système
- overview portefeuille
- paires / moteurs / risque / coûts / infra
- impossibilité d’activer C/D ou 12 paires

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

## KPI obligatoires
- fréquence brute
- fréquence utile
- coût simulé prudent
- DTR complets
- pass-rate économique
- pair health
- backlog stable

## Go si
- décisions reproductibles
- infra stable
- coût simulé crédible

## No-go si
- signaux non explicables
- DTR incomplets
- saturation latente

---

# 15. Build-12 — Micro-live Light

## Objectif
Valider coûts réels, fills, stale rate, reconciliation.

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

## Conditions go
- fréquence utile > V5.2
- edge net > 0 ou crédible
- CE > V5.2
- A/B stables
- budgets risque respectés
- beta BTC maîtrisé
- logs + DTR fiables

## Conditions no-go
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
Préparer Complete sans casser Light.

## Go si
- aucune régression Light
- coût infra acceptable

## No-go si
- surcharge CPU/queues
- complexité non monétisable

---

# 18. Build-15 — Moteur C

## Objectif
Ajouter breakout continuation seulement s’il apporte quelque chose que A n’apporte pas déjà.

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
Ajouter re-entry seulement si contribution marginale positive.

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
Ouvrir 12 paires / 4 moteurs seulement si la complexité supplémentaire paie réellement.

## Conditions go
- Live-Light stable
- A/B validés
- C/D validés
- K_eff augmente
- CE portefeuille augmente ou reste acceptable
- coût des 6 paires additionnelles sous contrôle
- infra stable

## Conditions no-go
- fréquence brute seule augmente
- CE baisse trop
- C/D n’ajoutent rien
- saturation infra ou DTR loss

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

## 21.9 Sortie Build-11/12/13
- Light validé

## 21.10 Sortie Build-14/15/16/17
- Complete seulement si gain réel

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
- la V5.3 Light devient l’étape rentable crédible
- la V5.3 Complete reste une extension conditionnelle, pas un saut de foi

---

## Fin du plan de build
