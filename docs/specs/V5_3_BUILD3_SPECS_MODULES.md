# V5.3 — BUILD-3 SPECS MODULES
## Execution Backbone Pack
### Specs détaillées module par module
### Troisième étape officielle du développement
### Sans code — prod-safe

---

# 0. Objet du document

Ce document couvre **Build-3** du plan officiel V5.3.

Build-3 a une mission unique :

> transformer une décision autorisée en exécution réelle, mesurable, réconciliable et économiquement interprétable.

Les modules couverts ici sont :

1. `order_decider`
2. `fill_tracker`
3. `execution_cost_meter`
4. `reconciliation_layer`

Aucun passage sérieux en shadow avancé, micro-live ou live ne doit être envisagé tant que ces quatre briques ne sont pas correctement spécifiées, testées et gelées.

---

# 1. Principes Build-3

## 1.1 Objectif stratégique

Build-3 ne cherche pas encore à optimiser le PnL.  
Il cherche à empêcher le scénario classique :

> un système semble bon en logique de signal, mais son edge est détruit par les coûts d’exécution, la latence, les partial fills, les annulations mal gérées ou l’état local faux.

Build-3 doit fournir :

- une décision d’ordre explicable
- un suivi précis des fills
- une mesure du coût réel
- une réconciliation fiable entre état local et état réel

## 1.2 Critère de réussite

Build-3 est réussi si :

- chaque ordre a une intention claire
- chaque fill est traçable
- le coût réalisé est mesuré
- l’état portefeuille local peut être réconcilié avec l’état exchange
- les écarts sont détectés et explicités
- aucun ordre ne peut “disparaître” silencieusement

## 1.3 Critère d’échec

Build-3 échoue si :

- le système ne peut pas dire pourquoi il a choisi market / limit / no-trade
- les partial fills sont mal suivis
- le coût réel n’est pas calculé
- l’état local diverge du compte réel
- les annulations / expirations ne sont pas correctement reflétées
- les métriques d’exécution sont trop pauvres pour un audit post-mortem

---

# 2. Vocabulaire officiel Build-3

## 2.1 Intention d’exécution
Décision pré-ordre décrivant :
- pourquoi on veut exécuter
- sur quelle paire
- dans quel sens
- à quelle taille
- avec quel type d’ordre autorisé
- sous quelles contraintes de coût

## 2.2 Fill
Événement d’exécution partielle ou complète d’un ordre.

## 2.3 Coût réel
Coût total effectivement payé par un trade :

- frais explicites
- slippage
- adverse selection
- partial fill cost
- coût d’annulation / re-entrée
- coût lié à la latence

## 2.4 Réconciliation
Processus qui compare :
- ordres connus localement
- fills connus localement
- positions locales
- état exchange réel

et produit :
- état aligné
- ou divergence explicite

---

# 3. Architecture Build-3

## 3.1 Chaîne de traitement

1. `order_decider`
2. `fill_tracker`
3. `execution_cost_meter`
4. `reconciliation_layer`

## 3.2 Principes de hiérarchie

- l’exécution dépend du scoring et du risk déjà validés, mais ne leur appartient pas
- la mesure du coût ne doit jamais être mélangée à la logique de signal
- la réconciliation est une vérité de sécurité, pas une option

---

# 4. MODULE 1 — ORDER_DECIDER

## 4.1 Nom canonique
`order_decider`

## 4.2 Mission

Décider si une opportunité autorisée doit être :
- exécutée en market
- exécutée en limit
- rejetée comme no-trade
- ou différée si les contraintes d’exécution ne sont pas satisfaites

## 4.3 Responsabilités exactes

- recevoir une intention d’exécution issue du pipeline métier
- vérifier le coût ex ante attendu
- vérifier les contraintes d’exécution
- choisir le mode d’ordre autorisé
- produire un `ExecutionIntent` explicite
- refuser explicitement un trade si l’exécution détruit l’edge attendu

## 4.4 Ce que ce module ne doit pas faire

- recalculer le signal métier
- contourner le risk engine
- exécuter “parce que le signal existe”
- supposer que market est toujours acceptable
- masquer un no-trade sous une pseudo exécution

## 4.5 Sous-composants

### 4.5.1 intent_builder
Rôle :
- construire l’intention d’ordre à partir du signal validé

### 4.5.2 order_type_selector
Rôle :
- choisir market / limit / no-trade selon coût et contexte

### 4.5.3 execution_guard
Rôle :
- refuser si coût, santé paire ou état infra rendent l’exécution non crédible

### 4.5.4 timeout_policy_selector
Rôle :
- définir les règles de temps de vie d’un ordre

### 4.5.5 decision_reporter
Rôle :
- produire un rapport de décision exécutable

## 4.6 Inputs

- `SignalCandidate` validé
- score final
- taille validée
- coût attendu
- pair health
- état infra
- budget risque déjà autorisé
- mode profil Light / Complete

## 4.7 Outputs

- `ExecutionIntent`
- type d’ordre recommandé
- no-trade explicite si refus
- raisons de refus
- politique timeout / cancel

## 4.8 État interne

- derniers intents
- paramètres d’ordre par profil
- compteurs no-trade exécution
- historique des refus liés au coût

## 4.9 Invariants obligatoires

- chaque ordre a une justification
- chaque no-trade a une justification
- aucun ordre ne part sans coût ex ante estimé
- aucun ordre ne contourne les hard blockers
- tout type d’ordre choisi doit être explicable ex post

## 4.10 Exigences de design

- séparé du moteur de signal
- séparé du module qui mesure le coût réalisé
- logique de refus explicite
- pas de types d’ordre exotiques inutiles
- comportement borné et stable

## 4.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `risk_engine` via interface
- `data_quality_engine` via interface
- `portfolio_engine` via interface si nécessaire
- `execution_cost_meter` uniquement pour historique / calibration ex ante

## 4.12 Dépendances interdites

- import direct des moteurs
- recalcul de score métier
- logique de portfolio cachée
- modification des caps risque

## 4.13 Logs attendus

- intent created
- order type chosen
- no-trade reason
- expected cost
- expected break-even
- timeout policy chosen
- profile at decision time

## 4.14 Métriques mathématiques utiles

Condition d’exécution minimale :

\[
\mathbb{E}[g_i \mid \mathcal{F}_i] > \mathbb{E}[c_i \mid \mathcal{F}_i] + \delta_{safe}
\]

Break-even prudent :

\[
g_i^{BE,cons} = f_i + s_i^{p90} + q_i^{p90} + a_i^{p90}
\]

Valeur nette attendue :

\[
EV_i^{net} = x_i \cdot \left(\mathbb{E}[g_i] - \mathbb{E}[c_i]\right)
\]

No-trade si :

\[
EV_i^{net} \le \epsilon
\]

## 4.15 Tests obligatoires

- market choisi quand attendu
- limit choisi quand attendu
- no-trade explicite si coût trop élevé
- refus si pair health dégradée
- refus si état infra dégradé
- timeout policy assignée
- logs de décision présents

## 4.16 Dérives possibles à ne pas faire

- exécuter “par défaut” en market
- laisser market/limit dépendre de heuristiques opaques
- ne pas mesurer la part de no-trade due au coût
- injecter du métier signal ici
- faire un module “intelligent” non audit-able

## 4.17 Priorité
P0 absolue

## 4.18 Verdict
**Implémenter maintenant**

---

# 5. MODULE 2 — FILL_TRACKER

## 5.1 Nom canonique
`fill_tracker`

## 5.2 Mission

Suivre de manière exhaustive l’état des ordres et des fills :
- order sent
- ack
- partial fill
- fill complet
- cancel
- expire
- reject

## 5.3 Responsabilités exactes

- enregistrer le cycle de vie d’un ordre
- agréger les fills partiels
- relier les fills à l’ordre source
- mesurer les temps de réponse
- alimenter le coût réel
- alimenter la réconciliation

## 5.4 Ce que ce module ne doit pas faire

- recalculer le signal
- décider de nouvelles entrées
- masquer les partial fills
- écraser un état d’ordre ambigu
- supposer qu’un ordre acké est un ordre exécuté

## 5.5 Sous-composants

### 5.5.1 order_state_tracker
Rôle :
- maintenir l’état order lifecycle

### 5.5.2 fill_aggregator
Rôle :
- agréger plusieurs fills d’un même ordre

### 5.5.3 latency_meter
Rôle :
- mesurer :
  - order submit latency
  - ack latency
  - first fill latency
  - full fill latency

### 5.5.4 order_terminal_state_resolver
Rôle :
- définir :
  - filled
  - partially_filled_cancelled
  - cancelled
  - expired
  - rejected

### 5.5.5 fill_reporter
Rôle :
- rapport de suivi des ordres

## 5.6 Inputs

- `ExecutionIntent`
- réponses d’ordre exchange
- événements fills
- événements cancel / reject / expire

## 5.7 Outputs

- état d’ordre à jour
- état de fill agrégé
- métriques de latence
- historique d’ordre
- événement terminal

## 5.8 État interne

- table des ordres actifs
- table des fills partiels
- statut terminal par ordre
- horodatages clés
- mapping order → trade / pair / moteur

## 5.9 Invariants obligatoires

- un ordre ne peut pas exister sans état courant
- un ordre acké n’est pas automatiquement rempli
- tous les fills doivent être reliés à un ordre
- l’état terminal doit être explicite
- les partial fills ne doivent jamais être ignorés

## 5.10 Exigences de design

- idempotence sur événements répétés
- résilience aux messages dupliqués
- support du désordre partiel d’événements
- granularité suffisante pour audit post-mortem

## 5.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `order_decider`
- `reconciliation_layer` logique en sortie
- `execution_cost_meter`

## 5.12 Dépendances interdites

- moteurs
- scoring
- risk business
- logique de portefeuille cachée

## 5.13 Logs attendus

- order submitted
- order acked
- partial fill
- full fill
- cancel request
- order cancelled
- order rejected
- order expired
- latency metrics
- terminal state

## 5.14 Métriques mathématiques utiles

Taux de partial fill :
\[
PFR = \frac{N_{partial}}{N_{orders}}
\]

Taux de rejet :
\[
RejectRate = \frac{N_{reject}}{N_{orders}}
\]

Latence ACK moyenne :
\[
AckLat = \frac{1}{N}\sum_i (t^{ack}_i - t^{send}_i)
\]

Latence premier fill :
\[
FirstFillLat = \frac{1}{N}\sum_i (t^{firstfill}_i - t^{send}_i)
\]

Taux de remplissage complet :
\[
FullFillRate = \frac{N_{full}}{N_{orders}}
\]

## 5.15 Tests obligatoires

- ack simple
- partial fill unique
- multi partial fills
- cancel avant fill
- cancel après partial fill
- reject
- expire
- messages dupliqués
- ordre des événements désordonné
- terminal state correct

## 5.16 Dérives possibles à ne pas faire

- considérer qu’un ordre envoyé = position ouverte
- perdre l’information partielle
- écraser des états intermédiaires utiles
- ne pas horodater les transitions
- ne pas lier fills et moteur / paire

## 5.17 Priorité
P0 absolue

## 5.18 Verdict
**Implémenter maintenant**

---

# 6. MODULE 3 — EXECUTION_COST_METER

## 6.1 Nom canonique
`execution_cost_meter`

## 6.2 Mission

Mesurer le coût réel payé à l’exécution pour chaque ordre, fill, trade, paire et moteur.

## 6.3 Responsabilités exactes

- calculer les frais explicites
- calculer les coûts implicites de traversée
- mesurer adverse selection ex post
- intégrer le coût des partial fills
- agréger les coûts par moteur / paire / période
- comparer coût attendu vs coût réalisé

## 6.4 Ce que ce module ne doit pas faire

- décider du signal
- choisir seul le type d’ordre
- masquer les coûts ex post
- réduire le coût à des fees moyens
- mélanger coût brut et edge net

## 6.5 Sous-composants

### 6.5.1 fee_meter
Rôle :
- calculer les frais explicites exacts

### 6.5.2 elw_meter
Rôle :
- mesurer l’Effective Liquidity Width

### 6.5.3 adverse_selection_meter
Rôle :
- mesurer le mouvement défavorable post-fill

### 6.5.4 partial_fill_cost_meter
Rôle :
- mesurer coût additionnel des fills fragmentés

### 6.5.5 cost_aggregator
Rôle :
- agréger coût par trade / paire / moteur

## 6.6 Inputs

- fills agrégés
- mid price au moment du fill
- bid/ask au moment du fill
- horodatages fills
- éventuels états post-fill nécessaires

## 6.7 Outputs

- coût explicite
- coût implicite
- coût total par trade
- coût moyen / p90
- break-even réalisé
- comparaison attendu / réalisé

## 6.8 État interne

- historiques de coûts
- historiques par moteur
- historiques par paire
- distribution des coûts
- agrégats journaliers

## 6.9 Invariants obligatoires

- tout trade a un coût total mesurable
- coût explicite et implicite distingués
- coût par moteur et par paire disponibles
- coût attendu vs coût réalisé comparables
- aucune exécution ne doit être “gratuite” par défaut

## 6.10 Exigences de design

- granularité fine
- agrégation simple
- auditabilité
- robustesse aux fills partiels
- support du p90/p95

## 6.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `fill_tracker`
- données de marché nécessaires pour mid / bid / ask
- `meta_engine` comme consommateur logique

## 6.12 Dépendances interdites

- logique de signal
- logique de scoring métier
- modifications d’ordres live

## 6.13 Logs attendus

- fee measured
- ELW measured
- adverse selection measured
- total cost computed
- cost expected vs realized
- p90 drift alert

## 6.14 Métriques mathématiques utiles

Frais explicites :
\[
f_i
\]

Effective Liquidity Width :
\[
ELW_i = \frac{|P_i^{exec} - Mid_i|}{Mid_i}
\]

Coût implicite round-trip approximatif :
\[
c_i^{impl} \approx ELW_i^{entry} + ELW_i^{exit}
\]

Adverse selection :
\[
AS_i(\Delta)=\operatorname{sign}(side)\cdot \frac{Mid_{t+\Delta} - P_i^{exec}}{P_i^{exec}}
\]

Coût total :
\[
c_i = f_i + c_i^{impl} + AS_i + PF_i
\]

Break-even empirique par moteur / paire :
\[
BE_{k,j} = \mathbb{E}[c \mid moteur=k, paire=j]
\]

## 6.15 Tests obligatoires

- calcul frais simple
- ELW achat
- ELW vente
- coût agrégé entrée/sortie
- adverse selection calculée
- partial fill cost intégré
- agrégation par moteur
- agrégation par paire
- comparaison attendu/réalisé

## 6.16 Dérives possibles à ne pas faire

- limiter le coût aux fees
- ne pas distinguer coût par moteur
- regarder le coût moyen sans p90
- ignorer adverse selection
- masquer les coûts très mauvais en les lissant trop fort

## 6.17 Priorité
P0 absolue

## 6.18 Verdict
**Implémenter maintenant**

---

# 7. MODULE 4 — RECONCILIATION_LAYER

## 7.1 Nom canonique
`reconciliation_layer`

## 7.2 Mission

Garantir que l’état local du système reste aligné avec l’état réel de l’exchange.

## 7.3 Responsabilités exactes

- comparer ordres locaux vs ordres réels
- comparer fills locaux vs fills réels
- comparer positions locales vs positions réelles
- comparer inventaire / solde local vs réel
- détecter les divergences
- produire un verdict de cohérence
- initier des procédures de recovery contrôlé

## 7.4 Ce que ce module ne doit pas faire

- corriger silencieusement l’état
- ignorer une divergence “mineure”
- décider seul d’un nouveau trade
- réécrire les historiques
- devenir un sac de hacks runtime

## 7.5 Sous-composants

### 7.5.1 order_reconciler
Rôle :
- comparer ordres locaux et réels

### 7.5.2 fill_reconciler
Rôle :
- comparer fills locaux et réels

### 7.5.3 position_reconciler
Rôle :
- comparer positions / inventaires

### 7.5.4 divergence_classifier
Rôle :
- classer divergence :
  - warning
  - blocking
  - critical

### 7.5.5 recovery_trigger
Rôle :
- déclencher une procédure de re-sync contrôlée si nécessaire

## 7.6 Inputs

- état local ordres/fills/positions
- état réel exchange (poll contrôlé ou feed dédié)
- configuration de tolérances
- pair health / infra context

## 7.7 Outputs

- verdict de réconciliation
- liste de divergences
- criticité
- besoin de recovery
- état local validé ou non

## 7.8 État interne

- dernier état local
- dernier état remote
- historique divergences
- dernière recovery
- compteurs par type de divergence

## 7.9 Invariants obligatoires

- aucune divergence critique ne doit être silencieuse
- un écart de position doit être classé
- le système doit savoir s’il est aligné ou non
- l’absence de réconciliation récente doit être visible

## 7.10 Exigences de design

- robuste
- explicite
- conservateur
- compatible avec recovery contrôlé
- jamais silencieux

## 7.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `fill_tracker`
- `rest_bootstrap` ou équivalent recovery read-only
- `data_quality_engine` / `monitoring_engine` en logique

## 7.12 Dépendances interdites

- moteur métier
- scoring
- modifications cachées du signal

## 7.13 Logs attendus

- reconciliation started
- reconciliation success
- divergence found
- divergence severity
- recovery triggered
- recovery resolved / failed

## 7.14 Métriques mathématiques utiles

Écart position :
\[
PosDiff = |Pos_{local} - Pos_{remote}|
\]

Écart ordre :
\[
OrderDiff = N_{local,open} - N_{remote,open}
\]

Taux de divergence :
\[
DivRate = \frac{N_{divergences}}{N_{reconciliations}}
\]

Âge de dernière réconciliation :
\[
\Delta_{recon} = t_{now} - t_{last\ recon}
\]

## 7.15 Tests obligatoires

- ordre local conforme
- ordre manquant côté remote
- fill manquant localement
- divergence de position
- divergence critique
- recovery déclenché
- recovery résolu
- divergence journalisée

## 7.16 Dérives possibles à ne pas faire

- considérer que “tout a l’air bon”
- corriger localement sans trace
- ne pas classer la sévérité
- faire dépendre la réconciliation d’un humain implicite
- réconciliation trop rare

## 7.17 Priorité
P0 absolue

## 7.18 Verdict
**Implémenter maintenant**

---

# 8. Interfaces entre modules Build-3

## 8.1 order_decider → fill_tracker
- `ExecutionIntent`
- order_id source
- contexte moteur / paire / trade

## 8.2 fill_tracker → execution_cost_meter
- fills agrégés
- horodatages fills
- état final ordre

## 8.3 fill_tracker → reconciliation_layer
- état local des ordres
- état local des fills
- état local des positions dérivées

## 8.4 execution_cost_meter → meta_engine / monitoring
- coût par trade
- coût par paire
- coût par moteur
- coût attendu vs réalisé

## 8.5 reconciliation_layer → monitoring / UI / ops
- verdict aligné / non aligné
- sévérité
- recovery demandé

---

# 9. Ordre précis d’implémentation Build-3

## Étape 1
`order_decider`

Pourquoi :
- il faut une intention propre avant de suivre des fills

## Étape 2
`fill_tracker`

Pourquoi :
- sans cycle de vie d’ordre fiable, le reste est faux

## Étape 3
`execution_cost_meter`

Pourquoi :
- le coût réel doit être mesuré dès que les fills existent

## Étape 4
`reconciliation_layer`

Pourquoi :
- la vérité ultime est l’alignement état local / état réel

---

# 10. Table synthétique Build-3

| Module | Ordre | Priorité | Gate critique | Sortie attendue |
|---|---:|---:|---|---|
| order_decider | 1 | P0 | intention explicite | décision d’ordre justifiée |
| fill_tracker | 2 | P0 | cycle de vie ordre fiable | fills traçables |
| execution_cost_meter | 3 | P0 | coût réel mesuré | edge net audit-able |
| reconciliation_layer | 4 | P0 | état aligné | portefeuille fiable |

---

# 11. Conditions de sortie de Build-3

Build-3 est terminé si :

- chaque ordre a un intent explicite
- chaque fill est suivi proprement
- chaque trade a un coût total calculable
- chaque divergence locale / réelle est détectable
- les logs d’exécution sont suffisants pour un audit post-mortem
- la réconciliation peut déclencher un recovery explicite

---

# 12. Critères de refus de sortie

Refuser Build-3 si :

- `order_decider` n’explique pas market / limit / no-trade
- `fill_tracker` ne gère pas correctement les partial fills
- `execution_cost_meter` ne calcule pas le coût réel total
- `reconciliation_layer` ne signale pas les divergences critiques
- un ordre ou fill peut se perdre silencieusement

---

# 13. Dérives globales Build-3 à ne pas faire

- commencer à juger les moteurs avant d’avoir les vrais coûts
- regarder le PnL brut sans coût réel
- considérer l’état local comme source de vérité
- réduire la réconciliation à une vérification occasionnelle
- mélanger logique d’exécution et logique de signal

---

# 14. Verdict final Build-3

Build-3 est la couche qui détermine si l’edge du système survivra à la réalité.

Sans Build-3 bien fait :
- les coûts réels seront invisibles
- les moteurs seront évalués de travers
- les positions pourront diverger silencieusement
- la prod deviendra dangereuse

Donc :

> Build-3 doit être traité comme un **build bloquant économique et de sécurité**, pas comme une simple couche ordre/fill.

---

# Guardrails issus des audits — Renforcements Build-3

## Coût réel prudent (GEM-07)
- Le `execution_cost_meter` ne doit pas se limiter au slippage
- Coût réel = slippage + market impact estimé + exchange fees
- Le market impact doit être modélisé de manière prudente (surestimer plutôt que sous-estimer)
- Pour les petites tailles initiales (Light), l'impact est faible mais le principe doit être documenté

## Market impact prudent minimal (GEM-07)
- Même si le système Light opère avec de petites tailles, le cost model doit inclure une composante d'impact
- Formule minimale : `impact_estimate = size * impact_coefficient * spread_bps`
- Le coefficient doit être calibrable et conservateur par défaut

## No-trade explicite (GEM-07b)
- Si le coût estimé total (slippage + impact + fees) dépasse l'edge net attendu, le trade est rejeté
- Ce rejet doit être loggé dans le DTR avec raison `COST_EXCEEDS_EDGE`
- Le `order_decider` doit intégrer ce filtre avant émission

## Latence plausible / monotone (GEM-08)
- Les mesures de latence d'exécution doivent utiliser un clock monotone
- Les valeurs aberrantes doivent être filtrées
- La latence d'exécution ne doit pas corrompre les statistiques moyennes

## Réconciliation à source externe (GEM-07c, QWEN-03)
- La `reconciliation_layer` doit être conçue pour accepter une source externe (état exchange réel)
- En trajectoire prod (Build-12+), la réconciliation exchange devient obligatoire
- En Build-3, un chemin runtime branché sur un adapter externe doit déjà exister et être testé de bout en bout
- Clarification : protocole ≠ runtime réel si non branché sur un adapter exchange
- Donc : Build-3 n'est pas validé si seule la surface contractuelle existe sans exécution réelle, suivi de fills, coût calculé et réconciliation branchée

---

## Fin du document
