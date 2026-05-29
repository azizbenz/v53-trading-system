# Run #1 + Run #2 — commandes exactes et procédure d'audit

**Date** : 2026-05-28
**Sources de raw data** : `L:\ordrebookpart1` + `J:\ordre book suite` + `L:\trades` + `L:\klines`
**Metadata** : `K:\v5.3 backtest\metadata\bybit\spot`

---

## Run #1 — Train ML (IA Lab) — LANCÉ 2026-05-28 21:25

**Background ID** : `bt0y2313j`

**Commande** :

```powershell
$env:PYTHONPATH = "E:\claude  v5.3\v53_trading_system\src"
python "E:\claude  v5.3\v53_trading_system\scripts\run_strategy_ladder_data_factory.py" `
  --run-id "lab_train-2026-05-28-5pairs-186j" `
  --pairs ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT `
  --timeframes 15m `
  --start 2025-04-29 `
  --end 2025-10-31 `
  --raw-root "L:\ordrebookpart1" `
  --raw-root "J:\ordre book suite" `
  --raw-root "L:\trades" `
  --raw-root "L:\klines" `
  --historical-metadata-root "K:\v5.3 backtest\metadata\bybit\spot" `
  --output-root "K:\output lab\runs\lab_train-2026-05-28-5pairs-186j\phase_a2_data_factory" `
  --feature-names "close_return,high_low_range,volume,spread_bps,slippage_bps,book_depth_levels,break_even_bps,fragility_score,false_breakout_context,vpin,cumulative_ofi,queue_pressure,kyle_lambda,realized_vol_current,realized_vol_at_break,latency_penalty_bps,micro_edge_exit_governor_observed,micro_edge_entry_timing_observed,history_score,marginal_value_score,reentry_lateness,concentration_headroom" `
  --storage-format jsonl-gz `
  --cache-base "K:\cache\a2\train_5pairs_186j"
```

**Window** : 2025-04-29 → 2025-10-31 (186 jours, pré-embargo)
**Output** : `K:\output lab\runs\lab_train-2026-05-28-5pairs-186j\phase_a2_data_factory\`
**Cache** : `K:\cache\a2\train_5pairs_186j\` (populé automatiquement)

**Estimation** : 3-6h wall time. K: a 303 GB libres, on est bon.

---

## Run #2 — Backtest OOS — À LANCER APRÈS RUN #1 + TRAINING

**Window** : 2025-11-15 → 2026-04-12 (149 jours, post-embargo 14j)
**Embargo** : 2025-11-01 → 2025-11-14 (zone interdite, ni train ni backtest)

**Commande** :

```powershell
$env:PYTHONPATH = "E:\claude  v5.3\v53_trading_system\src"
python "E:\claude  v5.3\v53_trading_system\scripts\run_strategy_ladder_data_factory.py" `
  --run-id "strategy_ladder_workflow-backtest-oos-2026-05-28-5pairs" `
  --pairs ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT `
  --timeframes 15m `
  --start 2025-11-15 `
  --end 2026-04-12 `
  --raw-root "L:\ordrebookpart1" `
  --raw-root "J:\ordre book suite" `
  --raw-root "L:\trades" `
  --raw-root "L:\klines" `
  --historical-metadata-root "K:\v5.3 backtest\metadata\bybit\spot" `
  --output-root "K:\output backtest\runs\strategy_ladder_workflow-backtest-oos-2026-05-28-5pairs\phase_a2_data_factory" `
  --feature-names "close_return,high_low_range,volume,spread_bps,slippage_bps,book_depth_levels,break_even_bps,fragility_score,false_breakout_context,vpin,cumulative_ofi,queue_pressure,kyle_lambda,realized_vol_current,realized_vol_at_break,latency_penalty_bps,micro_edge_exit_governor_observed,micro_edge_entry_timing_observed,history_score,marginal_value_score,reentry_lateness,concentration_headroom" `
  --storage-format jsonl-gz `
  --cache-base "K:\cache\a2\backtest_5pairs_149j"
```

**Output** : `K:\output backtest\runs\strategy_ladder_workflow-backtest-oos-2026-05-28-5pairs\phase_a2_data_factory\`
**Cache** : `K:\cache\a2\backtest_5pairs_149j\` (séparé du train, hash différent)

**Estimation** : 2.5-4h wall (149j vs 186j = ~80% du temps de Run #1).

---

## Audit checklist post-A2 (à exécuter à la fin de chaque run)

Exécute ce snippet pour valider AUTOMATIQUEMENT si le run est prêt pour downstream (B_ML training ou B1/B2 backtest) :

```powershell
python "E:\claude  v5.3\v53_trading_system\scripts\audit_a2_run.py" `
  --run-dir "K:\output lab\runs\lab_train-2026-05-28-5pairs-186j\phase_a2_data_factory"
```

(Le script `audit_a2_run.py` est livré dans la même session — voir fichier séparé.)

---

## Procédure de monitoring durant le run

Voir `scripts/monitor_a2_run.py` (livré même session). Affiche stage actuel + counters + ETA + K: free space en temps réel.

```powershell
python "E:\claude  v5.3\v53_trading_system\scripts\monitor_a2_run.py" `
  --run-dir "K:\output lab\runs\lab_train-2026-05-28-5pairs-186j\phase_a2_data_factory" `
  --poll-interval 60
```

---

## Workflow opérationnel cible

```
RUN #1 LANCÉ → ETA ~3-6h
   ↓
audit_a2_run.py → check anti-leakage GREEN + 0 rows_rejected
   ↓
python scripts/run_strategy_ladder_ml_lab_handoff.py
   --from-a2 K:\output lab\runs\lab_train-2026-05-28-5pairs-186j
   ↓ ~20-40 min training
artifact .lgb produit sous K:\output lab\artifacts\
   ↓
LAUNCH RUN #2 (backtest) sur K:
   ↓
audit_a2_run.py → check anti-leakage GREEN
   ↓
ITERATE B1+B2+B_ML avec le modèle .lgb + cache A2 → 5-15 min par itération
   ↓
P0-B ENGINES CALIBRATION (A.1 + A.2)
   ↓
"plus de proxies" : expected_edge + slippage calibrés
   ↓
VALIDATION FINALE : "de quoi est capable v5.3"
```
