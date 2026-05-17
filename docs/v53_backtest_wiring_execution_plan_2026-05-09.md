# V5.3 Backtest Wiring Execution Plan

Generated on 2026-05-09 from the current `src/` tree and the audit in `docs/v53_backtest_wiring_audit_2026-05-09.md`.

## Objective

Bring the V5.3 backtest path closer to the real governed stack by making `LOCAL_REPLAY` consume as much of the canonical shared core as possible:

- same contracts
- same decision logic
- same scoring/risk/portfolio semantics
- stronger execution realism
- artifact outputs still importable through the governed rail

This plan does **not** create a separate backtest architecture.

## Non-Negotiable Constraints

- one shared V5.3 codebase
- no new profile beyond `LIGHT` and `COMPLETE`
- use `runtime_mode=LOCAL_REPLAY`
- no bypass of Shadow / Micro-live / Live promotion gates
- no implicit second runtime for replay
- outputs must stay audit-ready and typed
- Build-14 stays additive, not a replacement for the canonical builds

## Current Truth

### Already on the effective rail

- `interface_contracts`
- `calibration_loader`
- `data_backbone`
- `regime_classifier`
- `execution_backbone`
- `sharia_compliance`
- `risk_backbone`
- `scoring_backbone`
- `engine_a`, `engine_b`, `engine_c`, `engine_d`
- `portfolio`
- `meta`
- `calibration_methods`
- `meta_learning`
- `local_replay_runtime`
- `backtest_artifact_import`
- `monitoring`
- `cockpit`

### Not effectively on the rail

- `complete_enablers`
- `protocols`
- `venue_adapters`
- `alerting`
- `secrets_manager`
- `ui`
- architecture foundation modules that should govern the rail but do not change replay behavior directly

### Main realism gap

The backtest rail still relies on `local_replay_runtime/shadow_execution_simulator.py` as a replay-specific execution path. That gives bounded realism, but not the strongest possible convergence with the canonical governed runtime path.

## Delivery Strategy

The migration should be done in **7 lots**. Each lot must land with tests and with explicit parity/proof output.

---

## Lot 0 - Architecture Truth Freeze

### Goal

Stop the drift between the declared architecture and the real backtest rail.

### Target files

- `src/manifest_registry/dependency_registry.py`
- `src/manifest_registry/module_inventory.py`
- `src/dag_validator/*`
- `src/local_replay_runtime/strategy_ladder_runner.py`
- `src/local_replay_runtime/strategy_ladder_detailed_replay.py`
- `src/local_replay_runtime/strategy_ladder_ml_lab_handoff.py`
- `src/cockpit/backtest_preflight.py`

### Work

- decide whether to:
  1. update the manifest DAG to reflect the current rail, or
  2. refactor the current code back under the declared DAG
- remove ambiguity before deeper rewiring
- add an explicit architectural note for the allowed `LOCAL_REPLAY` rail

### Risk

- medium
- if skipped, every later lot will keep conflicting architecture truth

### Done criteria

- DAG check passes against intended architecture
- no undocumented cross-module replay edge remains
- replay rail is explicitly documented as canonical

### Verification

- `dag_validator`
- contract scan for module edges
- targeted tests for current replay imports

---

## Lot 1 - Replay Execution Interface Extraction

### Goal

Insert a canonical seam between replay orchestration and execution realism, so `LOCAL_REPLAY` stops depending directly on one monolithic simulator.

### Target files

- `src/local_replay_runtime/shadow_execution_simulator.py`
- `src/local_replay_runtime/strategy_ladder_detailed_replay.py`
- `src/local_replay_runtime/replay_orchestrator_execution.py`
- `src/local_replay_runtime/contracts.py`
- `src/local_replay_runtime/enums.py`
- `src/interface_contracts/*execution*`
- `src/interface_contracts/artifact_contracts*.py`

### Work

- define a replay-execution interface with typed inputs/outputs
- separate:
  - opportunity preparation
  - execution realism evaluation
  - parity diagnostics
  - artifact serialization
- keep the current simulator as an implementation behind that interface first

### Risk

- medium
- interface mistakes can ripple into artifacts and reports

### Done criteria

- `strategy_ladder_detailed_replay.py` depends on an execution interface, not hard-coded simulator internals
- replay outputs are unchanged or intentionally versioned
- no operator surface regression in `cockpit`

### Verification

- replay artifact snapshot tests
- proof matrix regression
- typed model validation

---

## Lot 2 - Canonical Execution Backbone Convergence

### Goal

Reuse more of the real `execution_backbone` logic inside replay for cost/fill/slippage/spread realism.

### Target files

- `src/execution_backbone/execution_runtime.py`
- `src/execution_backbone/execution_runtime_support.py`
- `src/execution_backbone/execution_runtime_models.py`
- `src/execution_backbone/slippage_model.py`
- `src/execution_backbone/spread_guard.py`
- `src/execution_backbone/fee_aware_edge_gate.py`
- `src/execution_backbone/execution_cost_meter/*`
- `src/execution_backbone/order_decider/*`
- `src/local_replay_runtime/shadow_execution_simulator.py`
- `src/local_replay_runtime/strategy_ladder_detailed_replay.py`

### Work

- identify reusable pure logic from execution backbone
- route replay execution realism through canonical calculators where side-effect free
- keep venue/live side effects excluded
- preserve `research_fast_mode` and `shadow_fidelity_mode` semantics

### Risk

- high
- this is the main realism lot and the most likely to break behavior or latency

### Done criteria

- replay cost model consumes canonical fee/spread/slippage logic
- fill realism status is derived from canonicalized execution assumptions where possible
- parity diagnostics expose which components are canonical vs replay-only

### Verification

- targeted tests for `execution_backbone`
- replay-vs-shadow parity deltas
- backtest proof matrix updates

---

## Lot 3 - Complete Enablers Reintegration

### Goal

Bring `complete_enablers` into the effective backtest rail, especially for Engines C and D.

### Target files

- `src/complete_enablers/*`
- `src/engines/engine_c/*`
- `src/engines/engine_d/*`
- `src/local_replay_runtime/strategy_ladder_engine_c_input_builder.py`
- `src/local_replay_runtime/strategy_ladder_engine_d_input_builder.py`
- `src/local_replay_runtime/strategy_ladder_engine_native_adapter.py`
- `src/local_replay_runtime/feature_threshold_manifest.py`
- `src/local_replay_runtime/run_class_component_coverage.py`

### Work

- identify which Build-14 signals are replay-safe and deterministic
- integrate them through engine input composition, not documentation-only manifests
- ensure replay records whether C/D decisions were made with or without enablers

### Risk

- high
- Build-14 can silently distort replay if imported in the wrong place

### Done criteria

- `complete_enablers` is part of the effective rail
- Engine C/D replay explicitly records enabler activation provenance
- C/D backtest realism no longer depends only on partial local heuristics

### Verification

- C/D focused tests
- provenance assertions in replay artifacts
- component coverage checks

---

## Lot 4 - Shared-Core Decision Fidelity Hardening

### Goal

Ensure replay does not drift from canonical scoring/risk/portfolio decisions.

### Target files

- `src/scoring_backbone/*`
- `src/risk_backbone/*`
- `src/portfolio_minimal/*`
- `src/meta_minimal/*`
- `src/local_replay_runtime/strategy_ladder_runner.py`
- `src/local_replay_runtime/replay_metrics_collector.py`
- `src/local_replay_runtime/promotion_artifact_builder.py`

### Work

- audit every replay-only heuristic that affects final decisions
- replace heuristics with canonical pure functions where available
- version every remaining heuristic explicitly as bounded proxy logic

### Risk

- medium/high
- easiest place to accidentally create hidden divergence in trade selection

### Done criteria

- decision path states which layers are canonical and which remain proxy
- no silent replay-only decision rule remains
- promotion artifacts expose fidelity level by layer

### Verification

- deterministic replay decisions for known fixtures
- strategy ladder artifact regressions
- score/risk/selection parity assertions

---

## Lot 5 - Protocol Gate Reuse Without Live Coupling

### Goal

Reuse governed protocol proofs and promotion checks without pulling live transport concerns into replay.

### Target files

- `src/protocols/contracts*.py`
- `src/protocols/promotion_gates.py`
- `src/protocols/shadow_runtime_validation.py`
- `src/protocols/shadow_runtime_evidence.py`
- `src/protocols/execution_runtime_projection_bridge.py`
- `src/backtest_artifact_import/*`
- `src/local_replay_runtime/*proof*`
- `src/local_replay_runtime/*promotion*`
- `src/monitoring/artifact_visibility.py`

### Work

- reuse promotion and proof vocabulary
- reuse validation layers that are side-effect free
- keep websocket/venue/runtime transport out of replay

### Risk

- medium
- protocols has live/runtime concerns that must not leak into `LOCAL_REPLAY`

### Done criteria

- replay proof outputs are protocol-compatible
- import rail `LOCAL_REPLAY -> backtest_artifact_import -> SHADOW` becomes cleaner
- no live-only dependency is added to replay execution

### Verification

- artifact import validation
- promotion gate tests
- proof schema compatibility tests

---

## Lot 6 - Operator Surface and Launch Discipline

### Goal

Make `cockpit` launch only governed backtest flows and surface fidelity/provenance clearly.

### Target files

- `src/cockpit/action_support.py`
- `src/cockpit/backtest_preflight.py`
- `src/cockpit/runtime_support.py`
- `src/cockpit/state.py`
- `src/cockpit/backtest_state_support.py`
- `src/cockpit/templates/pages/backtest.html`
- `src/cockpit/templates/partials/*backtest*`

### Work

- expose backtest fidelity mode
- expose canonical/proxy layer status
- block launches that would produce misleading realism claims
- surface Build-14 / execution / protocol proof readiness

### Risk

- low/medium
- mostly operator UX and guardrails, but can confuse launches if badly aligned

### Done criteria

- cockpit reflects actual backtest fidelity
- operator can see what is still proxy
- launch blockers are governed and explicit

### Verification

- cockpit tests
- preflight tests
- HTML/view-model consistency checks

---

## Lot 7 - Regression Net and Closure

### Goal

Lock the rail with proof so future work does not reintroduce replay drift.

### Target files

- `tests/test_local_replay_runtime/*`
- `tests/test_execution_backbone/*`
- `tests/test_protocols/*`
- `tests/cockpit/*`
- `scripts/run_dag_check.py`
- `scripts/run_strategy_ladder_*`

### Work

- add replay-vs-shadow parity fixtures
- add edge-level proof expectations
- add regression tests for:
  - DAG validity
  - execution realism provenance
  - complete enablers activation
  - promotion artifact fidelity
  - cockpit launch blocking

### Risk

- low
- but mandatory to close the migration safely

### Done criteria

- test bands exist for all changed rails
- backtest fidelity claims are machine-checked
- no undocumented replay-only logic remains in critical path

### Verification

- full targeted pytest band
- DAG check
- proof matrix generation

---

## Recommended Order of Implementation

1. Lot 0
2. Lot 1
3. Lot 2
4. Lot 3
5. Lot 4
6. Lot 5
7. Lot 6
8. Lot 7

## Priority Interpretation

- `P0`: Lot 0, Lot 2, Lot 3
- `P1`: Lot 1, Lot 4, Lot 5
- `P2`: Lot 6, Lot 7

## Recommended First Patch Set

The first implementation slice should be small but strategic:

1. freeze architecture truth for the current replay rail
2. extract a typed replay-execution seam in `local_replay_runtime`
3. write tests around current simulator-backed behavior before replacing internals

That gives a stable platform for deeper rewiring without losing auditability.

## Explicit Post-Generation Checklist

- lot order defined
- target files listed per lot
- risks listed per lot
- done criteria listed per lot
- verification path listed per lot
- migration aligned with one shared V5.3 core
- no forbidden profile or parallel runtime introduced
