# V5.3 — BUILD-4 SPECS MODULES
## Risk Backbone Pack
### Specs détaillées module par module
### Quatrième étape officielle du développement
### Sans code — prod-safe

---

# 0. Objet du document

Ce document couvre **Build-4** du plan officiel V5.3.

Build-4 a une mission unique :

> empêcher qu’un système techniquement propre devienne économiquement dangereux à cause d’une mauvaise gestion d’exposition, d’un budget de perte insuffisant, d’une fausse diversification ou d’une concentration cachée au facteur BTC.

Les modules couverts ici sont :

1. `exposure_budgeter`
2. `loss_budgeter`
3. `btc_factor_guard`
4. `correlation_cluster_guard`

Aucun passage sérieux en micro-live ou live ne doit être envisagé tant que ces quatre briques ne sont pas correctement spécifiées, testées et gelées.

---

# 1. Principes Build-4

## 1.1 Objectif stratégique

Build-4 ne sert pas à “ajouter du risk management décoratif”.  
Il sert à imposer les **limites non négociables** de la V5.3 :

- combien de capital peut être engagé
- combien de perte planifiée peut être tolérée
- quelle exposition systémique au facteur BTC est acceptable
- combien de positions corrélées peuvent coexister

## 1.2 Critère de réussite

Build-4 est réussi si :

- aucune exposition brute excessive n’est possible
- aucun budget de perte excessif n’est possible
- l’exposition au facteur BTC est visible et bornée
- les clusters corrélés sont surveillés et limités
- les refus de prise de position sont explicites
- le portefeuille ne peut pas “avoir l’air diversifié” alors qu’il ne l’est pas

## 1.3 Critère d’échec

Build-4 échoue si :

- le système peut encore sur-allouer sans le savoir
- le notionnel est plafonné mais pas le risque de perte
- les altcoins sont traités comme indépendants
- la concentration factorielle n’est pas visible
- les moteurs peuvent contourner les caps via plusieurs petites positions corrélées

---

# 2. Vocabulaire officiel Build-4

## 2.1 Exposition brute
Somme des capitaux engagés sur les positions ouvertes.

## 2.2 Budget de perte
Somme des pertes maximales planifiées sur les positions ouvertes.

## 2.3 Facteur BTC
Composante systémique dominante qui explique une partie importante des rendements crypto spot.

## 2.4 Cluster corrélé
Groupe de positions ou de paires dont les rendements sont suffisamment liés pour devoir être traités comme un risque commun.

---

# 3. Architecture Build-4

## 3.1 Chaîne de traitement

1. `exposure_budgeter`
2. `loss_budgeter`
3. `btc_factor_guard`
4. `correlation_cluster_guard`

## 3.2 Principe de hiérarchie

- le budget de risque ne dépend pas de l’enthousiasme du moteur
- le sizing ne peut pas contourner le risk backbone
- la corrélation observée l’emporte sur l’intuition de diversification
- le facteur BTC est traité comme un risque structurel, pas comme un détail analytique

---

# 4. MODULE 1 — EXPOSURE_BUDGETER

## 4.1 Nom canonique
`exposure_budgeter`

## 4.2 Mission

Imposer une limite stricte sur l’exposition brute totale et sur l’exposition par position.

## 4.3 Responsabilités exactes

- calculer l’exposition brute en cours
- calculer l’exposition projetée si une nouvelle position est acceptée
- refuser une position qui ferait dépasser le cap
- exposer les marges restantes
- journaliser les refus et les consommations de budget

## 4.4 Ce que ce module ne doit pas faire

- décider du moteur
- décider du sens du trade
- évaluer l’edge
- supposer qu’un petit notionnel = petit risque
- traiter l’exposition brute comme unique vérité du risque

## 4.5 Sous-composants

### 4.5.1 gross_exposure_calculator
Rôle :
- calculer l’exposition brute actuelle

### 4.5.2 projected_exposure_checker
Rôle :
- calculer l’exposition après ajout d’un trade candidat

### 4.5.3 position_cap_guard
Rôle :
- imposer un cap par position

### 4.5.4 gross_cap_guard
Rôle :
- imposer le cap global d’exposition

### 4.5.5 exposure_reporter
Rôle :
- rapport de consommation d’exposition

## 4.6 Inputs

- capital total
- positions ouvertes
- taille candidate \(x_i\)
- profil actif
- caps configurés

## 4.7 Outputs

- exposition brute actuelle
- exposition brute projetée
- verdict accepté / refusé
- raison de refus
- capacité résiduelle

## 4.8 État interne

- exposition brute courante
- historique des refus
- historique des consommations
- caps actifs par profil

## 4.9 Invariants obligatoires

- aucune position ne doit dépasser son cap unitaire
- l’exposition globale ne doit jamais dépasser son cap
- l’exposition projetée doit être calculée avant acceptation
- le verdict de refus doit être explicite

## 4.10 Exigences de design

- calcul simple
- déterministe
- auditable
- compatible Light / Complete
- pas de logique cachée

## 4.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `portfolio_engine` via interface
- `reconciliation_layer` pour état positions validé

## 4.12 Dépendances interdites

- moteurs
- scoring
- logique de signal
- contournement par UI

## 4.13 Logs attendus

- gross exposure current
- gross exposure projected
- position cap breach
- gross cap breach
- trade refused by exposure
- remaining capacity

## 4.14 Métriques mathématiques utiles

Exposition brute :
\[
GrossExp = \sum_{i \in positions} x_i
\]

Contrainte globale :
\[
GrossExp \le X_{gross,max}
\]

Contrainte projetée :
\[
GrossExp + x_{new} \le X_{gross,max}
\]

Contrainte par position :
\[
x_i \le x_{max,pos}
\]

Ratio d’utilisation :
\[
GrossUtil = \frac{GrossExp}{X_{gross,max}}
\]

## 4.15 Tests obligatoires

- exposition nulle
- une position sous cap
- une position au-dessus du cap
- dépassement cap global
- calcul exposition projetée
- refus explicite
- cohérence après fermeture de position

## 4.16 Dérives possibles à ne pas faire

- confondre exposition brute et risque total
- ne pas recalculer après fills partiels
- utiliser des caps différents non journalisés
- laisser l’UI modifier les caps en live

## 4.17 Priorité
P0 absolue

## 4.18 Verdict
**Implémenter maintenant**

---

# 5. MODULE 2 — LOSS_BUDGETER

## 5.1 Nom canonique
`loss_budgeter`

## 5.2 Mission

Imposer une limite stricte sur la perte maximale planifiée du portefeuille.

## 5.3 Responsabilités exactes

- calculer la perte maximale planifiée de chaque position
- agréger les pertes maximales planifiées
- calculer la perte projetée si un nouveau trade est accepté
- refuser une position si le budget de perte serait dépassé
- exposer la capacité de perte restante

## 5.4 Ce que ce module ne doit pas faire

- supposer que petit notionnel = petite perte
- ignorer le stop / exit plan
- remplacer la mesure du drawdown réalisé
- se réduire à une règle de pourcentage floue

## 5.5 Sous-composants

### 5.5.1 position_loss_estimator
Rôle :
- estimer \(L_i\) pour une position

### 5.5.2 aggregate_loss_budgeter
Rôle :
- agréger les \(L_i\) actifs

### 5.5.3 projected_loss_checker
Rôle :
- calculer le budget après trade candidat

### 5.5.4 loss_cap_guard
Rôle :
- refuser si le budget serait dépassé

### 5.5.5 loss_reporter
Rôle :
- rapport de consommation du budget perte

## 5.6 Inputs

- positions ouvertes
- stop / invalidation / sortie de protection
- taille candidate
- budget perte configuré

## 5.7 Outputs

- perte planifiée par position
- budget perte courant
- budget perte projeté
- verdict accepté / refusé
- capacité de perte restante

## 5.8 État interne

- \(L_i\) par position
- budget courant
- historique breaches
- historique refus

## 5.9 Invariants obligatoires

- toute position doit avoir un \(L_i\) explicite
- le budget de perte projeté doit être calculé avant acceptation
- aucun trade ne doit être accepté sans impact perte connu
- refus explicite si budget dépassé

## 5.10 Exigences de design

- basé sur pertes plausibles, pas sur intuition
- déterministe
- audit-able
- simple à relier au moteur et à la paire

## 5.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `risk_engine` interne
- `reconciliation_layer` pour positions validées

## 5.12 Dépendances interdites

- logique moteur
- scoring
- exécution autonome
- modifications d’ordres

## 5.13 Logs attendus

- position loss estimated
- aggregate loss budget
- projected loss budget
- loss budget breach
- trade refused by loss budget

## 5.14 Métriques mathématiques utiles

Perte planifiée par position :
\[
L_i
\]

Budget de perte :
\[
LossBudget = \sum_{i \in positions} L_i
\]

Contrainte :
\[
LossBudget \le LB_{max}
\]

Contrainte projetée :
\[
LossBudget + L_{new} \le LB_{max}
\]

Ratio d’utilisation :
\[
LossUtil = \frac{LossBudget}{LB_{max}}
\]

## 5.15 Tests obligatoires

- une position avec \(L_i\) valide
- absence de \(L_i\) refusée
- budget perte sous cap
- budget perte dépassé
- budget projeté correct
- fermeture position libère budget

## 5.16 Dérives possibles à ne pas faire

- utiliser uniquement un cap notionnel
- ne pas lier \(L_i\) à un vrai plan de sortie
- définir \(L_i\) irréaliste juste pour “faire passer” un trade
- ignorer le budget de perte cluster

## 5.17 Priorité
P0 absolue

## 5.18 Verdict
**Implémenter maintenant**

---

# 6. MODULE 3 — BTC_FACTOR_GUARD

## 6.1 Nom canonique
`btc_factor_guard`

## 6.2 Mission

Empêcher que le portefeuille devienne une exposition cachée quasi monofactorielle au BTC.

## 6.3 Responsabilités exactes

- estimer ou consommer le \(\beta_j\) de chaque paire au facteur BTC
- calculer le \(\Beta_{port}\) portefeuille
- calculer le \(\Beta_{port}\) projeté après un nouveau trade
- refuser les prises de position qui dépassent le budget systémique
- exposer la concentration factorielle

## 6.4 Ce que ce module ne doit pas faire

- prétendre capturer toute la structure de risque
- remplacer les clusters corrélés
- supposer que 12 paires = diversification
- masquer l’incertitude sur les \(\beta_j\)

## 6.5 Sous-composants

### 6.5.1 pair_beta_registry
Rôle :
- stocker / exposer les \(\beta_j\) actifs

### 6.5.2 portfolio_beta_calculator
Rôle :
- calculer le \(\Beta_{port}\) courant

### 6.5.3 projected_beta_checker
Rôle :
- calculer l’impact d’un nouveau trade

### 6.5.4 beta_cap_guard
Rôle :
- refuser si le budget BTC est dépassé

### 6.5.5 beta_reporter
Rôle :
- rapport exposition systémique

## 6.6 Inputs

- poids / tailles des positions
- \(\beta_j\) estimés ou pré-calibrés
- trade candidat
- budget BTC configuré

## 6.7 Outputs

- \(\Beta_{port}\) courant
- \(\Beta_{port}\) projeté
- verdict accepté / refusé
- marge BTC restante
- concentration factorielle visible

## 6.8 État interne

- \(\beta_j\) par paire
- budget BTC courant
- historique dépassements
- historique refus

## 6.9 Invariants obligatoires

- chaque paire active a un \(\beta_j\) défini ou une politique explicite
- \(\Beta_{port}\) courant est calculable
- \(\Beta_{port}\) projeté est calculé avant acceptation
- dépassement du budget déclenche un refus explicite

## 6.10 Exigences de design

- simple
- lisible
- prudent
- ne pas prétendre à une précision faussement académique
- utilisable Light et Complete

## 6.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `portfolio_engine` via interface
- registry des paires

## 6.12 Dépendances interdites

- signal_engine
- moteurs
- UI overrides cachés

## 6.13 Logs attendus

- pair beta loaded
- portfolio beta current
- portfolio beta projected
- beta breach
- trade refused by beta guard

## 6.14 Métriques mathématiques utiles

Modèle facteur :
\[
r_j = \alpha_j + \beta_j r_{BTC} + \epsilon_j
\]

Bêta paire :
\[
\beta_j = \frac{Cov(r_j,r_{BTC})}{Var(r_{BTC})}
\]

Bêta portefeuille :
\[
\Beta_{port} = \sum_{j=1}^{M} w_j \beta_j
\]

Contrainte :
\[
|\Beta_{port}| \le B_{max}
\]

Contrainte projetée :
\[
|\Beta_{port}^{proj}| \le B_{max}
\]

## 6.15 Tests obligatoires

- paire avec beta connu
- portefeuille beta correct
- trade augmentant beta
- dépassement budget BTC refusé
- réduction d’exposition BTC acceptée
- journalisation des refus

## 6.16 Dérives possibles à ne pas faire

- ne pas recalibrer les \(\beta_j\) quand nécessaire
- croire qu’un beta approximatif = vérité absolue
- utiliser uniquement le notional par paire
- masquer le budget BTC à l’opérateur

## 6.17 Priorité
P0 absolue

## 6.18 Verdict
**Implémenter maintenant**

---

# 7. MODULE 4 — CORRELATION_CLUSTER_GUARD

## 7.1 Nom canonique
`correlation_cluster_guard`

## 7.2 Mission

Empêcher qu’un portefeuille apparemment diversifié ne soit en réalité qu’un ensemble de positions fortement corrélées.

## 7.3 Responsabilités exactes

- définir les clusters corrélés officiels
- calculer l’exposition courante par cluster
- calculer l’exposition projetée par cluster
- refuser les nouvelles positions qui surchargent un cluster
- exposer clairement la concentration corrélée

## 7.4 Ce que ce module ne doit pas faire

- remplacer l’analyse factorielle BTC
- prétendre faire une covariance parfaite temps réel
- être opaque
- définir des clusters arbitraires non documentés

## 7.5 Sous-composants

### 7.5.1 cluster_registry
Rôle :
- lister les clusters officiels et leurs membres

### 7.5.2 cluster_exposure_calculator
Rôle :
- calculer l’exposition par cluster

### 7.5.3 projected_cluster_checker
Rôle :
- calculer l’impact d’un nouveau trade

### 7.5.4 cluster_cap_guard
Rôle :
- refuser si le cap cluster est dépassé

### 7.5.5 cluster_reporter
Rôle :
- rapport de concentration corrélée

## 7.6 Inputs

- positions ouvertes
- mapping paire → cluster(s)
- trade candidat
- caps cluster configurés

## 7.7 Outputs

- exposition cluster courante
- exposition cluster projetée
- verdict accepté / refusé
- cluster dominant
- marges restantes

## 7.8 État interne

- clusters actifs
- exposition par cluster
- historique breaches
- historique refus

## 7.9 Invariants obligatoires

- chaque paire active appartient à un cluster explicite
- l’exposition par cluster est visible
- la projection est calculée avant acceptation
- les refus cluster sont explicites

## 7.10 Exigences de design

- clusters simples et audités
- pas de clustering opaque “IA”
- utilisable dès Light
- compatible avec enrichissement Complete

## 7.11 Dépendances autorisées

- `interface_contracts`
- `manifest_registry`
- `portfolio_engine` via interface
- registry paires / clusters

## 7.12 Dépendances interdites

- logique moteur
- UI override
- covariance temps réel lourde
- dépendance à du ML complexe

## 7.13 Logs attendus

- cluster exposure current
- cluster exposure projected
- cluster cap breach
- trade refused by cluster guard
- dominant cluster updated

## 7.14 Métriques mathématiques utiles

Exposition cluster :
\[
ClusterExp_c = \sum_{i \in cluster\ c} x_i
\]

Contrainte :
\[
ClusterExp_c \le X_{cluster,c}^{max}
\]

Contrainte projetée :
\[
ClusterExp_c + x_{new} \le X_{cluster,c}^{max}
\]

Ratio cluster :
\[
ClusterUtil_c = \frac{ClusterExp_c}{X_{cluster,c}^{max}}
\]

## 7.15 Tests obligatoires

- cluster simple
- exposition cluster correcte
- dépassement cluster refusé
- plusieurs clusters
- paire membre d’un cluster attendu
- refus journalisé

## 7.16 Dérives possibles à ne pas faire

- cluster implicite jamais documenté
- ignorer la concentration au motif que les tickers sont différents
- définir des clusters trop fins et inutilisables
- définir un cluster unique pour tout sans nuance opérationnelle

## 7.17 Priorité
P0 absolue

## 7.18 Verdict
**Implémenter maintenant**

---

# 8. Interfaces entre modules Build-4

## 8.1 exposure_budgeter → order_decider / portfolio_engine
- verdict d’exposition acceptable ou non
- capacité notionnelle restante

## 8.2 loss_budgeter → order_decider / portfolio_engine
- verdict budget perte acceptable ou non
- capacité perte restante

## 8.3 btc_factor_guard → portfolio_engine / UI / monitoring
- \(\Beta_{port}\) courant
- \(\Beta_{port}\) projeté
- refus systémique

## 8.4 correlation_cluster_guard → portfolio_engine / UI / monitoring
- exposition cluster
- cluster dominant
- refus cluster

---

# 9. Ordre précis d’implémentation Build-4

## Étape 1
`exposure_budgeter`

Pourquoi :
- premier niveau de cap le plus simple et indispensable

## Étape 2
`loss_budgeter`

Pourquoi :
- l’exposition brute ne suffit pas, il faut un cap de perte

## Étape 3
`btc_factor_guard`

Pourquoi :
- le portefeuille crypto est sinon aveugle à son facteur systémique principal

## Étape 4
`correlation_cluster_guard`

Pourquoi :
- complète le facteur BTC par une logique opérationnelle de concentration corrélée

---

# 10. Table synthétique Build-4

| Module | Ordre | Priorité | Gate critique | Sortie attendue |
|---|---:|---:|---|---|
| exposure_budgeter | 1 | P0 | cap notionnel | exposition brute bornée |
| loss_budgeter | 2 | P0 | cap perte | budget de perte borné |
| btc_factor_guard | 3 | P0 | cap systémique | beta BTC contrôlé |
| correlation_cluster_guard | 4 | P0 | cap cluster | concentration corrélée contrôlée |

---

# 11. Conditions de sortie de Build-4

Build-4 est terminé si :

- aucun trade ne peut dépasser les caps d’exposition
- aucun trade ne peut dépasser le budget de perte
- le \(\Beta_{port}\) est visible et utilisable
- les clusters corrélés sont visibles et bornés
- tous les refus sont explicites
- l’UI peut afficher les budgets critiques

---

# 12. Critères de refus de sortie

Refuser Build-4 si :

- `exposure_budgeter` ne bloque pas réellement les dépassements
- `loss_budgeter` n’exige pas un \(L_i\) explicite
- `btc_factor_guard` n’expose pas le \(\Beta_{port}\) projeté
- `correlation_cluster_guard` ne bloque pas une concentration évidente
- un moteur peut encore contourner le backbone risque via plusieurs petits trades

---

# 13. Dérives globales Build-4 à ne pas faire

- considérer que l’exposition brute suffit
- considérer que le budget de perte est “théorique”
- croire que plusieurs altcoins = vraie diversification
- ignorer le facteur BTC tant que “ça va”
- repousser les guards corrélés à plus tard

---

# 14. Verdict final Build-4

Build-4 est la couche qui transforme le système de “collection de signaux” en **portefeuille discipliné**.

Sans Build-4 bien fait :
- les moteurs peuvent sur-allouer
- la perte potentielle peut devenir incontrôlée
- la diversification peut être illusoire
- le portefeuille peut rester en fait quasi mono-factoriel

Donc :

> Build-4 doit être traité comme un **build bloquant de gouvernance du capital**, pas comme une couche risk cosmétique.

---

# Guardrails issus des audits — Renforcements Build-4

## Drawdown protection active (GEM-09)
- Le risk backbone doit inclure un drawdown guard actif dès Build-4 en trajectoire Light
- Si le drawdown intraday dépasse un seuil configurable, le système réduit l'exposition ou passe en observation
- Build-4 n'est pas validé si ce garde-fou reste une métrique décorative ou une simple note documentaire

## Limites beta statique / clusters fixes (GEM-09, QWEN-09)
- Le `correlation_cluster_guard` utilise des clusters définis en dur (DEFAULT_CLUSTERS)
- Limitation explicite : en cas de krach, toutes les corrélations tendent vers 1
- La diversification par cluster peut échouer exactement quand on en a besoin
- Le canon reconnaît cette limite et prévoit une calibration dynamique future (Build-14+)

## Clarification proxy risk vs risk réel (GEM-09)
- Le risk backbone Build-4 mesure un **proxy de risque** basé sur des corrélations statiques
- Ce proxy est utile mais ne capture pas le risque factoriel complet
- Le canon distingue explicitement :
  - **proxy risk** (Build-4) : corrélations statiques, clusters fixes, beta BTC estimé
  - **risk réel enrichi** (Build-14+) : Ledoit-Wolf, corrélation dynamique, risk contribution
- Le proxy risk est suffisant pour Light mais ne doit pas être confondu avec le risk réel

## Besoin de calibration dynamique future (GEM-09)
- Le passage à Build-14 doit apporter :
  - recalcul périodique des matrices de corrélation
  - Ledoit-Wolf ou estimation robuste
  - risk contribution monitor enrichi
- Ces enrichissements sont **activés à 100% en Shadow** (`SHADOW_ENABLED`), pleinement utilisés et observés
- Leur promotion live reste conditionnelle au verdict post-Shadow

---

## Fin du document
