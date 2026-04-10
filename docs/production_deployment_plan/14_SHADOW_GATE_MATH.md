# Shadow Gate Math — Critères mathématiques de promotion 1m / 2m / 3m

> **Statut** : fichier `14` du dossier `production_deployment_plan/`. Spécification mathématique des **gates humains** entre paliers Shadow (1m → 2m → 3m → MICRO_LIVE).
>
> **Date** : 2026-04-09. Auteur : Opus en mode planification.
>
> **Niveau** : production-safe / quant PhD / trader senior PhD / PhD algebra / PhD fintech / PhD developer.
>
> **Règle dure** : ce MD est un cadrage. Le repo gagne. Aucune méthode listée ici n'est implémentée à l'aveugle si le repo réel a déjà une convention différente.
>
> **Ce MD ne traite pas** :
> - calibration des seuils dynamiques → `13_CALIBRATION_METHODS.md`
> - pipeline d'artefact signé → `12_LOCAL_LAB_VS_VPS_SEPARATION.md`
> - timing humain des phases → `07_PHASE_PLAN_0_TO_4.md`

---

## 0. Format MD standardisé

Ce fichier suit le gabarit Opus (`00_README.md` § 0).

---

## 1. Objectif

Définir, pour chaque gate de promotion humain (`G2.1`, `G2.2`, `G2.3`, `G3`), **les critères mathématiques précis** que le système doit présenter à l'humain pour décider de promouvoir le runtime au palier suivant.

Le gate reste **humain** : ce MD ne l'automatise pas. Il fournit à l'humain :
- une **batterie de tests** statistiques
- des **seuils** numériques explicites par test
- des **vetos durs** (hard fail)
- un **format de rapport** standardisé

L'humain décide. Le système calcule.

**Principe directeur** : la rigueur **augmente** à chaque palier. Au G2.1 (1m→2m) on filtre uniquement les catastrophes ; au G2.3 (3m→MICRO_LIVE) on exige PSR ≥ 0.95 + DSR + Hansen SPA + audit halal.

---

## 2. Périmètre

**Inclus** :
- définition mathématique de chaque gate `G2.1`, `G2.2`, `G2.3`, `G3`
- batterie de tests statistiques (PSR, DSR, KS, Energy, Hansen SPA, etc.)
- seuils numériques par palier
- vetos durs
- format JSON normalisé du rapport de gate
- conditions d'**interruption immédiate** (hard veto en plein palier)

**Hors périmètre** :
- automatisation de la décision humaine (interdit)
- calcul des seuils dynamiques (cf. `13_...`)
- timing calendaire des phases (cf. `07_...`)
- topologie de stockage des artefacts de shadow (cf. `12_...`)

---

## 3. Invariants mathématiques (gate-specific)

| # | Invariant | Pourquoi |
|---|---|---|
| **GI-1** | **Le gate est humain.** Ce MD ne fournit jamais de "auto-promotion if X". | Sécurité du capital. |
| **GI-2** | **Échantillon réel uniquement.** Les critères de gate utilisent **les fills shadow réels**, pas le backtest historique (qui sert la calibration). | Évite le double-counting backtest/shadow. |
| **GI-3** | **Distribution-free quand possible.** Préférer KS, Energy distance, Mann-Whitney aux tests gaussiens. | Crypto = fat tails. |
| **GI-4** | **Severity scaling.** Le seuil de chaque test **augmente** entre G2.1 et G2.3. | Évite la promotion prématurée. |
| **GI-5** | **Hard vetos non-négociables.** Une seule violation d'un hard veto = **rejet du gate**, sans débat. | Filtre les catastrophes. |
| **GI-6** | **Multi-engine corrigé.** Si plusieurs engines (A/B/C/D) tournent en parallèle, les tests de Sharpe utilisent **Hansen SPA** pour filtrer la sélection. | Anti data-snooping multi-engine. |
| **GI-7** | **Halal indépendant.** Aucun gate ne peut être passé si **un seul ordre haram** a été émis pendant le palier. | Norme dure. |
| **GI-8** | **Live-vs-shadow drift check.** Si la distribution shadow diverge significativement de la distribution backtest qui a servi à la calibration, **veto**. | Détecte drift de modèle / régime. |
| **GI-9** | **Stationarity in-window.** Le palier doit lui-même être stationnaire (pas de tendance subreptice gain→perte sur les 30 derniers jours). | Détecte décrochage en fin de palier. |
| **GI-10** | **Sample minimum dur.** Aucun gate ne peut être validé si $n_{\text{trades}} < n_{\min}$ (par palier, voir § 5). | Évite décision sur bruit pur. |

---

## 4. Notation

- $r_t^{\text{live}}$ : return de la stratégie au pas $t$ pendant le shadow (réel, pas backtest)
- $r_t^{\text{bt}}$ : return correspondant en backtest "ground truth" calibré
- $n_{\text{trades}}$ : nombre de trades exécutés pendant le palier
- $n_{\text{days}}$ : nombre de jours de marché ouverts pendant le palier
- $\widehat{\text{SR}}_{\text{live}}$ : Sharpe annualisé estimé sur le shadow
- $\widehat{\text{DD}}_{\text{live}}$ : drawdown max observé en shadow
- $\hat\gamma_3, \hat\gamma_4$ : skewness, kurtosis empiriques du shadow
- $\Phi$ : CDF normale standard
- $\gamma_E \approx 0.5772$ : constante d'Euler-Mascheroni

---

## 5. Sample size requirements par palier

Sous H0 ($\text{SR} = 0$) vs H1 ($\text{SR} = \text{SR}^*$), la **taille minimale d'échantillon** pour détecter $\text{SR}^*$ avec significance $\alpha$ et power $1 - \beta$ est :

$$n_{\min} = \left(\frac{z_{1-\alpha/2} + z_{1-\beta}}{\text{SR}^*_{\text{daily}}}\right)^2 \cdot \left(1 + \frac{(\text{SR}^*_{\text{daily}})^2}{2}\right)$$

Avec $\text{SR}^*_{\text{annual}} = \text{SR}^*_{\text{daily}} \cdot \sqrt{252}$.

| Palier | $\text{SR}^*_{\text{annual}}$ visé | $\alpha$ | $1 - \beta$ | $n_{\min}$ daily | Échantillon réel attendu |
|---|---|---|---|---|---|
| **G2.1** (1m→2m) | 1.0 | 0.10 | 0.50 | ≈ 80 | $n_{\text{days}} \geq 20$ + $n_{\text{trades}} \geq 50$ |
| **G2.2** (2m→3m) | 1.0 | 0.05 | 0.70 | ≈ 200 | $n_{\text{days}} \geq 40$ + $n_{\text{trades}} \geq 150$ |
| **G2.3** (3m→MICRO) | 1.5 | 0.05 | 0.80 | ≈ 250 | $n_{\text{days}} \geq 60$ + $n_{\text{trades}} \geq 300$ |

> **Note pragmatique** : ces $n_{\min}$ sont **bas** intentionnellement. À 1 mois on n'a pas la puissance statistique d'un fonds. Le gate G2.1 sert à filtrer les catastrophes, pas à valider un edge. C'est cumulatif : pour passer G2.3, le système a au total ~3 mois de fills. La rigueur monte par couches.

**Hard veto §10 dur** : si $n_{\text{trades}} < n_{\min}$, **gate refusé d'office**, indépendamment des autres tests.

---

## 6. Tests statistiques requis

### 6.1 PSR — Probabilistic Sharpe Ratio (Bailey-López de Prado, 2012)

$$\text{PSR}(\text{SR}^*) = \Phi\left(\frac{(\widehat{\text{SR}}_{\text{live}} - \text{SR}^*) \sqrt{n - 1}}{\sqrt{1 - \hat\gamma_3 \widehat{\text{SR}}_{\text{live}} + \frac{\hat\gamma_4 - 1}{4}\widehat{\text{SR}}_{\text{live}}^2}}\right)$$

Interprétation : probabilité que le **vrai** SR soit $> \text{SR}^*$ étant donné l'observation.

**Seuils par palier** :

| Palier | Test | Seuil |
|---|---|---|
| G2.1 | $\text{PSR}(0)$ | $\geq 0.60$ |
| G2.2 | $\text{PSR}(0)$ | $\geq 0.85$ |
| G2.3 | $\text{PSR}(0)$ | $\geq 0.95$ |

### 6.2 DSR — Deflated Sharpe Ratio

Identique à `13_..., § 7`. Corrige pour le nombre $N$ de configs/engines testés en parallèle :

$$\text{SR}^*_{\text{adj}} = \sqrt{\widehat{\mathbb{V}}[\widehat{\text{SR}}]} \cdot \left((1 - \gamma_E)\Phi^{-1}\!\left(1 - \tfrac{1}{N}\right) + \gamma_E\Phi^{-1}\!\left(1 - \tfrac{1}{N \cdot e}\right)\right)$$

$$\text{DSR} = \Phi\left(\frac{(\widehat{\text{SR}} - \text{SR}^*_{\text{adj}}) \sqrt{n - 1}}{\sqrt{1 - \hat\gamma_3 \widehat{\text{SR}} + \frac{\hat\gamma_4 - 1}{4}\widehat{\text{SR}}^2}}\right)$$

**Seuils par palier** :

| Palier | Test | Seuil |
|---|---|---|
| G2.1 | DSR | non requis (échantillon trop petit) |
| G2.2 | DSR | $\geq 0.85$ |
| G2.3 | DSR | $\geq 0.95$ |

### 6.3 Distribution drift live-vs-backtest (KS + Energy distance)

Pour détecter qu'un drift distributionnel a eu lieu entre la calibration backtest et la réalité shadow :

#### 6.3.1 Kolmogorov-Smirnov à 2 échantillons

$$D_{n,m} = \sup_x \left| F_n^{\text{live}}(x) - F_m^{\text{bt}}(x) \right|$$

avec $n$ = taille shadow, $m$ = taille backtest correspondant.

p-value asymptotique (Smirnov) :
$$p \approx 2 \sum_{k=1}^{\infty} (-1)^{k-1} \exp\!\left(-2 k^2 \cdot D_{n,m}^2 \cdot \frac{nm}{n+m}\right)$$

**Seuils par palier** :
| Palier | Test | Seuil |
|---|---|---|
| G2.1 | KS p-value | $\geq 0.01$ (très tolérant) |
| G2.2 | KS p-value | $\geq 0.05$ |
| G2.3 | KS p-value | $\geq 0.10$ |

#### 6.3.2 Energy distance (Székely-Rizzo)

Plus puissant que KS pour les distributions multivariées :

$$\mathcal{E}(F_n, G_m) = 2 \mathbb{E}\|X - Y\| - \mathbb{E}\|X - X'\| - \mathbb{E}\|Y - Y'\|$$

estimé par U-statistique. Test par permutation (1000 réplicas).

**Seuils par palier** :
| Palier | Test | Seuil |
|---|---|---|
| G2.1 | Energy p-value | $\geq 0.01$ |
| G2.2 | Energy p-value | $\geq 0.05$ |
| G2.3 | Energy p-value | $\geq 0.10$ |

### 6.4 Maximum Drawdown test

#### 6.4.1 Distribution théorique (Magdon-Ismail-Atiya, 2004)

Pour un brownien drifté de Sharpe annuel $\mu/\sigma$ et durée $T$ :

$$\mathbb{E}[\text{DD}_{\max}] \approx \sigma\sqrt{T} \cdot Q\!\left(\frac{\mu}{\sigma}\sqrt{T}\right)$$

où $Q$ est une fonction explicite donnée dans le paper.

#### 6.4.2 Test

Le DD observé pendant le palier doit satisfaire :
$$\widehat{\text{DD}}_{\text{live}} \leq \mathbb{E}[\text{DD}_{\max}] + 2 \cdot \sqrt{\text{Var}[\text{DD}_{\max}]}$$

(borne supérieure à 95% sous l'hypothèse brownien drifté).

**Seuils additionnels en valeur absolue** :

| Palier | Hard cap DD relatif | Hard cap DD absolu |
|---|---|---|
| G2.1 | $\leq 1.5 \times \text{DD calib backtest}$ | $\leq -3\%$ equity |
| G2.2 | $\leq 1.3 \times \text{DD calib backtest}$ | $\leq -5\%$ equity |
| G2.3 | $\leq 1.2 \times \text{DD calib backtest}$ | $\leq -7\%$ equity |

> Les hard caps absolus dominent toujours. Si l'un est dépassé pendant le palier, le gate échoue **et** l'humain doit aussi décider si l'engine reste actif (cf. § 9 hard veto en plein palier).

### 6.5 Calmar ratio floor

$$\text{Calmar} = \frac{\text{return\_annualized}}{\widehat{\text{DD}}_{\text{max,live}}}$$

| Palier | Calmar floor |
|---|---|
| G2.1 | $\geq 0.5$ |
| G2.2 | $\geq 1.0$ |
| G2.3 | $\geq 2.0$ |

### 6.6 Sortino ratio floor

$$\text{Sortino} = \frac{\bar r - r_f}{\sigma_{\text{down}}}, \qquad \sigma_{\text{down}}^2 = \frac{1}{n_-}\sum_{r_t < 0} r_t^2$$

| Palier | Sortino floor (annualisé) |
|---|---|
| G2.1 | $\geq 0.5$ |
| G2.2 | $\geq 1.0$ |
| G2.3 | $\geq 1.5$ |

### 6.7 Profit factor

$$\text{PF} = \frac{\sum_{r_t > 0} r_t}{|\sum_{r_t < 0} r_t|}$$

| Palier | PF floor |
|---|---|
| G2.1 | $\geq 1.05$ |
| G2.2 | $\geq 1.15$ |
| G2.3 | $\geq 1.30$ |

### 6.8 Stationarity in-window (GI-9)

Pour détecter un décrochage en fin de palier (gain au début, perte à la fin), test de **Chow** ou **Mann-Kendall** sur la série cumulée des returns.

**Seuils par palier** :
| Palier | Mann-Kendall p-value sur tendance des returns | Seuil |
|---|---|---|
| G2.1 | tendance descendante détectée | rejet si $p < 0.05$ |
| G2.2 | tendance descendante détectée | rejet si $p < 0.10$ |
| G2.3 | tendance descendante détectée | rejet si $p < 0.20$ |

### 6.9 Hansen SPA test (Superior Predictive Ability)

Quand plusieurs engines (A/B/C/D) tournent en parallèle, on doit éviter de promouvoir l'engine qui "a eu de la chance" parmi N. Hansen SPA test : H0 = "le meilleur engine n'est pas significativement meilleur qu'une stratégie de référence".

**Stat de test** :
$$T_n^{\text{SPA}} = \max_{k \in \{1, \ldots, N\}} \frac{\sqrt{n}\bar d_k}{\hat\omega_k}$$

avec $d_k$ = différence de loss entre l'engine $k$ et le benchmark, et $\hat\omega_k$ estimé via stationary bootstrap.

p-value par bootstrap sous H0.

**Application aux gates** :
| Palier | Hansen SPA |
|---|---|
| G2.1 | non requis |
| G2.2 | p-value $\leq 0.10$ pour l'engine sélectionné |
| G2.3 | p-value $\leq 0.05$ pour l'engine sélectionné |

### 6.10 Rolling window stability

Découper le palier en **fenêtres tierces** (3 fenêtres égales). Le Sharpe doit être positif dans chacune (ou au moins dans 2 sur 3 selon le palier).

| Palier | Critère |
|---|---|
| G2.1 | au moins 2 fenêtres / 3 avec Sharpe > 0 |
| G2.2 | les 3 fenêtres avec Sharpe > 0 |
| G2.3 | les 3 fenêtres avec Sharpe > 0.5 (annualisé) |

---

## 7. Critères de promotion par palier

### 7.1 Gate `G2.1` — Shadow 1 mois → 2 mois

**Tests requis (tous OK)** :
- $n_{\text{days}} \geq 20$, $n_{\text{trades}} \geq 50$
- $\text{PSR}(0) \geq 0.60$
- KS p-value (live vs backtest) $\geq 0.01$
- Energy p-value $\geq 0.01$
- $\widehat{\text{DD}}_{\text{live}} \leq 1.5 \times \text{DD calib}$ et $\geq -3\%$ equity
- Calmar $\geq 0.5$, Sortino $\geq 0.5$, PF $\geq 1.05$
- Mann-Kendall : pas de tendance descendante significative ($p \geq 0.05$)
- Rolling : 2 fenêtres / 3 avec Sharpe > 0
- **Aucun hard veto §10 déclenché**

### 7.2 Gate `G2.2` — Shadow 2 mois → 3 mois

**Tests requis (tous OK)** :
- $n_{\text{days}} \geq 40$, $n_{\text{trades}} \geq 150$
- $\text{PSR}(0) \geq 0.85$
- $\text{DSR} \geq 0.85$
- KS p-value $\geq 0.05$, Energy p-value $\geq 0.05$
- $\widehat{\text{DD}}_{\text{live}} \leq 1.3 \times \text{DD calib}$ et $\geq -5\%$
- Calmar $\geq 1.0$, Sortino $\geq 1.0$, PF $\geq 1.15$
- Mann-Kendall : pas de tendance descendante significative ($p \geq 0.10$)
- Rolling : 3 fenêtres / 3 avec Sharpe > 0
- Hansen SPA p-value $\leq 0.10$ (si multi-engine)
- **Aucun hard veto §10 déclenché**

### 7.3 Gate `G2.3` — Shadow 3 mois → MICRO_LIVE

**Tests requis (tous OK)** :
- $n_{\text{days}} \geq 60$, $n_{\text{trades}} \geq 300$
- $\text{PSR}(0) \geq 0.95$
- $\text{DSR} \geq 0.95$
- KS p-value $\geq 0.10$, Energy p-value $\geq 0.10$
- $\widehat{\text{DD}}_{\text{live}} \leq 1.2 \times \text{DD calib}$ et $\geq -7\%$
- Calmar $\geq 2.0$, Sortino $\geq 1.5$, PF $\geq 1.30$
- Mann-Kendall : pas de tendance descendante significative ($p \geq 0.20$)
- Rolling : 3 fenêtres / 3 avec Sharpe $\geq 0.5$ (annualisé)
- Hansen SPA p-value $\leq 0.05$ (si multi-engine)
- **OOS reservation utilisé** : le 15% test reservé de la calibration peut maintenant être consulté en lecture seule pour une dernière validation
- **Audit halal complet** : 0 ordre haram, purification rate sous cap, 0 feature compte interdite
- **Aucun hard veto §10 déclenché**

### 7.4 Gate `G3` — MICRO_LIVE → LIVE complet (capital cible)

**Tests requis (tous OK)** :
- $n_{\text{days,micro}} \geq 30$, $n_{\text{trades,micro}} \geq 100$ (en réel, capital MICRO_LIVE)
- $\text{PSR}(0) \geq 0.90$ sur le micro live
- Reconciliation balances/positions OK 100% sans incident
- 0 ordre haram, 0 violation breaker, 0 reset secret
- $\widehat{\text{DD}}_{\text{live,micro}} \leq -3\%$ equity micro
- Live-vs-shadow distribution drift : KS p-value $\geq 0.05$
- Pre-engagement humain anti-panique signé (cf. `10_..., D-13`)

> Le passage `G3` est **différent** des `G2.x` parce qu'il implique le **passage du shadow au capital réel**. La rigueur n'est pas plus haute mathématiquement qu'au G2.3 — elle est plus haute **opérationnellement** (reconciliation, secrets, halal en conditions live).

---

## 8. Hard vetos non-négociables

Une **seule** violation d'un veto = **gate refusé**, peu importe les autres scores.

| # | Veto | Détection |
|---|---|---|
| **HV-1** | Un seul ordre **haram** émis pendant le palier | sharia layer log |
| **HV-2** | Un seul appel à une feature compte interdite (`/sapi/v1/margin/*`, `/sapi/v1/futures/*`, etc.) | account_features_audit log |
| **HV-3** | Hard cap humain `THR-R*` (daily / weekly / monthly breaker) **dépassé** dans la fenêtre du palier | risk_backbone log |
| **HV-4** | Reconciliation balances/positions divergente non résolue dans 60 s | reconciliation_layer log |
| **HV-5** | Une calibration utilisée par le runtime pendant le palier n'a **pas** été signée humainement | calibration_loader log |
| **HV-6** | Le système a tenté de re-calibrer **automatiquement** un seuil pendant le palier | runtime guard violation |
| **HV-7** | Un secret API a été manipulé / re-rotaté en plein palier sans incident déclaré | secret_loader log |
| **HV-8** | Un ordre **orphelin** (envoyé sans confirmation reçue puis status inconnu > 5 min) | order_state_machine log |
| **HV-9** | $n_{\text{trades}} < n_{\min}$ (cf. § 5) | reporting layer |
| **HV-10** | Disque ≥ 90% capacity sur le VPS pendant le palier | monitoring |

---

## 9. Hard vetos en plein palier (interruption immédiate)

Certains des vetos ci-dessus déclenchent **interruption immédiate** du shadow (sans attendre la fin du palier) et reset du compteur :

| Veto | Action immédiate |
|---|---|
| HV-1 (haram) | **arrêt complet** du runtime, alerte humaine, reset palier |
| HV-2 (feature interdite) | **arrêt complet** du runtime, alerte humaine, reset palier |
| HV-3 (breaker dépassé) | **arrêt** du runtime jusqu'à reset humain, palier non comptabilisé |
| HV-7 (secret manipulé sans incident) | **arrêt complet**, audit forensique, reset palier |
| HV-8 (ordre orphelin) | **pause** runtime, reconciliation forcée, palier comptabilisé en mode dégradé |

Les autres vetos (`HV-4 / 5 / 6 / 9 / 10`) ne déclenchent pas d'arrêt immédiat mais font **échouer le gate** au moment du calcul.

---

## 10. Multi-engine adjustment

### 10.1 Quand l'appliquer

Si plusieurs engines (A/B/C/D) sont actifs en parallèle pendant le shadow et qu'**un seul** est candidat à la promotion, il faut corriger le risque de "best-of-N" :

- **Romano-Wolf step-down** sur les p-values des tests (PSR, DSR) à travers les N engines
- **Hansen SPA** pour valider que le meilleur n'est pas dû au hasard parmi N

### 10.2 Quand ne pas l'appliquer

- Si **un seul** engine est actif → pas de correction nécessaire
- Si les engines tradent sur des **univers disjoints** sans overlap de paires → pas de correction (chaque engine a son propre test)
- Si le candidat à la promotion est **prédésigné** avant le début du palier (par doctrine, pas par data) → pas de correction

### 10.3 Trade-off

Romano-Wolf est conservateur. Pour 4 engines testés, les seuils de § 6 et § 7 doivent être interprétés comme **post-correction**, c'est-à-dire que les p-values utilisées sont déjà ajustées.

---

## 11. Halal-specific gate checks

Indépendant des tests statistiques. **Tout gate échoue** si **un seul** des items suivants n'est pas satisfait :

| # | Check halal | Condition |
|---|---|---|
| HC-1 | 0 ordre haram émis pendant le palier | log sharia layer == empty |
| HC-2 | 0 feature compte interdite utilisée | account_features_audit == empty |
| HC-3 | Purification rate par token tradé $\leq$ cap (`THR-H01`) | screening recalculé en fin de palier |
| HC-4 | Toutes les paires tradées passent le screening AAOIFI | screening recalculé en fin de palier |
| HC-5 | Aucun stablecoin non-validé par fatwa interne utilisé | matching contre la liste D-05 |
| HC-6 | Aucun "Earn", "Savings", "Staking" passif activé pendant le palier | API surface scan |

> Ces checks sont **déterministes**, pas statistiques. Pas de p-value, pas d'IC. Tout violation = veto dur.

---

## 12. Format normalisé du rapport de gate

```jsonc
{
  "gate_id": "G2.2",
  "palier": "shadow_2_to_3_months",
  "engine": "A",
  "evaluated_at": "2026-07-15T16:00:00Z",
  "data_window": {"start": "2026-05-15T00:00:00Z", "end": "2026-07-15T00:00:00Z"},
  "sample": {
    "n_days": 41,
    "n_trades": 187,
    "n_min_required": 150,
    "n_trades_satisfied": true
  },
  "stat_tests": {
    "PSR": {"value": 0.913, "threshold": 0.85, "pass": true},
    "DSR": {"value": 0.892, "threshold": 0.85, "pass": true, "N_trials": 4},
    "KS_pvalue_vs_backtest": {"value": 0.18, "threshold": 0.05, "pass": true},
    "Energy_pvalue_vs_backtest": {"value": 0.11, "threshold": 0.05, "pass": true},
    "drawdown_max_live": {"value": -0.038, "threshold_relative": "<= 1.3 * DD_calib", "threshold_absolute": -0.05, "pass": true},
    "calmar": {"value": 1.42, "threshold": 1.0, "pass": true},
    "sortino": {"value": 1.18, "threshold": 1.0, "pass": true},
    "profit_factor": {"value": 1.27, "threshold": 1.15, "pass": true},
    "mann_kendall_pvalue": {"value": 0.31, "threshold": 0.10, "pass": true},
    "rolling_3_windows_sharpe_positive": {"value": [0.4, 0.7, 0.5], "threshold": "all > 0", "pass": true},
    "hansen_spa_pvalue": {"value": 0.07, "threshold": 0.10, "pass": true}
  },
  "hard_vetos": {
    "HV-1_haram": {"violations": 0, "pass": true},
    "HV-2_forbidden_features": {"violations": 0, "pass": true},
    "HV-3_breaker_breached": {"violations": 0, "pass": true},
    "HV-4_reconciliation_unresolved": {"violations": 0, "pass": true},
    "HV-5_unsigned_calibration": {"violations": 0, "pass": true},
    "HV-6_auto_recalibration": {"violations": 0, "pass": true},
    "HV-7_secret_manipulation": {"violations": 0, "pass": true},
    "HV-8_orphan_orders": {"violations": 0, "pass": true},
    "HV-9_sample_too_small": {"pass": true},
    "HV-10_disk_full": {"pass": true}
  },
  "halal_checks": {
    "HC-1": "pass",
    "HC-2": "pass",
    "HC-3": "pass",
    "HC-4": "pass",
    "HC-5": "pass",
    "HC-6": "pass"
  },
  "overall_machine_recommendation": "PASS_RECOMMENDED",
  "human_decision_required": true,
  "human_signature": null,
  "calibration_in_use": "calibration_v3",
  "reproducibility": {
    "computed_with_method_version": "shadow_gate_math_v1",
    "code_commit": "v53@a1b2c3d",
    "data_hash_sha256": "..."
  }
}
```

> **Important** : `overall_machine_recommendation` n'est qu'une recommandation. La décision finale est humaine, signée explicitement (`human_signature`). Une recommandation `PASS_RECOMMENDED` ne donne **pas** de droit automatique au passage du gate. Une recommandation `FAIL` donne en revanche un **droit de veto opposable** : l'humain ne peut pas passer outre sans documenter explicitement pourquoi (et la trace est conservée pour audit).

---

## 13. Ce qu'il ne faut **pas** faire

| # | Interdiction | Pourquoi |
|---|---|---|
| NO-1 | Ne pas auto-promouvoir un palier sur la base des tests verts. | Viole GI-1. |
| NO-2 | Ne pas calculer les tests sur des données mélangeant shadow et backtest. | Viole GI-2. |
| NO-3 | Ne pas utiliser de test gaussien (t-test, z-test naïfs) pour le DD ou les queues. | Viole GI-3. |
| NO-4 | Ne pas baisser les seuils d'un palier "parce que l'échantillon est petit". L'échantillon trop petit déclenche HV-9, pas un assouplissement. | Viole GI-10. |
| NO-5 | Ne pas appliquer un seul des hard vetos `HV-*` "souplement". Les vetos sont absolus. | Viole GI-5. |
| NO-6 | Ne pas masquer les violations halal "parce que c'était un test". Test vs prod est sans importance pour la doctrine. | Viole GI-7. |
| NO-7 | Ne pas reporter un gate pour "améliorer le sample" en re-courant le même palier sans réinitialiser. Re-shadow = nouveau palier from scratch. | Évite p-hacking temporel. |
| NO-8 | Ne pas comparer le shadow à un benchmark choisi a posteriori (BTC HODL, ETH HODL, S&P, etc.). Le benchmark est défini **avant** le palier. | Anti data-snooping comparatif. |
| NO-9 | Ne pas relâcher le test OOS reservé en `G2.3` (15% data réservée). Une seule consultation, pas de retours. | Viole `13_...` § 6.4. |
| NO-10 | Ne pas considérer un veto humain "documenté" comme équivalent à un PASS machine. Le veto humain est une override, pas une mise au standard. | Audit-ready. |

---

## 14. Critères d'acceptation

- [ ] AC-1 : chaque gate `G2.1`, `G2.2`, `G2.3`, `G3` a une liste explicite et exhaustive de tests (§ 7)
- [ ] AC-2 : les seuils de chaque test augmentent monotonement entre G2.1 et G2.3
- [ ] AC-3 : tous les hard vetos `HV-*` sont reliés à un détecteur runtime existant ou planifié (T1-T13)
- [ ] AC-4 : le rapport JSON normalisé § 12 est produit automatiquement à la fin de chaque palier
- [ ] AC-5 : le calcul du rapport est **reproductible** (seed, version, hash)
- [ ] AC-6 : l'humain ne peut **techniquement** pas passer un gate sans signer (signature stockée dans l'artefact gate)
- [ ] AC-7 : les checks halal HC-1 → HC-6 sont déterministes et ne dépendent d'aucune p-value
- [ ] AC-8 : un veto en plein palier (§ 9) déclenche bien l'action immédiate associée
- [ ] AC-9 : Hansen SPA et Romano-Wolf appliqués automatiquement quand $N_{\text{engines}} > 1$
- [ ] AC-10 : les seuils numériques de § 6 et § 7 sont eux-mêmes versionnés (modifiables uniquement via décision humaine + signature)

---

## 15. Ordre de réalisation

1. **Préalable** : `13_CALIBRATION_METHODS.md` publié et tranches 13-A → 13-G en cours côté Local IA Lab.
2. **Étape 14-A** — implémenter les détecteurs runtime des `HV-1` à `HV-10` (la plupart sont déjà dans le scope T1-T13, ce MD ne fait que rendre leur log auditables).
3. **Étape 14-B** — implémenter le **calculateur de rapport de gate** (script `scripts/shadow_gate_check.py` ou équivalent), côté Local IA Lab. Le script lit les fills shadow exportés depuis le VPS et produit le JSON § 12.
4. **Étape 14-C** — implémenter les **tests stat de base** : PSR, DSR, KS, Energy, Calmar, Sortino, PF, Mann-Kendall.
5. **Étape 14-D** — implémenter Hansen SPA et Romano-Wolf (dépend d'un bootstrap stationnaire déjà codé en 13-A).
6. **Étape 14-E** — implémenter la **boucle de signature humaine** du rapport de gate (artefact `gate_G2.x.json` signé).
7. **Étape 14-F** — implémenter les **hard vetos en plein palier** (§ 9) côté runtime VPS : circuit breaker qui peut interrompre immédiatement.
8. **Étape 14-G** — tests bout-en-bout : faire passer un faux palier (shadow synthétique) à travers tout le pipeline jusqu'à signature.

**Aucune étape n'autorise un humain à shorter le pipeline.** Le rapport de gate est un préalable dur à toute promotion de palier.

---

## 16. Preuves / tests attendus

| Preuve | Localisation suggérée | Tranche |
|---|---|---|
| PSR retrouve la valeur du paper Bailey-López de Prado sur exemple connu | `tests/test_shadow_gate/test_psr.py` | 14-C |
| DSR cohérent avec implémentations de référence | `tests/test_shadow_gate/test_dsr.py` | 14-C |
| KS détecte un drift injecté sur une série synthétique | `tests/test_shadow_gate/test_ks.py` | 14-C |
| Energy distance cohérent avec scipy.stats sur exemple connu | `tests/test_shadow_gate/test_energy.py` | 14-C |
| Hansen SPA refuse le best-of-100 stratégies aléatoires | `tests/test_shadow_gate/test_hansen_spa.py` | 14-D |
| Hard veto HV-1 (haram) déclenche arrêt runtime | `tests/test_shadow_gate/test_hv_haram.py` | 14-F |
| Rapport JSON validé par schéma JSON | `tests/test_shadow_gate/test_report_schema.py` | 14-B |
| Rejet d'une promotion sans signature humaine | `tests/test_shadow_gate/test_signature_required.py` | 14-E |

---

## 17. Références bibliographiques

| Méthode | Référence |
|---|---|
| Probabilistic Sharpe Ratio | Bailey & López de Prado (2012), *J. of Risk* |
| Deflated Sharpe Ratio | Bailey & López de Prado (2014), *J. of Portfolio Management* |
| Maximum Drawdown distribution | Magdon-Ismail & Atiya (2004), *Risk Magazine* |
| Hansen SPA test | Hansen (2005), *J. of Business & Economic Statistics* |
| Romano-Wolf step-down | Romano & Wolf (2005), *Econometrica* |
| Energy distance | Székely & Rizzo (2013), *J. Stat. Plan. Inference* |
| Kolmogorov-Smirnov 2-sample | Smirnov (1948), *Annals of Mathematical Statistics* |
| Mann-Kendall trend test | Mann (1945) ; Kendall (1975) |
| Stationary block bootstrap | Politis & Romano (1994), *JASA* |
| Walk-forward analysis | López de Prado (2018), *Advances in Financial Machine Learning* |
| Sample size for SR detection | Lo (2002), *Financial Analysts Journal* |
| Halal screening reference | AAOIFI Sharia Standard 21 |

---

## 18. Suite logique

- **Fin du dossier `production_deployment_plan/`** : ce fichier `14_...` ferme la série. Le dossier compte désormais `00 → 14` + `11A` = **16 fichiers**.
- **Côté code** : tranches 14-A → 14-G, exécutées par l'agent codeur après que `13_...` ait débloqué les méthodes de calibration. Les deux MDs `13` et `14` sont **interdépendants** : la calibration produit des seuils qui définissent ce que le gate vérifie ; le gate consomme les fills shadow réels et compare au backtest qui a servi à calibrer.
- **Côté humain** : ce MD redéfinit la responsabilité du gate en termes mathématiques précis, mais la signature humaine reste **l'unique mécanisme de promotion**. Aucune recommandation machine ne peut s'y substituer.
