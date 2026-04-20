# 03_THRESHOLDS_CALIBRATION_SHADOW_MATH

## Included Source Docs
- docs/production_deployment_plan/11_DYNAMIC_THRESHOLDS_CATALOG.md
- docs/production_deployment_plan/11A_DYNAMIC_THRESHOLDS_REPO_CROSSCHECK.md
- docs/production_deployment_plan/13_CALIBRATION_METHODS.md
- docs/production_deployment_plan/14_SHADOW_GATE_MATH.md

---

## Source: docs/production_deployment_plan/11_DYNAMIC_THRESHOLDS_CATALOG.md

# Dynamic Thresholds Catalog â€” Aucun seuil hardcodÃ©

> **Principe directeur** â€” **Aucun seuil critique ne doit Ãªtre hardcodÃ© dans le code Python.** Tout seuil candidat est listÃ© dans ce catalogue, calibrÃ© via backtest dans le **Local IA Lab**, validÃ© via shadow avec **approbation humaine**, et chargÃ© au runtime depuis un **artefact de calibration signÃ©**.
>
> **Pourquoi** â€” Hardcoder un seuil = lier un comportement Ã  une opinion humaine de moment T sans traÃ§abilitÃ©, sans recalibration, sans audit. Ã€ 10 k$ rÃ©els, c'est inacceptable.
>
> **Source de vÃ©ritÃ©** â€” Chaque seuil pointe vers un fichier de calibration (`config/calibration/v1/...yml`) produit par le Local IA Lab et signÃ© par l'humain (cf. D-08).

---

## 1. Format de chaque entrÃ©e

```yaml
threshold_id: <unique_id>
description: <ce que le seuil contrÃ´le>
source_module: <chemin du fichier code qui consomme le seuil>
calibration_source: backtest | shadow | hybrid
calibration_artifact: config/calibration/v1/<file>.yml
default_value: <valeur initiale recommandÃ©e>
ic95_lower: <borne inf de l'IC95 sur backtest>
ic95_upper: <borne sup>
n_observations_min: <nb min d'observations pour recalibrer>
recalibration_freq: monthly | quarterly | yearly
human_signature_required: true | false
notes: <commentaire>
```

---

## 2. Catalogue par catÃ©gorie

### 2.1 CatÃ©gorie EDGE / ProfitabilitÃ©

#### THR-E01 â€” Edge multiplier minimum

```yaml
threshold_id: THR-E01
description: Multiplicateur minimum entre l'edge attendu et les coÃ»ts (fees + slippage). accept â‡” edge_bps â‰¥ multiplier Ã— (fee_rt_bps + slippage_bps)
source_module: src/scoring_backbone/fee_aware_edge_gate.py
calibration_source: backtest
calibration_artifact: config/calibration/v1/edge_gate.yml
default_value: 2.0
ic95_lower: 1.5
ic95_upper: 2.5
n_observations_min: 500
recalibration_freq: quarterly
human_signature_required: true
notes: Plus le multiplier est bas, plus on trade. Ã€ 2.0, on accepte ~50% des signaux backtest. Ã€ 3.0, ~25%. Calibrer par recherche grid sur Sharpe out-of-sample.
```

#### THR-E02 â€” Edge minimum absolu (bps)

```yaml
threshold_id: THR-E02
description: Edge minimum absolu en bps en-dessous duquel on ne trade jamais, mÃªme si le multiplier passe (filet de sÃ©curitÃ© numÃ©rique)
source_module: src/scoring_backbone/fee_aware_edge_gate.py
calibration_source: backtest
default_value: 15
ic95_lower: 10
ic95_upper: 25
recalibration_freq: quarterly
human_signature_required: true
notes: Anti edge < 1 bps en cas de bug. Si on trade des edges < 15 bps, c'est qu'on a survendu la prÃ©cision.
```

#### THR-E03 â€" Competitive Edge minimum par moteur (ce_min)

```yaml
threshold_id: THR-E03
description: Competitive Edge net minimum par moteur â€" en-dessous, le trade est rejetÃ© comme non-rentable
source_module: src/engines/engine_{a,b,c,d}/engine_{a,b,c,d}_runner.py + cost_feasibility_{a,b,c,d}.py
calibration_source: backtest (stationary block bootstrap IC 95% du CE net par paire)
calibration_artifact: config/calibration/v1/cost_feasibility.yml
default_value:
  engine_a: 0.0001
  engine_b: 0.0002
  engine_c: 0.00015
  engine_d: 0.00012
ic95_lower: pair-specific (bootstrap)
ic95_upper: pair-specific (bootstrap)
n_observations_min: 200
recalibration_freq: quarterly
human_signature_required: true
notes: |
  Valeurs par dÃ©faut actuellement hardcodÃ©es dans les EngineInput Pydantic models.
  Doivent migrer vers CalibrationLoader. Le ce_min est pair-spÃ©cifique en production
  (liquiditÃ©, spread moyen, volume). Engine B a le ce_min le plus Ã©levÃ© car
  mean-reversion a des CE plus serrÃ©s. Cf. 13_CALIBRATION_METHODS.md Â§2.1.
```

#### THR-E04 â€" Safety margin sur la profitabilitÃ© (delta_safe)

```yaml
threshold_id: THR-E04
description: Marge de sÃ©curitÃ© au-dessus du break-even â€" condition E[g] > E[c] + delta_safe
source_module: src/engines/engine_{a,b,c,d}/engine_{a,b,c,d}_runner.py + cost_feasibility_{a,b,c,d}.py
calibration_source: backtest (bootstrap IC + Almgren-Chriss slippage tail)
calibration_artifact: config/calibration/v1/cost_feasibility.yml
default_value:
  engine_a: 0.0005
  engine_b: 0.0008
  engine_c: 0.0005
  engine_d: 0.0005
ic95_lower: pair-specific
ic95_upper: pair-specific
n_observations_min: 200
recalibration_freq: quarterly
human_signature_required: true
notes: |
  delta_safe absorbe l'incertitude du modÃ¨le de coÃ»ts. Engine B est plus conservateur
  (0.0008) car le mean-reversion opÃ¨re sur des fenÃªtres plus courtes avec plus de
  variabilitÃ© de slippage. Doit intÃ©grer le percentile 95 du slippage rÃ©alisÃ© en shadow.
  Cf. 13_CALIBRATION_METHODS.md Â§2.1 THR-E01/E02 formule complÃ¨te.
```

---

### 2.2 CatÃ©gorie RISK / Loss budget

#### THR-R01 â€” Daily P&L breaker (intraday)

```yaml
threshold_id: THR-R01
description: Si DD intraday > X% â†’ SHADOW automatique le jour mÃªme
source_module: src/risk_backbone/loss_budgeter/daily_pnl_breaker.py
calibration_source: backtest + shadow
default_value: 0.02   # -2%
ic95_lower: 0.015
ic95_upper: 0.03
recalibration_freq: monthly
human_signature_required: true
notes: Trop strict (1.5%) = pause trop frÃ©quente sur du bruit. Trop lÃ¢che (3%) = laisse couler des pertes structurelles. Phase 0 doit produire la valeur calibrÃ©e.
```

#### THR-R02 â€” Weekly P&L breaker

```yaml
threshold_id: THR-R02
description: Si DD week > X% â†’ kill switch ARMED, retour Phase 2
source_module: src/risk_backbone/loss_budgeter/weekly_breaker.py
calibration_source: backtest
default_value: 0.10   # -10%
ic95_lower: 0.07
ic95_upper: 0.13
recalibration_freq: quarterly
human_signature_required: true
```

#### THR-R03 â€” Monthly P&L breaker

```yaml
threshold_id: THR-R03
description: Si DD month > X% â†’ kill switch CRITICAL, retour Phase 1
source_module: src/risk_backbone/loss_budgeter/monthly_breaker.py
calibration_source: backtest
default_value: 0.15   # -15%
ic95_lower: 0.10
ic95_upper: 0.20
recalibration_freq: quarterly
human_signature_required: true
```

#### THR-R04 â€” Position size max (USD)

```yaml
threshold_id: THR-R04
description: Taille max d'une position en USD (= cap absolu)
source_module: src/risk_backbone/exposure_budgeter/position_cap.py
calibration_source: hybrid (capital Ã— ratio + min/max bornes)
default_value: 2000   # 20% du capital cible
recalibration_freq: monthly
human_signature_required: true
notes: Ã‰volue avec le scaling Phase 4. Ã€ 500 USD MICRO_LIVE, cap = 100. Ã€ 10k LIVE, cap = 2000.
```

#### THR-R05 â€” Nb positions concurrentes max

```yaml
threshold_id: THR-R05
description: Nombre max de positions ouvertes en parallÃ¨le
source_module: src/risk_backbone/exposure_budgeter/concurrent_cap.py
calibration_source: backtest
default_value: 5
ic95_lower: 3
ic95_upper: 7
recalibration_freq: quarterly
human_signature_required: true
notes: 5 positions Ã— 2k = 10k = 100% capital. CohÃ©rent avec un fully-invested mode max.
```

#### THR-W01 â€" Drawdown warning threshold (risk runtime)

```yaml
threshold_id: THR-W01
description: Seuil de drawdown intra-session dÃ©clenchant un warning dans le risk runtime (OBSERVE_ONLY)
source_module: src/risk_backbone/risk_runtime.py (RiskLimits.drawdown_warning_threshold_pct)
calibration_source: backtest (distribution historique des DD intra-session)
calibration_artifact: config/calibration/v1/risk_limits.yml
default_value: 0.02   # 2%
ic95_lower: 0.015
ic95_upper: 0.03
n_observations_min: 100
recalibration_freq: monthly
human_signature_required: true
notes: |
  ConsommÃ© par evaluate_drawdown_guard() via RiskLimits. Ce seuil est distinct de
  THR-R01 (daily PnL breaker) : THR-W01 agit sur le runtime risk gate (OBSERVE_ONLY),
  THR-R01 agit sur le breaker (retour SHADOW). DÃ©faut 2% actuellement hardcodÃ©
  dans le model Pydantic. Doit Ãªtre injectÃ© depuis CalibrationLoader au boot.
  Calibrer via percentile 70 de la distribution des DD intra-session sur backtest.
```

#### THR-W02 â€" Drawdown observe threshold (risk runtime)

```yaml
threshold_id: THR-W02
description: Seuil de drawdown intra-session dÃ©clenchant un REDUCE_EXPOSURE dans le risk runtime
source_module: src/risk_backbone/risk_runtime.py (RiskLimits.drawdown_observe_threshold_pct)
calibration_source: backtest (EVT/POT tail de la distribution des DD)
calibration_artifact: config/calibration/v1/risk_limits.yml
default_value: 0.04   # 4%
ic95_lower: 0.03
ic95_upper: 0.06
n_observations_min: 100
recalibration_freq: monthly
human_signature_required: true
notes: |
  Threshold REDUCE_EXPOSURE = plus strict que WARNING. Calibrer via VaR 99%
  de la distribution des DD intra-session (EVT/POT/GPD, cf. 13_CALIBRATION_METHODS.md
  Â§5.2). DÃ©faut 4% actuellement hardcodÃ© dans RiskLimits. Le ratio W02/W01 = 2.0
  doit Ãªtre maintenu pour Ã©viter les false positive cascades.
```

---

### 2.3 CatÃ©gorie REGIME

#### THR-RG01 â€” BTC realized vol 24h â†’ STRESSED

```yaml
threshold_id: THR-RG01
description: Seuil de rÃ©alisÃ©e vol BTC 24h pour passer CALM â†’ STRESSED
source_module: src/regime_classifier/regime_lite.py
calibration_source: backtest
default_value: 0.04   # 4% daily realized vol
ic95_lower: 0.03
ic95_upper: 0.06
recalibration_freq: quarterly
human_signature_required: true
notes: Calibrer sur la distribution historique. Veut probablement ~percentile 70.
```

#### THR-RG02 â€” BTC drop 1h â†’ EXTREME

```yaml
threshold_id: THR-RG02
description: Seuil de drop BTC en 1h pour passer en EXTREME (peu importe l'Ã©tat prÃ©cÃ©dent)
source_module: src/regime_classifier/regime_lite.py
calibration_source: backtest
default_value: 0.05   # -5% en 1h
ic95_lower: 0.03
ic95_upper: 0.07
recalibration_freq: quarterly
human_signature_required: true
notes: Capitulation marker. Mars 2020 avait des drops -10% en 1h.
```

#### THR-RG03 â€” HystÃ©rÃ©sis durÃ©e minimum dans un Ã©tat

```yaml
threshold_id: THR-RG03
description: DurÃ©e minimum dans un Ã©tat avant de pouvoir downgrade (anti-flapping)
source_module: src/regime_classifier/regime_lite.py
calibration_source: empirical
default_value: 7200   # 2h en secondes
ic95_lower: 3600
ic95_upper: 14400
recalibration_freq: yearly
human_signature_required: false
notes: HystÃ©rÃ©sis 2h Ã©vite les passages STRESSED â†’ CALM â†’ STRESSED en 30min sur du bruit.
```

#### THR-RG04 â€” Cooldown EXTREME (durÃ©e pendant laquelle on ne re-trade pas)

```yaml
threshold_id: THR-RG04
description: DurÃ©e minimum d'arrÃªt total des nouvelles entries aprÃ¨s un passage en EXTREME
source_module: src/regime_classifier/regime_lite.py
calibration_source: backtest + judgment
default_value: 86400   # 24h en secondes
ic95_lower: 43200
ic95_upper: 172800
recalibration_freq: yearly
human_signature_required: true
notes: 24h post-capitulation laisse le marchÃ© se stabiliser. Les flash recovery V-shapes prennent souvent 12-48h.
```

---

### 2.4 CatÃ©gorie EXECUTION / Latency / Slippage

#### THR-X01 â€” Time sync drift max (ms)

```yaml
threshold_id: THR-X01
description: Drift max horloge locale vs Binance avant alerte
source_module: src/venue_adapters/binance_spot/time_sync.py
calibration_source: empirical
default_value: 500   # 500ms
ic95_lower: 200
ic95_upper: 1000
recalibration_freq: yearly
human_signature_required: false
notes: Binance accepte jusqu'Ã  1000ms (recvWindow). 500ms laisse une marge sÃ»re.
```

#### THR-X02 â€” WS gap detection (sec)

```yaml
threshold_id: THR-X02
description: DurÃ©e de gap WS avant blocage des nouveaux trades
source_module: src/venue_adapters/binance_spot/ws_client.py
calibration_source: empirical
default_value: 5   # 5 secondes
ic95_lower: 3
ic95_upper: 10
recalibration_freq: yearly
human_signature_required: false
```

#### THR-X03 â€” Rate limit Binance throttle (% du quota)

```yaml
threshold_id: THR-X03
description: Pourcentage du quota Binance Ã  partir duquel on throttle
source_module: src/execution_backbone/rate_limiter.py (ExecutionRateLimitModel.quota_ratio_ceiling)
calibration_source: empirical (Local IA Lab projection THR-X03)
calibration_artifact: config/calibration/v1/execution.yml
default_value: 0.80   # 80% du quota
recalibration_freq: yearly
human_signature_required: false
notes: |
  ConsommÃ© par evaluate_execution_rate_limit(). Le fichier rÃ©el est
  src/execution_backbone/rate_limiter.py (pas venue_adapters). Le quota ratio
  est une projection du Local IA Lab sur le dÃ©bit max acceptable. 80% de
  1200 weight/min = 960. Note : ce seuil contrÃ´le le quota d'exÃ©cution
  applicatif, PAS le tracking de poids API Binance (qui nÃ©cessite un token
  bucket sÃ©parÃ© dans venue_adapters/binance_spot/ â€" cf. W-07 work plan).
```

#### THR-X04 â€” Spread max acceptable (bps)

```yaml
threshold_id: THR-X04
description: Si bid-ask spread > X bps â†’ pas de trade
source_module: src/execution_backbone/spread_guard.py
calibration_source: backtest par symbole
default_value: 30   # 30 bps
ic95_lower: 10
ic95_upper: 50
recalibration_freq: monthly (par symbole)
human_signature_required: true
notes: Calibrer par symbole. BTC/ETH typiquement < 5 bps. Mid-caps 10-30. Large spread = signal de fuir.
```

#### THR-X05 â€” Slippage estimÃ© (bps par taille)

```yaml
threshold_id: THR-X05
description: ModÃ¨le de slippage estimÃ© en fonction de la taille d'order et de la depth
source_module: src/execution_backbone/execution_cost_meter/slippage_model.py
calibration_source: hybrid (orderbook depth + historical fills)
default_value: function of (order_size_usd, orderbook_depth)
recalibration_freq: monthly
human_signature_required: true
notes: ModÃ¨le, pas un nombre. Ã€ 100 USD/order et depth 100k USD, slippage â‰ˆ 1-3 bps. Calibrer par paire.
```

---

### 2.5 CatÃ©gorie HALAL

#### THR-H01 â€” Edge minimum aprÃ¨s purification

```yaml
threshold_id: THR-H01
description: Edge minimum aprÃ¨s dÃ©duction estimÃ©e de la purification (si stablecoin avec composante intÃ©rÃªt)
source_module: src/sharia_compliance/purification_calculator.py
calibration_source: judgment + fatwa
default_value: 0.02   # 2 bps de marge supplÃ©mentaire
recalibration_freq: yearly
human_signature_required: true
notes: Petit haircut additionnel pour absorber la part purification. Optionnel selon dÃ©cision D-03.
```

#### THR-H02 â€” Audit hebdomadaire features Binance

```yaml
threshold_id: THR-H02
description: FrÃ©quence de l'audit qui vÃ©rifie qu'aucune feature interest-bearing n'est activÃ©e sur le compte
source_module: src/sharia_compliance/account_features_audit.py
calibration_source: empirical
default_value: 604800   # 7 jours en secondes
human_signature_required: false
notes: 7 jours = compromis entre charge et rÃ©activitÃ©. Sur dÃ©tection : alerte CRITICAL immÃ©diate.
```

#### THR-H03 â€” Purification rate (annual)

```yaml
threshold_id: THR-H03
description: Taux annuel de purification estimÃ© sur la balance stable (USDT)
source_module: src/sharia_compliance/purification_calculator.py
calibration_source: external (T-Bill yield + papier commercial)
default_value: 0.02   # 2% du balance moyen mensuel
recalibration_freq: yearly
human_signature_required: true
notes: Ã€ ajuster selon les rapports Tether trimestriels. Approximation conservative.
```

---

### 2.6 CatÃ©gorie SHADOW gates

#### THR-S01 â€” Sharpe simulÃ© minimum SHADOW M1

```yaml
threshold_id: THR-S01
description: Sharpe simulÃ© minimum pour passer gate G2.1 (fin SHADOW mois 1)
source_module: docs/production_deployment_plan/07_PHASE_PLAN_0_TO_4.md (rÃ©fÃ©rence) + scripts/shadow_gate_check.py
calibration_source: backtest (Phase 0 produit la valeur rÃ©aliste)
default_value: 0.5
ic95_lower: 0.3
ic95_upper: 0.7
recalibration_freq: per phase
human_signature_required: true
notes: Volontairement peu strict pour M1 (Ã©chantillon faible). Strict augmente sur M2/M3.
```

#### THR-S02 â€” Sharpe simulÃ© minimum SHADOW M2

```yaml
threshold_id: THR-S02
default_value: 0.6
recalibration_freq: per phase
human_signature_required: true
```

#### THR-S03 â€” Sharpe simulÃ© minimum SHADOW M3

```yaml
threshold_id: THR-S03
default_value: 0.7
recalibration_freq: per phase
human_signature_required: true
```

#### THR-S04 â€” Max DD simulÃ© maximum SHADOW (cumulÃ©)

```yaml
threshold_id: THR-S04
default_value: 0.12   # 12%
recalibration_freq: per phase
human_signature_required: true
```

#### THR-S05 â€” Nb dÃ©cisions cumulÃ©es minimum SHADOW M3

```yaml
threshold_id: THR-S05
default_value: 100
recalibration_freq: per phase
human_signature_required: true
notes: En-dessous, pas de signification statistique pour valider GO MICRO_LIVE.
```

#### THR-S06 â€" Max allowed CE net drop (shadow gate)

```yaml
threshold_id: THR-S06
description: DÃ©gradation maximale tolÃ©rÃ©e du Competitive Edge net entre backtest et shadow
source_module: src/protocols/contracts.py (ShadowGateCheckInput.max_allowed_ce_net_drop)
calibration_source: shadow (comparaison backtest vs shadow rÃ©alisÃ©)
calibration_artifact: config/calibration/v1/shadow_gates.yml
default_value: 0.0005
ic95_lower: 0.0003
ic95_upper: 0.0010
n_observations_min: 50
recalibration_freq: per phase
human_signature_required: true
notes: |
  Mesure la dÃ©gradation du CE entre backtest et shadow. Si CE_shadow - CE_backtest < -THR-S06,
  le gate Ã©choue. Cf. 14_SHADOW_GATE_MATH.md Â§3.3. La valeur 0.0005 (5 bps) est un
  paramÃ¨tre de fonction avec dÃ©faut dans le contrat Pydantic (protocols/contracts.py:448).
  Calibrer via la distribution empirique des Ã©carts CE backtest/shadow sur la pÃ©riode
  de shadow complet. Percentile 90 du delta nÃ©gatif.
```

---

### 2.7 CatÃ©gorie SCALING (Phase 4)

#### THR-SC01 â€” Capital initial MICRO_LIVE (USD)

```yaml
threshold_id: THR-SC01
default_value: 500
human_signature_required: true
notes: Cf. D-05.
```

#### THR-SC02 â€” Capital target LIVE (USD)

```yaml
threshold_id: THR-SC02
default_value: 10000
human_signature_required: true
```

#### THR-SC03 â€” Step de scaling (USD)

```yaml
threshold_id: THR-SC03
default_value: [500, 2000, 5000, 10000]
human_signature_required: true
notes: Cf. D-06. Liste des paliers.
```

#### THR-SC04 â€” DurÃ©e minimum entre paliers (jours)

```yaml
threshold_id: THR-SC04
default_value: 14   # 2 semaines
human_signature_required: true
```

---

### 2.8 CatÃ©gorie INFRA

#### THR-I01 â€” Disk free alerte (warning)

```yaml
threshold_id: THR-I01
default_value: 0.30   # 30% libre
source_module: src/monitoring/disk_monitor.py
human_signature_required: false
```

#### THR-I02 â€” Disk free alerte (critical / kill switch)

```yaml
threshold_id: THR-I02
default_value: 0.10   # 10% libre
source_module: src/monitoring/disk_monitor.py
human_signature_required: false
notes: < 10% â†’ kill switch automatique. Ã‰vite les writes partiels.
```

#### THR-I03 â€” Log retention (jours)

```yaml
threshold_id: THR-I03
default_value: 90
human_signature_required: false
```

#### THR-I04 â€” Reconciliation freq (sec)

```yaml
threshold_id: THR-I04
default_value: 3600   # 1h
source_module: src/execution_backbone/reconciliation_layer/scheduler.py
human_signature_required: false
notes: Toutes les heures + au boot. Plus frÃ©quent = surcoÃ»t API. Moins frÃ©quent = drift latent.
```

---

## 3. Tableau de synthÃ¨se â€” tous les seuils

| ID | CatÃ©gorie | Default | Calibration | Recal freq | Sig humaine |
|---|---|---|---|---|---|
| THR-E01 | Edge multiplier | 2.0 | backtest | quarterly | âœ” |
| THR-E02 | Edge min abs (bps) | 15 | backtest | quarterly | âœ” |
| **THR-E03** | **ce_min per engine** | **A:0.0001 B:0.0002 C:0.00015 D:0.00012** | **backtest/bootstrap** | **quarterly** | **âœ”** |
| **THR-E04** | **delta_safe per engine** | **A:0.0005 B:0.0008 C:0.0005 D:0.0005** | **backtest/bootstrap** | **quarterly** | **âœ”** |
| THR-R01 | Daily P&L breaker | -2% | bt+shadow | monthly | âœ” |
| THR-R02 | Weekly P&L breaker | -10% | backtest | quarterly | âœ” |
| THR-R03 | Monthly P&L breaker | -15% | backtest | quarterly | âœ” |
| THR-R04 | Position size max (USD) | 2000 | hybrid | monthly | âœ” |
| THR-R05 | Nb positions max | 5 | backtest | quarterly | âœ” |
| **THR-W01** | **DD warning (risk runtime)** | **2%** | **backtest** | **monthly** | **âœ”** |
| **THR-W02** | **DD observe (risk runtime)** | **4%** | **backtest/EVT** | **monthly** | **âœ”** |
| THR-RG01 | BTC vol â†’ STRESSED | 4% | backtest | quarterly | âœ” |
| THR-RG02 | BTC drop 1h â†’ EXTREME | -5% | backtest | quarterly | âœ” |
| THR-RG03 | HystÃ©rÃ©sis durÃ©e | 2h | empirical | yearly | â€” |
| THR-RG04 | EXTREME cooldown | 24h | bt+judgment | yearly | âœ” |
| THR-X01 | Time sync drift (ms) | 500 | empirical | yearly | â€” |
| THR-X02 | WS gap (sec) | 5 | empirical | yearly | â€” |
| THR-X03 | Rate limit throttle | 80% | empirical/Lab | yearly | â€” |
| THR-X04 | Spread max (bps) | 30 | backtest/sym | monthly | âœ” |
| THR-X05 | Slippage model | function | hybrid | monthly | âœ” |
| THR-H01 | Edge post-purification | 2 bps | judgment | yearly | âœ” |
| THR-H02 | Audit features Binance freq | 7j | empirical | â€” | â€” |
| THR-H03 | Purification rate | 2%/an | external | yearly | âœ” |
| THR-S01 | Sharpe SHADOW M1 | 0.5 | backtest | per phase | âœ” |
| THR-S02 | Sharpe SHADOW M2 | 0.6 | backtest | per phase | âœ” |
| THR-S03 | Sharpe SHADOW M3 | 0.7 | backtest | per phase | âœ” |
| THR-S04 | Max DD SHADOW | 12% | backtest | per phase | âœ” |
| THR-S05 | Nb dÃ©cisions SHADOW M3 | 100 | empirical | per phase | âœ” |
| **THR-S06** | **Max CE net drop (shadow)** | **0.0005** | **shadow** | **per phase** | **âœ”** |
| THR-SC01 | Capital MICRO_LIVE | 500 | decision | â€” | âœ” |
| THR-SC02 | Capital LIVE | 10000 | decision | â€” | âœ” |
| THR-SC03 | Steps scaling | [500,2000,5000,10000] | decision | â€” | âœ” |
| THR-SC04 | Step duration min (jours) | 14 | decision | â€” | âœ” |
| THR-I01 | Disk warn | 30% libre | â€” | â€” | â€” |
| THR-I02 | Disk critical | 10% libre | â€” | â€” | â€” |
| THR-I03 | Log retention | 90j | â€” | â€” | â€” |
| THR-I04 | Reconciliation freq | 1h | â€” | â€” | â€” |

**Total : 37 seuils dynamiques rÃ©els** identifiÃ©s, dont **27 nÃ©cessitent une signature humaine** pour usage production.

> **Audit 2026-04-13** : +5 entrÃ©es (THR-E03, THR-E04, THR-W01, THR-W02, THR-S06) dÃ©couvertes par audit code vs plan. THR-X03 source_module corrigÃ© (execution_backbone, pas venue_adapters).

---

## 4. Architecture de chargement runtime

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  Local IA Lab (machine personnelle, jamais sur VPS)        â”‚
â”‚                                                              â”‚
â”‚  1. Backtest exhaustif via meta_learning/                   â”‚
â”‚  2. Production de calibration_v<N>.json                     â”‚
â”‚  3. Lecture humaine                                         â”‚
â”‚  4. Signature â†’ calibration_v<N>_signed.yml                 â”‚
â”‚                                                              â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                         â”‚
                         â”‚ rsync + signature verify
                         â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  VPS Hetzner CX43                                            â”‚
â”‚                                                              â”‚
â”‚  config/calibration/v<N>/                                    â”‚
â”‚    â”œâ”€â”€ edge_gate.yml                                        â”‚
â”‚    â”œâ”€â”€ loss_budget.yml                                      â”‚
â”‚    â”œâ”€â”€ regime_lite.yml                                      â”‚
â”‚    â”œâ”€â”€ shadow_gates.yml                                     â”‚
â”‚    â””â”€â”€ signature.asc (GPG ou simple hash signed)            â”‚
â”‚                                                              â”‚
â”‚  Au boot :                                                  â”‚
â”‚  1. calibration_loader.load(version=v<N>)                   â”‚
â”‚  2. Verify signature â†’ si KO, refuse de dÃ©marrer            â”‚
â”‚  3. Charge tous les seuils en mÃ©moire                       â”‚
â”‚  4. Instancie les modules avec les seuils chargÃ©s           â”‚
â”‚                                                              â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

**Modules concernÃ©s** :
- Nouveau : `src/calibration_loader/` (Ã  coder dans la Phase 1, tranche dÃ©pendante de toutes les autres)
- ModifiÃ© : tous les modules consommant un seuil dans le tableau ci-dessus

**Invariant central** :
> Aucun module Python ne doit contenir une valeur numÃ©rique magique correspondant Ã  un seuil critique. Toute valeur numÃ©rique doit venir de `calibration_loader.get(threshold_id)`.

**Audit** : grep pÃ©riodique sur `src/` pour dÃ©tecter les regex `\b\d+\.\d+\b` dans les nouveaux fichiers et flagger les valeurs suspectes.

---

## 5. Prochaines actions concrÃ¨tes

1. **Phase 0** : Local IA Lab produit `calibration_v1.json` avec tous les 32 seuils reels
2. **Humain** : signature de `calibration_v1_signed.yml`
3. **Tranche T0 (prÃ©liminaire P0)** : agent codeur code `src/calibration_loader/` (50-150 LOC)
4. **Toutes les autres tranches** : utilisent `calibration_loader.get(...)` pour les seuils, jamais de valeurs hardcodÃ©es
5. **Recalibration trimestrielle** : `calibration_v2`, `v3`, ... avec versioning conservÃ© pour audit

---

**Suite logique** : `12_LOCAL_LAB_VS_VPS_SEPARATION.md` â€” oÃ¹ vit chaque chose.



---

## Source: docs/production_deployment_plan/11A_DYNAMIC_THRESHOLDS_REPO_CROSSCHECK.md

# Dynamic Thresholds Repo Cross-Check

> But: executer la tranche intermediaire `W1` definie dans `09_CODING_SLICES_FOR_IMPLEMENTING_AGENT.md`.
>
> Methode: lire `11_DYNAMIC_THRESHOLDS_CATALOG.md`, extraire chaque `threshold_id`, comparer son `source_module` au repo reel, puis classer chaque seuil en `exists / partial / future target`.
>
> Regle: le repo gagne contre le MD. Un module absent dans le repo n'est pas un "bug cache"; c'est un `future target` ou un `partial` selon l'existence d'une surface voisine deja codee.

---

## 1. Legende

- `exists`: le consommateur exact du catalogue existe deja dans le repo et peut etre branche a un futur `calibration_loader` sans changement de topologie.
- `partial`: le module exact n'existe pas encore, mais une surface voisine ou une brique de meme famille existe deja dans le repo ou dans les docs de phase.
- `future target`: la famille de modules n'existe pas encore dans le repo actuel; le seuil ne doit pas etre traite comme regression du code courant.

---

## 2. Resume

- Seuils reels comptes: `32`
- `exists`: `6`
- `partial`: `25`
- `future target`: `1`

Verdict:

1. Le catalogue `11_...` est utile et exploitable des maintenant.
2. Il ne decrit pas majoritairement des consommateurs deja codes; il decrit surtout le **backlog de calibration** a brancher sur les phases P0/P1.
3. Le prochain travail logique apres ce cross-check est `W2`:
   - preparer le contrat partage de calibration
   - s'aligner maintenant sur l'ownership fixe par `12_LOCAL_LAB_VS_VPS_SEPARATION.md`

---

## 3. Inventory

| Threshold | Catalog source | Repo status | Current evidence | Next bounded slice |
|---|---|---|---|---|
| `THR-E01` | `src/scoring_backbone/fee_aware_edge_gate.py` | `exists` | `src/scoring_backbone/fee_aware_edge_gate.py` existe; `src/local_replay_runtime/edge_gate_calibration.py` produit déjà l'artefact partagé côté Local IA Lab | `T6 / P0-3` wiring runtime |
| `THR-E02` | `src/scoring_backbone/fee_aware_edge_gate.py` | `exists` | même constat que `THR-E01`; conversion explicite `expected_cost` fraction -> bps déjà codée dans le helper | `T6 / P0-3` wiring runtime |
| `THR-R01` | `src/risk_backbone/loss_budgeter/daily_pnl_breaker.py` | `partial` | `src/risk_backbone/loss_budgeter/` existe; `daily_pnl_breaker.py` est absent; `drawdown_guard.py` existe | `P1-3` |
| `THR-R02` | `src/risk_backbone/loss_budgeter/weekly_breaker.py` | `partial` | famille `loss_budgeter` presente; wrapper hebdo absent | `P1-3` |
| `THR-R03` | `src/risk_backbone/loss_budgeter/monthly_breaker.py` | `partial` | famille `loss_budgeter` presente; wrapper mensuel absent | `P1-3` |
| `THR-R04` | `src/risk_backbone/exposure_budgeter/position_cap.py` | `partial` | `src/risk_backbone/exposure_budgeter/` existe; `position_cap_guard.py` existe; `position_cap.py` est absent | risk calibration integration later |
| `THR-R05` | `src/risk_backbone/exposure_budgeter/concurrent_cap.py` | `partial` | `exposure_budgeter` existe; module exact absent | risk calibration integration later |
| `THR-RG01` | `src/regime_classifier/regime_lite.py` | `exists` | package `src/regime_classifier/` now exists with typed 3-state helper and documented threshold loader; live hooks still pending | `P1-1` runtime/risk wiring later |
| `THR-RG02` | `src/regime_classifier/regime_lite.py` | `exists` | same typed helper now carries explicit direct-EXTREME trigger for 1h BTC drop; governed hooks still pending | `P1-1` runtime/risk wiring later |
| `THR-RG03` | `src/regime_classifier/regime_lite.py` | `exists` | same typed helper now carries bounded downgrade hysteresis state memory; provider/runtime wiring still pending | `P1-1` runtime/risk wiring later |
| `THR-RG04` | `src/regime_classifier/regime_lite.py` | `exists` | same typed helper now carries EXTREME cooldown window for entry blocking; risk kill/entry hooks still pending | `P1-1` runtime/risk wiring later |
| `THR-X01` | `src/venue_adapters/binance_spot/time_sync.py` | `exists` | `src/venue_adapters/binance_spot/time_sync.py` existe et resout deja `THR-X01` via `calibration_loader` et `config/binance_adapter.yml` | `T1 / P0-1.A` |
| `THR-X02` | `src/venue_adapters/binance_spot/ws_client.py` | `exists` | `src/venue_adapters/binance_spot/ws_client.py`, `orderbook_manager.py`, le provider REST explicite de `depth snapshot`, et `resolve_websocket_gap_threshold_s()` existent | `T3 / P0-1.B` |
| `THR-X03` | `src/venue_adapters/binance_spot/rate_limiter.py` | `future target` | famille venue adapter absente | `T1/T3 / P0-1` |
| `THR-X04` | `src/execution_backbone/spread_guard.py` | `partial` | `src/execution_backbone/` existe, mais `spread_guard.py` est absent | execution guard slice later |
| `THR-X05` | `src/execution_backbone/execution_cost_meter/slippage_model.py` | `partial` | `src/execution_backbone/execution_cost_meter/` existe, mais `slippage_model.py` est absent | execution cost slice later |
| `THR-H01` | `src/sharia_compliance/purification_calculator.py` | `partial` | `purification_calculator.py` existe, mais le haircut edge post-purification n'est pas encore branché au runtime | `T5 / P0-2` |
| `THR-H02` | `src/sharia_compliance/account_features_audit.py` | `exists` | `account_features_audit.py` existe, résout déjà la fréquence via `calibration_loader`, et a maintenant un provider Binance read-only + launcher borné | `T5 / P0-2` |
| `THR-H03` | `src/sharia_compliance/purification_calculator.py` | `exists` | `purification_calculator.py` existe et résout déjà le taux annuel via `calibration_loader` | `T5 / P0-2` |
| `THR-S01` | `docs/production_deployment_plan/07_PHASE_PLAN_0_TO_4.md` + `scripts/shadow_gate_check.py` | `partial` | le plan de phase existe; `scripts/shadow_gate_check.py` est absent; le rail Shadow code/runtime existe deja | shadow gate review later |
| `THR-S02` | no explicit `source_module` in catalog | `partial` | seuil de gate de phase uniquement documente dans `07_PHASE_PLAN_0_TO_4.md` | shadow gate review later |
| `THR-S03` | no explicit `source_module` in catalog | `partial` | seuil de gate de phase uniquement documente | shadow gate review later |
| `THR-S04` | no explicit `source_module` in catalog | `partial` | seuil de gate de phase uniquement documente | shadow gate review later |
| `THR-S05` | no explicit `source_module` in catalog | `partial` | seuil de gate de phase uniquement documente | shadow gate review later |
| `THR-SC01` | no explicit `source_module` in catalog | `partial` | seuil de decision humaine Phase 3/4; pas de consommateur runtime actuel | depends on `D-05` |
| `THR-SC02` | no explicit `source_module` in catalog | `partial` | seuil de decision humaine Phase 4; pas de consommateur runtime actuel | depends on scaling policy |
| `THR-SC03` | no explicit `source_module` in catalog | `partial` | palier de scaling documente, pas de consommateur runtime actuel | depends on scaling policy |
| `THR-SC04` | no explicit `source_module` in catalog | `partial` | duree min entre paliers documentee, pas de consommateur runtime actuel | depends on scaling policy |
| `THR-I01` | `src/monitoring/disk_monitor.py` | `partial` | `src/monitoring/` existe; `disk_monitor.py` est absent | `P1-5` |
| `THR-I02` | `src/monitoring/disk_monitor.py` | `partial` | meme constat que `THR-I01` | `P1-5` |
| `THR-I03` | no explicit `source_module` in catalog | `partial` | `src/execution_backbone/reconciliation_layer/` existe, mais pas de scheduler/log retention module dedie | `P1-2` or infra slice |
| `THR-I04` | `src/execution_backbone/reconciliation_layer/scheduler.py` | `partial` | `reconciliation_layer/` existe, `scheduler.py` absent | `P1-2` |

---

## 4. Category verdict

### 4.1 Categories already adjacent to existing code (`partial`)

- `EDGE`: la famille `scoring_backbone` existe deja, mais le gate fee-aware n'est pas encore isole.
- `RISK`: `loss_budgeter/` et `exposure_budgeter/` existent deja; les breakers/position wrappers du catalogue sont des cibles de cablage et de calibration, pas des inventions hors-sol.
- `REGIME`: le repo consomme deja `regime` dans les engines, mais il n'a pas encore le calculateur/provider `regime_lite`.
- `EXECUTION` partiel:
  - `spread_guard` et `slippage_model` manquent
  - mais `execution_backbone/` et `execution_cost_meter/` existent deja
- `SHADOW gates`: les seuils vivent pour l'instant surtout dans le plan de phase, pas dans un script de gate dedie
- `SCALING`: ce sont d'abord des seuils de decision humaine et de gouvernance de capital
- `INFRA`: monitoring et reconciliation existent, mais pas encore les modules exacts de catalogue

### 4.2 Categories still absent from the repo (`future target`)

- `VENUE_ADAPTERS / BINANCE_SPOT / rate_limiter.py`

Le backlog `future target` ne porte plus sur des familles entières. Il reste surtout des sous-modules précis encore absents du repo courant.

---

## 5. Immediate consequences after `12`

Ce cross-check autorise maintenant le travail suivant, **en coherence avec `12_LOCAL_LAB_VS_VPS_SEPARATION.md`** :

1. creer un contrat partage `calibration_loader` en shared core
2. modeliser les artefacts de calibration par `threshold_id`
3. refuser tout fallback silencieux de seuil
4. après la première fermeture `EDGE`, preparer le branchement prioritaire sur les categories `partial` suivantes les plus proches du code reel:
   - `RISK`
   - `REGIME`
   - `INFRA`

Ce cross-check **n'autorise toujours pas** :

1. de figer ou coder la separation finale Local IA Lab / VPS
2. de creer `src/local_ai_lab`
3. de coder un control plane multi-VPS actif
4. de transformer une future vue flotte multi-VPS en orchestration ou failover automatique

---

## 6. Recommended next slice

Le prochain slice coherent est `W2`:

- nouveau module partage `src/calibration_loader/`
- contrats typés de calibration
- validation d'artefact
- acces par `threshold_id`
- aucun seuil hardcode en fallback

Le but de `W2` est de preparer la consommation des seuils dynamiques dans le shared core, avec ownership deja arbitre par `12_LOCAL_LAB_VS_VPS_SEPARATION.md`.

---

## 7. Update 2026-04-12

- `W2` is no longer hypothetical in the repo:
  - `src/calibration_loader/` exists
  - `calibration_loader` is now also registered in the canonical manifest/build-order/dependency registry
- `REGIME` has moved forward materially:
  - `src/regime_classifier/regime_lite.py` now resolves the documented `THR-RG01..04` seam through `calibration_loader`
  - the first bounded governed risk consumer exists via `src/risk_backbone/regime_lite_entry_gate.py`
  - an explicit governed `EXTREME -> safing recommendation` seam now exists via `src/risk_backbone/regime_lite_safing.py`
- consequence:
  - the remaining `REGIME` backlog is no longer "create the package"
  - it is now mostly operated/runtime wiring plus proof on real Shadow/Micro-live/VPS rails


---

## Source: docs/production_deployment_plan/13_CALIBRATION_METHODS.md

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


---

## Source: docs/production_deployment_plan/14_SHADOW_GATE_MATH.md

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


