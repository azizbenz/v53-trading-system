# Calibration Methods — Spec mathématique des seuils dynamiques

> **Statut** : fichier `13` du dossier `production_deployment_plan/`. Spécification mathématique des méthodes de calibration pour chaque seuil recensé dans `11_DYNAMIC_THRESHOLDS_CATALOG.md`.
>
> **Date** : 2026-04-09. Auteur : Opus en mode planification.
>
> **Niveau** : production-safe / quant PhD / trader senior PhD / PhD algebra / PhD fintech / PhD developer.
>
> **Règle dure** : ce MD est un cadrage. Le repo gagne. Aucune méthode listée ici n'est implémentée à l'aveugle si le repo réel a déjà une convention différente. L'agent codeur remonte tout écart, ne le résout pas silencieusement.
>
> **Ce MD ne traite pas** :
> - où vit la calibration → `12_LOCAL_LAB_VS_VPS_SEPARATION.md`
> - comment l'artefact est signé → `12_...` § 6
> - comment l'artefact est consommé → `src/calibration_loader/` (W2)
> - les critères de **promotion** entre paliers Shadow → `14_SHADOW_GATE_MATH.md`

---

## 0. Format MD standardisé

Ce fichier suit le gabarit Opus (`00_README.md` § 0) :
- Objectif
- Périmètre
- Invariants
- Modules touchés
- Interfaces d'entrée/sortie
- Ce qu'il ne faut **pas** faire
- Critères d'acceptation
- Ordre de réalisation
- Preuves / tests attendus

---

## 1. Objectif

Fournir, pour chaque `threshold_id` du catalogue `11_...`, **une** méthode statistique précise qui :

1. produit une **valeur** + un **intervalle de confiance**
2. respecte des **invariants math production-safe** (no look-ahead, no silent fallback, no fat-tail naïf)
3. est **reproductible** (seed, hash data, version code)
4. est **auditable** (rapport JSON normalisé)
5. **ne peut jamais** assouplir un hard cap humain défini en `10_DECISIONS_REQUIRED.md`

---

## 2. Périmètre

**Inclus** :
- méthode statistique par **catégorie** de seuil (EDGE / RISK / REGIME / EXECUTION / HALAL / SHADOW / SCALING / INFRA)
- bornes de robustesse (bootstrap, walk-forward, EVT)
- correction des biais (multiple testing, snooping, survivorship)
- handling des cas dégénérés
- format normalisé d'un rapport de calibration

**Hors périmètre** :
- spécification du JSON exact de l'artefact (déjà couverte par W2 `src/calibration_loader/contracts.py`)
- déploiement de l'artefact (`12_...`)
- critères mathématiques de promotion entre paliers Shadow (`14_...`)
- code Python d'implémentation (responsabilité agent codeur)

---

## 3. Invariants mathématiques (production-safe)

Ces invariants sont **durs**. Toute méthode de ce MD les respecte ; toute méthode future doit les respecter.

| # | Invariant | Pourquoi |
|---|---|---|
| **MI-1** | **No look-ahead.** Toute fenêtre de calibration utilise strictement $t < T_{\text{decision}}$. | Évite la fuite d'information future. |
| **MI-2** | **No silent fallback.** Si la méthode ne converge pas ou échoue un diagnostic, l'artefact est **rejeté**, jamais remplacé par une valeur par défaut. | Cohérent avec INV-2/INV-3 de `12_...` |
| **MI-3** | **No single-point estimator.** Tout seuil est publié avec un IC bootstrap (95% par défaut). | Élimine les valeurs aberrantes ponctuelles. |
| **MI-4** | **No survivorship bias.** L'univers historique au temps $t$ est exactement l'univers tradable au temps $t$ (pas l'univers actuel rétrojeté). | Évite la sur-estimation de l'edge. |
| **MI-5** | **Embargo + purging.** Les fenêtres train/val/test ont un gap d'au moins le horizon max d'un trade, doublé. | López de Prado, anti-leakage temporel. |
| **MI-6** | **DSR ≥ 0.95.** Tout seuil dérivé d'un Sharpe ou d'un return moyen passe le **Deflated Sharpe Ratio** (Bailey-López de Prado) ≥ 0.95. | Anti-backtest overfitting. |
| **MI-7** | **Hard caps win.** Une calibration ne peut **jamais** assouplir un hard cap humain. Elle peut uniquement **resserrer**. | Safety floor humain (10_...). |
| **MI-8** | **Reproducibility.** Tout rapport contient seed RNG, hash data, commit code, version méthode. | Audit-ready. |
| **MI-9** | **Stationarity check.** Toute série utilisée pour calibrer un quantile passe **deux** tests : ADF (rejet de H0 unit-root) **et** KPSS (non-rejet de H0 stationnarité). | Détecte régime change. |
| **MI-10** | **Fat-tail aware.** Aucun seuil de risque n'utilise la normalité comme assumption. EVT (POT/GPD) ou bootstrap empirique obligatoires pour les queues. | Crypto = fat tails extrêmes. |
| **MI-11** | **Conservative rounding.** Toute valeur publiée est arrondie dans le sens conservateur (resserre, jamais relâche), 6 chiffres significatifs max. | Évite les fausses précisions. |
| **MI-12** | **Multi-test correction.** Si N seuils sont calibrés simultanément sur les mêmes données, correction Romano-Wolf step-down ou Holm-Bonferroni. | Anti data-snooping multi-hypothèses. |

---

## 4. Notation et conventions

- $r_t$ : log-return de la stratégie au temps $t$
- $R_T = \prod_t (1 + r_t) - 1$ : return cumulé
- $\mu, \sigma$ : moyenne et écart-type empiriques
- $\hat q_\alpha$ : quantile empirique de niveau $\alpha$
- $\widehat{\text{SR}} = \sqrt{n} \cdot \mu / \sigma$ : Sharpe estimé (annualiser : multiplier par $\sqrt{252}$ pour daily)
- $\text{DD}_T = \max_{0 \leq s \leq t \leq T} (V_s - V_t)/V_s$ : drawdown maximal
- $f$ : fees par leg, $s$ : spread effectif, $i$ : impact
- $\Phi$ : CDF de la normale standard
- $\text{IC}_{1-\alpha}$ : intervalle de confiance bilatéral à $1-\alpha$
- $B$ : nombre de réplicas bootstrap (défaut $B = 10\,000$)
- $L$ : block length pour stationary bootstrap (Politis-Romano), choisi par méthode Politis-White
- $n_u$ : nombre d'exceedances au-dessus du seuil $u$ en POT
- $\xi, \beta$ : paramètres de forme et d'échelle de la GPD

---

## 5. Méthodes par catégorie

### 5.1 EDGE — `THR-E01`, `THR-E02`

#### 5.1.1 `THR-E01` — `edge_minimum_multiplier`

**Énoncé** : un trade est accepté si $\text{edge}_{\text{est}} \geq k \cdot (f + s + i)$. On calibre $k$.

**Méthode** :
1. Sur historique de $N$ trades simulés (univers tradable au temps $t$, MI-4), calculer pour chaque trade $i$ :
   - $e_i$ : edge réalisé (return net)
   - $c_i = f_i + s_i + i_i$ : coût total estimé ex ante
2. Définir le ratio par trade : $\rho_i = e_i / c_i$.
3. Estimer la distribution de $\rho$ via **stationary block bootstrap** (Politis-Romano), $B = 10\,000$, $L$ via Politis-White.
4. Calibrer $k$ tel que :
$$P(\rho \geq k \mid e > 0) \geq 0.7$$
   c'est-à-dire que dans **70% des trades positifs historiques**, l'edge dépasse $k \cdot c$.
5. **Floor humain dur** : $k \geq 2.0$ (MI-7).

**Robustesse** :
- IC bootstrap 95% sur $k$. La valeur **publiée** est la **borne supérieure** de l'IC (conservatif).
- Walk-forward sur $\geq 5$ plis non chevauchants, embargo $= 2 \times h_{\max}$ (horizon max trade).
- Si la dispersion inter-plis dépasse 30%, **rejet** (régime instable, MI-9 violé en pratique).

**Échec / rejet** :
- $N_{\text{trades positifs}} < 200$
- ADF ne rejette pas unit-root (MI-9)
- $|k_{\text{IC haut}} - k_{\text{IC bas}}| > 0.5 \cdot k_{\text{moyen}}$ (IC trop large)

#### 5.1.2 `THR-E02` — `edge_minimum_bps` (plancher absolu)

**Méthode** :
1. Calculer $f_i + s_i + i_i$ moyens par trade sur les **90 derniers jours**, par paire et par horizon.
2. Plancher = $\hat q_{0.9}(f + s + i) + \kappa$, où $\kappa = 5$ bps de marge.
3. **Floor humain dur** : 15 bps (MI-7).

#### 5.1.3 `THR-E03` — `ce_min` par engine (Competitive Edge minimum net)

**Énoncé** : pour chaque engine $E \in \{A, B, C, D\}$ et chaque paire $p$, le trade est rejeté si $\text{CE}_{E,p} < \text{ce\_min}_{E,p}$.

**Méthode** :
1. Sur l'historique backtest par engine $E$ et paire $p$, calculer :
   $$\text{CE}_i = e_i - c_i = \text{return net}_i - (f_i + s_i + i_i)$$
   pour tous les trades positifs ($e_i > 0$).
2. Estimer la distribution de $\text{CE}_i$ via **stationary block bootstrap** (Politis-Romano), $B = 10\,000$.
3. Calibrer $\text{ce\_min}_{E,p}$ tel que :
   $$\text{ce\_min}_{E,p} = \hat q_{0.05}(\text{CE}_i^{+})$$
   c'est-à-dire le **percentile 5** de la distribution des CE positifs. Un trade doit avoir un CE ≥ au pire CE encore acceptable.
4. **Floor humain dur** (MI-7) — bornes absolues par engine :
   - Engine A : $\text{ce\_min}_A \geq 0.0001$ (1 bps)
   - Engine B : $\text{ce\_min}_B \geq 0.0002$ (2 bps, mean-reversion = CE plus serrés)
   - Engine C : $\text{ce\_min}_C \geq 0.00015$ (1.5 bps)
   - Engine D : $\text{ce\_min}_D \geq 0.00012$ (1.2 bps, linkage = CE corrélé)

**Robustesse** :
- IC bootstrap 95% sur $\text{ce\_min}$. Publier la borne **supérieure** (conservatif).
- Walk-forward sur $\geq 5$ plis. Dispersion inter-plis > 50% → **rejet**.
- Si $N_{\text{trades positifs}} < 100$ pour un engine/paire → pas de calibration pair-specific, **utiliser le floor humain**.

**Dépendance** : $c_i$ dépend de THR-E02 (edge_minimum_bps) et THR-X05 (slippage model).

#### 5.1.4 `THR-E04` — `delta_safe` par engine (marge de sécurité coût)

**Énoncé** : un trade est accepté si $\mathbb{E}[g_i \mid E, p] > \mathbb{E}[c_i \mid E, p] + \delta_{\text{safe},E}$.

**Méthode** :
1. Sur historique backtest, pour chaque engine $E$ :
   $$\Delta_i = g_i - c_i$$
   où $g_i$ = gain brut estimé, $c_i$ = coût total estimé.
2. Estimer l'**incertitude** du modèle de coût via :
   $$\hat\sigma_c = \text{std}(c_{\text{estimé}} - c_{\text{réalisé}})$$
   sur les trades shadow (si disponibles) ou walk-forward.
3. Calibrer $\delta_{\text{safe},E}$ :
   $$\delta_{\text{safe},E} = \hat q_{0.95}(\hat\sigma_c) + \hat q_{0.95}(\text{slippage tail}_{E})$$
   La marge absorbe l'erreur d'estimation des coûts + le tail du slippage (Almgren-Chriss).
4. **Floor humain dur** (MI-7) :
   - Engine A : $\delta_{\text{safe},A} \geq 0.0005$ (5 bps)
   - Engine B : $\delta_{\text{safe},B} \geq 0.0008$ (8 bps, mean-reversion = fenêtres courtes = slippage volatile)
   - Engine C : $\delta_{\text{safe},C} \geq 0.0005$ (5 bps)
   - Engine D : $\delta_{\text{safe},D} \geq 0.0005$ (5 bps)

**Robustesse** :
- En shadow : comparer $\delta_{\text{safe}}$ calibré vs $|\hat c - c_{\text{réel}}|$ réalisé. Si la marge est dépassée dans > 5% des cas, **recalibration urgente**.
- Walk-forward avec embargo.

**Interaction** : $\delta_{\text{safe}}$ est mathématiquement le "tampon" entre THR-E03 (ce_min) et le break-even réel.

---

### 5.2 RISK — `THR-R01` à `THR-R05`

#### 5.2.1 `THR-R01` — `daily_loss_breaker` (% equity max perdu en 1 jour)

**Méthode (POT / GPD, EVT)** :
1. $L_t$ = perte journalière cumulée historique de la stratégie en backtest.
2. Choisir un seuil $u$ via **Hill plot** (ou Mean Excess Plot) tel que la GPD soit visuellement plate.
3. Récupérer les exceedances $X_i = -L_{(i)} - u$ pour $-L_{(i)} > u$.
4. Ajuster une GPD :
$$F_u(x) = 1 - \left(1 + \xi \frac{x}{\beta}\right)^{-1/\xi}, \quad x \geq 0$$
   par maximum de vraisemblance.
5. Estimer le quantile $\text{VaR}$ à 99.5% :
$$\widehat{\text{VaR}}_{0.995} = u + \frac{\hat\beta}{\hat\xi}\left[\left(\frac{n_u}{n}(1 - 0.995)\right)^{-\hat\xi} - 1\right]$$
6. Le breaker est fixé à $\widehat{\text{VaR}}_{0.995}$.
7. **Hard cap humain** (10_..., D-04 / D-05) : −2% du capital. La calibration ne peut que **resserrer** (MI-7).

**Robustesse** :
- IC sur $\xi$ et $\beta$ via vraisemblance profilée.
- **Refus** si $\hat\xi > 1$ (variance infinie, GPD pas exploitable).
- **Refus** si $n_u < 30$ exceedances (échantillon trop petit).
- Cross-validation par bootstrap : 100 réplicas du fit, dispersion de $\widehat{\text{VaR}}_{0.995}$ < 20% du moyen.

#### 5.2.2 `THR-R02`, `THR-R03` — `weekly_breaker`, `monthly_breaker`

Même méthode POT/GPD, sur fenêtres roulantes hebdo et mensuelles.

**Hard caps humains** :
- weekly : −5% du capital
- monthly : −10% du capital

#### 5.2.3 `THR-R04`, `THR-R05` — exposure caps (position cap, concurrent cap)

**Méthode (Kelly fractionnel + shrinkage)** :
$$f^* = \frac{\hat\mu}{\hat\sigma^2}, \qquad f_{\text{used}} = \lambda \cdot f^*$$
avec $\lambda = 0.25$ (quart-Kelly), choisi pour absorber l'erreur d'estimation de $\mu, \sigma$.

**Robustesse** : test de stabilité de $f^*$ sur 5 plis walk-forward. Si la dispersion > 50%, on remplace $\hat\mu$ par sa **borne basse** d'IC bootstrap.

**Hard caps humains** :
- `THR-R04` : position cap dur à 20% du capital sur une seule position
- `THR-R05` : 5 positions max simultanées

#### 5.2.4 `THR-W01`, `THR-W02` — drawdown runtime guards (warning / observe)

**Contexte** : distincts de THR-R01 (daily PnL breaker). THR-W01/W02 agissent dans `risk_runtime.py` (gate temps réel), pas dans le breaker (post-facto).

- **THR-W01** ($\theta_w$) : drawdown intra-session → `OBSERVE_ONLY` (le runtime laisse passer mais log un warning).
- **THR-W02** ($\theta_o$) : drawdown intra-session → `REDUCE_EXPOSURE` (le runtime réduit l'exposition).

**Méthode** :

1. Définir la série des **max drawdowns intra-session** historiques :
   $$D_t = \frac{\text{equity}_t - \text{peak}_t}{\text{peak}_t}$$
   mesurée sur chaque session backtest (1 jour = 1 session).

2. Estimer la distribution de $|D_t|$ :
   - Si $|D_t|$ est fat-tailed (test d'Anderson-Darling sur GPD, $p < 0.05$), utiliser **EVT/POT** :
     $$\theta_w = \hat q_{0.70}(|D_t|), \qquad \theta_o = \widehat{\text{VaR}}_{0.99}(|D_t|)$$
   - Si $|D_t|$ est thin-tailed (normal-like), utiliser les quantiles empiriques bootstrap :
     $$\theta_w = \hat q_{0.70}(|D_t|), \qquad \theta_o = \hat q_{0.95}(|D_t|)$$

3. **Contrainte structurelle** : $\theta_o / \theta_w \geq 1.5$ (éviter le collapse warning→observe).
   Si violé, élargir $\theta_o$ à $1.5 \times \theta_w$.

4. **Floors humains durs** (MI-7) :
   - $\theta_w \geq 0.015$ (1.5%, sinon alerts en permanence sur du bruit)
   - $\theta_o \geq 0.03$ (3%, sinon réduction d'exposition intempestive)
   - Defaults : $\theta_w = 0.02$, $\theta_o = 0.04$

5. **Caps humains** :
   - $\theta_w \leq 0.05$ (5%, sinon le warning arrive trop tard)
   - $\theta_o \leq 0.08$ (8%, sinon le reduce arrive trop tard)

**Robustesse** :
- Bootstrap stationnaire (Politis-Romano), $B = 5\,000$, IC 95% sur $\theta_w$ et $\theta_o$.
- Walk-forward sur $\geq 5$ plis. Dispersion > 40% → **rejet** (régime de drawdown instable).
- **En shadow** : compter le nombre de jours `OBSERVE_ONLY` et `REDUCE_EXPOSURE`. Si taux OBSERVE > 30% ou REDUCE > 10%, **recalibrer** (seuils trop serrés).

**Injection runtime** : au boot, `CalibrationLoader.get("THR-W01")` → `RiskLimits(drawdown_warning_threshold_pct=...)`.

---

### 5.3 REGIME — `THR-RG01` à `THR-RG04`

**Méthode (clustering robuste)** :

1. Construire un vecteur d'état marché par bar :
$$\vec s_t = \left(\sigma_{20,t},\ \text{ADX}_{14,t},\ \frac{\text{vol}_t}{\overline{\text{vol}}_{20}},\ s_{\text{rel},t},\ |\rho_{20,t}^{\text{BTC,ALT}}|\right)$$
2. Estimer $\vec\mu, \Sigma$ via **MCD (Minimum Covariance Determinant)** de Rousseeuw (robuste aux outliers).
3. Standardiser via **Mahalanobis** : $d^2_t = (\vec s_t - \vec\mu)^\top \Sigma^{-1} (\vec s_t - \vec\mu)$.
4. Définir $K \in \{2, 3, 4\}$ régimes via **Gaussian Mixture Model** sur $\vec s_t$, sélectionner $K^*$ par **BIC**.
5. Les seuils `THR-RG01..04` sont les **frontières de décision** entre clusters (centroïdes ± rayons).

**Robustesse** :
- **Stabilité** : 100 bootstraps sur $\vec s_t$. Si la frontière entre 2 clusters varie de plus de 15% sur ces réplicas, **rejet**.
- **Refit hebdomadaire** en backtest sur fenêtre roulante 180 jours, vérifier que les régimes restent identifiables (taux d'attribution stable).
- **Continuité temporelle** : ajout d'un Markov chain prior pour éviter les transitions instantanées (HMM-style smoothing avec persistence > 4 bars).

---

### 5.4 EXECUTION — `THR-X01` à `THR-X05`

#### 5.4.1 `THR-X01` — NTP offset max acceptable

**Méthode** :
1. Mesurer offset $o_t$ entre horloge locale et `serverTime` Binance sur $\geq 7$ jours.
2. Filtrage **Hampel** ($k = 3$, fenêtre 60 s) pour purger les outliers.
3. Seuil = $\hat q_{0.999}(|o|) + 200\text{ ms}$ marge.
4. **Hard cap humain** : 1 seconde dur. Au-delà, runtime refuse de trader.

#### 5.4.2 `THR-X02` — WebSocket gap max acceptable

**Méthode** :
1. Sur $\geq 30$ jours de WS Binance, mesurer les inter-arrival times $\Delta t_i$.
2. Distribution = mélange exponentiel approximatif.
3. Seuil "gap suspect" = $\hat q_{0.9999}(\Delta t)$, **borné supérieurement à 5 secondes**.
4. Au-delà, déclencher reconciliation REST + alerte.

#### 5.4.3 `THR-X03` — rate limit budget (token bucket)

**Méthode (Little's law)** :
- $L = \lambda \cdot W$ avec $L$ tokens en cours, $\lambda$ rate moyen, $W$ temps de service moyen.
- Capacité bucket = $\lambda \cdot \text{burst\_horizon} \cdot 1.5$ (marge 50%).
- **Hard cap humain** : 80% du quota Binance officiel (jamais 100%).

#### 5.4.4 `THR-X04` — spread guard (max relative spread)

**Méthode** :
- $s_{\text{rel}, i} = (\text{ask}_i - \text{bid}_i)/\text{mid}_i$
- Distribution log-normale en première approximation : tester par Q-Q plot.
- Seuil = $\exp(\hat\mu_{\log s} + 2\hat\sigma_{\log s})$ sur 30 jours, refit hebdomadaire.
- **Hard cap humain** : 50 bps dur.

#### 5.4.5 `THR-X05` — slippage model (Almgren-Chriss / Kyle)

**Méthode** :
$$\text{slip}_i = \eta \cdot \frac{v_i}{\text{ADV}_i} + \gamma \cdot \sqrt{v_i} + \varepsilon_i$$
- Estimation par OLS robuste (Huber, $k = 1.345$).
- Validation : $R^2 > 0.3$ minimum, sinon **rejet**.
- Le slippage estimé alimente le calcul de $i$ dans `THR-E01`.

---

### 5.5 HALAL — `THR-H01` à `THR-H03`

#### 5.5.1 `THR-H01` — purification ratio cap

**Méthode déterministe (normative, pas statistique)** :
$$\text{purif\_rate}_{\text{token}} = \frac{\text{revenu\_haram\_estimé}}{\text{revenu\_total}}$$
- Cap dur : **5%** (référence AAOIFI Sharia Standard 21).
- Au-delà, paire **haram** → exclue (enforcement par sharia layer, T5).

**Pas de calibration statistique.** C'est un seuil normatif, fixé par doctrine (D-02).

#### 5.5.2 `THR-H02` — interdiction features compte

Liste binaire d'API endpoints scannés par `account_features_audit` :
- `/sapi/v1/margin/*` (margin)
- `/sapi/v1/futures/*` (futures)
- `/sapi/v1/savings/*` (Earn / interest)
- `/sapi/v1/lending/*`
- `/sapi/v1/staking/*` (selon doctrine D-02)

**Pas de calibration.** Enforcement déterministe.

#### 5.5.3 `THR-H03` — screening de paire (ratios financiers AAOIFI)

Ratios fixes (référence AAOIFI / Usmani, à confirmer en D-02) :
- $\text{debt}/\text{total assets} \leq 33\%$
- $\text{cash + interest-bearing}/\text{total assets} \leq 33\%$
- $\text{interest income}/\text{total revenue} \leq 5\%$

**Pas de calibration statistique.** Source = audit token + screening providers (ex: Wahed, Zoya).

---

### 5.6 SHADOW — `THR-S01` à `THR-S06`

> Les seuils de promotion entre paliers Shadow (1m → 2m → 3m) sont **entièrement** spécifiés dans `14_SHADOW_GATE_MATH.md`.
>
> Ce paragraphe ne fait que rediriger pour éviter la duplication. Aucun calcul ici — sauf `THR-S06` ci-dessous.

#### 5.6.1 `THR-S06` — `max_allowed_ce_net_drop` (dégradation CE shadow vs backtest)

**Énoncé** : le gate shadow compare le Competitive Edge net moyen réalisé en shadow ($\overline{\text{CE}}_{\text{shadow}}$) à celui du backtest ($\overline{\text{CE}}_{\text{backtest}}$). Si la dégradation dépasse un seuil, le gate échoue.

**Méthode** :
1. Calculer la différence :
   $$\Delta\text{CE} = \overline{\text{CE}}_{\text{shadow}} - \overline{\text{CE}}_{\text{backtest}}$$
2. Le gate échoue si $\Delta\text{CE} < -\text{THR-S06}$.
3. Calibration de THR-S06 :
   - Sur les 5 walk-forward folds du backtest, calculer la variabilité inter-fold :
     $$\hat\sigma_{\text{CE}} = \text{std}(\overline{\text{CE}}_{\text{fold}_1}, \ldots, \overline{\text{CE}}_{\text{fold}_5})$$
   - THR-S06 = $2 \times \hat\sigma_{\text{CE}}$ (dégradation au-delà de 2σ inter-fold = anormale).
4. **Floor humain dur** : THR-S06 $\geq 0.0003$ (3 bps, sinon trop de faux rejets).
5. **Cap humain** : THR-S06 $\leq 0.0015$ (15 bps, sinon on tolère trop de dégradation).
6. **Default** : 0.0005 (5 bps).

**Robustesse** :
- Bootstrap sur $\hat\sigma_{\text{CE}}$ : IC 95%.
- Si le nombre de trades shadow < 50, **élargir** THR-S06 d'un facteur $\sqrt{50/N_{\text{shadow}}}$ pour compenser la variance d'échantillon.

---

### 5.7 SCALING — `THR-SC01` à `THR-SC04`

**Méthode (sizing par paliers PSR-validés)** :
1. À chaque palier $n$, calculer le **Probabilistic Sharpe Ratio** sur les returns réels :
$$\text{PSR}(\text{SR}^*) = \Phi\left(\frac{(\widehat{\text{SR}} - \text{SR}^*) \sqrt{n - 1}}{\sqrt{1 - \hat\gamma_3 \widehat{\text{SR}} + \frac{\hat\gamma_4 - 1}{4}\widehat{\text{SR}}^2}}\right)$$
2. Si $\text{PSR}(0) \geq 0.95$ sur le palier $n$, **autoriser** $\text{capital}_{n+1} = \text{capital}_n \cdot (1 + g)$.
3. $g = 0.5$ (palier de +50%) par défaut.
4. **Hard cap humain** : pas plus de +30% par palier tant que $T_{\text{cumul live}} < 90$ jours.

#### 5.7.1 Liste des seuils
- `THR-SC01` : PSR floor par palier (0.95)
- `THR-SC02` : croissance de capital par palier ($g$)
- `THR-SC03` : durée minimale par palier ($\tau \geq 14$ jours)
- `THR-SC04` : nombre maximal de paliers consécutifs sans recalibration ($\leq 4$)

---

### 5.8 INFRA — `THR-I01` à `THR-I04`

**Méthodes opérationnelles** (pas de stat avancée, ce sont des seuils techniques) :

| Seuil | Méthode |
|---|---|
| `THR-I01` disk warn | $0.80 \times \text{capacity}$ |
| `THR-I02` disk block | $0.90 \times \text{capacity}$ |
| `THR-I03` log retention | $\overline{\text{taille\_jour}} \times N_{\text{jours}} \times 1.5$ |
| `THR-I04` reconciliation lag max | $p_{99}$ historique des delays + 30 s marge |

---

## 6. Robustesse, bias correction, multiple testing

### 6.1 Stationary block bootstrap (Politis-Romano)

Pour chaque réplica $b \in \{1, \ldots, B\}$ :
1. Tirer un point de départ uniforme $i_1 \in \{1, \ldots, n\}$.
2. Tirer une longueur de bloc $L_b \sim \text{Geom}(1/L)$ où $L$ est l'espérance.
3. Empiler les blocs jusqu'à atteindre $n$ observations.
4. Calculer la statistique d'intérêt sur ce réplica.

**Choix automatique de $L$** (Politis-White, 2004) : maximiser un critère d'autocorrélation tronquée.

### 6.2 Walk-forward avec embargo et purging (López de Prado)

1. Diviser la fenêtre historique en $K$ plis temporels.
2. Pour chaque pli $k$ :
   - **train** sur $[T_0, T_k - \text{embargo}]$
   - **embargo** sur $[T_k - \text{embargo}, T_k]$ (gap = $2 \times h_{\max}$ trade)
   - **validation** sur $[T_k, T_{k+1}]$
3. Aucune information de validation ne peut influencer le train.
4. **Purging** : retirer du train tout label dont l'horizon recouvre la validation.

### 6.3 Multiple testing : Romano-Wolf step-down

Si $N$ seuils sont calibrés sur **les mêmes données**, appliquer Romano-Wolf step-down sur les p-values (au lieu de Bonferroni qui est trop conservateur). Si les calibrations sont **indépendantes** (data windows disjointes), pas de correction nécessaire.

### 6.4 Anti-snooping : OOS reservation

Split historique : **70% train, 15% validation, 15% test réservé**.
- Le test réservé n'est **jamais touché** avant le gate `G2.3` (passage 3m → MICRO_LIVE).
- Toute calibration touchant le test réservé invalide la séquence et exige un reset complet.

---

## 7. Anti-overfitting : Deflated Sharpe Ratio (Bailey-López de Prado, 2014)

Tout seuil dérivé d'un Sharpe ou d'un return moyen passe :

$$\text{DSR} = \Phi\left(\frac{(\widehat{\text{SR}} - \text{SR}^*) \sqrt{n - 1}}{\sqrt{1 - \hat\gamma_3 \widehat{\text{SR}} + \frac{\hat\gamma_4 - 1}{4}\widehat{\text{SR}}^2}}\right)$$

avec $\text{SR}^*$ ajusté par le nombre $N$ de stratégies/configurations testées :

$$\text{SR}^* = \sqrt{\widehat{\mathbb{V}}[\widehat{\text{SR}}]} \cdot \left((1 - \gamma_E)\Phi^{-1}\!\left(1 - \tfrac{1}{N}\right) + \gamma_E\Phi^{-1}\!\left(1 - \tfrac{1}{N \cdot e}\right)\right)$$

où $\gamma_E \approx 0.5772$ est la constante d'Euler-Mascheroni.

**Règle** : seuil accepté seulement si $\text{DSR} \geq 0.95$ (MI-6).

$\hat\gamma_3, \hat\gamma_4$ sont les estimateurs de skewness et kurtosis des returns. Pour des distributions très asymétriques (crypto), utiliser leurs versions robustes (Hosking L-moments).

---

## 8. Stress tests obligatoires avant signature

Avant qu'un humain signe `calibration_vN.json`, l'artefact passe les **5 stress tests** suivants. **Un seul échec** = rejet.

| # | Stress test | Critère de réussite |
|---|---|---|
| ST-1 | Replay sur **régime calm** historique | Aucun hard cap humain dépassé. PSR(0) > 0.6. |
| ST-2 | Replay sur **régime trend** historique | Aucun hard cap humain dépassé. PSR(0) > 0.6. |
| ST-3 | Replay sur **régime chaos** (incl. flash crash 2024-Q1, BTC dump 2025-Q1) | Aucun hard cap humain dépassé. Max DD ≤ hard cap mensuel. |
| ST-4 | Replay avec **WS gap injecté** (15 s), **API latency injectée** (p99 = 2 s) | Pas d'ordre orphelin. Reconciliation OK en < 60 s. |
| ST-5 | Replay avec **fee schedule × 1.5** | Edge gate filtre sans crash. PnL net reste positif ou perte ≤ hard cap mensuel. |

---

## 9. Format normalisé d'un rapport de calibration

(Compatible avec `src/calibration_loader/contracts.py` produit en W2.)

```jsonc
{
  "artefact_version": "calibration_v3",
  "produced_at": "2026-04-09T14:33:00Z",
  "produced_by": "local_ia_lab/azizbez",
  "data_window": {"start": "2024-01-01", "end": "2026-03-31"},
  "method_per_threshold": {
    "THR-E01": {
      "method": "stationary_block_bootstrap",
      "B": 10000,
      "block_length_L": 7,
      "block_length_method": "politis_white",
      "n_trades": 1247,
      "rho_estimator": "P(rho >= k | e>0) >= 0.7",
      "value_point": 2.18,
      "ic95_lower": 1.92,
      "ic95_upper": 2.41,
      "published_value": 2.41,
      "rounding": "conservative_up",
      "hard_cap_human": 2.0,
      "hard_cap_satisfied": true,
      "stress_tests": {"ST-1": "pass", "ST-2": "pass", "ST-3": "pass", "ST-4": "pass", "ST-5": "pass"},
      "stationarity": {"adf_pvalue": 0.003, "kpss_pvalue": 0.18},
      "dsr_check": "n/a"
    },
    "THR-R01": {
      "method": "POT_GPD",
      "u": 0.012,
      "u_selection": "hill_plot_visual",
      "n_exceedances": 47,
      "xi_hat": 0.31,
      "xi_ic95": [0.18, 0.44],
      "beta_hat": 0.008,
      "beta_ic95": [0.006, 0.011],
      "var_99_5": 0.0185,
      "var_99_5_ic95": [0.0162, 0.0211],
      "published_value": 0.0185,
      "hard_cap_human": 0.02,
      "hard_cap_satisfied": true,
      "stress_tests": {"ST-1": "pass", "ST-2": "pass", "ST-3": "pass", "ST-4": "pass", "ST-5": "pass"},
      "stationarity": {"adf_pvalue": 0.001, "kpss_pvalue": 0.22},
      "dsr_check": "n/a"
    }
    // ... autres seuils
  },
  "global_dsr": 0.97,
  "multi_test_correction": "romano_wolf_stepdown",
  "oos_reservation": {"train_share": 0.7, "val_share": 0.15, "test_reserved_share": 0.15, "test_reserved_touched": false},
  "reproducibility": {
    "rng_seed": 20260409,
    "data_hash_sha256": "abc123...",
    "code_commit": "v53@a1b2c3d",
    "method_version": "calibration_methods_v1"
  },
  "signature": {
    "algorithm": "ed25519",
    "signed_by": "human_operator",
    "signed_at": "2026-04-09T15:00:00Z",
    "signature": "..."
  }
}
```

---

## 10. Ce qu'il ne faut **pas** faire

| # | Interdiction | Pourquoi |
|---|---|---|
| NO-1 | Ne pas remplacer un rejet par une valeur "raisonnable par défaut". | Viole MI-2 (no silent fallback). |
| NO-2 | Ne pas utiliser une distribution normale pour calibrer un seuil de queue (VaR, breaker, drawdown). | Viole MI-10 (fat-tail aware). |
| NO-3 | Ne pas calibrer plusieurs seuils sur la même fenêtre sans correction multi-test. | Viole MI-12. |
| NO-4 | Ne pas toucher au test reservé (15% OOS) avant `G2.3`. | Viole § 6.4. |
| NO-5 | Ne pas publier une valeur ponctuelle sans son IC bootstrap. | Viole MI-3. |
| NO-6 | Ne pas réutiliser un seed RNG entre artefacts (rendrait les bootstraps corrélés). | Empêche reproductibilité indépendante. |
| NO-7 | Ne pas calibrer le `THR-H*` (halal) statistiquement. C'est normatif. | Doctrine, pas data. |
| NO-8 | Ne pas accepter une calibration qui assouplit un hard cap humain. | Viole MI-7. |
| NO-9 | Ne pas signer un artefact qui n'a pas passé les 5 stress tests § 8. | Risque catastrophique non bordé. |
| NO-10 | Ne pas mélanger train et test dans une même fenêtre (purging obligatoire). | Viole MI-5. |

---

## 11. Critères d'acceptation

- [ ] AC-1 : chaque `threshold_id` du catalogue `11_...` a une méthode dédiée dans § 5
- [ ] AC-2 : chaque méthode produit valeur + IC bootstrap + diagnostics
- [ ] AC-3 : chaque méthode liste explicitement ses conditions de **rejet**
- [ ] AC-4 : DSR ≥ 0.95 imposé pour tous les seuils dérivés d'un Sharpe
- [ ] AC-5 : EVT (POT/GPD) imposée pour tous les seuils de queue (`THR-R01..R03`)
- [ ] AC-6 : test OOS réservé (15%) défini et non-touché avant `G2.3`
- [ ] AC-7 : 5 stress tests § 8 obligatoires avant signature
- [ ] AC-8 : format JSON normalisé § 9 compatible avec W2 contracts
- [ ] AC-9 : aucun seuil halal n'est calibré statistiquement (normatif uniquement)
- [ ] AC-10 : tout hard cap humain (`10_...`) est référencé et **respecté** dans la méthode correspondante

---

## 12. Ordre de réalisation

L'agent codeur n'a **pas** à coder ce MD entier en une fois. L'ordre logique :

1. **Préalable** : W2 (`src/calibration_loader/`) fermée → contrats prêts. ✓
2. **Étape 13-A** — implémenter la **catégorie EDGE** (méthodes 5.1) car c'est la plus directement consommée par le P0 (T6 fee-aware edge gate).
3. **Étape 13-B** — implémenter la **catégorie RISK** (méthodes 5.2) pour alimenter T10 (breakers).
4. **Étape 13-C** — implémenter la **catégorie EXECUTION** (méthodes 5.4) pour T1, T3 (Binance adapter, WS).
5. **Étape 13-D** — implémenter la **catégorie REGIME** (méthodes 5.3) pour T9 (regime lite).
6. **Étape 13-E** — implémenter le **rapport JSON normalisé** (§ 9) avec cas EDGE en premier.
7. **Étape 13-F** — implémenter les **5 stress tests** (§ 8) comme jobs déclenchables sur Local IA Lab.
8. **Étape 13-G** — categories restantes (HALAL = pas de stat, INFRA = trivial, SCALING = dépend de PSR, SHADOW = dans `14_...`).

**Aucune étape ne touche au runtime VPS.** Tout vit côté Local IA Lab.

---

## 13. Preuves / tests attendus

| Preuve | Localisation suggérée | Tranche |
|---|---|---|
| Bootstrap stationnaire produit IC stable sur série synthétique connue | `tests/test_calibration_methods/test_bootstrap.py` | 13-A |
| GPD POT retrouve le quantile vrai sur une simulation Pareto | `tests/test_calibration_methods/test_pot_gpd.py` | 13-B |
| Walk-forward refuse train/val overlap | `tests/test_calibration_methods/test_walkforward.py` | 13-A |
| DSR calcul cohérent vs paper Bailey-López de Prado | `tests/test_calibration_methods/test_dsr.py` | 13-A |
| Stress test ST-3 (chaos) catch un breaker dépassé | `tests/test_calibration_methods/test_stress_chaos.py` | 13-F |
| Rapport JSON validé par schema W2 | `tests/test_calibration_loader/test_contracts.py` (étendre) | 13-E |
| Refus d'un artefact qui assouplit un hard cap | `tests/test_calibration_methods/test_hard_cap_floor.py` | 13-A |

---

## 14. Références bibliographiques

| Méthode | Référence |
|---|---|
| Stationary block bootstrap | Politis & Romano (1994), *JASA* |
| Auto block-length | Politis & White (2004), *Econometric Reviews* |
| GPD / POT (EVT) | Coles (2001), *An Introduction to Statistical Modeling of Extreme Values* |
| Mean Excess Plot (Hill) | Embrechts, Klüppelberg, Mikosch (1997), *Modelling Extremal Events* |
| Walk-forward / embargo / purging | López de Prado (2018), *Advances in Financial Machine Learning* |
| Deflated Sharpe Ratio | Bailey & López de Prado (2014), *J. of Portfolio Management* |
| Probabilistic Sharpe Ratio | Bailey & López de Prado (2012), *J. of Risk* |
| Hansen SPA test | Hansen (2005), *J. of Business & Economic Statistics* |
| Romano-Wolf step-down | Romano & Wolf (2005), *Econometrica* |
| Almgren-Chriss execution | Almgren & Chriss (2001), *J. of Risk* |
| Kelly fractional + shrinkage | Thorp (1969) ; MacLean, Thorp, Ziemba (2010) |
| Maximum Drawdown distribution | Magdon-Ismail & Atiya (2004), *Risk Magazine* |
| MCD robust covariance | Rousseeuw (1984), *JASA* |
| Hampel filter | Hampel (1974), *JASA* |
| AAOIFI Sharia Standard 21 | AAOIFI (2017) |

---

## 15. Suite logique

- **Côté math** : `14_SHADOW_GATE_MATH.md` complète ce fichier en spécifiant les critères mathématiques de promotion entre paliers Shadow.
- **Côté code** : tranches 13-A → 13-G, déclenchées dans l'ordre par l'agent codeur sur Local IA Lab.
- **Côté humain** : la signature `calibration_vN.json` reste un acte humain explicite. Ce MD ne l'automatise pas.
