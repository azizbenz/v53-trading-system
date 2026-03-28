# V5.3 MASTER FINAL UNIQUE
## Référence canonique unique — Architecture, modules, moteurs, UI, merge gates, math utiles
### Système quant crypto spot halal — prod-safe
### Sans code

---

# 0. Statut du document

Ce document devient la **source de vérité unique** de la V5.3.

Il remplace l’usage opérationnel parallèle de :
- notes d’audit
- annexes mathématiques séparées
- tables modules
- tables moteurs
- tables UI
- tables merge gates

Ces documents restent utiles comme matière de travail, mais **ne doivent plus être utilisés comme références concurrentes**.

## Règle absolue
Un développeur, un opérateur ou une IA ne doit jamais implémenter une brique sur la base d’un document secondaire si ce document contredit ou dépasse ce master.

## 0.1 Statut documentaire vs réalité d’implémentation

Pour éviter toute double vérité :

- le **core Build-1 à Build-9** reste la base réellement exécutable / gelable
- **Build-10** dispose désormais d’une première implémentation codée côté monitoring backend et projection UI Light verrouillée
- **Build-9X** est une extension méta **post-Build-9** maintenant codée dans une première version gouvernée, tout en restant soumise au pipeline canonique
- `LOCAL_REPLAY`, l’export d’artifact et l’import VPS disposent désormais de **scaffolds minimaux codés** ; cela ne vaut pas ouverture d’un runtime complet autonome
- **Build-11 à Build-17** restent des cibles futures et ne doivent pas être lus comme déjà validés

## 0.2 Invariants local / VPS

La V5.3 reste :

- **une seule base de code**
- **deux profils métier uniquement**
  - `LIGHT`
  - `COMPLETE`
- **quatre runtime_mode uniquement**
  - `LOCAL_REPLAY`
  - `SHADOW`
  - `MICRO_LIVE`
  - `LIVE`

Interdictions canoniques :

- `BACKTEST_PROFILE`
- `LOCAL_PROFILE`
- toute seconde V5.3 locale ou VPS
- toute promotion implicite d’une idée locale vers le live

---

# 1. Mission de la V5.3

La V5.3 doit transformer une V5.2 techniquement ambitieuse mais économiquement trop rare en un **portefeuille spot halal multi-paires, multi-moteurs, réellement monétisable**, sans perdre :
- la prudence de risque
- la discipline d’exécution
- la lisibilité d’architecture
- la traçabilité
- la robustesse d’infrastructure

## Le problème central
Avec :
- petit capital
- spot only
- pas de levier
- coûts réels
- fréquence initiale faible

un système peut rester :
**mathématiquement élégant mais économiquement stérile**.

La V5.3 existe pour corriger cela.

---

# 2. Contraintes non négociables

## 2.1 Contraintes marché / halal
- spot uniquement
- pas de levier
- pas de futures
- pas de perpetual
- pas de funding
- pas de dette
- pas de carry synthétique
- pas de construction à effet de levier implicite

## 2.2 Contraintes physiques
- CPU only
- pas de GPU requis en prod
- machine sobre
- pas de HFT
- faible latence utile
- Binance Spot comme environnement principal
- capital de départ modeste
- architecture résiliente aux flux dégradés

## 2.3 Contraintes de gouvernance
- source de vérité unique
- modules versionnés
- interfaces explicites
- contract tests obligatoires
- smoke tests bootstrap / recovery obligatoires
- aucun merge sans gates
- aucune activation live hors profil validé

---

# 3. Philosophie générale

La V5.3 ne cherche pas :
- à faire artificiellement plus de trades
- à relâcher aveuglément les seuils
- à ajouter des couches de math sans impact économique
- à remplacer un edge réel par du RL ou un cadre trop abstrait

La V5.3 cherche :
- plus de **fréquence utile**
- plus de **capital efficiency**
- plus de **diversité réelle d’edge**
- moins de **veto non fatals**
- plus de **discipline de coût**
- plus de **lisibilité d’implémentation**
- une séparation stricte entre :
  - sécurité
  - sélection
  - taille
  - exécution
  - gouvernance

---

# 4. Architecture cible complète

## 4.1 Vue d’ensemble
La V5.3 complète est définie comme un système :
- multi-paires : **12 paires**
- multi-moteurs : **4 moteurs**
- multi-couches :
  - Data / Ingestion
  - Data Quality
  - Microstructure
  - Regime
  - Signal
  - Scoring
  - Risk
  - Execution
  - Portfolio
  - Monitoring / Meta
  - Dependency Architecture
  - UI / Console opérateur

## 4.2 Les 12 paires cibles

### Classe A — piliers
1. BTC/USDT  
2. ETH/USDT  
3. BNB/USDT  
4. SOL/USDT  

### Classe B — actives et exploitables
5. XRP/USDT  
6. ADA/USDT  
7. LINK/USDT  
8. AVAX/USDT  

### Classe C — tactiques / encadrées
9. DOGE/USDT  
10. TRX/USDT  
11. TON/USDT  
12. DOT/USDT  

## 4.3 Les 4 moteurs

### Moteur A — Premium Trend / Expansion
Héritier du cœur V5.2. Haute conviction, qualité maximale, meilleur candidat à la concentration contrôlée.

### Moteur B — Mean Reversion Intraday
Moteur d’augmentation de fréquence utile et de rotation du capital, avec discipline stricte de coût.

### Moteur C — Breakout Continuation
Moteur de continuation à n’activer que s’il apporte un edge distinct de A.

### Moteur D — Re-entry / Second Chance Logic
Extension disciplinée d’un edge déjà validé ; jamais un moteur de “revenge trading” automatisé.

---

# 5. Profils officiels d’activation

## 5.1 Principe
Il n’existe pas plusieurs V5.3 documentaires.  
Il existe **une V5.3 unique** avec **deux profils officiels**.

## 5.2 V5.3 Light
- 6 paires maximum
- moteurs A + B uniquement
- T1 minimal utile
- T2 prudent
- T3 complet
- UI verrouillée Light
- pas de moteurs C/D live
- pas de RL
- pas de POMDP
- pas d’optimal stopping sophistiqué live

## 5.3 V5.3 Complete
- 12 paires
- moteurs A + B + C + D
- corrélation enrichie
- sizing tiers complet
- analytics enrichis
- UI complète
- uniquement après validation Light

## 5.4 Règle critique
Le document décrit le système complet.  
Le **profil actif** décrit ce qui a le droit d’exister en production aujourd’hui.

## 5.5 Runtime modes officiels

Les profils métier ne doivent pas être confondus avec les contextes d’exécution.

Les seuls `runtime_mode` autorisés sont :

- `LOCAL_REPLAY`
- `SHADOW`
- `MICRO_LIVE`
- `LIVE`

Le pipeline canonique de promotion reste :

`classification -> versioning -> shared core -> LOCAL_REPLAY -> export artifact -> import VPS -> candidature contrôlée -> Shadow -> Micro-live -> Live`

---

# 6. Réforme décisionnelle centrale : hard / soft / rank

## 6.1 Hard blockers
Réservés aux risques fatals :
- donnée corrompue
- stale data sévère
- liquidité absente
- spread extrême
- santé paire dégradée
- budget risque dépassé
- divergence critique d’état exécution
- incohérence infra sévère

## 6.2 Soft penalties
Réduisent score ou taille :
- prudence contextuelle
- signal moins propre
- microstructure dégradée mais pas invalide
- qualité moyenne mais pas fatale
- volatilité défavorable mais pas interdite

## 6.3 Ranking features
Classent les opportunités :
- qualité setup
- coût attendu
- capital efficiency attendue
- propreté du flux
- moteur / paire prioritaires
- impact corrélation

---

# 7. Catalogue canonique des modules

## 7.1 data_engine
Mission :
- ingestion WebSocket
- normalisation
- buffers
- heartbeats
- reconnexion
- routage interne

Sous-composants :
- websocket_gateway
- rest_bootstrap
- event_normalizer
- internal_router

Formules critiques :
\[
\rho_q=\frac{\lambda}{\mu_s}
\]
\[
W_q=\frac{\lambda}{\mu_s(\mu_s-\lambda)}
\]

Invariants :
- aucune analytics non critique ne doit bloquer ingestion
- exécution et risk > analytics
- une paire dégradée ne doit pas contaminer les autres

Dérives interdites :
- REST comme substitut temps réel
- file unique sans priorité
- backlog non mesuré

Profil :
- Light : NOW
- Complete : NOW

---

## 7.2 data_quality_engine
Mission :
- mesurer fraîcheur
- mesurer cohérence
- produire santé paire
- suspendre proprement

Sous-composants :
- freshness_checker
- consistency_checker
- pair_health_scorer

Formules critiques :
\[
pen_{stale}(\Delta_i)=\lambda \max(0,\Delta_i-\Delta_{max})
\]
\[
H_j = w_Q Q_j + w_L L_j + w_C C_j + w_R R_j
\]

Dérives interdites :
- “connexion OK” = qualité OK
- suspension sans raison explicite
- santé globale sans santé par paire

Profil :
- Light : NOW
- Complete : NOW

---

## 7.3 microstructure_engine
Mission :
- produire des signaux carnet/flux exploitables sans faux edge

Sous-composants :
- ofi_calculator
- book_imbalance
- microprice_estimator
- persistence_filter

Formules critiques :
\[
OFI_t = V_t^{buy} - V_t^{sell}
\]
\[
BI_t = \frac{Q_t^{bid}-Q_t^{ask}}{Q_t^{bid}+Q_t^{ask}}
\]
\[
MP_t = \frac{P_t^{ask}Q_t^{bid}+P_t^{bid}Q_t^{ask}}{Q_t^{bid}+Q_t^{ask}}
\]
\[
\bar{M}_{t,w} = \frac{1}{w}\sum_{u=t-w+1}^{t} M_u
\]

Dérives interdites :
- mini-HFT déguisé
- 15 features sans budget CPU
- feature microstructure utilisée seule

Profil :
- Light : minimal
- Complete : enrichi

---

## 7.4 regime_engine
Mission :
- segmenter le contexte de marché en régimes utiles

Sous-composants :
- regime_classifier_simple
- hmm_regime_layer
- regime_confidence

Formules critiques :
\[
\mu_s = \mathbb{E}[r \mid régime=s]
\]
\[
\mathbb{P}(z_t=s \mid y_{1:t})
\]

Dérives interdites :
- trop d’états
- HMM sur-fit
- ambiguïté de régime transformée en veto

Profil :
- Light : version simple
- Complete : version enrichie si stable

---

## 7.5 signal_engine
Mission :
- générer les setups candidats des moteurs A/B/C/D

Invariants :
- chaque moteur doit justifier sa fréquence, son coût, sa CE, sa compatibilité par paire
- aucun moteur ne doit exister s’il ne produit ni alpha net ni diversification

Profil :
- Light : A + B
- Complete : A + B + C + D

---

## 7.6 scoring_engine
Mission :
- construire score brut, pénalités, hard blockers, ranking

Sous-composants :
- raw_score_builder
- penalty_aggregator
- hard_block_gate
- ranking_router

Formules critiques :
\[
S_i^{raw} = \sum_m \alpha_m F_{i,m}
\]
\[
Pen_i = \sum_\ell pen_{i,\ell}
\]
\[
S_i = S_i^{raw} - Pen_i
\]
\[
A_i = \mathbf{1}_{HB_i=0}\mathbf{1}_{S_i \ge \tau}
\]

Dérives interdites :
- soft = hard déguisé
- score opaque
- ranking ignorant le portefeuille

Profil :
- Light : NOW
- Complete : NOW

---

## 7.7 risk_engine
Mission :
- maîtriser exposition, perte, corrélation, facteur BTC, sizing

Sous-composants :
- exposure_budgeter
- loss_budgeter
- btc_factor_guard
- correlation_cluster_guard
- kelly_guard_prudent

Formules critiques :
\[
GrossExp = \sum_i x_i
\]
\[
LossBudget = \sum_i L_i
\]
\[
\Beta_{port} = \sum_j w_j \beta_j
\]
\[
f_{mod} = \kappa \frac{\mu_{net}}{\sigma^2 + \lambda_{tail} + \lambda_{corr} + \lambda_{model}}
\]

Dérives interdites :
- sizing sans cap dur
- risque mesuré seulement par notional
- facteur BTC ignoré
- Kelly naïf non borné

Profil :
- Light : NOW
- Complete : NOW (plus riche)

---

## 7.8 execution_engine
Mission :
- exécuter, mesurer le coût réel, réconcilier l’état

Sous-composants :
- order_decider
- fill_tracker
- execution_cost_meter
- reconciliation_layer

Formules critiques :
\[
ELW = \frac{|P^{exec} - Mid|}{Mid}
\]
\[
c_i = f_i + c_i^{impl} + AS_i + PF_i
\]

Dérives interdites :
- coût réduit aux seuls fees
- portefeuille local non réconcilié
- exécuter sans break-even prudent

Profil :
- Light : NOW
- Complete : NOW

---

## 7.9 portfolio_engine
Mission :
- arbitrer les opportunités simultanées et le capital

Sous-composants :
- opportunity_selector
- allocation_router
- risk_contribution_monitor
- effective_edge_diversity

Formules critiques :
\[
Var(R_p)=w^\top\Sigma w
\]
\[
MRC_j = \frac{(\Sigma w)_j}{\sqrt{w^\top \Sigma w}}
\]
\[
K_{eff}^{spec} = \frac{(\operatorname{tr}\mathcal{R})^2}{\operatorname{tr}(\mathcal{R}^2)}
\]

Dérives interdites :
- sélectionner par score brut seul
- ignorer la corrélation
- croire à la diversification nominale

Profil :
- Light : minimal
- Complete : enrichi

---

## 7.10 monitoring_engine
Mission :
- rendre visibles performance, coût, risque, infra, backlog

Sous-composants :
- metrics_collector
- alert_manager
- health_dashboard_backend

Dérives interdites :
- dashboards décoratifs
- pas de CE
- pas de coût réel
- pas de backlog / queues

Profil :
- Light : NOW
- Complete : NOW

---

## 7.11 meta_engine
Mission :
- expliquer économiquement le système

Sous-composants :
- dtr_core
- cra_monitor
- amd_monitor
- edge_tracker_prudent
- break_even_dashboard

Formules critiques :
\[
DTR_i = (time_i, paire_i, moteur_i, S_i, HB_i, penalties_i, m_i, A_i, x_i, c_i, r_i)
\]
\[
SterilRate = \frac{\sum_i \mathbf{1}_{CE_i < CE_{min}} \mathbf{1}_{A_i=1}}{\sum_i A_i}
\]

Dérives interdites :
- perte silencieuse de DTR
- confusion trade actif / phantom
- posterior utilisé comme vérité absolue

Profil :
- Light : minimal utile
- Complete : enrichi

---

## 7.12 dependency_architecture
Mission :
- empêcher la dérive logicielle

Sous-composants :
- interface_contracts
- manifest_registry
- dag_validator
- contract_test_suite
- smoke_bootstrap_recovery

Dérives interdites :
- dicts libres partout
- cycles
- runtime caché non testé
- manifest incohérent

Profil :
- Light : NOW
- Complete : NOW

---

## 7.13 ui_console
Mission :
- pilotage contrôlé, jamais permissif

Écrans canoniques :
- overview portefeuille
- profils & état
- paires
- moteurs
- risque & exposition
- coûts & exécution
- qualité data & infra
- meta / DTR
- logs & événements
- administration contrôlée

Dérives interdites :
- profil custom libre
- bypass des hard blockers
- activer C/D en Light
- 12 paires activables en Light

Profil :
- Light : NOW
- Complete : NOW

---

# 8. Fiches détaillées des moteurs

## 8.1 Moteur A — Premium Trend / Expansion

Mission :
- moteur haute conviction, héritier V5.2
- candidat naturel à la concentration contrôlée

Paires autorisées :
- Light : BTC, ETH, BNB, SOL, XRP, LINK
- Complete : toutes les paires validées, priorité classes A/B

Régimes favorables :
- trend propre
- expansion propre
- reprise structurelle stable

Régimes défavorables :
- chop agressif
- range sale
- stress incohérent
- coût trop élevé

Formules :
\[
\mu_{A,j,s} = \mathbb{E}[r \mid A,j,s]
\]
\[
CE_{A,j} = \frac{\mathbb{E}[PnL \mid A,j]}{x \cdot h}
\]

Contraintes :
- coût prudent respecté
- budget corrélation libre
- Tier 3 seulement si budget portefeuille et santé système OK

Dérives interdites :
- moteur trop parfait pour trader
- confirmations infinies
- duplication avec C

Verdict :
- implémenter maintenant

---

## 8.2 Moteur B — Mean Reversion Intraday

Mission :
- augmenter fréquence utile et rotation capital

Paires autorisées :
- Light : BTC, ETH, SOL, XRP, ADA, LINK
- Complete : classes A/B, classes C si coût validé

Formule clé :
\[
z_t = \frac{p_t - \mu_t^{loc}}{\sigma_t^{loc}}
\]

Contraintes :
- coût plus sensible que A
- pas de Tier 3 sauf cas extrême
- fort contrôle sur faux retours à moyenne

Dérives interdites :
- mean reversion contre vraie cassure
- moteur de volume pour le volume
- z-score pur sans contexte

Verdict :
- implémenter maintenant

---

## 8.3 Moteur C — Breakout Continuation

Mission :
- capter les continuations non déjà absorbées par A

Paires autorisées :
- Complete seulement : BTC, ETH, SOL, XRP, BNB, AVAX, LINK

Formules :
\[
p_t > p_{range,max} + \delta
\]
\[
Vol_t > \theta_{Vol}
\]

Contraintes :
- pas en Light
- pas de Tier 3 initial
- doit prouver non-duplication avec A

Dérives interdites :
- faux breakout
- A plus nerveux rebaptisé C
- exécutions tardives chères

Verdict :
- implémenter plus tard

---

## 8.4 Moteur D — Re-entry / Second Chance

Mission :
- réengager une structure déjà validée sans overtrading

Paires autorisées :
- Complete : BTC, ETH, BNB, SOL, LINK en priorité

Formules :
\[
\mu_{D,j,s \mid history} = \mathbb{E}[r \mid D,j,s,historique]
\]

Contraintes :
- moteur marginal, pas central
- coût marginal strict
- jamais de concentration agressive au début

Dérives interdites :
- revenge trading automatisé
- doublon de A
- surconcentration

Verdict :
- implémenter plus tard

---

# 9. Architecture mathématique canonique

## 9.1 NOW — à implémenter en Light
- rendement net par trade :
\[
r_i = g_i - c_i
\]
- coût réel :
\[
c_i = f_i + c_i^{impl} + AS_i + PF_i
\]
- break-even prudent
- espérance / variance / Sharpe par trade
- capital efficiency :
\[
CE = \frac{PnL}{capital \times temps}
\]
- facteur BTC :
\[
r_j = \alpha_j + \beta_j r_{BTC} + \epsilon_j
\]
- variance portefeuille :
\[
Var(R_p)=w^\top \Sigma w
\]
- stale penalty
- pair health
- charge streaming \(\lambda/\mu_s\)
- logs minimaux

## 9.2 NEXT — pour Complete
- OFI dynamique
- microprice
- Ledoit-Wolf
- HMM enrichi
- Kelly modifié prudent
- \(K_{eff}\) enrichi
- sizing tiers complet

## 9.3 RESEARCH
- stopping optimal formel
- cadre bayésien hiérarchique plus riche
- POMDP conceptuel
- RL allocation théorique hors prod

## 9.4 FORBIDDEN FOR V5.3 PROD
- RL directionnel live
- PPO / DQN live
- POMDP complet live
- sophistication math sans gain direct en coût / CE / fréquence utile

---

# 10. Interface utilisateur canonique

## 10.1 Écrans obligatoires
1. Overview portefeuille  
2. Profils & état  
3. Paires  
4. Moteurs  
5. Risque & exposition  
6. Coûts & exécution  
7. Qualité data & infra  
8. Meta / DTR / phantom trades  
9. Logs & événements  
10. Administration contrôlée  

## 10.2 Règles non négociables
- aucune UI permissive
- aucune activation hors profil
- aucun bypass hard blocker
- aucune modification critique sans journalisation

## 10.3 Métriques minimales visibles
- capital
- exposition
- LossBudget
- PnL
- CE
- beta BTC
- coûts
- queue/backlog
- pair health
- moteur health
- sterilization rate

---

# 11. Merge gates et tests

## 11.1 Gate module
Un module n’est mergeable que si :
- interface définie
- dépendances valides
- contract tests
- unit tests
- smoke bootstrap
- smoke recovery si stateful
- logs critiques
- audit quant/risk si pertinent
- doc module minimale

## 11.2 Gate build
Build receivable si :
- tous modules P0 du profil présents
- logs critiques remontent
- UI minimale fonctionne
- aucun module forbidden activé
- aucun backlog critique non mesuré

## 11.3 Gate shadow
Conditions :
- décisions reproductibles
- coûts plausibles
- pass-rate économique lisible
- DTR complets
- infra stable

## 11.4 Gate micro-live
Conditions :
- coût réel vs attendu acceptable
- reconciliation stable
- stale rate faible
- backlog maîtrisé
- CE live mesurée

## 11.5 Gate live-light
Conditions :
- fréquence utile > V5.2
- edge net > 0 ou économiquement crédible
- CE > V5.2
- coûts stables
- DTR fiables
- budgets risque respectés
- beta BTC contrôlé

## 11.6 Gate live-complete
Conditions :
- Light déjà stable
- A/B validés
- C et D apportent alpha ou diversification
- K_eff augmente
- CE portefeuille augmente ou ne se dégrade pas excessivement
- infra toujours stable

---

# 12. Registre des risques canoniques

Risques à surveiller en permanence :
- non-stationnarité
- coût réel sous-estimé
- faux multi-edge
- facteur BTC caché
- faux signal microstructure
- drawdown psychologique
- stérilisation économique
- surcharge streaming
- stale data
- dérive documentaire
- sur-complexité développeur
- faux positifs statistiques
- panne de recovery
- mauvaise qualité de logs

---

# 13. Dérives structurelles interdites

- coder 12 paires + 4 moteurs d’un bloc
- utiliser plusieurs masters actifs
- confondre edge brut et edge net
- confondre fréquence brute et fréquence utile
- confondre diversification nominale et diversification réelle
- transformer soft penalties en hard blockers déguisés
- faire des modules sans tests
- laisser l’UI contourner l’architecture
- prendre les annexes math comme mandat de tout coder
- promouvoir Complete “pour avancer” sans validation économique

---

# 14. Workflow IA officiel

## ChatGPT Pro
- architecture
- audit logique quant
- risk review
- cohérence math
- arbitrage de design

## Claude Pro
- génération de code modulaire
- refactorisation
- gros fichiers techniques
- documentation technique

## Pipeline officiel
1. ChatGPT : spec module  
2. Claude : code module  
3. ChatGPT : audit quant / risk / logique  
4. Claude : correction ciblée  
5. tests  
6. merge si gates passés  

---

# 15. Plan de build module par module

## Build-0 — Fondations documentaires et architecture
1. geler ce master unique
2. geler nomenclature modules / moteurs / profils
3. geler conventions logs
4. geler conventions tests
5. geler manifest et build order

Livrables :
- master final
- plan de build
- manifest initial
- conventions test/log

Sortie :
- aucune implémentation tant que Build-0 non figé

---

## Build-1 — Dependency Architecture (P0)
Modules :
- interface_contracts
- manifest_registry
- dag_validator
- contract_test_suite
- smoke_bootstrap_recovery

Objectif :
- empêcher la dette technique avant le reste

Go :
- imports valides
- build clean
- contract tests exécutables
- smoke tests verts

---

## Build-2 — Data Backbone (P0)
Modules :
- websocket_gateway
- rest_bootstrap
- event_normalizer
- internal_router
- freshness_checker
- consistency_checker
- pair_health_scorer

Objectif :
- ingestion et qualité data fiables

Go :
- reconnect OK
- disorder OK
- stale detection OK
- suspension paire OK
- backlog visible

---

## Build-3 — Execution Backbone (P0)
Modules :
- order_decider
- fill_tracker
- execution_cost_meter
- reconciliation_layer

Objectif :
- exécution réelle mesurable et réconciliée

Go :
- ACK / fills fiables
- coûts loggés
- reconciliation stable
- partial fills gérés

---

## Build-4 — Risk Backbone (P0)
Modules :
- exposure_budgeter
- loss_budgeter
- btc_factor_guard
- correlation_cluster_guard

Objectif :
- caps d’exposition, perte et corrélation

Go :
- impossible de dépasser caps
- budget BTC affiché
- cluster caps fonctionnels

---

## Build-5 — Scoring Backbone (P0)
Modules :
- raw_score_builder
- penalty_aggregator
- hard_block_gate
- ranking_router

Objectif :
- hard / soft / rank réellement opérationnel

Go :
- décisions reproductibles
- soft ≠ hard
- ranking compatible portefeuille

---

## Build-6 — Moteur A (P0)
Modules :
- logique A
- inputs A
- outputs A
- logs A

Objectif :
- faire revivre le cœur V5.2 sans stérilité

Go :
- coûts cohérents
- fréquence utile non nulle
- DTR A propres

---

## Build-7 — Moteur B (P0)
Modules :
- logique B
- z-score local
- sorties B
- logs B

Objectif :
- augmenter fréquence utile et rotation capital

Go :
- CE correcte
- pas de destruction en cassure
- coût sous contrôle

---

## Build-8 — Portfolio Minimal (P0)
Modules :
- opportunity_selector
- allocation_router

Objectif :
- arbitrer A et B sur 6 paires sans chaos

Go :
- priorité économique visible
- caps corrélation appliqués
- pas d’allocation par score brut seul

---

## Build-9 — Meta Minimal (P0)
Modules :
- dtr_core
- cra_monitor
- break_even_dashboard
- edge_tracker_prudent minimal

Objectif :
- ne pas piloter à l’aveugle

Go :
- DTR sans perte silencieuse
- phantom trades détectés
- break-even réel visible

---

## Build-9X — Meta Learning Governed Layer (référence documentaire V2)

Mission :
- transformer l’observabilité post-trade en diagnostic gouverné
- produire des `diagnostics`
- produire des `breakdown reports`
- produire des `checklists`
- produire un `hypothesis registry`
- produire des `improvement candidates`
- produire des `replay bundles`

Contraintes :
- dépend de Build-9
- dépend opératoirement de Build-10 et de la future surface `LOCAL_REPLAY`
- aucun impact live direct
- aucune auto-modification live
- aucun fork local / VPS
- aucun nouveau profil métier

Verdict :
- **documentaire uniquement à ce stade**
- référence active : `V5_3_BUILD9X_SPEC_META_LEARNING_GOVERNED_LAYER_V2_FREEZE_READY.md`

---

## Build-10 — Monitoring + UI Light (P0/P1)
Modules :
- metrics_collector
- alert_manager
- dashboard backend
- UI Light verrouillée

Objectif :
- supervision actionnable

Go :
- Overview portefeuille OK
- profils & état OK
- paires/moteurs/risque/coûts/infra visibles
- impossible d’activer C/D ou 12 paires

---

## Build-11 — Shadow Light
Objectif :
- valider la logique sans capital

Go :
- décisions reproductibles
- DTR complets
- coûts plausibles
- infra stable

---

## Build-12 — Micro-live Light
Objectif :
- valider exécution réelle et coûts

Go :
- coûts réels acceptables
- fills/reconciliation stables
- CE mesurée
- stale/backlog maîtrisés

---

## Build-13 — Live-Light
Objectif :
- première production réelle

Go :
- fréquence utile > V5.2
- edge net > 0 ou crédible
- CE > V5.2
- A/B stables
- budgets respectés
- logs et DTR fiables

---

## Build-14 — Complete Enablers (P1/P2)
Modules :
- microstructure enrichie
- regime enrichi
- covariance plus robuste
- risk contributions
- \(K_{eff}\) enrichi

Objectif :
- préparer le passage Complete sans casser Light
- introduire d’abord les enrichissements **en lecture seule**
- n’autoriser qu’ensuite une influence limitée, jamais un moteur autonome
- absorber les `Build14_enabler` issus du protocole d’onboarding sans bypass des moteurs A/B/C/D, du risk backbone, du portfolio ni des gates de promotion

Go :
- aucune régression Light
- surcharge infra absente

---

## Build-15 — Moteur C
Objectif :
- ajouter continuation seulement si distincte de A

Go :
- alpha ou diversification démontrée
- coût supportable
- faux breakout tolérable

---

## Build-16 — Moteur D
Objectif :
- réentrée disciplinée seulement si marge utile

Go :
- contribution marginale positive
- pas de surconcentration
- coût marginal acceptable

---

## Build-17 — UI Complete + Live-Complete
Objectif :
- ouvrir 12 paires / 4 moteurs seulement si Light a prouvé sa valeur

Go :
- A/B validés
- C/D validés
- K_eff augmente
- CE portefeuille meilleure ou stable
- infra stable

---

# 16. Résultat attendu

Le projet n’est considéré V5.3 prod-safe que si :
- ce master reste unique
- le profil actif reste verrouillé
- les modules P0 sont stables
- Light est validé avant Complete
- la progression est gouvernée par :
  - edge net
  - coût réel
  - capital efficiency
  - fréquence utile
  - corrélation réelle
  - stabilité d’infrastructure

---

## Fin du master final unique
