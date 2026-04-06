# V5.3 — VPS ANNEXE MATHÉMATIQUE
## Liquidité, résilience, toxicité, survivabilité d’exécution
### Date : 2026-04-04
### Statut : ANNEXE MATHÉMATIQUE VPS

---

# 0. Objet

Cette annexe mathématique formalise les équations et métriques utiles pour la **VPS V5.3** dans sa nouvelle doctrine :

- liquidité
- résilience
- toxicité
- fragmentation
- survivabilité d’exécution

Ce document ne cherche pas à accumuler des formules décoratives.  
Il ne conserve que les équations ayant une utilité opérationnelle directe pour :

- `data_backbone`
- `risk_backbone`
- `scoring_backbone`
- `engines A/B/C/D`
- `execution_backbone`
- `portfolio`
- `complete_enablers`
- `monitoring`
- `protocols`

---

# 1. Principes de lecture

## 1.1 Trois classes d’équations

### Classe A — immédiatement codables
Formules simples, robustes, directement exploitables en runtime.

### Classe B — codables mais à valider en shadow
Formules utiles, mais qui demandent calibration et test de non-régression.

### Classe C — recherche / shadow only
Formules plus sophistiquées, à ne pas mettre en runtime live sans preuve.

## 1.2 Règle d’usage

Une équation n’entre pas dans la VPS live parce qu’elle est élégante.  
Elle entre seulement si elle améliore au moins un de ces axes :

- CE
- net PnL
- réduction de dommage
- survivabilité d’exécution
- robustesse portefeuille
- explicabilité

---

# 2. Delta et flux directionnel

## 2.1 Delta proxy par barre (Classe A)

Sur granularité VPS réaliste :

\[
\Delta V_t^{proxy} = \operatorname{sign}(C_t - O_t) \cdot V_t
\]

Version plus douce :

\[
\Delta V_t^{proxy} = \frac{C_t - O_t}{\max(H_t - L_t,\epsilon)} \cdot V_t
\]

avec :
- \(C_t\) close
- \(O_t\) open
- \(H_t\) high
- \(L_t\) low
- \(V_t\) volume

## 2.2 Delta cumulé (Classe A)

\[
CD_t = \sum_{u=t-k+1}^{t}\Delta V_u^{proxy}
\]

Utilité :
- confirmation trend
- divergence prix / flux
- contexte sweep / absorption

## 2.3 Divergence prix / delta (Classe A)

\[
Div^{price,delta}_t = z\big(r_{t-k:t}\big) - z\big(CD_{t-k:t}\big)
\]

où \(z(\cdot)\) est un z-score rolling.  
Utilité :
- faux breakout
- faux trend
- fatigue de move

---

# 3. Order Flow Imbalance / Book Imbalance / Microprice

## 3.1 OFI simple (Classe A)

\[
OFI_t = V_t^{buy} - V_t^{sell}
\]

Version normalisée :

\[
OFI_t^{norm} = \frac{V_t^{buy} - V_t^{sell}}{V_t^{buy} + V_t^{sell} + \epsilon}
\]

## 3.2 Book Imbalance (Classe A)

Pour un niveau donné ou agrégation multi-niveaux :

\[
BI_t = \frac{Q_t^{bid} - Q_t^{ask}}{Q_t^{bid} + Q_t^{ask} + \epsilon}
\]

## 3.3 Multi-level Book Imbalance (Classe B)

\[
BI_t^{(L)} = \frac{\sum_{\ell=1}^{L} w_\ell Q_{t,\ell}^{bid} - \sum_{\ell=1}^{L} w_\ell Q_{t,\ell}^{ask}}
{\sum_{\ell=1}^{L} w_\ell Q_{t,\ell}^{bid} + \sum_{\ell=1}^{L} w_\ell Q_{t,\ell}^{ask} + \epsilon}
\]

avec \(w_\ell\) décroissant avec la profondeur.

## 3.4 Microprice (Classe A)

\[
MP_t = \frac{P_t^{ask}Q_t^{bid} + P_t^{bid}Q_t^{ask}}{Q_t^{bid}+Q_t^{ask}+\epsilon}
\]

## 3.5 Écart microprice / mid (Classe A)

\[
\Delta MP_t = \frac{MP_t - Mid_t}{Mid_t}
\]

Utilité :
- pression locale
- dégradation microstructure
- confirmation / invalidation de continuation

---

# 4. Volume Profile et topographie

## 4.1 Point of Control (Classe A)

Pour une fenêtre \(W\), discrétisée en niveaux de prix \(p\) :

\[
POC_W = \arg\max_p Vol(p;W)
\]

## 4.2 Value Area (Classe B)

Définir l’ensemble des prix cumulant une part \(\alpha\) du volume total, typiquement \(\alpha=70\%\).

\[
VA_W(\alpha) = \{p : \text{cumul volume autour du POC jusqu’à } \alpha\}
\]

On en déduit :
- \(VAH_W\)
- \(VAL_W\)

## 4.3 HVN / LVN (Classe B)

- HVN : nœud de volume élevé
- LVN : nœud de volume faible

En pratique :
- détecter maxima / minima locaux de \(Vol(p;W)\)
- avec seuil minimum de séparation et de masse volumique

## 4.4 Distance au POC (Classe A)

\[
d^{POC}_t = \frac{P_t - POC_W}{P_t}
\]

## 4.5 Void Score (Classe B)

Pour un corridor de prix \([P_t, P_t + \Delta]\) ou \([P_t-\Delta,P_t]\) :

\[
VoidScore_t = 1 - \frac{\int_{\mathcal{R}} Vol(p;W)\,dp}{\int_{\mathcal{R}} \overline{Vol}_W\,dp + \epsilon}
\]

Version discrète plus simple :

\[
VoidScore_t = 1 - \frac{\sum_{p \in \mathcal{R}} Vol(p;W)}{|\mathcal{R}| \cdot \overline{Vol}_W + \epsilon}
\]

Utilité :
- Engine C
- no-trade avant mur de liquidité
- sizing prudence

---

# 5. Sweep / Absorption / False Breakout

## 5.1 Sweep Score (Classe A)

Soit une bougie candidate sur 1m.

### Composante mèche :

\[
WickRatio_t = \frac{|Wick_t|}{ATR_t + \epsilon}
\]

### Composante volume :

\[
VolBurst_t = \frac{V_t}{\overline{V}_{20}(t) + \epsilon}
\]

### Composante rejet :

\[
Reject_t = \mathbb{1}\{Close_t \text{ revient dans la plage précédente}\}
\]

### Score synthétique :

\[
SweepScore_t = w_1 \cdot \min(WickRatio_t, cap_1) + w_2 \cdot \min(VolBurst_t, cap_2) + w_3 \cdot Reject_t
\]

## 5.2 Absorption Score (Classe B)

L’idée : forte agression, faible déplacement.

\[
AbsorptionScore_t = \frac{|OFI_t^{norm}|}{|\Delta P_t| + \epsilon}
\]

Version enrichie :

\[
AbsorptionScore_t^{*} = \frac{|CD_t| + \lambda_1 |OFI_t|}{|\Delta P_t| + \lambda_2 Spread_t + \epsilon}
\]

Plus ce ratio est élevé, plus le marché absorbe sans céder.

## 5.3 False Breakout Score (Classe B)

\[
FBO_t = \alpha_1 SweepScore_t + \alpha_2 AbsorptionScore_t + \alpha_3 \mathbb{1}\{d^{HVN}_t < \tau_{hvn}\} - \alpha_4 DeltaConfirm_t
\]

Utilité :
- filtrer C
- protéger B
- informer D

---

# 6. Spread, slippage, micro-friction

## 6.1 Spread relatif (Classe A)

\[
SpreadRel_t = \frac{P_t^{ask} - P_t^{bid}}{Mid_t}
\]

## 6.2 Spread Z-score (Classe A)

\[
SpreadZ_t = \frac{SpreadRel_t - \mu_{Spread,W}}{\sigma_{Spread,W} + \epsilon}
\]

## 6.3 Proxy de slippage (Classe A)

Version runtime sobre :

\[
SlipProxy_t = a_1 SpreadRel_t + a_2 \sigma_{1m,t} + a_3 \cdot Participation_t
\]

avec :

\[
Participation_t = \frac{OrderSize_t}{\overline{Vol}_{1m,t} + \epsilon}
\]

## 6.4 Micro-Friction Score (Classe A)

\[
MicroFriction_t = b_1 SpreadRel_t + b_2 SlipProxy_t + b_3 Fragility_t + b_4 Toxicity_t
\]

## 6.5 Guard de micro-friction (Classe A)

Soit une espérance moteur \(\mathbb{E}[g_i]\), un coût estimé \(\widehat{c_i}\).

\[
NetEdge_i = \mathbb{E}[g_i] - \widehat{c_i}
\]

Si :

\[
NetEdge_i < \delta_{min}
\]

alors :
- `NO_TRADE`
- ou `SIZE_REDUCE`

Version prudente :

\[
\widehat{c_i} = Fees_i + SpreadCost_i + SlipProxy_i
\]

---

# 7. Résilience et survivabilité d’exécution

## 7.1 Book Resiliency (Classe B)

Soit un choc au book à \(t_0\), et \(D_t\) une mesure de profondeur.

\[
Resiliency(\tau) = \frac{D_{t_0+\tau} - D_{t_0}}{D_{pre} - D_{t_0} + \epsilon}
\]

Version simplifiée :
- profondeur avant choc
- profondeur juste après choc
- profondeur après \(\tau\) secondes / minutes

## 7.2 Refill Speed (Classe B)

\[
RefillSpeed_t = \frac{Q_{t+\tau}^{book} - Q_t^{book}}{\tau}
\]

## 7.3 Execution Survivability Score (Classe B)

\[
ESS_t = c_1(1-SpreadZ_t^{+}) + c_2 Resiliency_t + c_3 RefillSpeed_t - c_4 Toxicity_t - c_5 Fragility_t
\]

avec \(SpreadZ_t^{+} = \max(SpreadZ_t,0)\).

Utilité :
- filtre d’entrée
- réduction de taille
- protection contre faux edge

---

# 8. Toxicité

## 8.1 Toxicity Score simplifié (Classe B)

La toxicité ne doit pas obligatoirement passer par un VPIN académique complet en runtime.

Version simple :

\[
Toxicity_t = d_1 |OFI_t^{norm}| + d_2 SpreadZ_t + d_3 VolJump_t + d_4 Fragility_t
\]

où :

\[
VolJump_t = \frac{\sigma_{1m,t}}{\overline{\sigma}_{W,t} + \epsilon}
\]

## 8.2 États de toxicité (Classe A)

Définir des états :

- `TOXICITY_NORMAL`
- `TOXICITY_ELEVATED`
- `TOXICITY_DANGEROUS`

selon seuils calibrés sur \(Toxicity_t\).

## 8.3 Utilité

La toxicité pilote :
- no-trade
- size reduction
- timeout adjustment
- downgrade de B/C/D
- prudence exécution

---

# 9. Régime enrichi

## 9.1 Hurst ou régime enrichi (Classe B)

Le régime enrichi ne sert pas à créer une cosmologie mathématique lourde.  
Il sert à savoir si une logique est compatible.

Exemple de sortie :
- `TREND_STABLE`
- `TREND_FRAGILE`
- `RANGE_EXPLOITABLE`
- `CHAOTIC_TOXIC`
- `LOW_INFORMATION`

## 9.2 Distance de régime pour artifacts (Classe B)

Soit \(x_t\) le vecteur live des features de régime, \(\mu_{train}\) la moyenne d’entraînement, et \(\Sigma_{shrunk}\) la covariance régularisée.

\[
D_M(x_t) = \sqrt{(x_t - \mu_{train})^T \Sigma_{shrunk}^{-1}(x_t - \mu_{train})}
\]

### Règle
- faible distance -> `ACTIVE`
- distance intermédiaire -> `DECAYING`
- distance forte -> `DORMANT`

## 9.3 Covariance régularisée (Classe A pour gouvernance)

\[
\Sigma_{shrunk} = (1-\alpha)\Sigma + \alpha \cdot \operatorname{diag}(\Sigma)
\]

Cette forme garantit un calcul stable même avec fortes corrélations.

---

# 10. Action units et bornes d’influence

## 10.1 Action unit obligatoire (Classe A)

Toute action distillée doit préciser son unité :

- `RAW_SCORE_MULTIPLIER`
- `RAW_SCORE_ADD`
- `CONVICTION_ADD`
- `SIZE_FACTOR`
- `RANK_DELTA`
- `TIMEOUT_FACTOR`

## 10.2 Bornes runtime (Classe A)

Pour éviter les explosions de score :

\[
S_i^{new} = \min(S_i^{cap},\; S_i^{base} \cdot m_i + a_i)
\]

où :
- \(m_i\) = multiplicateur éventuel
- \(a_i\) = ajout éventuel
- \(S_i^{cap}\) = plafond

---

# 11. Engine A / B / C / D reconditionnés

## 11.1 Engine A — Trend physiquement confirmé

Score enrichi :

\[
A_t^{phys} = A_t^{base} + \beta_1 DeltaConfirm_t - \beta_2 Fragility_t - \beta_3 Toxicity_t
\]

Utilité :
- boost si trend soutenu par flux
- downgrade si trend prix sans flux

## 11.2 Engine B — Sweep Fade / Return to POC

\[
B_t^{phys} = B_t^{base} + \gamma_1 SweepScore_t + \gamma_2 AbsorptionScore_t - \gamma_3 SpreadZ_t - \gamma_4 Toxicity_t
\]

Utilité :
- fade de sweep
- retour vers POC
- no-trade si spread/tension trop élevés

## 11.3 Engine C — Void Traverse / Breakout sous condition

\[
C_t^{phys} = C_t^{base} + \eta_1 VoidScore_t - \eta_2 HVNProximity_t - \eta_3 FBO_t - \eta_4 Fragility_t
\]

Utilité :
- boost si vrai vide
- no-trade si mur proche
- protection faux breakout

## 11.4 Engine D — Re-entry sur absorption / reformation

\[
D_t^{phys} = D_t^{base} + \theta_1 AbsorptionScore_t + \theta_2 ReformationScore_t - \theta_3 Toxicity_t - \theta_4 Overextension_t
\]

Utilité :
- réengagement discipliné
- pas de revenge trade

---

# 12. Risk backbone modernisé

## 12.1 Stop de liquidité (Classe B)

Abandon du stop purement ATR-centrique comme centre unique.

### Stop basé sur mur de liquidité

Pour un long :

\[
Stop_{liq} = HVN_{below} - \delta_{safe}
\]

Pour un short :

\[
Stop_{liq} = HVN_{above} + \delta_{safe}
\]

Fallback :
- ATR seulement si absence de mur exploitable

## 12.2 Taille à risque dollar constant (Classe A)

\[
x_i = \frac{R_{\$}}{|Entry_i - Stop_i| + c_i}
\]

où :
- \(R_{\$}\) = risque dollar autorisé
- \(c_i\) = cushion coûts / slippage prudent

## 12.3 Capital Efficiency (Classe A)

\[
CE_i = \frac{\mathbb{E}[PnL_i^{net}]}{x_i \cdot h_i + \epsilon}
\]

où \(h_i\) est l’horizon de capital immobilisé.

---

# 13. Portefeuille enrichi

## 13.1 Effective Edge Diversity (Classe B)

\[
K_{eff} = \frac{\left(\sum_{j=1}^{M} w_j\right)^2}{\sum_{j=1}^{M} w_j^2}
\]

Version opératoire : mesurer la diversité effective de l’exposition au lieu de compter naïvement les moteurs / paires.

## 13.2 Risk Contribution (Classe B)

Pour une covariance portefeuille \(\Sigma\) et un poids \(w_i\) :

\[
RC_i = w_i \cdot (\Sigma w)_i
\]

Utilité :
- éviter les illusions de diversification
- crowding
- compétition de capital

---

# 14. Métriques meta / monitoring / preuve

## 14.1 Anti-cowardice / block discipline

Soit :
- \(BR\) = block rate
- \(F_u\) = fréquence utile
- \(PnL^{net}\)

Un artifact est suspect s’il augmente fortement \(BR\) sans amélioration suffisante de \(PnL^{net}\) ou de \(CE\).

## 14.2 Friction regret (Classe A)

Soit \(P_{blocked}\) le PnL net des trades bloqués contrefactuels :

\[
FrictionRegret = -\sum P_{blocked}^{positive}
\]

La règle n’est pas :
- zéro regret absolu

La règle est :
- regret acceptable au regard du dommage évité

## 14.3 Sharpe / variance utile (Classe B)

Pour la Classe D :

\[
Sharpe = \frac{\mu_r}{\sigma_r + \epsilon}
\]

ou au minimum :

\[
VarReduction = \sigma^2_{base} - \sigma^2_{artifact}
\]

---

# 15. Règles de passage runtime

## 15.1 Read Only -> Shadow Enabled -> Limited Influence

Une métrique ne passe pas directement en live.

Elle doit suivre :

1. `READ_ONLY`
2. `SHADOW_ENABLED`
3. `LIMITED_INFLUENCE`
4. éventuellement candidat micro-live
5. éventuellement candidat live

## 15.2 Classement d’une nouvelle métrique / règle

Une règle ou métrique est rejetée si :
- elle réduit trop la fréquence utile
- elle coûte trop cher en CPU / logs
- elle est trop fragile
- elle est trop opaque
- elle ne passe pas les tests meta

---

# 16. Conclusion

Cette annexe mathématique fournit la grammaire quantitative minimale de la **nouvelle VPS V5.3**.

Elle permet de passer :

- d’une lecture prix-centrique
- à une lecture de **physique du marché**

sans transformer le runtime en laboratoire académique.

Le principe final est :

- équations simples en runtime
- enrichissement prouvé en shadow
- distillation compacte
- gouvernance forte
- survivabilité d’exécution au centre
