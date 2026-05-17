# P0-B Addendum 2 - Scoring / Risk / ML / Regime Carriage Proof

## Scope
- Audit only.
- No production code changed.
- No engine, runtime, cockpit, or formula implementation changed.

## Sources inspected
- `src/engines/engine_a/*`
- `src/engines/engine_b/*`
- `src/engines/engine_c/*`
- `src/engines/engine_d/*`
- `src/scoring_backbone/*`
- `src/risk_backbone/*`
- `src/execution_backbone/*`
- `src/complete_enablers/*`
- `src/protocols/execution_opportunity_bridge.py`
- `src/cockpit/state_feature_bridge.py`
- `tests/test_scoring_backbone/*`
- `tests/test_risk_backbone/*`
- `tests/test_execution_backbone/*`
- `tests/test_complete_enablers/*`
- `tests/test_engines/*`

## High-level verdict
The governed rails are not uniformly symmetric.

What is proven:
- Shared scoring schema supports `execution_fragility`, `market_toxicity`, `spread_regime_penalty`, `participation_penalty`, and `supplementary_refs`.
- Shared risk schema supports the same micro-friction fields plus info-stress fields.
- Shared execution routing consumes live microstructure and regime context and is fail-closed on stale or low-coverage routing snapshots.
- ML direct side override remains blocked.
- No hidden side override, no hidden short route, and no leverage route were proven on the governed VPS rail.

What is not proven as fully carried:
- A/B/C/D scoring candidate builders do not populate the shared scoring-physics fields directly.
- A/B/C/D risk candidate builders do not populate the shared risk micro-friction or info-stress fields.
- A/B/C/D do not package `supplementary_refs` into `ScoringCandidateInput`.
- Regime artifact outputs are proven in execution routing, but not uniformly reinjected into scoring and risk rails.

## Main findings

### 1. Shared scoring-physics schema exists, but direct population is absent
`ScoringCandidateInput` in `src/scoring_backbone/scoring_runtime_support.py` contains:
- `supplementary_refs`
- `execution_fragility`
- `market_toxicity`
- `spread_regime_penalty`
- `participation_penalty`

`build_physics_projection(...)` and `build_scoring_soft_penalty_hook_input(...)` consume those fields.

But current engine candidate builders:
- `engine_a_scoring_candidate_builder._build_scoring_candidate`
- `engine_b_runtime_support._build_scoring_candidate`
- `engine_c_runtime_support.build_scoring_candidate`
- `engine_d_runtime_support.build_scoring_candidate`

do not set those fields.

Result:
- shared scoring physics is present in schema and runtime
- direct carriage from engines into those exact fields is absent
- default zeros create a real silent no-op risk if someone assumes those fields are live-populated

### 2. Engine A/B compensate partly via derived raw features
Engine A and Engine B compute local physics and then carry derived quantities into shared scoring as raw features:
- `fragility_score`
- `toxicity_score`
- `micro_friction_score`

This is proven in:
- `src/engines/engine_a/conviction_builder_a.py`
- `src/engines/engine_a/engine_a_scoring_candidate_builder.py`
- `src/engines/engine_b/conviction_builder_b.py`
- `src/engines/engine_b/engine_b_runtime_support.py`

So A/B are not unwired.
They use local micro-friction math first, then pass derived physics into the shared scoring rail.

### 3. Engine C/D do not show the same derived shared-scoring compensation
Engine C and Engine D populate shared scoring mostly from `engine_output.block_scores` and feature-weight maps, but this audit did not prove equivalent carriage of:
- `fragility_score`
- `toxicity_score`
- `micro_friction_score`
- `execution_fragility`
- `market_toxicity`
- `spread_regime_penalty`
- `participation_penalty`

into the shared scoring candidate.

Result:
- Engine C and D remain partially carried for shared micro-friction scoring physics
- their local math and downstream execution context are still real
- but the shared scoring-physics rail is not fully fed

### 4. Shared risk hooks exist, but engine risk candidates do not feed them
`RiskCandidate` in `src/risk_backbone/risk_runtime_models.py` contains:
- `execution_fragility`
- `market_toxicity`
- `spread_regime_penalty`
- `participation_penalty`
- `spread_bps`
- `reference_spread_bps`
- `depth_ratio`
- `order_cancellation_rate`
- `taker_imbalance`
- `micro_vol_divergence`

Risk runtime consumes them via:
- `_run_micro_friction_precheck_hook(...)`
- `_run_info_stress_precheck_hook(...)`
- `_evaluate_candidate_physics(...)`

But current engine risk builders:
- `EngineARuntime._evaluate_risk`
- `EngineBScoringState.build_risk_candidate`
- `engine_c_runtime_support.evaluate_risk`
- `engine_d_runtime_support.evaluate_risk`

only pass:
- pair
- engine_id
- size
- planned_loss
- pair_beta

They do not pass the micro-friction or info-stress fields.

Operational consequence:
- risk micro-friction physics degrade to default nominal values
- risk info-stress hooks see `None` for spread/depth/cancel/taker/micro-vol fields
- the risk rail is effectively fail-open or neutral on missing microstructure carriage

### 5. Execution bridge is materially wired and non-directional
`ExecutionRoutingBridge.project(...)` consumes:
- `spread_bps`
- `order_book_imbalance`
- `microprice_pressure`
- `aggressive_trade_imbalance`
- `market_toxicity_score`
- `regime_transition_risk`
- `regime_stability_score`
- `expected_duration_bucket`
- maker/taker fees

It rejects on:
- `stale_snapshot`
- `low_coverage`

`hybrid_router_equations.py` proves these features affect:
- fill probability
- adverse selection
- taker slippage
- maker EV
- taker EV
- latency staleness

The execution layer does not create side.
It normalizes or reuses a side already decided upstream.

### 6. ML supplementary refs are implemented generically but not proven on live engine carriage
The shared ML hook path is real:
- `ScoringSoftPenaltyLayerInput.supplementary_refs`
- `ml_scoring_soft_penalty_hook`
- `MlConfidenceEnabler.score_candidate_from_supplementary_refs(...)`

But A/B/C/D scoring candidate builders do not populate `supplementary_refs`.

Result:
- generic ML confidence hook exists and is tested
- live per-engine transport of supplementary refs into the shared scoring hook is not proven
- missing refs degrade safely to neutral/missing/invalid states
- direct ML confidence override remains blocked by default

### 7. Regime artifact reinjection is real in execution, partial elsewhere
`RegimeDetectorRuntime` emits only:
- `regime_transition_risk`
- `regime_stability_score`
- `market_toxicity_score`
- `expected_duration_bucket`

No directional label was proven.

Those outputs are proven consumed in:
- `execution_backbone/execution_routing_bridge.py`
- `execution_backbone/order_decider/hybrid_router.py`
- `execution_backbone/order_decider/hybrid_router_equations.py`

They are also visible in cockpit and artifacts:
- `state_feature_bridge.py`
- `feature_bridge.json`

But this audit did not prove uniform reinjection of regime artifact outputs back into:
- shared scoring candidate fields
- shared risk regime precheck payload
- per-engine ML supplementary ref packaging

## Engine verdicts
- Engine A: `LOCAL_MATH_ONLY_BUT_ACCEPTABLE`
- Engine B: `LOCAL_MATH_ONLY_BUT_ACCEPTABLE`
- Engine C: `PARTIAL_CARRIAGE`
- Engine D: `PARTIAL_CARRIAGE`

## Confirmed blockers
- Shared scoring-physics fields exist but are not populated by A/B/C/D candidate builders.
- Shared risk micro-friction/info-stress fields exist but are not populated by A/B/C/D risk builders.
- `supplementary_refs` live carriage into the ML scoring hook is not proven for A/B/C/D.
- Regime artifact context is decisional in execution but not uniformly carried into scoring/risk rails.
- Default zeros and empty refs create a real false-green / silent no-op risk if dashboards or audits assume those rails are active.

## Not confirmed as blockers
- Lack of direct engine L2 imports by itself is not a blocker under VPS non-HFT doctrine.
- Execution bridge microstructure usage is real and sufficient as a downstream non-directional rail.
- No active hidden short/leverage/funding-only route was proven.

## Validation summary
- `python -m compileall src/scoring_backbone src/risk_backbone src/execution_backbone src/complete_enablers src/engines` -> PASS
- `tests/test_complete_enablers` -> PASS
- `tests/test_engines` -> PASS
- `tests/test_scoring_backbone` -> PARTIAL: fee-aware-edge tests hit local `build/` permission errors
- `tests/test_risk_backbone` -> PARTIAL: temp/build permission issues during circuit-breaker and cleanup paths
- `tests/test_execution_backbone` -> PARTIAL: several tests write under `build/` and failed with permission errors
