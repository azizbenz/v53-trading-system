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

#### THR-E05 â€" EV^net floor explicite (economics gate)

```yaml
threshold_id: THR-E05
description: Floor explicite sur EV^net pour les gates economics partagÃ©s
source_module: src/scoring_backbone/ev_net_floor_thresholds.py + scoring_backbone/break_even_filter.py
calibration_source: backtest (EV net distribution + shadow drift review)
calibration_artifact: config/calibration/v1/ev_net_floor.yml
default_value: 0.0
ic95_lower: pair-specific
ic95_upper: pair-specific
n_observations_min: 200
recalibration_freq: quarterly
human_signature_required: true
notes: |
  Introduit pour supprimer la collision sÃ©mantique avec THR-W01. THR-W01 reste
  exclusivement rÃ©servÃ© au runtime risk / drawdown warning. THR-E05 porte la
  sÃ©mantique economics "EV^net floor" dans les docs 19/20/21/22 et dans les
  seams partagÃ©s de gating economics.
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
| **THR-E05** | **EV^net floor (economics gate)** | **0.0** | **backtest/shadow review** | **quarterly** | **âœ”** |
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

**Total : 38 seuils dynamiques rÃ©els** identifiÃ©s, dont **28 nÃ©cessitent une signature humaine** pour usage production.

> **Audit 2026-04-13** : +5 entrÃ©es (THR-E03, THR-E04, THR-W01, THR-W02, THR-S06) dÃ©couvertes par audit code vs plan. THR-X03 source_module corrigÃ© (execution_backbone, pas venue_adapters).
> **Audit 2026-04-20** : +1 entrÃ©e (THR-E05) pour dÃ©sambiguÃ¯ser le floor economics EV^net des seuils risk runtime. THR-W01 reste strictement rÃ©servÃ© au drawdown warning.

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
