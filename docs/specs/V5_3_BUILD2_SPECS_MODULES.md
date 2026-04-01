# V5.3 — BUILD-2 SPECS MODULES
## Data Backbone Pack
### Specs détaillées module par module
### Deuxième étape officielle du développement
### Sans code — prod-safe

---

# 0. Objet du document

Ce document couvre **Build-2** du plan officiel V5.3.

Build-2 a une mission unique :

> construire une couche data et qualité de données suffisamment robuste pour que les modules métier futurs puissent prendre des décisions sur une base fiable.

Les modules couverts ici sont :

1. `websocket_gateway`
2. `rest_bootstrap`
3. `event_normalizer`
4. `internal_router`
5. `freshness_checker`
6. `consistency_checker`
7. `pair_health_scorer`

Aucun moteur, aucun scoring, aucun risk gating métier ne doit être développé sérieusement tant que ces sept briques ne sont pas correctement spécifiées, testées et gelées.

---

# 1. Principes Build-2

## 1.1 Objectif stratégique

Build-2 ne cherche pas encore à produire des signaux.  
Il cherche à garantir que, plus tard, un signal signifiera réellement quelque chose.

En pratique, Build-2 doit empêcher :
- les décisions sur données obsolètes
- les incohérences d’état entre flux
- la contamination d’une paire vers les autres
- l’aveuglement sur les dégradations de streaming
- les architectures qui “ont l’air de marcher” alors qu’elles dérivent silencieusement

## 1.2 Critère de réussite

Build-2 est réussi si :

- l’ingestion WS est stable
- les événements sont normalisés proprement
- la fraîcheur est mesurable
- la cohérence des flux est testée
- chaque paire a un score de santé exploitable
- un flux dégradé peut suspendre une paire sans casser le portefeuille entier
- les métriques de backlog / stale / reconnect / disorder sont visibles

## 1.3 Critère d’échec

Build-2 échoue si :

- le système peut encore prendre une décision sur donnée périmée sans le savoir
- les événements n’ont pas de schéma stable
- la reconnexion casse l’état
- une paire dégradée contamine tout le système
- le backlog existe mais n’est pas mesuré
- la qualité de données est réduite à “connexion ouverte = tout va bien”

---

# 2. Vocabulaire officiel Build-2

## 2.1 Événement brut
Message reçu de l’exchange tel quel ou quasi tel quel.

## 2.2 Événement normalisé
Message converti en structure interne stable et versionnée.

## 2.3 Fraîcheur
Âge entre le moment de décision et la dernière mise à jour réellement exploitable.

## 2.4 Cohérence
Compatibilité logique entre les flux observés :
- ordre
- timestamps
- séquences
- complétude
- absence de contradictions majeures

## 2.5 Santé paire
Score synthétique reflétant si une paire peut rester active dans le système.

---

# 3. Architecture Build-2

## 3.1 Chaîne de traitement

1. `websocket_gateway`  
2. `rest_bootstrap`  
3. `event_normalizer`  
4. `internal_router`  
5. `freshness_checker`  
6. `consistency_checker`  
7. `pair_health_scorer`

## 3.2 Principes de hiérarchie

- l’ingestion ne dépend pas des modules métier
- la qualité de données ne dépend pas des signaux
- la santé paire est un verdict opérationnel, pas un score de trading
- les modules de Build-2 doivent rester utilisables en isolation

---

# 4. MODULE 1 — WEBSOCKET_GATEWAY

## 4.1 Nom canonique
`websocket_gateway`

## 4.2 Mission

Assurer une connexion fiable, observable et reconnectable aux flux WS nécessaires.

## 4.3 Responsabilités exactes

- établir les connexions WS
- gérer les abonnements par paire et par type de flux
- surveiller les heartbeats
- détecter les coupures
- reconnecter proprement
- horodater la réception
- transmettre les messages bruts au normalizer
- mesurer la dégradation de service

## 4.4 Ce que ce module ne doit pas faire

- parser profondément la logique métier
- décider si un signal est bon ou mauvais
- calculer des features complexes
- masquer silencieusement les pertes de flux
- dépendre de signal_engine, scoring_engine, risk_engine, execution_engine

## 4.5 Sous-composants

### 4.5.1 connection_manager
Rôle :
- ouverture / fermeture des sockets
- gestion de session
- reconnexion

### 4.5.2 subscription_manager
Rôle :
- gestion des abonnements
- mapping paire → flux

### 4.5.3 heartbeat_monitor
Rôle :
- surveiller présence des heartbeats / activity minimale
- détecter le silence anormal

### 4.5.4 reconnect_controller
Rôle :
- stratégie de reconnexion
- backoff
- reprise propre

### 4.5.5 raw_message_emitter
Rôle :
- transmettre les messages bruts avec métadonnées minimales

## 4.6 Inputs

- configuration des flux par paire
- profil actif (Light / Complete)
- liste des paires autorisées
- état de connexion précédent si recovery

## 4.7 Outputs

- événements bruts structurés minimalement
- événements de connexion / reconnexion
- métriques de latence et de backlog brut
- signaux de dégradation vers monitoring et qualité data

## 4.8 État interne

- connexions actives
- horodatage dernier message par flux
- compteur reconnects
- statut heartbeat
- files de messages en attente
- séquence de session

## 4.9 Invariants obligatoires

- chaque message brut doit avoir un `recv_time`
- chaque flux doit avoir un statut explicite
- la reconnexion doit être journalisée
- l’absence de flux doit être visible
- aucun message brut ne doit être réordonné silencieusement

## 4.10 Exigences de design

- module autonome
- observabilité native
- faible logique métier
- distinction claire entre :
  - flux vivant
  - flux silencieux
  - flux reconnecté
  - flux dégradé
- compatibilité Light / Complete

## 4.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- outils réseau / async officiels retenus
- `monitoring_engine` en sortie logique uniquement

## 4.12 Dépendances interdites

- signal_engine
- scoring_engine
- risk_engine
- execution_engine
- portfolio_engine

## 4.13 Logs attendus

- open / close socket
- subscribe / unsubscribe
- reconnect start / reconnect success / reconnect fail
- heartbeat miss
- silence duration
- raw message drop count
- backlog brut

## 4.14 Métriques mathématiques utiles

Taux total d’arrivée :
\[
\lambda_{tot} = \sum_{j=1}^{M}\sum_{f=1}^{F}\lambda_{j,f}
\]

Capacité de service :
\[
\mu_s
\]

Utilisation :
\[
\rho_q = \frac{\lambda_{tot}}{\mu_s}
\]

Stabilité :
\[
\lambda_{tot} < \mu_s
\]

Latence moyenne de file \(M/M/1\) approximative :
\[
W_q = \frac{\lambda_{tot}}{\mu_s(\mu_s-\lambda_{tot})}
\]

## 4.15 Tests obligatoires

- ouverture initiale
- reconnexion simple
- reconnexion multiple
- heartbeat absent
- silence prolongé sur un flux
- double abonnement interdit
- messages bruts reçus avec recv_time
- stress flux élevé
- backlog croissant détecté

## 4.16 Dérives possibles à ne pas faire

- considérer qu’un socket ouvert = flux sain
- ne pas distinguer silence et vraie coupure
- redémarrer sans journaliser
- laisser croître le backlog sans alerte
- brancher plus de flux que nécessaire
- faire de la logique métier ici

## 4.17 Priorité
P0 absolue

## 4.18 Verdict
**Implémenter maintenant**

---

# 5. MODULE 2 — REST_BOOTSTRAP

## 5.1 Nom canonique
`rest_bootstrap`

## 5.2 Mission

Fournir une procédure contrôlée de bootstrap et de resynchronisation par REST sans remplacer le streaming temps réel.

## 5.3 Responsabilités exactes

- récupérer les snapshots initiaux nécessaires
- combler un gap contrôlé
- réaligner l’état local si recovery
- respecter les limites API
- signaler explicitement l’âge et la validité du snapshot

## 5.4 Ce que ce module ne doit pas faire

- servir de pseudo temps réel permanent
- faire des polls frénétiques pour masquer un mauvais WS
- injecter silencieusement un snapshot ancien
- fusionner un snapshot sans contrôle de cohérence

## 5.5 Sous-composants

### 5.5.1 snapshot_fetcher
Rôle :
- récupérer le snapshot requis

### 5.5.2 rate_limit_guard
Rôle :
- protéger les quotas API
- journaliser l’usage

### 5.5.3 gap_fill_controller
Rôle :
- décider si un gap est acceptable à combler
- limiter l’ampleur des rattrapages

### 5.5.4 snapshot_age_validator
Rôle :
- calculer l’âge d’un snapshot
- invalider un snapshot trop vieux

### 5.5.5 bootstrap_reporter
Rôle :
- rapport de bootstrap / resync

## 5.6 Inputs

- paire ciblée
- type de snapshot nécessaire
- raison du bootstrap
- état de la session WS
- configuration quotas

## 5.7 Outputs

- snapshot validé
- snapshot rejeté
- rapport d’âge snapshot
- rapport de quota utilisé
- alerte si gap-fill excessif

## 5.8 État interne

- dernier bootstrap par paire
- compteur appels REST
- fenêtre de quota
- dernier échec bootstrap

## 5.9 Invariants obligatoires

- tout snapshot a un âge calculé
- aucun snapshot trop ancien n’est accepté silencieusement
- tout usage REST est explicite
- tout gap-fill a une taille mesurée
- le REST ne doit pas devenir le temps réel principal

## 5.10 Exigences de design

- REST utilisé uniquement pour :
  - bootstrap
  - recovery
  - gap-fill contrôlé
- pas de poll continu non justifié
- journalisation complète des usages

## 5.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- client REST officiel
- `data_quality_engine` comme consommateur logique

## 5.12 Dépendances interdites

- moteurs
- scoring
- logique d’exécution métier
- heuristiques de signal

## 5.13 Logs attendus

- bootstrap requested
- bootstrap success/fail
- snapshot age
- quota usage
- gap-fill count
- snapshot rejected

## 5.14 Métriques mathématiques utiles

Âge snapshot :
\[
\Delta_{snap} = t_{now} - t_{snapshot}
\]

Tolérance max :
\[
\Delta_{snap} \le \Delta_{snap,max}
\]

Taux d’usage REST :
\[
RESTRate = \frac{N_{REST}}{\text{temps}}
\]

## 5.15 Tests obligatoires

- bootstrap simple
- bootstrap après reconnexion
- snapshot trop vieux refusé
- gap-fill trop grand refusé
- quota dépassé géré
- rapport de bootstrap généré

## 5.16 Dérives possibles à ne pas faire

- masquer un mauvais WS par du REST
- accepter un snapshot vieux “par pragmatisme”
- bootstrap silencieux sans motif
- ne pas mesurer la fréquence d’usage REST

## 5.17 Priorité
P0 absolue

## 5.18 Verdict
**Implémenter maintenant**

---

# 6. MODULE 3 — EVENT_NORMALIZER

## 6.1 Nom canonique
`event_normalizer`

## 6.2 Mission

Convertir tous les événements bruts en structures internes stables, versionnées, horodatées et homogènes.

## 6.3 Responsabilités exactes

- parser les messages bruts
- identifier leur type
- convertir vers les contrats internes
- enrichir avec :
  - recv_time
  - source
  - paire
  - type flux
  - version schéma
- rejeter explicitement les messages invalides

## 6.4 Ce que ce module ne doit pas faire

- scorer les signaux
- agréger des features métier
- reconstruire des décisions
- masquer des champs manquants
- produire des objets ambigus

## 6.5 Sous-composants

### 6.5.1 schema_mapper
Rôle :
- mapper raw payload → contrat interne

### 6.5.2 timestamp_enricher
Rôle :
- ajouter recv_time
- transporter exchange_time si disponible
- calculer drift si utile

### 6.5.3 message_classifier
Rôle :
- identifier le type de message

### 6.5.4 invalid_message_guard
Rôle :
- rejeter proprement les messages non conformes

### 6.5.5 normalization_reporter
Rôle :
- suivre les succès / rejets / anomalies

## 6.6 Inputs

- raw messages WS
- raw data REST
- contrats d’interface

## 6.7 Outputs

- TradeEvent
- DepthEvent
- KlineEvent
- HeartbeatEvent
- SnapshotEvent
- erreurs de normalisation

## 6.8 État interne

- version schéma courante
- compteurs de normalisation
- compteurs d’erreurs
- compteurs par type d’événement

## 6.9 Invariants obligatoires

- chaque événement normalisé doit avoir :
  - type
  - paire
  - source
  - recv_time
- aucun raw payload ne doit fuir dans les modules métiers
- toute erreur de parsing doit être visible

## 6.10 Exigences de design

- déterministe
- schéma stable
- versionnable
- explicite sur les valeurs manquantes
- homogène pour toutes les paires

## 6.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`

## 6.12 Dépendances interdites

- scoring
- signaux
- exécution
- risque
- portfolio

## 6.13 Logs attendus

- event normalized
- invalid event rejected
- missing field
- unexpected type
- schema version used

## 6.14 Métriques mathématiques utiles

Latence événement :
\[
Lat_u = t_{recv,u} - t_{exch,u}
\]

Drift :
\[
Drift_u = t_{local} - t_{reference}
\]

Taux de rejet :
\[
RejectRate = \frac{N_{reject}}{N_{raw}}
\]

## 6.15 Tests obligatoires

- mapping trade
- mapping depth
- mapping kline
- champ manquant
- type inattendu
- timestamp enrichi
- rejet explicite

## 6.16 Dérives possibles à ne pas faire

- laisser circuler des raw dicts
- ajouter de la logique métier au normalizer
- normalisation différente selon la paire
- tolérer silencieusement des champs absents
- ne pas versionner les schémas

## 6.17 Priorité
P0 absolue

## 6.18 Verdict
**Implémenter maintenant**

---

# 7. MODULE 4 — INTERNAL_ROUTER

## 7.1 Nom canonique
`internal_router`

## 7.2 Mission

Distribuer les événements normalisés vers les bons consommateurs sans créer de contention ou de contamination croisée.

## 7.3 Responsabilités exactes

- router les événements par type et par paire
- gérer des queues dédiées par consommateur
- appliquer les priorités
- mesurer le backlog
- protéger les consommateurs critiques

## 7.4 Ce que ce module ne doit pas faire

- faire du métier
- transformer les événements
- laisser un consommateur non critique bloquer le système
- masquer un backlog croissant

## 7.5 Sous-composants

### 7.5.1 consumer_registry
Rôle :
- enregistrer les consommateurs et leurs subscriptions

### 7.5.2 priority_dispatcher
Rôle :
- dispatch avec priorité

### 7.5.3 queue_manager
Rôle :
- queues par consommateur
- mesures backlog
- mesures saturation

### 7.5.4 backpressure_guard
Rôle :
- protéger le système si un consommateur ralentit

### 7.5.5 routing_reporter
Rôle :
- rapport de distribution

## 7.6 Inputs

- événements normalisés
- registry consommateurs
- politique de priorité

## 7.7 Outputs

- événements distribués aux files internes
- alertes backlog
- alertes saturations consommateurs

## 7.8 État interne

- subscriptions
- queues par consommateur
- profondeur des queues
- âge moyen en queue
- compteurs drops si bornage

## 7.9 Invariants obligatoires

- priorité execution/risk > analytics
- backlog visible par consommateur
- aucun consommateur non critique ne doit geler ingestion
- toute perte de message bornée et visible

## 7.10 Exigences de design

- routing déterministe
- priorité explicite
- isolation partielle des consommateurs
- métriques de queue natives

## 7.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `monitoring_engine` logique

## 7.12 Dépendances interdites

- dépendance métier directe à un moteur
- dépendance à des modules business concrets

## 7.13 Logs attendus

- queue size
- dispatch success/fail
- backpressure triggered
- consumer lag
- dropped message count

## 7.14 Métriques mathématiques utiles

Taux arrivée file \(m\) :
\[
\lambda_m
\]

Taux service file \(m\) :
\[
\mu_m
\]

Backlog :
\[
B_m(t+1)=B_m(t)+A_m(t)-S_m(t)
\]

Utilisation file :
\[
\rho_m=\frac{\lambda_m}{\mu_m}
\]

## 7.15 Tests obligatoires

- dispatch simple
- plusieurs consommateurs
- priorité correcte
- consommateur lent
- backlog détecté
- drops visibles si file bornée

## 7.16 Dérives possibles à ne pas faire

- file unique géante
- analytics même priorité que execution
- backlog non exposé
- consommateur lent qui bloque tout

## 7.17 Priorité
P0 absolue

## 7.18 Verdict
**Implémenter maintenant**

---

# 8. MODULE 5 — FRESHNESS_CHECKER

## 8.1 Nom canonique
`freshness_checker`

## 8.2 Mission

Mesurer en permanence si l’information utilisée pour une décision est encore exploitable.

## 8.3 Responsabilités exactes

- calculer l’âge de la dernière donnée utile par paire et par flux
- produire des pénalités de fraîcheur
- déclencher un hard block stale si nécessaire
- exposer la fraîcheur aux modules aval

## 8.4 Ce que ce module ne doit pas faire

- décider seul d’un trade
- masquer un stale sévère par une pénalité “douce”
- ignorer la différence entre flux et paire

## 8.5 Sous-composants

### 8.5.1 last_update_tracker
Rôle :
- stocker dernier update par flux / paire

### 8.5.2 age_calculator
Rôle :
- calculer \(\Delta\)

### 8.5.3 stale_penalty_builder
Rôle :
- produire pénalité graduelle

### 8.5.4 stale_hard_guard
Rôle :
- déclencher un stale block explicite

### 8.5.5 freshness_reporter
Rôle :
- rapport stale

## 8.6 Inputs

- horodatages événements normalisés
- temps de décision
- seuils stale

## 8.7 Outputs

- âge par flux / paire
- pénalité stale
- verdict stale hard
- alertes stale

## 8.8 État interne

- dernier timestamp utile par flux
- dernier verdict stale par paire

## 8.9 Invariants obligatoires

- l’âge doit être mesuré explicitement
- stale hard doit être traçable
- toute décision aval doit pouvoir consulter la fraîcheur

## 8.10 Exigences de design

- granularité par paire
- granularité par type de flux
- pénalité graduelle + hard cut
- pas de magie implicite

## 8.11 Dépendances autorisées

- `interface_contracts`
- `event_normalizer`
- `internal_router`

## 8.12 Dépendances interdites

- moteurs
- scoring métier complet
- exécution

## 8.13 Logs attendus

- stale penalty
- stale hard block
- âge max observé
- flux manquant

## 8.14 Métriques mathématiques utiles

Âge :
\[
\Delta_i = t_{decision} - t_{last\ update}
\]

Pénalité :
\[
pen_{stale}(\Delta_i)=\lambda \max(0,\Delta_i-\Delta_{max})
\]

Hard block si :
\[
\Delta_i > \Delta_{hard}
\]

## 8.15 Tests obligatoires

- flux frais
- flux légèrement stale
- flux stale hard
- reprise après mise à jour fraîche
- multi-flux par paire

## 8.16 Dérives possibles à ne pas faire

- stale binaire seulement
- stale global sans granularité paire
- stale invisible aux logs
- seuils trop agressifs qui stérilisent le système

## 8.17 Priorité
P0 absolue

## 8.18 Verdict
**Implémenter maintenant**

---

# 9. MODULE 6 — CONSISTENCY_CHECKER

## 9.1 Nom canonique
`consistency_checker`

## 9.2 Mission

Détecter les contradictions et anomalies structurelles entre les flux.

## 9.3 Responsabilités exactes

- détecter duplication
- détecter disorder
- détecter gaps
- détecter séquences impossibles
- produire un score de cohérence exploitable

## 9.4 Ce que ce module ne doit pas faire

- prétendre résoudre toute vérité du marché
- ignorer les anomalies “parce que c’est crypto”
- remplacer la logique de santé paire

## 9.5 Sous-composants

### 9.5.1 sequence_checker
Rôle :
- ordre logique des messages

### 9.5.2 gap_detector
Rôle :
- trous observables

### 9.5.3 duplicate_detector
Rôle :
- duplications de messages

### 9.5.4 contradiction_checker
Rôle :
- événements incompatibles

### 9.5.5 consistency_reporter
Rôle :
- rapport cohérence

## 9.6 Inputs

- événements normalisés
- séquences attendues
- métadonnées flux

## 9.7 Outputs

- disorder rate
- gap rate
- duplicate rate
- consistency score
- alertes cohérence

## 9.8 État interne

- derniers ids / séquences vus
- compteurs anomalies par paire / flux

## 9.9 Invariants obligatoires

- toute anomalie doit être visible
- cohérence par paire et par flux
- aucune paire ne doit être considérée saine sans cohérence minimale

## 9.10 Exigences de design

- règles explicites
- anomalies non silencieuses
- score interprétable
- séparation de la santé et de la cohérence brute

## 9.11 Dépendances autorisées

- `interface_contracts`
- `event_normalizer`
- `freshness_checker` logique faible si nécessaire

## 9.12 Dépendances interdites

- scoring métier
- moteurs
- exécution

## 9.13 Logs attendus

- disorder event
- duplicate event
- gap event
- contradiction event
- consistency score update

## 9.14 Métriques mathématiques utiles

Score cohérence :
\[
ConsistencyScore = 1 - (w_1 Gaps + w_2 Duplicates + w_3 Disorder + w_4 Contradictions)
\]

Taux de gaps :
\[
GapRate = \frac{N_{gaps}}{N_{expected}}
\]

Taux de duplication :
\[
DupRate = \frac{N_{dup}}{N_{events}}
\]

## 9.15 Tests obligatoires

- séquence propre
- disorder simple
- duplication simple
- trous
- contradiction artificielle
- score cohérence mis à jour

## 9.16 Dérives possibles à ne pas faire

- score opaque
- anomalies seulement globales
- tolérer des trous sans les tracer
- considérer l’absence d’erreur fatale comme cohérence suffisante

## 9.17 Priorité
P0 absolue

## 9.18 Verdict
**Implémenter maintenant**

---

# 10. MODULE 7 — PAIR_HEALTH_SCORER

## 10.1 Nom canonique
`pair_health_scorer`

## 10.2 Mission

Produire le verdict opérationnel final sur la capacité d’une paire à rester active.

## 10.3 Responsabilités exactes

- agréger fraîcheur, cohérence, latence, recovery
- produire un score de santé \(H_j\)
- déclencher la suspension paire si nécessaire
- permettre la reprise propre quand les conditions redeviennent saines

## 10.4 Ce que ce module ne doit pas faire

- faire du scoring de trading
- masquer les raisons de suspension
- devenir un hard blocker global du système entier
- suspendre de manière irréversible sans motif

## 10.5 Sous-composants

### 10.5.1 quality_aggregator
Rôle :
- agréger freshness + consistency + latence + recovery

### 10.5.2 suspension_decider
Rôle :
- suspendre si santé sous seuil

### 10.5.3 recovery_evaluator
Rôle :
- décider si la paire peut revenir

### 10.5.4 health_state_tracker
Rôle :
- suivre actif / dégradé / suspendu / recovery

### 10.5.5 health_reporter
Rôle :
- rapport santé détaillé

## 10.6 Inputs

- freshness metrics
- consistency metrics
- latence observée
- statut reconnect / recovery
- politique de seuils

## 10.7 Outputs

- score \(H_j\)
- état paire
- raison de suspension
- raison de reprise
- alertes santé

## 10.8 État interne

- dernier score santé
- dernier état
- historique suspensions / reprises
- compteurs de transitions

## 10.9 Invariants obligatoires

- toute suspension a une raison explicite
- toute reprise a une raison explicite
- une paire suspendue ne doit pas contaminer les autres
- l’état santé doit être consultable par les modules aval

## 10.10 Exigences de design

- santé par paire
- santé interprétable
- transitions d’état explicites
- reprise contrôlée
- compatibilité Light / Complete

## 10.11 Dépendances autorisées

- `freshness_checker`
- `consistency_checker`
- `interface_contracts`
- `manifest_registry`

## 10.12 Dépendances interdites

- moteurs
- scoring métier
- exécution

## 10.13 Logs attendus

- health score update
- suspension pair
- resume pair
- health reason codes
- transition history

## 10.14 Métriques mathématiques utiles

Score santé :
\[
H_j = w_Q Q_j + w_L L_j + w_C C_j + w_R R_j
\]

Suspension si :
\[
H_j < H_{min}
\]

Reprise si :
\[
H_j > H_{resume}
\]

avec idéalement hystérésis :
\[
H_{resume} > H_{min}
\]

## 10.15 Tests obligatoires

- santé normale
- santé dégradée
- suspension paire
- reprise paire
- hystérésis
- non-contamination inter-paires

## 10.16 Dérives possibles à ne pas faire

- score santé magique incompréhensible
- même seuil pour suspension et reprise
- suspension silencieuse
- pas d’historique de transitions

## 10.17 Priorité
P0 absolue

## 10.18 Verdict
**Implémenter maintenant**

---

# 11. Interfaces entre modules Build-2

## 11.1 websocket_gateway → event_normalizer
- raw message envelope
- recv_time
- source
- pair
- stream type

## 11.2 rest_bootstrap → event_normalizer
- snapshot envelope
- snapshot age
- bootstrap context

## 11.3 event_normalizer → internal_router
- événements normalisés typés

## 11.4 internal_router → freshness_checker
- timestamps et événements routés

## 11.5 internal_router → consistency_checker
- séquences et événements

## 11.6 freshness_checker + consistency_checker → pair_health_scorer
- freshness metrics
- consistency metrics
- anomalies

## 11.7 pair_health_scorer → modules aval
- état paire
- score santé
- suspension / reprise

---

# 12. Ordre précis d’implémentation Build-2

## Étape 1
`websocket_gateway`

Pourquoi :
- aucune data temps réel sans lui

## Étape 2
`rest_bootstrap`

Pourquoi :
- bootstrap et recovery doivent exister avant normalisation complète

## Étape 3
`event_normalizer`

Pourquoi :
- aucun module aval ne doit consommer du raw

## Étape 4
`internal_router`

Pourquoi :
- les consommateurs aval ont besoin d’un flux proprement dispatché

## Étape 5
`freshness_checker`

Pourquoi :
- la fraîcheur est la première vérité qualité

## Étape 6
`consistency_checker`

Pourquoi :
- la cohérence complète la fraîcheur

## Étape 7
`pair_health_scorer`

Pourquoi :
- la paire ne peut être activée que si sa santé est calculable

---

# 13. Table synthétique Build-2

| Module | Ordre | Priorité | Gate critique | Sortie attendue |
|---|---:|---:|---|---|
| websocket_gateway | 1 | P0 | connect/reconnect/heartbeat | flux bruts fiables |
| rest_bootstrap | 2 | P0 | snapshot valide | bootstrap propre |
| event_normalizer | 3 | P0 | schéma stable | événements typés |
| internal_router | 4 | P0 | priorité + backlog | distribution sûre |
| freshness_checker | 5 | P0 | stale visible | fraîcheur mesurable |
| consistency_checker | 6 | P0 | anomalies visibles | cohérence mesurable |
| pair_health_scorer | 7 | P0 | suspension/reprise propres | santé paire exploitable |

---

# 14. Conditions de sortie de Build-2

Build-2 est terminé si :

- chaque module existe
- chaque module passe ses tests
- le pipeline Build-1 protège leurs interfaces et dépendances
- la donnée temps réel est observable
- la qualité data est mesurable
- une paire peut être suspendue sans casser le reste
- les métriques backlog / stale / reconnect / consistency / health sont visibles

---

# 15. Critères de refus de sortie

Refuser Build-2 si :

- `websocket_gateway` ne mesure pas les heartbeats ou reconnects
- `rest_bootstrap` est utilisé comme temps réel déguisé
- `event_normalizer` laisse passer des payloads ambigus
- `internal_router` masque le backlog
- `freshness_checker` ne produit pas de stale hard
- `consistency_checker` ne trace pas les anomalies
- `pair_health_scorer` suspend sans raison explicite

---

# 16. Dérives globales Build-2 à ne pas faire

- démarrer le signal_engine avant pair_health fonctionnel
- tolérer des flux “presque bons”
- considérer que du WS connecté = data saine
- cacher les anomalies pour garder le système “vert”
- confondre santé paire et qualité d’un trade
- agréger trop tôt des métriques globales sans granularité paire

---

# 17. Verdict final Build-2

Build-2 est la couche qui détermine si les modules métier futurs seront :
- fiables
- auditables
- économiquement interprétables

Sans Build-2 bien fait :
- les signaux seront faux
- les coûts seront mal compris
- les DTR seront trompeurs
- les suspensions de paires seront arbitraires
- la prod sera fragile

Donc :

> Build-2 doit être traité comme un **build bloquant runtime**, pas comme un simple pipeline data.

---

# Guardrails P0 issus des audits — Invariants Build-2

## Buffer policy explicite (GEM-05)
- Tout buffer de messages (`RawMessageEmitter` ou équivalent) doit utiliser `collections.deque(maxlen=K)`
- Politique obligatoire : **drop_oldest**, jamais drop_newest
- Garantit que le système travaille toujours sur le dernier tick reçu pendant les pics de volatilité

## Jitter tolerance (GEM-06)
- Le `contradiction_checker` doit implémenter une fenêtre de tolérance configurable (défaut : 5-10ms)
- Sur les exchanges distribués, l'out-of-order est un comportement réseau normal
- `TIMESTAMP_REVERSAL` ne doit être levé que si le retard dépasse le seuil de jitter configurable
- Faux positifs de jitter ≠ anomalies réelles

## Stale guard explicite (GEM-23)
- Chaque message entrant doit être comparé : `delta = local_timestamp - exchange_timestamp`
- Si `delta > seuil_stale_ms` (configurable, défaut 200ms), le message est marqué stale
- Un message stale ne doit pas alimenter le pipeline de décision en mode `MICRO_LIVE` ou `LIVE`
- En `SHADOW`, le stale est loggé mais pas bloquant

## Latence monotone et plausibility checks (GEM-08, QWEN-13)
- Toute mesure de latence doit utiliser un clock monotone (`time.monotonic()` ou `time.perf_counter()`)
- Les valeurs de latence négatives ou aberrantes (> seuil max) doivent être filtrées
- Une latence aberrante ne doit pas corrompre les statistiques moyennes
- Protection contre les sauts NTP dans les environnements conteneurisés

## Backlog saturation metrics (GEM-18)
- Le `internal_router` doit exposer des métriques de saturation :
  - high-water mark du backlog
  - drop rate (% de messages perdus)
  - taux de stale spikes
- Ces métriques sont obligatoires pour Build-10 (monitoring)

## Distinction "socket ouvert" ≠ "flux sain" (QWEN-03)
- Une connexion WebSocket ouverte ne signifie pas que le flux de données est valide
- Le `pair_health_scorer` doit intégrer la qualité réelle du flux, pas seulement l'état de connexion
- `pair_quarantine` doit être explicite : un pair en quarantaine ne doit pas recevoir de signaux

---

## Fin du document
