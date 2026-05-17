# Wave 4 External Evidence Summary

MemPalace check: performed earlier in this session. Project memory was not available in this shell. Source of truth for this pack is the current codebase plus the existing P0A/P0B audit docs and tests.

Scope: source-level evidence only for canonical microstructure estimators, LOB feature builders, regime feature carriers, and runtime consumers. This pack does not self-certify scientific correctness and does not approve any patch as final.

## Files scanned

Primary estimator sources:
- `src/data_backbone/microstructure/kyle_lambda.py`
- `src/data_backbone/microstructure/order_flow_imbalance.py`
- `src/data_backbone/microstructure/vpin.py`
- `src/data_backbone/microstructure/pin.py`
- `src/data_backbone/microstructure/amihud_illiquidity.py`
- `src/data_backbone/microstructure/roll_spread.py`
- `src/data_backbone/microstructure/corwin_schultz_spread.py`
- `src/data_backbone/microstructure/hawkes_intensity.py`
- `src/data_backbone/microstructure/realized_kernel_vol.py`
- `src/data_backbone/microstructure/queue_pressure.py`
- `src/data_backbone/microstructure/walls_and_spoofing.py`
- `src/data_backbone/microstructure/lob_regime_features.py`
- `src/data_backbone/microstructure/feature_registry.py`
- `src/data_backbone/microstructure/engine_input_provenance.py`

Primary consumers:
- `src/engines/engine_a/conviction_builder_a.py`
- `src/engines/engine_a/structure_detector_a.py`
- `src/engines/engine_a/signal_candidate_adapter.py`
- `src/engines/engine_a/cost_feasibility_a.py`
- `src/engines/engine_a/engine_a_scoring_candidate_builder.py`
- `src/engines/engine_b/excess_detector_b.py`
- `src/engines/engine_b/conviction_builder_b.py`
- `src/engines/engine_b/engine_b_runner.py`
- `src/engines/engine_c/continuation_validator_c.py`
- `src/engines/engine_c/engine_c_runtime_support.py`
- `src/engines/engine_c/engine_c_runtime_forecast_support.py`
- `src/engines/engine_c/invalidation_mapper_c.py`
- `src/engines/engine_d/runtime_input_assembler_d.py`
- `src/engines/engine_d/engine_d_runtime_support.py`
- `src/engines/engine_d/signal_math_d.py`
- `src/complete_enablers/regime_detector_runtime.py`
- `src/execution_backbone/order_decider/hybrid_router.py`
- `src/execution_backbone/order_decider/hybrid_router_equations.py`
- `src/cockpit/state_feature_bridge.py`
- `src/cockpit/state_data_quality.py`
- `src/cockpit/templates/partials/_feature_bridge.html`
- `src/local_replay_runtime/regime_detector_dataset_builder.py`

Primary tests:
- `tests/test_data_backbone/microstructure/*`
- `tests/test_microstructure/test_paper_repro.py`
- `tests/test_complete_enablers/test_regime_detector_runtime.py`
- `tests/test_engines/test_engine_c/*`
- `tests/test_engines/test_engine_d/*`
- `tests/test_execution_backbone/test_execution_runtime.py`
- `tests/test_execution_backbone/test_gatekeeper.py`
- `tests/test_execution_backbone/test_spread_guard.py`
- `tests/cockpit/test_state_feature_bridge.py`
- `tests/cockpit/test_state_data_quality.py`

## Evidence status by family

| Family | Status | Notes |
| --- | --- | --- |
| Kyle lambda | `EVIDENCE_EXTRACTED`, `ENGINE_CONSUMED`, `COST_GATE_CONSUMED`, `TEST_COVERED` | Canonical rolling OLS slope is proven; Engine C and Engine A cost uplift consumers are proven. |
| OFI | `EVIDENCE_EXTRACTED`, `ENGINE_CONSUMED`, `REGIME_CONTEXT_INPUT`, `TEST_COVERED` | Cont-Kukanov event contribution is proven; Engine C and LOB regime consumers are proven. |
| VPIN | `EVIDENCE_EXTRACTED`, `ENGINE_CONSUMED`, `TEST_COVERED` | Equal-volume bucket construction is proven; Engine B and Engine C consumers are proven. |
| PIN | `EVIDENCE_EXTRACTED`, `FUTURE_RESERVED`, `TEST_COVERED` | Formula from already-estimated parameters is present; runtime consumer beyond registry was not proven. |
| Amihud | `EVIDENCE_EXTRACTED`, `NOT_PROVEN_NEEDS_EXTERNAL_AUDIT`, `TEST_COVERED` | Canonical estimator exists; direct governed runtime consumer was not proven in this pass. |
| Roll spread | `EVIDENCE_EXTRACTED`, `NOT_PROVEN_NEEDS_EXTERNAL_AUDIT`, `TEST_COVERED` | Canonical estimator exists; feature registry points to execution cost meter, but direct runtime consumer was not proven. |
| Corwin-Schultz | `EVIDENCE_EXTRACTED`, `FUTURE_RESERVED`, `TEST_COVERED` | Estimator exists; only registry/interface/meta references were found. |
| Hawkes intensity | `EVIDENCE_EXTRACTED`, `FUTURE_RESERVED`, `TEST_COVERED` | Canonical intensity formula exists; registry claims Engine C/meta-learning intent, but direct runtime use was not proven. |
| Realized kernel vol | `EVIDENCE_EXTRACTED`, `ENGINE_CONSUMED`, `TEST_COVERED` | Engine A, Engine C, and Engine D volatility-seam consumers are proven. |
| Queue pressure | `EVIDENCE_EXTRACTED`, `ENGINE_CONSUMED`, `TEST_COVERED` | Top-k depth imbalance seam is proven; Engine C continuation consumer is proven. |
| Walls/spoofing | `EVIDENCE_EXTRACTED`, `REGIME_CONTEXT_INPUT`, `TEST_COVERED` | Runtime LOB regime feature bundle consumes wall/spoofing snapshot outputs. |
| LOB regime features | `EVIDENCE_EXTRACTED`, `REGIME_CONTEXT_INPUT`, `EXECUTION_GATE_CONSUMED`, `COCKPIT_ONLY`, `TEST_COVERED` | Runtime regime detector and hybrid router consumers are proven; cockpit is artifact/display only. |

## Core findings

1. Canonical microstructure estimators consistently expose `computed_at_ns`, `method_version_hash`, and `input_data_hash`, and most enforce `computed_at_ns >= latest_input_timestamp`.
2. Canonical estimators generally reject future data or structurally avoid it by filtering to windows ending at `computed_at_ns`; LOB regime features explicitly reject future events.
3. Engine C is the strongest direct microstructure consumer:
   - continuation/fake-breakout protection via OFI, queue pressure, VPIN, and Kyle lambda
   - realized-volatility fallback via realized-kernel carriers
4. Engine D is not an A/B-style shared-scoring physics carrier. It uses realized-kernel context in re-entry / first-episode / anti-revenge seams.
5. LOB regime runtime outputs stay within the non-directional allowed set:
   - `regime_transition_risk`
   - `regime_stability_score`
   - `market_toxicity_score`
   - `expected_duration_bucket`
6. Directional labels were found in `src/local_replay_runtime/regime_detector_dataset_builder.py`, but only on the dataset-building / training seam, not in the governed runtime regime output.

## Partiality / external-audit boundaries

- `PIN`, `Amihud`, `Roll`, `Corwin-Schultz`, and `Hawkes` have implementation evidence, but not all have direct governed runtime consumers proven in this pass.
- Feature registry intent is not treated as runtime proof by itself.
- Cockpit feature-bridge visibility does not prove runtime consumption.
- The pack does not certify scientific calibration or empirical realism; it only packages implementation and consumer evidence.

## Output files

- `WAVE4_KYLE_LAMBDA_SOURCE_EVIDENCE.md`
- `WAVE4_OFI_SOURCE_EVIDENCE.md`
- `WAVE4_VPIN_PIN_TOXICITY_SOURCE_EVIDENCE.md`
- `WAVE4_AMIHUD_ROLL_CORWIN_HAWKES_SOURCE_EVIDENCE.md`
- `WAVE4_REALIZED_KERNEL_VOL_SOURCE_EVIDENCE.md`
- `WAVE4_QUEUE_MICROPRICE_IMBALANCE_SOURCE_EVIDENCE.md`
- `WAVE4_WALLS_SPOOFING_SOURCE_EVIDENCE.md`
- `WAVE4_LOB_REGIME_FEATURES_SOURCE_EVIDENCE.md`
- `WAVE4_MICROSTRUCTURE_ANTI_LEAKAGE_EVIDENCE.md`
- `WAVE4_MICROSTRUCTURE_CONSUMER_MAP_EVIDENCE.md`
- `WAVE4_ENGINE_C_D_SEMANTIC_MAPPING_EVIDENCE.md`
- `WAVE4_COCKPIT_FALSE_GREEN_MICROSTRUCTURE_EVIDENCE.md`
- `WAVE4_SIDE_HALAL_MICROSTRUCTURE_SAFETY_EVIDENCE.md`
- `WAVE4_TEST_COVERAGE_EVIDENCE.md`
- `WAVE4_EXTERNAL_AUDIT_QUESTIONS.md`
