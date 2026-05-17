# P0-B Addendum 1 - Engine Feature Wiring Proof

## Scope

This addendum proves how quant, microstructure, risk, cost, execution, ML-confidence, and regime features are actually consumed by Engines A/B/C/D.

Audit rules followed:
- no code modification
- no formula patching
- no engine/runtime/template changes
- no filename-only inference
- only static seams, runtime-input assemblers, provenance bundles, feature bridge artifacts, shared scoring/risk/execution rails, and tests

## Method

Checked in order:
1. direct engine imports and typed inputs
2. runtime input assemblers and provenance bundles
3. scoring runtime seams
4. risk runtime seams
5. execution routing / order-decider seams
6. regime / ML artifact consumers
7. feature bridge / provenance artifacts
8. engine and shared-layer tests

## Cross-engine findings

### Proven system-level seams

1. Engine A, C, and D have explicit upstream-governed microstructure provenance seams in [engine_input_provenance.py](/E:/claude%20%20v5.3/v53_trading_system/src/data_backbone/microstructure/engine_input_provenance.py).
2. Engines A/B/C/D all emit `ScoringCandidateInput` into the common scoring runtime:
   - [engine_a_scoring_candidate_builder.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_a/engine_a_scoring_candidate_builder.py)
   - [engine_b_runtime_support.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_b/engine_b_runtime_support.py)
   - [engine_c_runtime_support.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_c/engine_c_runtime_support.py)
   - [engine_d_runtime_support.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_d/engine_d_runtime_support.py)
3. Shared scoring physics formulas exist in [scoring_runtime_support.py](/E:/claude%20%20v5.3/v53_trading_system/src/scoring_backbone/scoring_runtime_support.py), but current A/B/C/D scoring-candidate builders do **not** populate `execution_fragility`, `market_toxicity`, `spread_regime_penalty`, or `participation_penalty` into `ScoringCandidateInput`.
4. Shared risk precheck hooks exist in [risk_runtime_runtime.py](/E:/claude%20%20v5.3/v53_trading_system/src/risk_backbone/risk_runtime_runtime.py), but this addendum does **not** prove that A/B/C/D candidate builders currently feed those micro-friction fields into the shared risk rail.
5. Shared execution routing does consume LOB and regime snapshots in:
   - [execution_routing_bridge.py](/E:/claude%20%20v5.3/v53_trading_system/src/execution_backbone/execution_routing_bridge.py)
   - [hybrid_router_equations.py](/E:/claude%20%20v5.3/v53_trading_system/src/execution_backbone/order_decider/hybrid_router_equations.py)
6. Regime and artifact-level consumers exist even when direct engine imports do not:
   - [regime_detector_runtime.py](/E:/claude%20%20v5.3/v53_trading_system/src/complete_enablers/regime_detector_runtime.py)
   - [regime_detector_dataset_builder.py](/E:/claude%20%20v5.3/v53_trading_system/src/local_replay_runtime/regime_detector_dataset_builder.py)
   - [historical_data_gateway.py](/E:/claude%20%20v5.3/v53_trading_system/src/local_replay_runtime/historical_data_gateway.py)
   - [state_feature_bridge.py](/E:/claude%20%20v5.3/v53_trading_system/src/cockpit/state_feature_bridge.py)

### Feature-bridge conclusion

`feature_bridge.json` is a provenance / audit seam, not an engine import seam. It proves that features can be materialized and lineage-locked, but it does not by itself prove engine-side arithmetic. Direct engine proof still had to come from typed runtime seams and engine tests.

### Shared-physics caveat

The repo contains valid shared scoring and risk formulas for:
- `execution_fragility`
- `market_toxicity`
- `spread_regime_penalty`
- `micro_friction`
- `execution_survivability`

But current A/B/C/D `ScoringCandidateInput` builders only proved:
- `raw_features`
- `expected_cost`
- `expected_ce`
- `projected_size`
- `projected_loss`
- `cluster_id`
- `corr_penalty`
- `risk_penalty`

Therefore the shared scoring-physics formulas exist, but are not counted here as engine-consumed unless the engine uses the same signals directly in its own runner logic.

## Engine A

### 1. Role

[engine_a/__init__.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_a/__init__.py) describes Engine A as `Premium Trend / Expansion`, high-conviction structured continuation with readable cost and explicit invalidation.

### 2. Direct formulas implemented in engine

- structure detection in [structure_detector_a.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_a/structure_detector_a.py)
- context validation in [context_validator_a.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_a/context_validator_a.py)
- conviction building in [conviction_builder_a.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_a/conviction_builder_a.py)
- cost feasibility in [cost_feasibility_a.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_a/cost_feasibility_a.py)
- forecast normalization / break-even in [signal_candidate_adapter.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_a/signal_candidate_adapter.py)

### 3. Direct microstructure features consumed

- `realized_kernel_vol_scale`: direct structure input. [structure_detector_a.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_a/structure_detector_a.py) uses it as `effective_trend_stability`.
- `realized_vol_current`: direct forecast volatility proxy in [signal_candidate_adapter.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_a/signal_candidate_adapter.py).
- `ofi_flow_score`: direct conviction input via the canonical provenance seam.
- `kyle_lambda_cost_uplift`: direct cost-stage uplift in [cost_feasibility_a.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_a/cost_feasibility_a.py).

### 4. Indirect scoring features consumed

- Engine A exports `fragility_score`, `toxicity_score`, and `micro_friction_score` into `raw_features` in [engine_a_scoring_candidate_builder.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_a/engine_a_scoring_candidate_builder.py).
- However, this addendum does **not** count the shared scoring-physics rail as proven active for Engine A because `ScoringCandidateInput.execution_fragility / market_toxicity / spread_regime_penalty` are not populated by the current builder.

### 5. Risk gate features consumed

- no separate Engine A-only micro-risk hook was needed to prove direct consumption because Engine A already consumes fragility / toxicity / spread-regime directly in its own conviction math
- shared risk hook existence is proven, but Engine A-specific population into that shared micro-friction rail is not proven in this addendum

### 6. Cost gate features consumed

- `expected_cost`
- `expected_ce`
- `ce_min`
- `kyle_lambda_cost_uplift`
- break-even conditioning and no-trade reason codes

### 7. Execution gate features consumed

Proven only on the shared downstream rail:
- `spread_bps`
- `order_book_imbalance`
- `microprice_pressure`
- `aggressive_trade_imbalance`
- `market_toxicity_score`
- `regime_transition_risk`
- `regime_stability_score`
- `expected_duration_bucket`

These are not direct Engine A imports, but they are valid VPS non-HFT downstream execution gates.

### 8. ML confidence features consumed

Generic ML score modulation exists through [ml_scoring_soft_penalty_hook.py](/E:/claude%20%20v5.3/v53_trading_system/src/complete_enablers/ml_scoring_soft_penalty_hook.py), but Engine A-specific `supplementary_refs` packaging was not proven in this addendum. Classification: `NOT_PROVEN_NEEDS_MANUAL_AUDIT`.

### 9. Regime context features consumed

Directly consumed:
- `regime_favorability`
- `pair_health`
- `data_freshness`
- `flow_coherence`

### 10. Feature bridge / artifact-consumed features

- Engine A has explicit provenance ownership in [engine_input_provenance.py](/E:/claude%20%20v5.3/v53_trading_system/src/data_backbone/microstructure/engine_input_provenance.py).
- Bridge audit surfaces are produced in [historical_data_gateway.py](/E:/claude%20%20v5.3/v53_trading_system/src/local_replay_runtime/historical_data_gateway.py) and read in [state_feature_bridge.py](/E:/claude%20%20v5.3/v53_trading_system/src/cockpit/state_feature_bridge.py).

### 11. Forecast / refusal / coordination seams

- forecast volatility proxy reason codes
- break-even conditioning
- downstream scoring and runtime-status annotations

### 12. Tests proving consumption

- [test_engine_input_provenance.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_data_backbone/microstructure/test_engine_input_provenance.py)
- [test_engine_a.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_engines/test_engine_a/test_engine_a.py)
- [test_signal_candidate_adapter_a.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_engines/test_engine_a/test_signal_candidate_adapter_a.py)
- [test_engine_a_runtime.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_engines/test_engine_a/test_engine_a_runtime.py)

### 13. Missing tests

- no engine-A-specific test was found proving packaged ML supplementary refs travel into the shared ML hook

### 14. NOT_CONSUMED features

- none in the direct Engine A seam among `ofi`, `realized kernel`, `realized vol`, `kyle uplift`

### 15. NOT_PROVEN_NEEDS_MANUAL_AUDIT

- per-engine ML supplementary refs
- direct use of walls / spoofing family inside Engine A itself

### 16. Strategic verdict

`HEALTHY_DIRECT_WIRING`

## Engine B

### 1. Role

[engine_b/__init__.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_b/__init__.py) describes Engine B as the `Mean Reversion Intraday Motor`.

### 2. Direct formulas implemented in engine

- local mean / z-score stage
- excess detection
- anti-breakout filter
- cost feasibility
- conviction and downstream forecast conditioning

### 3. Direct microstructure features consumed

- `vpin_current` in [excess_detector_b.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_b/excess_detector_b.py)
- `toxic_flow_correlation` in the same toxic-flow suppressor
- `microstructure_breakout_confirmation` in [anti_breakout_filter_b.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_b/anti_breakout_filter_b.py)

### 4. Indirect scoring features consumed

- breakout penalty is explicitly pushed into shared scoring penalties in [engine_b_runtime_support.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_b/engine_b_runtime_support.py)
- shared scoring-physics fields exist, but Engine B builder does not prove population of `ScoringCandidateInput.execution_fragility / market_toxicity / spread_regime_penalty`

### 5. Risk gate features consumed

- `execution_fragility`
- `market_toxicity`
- `spread_regime_penalty`

These are direct Engine B inputs inside local conviction math. Shared risk/scoring-physics carriage is not over-claimed here.

### 6. Cost gate features consumed

- `expected_cost`
- `expected_ce`
- break-even / emission gating via runtime forecast support

### 7. Execution gate features consumed

Shared execution-gate consumption is proven at the engine-agnostic downstream rail, same as Engine A.

### 8. ML confidence features consumed

Same status as Engine A: shared ML hook exists, but Engine B-specific `supplementary_refs` packaging is not proven.

### 9. Regime context features consumed

Directly consumed:
- `regime_favorability`
- `pair_health`
- `data_freshness`
- `flow_coherence`

### 10. Feature bridge / artifact-consumed features

- no dedicated Engine B microstructure provenance bundle was found
- direct Engine B proof comes from typed runner inputs and tests, not from a separate bridge seam

### 11. Forecast / refusal / coordination seams

- toxic-flow fade reason codes propagate through runtime forecast state
- breakout penalty is preserved into downstream scoring

### 12. Tests proving consumption

- [test_engine_b.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_engines/test_engine_b/test_engine_b.py)
- [test_engine_b_runtime.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_engines/test_engine_b/test_engine_b_runtime.py)
- [test_signal_candidate_adapter_b.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_engines/test_engine_b/test_signal_candidate_adapter_b.py)

### 13. Missing tests

- no dedicated Engine B test proving ML supplementary refs are attached to scoring candidates

### 14. NOT_CONSUMED features

- none for the core B toxic-flow seam (`vpin_current`, `toxic_flow_correlation`, `microstructure_breakout_confirmation`)

### 15. NOT_PROVEN_NEEDS_MANUAL_AUDIT

- per-engine ML supplementary refs
- direct wall/spoof feature imports inside Engine B

### 16. Strategic verdict

`HEALTHY_DIRECT_WIRING`

## Engine C

### 1. Role

[engine_c/__init__.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_c/__init__.py) describes Engine C as a `shadow-capable breakout continuation engine`.

### 2. Direct formulas implemented in engine

- breakout score
- context score
- continuation score
- fake-breakout risk
- continuation microstructure gate
- cost feasibility

### 3. Direct microstructure features consumed

Direct in [continuation_validator_c.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_c/continuation_validator_c.py):
- `cumulative_ofi`
- `queue_pressure`
- `vpin`
- `kyle_lambda`

Direct volatility / invalidation seam:
- `realized_vol_current`
- `realized_vol_at_break`

### 4. Indirect scoring features consumed

- Engine C emits block-score-based raw features into `ScoringCandidateInput` in [engine_c_runtime_support.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_c/engine_c_runtime_support.py)
- this addendum does not count shared scoring-physics micro-friction fields as active for Engine C because the current builder does not populate them

### 5. Risk gate features consumed

- common risk runtime exists downstream
- no evidence was found that Engine C bypasses the shared risk rail
- but Engine C-specific population into the shared micro-friction precheck fields is not proven

### 6. Cost gate features consumed

- `expected_cost`
- `expected_ce`
- `ce_min`
- break-even filter in runtime forecast support

### 7. Execution gate features consumed

Shared downstream execution routing is proven. This is valid non-HFT indirect consumption for LOB features not directly imported into Engine C.

### 8. ML confidence features consumed

ML modulation exists only generically at the scoring hook level. Engine C-specific packaged supplementary refs were not proven.

### 9. Regime context features consumed

Directly consumed:
- `regime_favorability`
- `pair_health`
- `data_freshness`
- `flow_coherence`

### 10. Feature bridge / artifact-consumed features

Artifact-level regime / LOB features are consumed outside the direct engine seam:
- [regime_detector_dataset_builder.py](/E:/claude%20%20v5.3/v53_trading_system/src/local_replay_runtime/regime_detector_dataset_builder.py) consumes `deceptive_liquidity_score`, `liquidity_thinning_score`, `spoof_like_suspicion_*`, `order_book_imbalance`, `microprice_pressure`
- [regime_detector_runtime.py](/E:/claude%20%20v5.3/v53_trading_system/src/complete_enablers/regime_detector_runtime.py) consumes artifact-declared `LobRegimeFeatureSnapshot` features

### 11. Forecast / refusal / coordination seams

[engine_c_runtime_forecast_support.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_c/engine_c_runtime_forecast_support.py) emits explicit conditioning codes for:
- microstructure missing
- microstructure contradictory
- microstructure confirmed
- microstructure required

### 12. Tests proving consumption

- [test_engine_input_provenance.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_data_backbone/microstructure/test_engine_input_provenance.py)
- [test_continuation_validator_c.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_engines/test_engine_c/test_continuation_validator_c.py)
- [test_engine_c.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_engines/test_engine_c/test_engine_c.py)
- [test_engine_c_runtime.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_engines/test_engine_c/test_engine_c_runtime.py)

### 13. Missing tests

- no dedicated end-to-end Engine C test proving regime-detector artifact outputs are injected back into Engine C as named inputs

### 14. NOT_CONSUMED features

- none for the core C continuation seam (`ofi`, `queue_pressure`, `vpin`, `kyle_lambda`, realized-vol seam)

### 15. NOT_PROVEN_NEEDS_MANUAL_AUDIT

- direct import of walls / spoofing family into Engine C
- per-engine ML supplementary refs

### 16. Strategic verdict

`HEALTHY_DIRECT_WIRING`

### Engine C toxic-flow check

Engine C is not implemented as a pure toxic-flow fade engine.

What is proven:
- Engine C is a breakout / continuation engine.
- Toxic-flow and microstructure are used as confirmation / veto context.
- `VPIN`, `OFI`, `queue_pressure`, and `kyle_lambda` can explicitly block or de-confirm the continuation.

Classification:
- `breakout/continuation engine protected by toxic-flow veto/context`
- not a standalone toxic-flow fade engine

## Engine D

### 1. Role

[engine_d/__init__.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_d/__init__.py) describes Engine D as a `shadow-capable re-entry engine`.

### 2. Direct formulas implemented in engine

- history score
- context score
- reformation score
- marginal value score
- historical linkage / first-episode coordination
- re-entry cost feasibility

### 3. Direct microstructure features consumed

Directly proven via runtime input assembly:
- `realized_vol_current`
- `realized_vol_post_close`

These are injected in [runtime_input_assembler_d.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_d/runtime_input_assembler_d.py) and used in [engine_d_runtime_support.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_d/engine_d_runtime_support.py) as the volatility proxy.

### 4. Indirect scoring features consumed

- Engine D emits a normal `ScoringCandidateInput` into the common scoring runtime.
- Shared scoring-physics formulas exist, but Engine D builder does not prove population of the dedicated scoring-physics fields.

### 5. Risk gate features consumed

- Engine D accepted candidates enter the same shared risk runtime as the other engines.
- no bypass of the common risk precheck rails was found
- engine-specific injection into shared micro-friction fields is not proven here

### 6. Cost gate features consumed

- `expected_cost`
- `expected_ce`
- additive break-even decision

### 7. Execution gate features consumed

Engine D has the strongest case for valid VPS-style indirect wiring:
- direct realized-kernel seam for volatility control
- shared downstream execution routing for LOB, toxicity, duration, and fee-aware routing

### 8. ML confidence features consumed

Generic shared hook exists, but Engine D-specific supplementary-ref packaging was not proven.

### 9. Regime context features consumed

Direct in [signal_math_d.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_d/signal_math_d.py):
- `regime_favorability`
- `pair_health`
- `data_freshness`
- `flow_coherence`

### 10. Feature bridge / artifact-consumed features

- realized-kernel records are governed upstream through the shared microstructure provenance seam
- artifact-level regime / LOB features remain shared, not direct Engine D imports

### 11. Forecast / refusal / coordination seams

- first-episode and reset-state coordination seams
- runtime-status annotations
- volatility-proxy reason codes

### 12. Tests proving consumption

- [test_engine_input_provenance.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_data_backbone/microstructure/test_engine_input_provenance.py)
- [test_runtime_input_assembler_d.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_engines/test_engine_d/test_runtime_input_assembler_d.py)
- [test_engine_d_runtime.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_engines/test_engine_d/test_engine_d_runtime.py)
- [test_invalidation_mapper_d.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_engines/test_engine_d/test_invalidation_mapper_d.py)

### 13. Missing tests

- no Engine D-specific test was found proving attachment of ML supplementary refs into the shared ML hook

### 14. NOT_CONSUMED features

- none for the realized-kernel seam

### 15. NOT_PROVEN_NEEDS_MANUAL_AUDIT

- direct import of OFI / VPIN / wall/spoof family into Engine D itself
- per-engine ML supplementary refs

### 16. Strategic verdict

`HEALTHY_INDIRECT_WIRING_FOR_VPS_NON_HFT`

### Engine D realized-kernel check

Verified as:
- `DIRECT_ENGINE_INPUT` at the runtime-assembler seam
- used as volatility proxy in forecast economics
- used by invalidation mapping
- not merely a test-only artifact

## Mandatory-family trace summary

### Proven direct engine-family consumers

- `Kyle lambda`: Engine A cost uplift, Engine C continuation veto
- `OFI`: Engine A flow seam, Engine C continuation seam
- `VPIN`: Engine B toxic-flow fade, Engine C continuation veto
- `queue_pressure`: Engine C continuation seam
- `realized kernel volatility`: Engine A structure/forecast, Engine D re-entry volatility seam, Engine C realized-vol seam
- `expected_cost / expected_ce / break-even`: A/B/C/D

### Proven shared indirect consumers

- `spread_bps`
- `order_book_imbalance`
- `microprice_pressure`
- `aggressive_trade_imbalance`
- `market_toxicity_score`
- `regime_transition_risk`
- `regime_stability_score`
- `expected_duration_bucket`

These are proven on the shared downstream execution / artifact rails, not on the current engine scoring-candidate physics fields.

### Proven artifact-level consumers

- `deceptive_liquidity_score`
- `liquidity_thinning_score`
- `spoof_like_suspicion_*`
- `real_wall_score_*` when included in regime-detector artifact feature names

### Not proven as current engine consumers

- `PIN`
- `Amihud`
- `Roll spread`
- `Corwin-Schultz`
- `Hawkes intensity`

## Final verdict

- Engine A: `HEALTHY_DIRECT_WIRING`
- Engine B: `HEALTHY_DIRECT_WIRING`
- Engine C: `HEALTHY_DIRECT_WIRING`
- Engine D: `HEALTHY_INDIRECT_WIRING_FOR_VPS_NON_HFT`

No engine met the hard-failure condition for `NOT_WIRED`.
