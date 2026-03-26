# V5.3 — BUILD-5 SPECS MODULES
## Scoring Backbone Pack
### Specs détaillées module par module
### Cinquième étape officielle du développement
### Sans code — prod-safe

---

# 0. Objet du document

Ce document couvre **Build-5** du plan officiel V5.3.

Build-5 a une mission unique :

> transformer des signaux candidats en décisions auditables, graduelles et économiquement cohérentes, sans recréer le sur-filtrage destructeur de la V5.2.

Les modules couverts ici sont :

1. `raw_score_builder`
2. `penalty_aggregator`
3. `hard_block_gate`
4. `ranking_router`

Aucun moteur ne doit être considéré utilisable en shadow avancé, micro-live ou live tant que ces quatre briques ne sont pas correctement spécifiées, testées et gelées.

---

# 1. Principes Build-5

## 1.1 Objectif stratégique

Build-5 n’a pas pour mission de “rendre le système intelligent”.  
Il doit rendre le système :

- lisible
- reproductible
- économiquement cohérent
- compatible avec les coûts
- compatible avec les budgets de risque
- résistant à la tentation du veto excessif

## 1.2 Problème historique à corriger

Dans une architecture trop complexe, on dérive facilement vers :

- trop de filtres binaires
- trop d’exceptions implicites
- trop de scores opaques
- trop de signaux “valides” qui deviennent des phantom trades
- un ranking qui ignore portefeuille et coût réel

Build-5 existe pour l’empêcher.

## 1.3 Critère de réussite

Build-5 est réussi si :

- le score brut est explicable
- les pénalités sont graduelles et non binaires
- les hard blockers restent rares et fatals
- le ranking tient compte de la logique portefeuille
- chaque décision peut être reproduite ex post
- le système distingue clairement :
  - trade refusé
  - trade pénalisé
  - trade classé plus bas
  - trade phantom

## 1.4 Critère d’échec

Build-5 échoue si :

- les soft penalties redeviennent des veto cachés
- le score brut est impossible à expliquer
- les hard blockers couvrent la moitié des cas métier
- le ranking sélectionne le plus gros score sans coût ni risque
- les décisions ne sont pas reproductibles
- l’ordre de priorité entre opportunités reste arbitraire

---

# 2. Vocabulaire officiel Build-5

## 2.1 Score brut
Évaluation initiale d’une opportunité avant prudence et contraintes.

## 2.2 Pénalité
Réduction graduelle du score ou de la taille, sans blocage fatal.

## 2.3 Hard blocker
Condition fatale qui interdit toute exécution.

## 2.4 Ranking
Sélection relative entre plusieurs opportunités valides.

## 2.5 Phantom trade
Trade formellement valide, mais économiquement non monétisable.

---

# 3. Architecture Build-5

## 3.1 Chaîne de traitement

1. `raw_score_builder`
2. `penalty_aggregator`
3. `hard_block_gate`
4. `ranking_router`

## 3.2 Principe de hiérarchie

- le score brut exprime la qualité du signal
- les pénalités expriment la prudence graduelle
- les hard blockers expriment les interdictions fatales
- le ranking arbitre les opportunités survivantes dans un cadre portefeuille

---

# 4. MODULE 1 — RAW_SCORE_BUILDER

## 4.1 Nom canonique
`raw_score_builder`

## 4.2 Mission

Construire un score brut lisible, stable et exploitable à partir des informations pertinentes du signal candidat.

## 4.3 Responsabilités exactes

- recevoir les features du signal candidat
- calculer un score brut cohérent avec le moteur
- préserver l’interprétabilité minimale
- séparer les composantes du score
- produire un `ScorePayload` explicite

## 4.4 Ce que ce module ne doit pas faire

- intégrer des hard blockers
- mélanger les pénalités dans le score brut
- recalculer le risque
- masquer la composition du score
- utiliser des coefficients arbitraires impossibles à tracer

## 4.5 Sous-composants

### 4.5.1 feature_selector
Rôle :
- sélectionner les features autorisées pour le moteur

### 4.5.2 weight_registry
Rôle :
- fournir les poids / priorités du score brut

### 4.5.3 raw_score_calculator
Rôle :
- calculer le score brut

### 4.5.4 score_component_breakdown
Rôle :
- décomposer le score par blocs interprétables

### 4.5.5 score_reporter
Rôle :
- fournir un objet de score audit-able

## 4.6 Inputs

- `SignalCandidate`
- moteur concerné
- paire
- régime
- features dérivées autorisées
- configuration du moteur

## 4.7 Outputs

- `ScorePayload`
- score brut total
- score par composante
- features utilisées
- version de scoring

## 4.8 État interne

- version des poids
- features activées par moteur
- historique minimal des versions de score

## 4.9 Invariants obligatoires

- chaque score brut doit être décomposable
- aucune feature non autorisée ne doit entrer dans le score
- le score doit être reproductible à partir des mêmes inputs
- toute modification de poids doit être versionnée

## 4.10 Exigences de design

- interprétabilité suffisante
- séparation par moteur
- peu de magie
- granularité correcte
- stabilité d’échelle entre versions

## 4.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `signal_engine`
- `regime_engine`
- `microstructure_engine` via outputs autorisés
- `data_quality_engine` via outputs autorisés

## 4.12 Dépendances interdites

- `risk_engine` pour caps et budgets
- `execution_engine`
- `portfolio_engine`
- `penalty_aggregator`
- `hard_block_gate`

## 4.13 Logs attendus

- raw score computed
- score components
- features used
- score version
- score out-of-range anomaly

## 4.14 Métriques mathématiques utiles

Score brut générique :
\[
S_i^{raw} = \sum_{m=1}^{M_f}\alpha_m F_{i,m}
\]

Version par blocs :
\[
S_i^{raw} = S_i^{structure} + S_i^{context} + S_i^{flow} + S_i^{cost\_preference}
\]

Normalisation éventuelle :
\[
\tilde{S}_i^{raw} = \frac{S_i^{raw} - \mu_S}{\sigma_S}
\]

Seulement si utile et bien versionnée.

## 4.15 Tests obligatoires

- score brut calculé pour signal valide
- score brut décomposé
- features manquantes correctement traitées
- feature interdite refusée
- poids versionnés
- même input → même score

## 4.16 Dérives possibles à ne pas faire

- empiler 25 features sans justification
- mélanger coût/risque/blockers dans le score brut
- créer un score “ML” opaque sans auditabilité
- changer les poids sans version

## 4.17 Priorité
P0 absolue

## 4.18 Verdict
**Implémenter maintenant**

---

# 5. MODULE 2 — PENALTY_AGGREGATOR

## 5.1 Nom canonique
`penalty_aggregator`

## 5.2 Mission

Appliquer les pénalités graduelles nécessaires sans transformer le système en moteur de veto caché.

## 5.3 Responsabilités exactes

- recevoir le score brut
- agréger les pénalités non fatales
- produire score ajusté et/ou multiplicateur de taille
- distinguer pénalités score et pénalités sizing
- tracer la contribution de chaque pénalité

## 5.4 Ce que ce module ne doit pas faire

- définir des hard blockers
- tuer silencieusement un trade par accumulation opaque
- appliquer des pénalités dupliquées sans contrôle
- faire de la logique portefeuille profonde

## 5.5 Sous-composants

### 5.5.1 penalty_registry
Rôle :
- lister les pénalités autorisées
- versionner leur présence

### 5.5.2 score_penalty_builder
Rôle :
- construire la pénalité additive sur le score

### 5.5.3 size_penalty_builder
Rôle :
- construire le multiplicateur de taille

### 5.5.4 penalty_cap_guard
Rôle :
- empêcher qu’une somme de soft penalties redevienne un veto déguisé sans trace

### 5.5.5 penalty_reporter
Rôle :
- exposer le détail des pénalités

## 5.6 Inputs

- `ScorePayload` brut
- contexte de prudence
- qualité data
- qualité microstructure
- régime
- coût attendu
- santé paire
- état infra non fatal

## 5.7 Outputs

- score pénalisé
- pénalité additive totale
- multiplicateur de taille
- détail des pénalités appliquées
- indicateur de stérilisation potentielle

## 5.8 État interne

- version des pénalités
- pénalités actives par profil / moteur
- caps de pénalité
- historique minimal des versions

## 5.9 Invariants obligatoires

- toute pénalité appliquée doit être traçable
- les pénalités doivent rester graduelles
- une pénalité non fatale ne doit pas devenir un hard block implicite
- le système doit distinguer :
  - baisse de score
  - baisse de taille
  - trade phantom

## 5.10 Exigences de design

- clarté additive
- multiplicateurs bornés
- caps explicitement définis
- pas de doublons corrélés silencieux
- calcul stable

## 5.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `raw_score_builder`
- `data_quality_engine`
- `microstructure_engine`
- `regime_engine`
- `execution_cost_meter` via outputs synthétiques si autorisé

## 5.12 Dépendances interdites

- `hard_block_gate`
- `portfolio_engine` complet
- `execution_engine` live
- moteurs directement

## 5.13 Logs attendus

- penalty applied
- penalty components
- score penalty total
- size penalty total
- penalty cap reached
- phantom risk warning

## 5.14 Métriques mathématiques utiles

Pénalité additive :
\[
Pen_i = \sum_{\ell=1}^{L} pen_{i,\ell}
\]

Score ajusté :
\[
S_i = S_i^{raw} - Pen_i
\]

Multiplicateur de taille :
\[
m_i = \prod_{\ell=1}^{L} m_{i,\ell}, \quad 0<m_{i,\ell}\le1
\]

Log multiplicatif :
\[
\log m_i = \sum_{\ell=1}^{L}\log m_{i,\ell}
\]

Risque de phantom trade :
\[
x_i \cdot \mathbb{E}[r_i] \le c_i^{op} + \epsilon
\]

## 5.15 Tests obligatoires

- une pénalité simple
- plusieurs pénalités additives
- plusieurs multiplicateurs de taille
- détail des pénalités exporté
- cap de pénalité appliqué
- trade non fatal mais fortement réduit marqué correctement

## 5.16 Dérives possibles à ne pas faire

- empiler des pénalités corrélées
- tuer le trade sans le dire
- mélanger score et taille sans distinction
- laisser les pénalités croître sans cap
- transformer ce module en hard blocker déguisé

## 5.17 Priorité
P0 absolue

## 5.18 Verdict
**Implémenter maintenant**

---

# 6. MODULE 3 — HARD_BLOCK_GATE

## 6.1 Nom canonique
`hard_block_gate`

## 6.2 Mission

Décider explicitement si une opportunité doit être interdite pour une raison fatale.

## 6.3 Responsabilités exactes

- recevoir le score pénalisé et les états critiques
- détecter les conditions fatales
- émettre un verdict binaire de blocage
- journaliser précisément la cause
- distinguer le hard block du simple rejet au ranking

## 6.4 Ce que ce module ne doit pas faire

- absorber la prudence graduelle
- contenir des règles métier “confort”
- bloquer pour des raisons de ranking
- bloquer à cause d’un simple doute qualitatif non fatal

## 6.5 Sous-composants

### 6.5.1 blocker_registry
Rôle :
- lister les hard blockers autorisés

### 6.5.2 blocker_evaluator
Rôle :
- évaluer chaque condition fatale

### 6.5.3 blocker_reason_encoder
Rôle :
- encoder les raisons de refus de manière stable

### 6.5.4 blocker_decision_builder
Rôle :
- produire le verdict final bloqué / non bloqué

### 6.5.5 blocker_reporter
Rôle :
- rapport de hard blocking

## 6.6 Inputs

- score pénalisé
- stale hard
- pair health
- état infra
- budget risque
- état exécution / reconciliation si pertinent
- profil actif

## 6.7 Outputs

- verdict hard block oui/non
- liste des raisons
- criticité
- événement blocage
- booléen autorisant ou non le ranking aval

## 6.8 État interne

- registry des blockers
- historique des hard blocks
- compteurs par raison
- version du registry

## 6.9 Invariants obligatoires

- chaque hard block doit avoir une raison explicite
- seules les raisons fatales sont autorisées
- un trade non bloqué doit rester classable
- pas de “block” silencieux sans raison codée

## 6.10 Exigences de design

- petit nombre de blockers
- raisons stables
- auditabilité
- zéro ambiguïté sur la causalité du refus

## 6.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `penalty_aggregator`
- `data_quality_engine`
- `risk_engine`
- `reconciliation_layer`
- `monitoring_engine` logique

## 6.12 Dépendances interdites

- moteurs
- logique ranking
- portefeuille profond
- heuristiques métier non fatales

## 6.13 Logs attendus

- hard block triggered
- block reason code
- block source subsystem
- block count by reason
- non-block pass

## 6.14 Métriques mathématiques utiles

Décision binaire :
\[
A_i^{HB} = \mathbf{1}_{HB_i=0}
\]

Hard block si l’une des conditions fatales est vraie :
\[
HB_i = \mathbf{1}\left(\bigcup_{b=1}^{B} condition_{b,i}\right)
\]

Taux de hard block :
\[
HBRate = \frac{N_{HB}}{N_{candidates}}
\]

Hard block par raison \(r\) :
\[
HBRate_r = \frac{N_{HB,r}}{N_{candidates}}
\]

## 6.15 Tests obligatoires

- aucun hard block sur cas sain
- stale hard block
- pair suspended block
- risk budget block
- reconciliation critical block
- raison encodée correctement
- plusieurs raisons simultanées tracées

## 6.16 Dérives possibles à ne pas faire

- ajouter 15 hard blockers “pour être safe”
- bloquer pour une simple pénalité
- faire du hard blocking dans le score builder
- raisons non standardisées
- rendre impossible l’audit du taux de hard block

## 6.17 Priorité
P0 absolue

## 6.18 Verdict
**Implémenter maintenant**

---

# 7. MODULE 4 — RANKING_ROUTER

## 7.1 Nom canonique
`ranking_router`

## 7.2 Mission

Classer les opportunités survivantes et sélectionner celles qui méritent réellement du capital dans un cadre portefeuille.

## 7.3 Responsabilités exactes

- recevoir les opportunités non hard-blocked
- comparer score, coût, CE attendue, risque et corrélation
- produire une liste ordonnée
- sélectionner les opportunités compatibles avec le portefeuille
- signaler les opportunités refusées par arbitrage relatif

## 7.4 Ce que ce module ne doit pas faire

- ignorer les budgets portefeuille
- sélectionner au score brut seul
- transformer un refus de ranking en hard block
- masquer pourquoi une opportunité perd contre une autre

## 7.5 Sous-composants

### 7.5.1 candidate_pool_builder
Rôle :
- construire le pool d’opportunités survivantes

### 7.5.2 ranking_score_builder
Rôle :
- calculer la priorité relative des candidats

### 7.5.3 portfolio_compatibility_checker
Rôle :
- vérifier budgets et corrélation avant sélection

### 7.5.4 selection_resolver
Rôle :
- choisir quelles opportunités passent réellement

### 7.5.5 ranking_reporter
Rôle :
- rapport complet de classement et refus relatifs

## 7.6 Inputs

- score pénalisé
- verdict hard block
- coût attendu
- taille projetée
- CE attendue
- risque projeté
- budget BTC disponible
- budget cluster disponible
- état portefeuille courant

## 7.7 Outputs

- liste ordonnée des opportunités
- opportunités sélectionnées
- opportunités rejetées par ranking
- motif de rejet relatif
- priorité finale

## 7.8 État interne

- pool courant
- version de ranking
- critères actifs
- historique des refus relatifs

## 7.9 Invariants obligatoires

- une opportunité non retenue doit être classée, pas “disparue”
- le ranking doit prendre en compte le portefeuille
- le motif de non sélection doit être explicite
- le ranking doit être reproductible

## 7.10 Exigences de design

- simple
- stable
- coût et CE visibles
- corrélation prise en compte
- compatible multi-moteurs et multi-paires

## 7.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `hard_block_gate`
- `risk_engine`
- `portfolio_engine`
- `execution_cost_meter` via coûts attendus
- `meta_engine` pour audit

## 7.12 Dépendances interdites

- recalcul moteur
- execution live
- overrides UI
- règles opaques non versionnées

## 7.13 Logs attendus

- candidate pool size
- ranking computed
- selected candidates
- rejected by ranking
- reason for relative rejection
- version ranking

## 7.14 Métriques mathématiques utiles

Décision finale sans hard block :
\[
A_i = \mathbf{1}_{HB_i=0}\mathbf{1}_{i \in Selected}
\]

Score de ranking conceptuel :
\[
R_i = \omega_1 S_i + \omega_2 CE_i^{exp} - \omega_3 Cost_i^{exp} - \omega_4 CorrPenalty_i - \omega_5 RiskPenalty_i
\]

où :
- \(S_i\) = score pénalisé
- \(CE_i^{exp}\) = capital efficiency attendue
- \(Cost_i^{exp}\) = coût attendu
- \(CorrPenalty_i\) = pénalité de corrélation / cluster / beta BTC
- \(RiskPenalty_i\) = pénalité de budget perte / exposition

Sélection :
\[
Selected = \operatorname*{arg\,top-k}_{i \in Candidates} R_i
\]
sous contraintes portefeuille.

Fréquence utile :
\[
F_{utile} = \frac{\text{trades à expectancy utile}}{\text{temps}}
\]

## 7.15 Tests obligatoires

- une seule opportunité valide
- plusieurs opportunités classées
- opportunité à score plus faible mais meilleur coût retenue
- opportunité refusée par manque de budget portefeuille
- opportunité refusée par corrélation cluster
- raisons de rejet relatives visibles
- résultats reproductibles

## 7.16 Dérives possibles à ne pas faire

- score brut = ranking final
- ignorer le coût
- ignorer la corrélation
- rejeter silencieusement
- utiliser un ranking non versionné
- complexifier à outrance sans gain économique

## 7.17 Priorité
P0 absolue

## 7.18 Verdict
**Implémenter maintenant**

---

# 8. Interfaces entre modules Build-5

## 8.1 raw_score_builder → penalty_aggregator
- `ScorePayload` brut
- composantes du score
- features utilisées
- version scoring

## 8.2 penalty_aggregator → hard_block_gate
- score pénalisé
- multiplicateur de taille
- pénalités détaillées
- indicateur phantom risk

## 8.3 hard_block_gate → ranking_router
- verdict hard block
- raisons de blocage
- score pénalisé survivant

## 8.4 ranking_router → order_decider / portfolio_engine
- opportunités sélectionnées
- priorités finales
- refus relatifs
- contexte de ranking

---

# 9. Ordre précis d’implémentation Build-5

## Étape 1
`raw_score_builder`

Pourquoi :
- il faut d’abord définir comment on lit la qualité d’un signal

## Étape 2
`penalty_aggregator`

Pourquoi :
- la prudence graduelle vient après le score brut

## Étape 3
`hard_block_gate`

Pourquoi :
- les interdictions fatales doivent être séparées des pénalités

## Étape 4
`ranking_router`

Pourquoi :
- le ranking n’a de sens qu’une fois le score, les pénalités et les hard blocks établis

---

# 10. Table synthétique Build-5

| Module | Ordre | Priorité | Gate critique | Sortie attendue |
|---|---:|---:|---|---|
| raw_score_builder | 1 | P0 | score brut explicable | qualité signal lisible |
| penalty_aggregator | 2 | P0 | prudence graduelle | score/taille ajustés |
| hard_block_gate | 3 | P0 | veto fatal explicite | blocage audit-able |
| ranking_router | 4 | P0 | arbitrage portefeuille | sélection finale cohérente |

---

# 11. Conditions de sortie de Build-5

Build-5 est terminé si :

- le score brut est reproductible et décomposable
- les pénalités sont graduelles et tracées
- les hard blockers sont rares, explicites et fatals
- le ranking tient compte du portefeuille, du coût et du risque
- les refus de trade sont distingués correctement :
  - hard block
  - penalty
  - rejet relatif
  - trade phantom

---

# 12. Critères de refus de sortie

Refuser Build-5 si :

- `raw_score_builder` produit un score opaque
- `penalty_aggregator` stérilise sans trace
- `hard_block_gate` contient des règles de confort non fatales
- `ranking_router` ignore coût ou corrélation
- un rejet relatif apparaît comme un hard block
- les décisions ne sont pas reproductibles

---

# 13. Dérives globales Build-5 à ne pas faire

- refaire une V5.2 avec des noms différents
- appeler “soft penalty” une quasi-interdiction
- garder un score impossible à auditer
- confondre meilleur score et meilleur trade portefeuille
- utiliser trop de règles implicites
- optimiser le score avant d’avoir validé la lisibilité économique

---

# 14. Verdict final Build-5

Build-5 est la couche qui détermine si la V5.3 devient réellement :
- lisible
- économique
- anti-stérile
- compatible portefeuille

Sans Build-5 bien fait :
- les moteurs resteront opaques
- la prudence deviendra un veto caché
- les meilleurs trades ne seront pas forcément sélectionnés
- les analytics ex post seront trompeurs

Donc :

> Build-5 doit être traité comme un **build bloquant de logique décisionnelle**, pas comme une simple couche de score.

---

## Fin du document
