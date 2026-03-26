# V5.3 — BUILD-10 SPECS MODULES
## Monitoring + UI Light Pack
### Specs détaillées module par module
### Dixième étape officielle du développement
### Sans code — prod-safe

---

# 0. Objet du document

Ce document couvre **Build-10** du plan officiel V5.3.

Build-10 a une mission unique :

> rendre la V5.3 Light **observable, gouvernable et non contournable** par une couche de monitoring et d’interface opérateur verrouillée.

Les modules couverts ici sont :

1. `metrics_collector`
2. `alert_manager`
3. `health_dashboard_backend`
4. `ui_light_locked`

Build-10 ne cherche pas encore à produire l’interface complète de la V5.3 Complete.  
Il doit produire une **UI Light verrouillée**, orientée risque, coût, santé infra, état portefeuille et explicabilité minimale.

---

# 1. Principes Build-10

## 1.1 Objectif stratégique

À ce stade, la V5.3 Light sait déjà :
- ingérer la donnée
- vérifier sa qualité
- exécuter
- mesurer les coûts
- contrôler le risque
- scorer
- faire tourner A et B
- arbitrer un portefeuille minimal
- suivre DTR / CRA / break-even / edge prudent

Mais elle n’est pas encore exploitable proprement si :

- les métriques critiques ne sont pas rassemblées
- les alertes sont absentes ou trop bruyantes
- l’opérateur ne voit pas l’état réel du système
- l’UI permet des contournements de profil ou de guards
- les dashboards cachent les coûts, la CE ou les saturations

Build-10 existe pour résoudre cela.

## 1.2 Position dans l’architecture

Build-10 est :
- **obligatoire en Light**
- **obligatoire en Complete**
- **P0/P1**
- la couche de supervision active de la Light
- la couche qui transforme le système en outil opérable

## 1.3 Critère de réussite

Build-10 est réussi si :

- les métriques critiques sont centralisées
- les alertes utiles sont visibles
- les dashboards exposent capital, risque, coût, CE, santé, backlog, DTR
- l’UI Light ne permet aucun contournement structurel
- l’opérateur peut comprendre l’état du système en quelques secondes
- toute action sensible est journalisée

## 1.4 Critère d’échec

Build-10 échoue si :

- les métriques sont dispersées
- l’alerting n’aide pas l’action
- l’UI est décorative
- l’UI permet d’activer des éléments hors profil
- les coûts et la CE ne sont pas visibles
- les saturations queues / stale / DTR loss ne sont pas remontées

---

# 2. Vocabulaire officiel Build-10

## 2.1 Métrique critique
Valeur nécessaire pour piloter la production sans aveuglement :
- capital
- exposition
- coût
- CE
- stale
- backlog
- pair health
- DTR loss
- edge status

## 2.2 Alerte actionnable
Alerte associée à une décision ou réaction concrète :
- suspendre une paire
- passer en degraded
- analyser un coût
- investiguer une divergence

## 2.3 Dashboard santé
Vue consolidée de l’état du portefeuille, des moteurs, des paires et de l’infrastructure.

## 2.4 UI Light verrouillée
Interface opérateur qui expose la supervision et les actions autorisées du profil Light, sans permettre :
- profil custom
- activation C/D
- activation 12 paires
- override des hard guards

---

# 3. Architecture Build-10

## 3.1 Chaîne de traitement

1. `metrics_collector`
2. `alert_manager`
3. `health_dashboard_backend`
4. `ui_light_locked`

## 3.2 Principe de hiérarchie

- `metrics_collector` agrège les vérités utiles
- `alert_manager` transforme certaines métriques en signaux actionnables
- `health_dashboard_backend` structure l’information pour l’UI
- `ui_light_locked` expose cette information sans ouvrir de portes dangereuses

---

# 4. MODULE 1 — METRICS_COLLECTOR

## 4.1 Nom canonique
`metrics_collector`

## 4.2 Mission

Centraliser les métriques critiques issues des couches précédentes pour rendre le système pilotable.

## 4.3 Responsabilités exactes

- collecter les métriques de portefeuille
- collecter les métriques de moteurs
- collecter les métriques de paires
- collecter les métriques d’exécution
- collecter les métriques infra
- collecter les métriques meta
- standardiser leur publication
- horodater les snapshots

## 4.4 Ce que ce module ne doit pas faire

- recalculer la logique métier source
- lisser excessivement les métriques
- masquer les données anormales
- remplacer les modules producteurs
- émettre des alertes lui-même

## 4.5 Sous-composants

### 4.5.1 portfolio_metrics_adapter
Rôle :
- récupérer capital, exposition, PnL, CE, beta BTC, budgets

### 4.5.2 engine_metrics_adapter
Rôle :
- récupérer fréquence utile, rendement net, coût, CE, Sharpe, drawdown par moteur

### 4.5.3 pair_metrics_adapter
Rôle :
- récupérer santé paire, stale, coût, fréquence, CE, état actif/suspendu

### 4.5.4 infra_metrics_adapter
Rôle :
- récupérer queues, backlog, reconnects, stale, DTR loss, log loss, CPU/RAM

### 4.5.5 meta_metrics_adapter
Rôle :
- récupérer DTR coverage, CRA alerts, sterilization rate, break-even, edge status

### 4.5.6 metrics_snapshot_builder
Rôle :
- construire un snapshot cohérent exploitable par alerting et dashboard

## 4.6 Inputs

- outputs du portfolio engine
- outputs du risk engine
- outputs des moteurs A/B
- outputs de data quality / infra
- outputs execution_cost_meter
- outputs DTR / CRA / edge tracker
- horloge système

## 4.7 Outputs

- snapshots métriques portefeuille
- snapshots métriques moteurs
- snapshots métriques paires
- snapshots infra
- snapshots meta
- publication normalisée pour alerting / dashboard

## 4.8 État interne

- dernier snapshot par famille
- horodatage du dernier refresh
- historique court des métriques clés
- indicateur de fraîcheur des métriques elles-mêmes

## 4.9 Invariants obligatoires

- toute métrique critique a une source définie
- chaque snapshot est horodaté
- les métriques affichées doivent être cohérentes entre elles
- les snapshots ne doivent pas mélanger des états incompatibles sans signaler leur âge

## 4.10 Exigences de design

- structure simple
- nomenclature stable
- séparation des familles de métriques
- compatibilité UI / alerting
- faible ambiguïté temporelle

## 4.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `portfolio_engine`
- `risk_engine`
- `execution_engine`
- `data_quality_engine`
- `meta_engine`

## 4.12 Dépendances interdites

- logique moteur active
- recalcul du signal
- actions opérateur

## 4.13 Logs attendus

- metrics snapshot built
- metrics source stale
- metrics family refresh
- metrics inconsistency warning

## 4.14 Métriques mathématiques minimales

### Portefeuille
\[
GrossExp = \sum_i x_i
\]
\[
LossBudget = \sum_i L_i
\]
\[
CE_{port} = \frac{\sum_i PnL_i}{\sum_i x_i h_i}
\]
\[
\Beta_{port} = \sum_j w_j \beta_j
\]

### Exécution / coût
\[
BE_{k,j} = \mathbb{E}[c \mid moteur=k, paire=j]
\]

### Meta
\[
SterilRate = \frac{\sum_i \mathbf{1}_{CE_i < CE_{min}}\mathbf{1}_{A_i=1}}{\sum_i A_i}
\]

### Infra
\[
\rho_q = \frac{\lambda}{\mu_s}
\]
\[
W_q = \frac{\lambda}{\mu_s(\mu_s-\lambda)}
\]
\[
DTRLossRate = \frac{N_{DTR,drops}}{N_{DTR,attempted}}
\]

## 4.15 Tests obligatoires

- snapshot portefeuille
- snapshot moteur
- snapshot paire
- snapshot infra
- snapshot meta
- horodatage cohérent
- incohérence source détectée
- métriques critiques présentes

## 4.16 Dérives possibles à ne pas faire

- afficher trop de métriques inutiles
- oublier les métriques de coût / CE
- agréger au point de masquer les moteurs ou paires
- utiliser des noms instables selon les écrans

## 4.17 Priorité
P0 absolue

## 4.18 Verdict
**Implémenter maintenant**

---

# 5. MODULE 2 — ALERT_MANAGER

## 5.1 Nom canonique
`alert_manager`

## 5.2 Mission

Transformer un sous-ensemble des métriques critiques en alertes réellement actionnables.

## 5.3 Responsabilités exactes

- définir les alertes officielles
- évaluer les conditions de déclenchement
- distinguer les niveaux de gravité
- réduire le bruit inutile
- journaliser les déclenchements et résolutions
- exposer des alertes aux dashboards et à l’UI

## 5.4 Ce que ce module ne doit pas faire

- alerter sur tout
- masquer les alertes graves dans du bruit
- lancer des actions irréversibles automatiques sans cadre explicite
- créer des règles ad hoc non versionnées

## 5.5 Sous-composants

### 5.5.1 alert_rule_registry
Rôle :
- lister les règles d’alerte officielles

### 5.5.2 severity_classifier
Rôle :
- classer info / warning / major / critical

### 5.5.3 deduplication_guard
Rôle :
- éviter les alertes répétitives identiques

### 5.5.4 resolution_tracker
Rôle :
- suivre l’ouverture / résolution des alertes

### 5.5.5 alert_reporter
Rôle :
- exposer les alertes actives et l’historique

## 5.6 Inputs

- snapshots du `metrics_collector`
- statuts système
- état du profil
- seuils d’alerte versionnés

## 5.7 Outputs

- alertes actives
- alertes résolues
- niveau de gravité
- raison codée
- horodatage ouverture / résolution

## 5.8 État interne

- règles d’alerte actives
- alertes ouvertes
- historique des alertes
- déduplication state

## 5.9 Invariants obligatoires

- chaque alerte a une règle source
- chaque alerte a une gravité explicite
- une alerte grave ne doit pas être noyée dans le bruit
- les résolutions doivent être traçables
- les alertes critiques doivent être visibles immédiatement dans l’UI

## 5.10 Exigences de design

- petit ensemble d’alertes à forte valeur
- déduplication
- gravité claire
- non-opacité
- compatibilité opérateur

## 5.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `metrics_collector`
- `health_dashboard_backend`
- `ui_light_locked`

## 5.12 Dépendances interdites

- recalcul des métriques
- logique moteur
- overrides cachés
- modifications runtime des caps

## 5.13 Logs attendus

- alert opened
- alert updated
- alert resolved
- alert deduplicated
- alert severity changed

## 5.14 Alertes minimales recommandées

### Data / infra
- stale hard
- pair suspended
- reconnect storm
- backlog high
- queue overload
- DTR loss non nul significatif
- log loss non nul significatif

### Exécution
- cost drift élevé
- reconciliation divergence
- partial fill anomaly

### Portefeuille / risque
- gross cap near/full
- loss budget near/full
- beta BTC breach
- cluster breach

### Meta
- sterilization spike
- break-even drift
- edge status degraded

## 5.15 Tests obligatoires

- ouverture alerte simple
- gravité correcte
- déduplication correcte
- résolution correcte
- alerte critique visible
- plusieurs alertes simultanées
- journalisation complète

## 5.16 Dérives possibles à ne pas faire

- alerte sur chaque petite variation
- pas de gravité claire
- alerte non résolue qui reste éternellement ouverte
- système d’alertes tellement bruyant qu’il est ignoré
- seuils non versionnés

## 5.17 Priorité
P0 absolue

## 5.18 Verdict
**Implémenter maintenant**

---

# 6. MODULE 3 — HEALTH_DASHBOARD_BACKEND

## 6.1 Nom canonique
`health_dashboard_backend`

## 6.2 Mission

Structurer les métriques et alertes en vues cohérentes pour l’interface Light.

## 6.3 Responsabilités exactes

- construire les datasets d’écran
- organiser l’information par vue :
  - overview portefeuille
  - profils & état
  - paires
  - moteurs
  - risque & exposition
  - coûts & exécution
  - data & infra
  - meta / DTR
  - logs / événements
- exposer une API backend stable pour l’UI
- garantir la cohérence entre écrans

## 6.4 Ce que ce module ne doit pas faire

- recalculer la logique métier
- modifier des états système
- autoriser des bypass de profil
- masquer des signaux critiques au profit d’un design cosmétique

## 6.5 Sous-composants

### 6.5.1 overview_view_builder
Rôle :
- construire la vue synthétique portefeuille

### 6.5.2 profile_state_view_builder
Rôle :
- exposer profil actif, état de déploiement, transitions

### 6.5.3 pair_view_builder
Rôle :
- tableau des paires, santé, coûts, CE, état

### 6.5.4 engine_view_builder
Rôle :
- tableau moteurs A/B, fréquence utile, coût, CE, Sharpe, état

### 6.5.5 risk_view_builder
Rôle :
- exposition, perte, beta BTC, clusters

### 6.5.6 execution_view_builder
Rôle :
- coûts, fills, partial fills, drift coût

### 6.5.7 infra_view_builder
Rôle :
- reconnects, queues, stale, DTR loss

### 6.5.8 meta_view_builder
Rôle :
- DTR coverage, CRA, break-even, edge status

## 6.6 Inputs

- snapshots du `metrics_collector`
- alertes du `alert_manager`
- statut du profil
- historique court utile

## 6.7 Outputs

- payloads backend par vue
- structures stables pour UI
- vues résumées + drill-down
- état agrégé du système

## 6.8 État interne

- version des vues
- derniers payloads
- timestamps par vue

## 6.9 Invariants obligatoires

- les vues critiques doivent être cohérentes entre elles
- les données affichées doivent avoir un âge connu
- les écrans critiques doivent afficher les métriques critiques
- aucune vue ne doit rendre invisibles les alertes majeures

## 6.10 Exigences de design

- structure simple
- API stable
- cohérence inter-vues
- orienté supervision
- faible ambiguïté temporelle

## 6.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `metrics_collector`
- `alert_manager`

## 6.12 Dépendances interdites

- modules moteurs
- modifications directes de l’état système
- logique de décision active

## 6.13 Logs attendus

- dashboard payload built
- view refreshed
- stale dashboard payload warning
- missing metric warning

## 6.14 Vues minimales obligatoires

### Overview portefeuille
- profil
- état déploiement
- capital
- exposition
- PnL
- CE
- beta BTC
- alertes critiques

### Profils & état
- Light actif
- état SHADOW / MICRO-LIVE / LIVE-LIGHT / DEGRADED / HALTED
- dernière transition

### Paires
- état
- santé
- coût moyen
- coût p90
- CE
- fréquence utile
- raisons de suspension

### Moteurs
- A / B
- fréquence utile
- rendement net
- coût
- CE
- Sharpe
- drawdown
- raison de suspension

### Risque
- GrossExp
- LossBudget
- Beta BTC
- cluster dominant
- breaches

### Exécution
- ELW
- coût attendu vs réalisé
- partial fills
- fill latency
- reconciliation alerts

### Data & infra
- reconnects
- queue usage
- backlog
- stale
- DTR loss
- log loss

### Meta
- DTR coverage
- CRA alerts
- sterilization rate
- break-even
- edge status

## 6.15 Tests obligatoires

- chaque vue se construit
- métriques minimales présentes
- alertes critiques visibles
- payloads horodatés
- vue stale détectée
- cohérence overview / risk / pair / engine

## 6.16 Dérives possibles à ne pas faire

- backend dashboard qui cache les métriques dérangeantes
- payloads différents selon les écrans sans cohérence
- absence de timestamps
- vues trop chargées pour être actionnables

## 6.17 Priorité
P0/P1

## 6.18 Verdict
**Implémenter maintenant**

---

# 7. MODULE 4 — UI_LIGHT_LOCKED

## 7.1 Nom canonique
`ui_light_locked`

## 7.2 Mission

Fournir une interface opérateur Light verrouillée, lisible, orientée risque/coût/état, sans possibilité de contourner le profil ou les garde-fous.

## 7.3 Responsabilités exactes

- afficher les vues critiques du backend dashboard
- afficher les alertes et états système
- permettre les actions autorisées du profil Light
- refuser explicitement les actions interdites
- journaliser toute action opérateur
- rester fonctionnelle en mode dégradé

## 7.4 Ce que ce module ne doit pas faire

- autoriser un profil custom
- activer moteurs C/D
- activer 12 paires
- bypass les hard blockers
- modifier les caps portefeuille
- devenir un cockpit de bricolage

## 7.5 Sous-composants

### 7.5.1 overview_screen
Rôle :
- synthèse portefeuille

### 7.5.2 profile_state_screen
Rôle :
- afficher profil Light et états officiels

### 7.5.3 pair_control_screen
Rôle :
- voir et suspendre/reprendre les paires autorisées

### 7.5.4 engine_screen
Rôle :
- suivre A/B et leur état

### 7.5.5 risk_screen
Rôle :
- voir budgets et breaches

### 7.5.6 execution_screen
Rôle :
- voir coûts et exécution

### 7.5.7 infra_screen
Rôle :
- voir qualité data et infra

### 7.5.8 meta_screen
Rôle :
- voir DTR, CRA, break-even, edge prudent

### 7.5.9 admin_control_panel_light
Rôle :
- exposer uniquement les actions autorisées

## 7.6 Inputs

- payloads du `health_dashboard_backend`
- alertes actives
- statut profil
- état des paires
- état des moteurs

## 7.7 Outputs

- affichage UI
- commandes opérateur autorisées
- journal d’actions opérateur
- refus UI explicites

## 7.8 État interne

- session opérateur
- dernière action
- historique local d’actions UI
- vue active
- filtres de consultation

## 7.9 Invariants obligatoires

- profil Light visible en permanence
- aucune action hors profil possible
- toute action sensible journalisée
- les alertes critiques doivent être visibles
- l’UI doit rester utile même si certaines vues secondaires sont indisponibles

## 7.10 Exigences de design

- sobre
- actionnable
- non permissive
- résistante au mode dégradé
- peu de boutons critiques
- cohérente avec le master canonique

## 7.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `health_dashboard_backend`
- `alert_manager`

## 7.12 Dépendances interdites

- accès direct aux moteurs
- accès direct à l’exécution live sans guards
- overrides des caps
- profil custom
- activation C/D
- activation > 6 paires

## 7.13 Actions autorisées Light

- consulter toutes les vues critiques
- suspendre une paire autorisée
- demander reprise d’une paire si conditions levées
- suspendre un moteur A ou B
- passer en HALTED
- consulter historique d’alertes et événements

## 7.14 Actions interdites Light

- charger Complete
- activer C
- activer D
- activer > 6 paires
- modifier caps de risque
- bypass hard blocker
- injecter une config non versionnée

## 7.15 Logs attendus

- operator action requested
- operator action accepted
- operator action rejected
- rejection reason
- screen opened
- critical alert acknowledged

## 7.16 Tests obligatoires

- profil Light visible
- action autorisée réussie
- action interdite refusée
- journalisation des actions
- alertes critiques visibles
- écran overview minimal fonctionnel
- UI cohérente en mode dégradé
- impossible d’activer C/D ou 12 paires

## 7.17 Dérives possibles à ne pas faire

- UI “power user” qui casse la discipline
- écran joli mais sans CE / coût / risque
- trop de boutons critiques
- refus UI silencieux
- masquer les alertes critiques derrière des menus

## 7.18 Priorité
P0/P1

## 7.19 Verdict
**Implémenter maintenant**

---

# 8. Interfaces entre modules Build-10

## 8.1 metrics_collector → alert_manager
- snapshots critiques
- métriques horodatées
- statuts source

## 8.2 metrics_collector + alert_manager → health_dashboard_backend
- métriques consolidées
- alertes actives
- état système

## 8.3 health_dashboard_backend + alert_manager → ui_light_locked
- payloads d’écran
- alertes actives
- état profil
- actions autorisées / interdites

## 8.4 ui_light_locked → monitoring / logs
- journal d’actions opérateur
- acknowledgements d’alertes
- refus d’actions

---

# 9. Ordre précis d’implémentation Build-10

## Étape 1
`metrics_collector`

Pourquoi :
- il faut d’abord centraliser les vérités utiles

## Étape 2
`alert_manager`

Pourquoi :
- les alertes dépendent de métriques structurées

## Étape 3
`health_dashboard_backend`

Pourquoi :
- les dashboards doivent être construits sur métriques + alertes déjà propres

## Étape 4
`ui_light_locked`

Pourquoi :
- l’UI vient en dernier, une fois l’information et les contraintes stabilisées

---

# 10. Table synthétique Build-10

| Module | Ordre | Priorité | Gate critique | Sortie attendue |
|---|---:|---:|---|---|
| metrics_collector | 1 | P0 | métriques critiques centralisées | supervision fiable |
| alert_manager | 2 | P0 | alertes actionnables | réaction opérateur possible |
| health_dashboard_backend | 3 | P0/P1 | vues cohérentes | dashboards exploitables |
| ui_light_locked | 4 | P0/P1 | UI non contournable | Light opérable et verrouillée |

---

# 11. Conditions de sortie de Build-10

Build-10 est terminé si :

- les métriques critiques sont centralisées et horodatées
- les alertes minimales sont actives et classées
- les vues dashboards Light sont complètes
- l’UI Light expose les bonnes actions et refuse les mauvaises
- les coûts, la CE, la santé infra et la meta sont visibles
- aucune action Light ne permet de sortir du périmètre validé

---

# 12. Critères de refus de sortie

Refuser Build-10 si :

- `metrics_collector` omet des métriques critiques
- `alert_manager` produit trop de bruit ou pas assez de signal
- `health_dashboard_backend` masque les alertes critiques
- `ui_light_locked` permet d’activer des fonctions Complete
- l’opérateur ne voit pas clairement coût / CE / risque / santé

---

# 13. Dérives globales Build-10 à ne pas faire

- construire une UI avant d’avoir des métriques propres
- faire de l’alerting “tout rouge tout le temps”
- masquer la CE et les coûts derrière le PnL
- utiliser l’UI comme outil d’expérimentation libre
- faire des dashboards qui impressionnent mais n’aident pas à décider

---

# 14. Verdict final Build-10

Build-10 est la couche qui transforme la V5.3 Light en système **supervisable en conditions réelles**.

Si Build-10 est bien fait :
- l’opérateur voit le vrai état du système
- les coûts, la CE, les budgets et les alertes deviennent actionnables
- la Light devient gouvernable sans bricolage
- la transition vers Shadow / Micro-live / Live-Light devient crédible

Si Build-10 est mal fait :
- la Light restera opaque malgré de bons modules internes
- les problèmes seront vus trop tard
- l’UI pourra casser la discipline
- la production perdra sa safety opérationnelle

Donc :

> Build-10 doit être traité comme un **build bloquant de supervision et d’interface sécurisée**, pas comme une simple couche de présentation.

---

## Fin du document
