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
