# V5.3 — ANNEXE MATHEMATIQUE
## Doctrine cible : Market Physics / Liquidity Topography
### Date : 2026-04-03
### Statut : proposition d'annexe mathematique operationnelle
### Portee : Light d'abord, Complete ensuite, sans casser le canon V5.3

---

# 0. Objet

Cette annexe mathematique formalise la transition de V5.3 d'une lecture principalement :
- geometrique du prix
- basee sur des indicateurs retardes classiques
- et souvent predictible pour les autres bots

a une lecture plus moderne, centree sur :
- la topographie de liquidite
- la pression agressive vs passive
- les vides de liquidite
- l'absorption
- la friction d'execution
- la survivabilite economique nette

Cette annexe ne cree pas une V5.3 parallele.
Elle reste compatible avec les principes canoniques :
- Build-14 comme couche d'enrichissement gouvernee
- risk / scoring / protocols / monitoring comme surfaces obligatoires
- promotion via replay -> shadow -> micro-live -> live
- aucun moteur hors A / B / C / D

Le canon V5.3 exige d'ameliorer simultanement :
- frequence utile
- edge net
- capital efficiency
- diversite reelle d'edge

tout en maitrisant :
- variance
- couts
- correlation
- exposition systemique
- budget de perte
- saturation infra

Voir : master canonique et architecture mathematique resumee. fileciteturn7file4

---

# 1. Règles de lecture

## 1.1 Hierarchie des equations

Les equations sont classees en 3 classes.

### Classe A — operationnelles immediates
Codables vite, robustes, utilisables sur VPS en 1m / 5m / 15m.

### Classe B — operationnelles enrichies
Plus justes, un peu plus lourdes, a deployer d'abord en shadow / Build-14.

### Classe C — recherche
Utiles pour recherche, diagnostics ou calibration, mais pas a imposer tout de suite dans le live.

## 1.2 Regle prod-safe

Une equation n'entre pas en production juste parce qu'elle est elegante.
Elle doit prouver :
1. utilite economique
2. stabilite technique
3. non-regression Light

Cette discipline est coherente avec le canon Build-14. fileciteturn7file18

## 1.3 Regle anti-fausse precision

Quand une mesure microstructure exacte n'est pas observable sur VPS,
on utilise :
- un proxy explicite
- versionne
- auditable
- compare au vrai comportement ex post

Le but n'est pas d'imiter le HFT.
Le but est d'avoir une lecture suffisamment vraie pour survivre. Le manifeste microstructure pose bien ce paradigme VPS/post-HFT. fileciteturn7file6turn7file12

---

# 2. Notation commune

- p_t : prix courant
- m_t : mid-price au temps t
- b_t : meilleur bid
- a_t : meilleur ask
- s_t = a_t - b_t : spread absolu
- s_t_pct = (a_t - b_t) / m_t : spread relatif
- v_t : volume echange sur l'intervalle t
- q_bid,t : quantite disponible au bid
- q_ask,t : quantite disponible a l'ask
- r_t = ln(p_t / p_(t-1)) : rendement log
- sigma_n : volatilite realisee sur n observations
- x_i : taille notionnelle ou taille en devise du trade i
- h_i : horizon de detention du trade i
- c_i : cout total estime ou realise du trade i
- g_i : gain brut attendu du trade i
- EV_i : esperance nette du trade i
- CE_i : capital efficiency du trade i
- DD_t : drawdown courant
- beta_i : exposition factorielle BTC de la paire i
- rho_ij : correlation entre i et j
- R_i : risque dollar du trade i

---

# 3. Couche data / microstructure : nouvelle physique utile

Le canon V5.3 contient deja une microstructure minimale :
- OFI
- book imbalance
- microprice
- persistence filter

et Build-14 autorise une version enrichie. fileciteturn7file18

La mutation recommandee est donc d'enrichir cette famille, pas de la contourner.

## 3.1 Delta volume proxy VPS

### But
Mesurer la pression directionnelle reelle, meme sans tick aggressor parfait.

### Formule A1 — proxy simple
Delta_t = sign(Close_t - Open_t) * Volume_t

### Formule A2 — proxy plus graduel
Delta_t = ((Close_t - Open_t) / max(High_t - Low_t, eps)) * Volume_t

Cette version est meilleure que le simple signe, car elle tient compte de la position de cloture dans la bougie.

### Cumulative delta
CumDelta_t = Sum_{u=t-L+1..t}(Delta_u)

### Divergence prix / flux
DeltaDiv_t = sign(p_t - p_(t-L)) * sign(CumDelta_t)

Interpretation :
- DeltaDiv_t = +1 : prix et flux coherents
- DeltaDiv_t = -1 : divergence potentiellement dangereuse

### Usage recommande
- Engine A : confirmation ou blocage de trend
- Engine D : validation de re-entry si le flux redevient coherent
- monitoring : panneau de pression dominante

Le manifeste propose bien `volume_delta_aggregator` et la divergence prix / cumulative delta. fileciteturn7file13turn7file9

## 3.2 OFI — Order Flow Imbalance

### Formule A
OFI_t = V_buy,t - V_sell,t

### Normalisation utile
OFI_norm,t = (V_buy,t - V_sell,t) / max(V_buy,t + V_sell,t, eps)

OFI_norm,t appartient a [-1, +1].

### OFI persistant
DOFI_t = Sum_{u=t-k+1..t}(w_u * OFI_norm,u)
avec w_u decroissants ou uniformes.

### Usage recommande
- filtrage de continuation
- retournement post-sweep
- lecture d'inventaire MM / absorption locale

Build-14 canonique cite deja OFI et imbalance carnet comme briques enrichissables. fileciteturn7file18

## 3.3 Book imbalance

### Formule A
BI_t = (Q_bid,t - Q_ask,t) / max(Q_bid,t + Q_ask,t, eps)

### Version multi-niveaux
BI_t^(K) = (Sum_{l=1..K} q_bid,t^(l) - Sum_{l=1..K} q_ask,t^(l)) /
           max(Sum_{l=1..K} q_bid,t^(l) + Sum_{l=1..K} q_ask,t^(l), eps)

### Usage
- Build-14 : contexte microstructure
- Engine B : renversement post-sweep
- Engine C : mur oppose / vide devant

## 3.4 Microprice

### Formule canonique simple
MP_t = (a_t * q_bid,t + b_t * q_ask,t) / max(q_bid,t + q_ask,t, eps)

### Ecart microprice / mid
DeltaMP_t = (MP_t - m_t) / max(m_t, eps)

### Interpretation
- DeltaMP_t > 0 : pression haussiere implicite
- DeltaMP_t < 0 : pression baissiere implicite

### Usage
- confirmation de sens
- detection d'absorption si DeltaMP reste oriente mais le niveau ne cede pas

## 3.5 Rolling volume profile

Le manifeste propose de migrer d'une lecture OHLCV pure vers une lecture volume-profile / POC / HVN / LVN. C'est une direction valide. fileciteturn7file6turn7file13

### Discretisation
On decoupe l'axe prix en bins B_k.

### Volume profile rolling
VP_k(T) = Sum_{u in fenetre T} Volume_u * 1{Price_u appartient a B_k}

### Point of Control
POC(T) = argmax_k VP_k(T)

### Volume total de la fenetre
V_tot(T) = Sum_k VP_k(T)

### Value Area
Trouver le plus petit ensemble de bins A(T) tel que :
Sum_{k in A(T)} VP_k(T) >= alpha * V_tot(T)
avec alpha = 0.70 en pratique.

On note ensuite :
- VAL(T) = borne basse de A(T)
- VAH(T) = borne haute de A(T)

### High Volume Node / Low Volume Node
- HVN : bin localement tres charge en volume
- LVN : bin localement tres faible en volume

### Score de vide de liquidite
VoidScore_t = 1 - (VolumeBetween(p_t, p_target, T) / max(MeanLocalVolume(T), eps))

Interpretation pratique :
- VoidScore proche de 1 : vrai vide
- VoidScore faible : beaucoup de friction historique

### Usage recommande
- Engine B : retour vers POC / Value Area
- Engine C : breakout seulement si vide devant
- Risk : invalidation par mur / HVN au lieu d'ATR seul

Le changelog microstructure propose exactement l'ajout de `poc_price_24h`, `val_high_24h`, `val_low_24h`, `nearest_hvn`, `nearest_lvn`, `is_liquidity_void_ahead`. fileciteturn7file15

## 3.6 Sweep detection

Le sweep est une brique centrale de la nouvelle doctrine. Le manifeste et le changelog en font un point d'entree pour B et D. fileciteturn7file8turn7file17

### Formule A — score de sweep simple
SweepScore_t = w1 * WickRatio_t + w2 * VolSpike_t + w3 * Rejection_t

avec :
- WickRatio_t = upper_wick_t / max(ATR_14, eps) pour un sell sweep
- VolSpike_t = Volume_t / max(MeanVolume_20, eps)
- Rejection_t = 1 si close revient dans la plage precedente, sinon 0

### Regle operationnelle proposee
Sweep detecte si :
- WickRatio_t > 1.5
- VolSpike_t > 2.5
- Rejection_t = 1

### Sortie
SweepEvent = {direction, exhaustion_price, intensity, timestamp}

### Remarque critique
Ici, ATR n'est plus un stop principal.
Il reste un simple normalisateur local de wick.
C'est une bonne utilisation secondaire d'un indicateur classique.

## 3.7 Absorption detection

### Idee physique
Si le flux agressif tape un niveau, mais que le niveau ne cede pas, un gros passif absorbe.

### Formule A — score d'absorption
AbsorptionScore_t = |Delta_t| * 1{Distance(price_t, level) <= eta} * 1{MoveAfterImpact_t <= tau}

ou plus explicitement :
AbsorptionScore_t = (|Delta_t| / max(MeanAbsDelta, eps)) *
                    exp(-|p_t - level| / eta) *
                    exp(-|p_(t+h) - p_t| / tau)

### Interpretation
- score eleve : beaucoup d'agression, peu de deplacement
- score faible : pas d'absorption convaincante

### Usage
- Engine D : re-entry disciplinee
- Engine B : validation d'inventaire / mur reel

## 3.8 Persistence filter

### Formule
Persist_t = Sum_{u=t-k+1..t}(1{signal_u a meme signe}) / k

ou version plus douce :
Persist_t = Sum_{u=t-k+1..t}(w_u * sign(signal_u))

### Usage
Eviter qu'un spike microstructure instantane devienne un veto ou un boost abusif.

---

# 4. Couche execution / friction : la vraie survie du petit capital

Le canon V5.3 impose deja la mesure des couts reels, du break-even et de la capital efficiency. fileciteturn7file10turn7file14

Le manifeste va dans le bon sens en demandant un guard de friction microstructure. Il faut cependant raffiner la formule pour eviter des proxies trop fragiles. fileciteturn7file15turn7file16

## 4.1 Spread relatif

SpreadPct_t = (a_t - b_t) / max(m_t, eps)

### Spread regime score
SpreadZ_t = (SpreadPct_t - MeanSpread_1h) / max(StdSpread_1h, eps)

### Blocage prudent
Spread hard block si :
SpreadPct_t > k_spread * MeanSpread_1h
avec k_spread entre 2.0 et 2.5 selon moteur

Le changelog propose 2.5x la moyenne rolling 1h, ce qui est raisonnable comme v1. fileciteturn7file15turn7file17

## 4.2 Volatilite realisee courte

### Rendements
r_u = ln(p_u / p_(u-1))

### Volatilite 1m ou courte
sigma_short = sqrt(Sum_{u=t-L+1..t}(r_u - mean(r))^2 / max(L-1,1))

### Variante annualisee inutile ici
En micro-friction, on garde une volatilite locale non annualisee.

## 4.3 Slippage estime — formule simple robuste

La formule brute du manifeste a la bonne intuition mais peut etre amelioree. Au lieu de :
slippage ~ sigma_1m * volume / taille

je recommande :

### Formule A
SlipEst_i = k1 * SpreadPct_t + k2 * sigma_short * sqrt(x_i / max(Vol1mValue_t, eps))

avec :
- x_i : taille ordre en valeur
- Vol1mValue_t : volume echange en valeur sur 1m
- k1, k2 calibres par replay / shadow

Cette forme est meilleure car :
- le spread est separe explicitement
- l'impact croit avec la racine de la participation, pas de facon lineaire naive
- la calibration reste simple

### Formule B — proxy de Kyle prudent
LambdaProxy_t = sigma_short / max(Vol1mValue_t, eps)
SlipImpact_i = LambdaProxy_t * x_i

Puis :
SlipEst_i = k1 * SpreadPct_t + k2 * SlipImpact_i

### Recommandation
- Formule A en prod v1
- Formule B en shadow / calibration

## 4.4 Cout total estime

CostEst_i = Fees_i + SpreadHalfIn_i + SpreadHalfOut_i + SlipEst_i

si l'on simplifie :
CostEst_i = Fees_i + SpreadPct_t + SlipEst_i

## 4.5 Esperance nette et micro_friction_guard

### Esperance nette
EV_net_i = g_i - CostEst_i

### Hard block de friction
Si EV_net_i < EV_min_required alors HARD BLOCK

### Variante en basis points
EdgeNetBps_i = EdgeGrossBps_i - CostEstBps_i

Si EdgeNetBps_i < EdgeFloorBps alors HARD BLOCK

Le manifeste propose deja cette logique : si le cout estimé depasse l'esperance moteur, on bloque. C'est une excellente direction. fileciteturn7file15turn7file16

## 4.6 Break-even prudent

BE_i = CostEst_i

### Break-even prudent majore
BE_prudent_i = CostEst_i + MarginSafety_i

### Condition de survie
Signal admissible si :
ExpectedGrossMove_i > BE_prudent_i

## 4.7 Capital efficiency

Le canon fait de la capital efficiency un juge central. fileciteturn7file4turn7file10

### Par trade
CE_i = NetPnL_i / max(x_i * h_i, eps)

### En attente / ex ante
CEexp_i = EV_net_i / max(x_i * h_exp_i, eps)

### Usage
- ranking entre opportunites
- comparaison A vs B vs C vs D
- validation d'enrichissement Build-14

---

# 5. Risk backbone : du risque geometrique au risque de topographie

Le canon V5.3 a deja :
- gross cap
- loss cap
- budget BTC
- cluster guard
- drawdown guard

La nouvelle doctrine ne remplace pas ces briques.
Elle ajoute une couche de risque de friction et de stop geometry. fileciteturn7file18

## 5.1 Exposition brute

GrossExp = Sum_i x_i

Contrainte :
GrossExp <= X_gross_max

## 5.2 Budget de perte

LossBudget = Sum_i R_i

Contrainte :
LossBudget <= L_max

## 5.3 Risque d'un trade

R_i = x_i * StopDistancePct_i

ou si taille en base :
R_i = Qty_i * |Entry_i - Stop_i|

## 5.4 Stop de liquidite

Le manifeste a raison sur le fond : un ATR-stop pur est trop visible. fileciteturn7file12turn7file16

### Ancien schema faible
Stop_i = Entry_i - k_ATR * ATR_i

### Nouveau schema recommande
Stop_i = Wall_i - Buffer_i
pour un achat, ou
Stop_i = Wall_i + Buffer_i
pour une vente

avec :
- Wall_i = nearest_hvn ou niveau d'absorption valide
- Buffer_i = max(delta_min, c_buf * sigma_short)

### Condition de viabilite du stop
StopDistancePct_i = |Entry_i - Stop_i| / max(Entry_i, eps)

Si StopDistancePct_i < StopNoiseFloor :
- soit fallback ATR
- soit trade refuse

### Distance de mur
WallDistancePct_i = |Entry_i - Wall_i| / max(Entry_i, eps)

Le changelog propose explicitement cette logique de nearest_hvn + buffer. fileciteturn7file15turn7file17

## 5.5 Taille selon risque dollar constant

Si le stop devient variable selon la liquidite, la taille doit s'adapter.
Le changelog le note correctement. fileciteturn7file17

### Formule
Qty_i = RiskDollarTarget / max(|Entry_i - Stop_i|, eps)

### Variante notionnelle
x_i = RiskDollarTarget / max(StopDistancePct_i, eps)

puis cappee par :
- position cap
- gross cap
- cluster cap
- budget BTC
- micro_friction_guard

## 5.6 Budget BTC

BetaPort_t = Sum_i w_i * beta_i

Contrainte :
|BetaPort_t| <= BetaMax

## 5.7 Cluster risk

ClusterExp_g = Sum_{i appartient a g} x_i

Contrainte :
ClusterExp_g <= ClusterCap_g

### Variante correlation-aware
MargCluster_i = Sum_j x_i * x_j * rho_ij

Cette variante est plus riche, mais a garder d'abord en shadow / Complete.

## 5.8 Drawdown-aware attenuation

### Drawdown courant
DD_t = 1 - Equity_t / max(PeakEquity_t, eps)

### Facteur de reduction
phi_DD_t = max(phi_min, 1 - gamma_DD * DD_t)

### Taille attenuee
x_i_eff = phi_DD_t * x_i

Le canon cite deja des seuils drawdown warning / observe dans la couche risk actuelle. Les enrichissements doivent s'y brancher, pas les dupliquer. fileciteturn0file2

---

# 6. Scoring backbone : de la lecture de prix a la lecture causale

Le canon V5.3 impose deja :
- score brut
- penalties
- hard blockers rares et fatals
- ranking
- decision auditability

La bonne evolution consiste a faire entrer les nouvelles mesures physiques dans ce cadre, pas a recréer un score obscur. fileciteturn7file18

## 6.1 Score brut general

S_raw,i = Sum_m alpha_m * F_i,m

### Nouvelle decomposition recommandee
S_raw,i = S_structure,i + S_context,i + S_flow,i + S_liquidity,i

avec :
- S_structure : structure prix / pattern moteur
- S_context : regime, health, coherence
- S_flow : delta, OFI, imbalance, absorption
- S_liquidity : void, wall, POC distance, friction preference

## 6.2 Penalties

Pen_i = Pen_context,i + Pen_cost,i + Pen_portfolio,i + Pen_micro_noise,i

### Score penalise
S_eff,i = S_raw,i - Pen_i

## 6.3 Hard blockers

HardBlock_i = 1 si l'une des conditions fatales est vraie, sinon 0

La reforme canonique impose que hard block reste reserve aux vrais risques fatals. fileciteturn7file18

### Nouveaux hard blockers legitimes
- RISK_MICRO_FRICTION_BLOCK
- RISK_SPREAD_WIDEN_BLOCK
- PHYSICS_C_HVN_WALL_BLOCK
- PHYSICS_A_DELTA_DIVERGENCE_BLOCK

### Nouveaux boosts legitimes
- PHYSICS_B_SWEEP_FADE_BOOST
- PHYSICS_C_VOID_BOOST
- PHYSICS_A_DELTA_CONFIRM_BOOST
- PHYSICS_D_ABSORPTION_REENTRY

Ces reason codes sont proposes dans le changelog microstructure. fileciteturn7file13turn7file17

## 6.4 Ranking economique

ScoreRank_i = w1 * S_eff,i + w2 * CEexp_i - w3 * CostEst_i - w4 * CorrLoad_i

### Commentaire critique
Le ranking ne doit jamais choisir le plus beau setup si :
- il est trop cher
- il bloque du capital longtemps
- il ajoute de la redondance portefeuille

Le canon insiste deja sur le ranking economique et portefeuille. fileciteturn7file18

---

# 7. Formules par moteur

## 7.1 Moteur A — Delta-confirmed premium trend

Le moteur A reste premium trend, mais il doit maintenant distinguer :
- trend visible par le prix
- trend reellement porte par l'agression

### TrendScore_A
TrendScore_A = a1 * StructureTrend + a2 * RegimeFit + a3 * DeltaConfirm + a4 * CostQuality

### Delta confirmation
DeltaConfirm = tanh(CumDelta_t / ScaleDelta)

### Divergence block
Si sign(Return_L) != sign(CumDelta_L) et |Return_L| > r_min :
HardBlock_A = 1

### Esperance moteur A
g_A = f_A(ContinuationQuality, RegimeFit, CostWindow, LiquiditySupport)

### Usage
- conviction haute
- taille potentiellement plus haute
- refus si le move n'est qu'un retrait de liquidite passive

## 7.2 Moteur B — Sweep fade / return to POC

Le manifeste a raison : le vrai B 2026 ne doit pas mean-revert "dans le vide". Il doit mean-revert apres evenement physique credible. fileciteturn7file8turn7file13

### B_score
B_score = b1 * ExcessToPOC + b2 * SweepSignal + b3 * ReversalFlow + b4 * CostTightness

### Ecart au centre de gravite
ExcessToPOC = |p_t - POC_t| / max(ATR_t, eps)

### SweepSignal
SweepSignal = 1 si SweepEvent recent de sens oppose, sinon 0

### Reversal flow
ReversalFlow = -sign(sweep_direction) * DOFI_t

### Target principale
Target_B = POC_t

### Stop principal
Stop_B = SweepExtreme +/- Buffer

## 7.3 Moteur C — Void traverse breakout

Le moteur C ne doit pas breakout une ligne de prix. Il doit traverser un vrai vide de liquidite. Le manifeste et le changelog ont raison sur ce point. fileciteturn7file8turn7file13

### C_score
C_score = c1 * BreakoutStructure + c2 * VoidScore + c3 * FlowSupport - c4 * WallRisk - c5 * CostEst

### Regle cle
Si nearest_hvn est trop proche dans la direction du breakout :
HardBlock_C = 1

### Boost legitime
Si VoidScore_t > theta_void :
C_score = C_score * BoostVoid

### Stop C
Stop_C = bord d'entree du vide ou dernier mur valide

## 7.4 Moteur D — Absorption re-entry

Le moteur D doit re-engager seulement si le marche a montre qu'un niveau defend encore l'hypothese initiale. C'est coherent avec le Build-16 canonique, qui refuse tout revenge trading automatise. fileciteturn0file26

### D_score
D_score = d1 * ReformationQuality + d2 * AbsorptionScore + d3 * FlowRecovery - d4 * SaturationPenalty

### Gate critique
Absorption recent obligatoire proche du niveau d'invalidation ou du niveau de retest.

### Lien economique marginal
MarginalValue_D = EV_reentry - EV_no_reentry

D n'est admissible que si :
MarginalValue_D > 0

---

# 8. Portefeuille et diversification reelle

Le canon veut de la diversite reelle d'edge, pas un faux multi-edge. fileciteturn7file4turn7file19

## 8.1 Correlation load

CorrLoad_i = Sum_j w_j * rho_ij

## 8.2 Effective edge diversity

### Formule simple type Herfindahl inverse
K_eff = 1 / Sum_k pi_k^2

ou pi_k est la contribution relative de chaque famille d'edge.

### Interpretation
- K_eff faible : fausse diversification
- K_eff eleve : plusieurs moteurs / paires contribuent reellement

Le canon fait deja de K_eff un critere de go/no-go Complete. fileciteturn7file4

## 8.3 Risk contribution

RC_i = w_i * (Sigma * w)_i / max(w' * Sigma * w, eps)

Cette formule est plus Complete / Build-14 enrichi, pas necessaire en Light initiale.

---

# 9. Meta / monitoring / validation

Le canon impose DTR, CRA, break-even, edge tracker prudent et dashboards honnêtes. fileciteturn7file10turn7file14

## 9.1 Decision Trace Record enrichi

Pour chaque opportunite i, enregistrer :
- S_raw,i
- Pen_i
- HardBlock_i
- CostEst_i
- CEexp_i
- reason_codes
- POC / HVN / LVN / Sweep / Absorption / CumDelta

## 9.2 Sterilization rate

SterRate = N_phantom / max(N_candidates, 1)

## 9.3 Pass-rate economique

EconPass = N_{EV_net > 0} / max(N_candidates, 1)

## 9.4 Shadow parity score

Parity = N_{same decisions local vs shadow} / max(N_compared, 1)

Le plan local/VPS canonique insiste justement sur l'identite logique entre replay et VPS. fileciteturn0file30

## 9.5 Friction regret

FrictionRegret = Sum_i max(0, EV_gross_i - EV_net_i)

Permet de mesurer combien de PnL theoriquement bon est tue par la microstructure.

---

# 10. Calibration pratique recommande

## 10.1 Fenetres utiles

- 1m : friction, sweep, absorption, delta court
- 5m : confirmation de contexte local
- 15m : inventaire / pression cumulative / qualite de move
- 1h : POC local, spread regime, regime utile
- 24h : volume profile rolling, HVN/LVN structurants

## 10.2 Parametres a calibrer, pas a sacraliser

- alpha de Value Area
- seuil de VoidScore
- multiplicateur de spread widen
- coefficients k1 / k2 du slippage proxy
- buffer de liquidity stop
- fenetre de validite d'un SweepEvent
- fenetre de validite d'un AbsorptionEvent

## 10.3 Ce qui doit rester Shadow-only d'abord

- AbsorptionScore trop complexe
- RC_i complet via matrice robuste
- classification fine des faux sweeps
- heuristiques microprice multi-niveaux trop sensibles

---

# 11. Ce qu'il faut garder, declasser, remplacer

## 11.1 Garder

- ATR comme normalisateur local de volatilite
- moyennes locales comme fallback / baseline
- regime simple stable
- hard/soft/rank canonique
- gross cap / loss cap / beta / cluster / drawdown

## 11.2 Declasser

- ATR-stop pur
- mean reversion basee seulement sur MA / RSI
- breakout prix pur sans lecture de vide ou mur
- scoring trop centre sur la geometrie du prix

## 11.3 Remplacer au centre

- moyenne locale principale -> POC / Value Area
- breakout lineaire -> void traverse logic
- invalidation geometrique pure -> liquidity stop
- edge brut -> edge net apres friction
- lecture prix pure -> lecture prix + flux + topographie + cout

---

# 12. Verdict mathematique final

La V5.3 cible la plus mature ne doit plus etre formulee comme :

"trouver des signaux de prix puis verifier si on peut survivre"

mais comme :

"lire d'abord la topographie de liquidite, la pression de flux et la friction,
puis n'autoriser les signaux A / B / C / D que s'ils restent
monetisables, explicables et defensables apres couts"

Autrement dit :

- le prix devient une surface visible
- la liquidite devient la structure reelle
- la friction devient le juge final
- le portefeuille devient l'arbitre economique
- le meta devient la preuve de non-illusion

C'est la forme mathematique la plus credible de l'evolution V5.3 dans la direction que tu vises :
- compatible avec le canon
- plus moderne
- plus difficile a predator
- plus honnete economiquement
- mieux adaptee a petit capital + VPS

