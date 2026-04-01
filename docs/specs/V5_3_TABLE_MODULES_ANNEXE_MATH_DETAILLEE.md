# V5.3 — TABLE DÉTAILLÉE DES MODULES + ANNEXE MATHÉMATIQUE PAR MODULE
## Spécification développeur prod-safe
### Complément canonique subordonné au `V5_3_MASTER_FINAL_UNIQUE.md`
### Architecture cible complète + profils Light / Complete
### Sans code

---

# 0. Objet du document

Ce document transforme le master officiel unique en **spécification développeur détaillée**.

Il fournit pour chaque module :

- responsabilité exacte
- sous-composants
- inputs
- outputs
- état interne
- dépendances autorisées
- formules et métriques mathématiques utiles
- logs obligatoires
- tests obligatoires
- activation Light / Complete
- priorité d’implémentation
- dérives possibles
- interdits de conception

## 0.1 Règle d’alignement doctrinal

Cette annexe mathématique :

- est **subordonnée** au `V5_3_MASTER_FINAL_UNIQUE.md`
- décrit les briques enrichies Build-14 comme **pleinement actives en Shadow** (`SHADOW_ENABLED`)
- décrit les moteurs C/D comme **activés et observés en Shadow** dans la phase de vérité système complète
- ne donne **jamais** de droit de promotion live : seul le verdict post-Shadow peut conduire à `SHADOW_VALIDATED`, `DORMANT` puis à une promotion explicite
- ne peut jamais servir de source concurrente pour redéfinir les Hard States, les gates de promotion ou la hiérarchie documentaire

Le but n’est pas d’empiler des idées.  
Le but est de rendre la V5.3 **implémentable sans ambiguïté**.

---

# 1. Règles de lecture

## 1.1 Tags d’activation

- **NOW** : à implémenter pour V5.3 Light
- **NEXT** : à implémenter pour V5.3 Complete
- **RESEARCH** : documenté, non requis en production initiale
- **FORBIDDEN** : ne pas implémenter pour V5.3

## 1.2 Profils

- **Light** = 6 paires, moteurs A + B
- **Complete** = 12 paires, moteurs A + B + C + D

## 1.3 Convention mathématique

Le document n’utilise que des formules qui ont un rôle opérationnel direct :

- décision
- coût
- sizing
- risque
- fréquence utile
- capital efficiency
- santé infra
- corrélation réelle

---

# 2. Tableau maître des modules

| Module | Priorité | Light | Complete | Rôle central | Danger majeur si mal conçu |
|---|---:|---:|---:|---|---|
| data_engine | P0 | oui | oui | ingestion et cohérence temporelle | état incohérent, backlog, stale decisions |
| data_quality_engine | P0 | oui | oui | santé data et suspension propre | faux signaux sur données invalides |
| microstructure_engine | P1 | minimal | enrichi | signaux carnet/flux | faux edge, spoofing, surcharge CPU |
| regime_engine | P1 | simple | enrichi | filtrage contextuel | sur-fit régimes, gating instable |
| signal_engine | P0 | A+B | A+B+C+D | génération de setups | duplication d’edge, bruit inutile |
| scoring_engine | P0 | oui | oui | hard/soft/rank | re-création du sur-filtrage |
| risk_engine | P0 | oui | oui | budget perte, sizing, corrélation | drawdown, concentration cachée |
| execution_engine | P0 | oui | oui | ordres, fills, coûts réels | slippage non mesuré, désalignement état/compte |
| portfolio_engine | P0 | minimal | complet | arbitrage des opportunités simultanées | portefeuille mono-factoriel caché |
| monitoring_engine | P0 | oui | oui | métriques live, infra, alertes | aveuglement opérationnel |
| meta_engine | P0 | minimal utile | enrichi | DTR, CRA, BEE prudent | logs incomplets, faux diagnostic |
| dependency_architecture | P0 | oui | oui | interfaces, tests, DAG, build | dette technique irréversible |
| ui_console | P1 | oui | oui | pilotage contrôlé | activation sauvage, contournement des garde-fous |

---

# 3. MODULE 1 — DATA_ENGINE

## 3.1 Mission

Garantir une ingestion de marché cohérente, stable, horodatée, reconnectable et exploitable par tous les autres modules.

## 3.2 Sous-composants

### 3.2.1 websocket_gateway
Rôle :
- ouvrir les streams
- gérer heartbeats
- détecter les coupures
- reconnecter

Inputs :
- abonnements par paire
- configuration des flux

Outputs :
- événements bruts normalisés par type

État interne :
- connexions actives
- statut heartbeat
- compteur reconnects
- backlog brut

Math utile :
- charge flux :
\[
\lambda_{tot} = \sum_{j=1}^{M}\sum_{f=1}^{F}\lambda_{j,f}
\]

- utilisation service :
\[
\rho_q = \frac{\lambda_{tot}}{\mu_s}
\]

- stabilité minimale :
\[
\lambda_{tot} < \mu_s
\]

Logs obligatoires :
- connect / disconnect
- reconnect count
- heartbeat misses
- stream lag
- backlog size

Tests obligatoires :
- perte de connexion
- reconnexion
- duplication d’événements
- ordre d’arrivée désordonné
- pic de flux

Dérives à éviter :
- écouter trop de streams “par confort”
- reconstruire le temps réel par REST
- ignorer l’ordre des événements
- ne pas mesurer le backlog

Verdict :
- Light : NOW
- Complete : NOW

---

### 3.2.2 rest_bootstrap
Rôle :
- bootstrap initial
- recovery contrôlé
- gap fill prudent

Inputs :
- paire
- type de resync

Outputs :
- snapshot cohérent

État interne :
- dernier bootstrap
- quotas API
- erreurs REST

Math utile :
- âge snapshot :
\[
\Delta_{snap} = t_{now} - t_{snapshot}
\]

- tolérance max :
\[
\Delta_{snap} \le \Delta_{snap,max}
\]

Dérives à éviter :
- utiliser REST comme substitut au stream
- gap-fill massif silencieux
- mélanger snapshot ancien et flux récent sans contrôle

Verdict :
- Light : NOW
- Complete : NOW

---

### 3.2.3 event_normalizer
Rôle :
- homogénéiser les événements
- imposer formats
- enrichir timestamps

Inputs :
- raw trades
- raw depth
- raw kline

Outputs :
- événements typés

État :
- mapping des schémas
- versioning des formats

Math utile :
- latence événement :
\[
Lat_u = t_{recv,u} - t_{exch,u}
\]

- dérive de temps :
\[
Drift_u = t_{local} - t_{reference}
\]

Dérives à éviter :
- parser au fil de l’eau sans schéma versionné
- timestamp local unique sans exchange time
- format variable selon paire

Verdict :
- Light : NOW
- Complete : NOW

---

### 3.2.4 internal_router
Rôle :
- distribuer les événements aux modules consommateurs

Inputs :
- événements normalisés

Outputs :
- files par consommateur

État :
- queues par module
- priorités

Math utile :
- taux arrivée par queue :
\[
\lambda_m
\]

- capacité de service module :
\[
\mu_m
\]

- backlog :
\[
B_m(t+1)=B_m(t)+A_m(t)-S_m(t)
\]

Dérives à éviter :
- file unique géante
- priorité équivalente entre exécution et analytics
- pas de backpressure

Verdict :
- Light : NOW
- Complete : NOW

---

## 3.3 Invariants prod-safe du data_engine

- aucun consommateur non critique ne doit bloquer l’ingestion
- exécution et risk ont priorité sur analytics
- toute paire peut être suspendue indépendamment
- aucune décision ne doit être prise sur un événement non horodaté proprement

## 3.4 Dépendances autorisées

- dependency_architecture
- monitoring_engine
- data_quality_engine

## 3.5 Dépendances interdites

- signal_engine
- scoring_engine
- risk_engine
- execution_engine ne doivent pas être importés ici

---

# 4. MODULE 2 — DATA_QUALITY_ENGINE

## 4.1 Mission

Décider si la donnée est suffisamment saine pour autoriser :
- calcul de feature
- scoring
- prise de décision
- exécution

## 4.2 Sous-composants

### 4.2.1 freshness_checker
Rôle :
- mesurer l’âge de la dernière donnée utile

Math utile :
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

Danger si mal conçu :
- signaux pris sur données mortes
- auto-stérilisation si seuils trop agressifs

Verdict :
- Light : NOW
- Complete : NOW

---

### 4.2.2 consistency_checker
Rôle :
- vérifier cohérence entre flux
- vérifier séquences impossibles
- détecter trous ou duplications

Métriques :
- duplicate rate
- gap rate
- out-of-order rate

Formule utile :
\[
ConsistencyScore = 1 - (w_1 Gaps + w_2 Duplicates + w_3 Disorder)
\]

Dérives :
- considérer “connexion vivante” comme qualité suffisante
- tolérer trop de disorder silencieux

Verdict :
- Light : NOW
- Complete : NOW

---

### 4.2.3 pair_health_scorer
Rôle :
- produire un score santé exploitable

Score :
\[
H_j = w_Q Q_j + w_L L_j + w_C C_j + w_R R_j
\]

Suspension si :
\[
H_j < H_{min}
\]

Dérives :
- score opaque impossible à diagnostiquer
- pas de raison explicite de suspension
- santé globale sans santé par paire

Verdict :
- Light : NOW
- Complete : NOW

---

## 4.3 Logs obligatoires

- stale events
- hard stale blocks
- score santé par paire
- raisons de suspension
- raisons de reprise

## 4.4 Tests obligatoires

- flux figé
- flux ralenti
- flux incohérent
- reprise après suspension
- contamination inter-paires interdite

---

# 5. MODULE 3 — MICROSTRUCTURE_ENGINE

## 5.1 Mission

Produire des signaux microstructure exploitables sans tomber dans le piège du faux edge.

## 5.2 Sous-composants

### 5.2.1 ofi_calculator
Formule :
\[
OFI_t = V_t^{buy} - V_t^{sell}
\]

Version normalisée :
\[
OFI_t^{norm} = \frac{V_t^{buy}-V_t^{sell}}{V_t^{buy}+V_t^{sell}}
\]

Interprétation :
pression nette du flux

Hypothèses :
- les trades agressifs reflètent une vraie pression
- classification buy/sell correcte

Dangers :
- faible volume
- prints erronés
- spoofing non vu
- surpondération d’un spike

Verdict :
- Light : NEXT minimal si coût CPU OK
- Complete : NEXT enrichi

---

### 5.2.2 book_imbalance
Formule :
\[
BI_t = \frac{Q_t^{bid}-Q_t^{ask}}{Q_t^{bid}+Q_t^{ask}}
\]

Interprétation :
inclinaison instantanée du carnet

Danger :
le carnet ment facilement en crypto

Règle :
jamais utiliser BI seul pour une décision.

Verdict :
- Light : RESEARCH/minimal si utile
- Complete : NEXT

---

### 5.2.3 microprice_estimator
Formule :
\[
MP_t = \frac{P_t^{ask}Q_t^{bid}+P_t^{bid}Q_t^{ask}}{Q_t^{bid}+Q_t^{ask}}
\]

Écart :
\[
\Delta MP_t = \frac{MP_t - Mid_t}{Mid_t}
\]

Danger :
fragile si volumes top-of-book artificiels

Verdict :
- Light : RESEARCH
- Complete : NEXT

---

### 5.2.4 persistence_filter
Formule :
\[
\bar{M}_{t,w} = \frac{1}{w}\sum_{u=t-w+1}^{t} M_u
\]

But :
exiger une persistance minimale du signal

Danger :
fenêtre trop courte = bruit
fenêtre trop longue = retard

Verdict :
- Light : NOW si microstructure utilisée
- Complete : NOW

---

## 5.3 Invariants

- aucune feature microstructure ne doit être utilisée seule
- toute feature doit avoir :
  - persistance
  - volume réel
  - interprétation économique
- les features décoratives doivent être coupables de suppression si coût CPU > utilité

## 5.4 Dérives interdites

- transformer le microstructure engine en mini-HFT
- brancher 15 features carnet sans budget CPU
- croire que plus de features = plus d’edge

---

# 6. MODULE 4 — REGIME_ENGINE

## 6.1 Mission

Segmenter le contexte de marché en régimes économiquement utiles.

## 6.2 Sous-composants

### 6.2.1 regime_classifier_simple
Inputs :
- volatilité locale
- tendance locale
- range quality
- direction macro récente

Outputs :
- régime simple :
  - trend
  - range
  - stressed

Math utile :
\[
\mu_s = \mathbb{E}[r \mid régime=s]
\]
\[
\sigma_s^2 = \mathbb{V}[r \mid régime=s]
\]

Verdict :
- Light : NOW

---

### 6.2.2 hmm_regime_layer
Usage :
- seulement si stabilité démontrée

Math utile :
\[
\mathbb{P}(z_t=s \mid y_{1:t})
\]

Danger :
- sur-fit
- instabilité
- gating excessif

Verdict :
- Light : RESEARCH / FORBIDDEN si non stable
- Complete : NEXT

---

### 6.2.3 regime_confidence
But :
ne pas utiliser un régime ambigu comme hard block

Score :
\[
Conf_{reg} = \max_s \mathbb{P}(z_t=s \mid data)
\]

Dérive :
transformer toute ambiguïté de régime en veto.

Verdict :
- Light : NOW simple
- Complete : NOW enrichi

---

## 6.3 Dérives interdites

- trop d’états de régime
- régime “intelligent” sans utilité PnL
- changement de régime utilisé comme alibi de sur-filtrage

---

# 7. MODULE 5 — SIGNAL_ENGINE

## 7.1 Mission

Transformer données + contexte en opportunités candidates.

## 7.2 Sous-composants par moteur

### 7.2.1 moteur_A_premium_trend
But :
capturer les setups de plus haute conviction

Math utile :
\[
\mu_{A,j,s} = \mathbb{E}[r \mid moteur=A, paire=j, régime=s]
\]

Signaux typiques :
- structure directionnelle
- alignement contexte
- coût acceptable

Dérives :
- sur-rareté
- trop d’exigences simultanées
- duplication avec breakout

Verdict :
- Light : NOW
- Complete : NOW

---

### 7.2.2 moteur_B_mean_reversion
Signal central :
\[
z_t = \frac{p_t - \mu_t^{loc}}{\sigma_t^{loc}}
\]

Entrée si :
\[
|z_t| > z^\star
\]

Danger :
- mean reversion dans un marché qui casse
- faux retour vers moyenne
- coût qui annule le petit edge

Verdict :
- Light : NOW
- Complete : NOW

---

### 7.2.3 moteur_C_breakout
Signal central :
\[
p_t > p_{range,max} + \delta
\]

avec confirmation qualité

Danger :
- faux breakout
- copie déguisée du moteur A
- coût trop élevé dans l’expansion

Verdict :
- Light : FORBIDDEN
- Complete : NEXT

---

### 7.2.4 moteur_D_reentry
But :
réengager un trade après structure validée

Danger :
- doublon conceptuel du moteur A
- revenge trading automatisé
- surconcentration

Verdict :
- Light : FORBIDDEN
- Complete : NEXT

---

## 7.3 Invariant global du signal_engine

Chaque moteur doit justifier :
- une fréquence attendue
- un edge net attendu
- un coût attendu
- une duration attendue
- une compatibilité par paire
- une vraie différence par rapport aux autres moteurs

---

# 8. MODULE 6 — SCORING_ENGINE

## 8.1 Mission

Réconcilier signal, coût, contexte et prudence sans recréer un système à veto excessif.

## 8.2 Sous-composants

### 8.2.1 raw_score_builder
Formule générique :
\[
S_i^{raw} = \sum_{m=1}^{M_f}\alpha_m F_{i,m}
\]

Danger :
- score opaque
- coefficients arbitraires
- mélange non justifié de features incompatibles

Verdict :
- Light : NOW

---

### 8.2.2 penalty_aggregator
Formule :
\[
Pen_i = \sum_{\ell=1}^{L} pen_{i,\ell}
\]

Score final :
\[
S_i = S_i^{raw} - Pen_i
\]

Danger :
- soft penalties qui redeviennent des veto cachés
- addition de pénalités corrélées

Verdict :
- Light : NOW

---

### 8.2.3 hard_block_gate
Décision :
\[
A_i = \mathbf{1}_{HB_i=0}\mathbf{1}_{S_i \ge \tau}
\]

Danger :
- trop de hard blockers
- soft -> hard par paresse de design

Verdict :
- Light : NOW

---

### 8.2.4 ranking_router
But :
si plusieurs trades sont valides, choisir les meilleurs

Métriques :
- score net
- coût attendu
- CE attendue
- impact corrélation

Verdict :
- Light : NOW minimal
- Complete : NOW enrichi

---

## 8.3 Dérives interdites

- hard blockers métiers non fatals
- score sans interprétabilité minimum
- seuil unique sans lien avec coût réel
- ranking qui ignore portefeuille

---

# 9. MODULE 7 — RISK_ENGINE

## 9.1 Mission

Protéger le capital contre :
- concentration
- drawdown
- faux diversification
- sizing trop agressif
- budgets dépassés

## 9.2 Sous-composants

### 9.2.1 exposure_budgeter
Contrainte :
\[
GrossExp = \sum_i x_i \le X_{gross,max}
\]

Verdict :
- Light : NOW

---

### 9.2.2 loss_budgeter
Budget perte :
\[
LossBudget = \sum_i L_i \le LB_{max}
\]

Danger :
- sizing par exposition sans sizing par perte
- stops non crédibles

Verdict :
- Light : NOW

---

### 9.2.3 btc_factor_guard
Modèle :
\[
r_j = \alpha_j + \beta_j r_{BTC} + \epsilon_j
\]
\[
\Beta_{port} = \sum_j w_j \beta_j
\]

Contrainte :
\[
|\Beta_{port}| \le B_{max}
\]

Verdict :
- Light : NOW

---

### 9.2.4 correlation_cluster_guard
Contrainte :
\[
\sum_{i \in cluster\ c} x_i \le X_{cluster,c}^{max}
\]

Danger :
- 6 positions “diversifiées” qui sont en fait le même pari

Verdict :
- Light : NOW simple
- Complete : NOW enrichi

---

### 9.2.5 kelly_guard_prudent
Kelly naïf :
\[
f^\star \approx \frac{\mu}{\sigma^2}
\]

Version autorisée :
\[
f_{mod} = \kappa \frac{\mu_{net}}{\sigma^2 + \lambda_{tail} + \lambda_{corr} + \lambda_{model}}
\]

Danger :
- Kelly non réduit = trop agressif
- faux \(\mu\) = sizing suicidaire

Verdict :
- Light : RESEARCH / FORBIDDEN si non borné
- Complete : NEXT très prudent

---

## 9.3 Dérives interdites

- sizing théorique sans cap dur
- risque mesuré seulement par notional
- corrélation ignorée
- drawdown traité comme métrique secondaire

---

# 10. MODULE 8 — EXECUTION_ENGINE

## 10.1 Mission

Transformer une décision autorisée en exécution réelle traçable, réconciliable et mesurable en coût.

## 10.2 Sous-composants

### 10.2.1 order_decider
Choisit :
- market
- limit
- no-trade

Critère central :
\[
\mathbb{E}[g_i] - \mathbb{E}[c_i] > \delta_{safe}
\]

Danger :
- exécuter juste parce qu’un signal existe
- ignorer coût implicite

Verdict :
- Light : NOW

---

### 10.2.2 fill_tracker
But :
suivre ack, partial fills, fill final, reste, annulations

Logs :
- fill ratio
- partial fill count
- avg fill latency

Danger :
- portefeuille local désaligné du compte réel

Verdict :
- Light : NOW

---

### 10.2.3 execution_cost_meter
Mesure :
\[
ELW_t = \frac{|P_t^{exec} - Mid_t|}{Mid_t}
\]

et coût total :

\[
c_i = f_i + c_i^{impl} + AS_i + PF_i
\]

Danger :
- coût mesuré seulement par frais exchange

Verdict :
- Light : NOW

---

### 10.2.4 reconciliation_layer
But :
réconcilier :
- compte
- positions
- ordres
- fills
- ledger local

Dérives :
- confiance aveugle dans l’état local
- absence de recovery après crash

Verdict :
- Light : NOW

---

# 11. MODULE 9 — PORTFOLIO_ENGINE

## 11.1 Mission

Arbitrer les opportunités simultanées dans une logique de portefeuille, pas de signaux isolés.

## 11.2 Sous-composants

### 11.2.1 opportunity_selector
Rôle :
choisir quels trades passent quand plusieurs sont simultanément valides

Critère :
- score
- coût
- CE attendue
- moteur
- paire
- corrélation

Verdict :
- Light : NOW

---

### 11.2.2 allocation_router
But :
allouer le capital entre paires et moteurs

Forme simple :
\[
x_i = x_{base}\,m_i\,\psi(S_i)
\]

Contrainte :
\[
\sum_i x_i \le X_{gross,max}
\]

Verdict :
- Light : NOW

---

### 11.2.3 risk_contribution_monitor
Variance portefeuille :
\[
Var(R_p)=w^\top \Sigma w
\]

Contribution marginale :
\[
MRC_j = \frac{(\Sigma w)_j}{\sqrt{w^\top \Sigma w}}
\]

Danger :
- une petite paire apporte beaucoup trop de risque réel

Verdict :
- Light : NEXT minimal
- Complete : NOW enrichi

---

### 11.2.4 effective_edge_diversity
Approximation :
\[
K_{eff}^{spec} = \frac{(\operatorname{tr}\mathcal{R})^2}{\operatorname{tr}(\mathcal{R}^2)}
\]

Danger :
- croire à 4 moteurs et 12 paires comme s’ils étaient indépendants

Verdict :
- Light : NEXT simple
- Complete : NEXT/RESEARCH utile

---

# 12. MODULE 10 — MONITORING_ENGINE

## 12.1 Mission

Rendre visibles les états économiques, de risque et d’infrastructure.

## 12.2 Sous-composants

### 12.2.1 metrics_collector
Collecte :
- PnL
- CE
- drawdown
- beta BTC
- queue lag
- pair health
- cost metrics

Verdict :
- Light : NOW

---

### 12.2.2 alert_manager
Alertes :
- stale data
- pair suspended
- DTR loss
- queue overload
- cost spike
- correlation breach

Verdict :
- Light : NOW

---

### 12.2.3 health_dashboard_backend
Expose :
- portefeuille
- moteurs
- paires
- infra

Verdict :
- Light : NOW

---

## 12.3 Dérives interdites

- dashboards décoratifs
- métriques non actionnables
- omission des métriques de coût et CE
- monitoring sans backlog / queue / reconnects

---

# 13. MODULE 11 — META_ENGINE

## 13.1 Mission

Donner la couche d’analyse économique et causale minimale nécessaire pour ne pas piloter à l’aveugle.

## 13.2 Sous-composants

### 13.2.1 dtr_core
Minimum à logger :
\[
DTR_i = (time_i, paire_i, moteur_i, S_i, HB_i, penalties_i, m_i, A_i, x_i, c_i, r_i)
\]

Exigence :
- aucune perte silencieuse

Danger :
- diagnostic faux précisément en stress

Verdict :
- Light : NOW

---

### 13.2.2 cra_monitor
But :
détecter :
\[
m_i < m_{phantom}
\]
ou
\[
CE_i < CE_{min}
\]

Danger :
- activité apparente sans valeur économique

Verdict :
- Light : NOW

---

### 13.2.3 amd_monitor
But :
détecter les pertes “all clear”

Danger :
- prendre une simple variance pour un angle mort
- besoin de lecture conditionnelle par régime / moteur / paire

Verdict :
- Light : NEXT prudent
- Complete : NEXT

---

### 13.2.4 edge_tracker_prudent
Objet :
\[
\mu_{k,j,s}^{net}, \quad \sigma_{k,j,s}
\]

Usage :
- gouvernance
- pas oracle

Danger :
- cellules trop petites
- posterior pris comme vérité

Verdict :
- Light : NOW minimal
- Complete : NEXT enrichi

---

### 13.2.5 break_even_dashboard
But :
suivre le coût réel et le break-even prudent

Verdict :
- Light : NOW

---

# 14. MODULE 12 — DEPENDENCY_ARCHITECTURE

## 14.1 Mission

Empêcher la dette technique et la dérive d’architecture.

## 14.2 Sous-composants

### 14.2.1 interface_contracts
Rôle :
- inputs / outputs explicites
- types métiers stables

Dérive :
- dicts libres partout
- formats implicites

Verdict :
- Light : NOW

---

### 14.2.2 manifest_registry
Rôle :
- source d’inventaire modules
- versions
- ownership
- build order

Verdict :
- Light : NOW

---

### 14.2.3 dag_validator
Rôle :
- interdire les dépendances interdites
- prévenir les cycles

Dérive :
- dépendances runtime cachées non testées

Verdict :
- Light : NOW

---

### 14.2.4 contract_test_suite
Rôle :
- garantir les shapes, invariants, bornes

Verdict :
- Light : NOW

---

### 14.2.5 smoke_bootstrap_recovery
Rôle :
- vérifier démarrage clean
- restart
- recovery après panne

Danger :
- système “beau sur papier”, cassé après incident

Verdict :
- Light : NOW

---

# 15. MODULE 13 — UI_CONSOLE

## 15.1 Mission

Permettre le pilotage contrôlé du système sans ouvrir de portes dangereuses.

## 15.2 Sous-composants

### 15.2.1 profile_selector
Choix autorisés :
- Light
- Complete

Interdit :
- composer un profil custom non validé

Verdict :
- Light : NOW

---

### 15.2.2 deployment_state_panel
États :
- SHADOW
- MICRO-LIVE
- LIVE-LIGHT
- LIVE-COMPLETE
- DEGRADED
- HALTED

Verdict :
- Light : NOW

---

### 15.2.3 pair_activation_panel
Rôle :
- activer / suspendre les paires autorisées par le profil

Interdit :
- dépasser le max profil
- réactiver une paire hard-blocked sans audit

Verdict :
- Light : NOW

---

### 15.2.4 engine_status_panel
Rôle :
- afficher moteurs autorisés, état, santé, perf

Verdict :
- Light : NOW

---

### 15.2.5 risk_override_panel
Principe :
- overrides extrêmement limités
- journalisés
- révocables
- jamais de contournement des hard guards fondamentaux

Verdict :
- Light : NEXT minimal uniquement si justifié

---

# 16. Table des dérives structurelles à ne pas faire

| Dérive | Pourquoi c’est dangereux | Module concerné |
|---|---|---|
| coder 12 paires + 4 moteurs d’un coup | dette de debug et faux diagnostic | tous |
| utiliser plusieurs documents actifs | contradictions et implémentation divergente | gouvernance |
| confondre signal et exécution | edge brut détruit par coût | signal / execution |
| confondre soft penalty et hard block | recrée le sur-filtrage | scoring |
| utiliser REST comme temps réel | état faux et latence cachée | data |
| ignorer le facteur BTC | fausse diversification | risk / portfolio |
| croire qu’un moteur de plus = edge de plus | faux multi-edge | signal / portfolio |
| ajouter 20 features microstructure | surcharge CPU sans alpha prouvé | microstructure |
| ne pas logger les coûts réels | impossibilité de mesurer l’edge net | execution / meta |
| utiliser Kelly naïf | sur-sizing destructeur | risk |
| laisser la UI contourner les garde-fous | prod non maîtrisée | ui |
| faire des modules sans tests de contrat | bugs silencieux de pipeline | dependency_architecture |
| perdre des DTR silencieusement | analytics faux en stress | meta |
| trop de régimes | gating instable et sur-fit | regime |
| considérer la fréquence brute | illusion de progrès | portfolio / meta |

---

# 17. Table mathématique de référence par module

| Module | Quantités à suivre | Formules minimales |
|---|---|---|
| data_engine | \(\lambda_{tot}, \mu_s, \rho_q, W_q\) | \(\rho_q=\lambda/\mu_s\), \(W_q=\lambda/(\mu_s(\mu_s-\lambda))\) |
| data_quality | \(\Delta_i, H_j\) | \(pen_{stale}(\Delta_i)\), \(H_j=w_QQ_j+w_LL_j+w_CC_j+w_RR_j\) |
| microstructure | \(OFI, BI, MP, \bar{M}\) | \(OFI_t, BI_t, MP_t, \bar{M}_{t,w}\) |
| regime | \(\mu_s, \sigma_s^2, Conf_{reg}\) | \(\mu_s=\mathbb{E}[r|s]\) |
| signal | \(\mu_{k,j,s}\) | \(\mu_{k,j,s}=\mathbb{E}[r|k,j,s]\) |
| scoring | \(S_i^{raw}, Pen_i, S_i, A_i\) | \(S_i=S_i^{raw}-Pen_i\), \(A_i=\mathbf{1}_{HB_i=0}\mathbf{1}_{S_i\ge\tau}\) |
| risk | \(GrossExp, LossBudget, \Beta_{port}\) | \(LossBudget=\sum L_i\), \(\Beta_{port}=\sum w_j\beta_j\) |
| execution | \(ELW, c_i, AS_i\) | \(c_i=f_i+c_i^{impl}+AS_i+PF_i\) |
| portfolio | \(Var(R_p), MRC_j, K_{eff}\) | \(Var(R_p)=w^\top\Sigma w\) |
| monitoring | PnL, CE, drawdown | \(CE=\frac{PnL}{capital\times temps}\) |
| meta | \(DTR, SterilRate, \mu_{net}\) | \(SterilRate=\frac{\sum \mathbf{1}_{CE_i<CE_{min}}\mathbf{1}_{A_i=1}}{\sum A_i}\) |
| dependency_architecture | N/A | invariants, pas d’équation centrale |
| ui_console | N/A | pas de math centrale, contraintes d’état |

---

# 18. Priorités canoniques d’implémentation

## P0 absolu
- data_engine
- data_quality_engine
- scoring_engine
- risk_engine
- execution_engine
- portfolio_engine minimal
- monitoring_engine
- meta_engine minimal
- dependency_architecture

## P1
- microstructure minimal utile
- regime simple
- moteur B bien calibré
- UI complète de supervision
- moteurs C / D après validation Light

## P2
- HMM enrichi
- Ledoit-Wolf
- Kelly modifié
- analytics avancés
- métriques effectives \(K_{eff}\) enrichies

## FORBIDDEN V5.3
- RL live
- POMDP live
- stopping optimal sophistiqué live
- sophistication math sans gain direct en CE / coût / fréquence utile

---

# 19. Critères de complétude de ce document

Ce document est considéré exploitable si le développeur peut, pour chaque module :
- connaître son rôle
- savoir quand le coder
- savoir avec quoi il interagit
- savoir quelles métriques il doit produire
- savoir ce qu’il ne faut surtout pas faire

---

# 20. Décision finale

La V5.3 peut maintenant être développée de façon prod-safe **à condition** de respecter ce document comme table détaillée unique des modules, et de ne pas ré-ouvrir le scope par improvisation.

Le principe de travail correct devient :

1. **master canonique**  
2. **table détaillée des modules**  
3. **tests / invariants**  
4. **développement module par module**  
5. **audit croisé ChatGPT / Claude**  
6. **merge seulement après gates**

---

## Fin du document
