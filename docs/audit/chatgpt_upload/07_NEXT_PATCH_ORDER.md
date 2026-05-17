# 07 NEXT PATCH ORDER

## P0-A: Orphan resolution import graph
Goal:
- resolve the dashboard ownership/import graph for the mandatory P0 domains

Must include:
- `src/interface_contracts/*`
- `src/execution_backbone/*`
- `src/venue_adapters/*`
- `src/secrets_manager/*`
- `src/calibration_methods/*`
- `src/local_replay_runtime/*`
- `src/backtest_artifact_import/*`
- `src/engines/*`
- `src/data_backbone/microstructure/*`
- `scripts/run_shadow_vps_service.py`

Acceptance:
- no mandatory domain remains `owner_page_candidate = unknown`
- every mandatory domain gets a cockpit owner or explicit non-cockpit justification

## P0-B: Formula ledger cleanup
Goal:
- replace raw `CODE_FORMULA_FOUND` overreach with human-safe source classes

Must do:
- split into:
  - `REAL_QUANT_FORMULA`
  - `OPERATIONAL_DIAGNOSTIC`
  - `THRESHOLD_CONSTANT`
  - `PYDANTIC_FIELD`
  - `STATUS_FLAG`
  - `REPORT_VALUE`
  - `TEXT_OR_LIST`
  - `FALSE_POSITIVE`
- remove zero-default / `Field(...)` / text-builder pollution from formula review surfaces

Acceptance:
- CE/exec-rate placeholders no longer look like live quant formulas

## P0-C: Backtest source-mapped display
Goal:
- make Backtest the real owner of replay/calibration/reproducibility source proof

Must add:
- source-mapped replay aggregates
- parity metrics
- artifact manifest / release candidate / proof summary refs
- calibration proof bank visibility
- formula-source labels

Acceptance:
- Backtest page can answer where each replay/calibration metric comes from

## P0-D: VPS/Shadow control proof ownership
Goal:
- make VPS the canonical owner of service and queue proof, Shadow the owner of readiness

Must do:
- `VPS` owns:
  - service liveness
  - queue consumption proof
  - heartbeat freshness
  - disk/log growth
  - command queue status
- `Shadow` owns:
  - warmup
  - blockers
  - eligible_to_trade
  - shadow verdict

Acceptance:
- no full queue/service tables remain duplicated outside `VPS`

## P1-E: Overview duplication collapse
Goal:
- keep Overview compact and honest

Must remove:
- deep calibration tables
- deep lab review
- deep model risk
- deep refusal journal
- deep feature bridge

Acceptance:
- Overview becomes badge-only for shared cross-page status

## P1-F: Trading false-green cleanup
Goal:
- make Trading stop presenting placeholders as evidence

Must do:
- separate real CE/exec formulas from defaults
- keep feature lineage warnings on Trading owner surface
- remove non-owner calibration depth

Acceptance:
- Trading does not imply profitable/valid economics from placeholder values

## P1-G: IA Lab model-risk/refusal source status
Goal:
- make IA Lab explicit about what is persisted vs placeholder

Must do:
- show `source_status` clearly for:
  - `model_risk`
  - `refusal_journal`
- keep detailed refusal semantics on the correct owner surface

Acceptance:
- IA Lab no longer looks "complete" when the source is still `NOT_YET_PERSISTED`

## Execution order summary
1. `P0-A` Orphan resolution import graph
2. `P0-B` Formula ledger cleanup
3. `P0-C` Backtest source-mapped display
4. `P0-D` VPS/Shadow control proof ownership
5. `P1-E` Overview duplication collapse
6. `P1-F` Trading false-green cleanup
7. `P1-G` IA Lab model-risk/refusal source status
