# V5.3 — BUILD-9 SPECS MODULES
## Meta Minimal Pack
### Specs détaillées module par module
### Neuvième étape officielle du développement
### Sans code — prod-safe

---

# 0. Objet du document

Ce document couvre **Build-9** du plan officiel V5.3.

Build-9 a une mission unique :

> donner au système un niveau minimal mais suffisant d’explicabilité économique et causale, pour que la V5.3 Light ne soit pas pilotée à l’intuition, au PnL brut ou aux impressions de marché.

Les modules couverts ici sont :

1. `dtr_core`
2. `cra_monitor`
3. `break_even_dashboard`
4. `edge_tracker_prudent_minimal`

Build-9 ne cherche pas à construire toute la couche meta finale de la V5.3 Complete.  
Il construit le **noyau minimal obligatoire** pour :

- comprendre les décisions
- détecter la stérilisation économique
- suivre le coût de rentabilité réel
- surveiller l’edge net avec prudence

Aucun passage sérieux en micro-live robuste ou live-light ne doit être envisagé tant que ces quatre briques ne sont pas correctement spécifiées, testées et gelées.

---

# 1. Principes Build-9

## 1.1 Objectif stratégique

À ce stade du projet, le système sait déjà :

- ingérer la donnée
- vérifier sa qualité
- exécuter
- mesurer les coûts réels
- borner le risque
- scorer
- produire des moteurs A/B
- arbitrer un portefeuille minimal

Mais sans Build-9, il manque encore la capacité à répondre proprement à quatre questions fondamentales :

1. **Pourquoi ce trade a-t-il été pris ou non pris ?**
2. **Combien de trades sont devenus économiquement stériles ?**
3. **Quel est le vrai seuil de rentabilité après coûts ?**
4. **L’edge net observé reste-t-il crédible, ou est-il en train de dériver ?**

Build-9 existe pour fournir ces réponses.

## 1.2 Position dans l’architecture

Build-9 est :
- **obligatoire en Light**
- **obligatoire en Complete**
- **P0**
- la première vraie couche d’intelligence d’observabilité économique
- la couche qui transforme les journaux en lecture exploitable

## 1.3 Critère de réussite

Build-9 est réussi si :

- chaque décision est reconstructible
- les trades phantom sont mesurables
- le break-even réel est visible par moteur et par paire
- l’edge net est suivi sans prétention faussement académique
- les modules précédents deviennent auditables ex post
- le système peut distinguer :
  - signal rare
  - signal bloqué
  - signal pénalisé
  - signal sélectionné
  - trade stérilisé

## 1.4 Critère d’échec

Build-9 échoue si :

- les décisions ne sont pas traçables
- les trade refusés disparaissent sans raison structurée
- le break-even reste implicite
- le coût est suivi mais jamais relié à la rentabilité
- l’edge est traité comme une moyenne brute sans prudence
- les phantom trades ne sont pas distingués des trades productifs

---

# 2. Vocabulaire officiel Build-9

## 2.1 DTR
Decision Trace Record : enregistrement causal minimal d’une décision de trading.

## 2.2 CRA
Cumulative Reduction Alarm : signal indiquant qu’un trade est devenu économiquement stérile par accumulation de réductions ou de coûts.

## 2.3 Break-even réel
Niveau de rendement nécessaire pour couvrir les coûts réellement observés ou raisonnablement attendus.

## 2.4 Edge tracker prudent
Suivi de l’edge net observé avec prudence :
- coûts inclus
- faible fréquence reconnue
- interprétation conservatrice
- pas d’illusion de certitude

## 2.5 Phantom trade
Trade formellement vivant dans la chaîne de décision, mais économiquement trop faible pour être considéré comme un vrai contributeur.

---

# 3. Architecture Build-9

## 3.1 Chaîne de traitement

1. `dtr_core`
2. `cra_monitor`
3. `break_even_dashboard`
4. `edge_tracker_prudent_minimal`

## 3.2 Principe de hiérarchie

- `dtr_core` enregistre les faits
- `cra_monitor` détecte la stérilisation
- `break_even_dashboard` exprime le coût de rentabilité
- `edge_tracker_prudent_minimal` synthétise l’edge net avec prudence

---

# 4. MODULE 1 — DTR_CORE

## 4.1 Nom canonique
`dtr_core`

## 4.2 Mission

Construire un enregistrement minimal, complet et audit-able de chaque décision de trading significative.

## 4.3 Responsabilités exactes

- enregistrer les entrées causales de la décision
- enregistrer le statut de la décision
- distinguer les différents états :
  - non évalué
  - évalué
  - hard-blocked
  - rejeté par ranking
  - sélectionné
  - réduit
  - phantom
  - exécuté
- conserver les éléments nécessaires à un post-mortem quantitatif
- alimenter les autres briques meta

## 4.4 Ce que ce module ne doit pas faire

- être un simple log texte non structuré
- omettre les raisons de refus
- confondre signal candidat et trade exécuté
- perdre silencieusement des DTR
- reconstruire ex post des informations non capturées au moment utile

## 4.5 Sous-composants

### 4.5.1 dtr_record_builder
Rôle :
- construire un DTR complet pour chaque opportunité significative

### 4.5.2 decision_state_encoder
Rôle :
- coder proprement l’état final de la décision

### 4.5.3 cause_chain_assembler
Rôle :
- rassembler score, pénalités, blockers, ranking, allocation, exécution

### 4.5.4 trace_persistence_layer
Rôle :
- persister les DTR sans perte silencieuse

### 4.5.5 dtr_reporter
Rôle :
- exposer les DTR à l’UI, au monitoring et aux audits

## 4.6 Inputs

- signal candidat
- score brut
- score pénalisé
- hard blockers
- verdict de ranking
- allocation finale
- décision d’exécution
- coût attendu
- coût réalisé si exécution
- état portefeuille
- paire
- moteur
- régime
- timestamps utiles

## 4.7 Outputs

- `DTRRecord`
- état final de décision
- code raison principal
- chaîne causale
- événement de persistance du DTR

## 4.8 État interne

- buffer DTR temporaire
- file de persistance
- historique des DTR
- compteurs de pertes / rejets / retards de persistance

## 4.9 Invariants obligatoires

- aucune décision significative ne doit exister sans DTR
- aucun DTR ne doit être persistant “best effort” sans mesure de perte
- chaque DTR doit permettre de distinguer :
  - blocage fatal
  - rejet relatif
  - réduction
  - stérilisation
  - exécution
- les causes doivent être codées explicitement

## 4.10 Exigences de design

- structure stable
- version de schéma
- persistance fiable
- lecture humaine possible
- lecture machine simple
- pas d’ambiguïté entre “pas de signal” et “signal rejeté”

## 4.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `signal_engine`
- `scoring_engine`
- `risk_engine`
- `portfolio_engine`
- `execution_engine`
- `monitoring_engine`

## 4.12 Dépendances interdites

- logique moteur cachée
- reconstruction approximative a posteriori
- persistance silencieuse sans erreur

## 4.13 Logs attendus

- DTR created
- DTR persisted
- DTR persistence delayed
- DTR persistence failed
- decision state encoded
- cause chain attached

## 4.14 Formules et structures utiles

Structure minimale conceptuelle :
\[
DTR_i = (time_i,\ paire_i,\ moteur_i,\ régime_i,\ S_i^{raw},\ Pen_i,\ S_i,\ HB_i,\ Rank_i,\ x_i,\ c_i^{exp},\ c_i^{real},\ state_i)
\]

Taux de couverture DTR :
\[
DTRCoverage = \frac{N_{DTR}}{N_{opportunités\ significatives}}
\]

Taux de perte DTR :
\[
DTRLossRate = \frac{N_{DTR,drops}}{N_{DTR,attempted}}
\]

## 4.15 Tests obligatoires

- DTR créé pour opportunité sélectionnée
- DTR créé pour hard block
- DTR créé pour rejet par ranking
- DTR créé pour trade réduit / phantom
- persistance réussie
- perte de persistance détectée
- causes correctement encodées
- schéma stable

## 4.16 Dérives possibles à ne pas faire

- DTR minimaliste sans score ni cause
- absence de DTR pour les refus
- persistance “fire and forget”
- mélange entre logs humains et DTR machine
- pas de version de schéma

## 4.17 Priorité
P0 absolue

## 4.18 Verdict
**Implémenter maintenant**

---

# 5. MODULE 2 — CRA_MONITOR

## 5.1 Nom canonique
`cra_monitor`

## 5.2 Mission

Détecter quand un trade théoriquement viable a été économiquement vidé de sa substance par :
- réduction de taille
- coût excessif
- durée défavorable
- combinaison de pénalités

## 5.3 Responsabilités exactes

- mesurer le risque de phantom trade
- marquer les trades économiquement stérilisés
- distinguer réduction saine vs réduction stérilisante
- remonter des alertes exploitables
- permettre une lecture par moteur, paire et période

## 5.4 Ce que ce module ne doit pas faire

- se substituer au risk engine
- juger un moteur uniquement sur quelques trades
- traiter toute réduction comme problème
- devenir un simple compteur d’ordres petits

## 5.5 Sous-composants

### 5.5.1 reduction_trace_reader
Rôle :
- lire les réductions issues du scoring / allocation

### 5.5.2 phantom_risk_estimator
Rôle :
- estimer le risque de stérilisation économique

### 5.5.3 sterilization_classifier
Rôle :
- classer un trade comme :
  - sain
  - réduit mais encore viable
  - phantom probable
  - phantom confirmé

### 5.5.4 cra_alert_builder
Rôle :
- produire des alertes par moteur / paire / période

### 5.5.5 cra_reporter
Rôle :
- exposer les résultats au monitoring et à l’UI

## 5.6 Inputs

- DTR
- score pénalisé
- multiplicateur de taille
- taille finale
- coût attendu
- coût réalisé
- durée attendue / durée réalisée
- CE attendue / CE réalisée

## 5.7 Outputs

- indicateur phantom trade
- classification de stérilisation
- CRA alert
- taux de stérilisation par moteur / paire
- raisons dominantes de stérilisation

## 5.8 État interne

- historique des trades réduits
- historique des alertes CRA
- compteurs de stérilisation
- agrégats par moteur / paire / profil

## 5.9 Invariants obligatoires

- toute stérilisation détectée doit être traçable
- un trade réduit n’est pas automatiquement un phantom
- une stérilisation doit être reliée à ses causes
- le monitoring doit distinguer :
  - réduction saine
  - réduction destructrice

## 5.10 Exigences de design

- lisibilité
- seuils explicites
- support d’agrégation
- pas de règle magique opaque
- robustesse aux fills partiels

## 5.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `dtr_core`
- `execution_cost_meter`
- `monitoring_engine`
- `portfolio_engine` via outputs nécessaires

## 5.12 Dépendances interdites

- signal_engine direct
- modification live des moteurs
- logique de scoring active

## 5.13 Logs attendus

- CRA risk detected
- phantom trade flagged
- sterilization classified
- CRA alert emitted
- dominant reduction cause

## 5.14 Formules utiles

Multiplicateur total :
\[
m_i = \prod_{\ell=1}^{L} m_{i,\ell}
\]

Condition phantom conceptuelle :
\[
x_i \cdot \mathbb{E}[r_i] \le c_i^{op} + \epsilon
\]

Capital efficiency :
\[
CE_i = \frac{PnL_i}{x_i \cdot h_i}
\]

Stérilisation :
\[
Steril_i = \mathbf{1}_{A_i=1} \cdot \mathbf{1}_{CE_i < CE_{min}}
\]

Taux de stérilisation :
\[
SterilRate = \frac{\sum_i Steril_i}{\sum_i A_i}
\]

Taux de stérilisation par moteur :
\[
SterilRate_k = \frac{\sum_{i \in k} Steril_i}{\sum_{i \in k} A_i}
\]

## 5.15 Tests obligatoires

- trade sain non signalé
- trade réduit mais encore viable
- trade réduit devenu phantom
- trade avec coût excessif signalé
- agrégation correcte par moteur
- agrégation correcte par paire
- alerte CRA générée

## 5.16 Dérives possibles à ne pas faire

- appeler “phantom” tout petit trade
- oublier la CE et ne regarder que la taille
- ne pas relier la stérilisation à la durée
- ne pas distinguer coût attendu et coût réalisé
- se servir du CRA comme substitut à un vrai diagnostic moteur

## 5.17 Priorité
P0 absolue

## 5.18 Verdict
**Implémenter maintenant**

---

# 6. MODULE 3 — BREAK_EVEN_DASHBOARD

## 6.1 Nom canonique
`break_even_dashboard`

## 6.2 Mission

Rendre visible le coût réel de rentabilité du système par :
- trade
- paire
- moteur
- période

## 6.3 Responsabilités exactes

- calculer et afficher le break-even prudent
- calculer et afficher le break-even observé
- comparer coût attendu et coût réalisé
- fournir une lecture simple de la pression de coût
- permettre de voir si un moteur vit au-dessus ou en dessous de son seuil de viabilité

## 6.4 Ce que ce module ne doit pas faire

- être un dashboard cosmétique
- réduire le coût aux fees
- masquer les percentiles défavorables
- mélanger break-even prudent et résultat net sans distinction

## 6.5 Sous-composants

### 6.5.1 expected_break_even_calculator
Rôle :
- calculer le break-even ex ante

### 6.5.2 realized_break_even_calculator
Rôle :
- calculer le break-even ex post

### 6.5.3 cost_distribution_aggregator
Rôle :
- agréger coûts moyens, p90, p95

### 6.5.4 motor_pair_break_even_view
Rôle :
- vue moteur / paire / période

### 6.5.5 break_even_reporter
Rôle :
- rapport break-even exploitable par UI et monitoring

## 5.6 Inputs

- coût attendu
- coût réalisé
- trade fills
- moteur
- paire
- période
- distributions de coûts

## 6.7 Outputs

- break-even prudent
- break-even réalisé
- coût moyen / p90 / p95
- écarts attendu vs réalisé
- alertes de dérive coût

## 6.8 État interne

- agrégats par moteur
- agrégats par paire
- historiques journaliers
- distributions de coûts

## 6.9 Invariants obligatoires

- break-even affiché distinctement ex ante / ex post
- coût par moteur et par paire visible
- les percentiles défavorables doivent être visibles
- les dérives de coût doivent être traçables

## 6.10 Exigences de design

- simple
- lisible
- orienté décision économique
- compatible UI / monitoring
- non trompeur

## 6.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `execution_cost_meter`
- `fill_tracker`
- `monitoring_engine`
- `ui_console`

## 6.12 Dépendances interdites

- logique moteur active
- décision de signal
- modification des coûts en runtime

## 6.13 Logs attendus

- break-even expected updated
- break-even realized updated
- cost percentile updated
- expected vs realized cost drift
- break-even alert

## 6.14 Formules utiles

Break-even simple :
\[
g_i^{BE} = c_i
\]

Break-even prudent :
\[
g_i^{BE,cons} = f_i + s_i^{p90} + q_i^{p90} + a_i^{p90}
\]

Break-even moteur / paire :
\[
BE_{k,j} = \mathbb{E}[c \mid moteur=k, paire=j]
\]

Écart coût réalisé vs attendu :
\[
CostDrift_i = c_i^{real} - c_i^{exp}
\]

## 6.15 Tests obligatoires

- calcul break-even simple
- calcul break-even prudent
- agrégation moteur
- agrégation paire
- p90 visible
- dérive coût attendue/réalisée détectée
- rapport UI exploitable

## 6.16 Dérives possibles à ne pas faire

- ne montrer que le coût moyen
- oublier les p90/p95
- afficher un break-even global qui masque les moteurs
- déconnecter ce dashboard du coût réel d’exécution

## 6.17 Priorité
P0 absolue

## 6.18 Verdict
**Implémenter maintenant**

---

# 7. MODULE 4 — EDGE_TRACKER_PRUDENT_MINIMAL

## 7.1 Nom canonique
`edge_tracker_prudent_minimal`

## 7.2 Mission

Fournir un suivi minimal mais prudent de l’edge net observé, par moteur et par paire, sans prétendre à une certitude statistique excessive.

## 7.3 Responsabilités exactes

- agréger les rendements nets observés
- distinguer edge brut et edge net
- produire une lecture prudente de l’edge par moteur / paire / période
- signaler la dérive possible sans sur-réagir
- fournir des signaux de gouvernance, pas des oracles

## 7.4 Ce que ce module ne doit pas faire

- piloter seul les activations live
- traiter quelques observations comme preuve définitive
- ignorer la faible fréquence et la variance
- prétendre à une inférence académique complète en Light
- devenir un mini moteur bayésien sur-complexe

## 7.5 Sous-composants

### 7.5.1 return_aggregator
Rôle :
- agréger les rendements nets observés

### 7.5.2 sample_size_tracker
Rôle :
- suivre le nombre d’observations utiles

### 7.5.3 uncertainty_estimator
Rôle :
- estimer une incertitude prudente

### 7.5.4 edge_status_classifier
Rôle :
- classifier :
  - insuffisant
  - crédible
  - sous surveillance
  - dégradé

### 7.5.5 edge_reporter
Rôle :
- exposer les résultats à l’UI, monitoring et gouvernance

## 7.6 Inputs

- rendements nets réalisés
- coût réalisé
- moteur
- paire
- période
- fréquence utile
- CE observée
- taille d’échantillon

## 7.7 Outputs

- edge net moyen observé
- dispersion observée
- niveau de confiance prudent
- statut moteur / paire
- alerte de dérive éventuelle

## 7.8 État interne

- agrégats par moteur
- agrégats par paire
- agrégats par moteur/paire
- taille d’échantillon
- historique des statuts edge

## 7.9 Invariants obligatoires

- l’edge suivi doit être net de coûts
- la taille d’échantillon doit être visible
- l’incertitude doit être visible
- le statut doit être prudent
- un edge peu observé ne doit pas être sur-interprété

## 7.10 Exigences de design

- conservateur
- simple
- lisible
- utile à la gouvernance
- non dogmatique

## 7.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `execution_cost_meter`
- `monitoring_engine`
- `break_even_dashboard`
- `dtr_core`

## 7.12 Dépendances interdites

- activation live directe
- modifications moteur automatiques
- politique RL / POMDP
- sophistication bayésienne non minimale

## 7.13 Logs attendus

- edge estimate updated
- sample size updated
- uncertainty updated
- edge status changed
- drift warning emitted

## 7.14 Formules utiles

Rendement net par trade :
\[
r_i = g_i - c_i
\]

Espérance observée :
\[
\hat{\mu} = \frac{1}{N}\sum_{i=1}^{N} r_i
\]

Variance observée :
\[
\hat{\sigma}^2 = \frac{1}{N-1}\sum_{i=1}^{N}(r_i-\hat{\mu})^2
\]

Erreur standard :
\[
SE(\hat{\mu}) = \frac{\hat{\sigma}}{\sqrt{N}}
\]

Sharpe par trade observé :
\[
Sh = \frac{\hat{\mu}}{\hat{\sigma}}
\]

Capital efficiency observée :
\[
CE = \frac{\sum_i PnL_i}{\sum_i x_i h_i}
\]

## 7.15 Règle de prudence

Ne jamais conclure “moteur validé” à partir de \(\hat{\mu} > 0\) seul.

La lecture minimale doit inclure :
- \(\hat{\mu}\)
- \(N\)
- \(SE(\hat{\mu})\)
- coût moyen / p90
- CE
- contexte portefeuille

## 7.16 Statuts recommandés

### insuffisant
- trop peu de données

### crédible
- edge net positif + coûts stables + CE correcte + échantillon raisonnable

### sous surveillance
- edge encore positif mais fragile ou bruité

### dégradé
- edge net négatif ou coût devenu destructeur

## 7.17 Tests obligatoires

- agrégation simple de rendements
- échantillon faible correctement marqué
- edge positif mais incertain marqué prudemment
- edge dégradé signalé
- séparation moteur
- séparation paire
- séparation moteur/paire

## 7.18 Dérives possibles à ne pas faire

- appeler “alpha” un échantillon de quelques trades
- utiliser une moyenne brute sans coûts
- ignorer la variance
- réagir trop vite à une courte séquence
- considérer ce module comme oracle de promotion

## 7.19 Priorité
P0 absolue

## 7.20 Verdict
**Implémenter maintenant**

---

# 8. Interfaces entre modules Build-9

## 8.1 modules amont → dtr_core
- score
- pénalités
- blockers
- ranking
- allocation
- exécution
- coûts

## 8.2 dtr_core → cra_monitor
- DTR complets
- taille finale
- score pénalisé
- coût attendu / réalisé
- état final

## 8.3 execution_cost_meter → break_even_dashboard
- coûts attendus / réalisés
- distributions par moteur / paire

## 8.4 dtr_core + execution_cost_meter → edge_tracker_prudent_minimal
- rendements nets
- moteurs
- paires
- tailles d’échantillon
- coûts

## 8.5 Build-9 → UI / monitoring
- DTR visibles
- CRA alerts
- break-even visible
- edge status visible

---

# 9. Ordre précis d’implémentation Build-9

## Étape 1
`dtr_core`

Pourquoi :
- sans trace des décisions, le reste repose sur du vide

## Étape 2
`cra_monitor`

Pourquoi :
- la stérilisation économique doit être détectée tôt

## Étape 3
`break_even_dashboard`

Pourquoi :
- il faut rendre visible le coût de rentabilité

## Étape 4
`edge_tracker_prudent_minimal`

Pourquoi :
- l’edge doit être suivi après avoir sécurisé décision, stérilisation et break-even

---

# 10. Table synthétique Build-9

| Module | Ordre | Priorité | Gate critique | Sortie attendue |
|---|---:|---:|---|---|
| dtr_core | 1 | P0 | décisions traçables | causalité exploitable |
| cra_monitor | 2 | P0 | stérilisation visible | phantom trades détectés |
| break_even_dashboard | 3 | P0 | coût de rentabilité visible | seuil économique lisible |
| edge_tracker_prudent_minimal | 4 | P0 | edge net prudent | gouvernance économique minimale |

---

# 11. Conditions de sortie de Build-9

Build-9 est terminé si :

- chaque décision significative a un DTR
- les phantom trades peuvent être détectés
- le break-even réel est visible par moteur et par paire
- l’edge net observé est suivi avec prudence
- l’UI et le monitoring peuvent afficher ces informations
- les modules précédents deviennent auditables ex post

---

# 12. Critères de refus de sortie

Refuser Build-9 si :

- `dtr_core` ne couvre pas les refus
- `cra_monitor` ne distingue pas réduction saine et stérilisation
- `break_even_dashboard` ne montre que les coûts moyens
- `edge_tracker_prudent_minimal` ignore la taille d’échantillon
- le système ne peut toujours pas expliquer pourquoi il a réellement tradé ou non

---

# 13. Dérives globales Build-9 à ne pas faire

- croire que le PnL brut suffit comme observabilité
- réduire les DTR à un log texte
- appeler “phantom trade” tout petit trade
- confondre break-even prudent et profit réalisé
- traiter l’edge tracker comme une preuve académique complète
- oublier que cette couche doit aider à gouverner, pas à impressionner

---

# 14. Verdict final Build-9

Build-9 est la couche qui transforme la V5.3 Light en système **pilotable rationnellement**.

Si Build-9 est bien fait :
- les décisions sont explicables
- la stérilisation est visible
- le coût de rentabilité est concret
- l’edge net est surveillé sans illusion

Si Build-9 est mal fait :
- la Light sera conduite au ressenti
- les moteurs seront jugés injustement
- les coûts seront mal reliés à la rentabilité
- la production deviendra opaque

Donc :

> Build-9 doit être traité comme un **build bloquant d’intelligence d’observabilité économique**, pas comme une couche analytics secondaire.

---

# Guardrails issus des audits — Renforcements Build-9

## Distinction entre méta utile et méta vide
- Le méta-engine doit produire des diagnostics basés sur de vrais chemins de décision et d'exécution
- Un DTR qui n'est pas alimenté par des trades réels (ou shadow réels) est un DTR vide
- Un edge_tracker qui s'auto-alimente sur des séries synthétiques est un piège d'auto-référence

## Exigence que DTR / edge / break-even soient alimentés par vrais chemins
- Le `dtr_core` doit tracer le chemin complet : data → engine → scoring → portfolio → execution
- Si un maillon du chemin est manquant ou mocké, le DTR doit le signaler explicitement
- Le `break_even_dashboard` doit utiliser les coûts réels mesurés, pas des estimations décoratives

## Garde contre auto-référence sur séries synthétiques
- Le `edge_tracker_prudent` ne doit pas calculer un edge sur des données générées par le système lui-même
- L'edge doit être mesuré sur des données de marché réelles (historiques ou live)
- En `LOCAL_REPLAY`, l'edge est indicatif et ne constitue pas une validation prod
- Le `amd_monitor` (Asset Model Drift) doit signaler si les inputs sont synthétiques

## Persistance DTR obligatoire (QWEN-01)
- Les records DTR doivent être persistés périodiquement vers fichier
- La perte totale du DTR au redémarrage n'est pas acceptable
- Pattern minimal : flush JSON périodique + rotation de fichiers

---

## Fin du document
