# Cartographie Groupe A — `calibration_methods/` + `calibration_loader/`

**Date** : 2026-04-19  
**Auteur** : Opus (lecture ligne par ligne exhaustive)  
**Racine** : `src/calibration_methods/` (15 fichiers) + `src/calibration_loader/` (3 fichiers)  
**Total LOC analysées** : 3 048 L

---

## Package `calibration_methods/`

---

### Fichier : `__init__.py` (167L)

**Rôle** : Point d'entrée public du package — ré-exporte la totalité des symboles publics des 14 modules internes. Aucune logique propre.

**Re-exports publics** :
`EnergyDistanceError/Result/compute_energy_distance_test`, `KolmogorovSmirnovError/Result/compute_ks_2sample`, `MannKendallError/Result/compute_mann_kendall_test`, `ProbabilisticSharpeRatioError/Result/compute_probabilistic_sharpe_ratio`, `DeflatedSharpeRatioError/Result/compute_deflated_sharpe_ratio`, `StationaryBootstrapConfig/Error/Interval/infer_stationary_block_length/stationary_bootstrap_confidence_interval`, `ExecutionCalibrationError/ExecutionSlippageModelEstimate/ExecutionThresholdEstimate/HampelFilterResult/apply_hampel_filter/calibrate_*`, `HumanHardCapPolicyError/Result/apply_human_maximum_cap/apply_human_minimum_floor`, `HansenSpaError/Result/compute_hansen_spa_test`, `HolmBonferroniAdjustedHypothesis/Result/MultipleTestingError/apply_holm_bonferroni`, `CURRENT_REPO_PAIR_UNIVERSE_COUNT/V53_CANONICAL_SHADOW_PAIR_FLOOR/HarveyLiuZhu*/MultipleTestingGuardError/compose_hlz_test_count/compute_harvey_liu_zhu_deflated_sharpe`, `PotGpdConfig/Error/Result/fit_pot_gpd_tail_risk`, `AugmentedDickeyFullerResult/DualStationarityResult/KpssLevelStationarityResult/StationarityTestError/compute_adf_level_stationarity/compute_kpss_level_stationarity/evaluate_dual_stationarity`, `PurgedWalkForwardConfig/Error/Fold/Plan/build_purged_walk_forward_plan`

**Logging** : Aucun  
**Dépendances internes** : tous les modules du package  
**État** : COMPLETE  
**Anomalies** : Aucune

---

### Fichier : `bootstrap.py` (213L)

**Rôle** : Implémente le bootstrap stationnaire par blocs (Politis & Romano 1994) — inférence de la longueur de bloc par autocorrélation tronquée, tirage d'indices, calcul d'intervalle de confiance pour un estimateur arbitraire.

**Inputs** :
- `infer_stationary_block_length(values: Iterable[float], *, max_block_length: int | None) -> int`
- `stationary_bootstrap_confidence_interval(values: Iterable[float], *, estimator: Callable[[tuple[float,...]], float], config: StationaryBootstrapConfig | None) -> StationaryBootstrapInterval`

**Outputs** :
- `int` (longueur de bloc)
- `StationaryBootstrapInterval` (pydantic frozen, champs: `sample_count`, `bootstrap_samples`, `expected_block_length`, `confidence_level`, `point_estimate`, `ci_lower`, `ci_upper`, `rng_seed`)

**Equations mathématiques** :
```
# Longueur de bloc par autocorrélation intégrée
upper_bound = max(2, min(n//3, sqrt(n)+1))
rho(lag) = sum((x_i - mu)(x_{i-lag} - mu), i=lag..n) / ((n-lag) * sigma^2)
L = round(1 + sum(lag * rho(lag) for lag if rho(lag) > 0))

# Probabilité de restart stationnaire
p_restart = 1 / expected_block_length

# IC empirique
alpha = (1 - confidence_level) / 2
ci_lower = quantile(bootstrap_estimates, alpha)
ci_upper = quantile(bootstrap_estimates, 1 - alpha)
```

**Logging** : Aucun  
**Dépendances internes** : Aucune (stdlib + pydantic uniquement)  
**État** : COMPLETE  
**Anomalies** :
- `rng_seed: int = 53` — valeur hardcodée dans `StationaryBootstrapConfig` (acceptable comme default mais non configurable via seam externe)

---

### Fichier : `dsr.py` (136L)

**Rôle** : Calcule le Deflated Sharpe Ratio (Bailey & López de Prado 2012) corrigé pour la non-normalité et la sélection multiple (benchmark SR via loi de valeur extrême de Gumbel).

**Inputs** :
- `compute_deflated_sharpe_ratio(returns: Iterable[float], *, trial_count: int, acceptance_floor: float = 0.95) -> DeflatedSharpeRatioResult`

**Outputs** :
- `DeflatedSharpeRatioResult` (champs: `observation_count`, `trial_count`, `acceptance_floor`, `mean_return`, `sample_std`, `sharpe_ratio`, `skewness`, `kurtosis`, `sharpe_variance`, `benchmark_sharpe`, `dsr`, `passes_floor`)

**Equations mathématiques** :
```
SR_hat = mean(r) / std_sample(r)
gamma_3 = population skewness (3rd standardized moment)
gamma_4 = population kurtosis (4th standardized moment)

# Variance de SR sous non-normalité
denominator_term = 1 - gamma_3 * SR_hat + ((gamma_4 - 1) / 4) * SR_hat^2
sharpe_variance = denominator_term / (n - 1)

# Benchmark SR (loi de Gumbel des maxima)
gamma_e = 0.5772156649015329  # constante d'Euler-Mascheroni
sqrt_v = sqrt(sharpe_variance)
q1 = Phi^{-1}(1 - 1/T)
q2 = Phi^{-1}(1 - 1/(T*e))
SR_benchmark = sqrt_v * ((1 - gamma_e) * q1 + gamma_e * q2)

# DSR
z = (SR_hat - SR_benchmark) * sqrt(n-1) / sqrt(denominator_term)
DSR = Phi(z)
passes_floor = DSR >= acceptance_floor
```

**Logging** : Aucun  
**Dépendances internes** : Aucune (stdlib uniquement)  
**État** : COMPLETE  
**Anomalies** :
- `gamma_e = 0.5772156649015329` — constante mathématique inline (non anomalie, correct)
- `acceptance_floor = 0.95` — default hardcodé, mais c'est un paramètre d'entrée modifiable ; pas de seam manquant

---

### Fichier : `energy_distance.py` (180L)

**Rôle** : Test de distance d'énergie (Székely & Rizzo 2004) pour détecter une divergence distributionnelle entre séries shadow et backtest — plus puissant que KS pour les queues et distributions multimodales.

**Inputs** :
- `compute_energy_distance_test(shadow_returns: Iterable[float], backtest_returns: Iterable[float], *, acceptance_floor: float = 0.05, n_permutations: int = 1000, random_seed: int | None = 42) -> EnergyDistanceResult`

**Outputs** :
- `EnergyDistanceResult` (champs: `n_shadow`, `n_backtest`, `energy_statistic`, `p_value`, `n_permutations`, `passes_floor`, `acceptance_floor`)

**Equations mathématiques** :
```
# Statistique d'énergie U-statistic (1D)
E_hat(F,G) = 2*E|X-Y| - E|X-X'| - E|Y-Y'|
           = (2/(n*m)) * sum_ij |x_i - y_j|
             - (1/n^2) * sum_ij |x_i - x_j|
             - (1/m^2) * sum_ij |y_i - y_j|

T(x,y) = (n*m)/(n+m) * max(E_hat, 0)

# p-value par permutation
p = (#{T_perm >= T_obs} + 1) / (n_permutations + 1)  # correction de continuité
passes_floor = p >= acceptance_floor
```

**Logging** : Aucun  
**Dépendances internes** : Aucune  
**État** : COMPLETE  
**Anomalies** :
- `random_seed: int | None = 42` — graine hardcodée par défaut (acceptable comme valeur reproductible, mais non configurable via seam externe)
- Complexité O(n*m) pour la statistique : acceptable pour shadow (n,m < 1000), pas pour backtests longs

---

### Fichier : `execution.py` (511L)

**Rôle** : Calibration des 5 seuils d'exécution THR-X01 à THR-X05 : synchronisation horloge (ms), gap websocket (s), quota rate limit (ratio), spread guard (bps), modèle de slippage sqrt(size) via régression Huber. Inclut le filtre Hampel pour le nettoyage des outliers.

**Inputs** :
- `apply_hampel_filter(values: tuple[float,...], *, window_size: int = 60, k: float = 3.0) -> HampelFilterResult`
- `calibrate_time_sync_threshold_ms(offsets_ms: tuple[float,...], *, quantile: float = 0.999, additive_margin_ms: float = 200.0, hard_cap_ms: float = 1000.0, ...) -> ExecutionThresholdEstimate`
- `calibrate_websocket_gap_threshold_s(interarrival_s: tuple[float,...], *, quantile: float = 0.9999, hard_cap_s: float = 5.0) -> ExecutionThresholdEstimate`
- `calibrate_spread_guard_threshold_bps(spread_bps: tuple[float,...], *, hard_cap_bps: float = 50.0) -> ExecutionThresholdEstimate`
- `calibrate_rate_limit_throttle_ratio(*, quota_call_counts, quota_probe_durations_s, quota_limit_calls_per_minute_values, ...) -> ExecutionThresholdEstimate`
- `calibrate_slippage_model_bps(slippage_bps, *, candidate_sizes, final_sizes, min_r_squared: float = 0.30, ...) -> ExecutionSlippageModelEstimate`
- `empirical_quantile(values: tuple[float,...], *, quantile: float) -> float`

**Outputs** : `ExecutionThresholdEstimate` (threshold unique) ou `ExecutionSlippageModelEstimate` (modèle linéaire)

**Equations mathématiques** :
```
# THR-X01 (horloge)
point_estimate = quantile(|offsets_ms|, 0.999) + additive_margin_ms
published = min(point_estimate, hard_cap_ms=1000.0)

# THR-X02 (websocket)
published = min(quantile(interarrival_s, 0.9999), hard_cap_s=5.0)

# THR-X04 (spread guard, lognormal mu+2sigma)
mu_log = mean(log(spread_bps[spread_bps > 0]))
sigma_log = pstdev(log(spread_bps[spread_bps > 0]))
point_estimate = exp(mu_log + 2*sigma_log)    # ~ percentile 97.7%
published = min(point_estimate, hard_cap_bps=50.0)

# THR-X03 (rate limit, Little's law + burst margin)
lambda_q = quantile(calls_per_minute, 0.95)
point_estimate = (lambda_q * burst_horizon_min * burst_margin_mult) / quota_cap
published = min(point_estimate, hard_cap=0.80)

# THR-X05 (slippage, Huber IRLS sqrt-size)
# Iteration Huber IRLS (max_iter=25, tol=1e-8)
# threshold = k * 1.4826 * MAD(residuals)
# w_i = 1 if |r_i| <= threshold else threshold / |r_i|
slippage_bps ~ intercept + slope * sqrt(size)  # WLS Huber
R^2 >= min_r_squared (= 0.30 par defaut)

# Filtre Hampel
scaled_MAD = 1.4826 * median(|x_i - median(window)|)
outlier si |x_i - median(window)| > k * scaled_MAD  (k=3.0 par defaut)
```

**Logging** : Aucun  
**Dépendances internes** : `calibration_methods.hard_cap_floor` (apply_human_maximum_cap)  
**État** : COMPLETE  
**Anomalies** :
- `hard_cap_ms: float = 1000.0` — hardcodé dans signature (non configurable depuis seam externe ; acceptable comme default mais idéalement calibration seam)
- `hard_cap_s: float = 5.0` — idem
- `hard_cap_bps: float = 50.0` — idem
- `hard_cap_quota_ratio: float = 0.80` — idem
- `additive_margin_ms: float = 200.0` — idem
- `quantile: float = 0.9999` — idem
- `min_r_squared: float = 0.30` — idem. Tous ces defaults sont des paramètres de la fonction (modifiables à l'appel) mais ne passent pas par un fichier d'artefact de calibration. Risque : cohérence entre déploiements.
- `quantile=0.97725` hardcodé dans `calibrate_spread_guard_threshold_bps` (valeur dérivée de mu+2sigma, commentaire implicite)

---

### Fichier : `hansen_spa.py` (288L)

**Rôle** : Test SPA de Hansen (2005) pour la sélection multi-engine shadow — corrige le biais de sélection du meilleur candidat via bootstrap stationnaire conjoint avec recentrage positif de la loi nulle.

**Inputs** :
- `compute_hansen_spa_test(loss_differentials_by_candidate: Mapping[str, Iterable[float]], *, acceptance_ceiling: float = 0.10, bootstrap_samples: int = 1000, expected_block_length: int | None = None, rng_seed: int = 53) -> HansenSpaResult`

**Outputs** :
- `HansenSpaResult` (champs: `candidate_count`, `observation_count`, `selected_candidate_id`, `selected_candidate_mean_differential`, `selected_candidate_omega_hat`, `test_statistic`, `p_value`, `passes_floor`, `acceptance_ceiling`, `bootstrap_samples`, `expected_block_length`, `rng_seed`)

**Equations mathématiques** :
```
# Omega_hat (variance bootstrap de sqrt(n)*mean)
d_centered_i = d_i - mean(d_i)
replicate_b = sqrt(n) * mean(d_centered[bootstrap_indices_b])
omega_hat_k = max(std(replicates_k), 1e-12)

# Statistique studentisée (positive-part)
t_k = max(0, sqrt(n) * mean(d_k) / omega_hat_k)
T_obs = max(t_k over k)

# Loi nulle (recentrage positif Hansen)
d_null_k = d_k - max(mean(d_k), 0)
T_boot_b = max_k( sqrt(n) * mean(d_null_k[indices_b]) / omega_hat_k )

# p-value
p = #{T_boot >= T_obs - 1e-12} / bootstrap_samples
passes_floor = p <= acceptance_ceiling
```

**Logging** : Aucun  
**Dépendances internes** : `calibration_methods.bootstrap.infer_stationary_block_length`  
**État** : COMPLETE  
**Anomalies** :
- `1e-12` hardcodé (floor omega_hat et tolérance comparaison) — valeur technique standard, pas d'anomalie fonctionnelle
- `rng_seed: int = 53` — default hardcodé (modifiable à l'appel)

---

### Fichier : `hard_cap_floor.py` (68L)

**Rôle** : Applique une politique humaine de plancher minimum ou plafond maximum sur une valeur candidate de calibration — produit un résultat audit-ready avec `hard_cap_binding` indiquant si la borne a été contraignante.

**Inputs** :
- `apply_human_minimum_floor(candidate_value: float, human_floor: float) -> HumanHardCapPolicyResult`
- `apply_human_maximum_cap(candidate_value: float, human_cap: float) -> HumanHardCapPolicyResult`

**Outputs** :
- `HumanHardCapPolicyResult` (champs: `candidate_value`, `published_value`, `hard_cap_human`, `bound_kind`, `hard_cap_satisfied`, `hard_cap_binding`)

**Equations mathématiques** :
```
published_value = max(candidate_value, human_floor)  # floor
published_value = min(candidate_value, human_cap)    # cap
hard_cap_binding = (candidate_value < human_floor)   # floor
hard_cap_binding = (candidate_value > human_cap)     # cap
```

**Logging** : Aucun  
**Dépendances internes** : Aucune  
**État** : COMPLETE  
**Anomalies** : Aucune

---

### Fichier : `ks_test.py` (159L)

**Rôle** : Test KS à deux échantillons (Kolmogorov-Smirnov) pour détecter une divergence distributionnelle entre retours shadow et backtest — implémentation pure Python sans scipy, p-value via approximation asymptotique de Smirnov.

**Inputs** :
- `compute_ks_2sample(shadow_returns: Iterable[float], backtest_returns: Iterable[float], *, acceptance_floor: float = 0.05) -> KolmogorovSmirnovResult`

**Outputs** :
- `KolmogorovSmirnovResult` (champs: `n_shadow`, `n_backtest`, `ks_statistic`, `p_value`, `passes_floor`, `acceptance_floor`)

**Equations mathématiques** :
```
# Statistique KS
D_{n,m} = sup_t |F_n(t) - G_m(t)|

# p-value Smirnov asymptotique
nm_eff = n*m / (n+m)
t = D_{n,m} * sqrt(nm_eff)
K(t) = 2 * sum_{k=1}^{100} (-1)^{k-1} * exp(-2*k^2*t^2)
p = clamp(K(t), 0, 1)
passes_floor = p >= acceptance_floor
```

**Logging** : Aucun  
**Dépendances internes** : Aucune  
**État** : COMPLETE  
**Anomalies** :
- Troncature série à `k=100` — hardcodée mais mathématiquement correcte (convergence rapide, erreur < 1e-15 après k~10)
- `1e-15` hardcodé (critère d'arrêt) — valeur technique standard

---

### Fichier : `mann_kendall.py` (145L)

**Rôle** : Test de tendance monotone Mann-Kendall pour détecter une dégradation des retours shadow — calcule S, tau de Kendall, variance avec correction pour les ex-aequo, z-score et p-value bilatérale, flags `descending_trend_detected` et `passes_floor`.

**Inputs** :
- `compute_mann_kendall_test(values: Iterable[float], *, acceptance_floor: float = 0.05) -> MannKendallResult`

**Outputs** :
- `MannKendallResult` (champs: `observation_count`, `s_statistic`, `kendall_tau`, `variance_s`, `z_score`, `p_value`, `trend_direction`, `has_significant_trend`, `descending_trend_detected`, `passes_floor`, `acceptance_floor`)

**Equations mathématiques** :
```
# Statistique S
S = sum_{i<j} sgn(x_j - x_i)
tau = S / (n*(n-1)/2)

# Variance avec correction ties
penalty = sum_{t_k > 1} t_k*(t_k-1)*(2*t_k+5)
Var(S) = [n*(n-1)*(2*n+5) - penalty] / 18

# z-score (continuity correction)
z = (S - 1) / sqrt(Var(S))  if S > 0
z = (S + 1) / sqrt(Var(S))  if S < 0
p = 2 * (1 - Phi(|z|))

descending_trend_detected = (tau < 0) and (p < acceptance_floor)
passes_floor = not descending_trend_detected
```

**Logging** : Aucun  
**Dépendances internes** : Aucune  
**État** : COMPLETE  
**Anomalies** : Aucune

---

### Fichier : `multiple_testing.py` (90L)

**Rôle** : Correction de Holm-Bonferroni step-down pour tests multiples — trie les hypothèses par p-value croissante, applique alpha ajusté décroissant, préserve l'ordre d'entrée dans le résultat.

**Inputs** :
- `apply_holm_bonferroni(hypotheses: Iterable[tuple[str, float]], *, family_alpha: float = 0.05) -> HolmBonferroniResult`

**Outputs** :
- `HolmBonferroniResult` (champs: `family_alpha`, `hypothesis_count`, `any_rejected`, `all_rejected`, `adjusted_hypotheses: tuple[HolmBonferroniAdjustedHypothesis,...]`)

**Equations mathématiques** :
```
# Tri par p-value croissante (stable: tie-break par id)
ordered = sort(hypotheses, key=(p_value, id))
alpha_i = family_alpha / (m - rank_i)   # rank_i = 0..m-1
rejected_i = (all prior rejected) and (p_value_i <= alpha_i)
```

**Logging** : Aucun  
**Dépendances internes** : Aucune  
**État** : COMPLETE  
**Anomalies** : Aucune

---

### Fichier : `multiple_testing_guard.py` (150L)

**Rôle** : Garde multiple-testing Harvey-Liu-Zhu (HLZ) pour les gates de promotion V5.3 — compose le nombre effectif de tests (paires observées vs plancher canonique de 20), calcule le haircut Sharpe HLZ eq.(8).

**Inputs** :
- `compose_hlz_test_count(*, observed_pair_count: int, pair_count_mode: HarveyLiuZhuPairCountMode, promotion_pair_floor: int = 20, repo_pair_universe_count: int = len(ALL_PAIRS)) -> HarveyLiuZhuTestCount`
- `compute_harvey_liu_zhu_deflated_sharpe(raw_sharpe: float, *, observation_count: int, observed_pair_count: int, ...) -> HarveyLiuZhuDeflatedSharpeResult`

**Outputs** :
- `HarveyLiuZhuTestCount`, `HarveyLiuZhuDeflatedSharpeResult`

**Equations mathématiques** :
```
# Nombre effectif de tests
k_hlz = observed_pair_count                               # mode OBSERVED_SHADOW
k_hlz = max(observed_pair_count, promotion_pair_floor=20) # mode PROMOTION_FLOOR

# Haircut HLZ eq.(8)
scale_factor = sqrt((n - k_hlz) / (n - 1))
deflated_sharpe = raw_sharpe * scale_factor
```

**Logging** : Aucun  
**Dépendances internes** : `interface_contracts.domain_types.ALL_PAIRS`  
**État** : COMPLETE  
**Anomalies** :
- `V53_CANONICAL_SHADOW_PAIR_FLOOR = 20` — constante module-level hardcodée (intentionnel, valeur canonique V5.3)
- Dépendance externe `interface_contracts.domain_types.ALL_PAIRS` : si ce module est absent ou modifié, `CURRENT_REPO_PAIR_UNIVERSE_COUNT` change silencieusement

---

### Fichier : `pot_gpd.py` (188L)

**Rôle** : Ajuste un modèle POT-GPD (Peaks Over Threshold, Generalized Pareto Distribution) sur les pertes au-delà d'un quantile seuil — estime xi (shape) et beta (scale) par moments, calcule la VaR POT et un intervalle bootstrap de dispersion.

**Inputs** :
- `fit_pot_gpd_tail_risk(losses: Iterable[float], *, config: PotGpdConfig | None = None) -> PotGpdResult`

**Outputs** :
- `PotGpdResult` (champs: `observation_count`, `threshold_quantile`, `threshold_u`, `exceedance_count`, `xi_hat`, `beta_hat`, `var_confidence`, `var_estimate`, `bootstrap_samples`, `bootstrap_success_count`, `var_ci_lower`, `var_ci_upper`, `bootstrap_dispersion_ratio`, `passes_dispersion`)

**Equations mathématiques** :
```
# Seuil
u = empirical_quantile(losses, threshold_quantile=0.90)
exceedances = {x - u : x in losses, x > u}

# Ajustement GPD par moments (Coles 2001)
mu_e = mean(exceedances)
s^2_e = sample_var(exceedances)
xi_hat = 0.5 * (1 - mu_e^2 / s^2_e)
beta_hat = mu_e * (1 - xi_hat)
# Guard: xi_hat < 1 (variance finie), beta_hat > 0

# VaR POT
p_tail = (n_exceedances / n_total) * (1 - var_confidence)
VaR = u + (beta/xi) * (p_tail^{-xi} - 1)     si |xi| >= 1e-9
VaR = u + beta * log(1/p_tail)                  si |xi| < 1e-9  (limite exponentielle)

# Bootstrap de dispersion (IID sur exceedances)
dispersion_ratio = (VaR_CI_97.5 - VaR_CI_2.5) / VaR_estimate
passes_dispersion = dispersion_ratio < 0.20
```

**Logging** : Aucun  
**Dépendances internes** : Aucune  
**État** : COMPLETE  
**Anomalies** :
- `passes_dispersion=dispersion_ratio < 0.20` — seuil `0.20` hardcodé sans calibration seam (P1 : threshold critique de qualité d'ajustement, devrait passer par artefact)
- `min_exceedances: int = Field(default=30, ge=3)` — 30 hardcodé dans config (configurable mais default non trivial)
- `1e-9` (tolérance xi nul) — valeur technique standard

---

### Fichier : `psr.py` (150L)

**Rôle** : Calcule le Probabilistic Sharpe Ratio (Bailey & López de Prado 2012) — P(true SR > SR* | données observées) en corrigeant pour non-normalité via moments d'ordre 3 et 4.

**Inputs** :
- `compute_probabilistic_sharpe_ratio(returns: Iterable[float], *, benchmark_sharpe: float = 0.0, acceptance_floor: float = 0.95) -> ProbabilisticSharpeRatioResult`

**Outputs** :
- `ProbabilisticSharpeRatioResult` (champs: `observation_count`, `benchmark_sharpe`, `sample_sharpe`, `skewness`, `kurtosis`, `psr`, `passes_floor`, `acceptance_floor`)

**Equations mathématiques** :
```
SR_hat = mean(r) / std_sample(r)
gamma_3 = population skewness, gamma_4 = population kurtosis

# Variance de SR_hat (Bailey-LdP 2012, eq. 3)
inner = 1 - gamma_3 * SR_hat + ((gamma_4 - 1) / 4) * SR_hat^2

# PSR
z = (SR_hat - SR*) * sqrt(n-1) / sqrt(inner)
PSR(SR*) = Phi(z)
passes_floor = PSR >= acceptance_floor
```

**Logging** : Aucun  
**Dépendances internes** : Aucune  
**État** : COMPLETE  
**Anomalies** : Aucune

---

### Fichier : `stationarity.py` (165L)

**Rôle** : Tests de stationnarité ADF (intercept, 0 lag) et KPSS niveau (kernel Bartlett, Newey-West) — verdict dual MI-9 : `passes_dual_test = ADF rejette racine unitaire ET KPSS ne rejette pas la stationnarité` (à 5%).

**Inputs** :
- `compute_adf_level_stationarity(series: Iterable[float]) -> AugmentedDickeyFullerResult`
- `compute_kpss_level_stationarity(series: Iterable[float]) -> KpssLevelStationarityResult`
- `evaluate_dual_stationarity(series: Iterable[float]) -> DualStationarityResult`

**Outputs** :
- `AugmentedDickeyFullerResult` (`statistic`, `rejects_unit_root_5pct`)
- `KpssLevelStationarityResult` (`bandwidth`, `statistic`, `rejects_stationarity_5pct`)
- `DualStationarityResult` (`adf`, `kpss`, `passes_dual_test`)

**Equations mathématiques** :
```
# ADF (OLS, lag 0, intercept)
delta_y_t = alpha + beta * y_{t-1} + eps_t
beta_hat = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x^2)
t_ADF = beta_hat / sqrt(var_beta)
rejects_unit_root_5pct = t_ADF <= -2.86

# KPSS
mean_y = mean(y)
S_t = sum_{i=1}^{t} (y_i - mean_y)   # partial sums
eta_hat = sum(S_t^2)
bandwidth L = round(sqrt(n))

# Variance long-terme Newey-West (Bartlett kernel)
gamma_0 = mean(eps_t^2)
LRV = gamma_0 + 2 * sum_{l=1}^{L} (1 - l/(L+1)) * gamma_l
KPSS = eta_hat / (n^2 * LRV)
rejects_stationarity_5pct = KPSS >= 0.463

# Valeurs critiques hardcodées (tables MacKinnon ADF / Kwiatkowski KPSS)
ADF:  10%=-2.57,  5%=-2.86,  1%=-3.43
KPSS: 10%=0.347,  5%=0.463,  1%=0.739
```

**Logging** : Aucun  
**Dépendances internes** : Aucune  
**État** : COMPLETE  
**Anomalies** :
- `critical_value_10pct: float = -2.57`, `critical_value_5pct: float = -2.86`, `critical_value_1pct: float = -3.43` — valeurs critiques ADF hardcodées dans le modèle Pydantic (tables MacKinnon, valeur intercept, n→∞). Acceptable pour les séries longues ; sous-optimal pour n < 50.
- `critical_value_10pct: float = 0.347`, `critical_value_5pct: float = 0.463`, `critical_value_1pct: float = 0.739` — valeurs critiques KPSS hardcodées (Kwiatkowski 1992).
- `rejects_unit_root_5pct=statistic <= -2.86` — seuil 5% hardcodé dans la logique de décision (pas de seam)
- `rejects_stationarity_5pct=statistic >= 0.463` — idem
- `bandwidth = round(sqrt(n))` — choix de bande passante hardcodé (convention standard)

---

### Fichier : `walkforward.py` (123L)

**Rôle** : Construit un plan de walk-forward avec purge et embargo — découpe `observation_count` observations en `fold_count` fenêtres de validation non-chevauchantes, avec embargo pré-validation et purge basée sur `label_horizon_size`.

**Inputs** :
- `build_purged_walk_forward_plan(observation_count: int, *, config: PurgedWalkForwardConfig) -> PurgedWalkForwardPlan`

**Outputs** :
- `PurgedWalkForwardPlan` (champs: `observation_count`, `fold_count`, `validation_window_size`, `embargo_size`, `label_horizon_size`, `folds: tuple[PurgedWalkForwardFold,...]`)
- Chaque `PurgedWalkForwardFold` : `fold_index`, `train_indices`, `embargo_indices`, `validation_indices`, plages de dates entières et comptages

**Equations mathématiques** :
```
total_validation_width = fold_count * validation_window_size
first_validation_start = n - total_validation_width

# Pour chaque fold k (k=0..fold_count-1)
validation_start = first_validation_start + k * validation_window_size
validation_end = validation_start + validation_window_size - 1
embargo_start = max(0, validation_start - embargo_size)
purge_start = max(0, validation_start - label_horizon_size)
train_end_exclusive = min(embargo_start, purge_start)
train_indices = [0, train_end_exclusive)
embargo_indices = [embargo_start, validation_start)
validation_indices = [validation_start, validation_end]

# Purge effective
purged_train_count = max(0, embargo_start - train_end_exclusive)
```

**Logging** : Aucun  
**Dépendances internes** : Aucune  
**État** : COMPLETE  
**Anomalies** : Aucune

---

## Package `calibration_loader/`

---

### Fichier : `__init__.py` (39L)

**Rôle** : Ré-exporte l'ensemble des symboles publics de `contracts.py` et `loader.py`.

**Re-exports publics** :
`CalibrationArtifact`, `CalibrationArtifactCollection`, `CalibrationManualSignature`, `CalibrationSignatureMode`, `CalibrationThresholdEntry`, `CalibrationArtifactFormatError`, `CalibrationArtifactNotFoundError`, `CalibrationArtifactSignatureError`, `CalibrationArtifactValidationError`, `CalibrationLoader`, `CalibrationLoaderError`, `CalibrationThresholdNotFoundError`, `load_calibration_artifact`, `load_calibration_collection`

**Logging** : Aucun  
**Dépendances internes** : `calibration_loader.contracts`, `calibration_loader.loader`  
**État** : COMPLETE  
**Anomalies** : Aucune

---

### Fichier : `contracts.py` (120L)

**Rôle** : Définit les contrats Pydantic pour les artefacts de calibration — `CalibrationThresholdEntry` (un seuil par id), `CalibrationArtifact` (artefact signé, hash SHA-256 du payload canonique), `CalibrationArtifactCollection` (agrégat multi-artefacts sans doublon de threshold_id).

**Inputs** :
- `CalibrationArtifact.model_validate(dict)` — validation depuis payload désérialisé
- `CalibrationArtifact.payload_hash_sha256() -> str` — hash du payload canonique
- `CalibrationArtifactCollection.threshold_entries -> tuple[CalibrationThresholdEntry,...]` — vue aplatie

**Outputs** :
- Modèles Pydantic frozen (immuables)

**Equations mathématiques** :
```
# Hash d'attestation
canonical_payload = json.dumps(sorted_keys(payload), separators=(',',':'))
signature.payload_hash_sha256 = SHA-256(canonical_payload.encode('utf-8'))
# La validation Pydantic compare le hash calculé au hash fourni (si non vide)
```

**Logging** : Aucun  
**Dépendances internes** : Aucune (stdlib + pydantic)  
**État** : COMPLETE  
**Anomalies** :
- `payload_hash_sha256: str = Field(default="", pattern=r"^[0-9a-f]{64}$|^$")` — la chaîne vide est autorisée, ce qui rend la vérification de hash optionnelle. Un artefact sans hash fourni n'est pas rejeté — seule la signature `signed_by` et `signed_at` sont obligatoires. C'est un choix délibéré (backward compat) mais constitue une faiblesse d'intégrité si les artefacts anciens sont réutilisés sans hash.

---

### Fichier : `loader.py` (156L)

**Rôle** : Charge et valide des artefacts de calibration depuis le disque (JSON ou YAML) — supporte un fichier unique ou un répertoire entier (tri alphabétique), vérifie la présence de la signature, expose `CalibrationLoader` (version-aware) avec `load()`, `get_entry()`, `get_value()`.

**Inputs** :
- `load_calibration_artifact(path: Path | str) -> CalibrationArtifact`
- `load_calibration_collection(path: Path | str) -> CalibrationArtifactCollection`
- `CalibrationLoader(root: Path | str).load(*, version: str) -> CalibrationArtifactCollection`
- `CalibrationLoader.get_entry(collection, threshold_id) -> CalibrationThresholdEntry`
- `CalibrationLoader.get_value(collection, threshold_id) -> bool | int | float | str`

**Outputs** :
- `CalibrationArtifact`, `CalibrationArtifactCollection`, `CalibrationThresholdEntry`, valeur scalaire

**Equations mathématiques** : Aucune (lecture disque + désérialisation)

**Logging** : Aucun  
**Dépendances internes** : `calibration_loader.contracts`  
**Dépendances externes** : `yaml` (PyYAML ou ruamel.yaml), `pydantic`  
**État** : COMPLETE  
**Anomalies** :
- Pas de timeout ni de limite de taille de fichier sur `path.read_text()` — un artefact pathologiquement grand pourrait bloquer
- `artifact_paths = sorted(child for child in candidate.iterdir() ...)` — tri alphabétique des artefacts dans un répertoire : l'ordre d'agrégation est déterministe mais dépend des noms de fichiers, ce qui n'est pas documenté explicitement dans les erreurs utilisateur

---

## Synthèse Groupe A

### Fichiers SKELETON

Aucun — tous les fichiers ont une logique métier complète.

### Fichiers PARTIAL

Aucun — toutes les branches sont couvertes, pas de TODO fonctionnel ni NotImplementedError.

### Anomalies critiques (hardcoded thresholds, NotImplementedError)

| Sévérité | Fichier | Ligne / zone | Anomalie |
|----------|---------|--------------|----------|
| P1 | `pot_gpd.py` | `passes_dispersion=dispersion_ratio < 0.20` | Seuil de dispersion 0.20 hardcodé dans la logique de décision — devrait être paramètre de `PotGpdConfig` ou artefact de calibration |
| P1 | `stationarity.py` | `rejects_unit_root_5pct=statistic <= -2.86` | Seuil de décision ADF 5% hardcodé — tables MacKinnon asymptotiques, sous-optimales pour n < 50 |
| P1 | `stationarity.py` | `rejects_stationarity_5pct=statistic >= 0.463` | Idem KPSS |
| P2 | `execution.py` | defaults `hard_cap_ms=1000.0`, `hard_cap_s=5.0`, `hard_cap_bps=50.0`, `hard_cap_quota_ratio=0.80`, `additive_margin_ms=200.0` | Plafonds humains hardcodés dans les signatures de fonctions — devraient idéalement transiter par des artefacts de calibration pour garantir la traçabilité entre déploiements |
| P2 | `execution.py` | `quantile=0.97725` dans `calibrate_spread_guard_threshold_bps` | Valeur dérivée implicite de mu+2sigma, commentaire absent |
| P2 | `contracts.py` | `payload_hash_sha256: str = Field(default="")` | Hash vide autorisé → vérification d'intégrité optionnelle sur les artefacts sans hash |
| P3 | `bootstrap.py` | `rng_seed: int = 53` | Graine RNG hardcodée dans `StationaryBootstrapConfig` (reproductibilité assurée mais non tracée dans artefacts) |
| P3 | `hansen_spa.py` | `rng_seed: int = 53` | Idem |
| P3 | `multiple_testing_guard.py` | `V53_CANONICAL_SHADOW_PAIR_FLOOR = 20` | Constante canonique module-level (intentionnelle mais doit rester synchronisée avec doc 14_SHADOW_GATE_MATH.md §...) |
| P3 | `energy_distance.py` | `random_seed: int | None = 42` | Graine par défaut hardcodée |
| P3 | `stationarity.py` | valeurs critiques dans modèles Pydantic (`critical_value_*`) | Tables hardcodées asymptotiques — correctes pour n > 200, approximatives pour n < 50 |
| P3 | `loader.py` | pas de limite de taille sur `read_text()` | Risque de blocage sur artefact pathologique |

### Dépendances internes manquantes

| Module | Importe | Statut |
|--------|---------|--------|
| `multiple_testing_guard.py` | `interface_contracts.domain_types.ALL_PAIRS` | A vérifier — si `ALL_PAIRS` change, `CURRENT_REPO_PAIR_UNIVERSE_COUNT` change silencieusement sans erreur |
| `execution.py` | `calibration_methods.hard_cap_floor` | Présent dans le même package — OK |
| `hansen_spa.py` | `calibration_methods.bootstrap.infer_stationary_block_length` | Présent dans le même package — OK |
| `calibration_loader.loader` | `yaml` (PyYAML) | Dépendance externe — doit figurer dans `pyproject.toml` / `requirements.txt` |

### Observations globales

- **Architecture** : Les deux packages sont cohérents et bien typés (Pydantic frozen sur tous les résultats). Aucun `except Exception`, aucun `print()`, aucun `type: ignore`, aucun `TODO/FIXME` détecté dans l'ensemble des 3 048 lignes.
- **Logging** : Aucun appel `logger.*` dans les deux packages — les erreurs sont levées via des exceptions nommées spécifiques. Acceptable pour des modules de calcul pur, mais l'absence de logging structuré structlog signifie que les invocations de calibration ne produisent pas de trace observable sans instrumentation externe.
- **Calibration seam** : Les fonctions de `execution.py` et `pot_gpd.py` exposent leurs plafonds comme paramètres de fonction mais pas comme artefacts chargeables depuis `calibration_loader` — la doctrine "thresholds go through calibration seams" (CLAUDE.md) n'est pas entièrement respectée pour ces modules.
