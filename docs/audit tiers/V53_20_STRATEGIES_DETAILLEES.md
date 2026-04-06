# V5.3 — 20 STRATÉGIES DÉTAILLÉES D'ENRICHISSEMENT
## Date : 2026-04-03
## Perspective : PhD — Dev / IA-ML / Trader / Quant / Architecte / Math / Algèbre / Fintech
## Statut : PLAN STRATÉGIQUE ACTIONNABLE

---

# 0. Cadre de lecture

Chaque stratégie est décrite selon une grille unifiée :

- **Nom** et identifiant
- **Angle disciplinaire** dominant
- **Problème résolu**
- **Couche V5.3 ciblée** (où la logique doit vivre)
- **Formulation mathématique** (si applicable)
- **Implémentation** (modules touchés, inputs/outputs)
- **Preuve requise** (replay, shadow, métriques de succès)
- **Risque et anti-patterns**
- **Critère d'abandon** (quand arrêter)
- **Lot backlog** associé

---

# STRATÉGIE 1 — CONCEPT DRIFT DETECTOR PAR MOTEUR

## Angle : IA-ML / Quant

## Problème
Les moteurs A/B/C/D sont calibrés sur des distributions passées. Si la distribution des rendements change (non-stationnarité), le moteur continue d'opérer sur une hypothèse invalide sans le savoir.

## Couche ciblée
`meta_learning` + `monitoring`

## Formulation mathématique
Utiliser un test de Page-Hinkley (PH) séquentiel sur le rendement net par moteur :

$$g_t = \sum_{i=1}^{t}(r_i - \bar{r} - \delta)$$
$$G_t = \min_{1 \le k \le t} g_k$$

Alarme drift si $g_t - G_t > \lambda_{PH}$, où $\delta$ est la tolérance de dérive minimale et $\lambda_{PH}$ est le seuil de détection.

Alternative : ADWIN (Adaptive Windowing) pour une fenêtre adaptative sans paramètre de seuil fixe.

## Implémentation
- Ajouter `drift_detector.py` dans `meta_learning/diagnostics/`
- Input : séquence de $r_i^{net}$ par moteur × paire
- Output : `DriftAlert(engine_id, pair_id, drift_score, p_value, window_size)`
- Brancher la sortie dans `monitoring/alert_manager`
- Projeter dans le dashboard technique : panneau "Model Health"

## Preuve requise
- Replay sur données historiques avec changements de régime connus (ex : crash mars 2020, rally Q4 2024)
- Vérifier que le détecteur alarme AVANT que le PnL se dégrade significativement
- Taux de faux positifs < 5% sur régime stable

## Risque
- Faux positifs trop fréquents → paralysie du système
- Paramètres ($\delta$, $\lambda$) mal calibrés → détection trop tardive ou trop agressive

## Anti-pattern
Ne PAS utiliser le drift comme hard blocker automatique. Utiliser comme signal d'alerte + réduction de sizing (soft penalty).

## Critère d'abandon
Si après calibration sur 6 mois de données, le détecteur ne distingue pas mieux qu'un simple rolling Sharpe, abandonner.

## Lot backlog : 0 + 1

---

# STRATÉGIE 2 — TAIL RISK BUDGETING VIA EVT

## Angle : Math / Quant

## Problème
Les seuils de drawdown (2% warning, 4% observe) sont arbitraires. Ils ne tiennent pas compte de la distribution réelle des pertes extrêmes.

## Couche ciblée
`risk_backbone`

## Formulation mathématique
Appliquer la théorie des valeurs extrêmes (EVT) sur les pertes journalières :

Pour les pertes $L > u$ (seuil élevé), la distribution excédentaire suit une GPD :

$$\mathbb{P}(L - u \le y \mid L > u) = 1 - \left(1 + \frac{\xi y}{\tilde{\sigma}}\right)^{-1/\xi}$$

VaR au niveau $\alpha$ :

$$VaR_\alpha = u + \frac{\tilde{\sigma}}{\xi}\left[\left(\frac{n}{N_u}(1-\alpha)\right)^{-\xi} - 1\right]$$

CVaR (Expected Shortfall) :

$$ES_\alpha = \frac{VaR_\alpha}{1 - \xi} + \frac{\tilde{\sigma} - \xi u}{1 - \xi}$$

## Implémentation
- Ajouter `tail_risk_estimator.py` dans `risk_backbone/`
- Calibrer $\xi$ et $\tilde{\sigma}$ sur fenêtre glissante de 90 jours de PnL réel
- Remplacer les seuils fixes par : `drawdown_warning = VaR_{95%}`, `drawdown_observe = VaR_{99%}`
- Exposer les paramètres GPD dans `monitoring`

## Preuve requise
- Goodness-of-fit test (Kolmogorov-Smirnov) sur la GPD calibrée
- Backtesting du VaR : taux de violation proche du niveau théorique (Kupiec test)
- Comparaison avec seuils fixes : le EVT-based doit réduire le max drawdown réel sans augmenter la stérilisation

## Risque
- Échantillon trop petit → estimation $\xi$ instable
- $\xi > 0.5$ → distribution à queue si lourde que le CVaR est infini → fallback sur seuils fixes nécessaire

## Critère d'abandon
Si la GPD ne passe pas le KS-test sur 3 fenêtres consécutives, revenir aux seuils calibrés empiriquement.

## Lot backlog : 1

---

# STRATÉGIE 3 — ALLOCATION RISK PARITY INTRA-PORTEFEUILLE

## Angle : Quant / Math / Algèbre

## Problème
Le `portfolio_minimal` arbitre par score et budget, mais sans modèle d'allocation fondé sur la contribution au risque. Résultat : le portefeuille peut être dominé par un seul facteur sans le savoir.

## Couche ciblée
`portfolio_minimal` → `portfolio enrichi`

## Formulation mathématique
Risk Parity : chaque position contribue également au risque total.

Contribution au risque de la position $j$ :

$$RC_j = w_j \cdot \frac{(\Sigma w)_j}{\sqrt{w^\top \Sigma w}}$$

Objectif : $RC_j = RC_k$ pour tout $j, k$.

Résolution par optimisation convexe :

$$\min_w \sum_{j} \left(\ln w_j + \frac{1}{2} \lambda w^\top \Sigma w\right) \quad \text{s.c. } w_j > 0, \sum w_j \le W_{max}$$

Alternative simplifiée (inverse-volatilité) :

$$w_j^{IV} = \frac{1/\sigma_j}{\sum_k 1/\sigma_k}$$

## Implémentation
- Enrichir `allocation_router.py` avec un mode `RISK_PARITY`
- Input : matrice $\Sigma$ (Ledoit-Wolf si Complete, diagonale si Light), signaux validés
- Output : poids ajustés par contribution au risque
- Contrainte : ne pas dépasser les caps existants (`gross_cap`, `cluster_cap`)

## Preuve requise
- Replay comparatif : portefeuille risk parity vs portefeuille score-based
- Métriques : Sharpe portefeuille, max drawdown, concentration (Herfindahl), $K_{eff}$
- Le risk parity doit améliorer le Sharpe OU réduire le drawdown sans tuer la fréquence

## Risque
- Sur un portefeuille de 2-3 positions, risk parity = allocation quasi-égale → peu d'intérêt
- Estimation $\Sigma$ bruitée → allocation instable → turnover excessif

## Critère d'abandon
Si le turnover induit par risk parity > 2× le turnover du mode actuel sans gain de Sharpe.

## Lot backlog : 5

---

# STRATÉGIE 4 — WALK-FORWARD REPLAY PROTOCOL

## Angle : Quant / ML / Dev

## Problème
Le replay actuel est un backtest classique potentiellement sujet au look-ahead bias et au overfitting. Sans walk-forward, les enrichissements sont validés sur des données qu'ils ont "vues".

## Couche ciblée
`local_replay_runtime` + `protocols`

## Formulation
Découper l'historique en K fenêtres glissantes :

- Fenêtre $k$ : train sur $[t_{k-W}, t_k]$, test sur $[t_k, t_k + H]$
- Agrégation : $\bar{\mu}_{WF} = \frac{1}{K}\sum_{k=1}^{K} \hat{\mu}_k^{test}$
- Variance de performance : $\hat{\sigma}^2_{WF} = \frac{1}{K-1}\sum_{k=1}^{K}(\hat{\mu}_k^{test} - \bar{\mu}_{WF})^2$

Un enrichissement est validé seulement si $\bar{\mu}_{WF} > 0$ ET $\bar{\mu}_{WF} / \hat{\sigma}_{WF} > \tau_{min}$ (ratio de stabilité).

## Implémentation
- Ajouter `walk_forward_runner.py` dans `local_replay_runtime/`
- Paramètres : $W$ (taille fenêtre train), $H$ (taille horizon test), $K$ (nombre de folds), $\tau_{min}$
- Output : `WalkForwardReport(mean_pnl, std_pnl, stability_ratio, fold_details[])`
- Intégrer dans le pipeline `meta_learning` : aucune hypothèse n'est promouvable sans rapport WF

## Preuve requise
- Sur un enrichissement déjà validé en replay classique, montrer que le WF confirme ou infirme
- Sur un enrichissement connu comme surajusté (artificiellement créé), montrer que le WF le rejette

## Risque
- Données crypto trop courtes pour K=10 folds avec fenêtres significatives
- Walk-forward ne capture pas les changements structurels de marché

## Critère d'abandon
Si les données disponibles ne permettent pas K ≥ 5 folds avec H ≥ 7 jours, utiliser un protocole bootstrap combinatoire à la place.

## Lot backlog : 0

---

# STRATÉGIE 5 — CORRÉLATION CONDITIONNELLE AU RÉGIME (DCC SIMPLIFIÉ)

## Angle : Math / Quant / Algèbre

## Problème
La covariance Ledoit-Wolf est statique. En réalité, les corrélations entre paires augmentent en période de stress — le moment où la diversification est la plus nécessaire.

## Couche ciblée
`risk_backbone` + `portfolio`

## Formulation mathématique
DCC-GARCH simplifié (Engle 2002) :

Corrélation dynamique entre paires $i$ et $j$ :

$$q_{ij,t} = (1-a-b)\bar{\rho}_{ij} + a \cdot \epsilon_{i,t-1}\epsilon_{j,t-1} + b \cdot q_{ij,t-1}$$

$$\rho_{ij,t} = \frac{q_{ij,t}}{\sqrt{q_{ii,t} \cdot q_{jj,t}}}$$

Version simplifiée pour V5.3 : EWMA sur la corrélation rolling :

$$\hat{\rho}_{ij,t}^{EWMA} = \lambda \hat{\rho}_{ij,t-1}^{EWMA} + (1-\lambda) \frac{r_{i,t}r_{j,t}}{\sigma_{i,t}\sigma_{j,t}}$$

## Implémentation
- Enrichir `correlation_cluster_guard.py` avec un mode `DYNAMIC_CORRELATION`
- Calculer $\hat{\rho}_{ij,t}$ en EWMA avec $\lambda = 0.94$ (RiskMetrics standard)
- Ajuster les `cluster_cap` dynamiquement : quand la corrélation monte, le cap baisse
- Formule : $X_{cluster,c}^{max}(t) = X_{cluster,c}^{base} \cdot (1 - \gamma \cdot \max(0, \hat{\rho}_{c,t} - \bar{\rho}_c))$

## Preuve requise
- Shadow : comparer portefeuille avec corrélation statique vs dynamique
- Le mode dynamique doit réduire les drawdowns en période de stress sans trop réduire le PnL en période calme

## Risque
- Corrélation EWMA est un indicateur retardé (la crise a déjà commencé quand il réagit)
- Paramètre $\lambda$ unique pour toutes les paires → trop simpliste

## Critère d'abandon
Si le gain en drawdown < 10% relatif sur les épisodes de stress historiques, la complexité ne se justifie pas.

## Lot backlog : 5

---

# STRATÉGIE 6 — EDGE ATTRIBUTION FRAMEWORK

## Angle : Trader / Quant

## Problème
Le système mesure le PnL mais ne décompose pas l'edge en ses sources. On ne sait pas si le gain vient de l'alpha de timing, de la sélection de paire, de la gestion de position, ou du biais de survivorship.

## Couche ciblée
`meta_minimal` + `meta_learning`

## Formulation
Décomposition Brinson-like adaptée au trading systématique :

$$PnL_{total} = \underbrace{PnL_{timing}}_{\text{quand entrer}} + \underbrace{PnL_{selection}}_{\text{quelle paire}} + \underbrace{PnL_{sizing}}_{\text{combien}} + \underbrace{PnL_{execution}}_{\text{coût réel}} + \underbrace{PnL_{interaction}}_{\text{cross-effects}}$$

Où :
- $PnL_{timing} = \sum_i (r_i^{signal} - r_i^{random}) \cdot x_i$
- $PnL_{selection} = \sum_i (r_i^{pair} - r_i^{universe}) \cdot x_i$
- $PnL_{sizing} = \sum_i r_i \cdot (x_i^{actual} - x_i^{equal\_weight})$
- $PnL_{execution} = -\sum_i c_i$

## Implémentation
- Ajouter `edge_attribution.py` dans `meta_minimal/`
- Input : trades avec timestamps, prix d'entrée/sortie, sizing, coûts
- Output : `EdgeAttribution(timing_pnl, selection_pnl, sizing_pnl, execution_pnl, interaction_pnl)`
- Projeter par moteur, par paire, par régime dans `monitoring`

## Preuve requise
- La somme des attributions = PnL total (vérification comptable)
- Chaque composante est stable sur au moins 30 trades
- L'attribution révèle des insights non visibles dans le PnL agrégé

## Risque
- Sur-décomposition avec trop peu de trades → bruit
- L'interaction term peut absorber tout si le modèle est mal spécifié

## Critère d'abandon
Si l'interaction term > 30% du PnL total, le modèle d'attribution est trop grossier.

## Lot backlog : 7

---

# STRATÉGIE 7 — STRESS TESTING SYSTÉMATIQUE PAR SCÉNARIO

## Angle : Trader / Quant / Fintech

## Problème
Aucun lot de stress testing n'existe. Le système n'est validé qu'en conditions normales.

## Couche ciblée
`local_replay_runtime` + `risk_backbone`

## Scénarios obligatoires

| # | Scénario | Paramètres |
| --- | --- | --- |
| S1 | Flash crash | -15% en 5 minutes sur BTC, corrélation → 0.95 |
| S2 | Liquidity hole | Spread × 10, profondeur / 5 pendant 30 minutes |
| S3 | Exchange maintenance | Déconnexion 2 heures, puis reconnexion avec gap |
| S4 | Funding rate spike | Funding × 5 pendant 8 heures |
| S5 | Correlation breakdown | Corrélation BTC/alts passe de 0.7 à 0.3 en 1 heure |
| S6 | Volatilité nulle | Vol réalisée → 0.1× normal pendant 48h (range compression) |
| S7 | Cascade de stops | Mouvement 5% suivi de retrace 80% en 15 minutes |

## Implémentation
- Ajouter `stress_scenario_runner.py` dans `local_replay_runtime/`
- Chaque scénario modifie les données d'entrée du replay selon des paramètres de stress
- Output : `StressReport(scenario_id, max_drawdown, num_trades, pnl, risk_breaches[])`
- Gate : aucun scénario ne doit produire une perte > $LossBudget_{max} \times 1.5$

## Preuve requise
- Le système survit à chaque scénario sans crash ni état incohérent
- Le drawdown sous stress est borné par les mécanismes de risk

## Critère d'abandon
Non applicable — le stress testing est obligatoire, pas optionnel.

## Lot backlog : nouveau lot dédié (recommandé : Lot 9)

---

# STRATÉGIE 8 — ANTI-CROWDING FILTER ENRICHI

## Angle : Trader / Quant

## Problème
Le `competition_monitor` (Build-14) détecte le crowding mais ne le quantifie pas assez finement. En crypto, le crowding se manifeste par : open interest élevé + funding élevé + volume concentré.

## Couche ciblée
`complete_enablers` (enrichissement `competition_monitor`)

## Formulation
Score de crowding composite :

$$Crowd_t = \omega_1 \frac{OI_t - \bar{OI}}{std(OI)} + \omega_2 \frac{FR_t - \bar{FR}}{std(FR)} + \omega_3 \frac{Vol_t^{top5}}{Vol_t^{total}}$$

Où : OI = open interest, FR = funding rate, $Vol^{top5}/Vol^{total}$ = concentration du volume dans le top 5 de l'order book.

Pénalité scoring : $pen_{crowd} = \max(0, Crowd_t - \theta_{crowd}) \times \kappa_{crowd}$

## Implémentation
- Enrichir `competition_monitor.py`
- Ajouter les feeds OI et funding rate dans `data_backbone`
- Output : `CrowdingSnapshot(crowd_score, oi_zscore, fr_zscore, vol_concentration)`
- Brancher comme soft penalty dans `scoring_backbone`

## Preuve requise
- Shadow : les trades exécutés sur signaux "crowdés" ont-ils un PnL inférieur ?
- Corrélation $Crowd_t$ vs slippage réel > 0.3

## Critère d'abandon
Si la corrélation crowding → underperformance est < 0.15 sur 90 jours de shadow.

## Lot backlog : 6

---

# STRATÉGIE 9 — ADAPTIVE SIZING PAR RÉGIME

## Angle : Quant / Trader / Math

## Problème
Le sizing est actuellement gouverné par les tiers (T1/T2/T3) et les caps de risque, mais ne s'adapte pas au régime de marché détecté. En régime trend, les positions devraient être plus grosses ; en régime stressed, plus petites.

## Couche ciblée
`risk_backbone` + `scoring_backbone`

## Formulation
Multiplicateur de sizing conditionnel au régime :

$$m_{size}(s) = \begin{cases} m_{trend} & \text{si régime = trend} \\ m_{range} & \text{si régime = range} \\ m_{stressed} & \text{si régime = stressed} \end{cases}$$

Avec $m_{trend} \in [0.8, 1.2]$, $m_{range} \in [0.5, 1.0]$, $m_{stressed} \in [0.2, 0.5]$.

Taille finale : $x_i^{final} = x_i^{base} \times m_{size}(s) \times m_{risk}(i) \times m_{penalty}(i)$

Contrainte : $x_i^{final} \le x_{cap}$ toujours respecté.

## Implémentation
- Ajouter un `regime_size_adapter` dans `risk_backbone/`
- Input : régime courant (depuis `regime_engine` ou `hurst_regime_classifier`)
- Output : multiplicateur de sizing
- Brancher comme `size_penalty` dans `penalty_aggregator`

## Preuve requise
- Walk-forward : le sizing adaptatif améliore-t-il le Sharpe vs sizing fixe ?
- Shadow : les grandes positions en régime stressed sont-elles effectivement réduites ?

## Critère d'abandon
Si le gain de Sharpe < 0.05 sur le walk-forward.

## Lot backlog : 2

---

# STRATÉGIE 10 — FALSE BREAKOUT CLASSIFIER (ML LÉGER)

## Angle : IA-ML / Trader

## Problème
Le `false_breakout_model` (Build-14) existe mais sa logique interne n'est pas spécifiée. Un modèle ML léger (gradient boosting) entraîné sur les features du breakout peut discriminer les vrais des faux breakouts.

## Couche ciblée
`complete_enablers` (enrichissement `false_breakout_model`)

## Features d'entrée
- Volume au moment du breakout vs volume moyen
- Profondeur du carnet côté breakout vs côté opposé
- OFI normalisé
- Durée de la consolidation pré-breakout
- Nombre de tests du niveau cassé dans les 24h
- Hurst exponent local
- Funding rate
- Open interest delta sur 1h

## Formulation
Modèle : LightGBM binaire (vrai breakout = 1, faux = 0)

$$\hat{p}_{false} = f_{LGB}(features)$$

Pénalité : $pen_{false\_bo} = \hat{p}_{false} \times \kappa_{false\_bo}$

Seuil de hard block : $\hat{p}_{false} > 0.85$ → hard block pour moteur C uniquement.

## Implémentation
- Entraînement offline sur données labellisées (breakout suivi d'un retrace > 80% en 2h = faux)
- Modèle sérialisé, chargé au boot dans `false_breakout_model.py`
- Re-entraînement tous les 30 jours avec walk-forward
- Monitoring du AUC en production (concept drift → ré-entraînement)

## Preuve requise
- AUC > 0.70 en walk-forward
- Precision sur les faux breakouts > 0.60
- Le filtre réduit le taux de faux breakouts de > 20% en shadow

## Critère d'abandon
Si AUC < 0.60 en walk-forward ou si le concept drift rend le modèle instable sur 3 re-entraînements consécutifs.

## Lot backlog : 3

---

# STRATÉGIE 11 — EXECUTION QUALITY SCORE (EQS) DYNAMIQUE

## Angle : Fintech / Trader / Quant

## Problème
L'`execution_backbone` mesure le coût mais ne produit pas de score de qualité d'exécution comparable entre paires et entre moteurs. On ne sait pas si l'exécution sur SOL/USDT est meilleure ou pire que sur ETH/USDT.

## Couche ciblée
`execution_backbone` + `meta_minimal`

## Formulation
EQS composite par trade :

$$EQS_i = 1 - \frac{c_i^{total}}{|r_i^{gross}|} \cdot \mathbf{1}_{r_i^{gross} \ne 0}$$

EQS agrégé par paire :

$$\overline{EQS}_j = \frac{1}{N_j}\sum_{i \in pair_j} EQS_i$$

Score de qualité d'exécution normalisé : $EQS_j^{norm} = \frac{\overline{EQS}_j - \min_k \overline{EQS}_k}{\max_k \overline{EQS}_k - \min_k \overline{EQS}_k}$

## Implémentation
- Ajouter `execution_quality_scorer.py` dans `execution_backbone/`
- Output par paire × moteur : `EQScore(pair_id, engine_id, eqs_raw, eqs_normalized, num_trades)`
- Brancher dans `scoring_backbone` comme feature de ranking
- Projeter dans le dashboard "Execution Quality"

## Preuve requise
- Corrélation EQS vs CE > 0.3 (l'exécution de qualité corrèle avec la performance)
- Les paires à EQS faible ont un edge net significativement inférieur

## Critère d'abandon
Si EQS ne discrimine pas les paires (variance inter-paires < variance intra-paire).

## Lot backlog : 7

---

# STRATÉGIE 12 — MEAN REVERSION REGIME GUARD POUR ENGINE B

## Angle : Trader / Quant

## Problème
Engine B (mean reversion) peut combattre un vrai trend structurel si les filtres régime ne sont pas assez stricts. Le Hurst exponent est le meilleur indicateur : H < 0.5 → mean-reverting, H > 0.5 → trending.

## Couche ciblée
`engine_b` + `complete_enablers` (`hurst_regime_classifier`)

## Formulation
Guard conditionnel :

$$\text{B autorisé ssi } H_t^{local} < H_{max}^B \text{ ET } Conf_{regime} > C_{min}$$

Avec $H_{max}^B \approx 0.45$ et $C_{min} \approx 0.65$.

Pénalité graduelle :

$$pen_{regime\_B} = \max(0, H_t - H_{soft}^B) \times \kappa_H$$

Avec $H_{soft}^B \approx 0.40$, $\kappa_H \approx 2.0$.

## Implémentation
- Enrichir le builder de `engine_b` pour consulter `hurst_regime_classifier`
- Ajouter la pénalité dans `penalty_aggregator` avec un `penalty_id = "B_HURST_GUARD"`
- Hard block : $H_t > H_{max}^B$ ET moteur = B → code `RISK_REGIME_MISMATCH_B`

## Preuve requise
- Replay : les trades B perdants sont-ils corrélés avec $H_t > 0.5$ ?
- Shadow : le guard réduit-il les pertes de B sans tuer sa fréquence de > 50% ?

## Critère d'abandon
Si le guard réduit la fréquence de B de > 60% sans amélioration du Sharpe.

## Lot backlog : 2

---

# STRATÉGIE 13 — PORTFOLIO OVERLAP DETECTOR

## Angle : Architecte / Quant

## Problème
Deux moteurs sur la même paire peuvent générer des signaux quasi-identiques (A et C sur BTC en trend). Le portefeuille ne le détecte pas formellement.

## Couche ciblée
`portfolio_minimal`

## Formulation
Score d'overlap entre deux positions $i$ (moteur $m_1$) et $j$ (moteur $m_2$) :

$$Overlap_{ij} = \mathbf{1}_{pair_i = pair_j} \cdot \mathbf{1}_{dir_i = dir_j} \cdot \left(\frac{\min(|x_i|, |x_j|)}{\max(|x_i|, |x_j|)}\right) \cdot \rho_{m_1,m_2}$$

Overlap portefeuille : $OVL_{port} = \frac{\sum_{i<j} Overlap_{ij}}{\binom{N}{2}}$

Contrainte : $OVL_{port} \le OVL_{max}$

## Implémentation
- Ajouter `overlap_detector.py` dans `portfolio/`
- Input : positions actives + corrélation historique inter-moteurs
- Output : `OverlapReport(overlap_score, overlap_pairs[], recommendation)`
- Si $OVL_{port} > OVL_{max}$ → réduire la position du moteur à plus faible conviction

## Preuve requise
- Replay : les épisodes de high overlap correspondent-ils à des drawdowns plus profonds ?
- La contrainte d'overlap réduit-elle le max drawdown sans tuer le PnL ?

## Critère d'abandon
Si overlap et drawdown ne sont pas corrélés (corr < 0.2).

## Lot backlog : 5

---

# STRATÉGIE 14 — LATENCE END-TO-END MONITORING

## Angle : Architecte / Dev / Fintech

## Problème
Aucun monitoring de la latence complète du pipeline : data → signal → scoring → risk → portfolio → execution. Un enrichissement peut ajouter 200ms de latence sans que personne ne le détecte.

## Couche ciblée
`monitoring` + infrastructure

## Implémentation
- Instrumenter chaque module avec un timestamp d'entrée et de sortie
- Calculer : $Lat_{total} = t_{execution\_sent} - t_{data\_received}$
- Décomposer : $Lat_{total} = Lat_{data} + Lat_{signal} + Lat_{scoring} + Lat_{risk} + Lat_{portfolio} + Lat_{execution}$
- Alerter si $Lat_{total} > Lat_{max}$ (ex : 500ms pour Light)
- Projeter le profil de latence dans le dashboard avec percentiles (p50, p90, p99)

## Preuve requise
- Avant enrichissement : mesurer la baseline
- Après chaque enrichissement : vérifier que $\Delta Lat_{total} < Lat_{budget}$ alloué

## Critère d'abandon
Non applicable — monitoring obligatoire.

## Lot backlog : 0

---

# STRATÉGIE 15 — META-DIAGNOSTIC DE STÉRILISATION

## Angle : Trader / Quant / IA-ML

## Problème
Le taux de stérilisation est mesuré globalement mais pas décomposé. On ne sait pas si la stérilisation vient du risk, du scoring, des hard blocks, ou du portefeuille.

## Couche ciblée
`meta_learning` + `monitoring`

## Formulation
Décomposition de la stérilisation :

$$SterilRate = \frac{N_{sterilized}}{N_{candidates}}$$

Avec ventilation :

$$N_{sterilized} = N_{hard\_block} + N_{risk\_veto} + N_{score\_too\_low} + N_{portfolio\_reject} + N_{overlap\_reject} + N_{phantom}$$

Pour chaque composante, calculer son taux relatif :

$$SterilShare_k = \frac{N_k}{N_{sterilized}}$$

## Implémentation
- Enrichir `ScoringCandidateAudit` avec un champ `sterilization_source`
- Agréger dans `meta_learning` par moteur × paire × période
- Projeter dans un panneau dédié "Sterilization Anatomy"

## Preuve requise
- Sur 30 jours de shadow, identifier le top 3 des sources de stérilisation
- Vérifier que les enrichissements ciblent la bonne source

## Critère d'abandon
Non applicable — c'est de l'observabilité pure.

## Lot backlog : 1

---

# STRATÉGIE 16 — ADVERSE SELECTION DETECTOR

## Angle : Trader / Fintech / Quant

## Problème
L'adverse selection (le prix bouge immédiatement contre nous après un fill) est mesurée dans `execution_backbone` mais pas utilisée comme feedback loop pour les moteurs.

## Couche ciblée
`execution_backbone` → `scoring_backbone` → `meta_learning`

## Formulation
Score d'adverse selection par trade :

$$AS_i = \frac{P_{t+\Delta}^{mid} - P_i^{fill}}{P_i^{fill}} \times sign_i$$

Où $sign_i = -1$ si long, $+1$ si short, et $\Delta$ = 1 minute.

Pénalité prospective : si un moteur × paire a un $\overline{AS}$ historique > seuil, pénaliser les futurs candidats.

$$pen_{AS}(engine, pair) = \max(0, \overline{AS}_{engine,pair} - \theta_{AS}) \times \kappa_{AS}$$

## Implémentation
- Calculer $AS_i$ dans `execution_cost_meter.py` pour chaque fill
- Agréger dans `meta_learning` : rolling $\overline{AS}$ par moteur × paire (fenêtre 50 trades)
- Brancher comme penalty dans `penalty_aggregator`

## Preuve requise
- Shadow : $\overline{AS}$ élevé corrèle avec edge net négatif
- Les paires à forte adverse selection sont effectivement pénalisées

## Critère d'abandon
Si $\overline{AS}$ ne discrimine pas les trades gagnants des perdants (AUC < 0.55).

## Lot backlog : 7

---

# STRATÉGIE 17 — ENGINE D CONTEXT LEGITIMACY SCORE

## Angle : Trader / Quant / Architecte

## Problème
Engine D (re-entry) peut devenir un moteur de revenge trading si le contexte de re-entry n'est pas rigoureusement validé.

## Couche ciblée
`engine_d` + `meta_learning`

## Formulation
Score de légitimité de re-entry :

$$Legit_D = \alpha_1 \cdot \mathbf{1}_{regime\_improved} + \alpha_2 \cdot \mathbf{1}_{initial\_too\_tight} + \alpha_3 \cdot \mathbf{1}_{execution\_failed} - \beta_1 \cdot \mathbf{1}_{loss\_on\_initial} - \beta_2 \cdot \mathbf{1}_{same\_direction\_same\_bar}$$

Avec $\alpha_i > 0$ (facteurs légitimes) et $\beta_j > 0$ (facteurs de revenge).

Hard block D : $Legit_D < 0$

## Implémentation
- Enrichir le builder de `engine_d` avec `legitimacy_scorer.py`
- Input : trade initial (via `origin_context_id`), régime actuel vs initial, PnL initial, timing
- Output : `LegitimacyScore(score, factors[], is_blocked)`
- Logger dans `meta_learning` chaque re-entry avec son score

## Preuve requise
- Replay : les re-entries à $Legit_D < 0$ ont-elles un PnL significativement pire ?
- Les re-entries légitimes (régime amélioré, exécution ratée) ont-elles un PnL meilleur ?

## Critère d'abandon
Si la distribution de PnL des re-entries ne diffère pas significativement entre $Legit_D > 0$ et $Legit_D < 0$ (test de Kolmogorov-Smirnov, p > 0.10).

## Lot backlog : 4

---

# STRATÉGIE 18 — CAPACITY AWARE POSITION SIZING

## Angle : Fintech / Trader / Quant

## Problème
Le sizing ne tient pas compte de la capacité réelle du marché. Sur une paire à faible liquidité, un sizing de T2 peut représenter 10% du volume quotidien, créant un impact de marché significatif.

## Couche ciblée
`risk_backbone` + `execution_backbone`

## Formulation
Participation rate :

$$PR_i = \frac{x_i}{ADV_j \times H_{holding}}$$

Où $ADV_j$ = average daily volume de la paire $j$, $H_{holding}$ = durée moyenne de holding.

Contrainte : $PR_i \le PR_{max}$ (ex : 1% du volume quotidien)

Si $PR_i > PR_{max}$, réduire : $x_i^{adjusted} = PR_{max} \times ADV_j \times H_{holding}$

## Implémentation
- Calculer $ADV_j$ glissant (20 jours) dans `data_backbone`
- Ajouter `capacity_guard.py` dans `risk_backbone/`
- Appliquer la contrainte de participation rate après le sizing par tiers

## Preuve requise
- Les trades à $PR > 2\%$ ont-ils un slippage significativement plus élevé ?
- La contrainte de capacity réduit-elle les coûts d'exécution sur les paires peu liquides ?

## Critère d'abandon
Si les paires éligibles sont toutes suffisamment liquides pour ne jamais déclencher la contrainte.

## Lot backlog : 2

---

# STRATÉGIE 19 — BAYESIAN EDGE ESTIMATION AVEC PRIOR SCEPTIQUE

## Angle : Math / Quant / Algèbre

## Problème
L'estimation de l'edge net $\hat{\mu}_{net}$ est un estimateur fréquentiste ponctuel. Avec peu de trades, l'incertitude est énorme mais invisible. Un framework bayésien avec prior sceptique rend l'incertitude explicite.

## Couche ciblée
`meta_minimal` + `meta_learning`

## Formulation mathématique
Prior sceptique sur l'edge : $\mu \sim \mathcal{N}(0, \sigma_{prior}^2)$

Avec $\sigma_{prior}$ calibré pour refléter le scepticisme : "la plupart des stratégies n'ont pas d'edge".

Posterior après $N$ trades observés avec moyenne $\bar{r}$ et variance $s^2$ :

$$\mu_{post} = \frac{\frac{N\bar{r}}{s^2}}{\frac{N}{s^2} + \frac{1}{\sigma_{prior}^2}}$$

$$\sigma_{post}^2 = \frac{1}{\frac{N}{s^2} + \frac{1}{\sigma_{prior}^2}}$$

Probabilité que l'edge soit positif : $P(\mu > 0 | data) = \Phi\left(\frac{\mu_{post}}{\sigma_{post}}\right)$

Un moteur est "crédiblement profitable" seulement si $P(\mu > 0 | data) > 0.80$.

## Implémentation
- Enrichir `edge_tracker_prudent` avec un mode bayésien
- $\sigma_{prior} = 0.001$ (1 bp par trade — sceptique mais pas nihiliste)
- Output : `BayesianEdge(posterior_mean, posterior_std, prob_positive, credible_interval_95)`
- Utiliser $P(\mu > 0)$ comme gate pour les promotions Shadow → Micro-live

## Preuve requise
- Sur les moteurs historiquement profitables, $P(\mu > 0)$ converge vers > 0.90
- Sur les enrichissements ratés, $P(\mu > 0)$ reste < 0.60

## Critère d'abandon
Non applicable — c'est un framework d'estimation supérieur à l'estimateur ponctuel.

## Lot backlog : 1

---

# STRATÉGIE 20 — ENRICHMENT PRUNING PROTOCOL

## Angle : Architecte / Dev / Quant

## Problème
Le système n'a aucun mécanisme formel pour retirer un enrichissement qui s'avère inutile ou nocif. La complexité ne fait que croître.

## Couche ciblée
`meta_learning` + `protocols` + `monitoring`

## Formulation
Chaque enrichissement reçoit un TTL (Time-To-Live) et un score de valeur :

$$Value_e = \frac{\Delta CE_e}{\Delta Complexity_e}$$

Où :
- $\Delta CE_e$ = changement de capital efficiency attribuable à l'enrichissement (via edge attribution)
- $\Delta Complexity_e$ = coût en latence + lignes de code + tests supplémentaires

Règle de pruning : si après $TTL$ jours, $Value_e < V_{min}$ → l'enrichissement est candidat à la suppression.

Process :
1. Chaque enrichissement est taggé avec un `enrichment_id` et une date d'activation
2. À chaque revue (mensuelle), calculer $Value_e$
3. Si $Value_e < V_{min}$ sur 2 revues consécutives → marquer `DEPRECATED`
4. Si `DEPRECATED` pendant 30 jours sans contestation → supprimer

## Implémentation
- Ajouter `enrichment_lifecycle.py` dans `meta_learning/`
- Table : `enrichment_registry(id, name, lot, activation_date, ttl_days, value_score, status)`
- Statuts : `ACTIVE`, `UNDER_REVIEW`, `DEPRECATED`, `REMOVED`
- Brancher dans `review_orchestrator` pour les revues mensuelles

## Preuve requise
- Au moins un enrichissement est identifié comme candidat à la suppression après le premier cycle
- La suppression d'un enrichissement `DEPRECATED` ne casse aucun test

## Critère d'abandon
Non applicable — c'est l'anti-stratégie de la complexité croissante.

## Lot backlog : 0

---

# SYNTHÈSE DES 20 STRATÉGIES

| # | Nom | Angle dominant | Lot | Criticité |
| --- | --- | --- | --- | --- |
| 1 | Concept Drift Detector | IA-ML / Quant | 0+1 | Critique |
| 2 | Tail Risk EVT | Math / Quant | 1 | Critique |
| 3 | Risk Parity Allocation | Quant / Math | 5 | Élevée |
| 4 | Walk-Forward Replay | Quant / ML | 0 | Critique |
| 5 | Corrélation Conditionnelle DCC | Math / Quant | 5 | Élevée |
| 6 | Edge Attribution | Trader / Quant | 7 | Élevée |
| 7 | Stress Testing Systématique | Trader / Quant | 9 (nouveau) | Critique |
| 8 | Anti-Crowding Filter | Trader / Quant | 6 | Moyenne-haute |
| 9 | Adaptive Sizing par Régime | Quant / Trader | 2 | Élevée |
| 10 | False Breakout Classifier ML | IA-ML / Trader | 3 | Élevée |
| 11 | Execution Quality Score | Fintech / Trader | 7 | Moyenne-haute |
| 12 | Hurst Guard pour Engine B | Trader / Quant | 2 | Élevée |
| 13 | Portfolio Overlap Detector | Architecte / Quant | 5 | Moyenne-haute |
| 14 | Latence End-to-End Monitoring | Architecte / Dev | 0 | Critique |
| 15 | Meta-Diagnostic Stérilisation | Trader / Quant | 1 | Élevée |
| 16 | Adverse Selection Detector | Trader / Fintech | 7 | Élevée |
| 17 | Engine D Legitimacy Score | Trader / Quant | 4 | Élevée |
| 18 | Capacity Aware Sizing | Fintech / Trader | 2 | Moyenne-haute |
| 19 | Bayesian Edge Estimation | Math / Quant | 1 | Élevée |
| 20 | Enrichment Pruning Protocol | Architecte / Dev | 0 | Critique |

---

# ORDRE D'IMPLÉMENTATION RECOMMANDÉ

## Phase Immédiate (pré-requis à tout enrichissement)
- **S14** — Latence end-to-end monitoring
- **S4** — Walk-forward replay protocol
- **S20** — Enrichment pruning protocol

## Phase Fondation (Lots 0-1)
- **S1** — Concept drift detector
- **S15** — Meta-diagnostic stérilisation
- **S19** — Bayesian edge estimation
- **S2** — Tail risk EVT

## Phase Moteurs (Lots 2-4)
- **S12** — Hurst guard pour Engine B
- **S9** — Adaptive sizing par régime
- **S18** — Capacity aware sizing
- **S10** — False breakout classifier ML
- **S17** — Engine D legitimacy score

## Phase Portefeuille (Lot 5)
- **S3** — Risk parity allocation
- **S5** — Corrélation conditionnelle DCC
- **S13** — Portfolio overlap detector

## Phase Exploitation (Lots 6-7)
- **S8** — Anti-crowding filter
- **S6** — Edge attribution
- **S11** — Execution quality score
- **S16** — Adverse selection detector

## Phase Résilience (Lot 9 nouveau)
- **S7** — Stress testing systématique

---

## Fin du document stratégique
