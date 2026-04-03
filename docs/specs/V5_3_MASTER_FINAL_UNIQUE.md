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

Par stabilisation documentaire finale :

- `V5_3_MASTER_FINAL_UNIQUE.md` est le **seul master actif**
- `V5_3_MASTER_FINAL_CANONICAL.md`, s'il est conservé, n'est qu'un **miroir secondaire**
- aucune table, annexe, addendum ou note transverse ne peut se comporter comme une source autonome si elle contredit ce master

## Règle absolue
Un développeur, un opérateur ou une IA ne doit jamais implémenter une brique sur la base d’un document secondaire si ce document contredit ou dépasse ce master.

## 0.1 Statut documentaire vs réalité d’implémentation

Pour éviter toute double vérité :

- le **core Build-1 à Build-9** reste la base réellement exécutable / gelable
- **Build-10** dispose désormais d’une première implémentation codée côté monitoring backend et projection UI Light verrouillée
- **Build-9X** est une extension méta **post-Build-9** maintenant codée dans une première version gouvernée, tout en restant soumise au pipeline canonique
- `LOCAL_REPLAY`, l’export d’artifact et l’import VPS disposent désormais de **scaffolds minimaux codés** ; cela ne vaut pas ouverture d’un runtime complet autonome
- **Build-11 à Build-17** restent des etapes canoniques de validation et
  d'extension du rollout ; ils ne doivent pas etre lus comme des architectures
  concurrentes ni comme deja valides

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

## 0.3 Intégration des audits tiers — Principe officiel

Les audits tiers (Gemini, Opus, Qwen, ou tout futur audit) sont de la **matière de correction**, jamais une source de vérité active.

Règles d’intégration :
- chaque finding est classé dans une catégorie unique : NOW_P0 / NOW_LIGHT / NEXT_BUILD14 / RESEARCH_LOCAL / REJECT
- un finding classé est absorbé dans le fichier MD cible concerné, pas dans un document concurrent
- un audit ne peut jamais créer une architecture concurrente, un nouveau profil, un nouveau moteur hors A/B/C/D, ou un bypass de gate
- le rapport de triage officiel est `V5_3_AUDIT_INTEGRATION_DECISIONS.md`

## 0.4 HARD STATE documentaire — Cycle de vie officiel

Chaque brique, build, moteur ou couche du système V5.3 est décrite par un **état officiel unique et non ambigu** :

| Hard State | Signification |
|---|---|
| `CODED` | Le code existe dans le dépôt |
| `DOCUMENTED` | La spécification canonique est écrite et cohérente |
| `SHADOW_ENABLED` | Activé à 100% en mode SHADOW, pleinement utilisé et observé |
| `SHADOW_VALIDATED` | Les 30 jours de Shadow sont terminés avec verdict positif |
| `MICRO_LIVE_ELIGIBLE` | Éligible au passage Micro-live après verdict Shadow |
| `LIVE_LIGHT_ELIGIBLE` | Éligible au passage Live-Light après Micro-live validé |
| `COMPLETE_ELIGIBLE` | Éligible au passage Live-Complete après Shadow Complete validé |
| `PROMOTED` | Activé en production dans le profil autorisé |
| `DORMANT` | Codé et documenté mais volontairement non activé |
| `FORBIDDEN` | Interdit en V5.3 prod (RL live, POMDP live, etc.) |

Règles :
- Un build `CODED` n’est PAS un build `SHADOW_VALIDATED`.
- Un build `SHADOW_VALIDATED` n’est PAS un build `PROMOTED`.
- `SHADOW_ENABLED` signifie **activé à 100% et pleinement utilisé** en Shadow, pas en lecture seule.
- En particulier : Build-14 `CODED` ≠ Build-14 `PROMOTED`.
- Complete enablers `SHADOW_ENABLED` ≠ activation Complete live.
- Activation en Shadow ≠ promotion automatique vers Live.

## 0.6 HARD STATEMENT — Règle de promotion temporelle obligatoire

> **Cette règle est NON NÉGOCIABLE. Aucune dérogation, aucun raccourci, aucune exception.**

### Principe fondamental

Toute la solution V5.3 (Light + Complete, Builds 1→17) est **codée intégralement**.
Mais le code existant ne donne **aucun droit de promotion automatique**.
La promotion suit un pipeline temporel hard :

### Pipeline de promotion hard

```
[TOUT CODÉ] → Light Shadow intégral 30j → Light Live → Complete Shadow 30j → Complete Live
```

### Règle 1 — Shadow intégral = phase de vérité système

- Le Shadow 30 jours est la **phase de vérité système** où la solution est testée dans sa forme intégrale observée
- Pendant ces 30 jours, **tous les composants du rollout Light sont activés à 100%** :
  - Moteurs A et B actifs, scorés, classés, arbitrés et observés
  - Build-14 (Complete Enablers) activé à 100%, pleinement utilisé dans les décisions Shadow
  - Enrichissements microstructure, régime, covariance robuste, risk contribution, edge diversity actifs
  - Monitoring, DTR, coût, risk, portefeuille, toxicité complets
- Le Shadow n’est plus une simple validation Light minimale ; il est la **phase où l’on observe le rollout Light complet avant de décider quoi promouvoir**

### Règle 2 — Light Shadow obligatoire 30 jours

- La version **Light** doit trader en mode **SHADOW** pendant un minimum de **30 jours calendaires consécutifs** avant toute activation en live
- Pendant ces 30 jours : données réelles, pipeline complet, DTR complet, aucun ordre réel envoyé
- **Build-14 et tous les enrichissements du rollout Light sont activés à 100% en Shadow** pour observer leur comportement réel
- Si un incident interrompt le shadow pendant plus de 24h, le compteur reprend à zéro
- Aucune activation Micro-live ni Live-Light n’est autorisée avant l’expiration de cette période
- Les 30 jours doivent produire un rapport shadow exploitable (CE, coûts estimés, edge, drawdown, stale rate, comparaison inter-moteurs A/B, contribution Build-14)

### Règle 3 — Activation Shadow ≠ promotion Live

- L’activation intégrale en Shadow (Build-14 à 100%, A/B/C/D actifs) **ne signifie pas promotion automatique vers Live**
- La promotion reste strictement conditionnelle au **verdict post-Shadow**
- Possibilité de rollback, downgrade ou désactivation sélective à l’issue des 30 jours
- Chaque composant est jugé individuellement : un moteur peut être validé en Shadow mais non promu en Live

### Règle 4 — Light Live = condition préalable à Complete Live

- La version Light doit être **stable en Live-Light** avant toute considération de Complete Live
- "Stable" signifie : CE positive ou économiquement crédible, pas de kill switch déclenché, DTR complet, réconciliation sans divergence critique

### Règle 5 — Complete Shadow obligatoire 30 jours

- La version **Complete** (activation des enablers Build-14, engines C/D, 12 paires) doit trader en mode **SHADOW** pendant un minimum de **30 jours calendaires consécutifs** avant toute activation en live
- Pendant ces 30 jours : la version Complete tourne en parallèle de la version Light live
- Si l’enrichissement Complete dégrade les métriques Light shadow, il est désactivé et le compteur reprend à zéro
- Non-régression Light obligatoire : Complete shadow doit démontrer que Light n’est pas dégradée
- Les 30 jours doivent produire un rapport comparatif Light vs Complete

### Règle 6 — Aucun raccourci

- Aucun opérateur, aucune IA, aucun audit ne peut bypasser ces délais
- "Le code est prêt" n’est pas un argument pour réduire la période de shadow
- "Les tests passent" n’est pas un argument pour réduire la période de shadow
- Seul le temps réel de marché valide un système de trading
- L’activation intégrale en Shadow est un **essai structuré**, pas une promotion déguisée

## 0.5 Guardrails P0 issus des audits (invariants système)

Les invariants suivants sont **obligatoires** dans tout le système V5.3 :

1. **Crossed book** : toute structure DepthEvent doit valider `best_ask >= best_bid` ; un carnet croisé est rejeté, jamais traité
2. **Epsilon risk/reward** : tout calcul risk/reward doit avoir un epsilon minimum (`risk < 1e-6 → None`) ; pas de ratio aberrant
3. **Imports dynamiques** : le DAG validator doit signaler tout usage de `importlib.import_module` comme dépendance wildcard potentielle
4. **Recovery backoff** : tout cycle recovery doit implémenter un exponential backoff avec vérification de libération des ressources I/O
5. **Buffer drop_oldest** : tout buffer de messages doit utiliser une politique drop_oldest (deque maxlen), jamais drop_newest
6. **Jitter tolerance** : le contradiction checker doit tolérer un jitter réseau configurable (5-10ms) avant de lever TIMESTAMP_REVERSAL
7. **Latence monotone** : toute mesure de latence doit utiliser un clock monotone et filtrer les valeurs aberrantes (négatives ou > seuil)
8. **Kill switch persistant** : l’état du circuit breaker doit être persisté sur disque (écriture atomique) et survivre aux redémarrages
9. **Persistance atomique** : toute écriture d’état critique doit passer par write-tmp-then-rename
10. **Stale guard runtime** : tout message dont le delta exchange_time vs local_time dépasse un seuil configurable est rejeté du pipeline de décision
11. **Persistance minimale stores critiques** : DTR, états portefeuille et logs d’audit doivent avoir un flush périodique vers fichier
12. **Kill switch externe** : un mécanisme hors processus Python (fichier flag ou API admin) doit pouvoir couper le trading instantanément

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

# 5. Profils officiels de rollout et d’activation

## 5.1 Principe
Il n’existe pas plusieurs V5.3 documentaires.
Il existe **une V5.3 unique** avec **deux enveloppes officielles de rollout**.

`LIGHT` et `COMPLETE` ne decrivent pas deux architectures differentes.
Ils decrivent deux envelopes d'activation reelle d'une meme architecture
complete, prod-safe et gouvernee.

`COMPLETE` désigne exclusivement l'enveloppe de rollout élargie.
Le Shadow du profil `LIGHT` avec A/B/C/D et Build-14 activés à 100% en
observation est nommé `Shadow intégral`.
`Shadow intégral` n'est pas le profil `COMPLETE`.

## 5.2 V5.3 Light
- premier rollout reel prudent et gouverne
- 6 paires maximum en production reelle
- architecture complete disponible et documentee
- moteurs A/B au coeur du rollout Light ; C/D observés pendant le Shadow 30 jours puis promouvables seulement sous verdict et hardening dédiés
- A/B attendus au coeur du rollout initial live
- **Build-14 activé à 100% pendant le Shadow 30 jours** : utilise dans les decisions du rollout Light et compare au coeur A/B
- C/D peuvent être observés via Build-11, mais ne sont jamais promus via Build-11 sans verdict post-Shadow et gates dédiés
- portfolio, risk, execution, UI et logs complets et auditables
- pas de profil custom
- pas de RL live
- pas de POMDP live
- pas de sophistication opaque sans valeur prod-safe demontree

## 5.3 V5.3 Complete
- extension gouvernee du meme systeme
- jusqu'a 12 paires
- A/B/C/D activables sous gouvernance
- correlation enrichie
- sizing tiers complet
- analytics enrichis
- UI complete
- uniquement apres stabilisation du rollout LIGHT et validation des paliers

## 5.4 Règle critique
Le document decrit le systeme complet.
Le **profil actif** decrit ce qui peut etre active en production aujourd'hui,
pas ce qui existe doctrinalement dans l'architecture cible.

## 5.5 Runtime modes officiels

Les profils métier ne doivent pas être confondus avec les contextes d’exécution.

Les seuls `runtime_mode` autorisés sont :

- `LOCAL_REPLAY`
- `SHADOW`
- `MICRO_LIVE`
- `LIVE`

Le pipeline canonique de promotion reste :

`classification -> versioning -> shared core -> LOCAL_REPLAY -> export artifact -> import VPS -> candidature contrôlée -> Shadow -> Micro-live -> Live`

## 5.6 Matrice canonique des états

Un état de rollout se lit toujours comme :

- `profil + runtime_mode`

Repères canoniques :

- `profil=LIGHT`, `runtime_mode=LOCAL_REPLAY` : préparation locale et preuve
  avant candidature
- `profil=LIGHT`, `runtime_mode=SHADOW` : Build-11, nommé `Shadow intégral`
- `profil=LIGHT`, `runtime_mode=MICRO_LIVE` : Build-12
- `profil=LIGHT`, `runtime_mode=LIVE` : Build-13, nommé `Live-Light`
- `profil=COMPLETE`, `runtime_mode=SHADOW` : Shadow Complete
- `profil=COMPLETE`, `runtime_mode=LIVE` : Live-Complete

Règle de lecture :

- `LIGHT` et `COMPLETE` sont des profils
- `SHADOW`, `MICRO_LIVE` et `LIVE` sont des contextes d'exécution
- `Shadow intégral` est un nom de phase, pas un troisième profil

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
- LIGHT : base gouvernee compatible rollout initial
- COMPLETE : couche enrichie gouvernee

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
- LIGHT : version gouvernee pour rollout initial
- COMPLETE : version enrichie si stable et utile

---

## 7.5 signal_engine
Mission :
- générer les setups candidats des moteurs A/B/C/D

Invariants :
- chaque moteur doit justifier sa fréquence, son coût, sa CE, sa compatibilité par paire
- aucun moteur ne doit exister s’il ne produit ni alpha net ni diversification

Profil :
- LIGHT : A/B coeur attendu en live ; C/D observés en Shadow ; promotion aval uniquement si validés et industrialisés
- COMPLETE : A/B/C/D dans une enveloppe de rollout elargie

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
- LIGHT : base gouvernee compatible rollout initial
- COMPLETE : couche enrichie gouvernee

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
- LIGHT : socle explicatif obligatoire
- COMPLETE : couche enrichie gouvernee

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
- activer un moteur sans gates, budgets ou journalisation
- ouvrir > 6 paires en LIGHT sans validation de rollout

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
- SHADOW : toutes paires Light (activé à 100%, scoré, comparé à A/B)
- LIVE LIGHT : promu seulement si verdict Shadow positif, gates C validées
- COMPLETE : BTC, ETH, SOL, XRP, BNB, AVAX, LINK puis extension gouvernee

Formules :
\[
p_t > p_{range,max} + \delta
\]
\[
Vol_t > \theta_{Vol}
\]

Contraintes :
- activé à 100% en Shadow, pas en live par défaut
- pas de Tier 3 initial
- doit prouver non-duplication avec A pendant les 30 jours Shadow

Dérives interdites :
- faux breakout
- A plus nerveux rebaptisé C
- exécutions tardives chères
- confondre activation Shadow et promotion live

Hard State : `SHADOW_ENABLED` → verdict → `SHADOW_VALIDATED` ou `DORMANT`

Verdict :
- moteur natif de la solution complete, activé à 100% en Shadow, promotion live strictement gouvernee par verdict post-Shadow

---

## 8.4 Moteur D — Re-entry / Second Chance

Mission :
- réengager une structure déjà validée sans overtrading

Paires autorisées :
- SHADOW : toutes paires Light (activé à 100%, scoré, comparé à A/B/C)
- LIVE LIGHT : promu seulement si verdict Shadow positif, gates D validées
- COMPLETE : BTC, ETH, BNB, SOL, LINK en priorite puis extension gouvernee

Formules :
\[
\mu_{D,j,s \mid history} = \mathbb{E}[r \mid D,j,s,historique]
\]

Contraintes :
- moteur marginal, pas central
- coût marginal strict
- jamais de concentration agressive au début
- activé à 100% en Shadow, pas en live par défaut

Dérives interdites :
- revenge trading automatisé
- doublon de A
- surconcentration
- confondre activation Shadow et promotion live

Hard State : `SHADOW_ENABLED` → verdict → `SHADOW_VALIDATED` ou `DORMANT`

Verdict :
- moteur natif de la solution complete, activé à 100% en Shadow, promotion live strictement gouvernee par verdict post-Shadow

---

# 9. Architecture mathématique canonique

La difference canonique porte sur l'ordre de verification et d'activation
reelle, pas sur l'existence doctrinale des composants.

## 9.1 Obligatoire avant rollout reel initial
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

## 9.2 Obligatoire avant extension gouvernée du rollout
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
- architecture complete toujours observable et non contournable

## 11.6 Gate live-complete
Conditions :
- LIGHT déjà stable
- A/B validés
- C et D apportent alpha ou diversification
- K_eff augmente
- CE portefeuille augmente ou ne se dégrade pas excessivement
- infra toujours stable
- aucune inflation de complexité UI ou de veto non gouvernée

---

# 12. Registre des risques canoniques et angles morts

Chaque angle mort critique doit etre documente avec risque, impact, garde-fou
et signal de surveillance.

- duplication A vs C : faux nouveau moteur ; impact = sur-activation et faux
  multi-edge ; garde-fou = test de non-duplication, budget cout ; signal =
  correlation inter-moteurs, gain marginal
- duplication A vs D : re-entry redondant ; impact = concentration cachee ;
  garde-fou = budget correlation et historique trade-aware ; signal =
  exposition marginale, CE marginale
- B contre vraie cassure : mean reversion toxique ; impact = pertes de regime ;
  garde-fou = blockers regime/cout ; signal = drawdown par regime
- C trop tardif : breakout deja trop cher ; impact = edge detruit ; garde-fou
  = gate cout/slippage ; signal = cout de capture, faux breakout
- D en surconcentration : impact = portefeuille fragilise ; garde-fou =
  cap par paire/moteur ; signal = concentration et drawdown conditionnel
- illusion de diversite d'edge : impact = faux sentiment de securite ; garde-
  fou = K_eff, contribution risque ; signal = facteur BTC cache, correlation
- latence / backlog / stale : impact = decisions obsoletes ; garde-fou =
  charge streaming, stale gates ; signal = lambda/mu_s, backlog, stale rate
- desalignement etat local / exchange : impact = execution incoherente ; garde-
  fou = reconciliation stricte ; signal = ecarts d'etat et recovery failures
- inflation de veto ou de complexite UI : impact = sterilisation ou alertes
  noyees ; garde-fou = UI gouvernee ; signal = sterilization rate, alert fatigue
- contournement operateur : impact = rupture de gouvernance ; garde-fou = pas
  d'override non journalise ; signal = journal d'actions admin
- derive documentaire : impact = contradiction architecture/rollout/runtime ;
  garde-fou = source canonique unique ; signal = ecarts master/build/gates

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
- état canonique : `profil=LIGHT`, `runtime_mode=SHADOW`

Go :
- décisions reproductibles
- DTR complets
- coûts plausibles
- infra stable

---

## Build-12 — Micro-live Light
Objectif :
- valider exécution réelle et coûts
- état canonique : `profil=LIGHT`, `runtime_mode=MICRO_LIVE`

Go :
- coûts réels acceptables
- fills/reconciliation stables
- CE mesurée
- stale/backlog maîtrisés

---

## Build-13 — Live-Light
Objectif :
- première production réelle
- état canonique : `profil=LIGHT`, `runtime_mode=LIVE`

Go :
- fréquence utile > V5.2
- edge net > 0 ou crédible
- CE > V5.2
- composants promus stables
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
- **activer les enrichissements à 100% en Shadow** (`SHADOW_ENABLED`)
- pleinement utilisés dans les décisions Shadow, tracés, comparés, auditables
- promotion live non automatique : soumis au verdict post-Shadow
- jamais un moteur autonome
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
- **HARD : Complete a tradé en shadow 30 jours consécutifs minimum**
- **HARD : non-régression Light démontrée pendant ces 30 jours**
- **HARD : rapport comparatif Light vs Complete produit et approuvé**

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

---

# 17. Build-14 — Conditions d'activation et de promotion

Build-14 est **activé à 100% en Shadow** (`SHADOW_ENABLED`) :
- pleinement utilisé dans les décisions Shadow
- ses outputs sont tracés, comparés, auditables
- il influence activement le scoring, le risk et le portefeuille en Shadow

Build-14 reste **non-promu en Live** tant que :
- le verdict post-Shadow n'a pas été rendu
- **HARD : 30 jours de Shadow complet consécutifs minimum**
- les gates Shadow et Micro-live ne sont pas vertes
- aucun enabler Build-14 n'a démontré de valeur pendant le Shadow

Build-14 ne doit **jamais** :
- être un **hard blocker central** qui modifie le flux de décision Light en live sans verdict
- être une **activation implicite de Complete**
- échapper à la **non-régression Light obligatoire** : tout enrichissement Build-14 qui dégrade les métriques Light est désactivé

Hard State : `CODED` → `SHADOW_ENABLED` → verdict → `SHADOW_VALIDATED` ou `DORMANT`

Les enablers issus des audits tiers absorbés dans Build-14 (LOB deep filter, OBI, Hurst enrichi, anti-spoofing) suivent exactement ces mêmes règles.

**HARD STATEMENT** : Même si tout le code Complete est implémenté, testé et prêt, la promotion de Complete vers le live exige 30 jours supplémentaires de shadow Complete après la stabilisation de Light en live. L'activation intégrale en Shadow est un essai structuré, pas une promotion déguisée.

---

# 18. Protocole d'intégration des audits

Le pass documentaire d'intégration des audits suit ce protocole :

1. **Freeze documentaire** : gel du canon avant modifications
2. **Triage des findings** : classification NOW_P0 / NOW_LIGHT / NEXT_BUILD14 / RESEARCH_LOCAL / REJECT
3. **Patch des builds P0** : injection des invariants dans les specs concernées
4. **Réalignement docs → code** : vérification que le code respecte les docs patchées
5. **Interdiction de promotion implicite** : aucun build ne change de statut par le seul fait du patch documentaire
6. **Requalification** : les builds 1→14 déjà codés sont requalifiés selon le nouveau corpus patché

---

## Fin du master final unique
