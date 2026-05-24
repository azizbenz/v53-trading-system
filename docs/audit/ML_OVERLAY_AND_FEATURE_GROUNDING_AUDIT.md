# ML Overlay And Feature Grounding Audit

Date: 2026-05-24
Repository: `E:\claude  v5.3\v53_trading_system`
Status: read-only audit before implementation

## Scope

This audit grounds the `ml new adon v5.3 .docx` doctrine in the current codebase.
It does not change strategy thresholds, engines A/B/C/D, `SignalCandidate`, runtime
mode, or Shadow/Micro-live/Live gates.

## Source-Of-Truth Notes

- MemPalace was checked and project memory exists for wing `v53_trading_system`.
- Current code remains the source of truth when it disagrees with historical memory.
- The current handoff and white-book state is consistent with a fail-closed rule:
  legacy features can train from klines, while non-legacy features currently require
  B2 replay grounding.

## Current Wiring

### Where The Feature Picker Is Read

- IA Lab route: `src/cockpit/server.py`, endpoint `/lab/strategy-ladder-ml-handoff`.
- Backtest route: `src/cockpit/server.py`, endpoint `/backtest/run`.
- Shared normalization: `_normalize_feature_picker_selection()` in
  `src/cockpit/server.py`.

The cockpit already prefers the hidden CSV mirror when checkbox payloads are missing.

### Where The Feature List Is Persisted

- IA Lab form state: `src/cockpit/form_state_support.py`, `LabMlHandoffFormState`.
- Backtest form state: `src/cockpit/form_state_support.py`, `BacktestFormState`.
- Backtest ML chain state: `src/cockpit/backtest_state_support.py`,
  `BacktestMlChainState`.
- Job request sidecar: `src/cockpit/action_support.py`,
  `_write_patch6_job_request()`, with `feature_names_csv`,
  `requested_feature_names`, and non-legacy counts.

### Where The Three Legacy Features Are Imposed

- `src/local_replay_runtime/strategy_ladder_expected_edge_training.py`
  defines `DEFAULT_EXPECTED_EDGE_FEATURE_NAMES`:
  `close_return`, `high_low_range`, `volume`.
- `_require_supported_legacy_features()` blocks non-legacy names on the kline-only
  training rail.
- `StrategyLadderExpectedEdgeTrainingRequest._validate_sources()` also rejects
  non-legacy features unless `b2_run_root` or `label_store_dataset_path` is present.

### Where Non-Legacy Is Blocked Without B2

- IA Lab route computes `_non_legacy_expected_edge_features()` and redirects with
  an error if launch is requested without `b2_run_root`.
- Backtest auto-chain builds a Lab handoff request and blocks non-legacy selected
  features without an existing Phase B2 replay root.
- The trainer request itself has the same fail-closed validator, so command-line
  invocation is also protected.

### Where The Frozen Artifact Imposes Its Feature List

- `src/cockpit/backtest_preflight.py` resolves artifact feature names from handoff,
  artifact summary, or backtest input.
- `src/cockpit/state.py` treats the frozen artifact as authoritative when
  `ML_MODE_OVERLAY_FROZEN` is ready.
- `src/cockpit/templates/pages/backtest.html` renders the picker as read-only in
  frozen mode and displays the artifact feature list.
- Runtime loading is guarded in
  `src/local_replay_runtime/strategy_ladder_edge_model_provider.py`; missing feature
  values fail closed instead of producing a score.

## Insertion Points

### Feature Grounding Registry

Best insertion:

- New module: `src/local_replay_runtime/feature_grounding_registry.py`.
- Optional machine-readable artifact: `docs/audit/feature_grounding_registry.json`.

Reason:

- There is already a promotion registry, but it captures SHAP/ablation verdicts,
  not temporal grounding or label leakage status.
- A separate grounding registry avoids mixing evidence quality with causality and
  runtime admissibility.

### Training Source Contract

Best insertion:

- New module: `src/local_replay_runtime/training_source_contract.py`.
- Handoff integration: `src/local_replay_runtime/strategy_ladder_ml_lab_handoff.py`
  can write contract reports under `export_dir/reports/`.
- Cockpit visibility can be added from existing handoff report refs without changing
  engines.

Reason:

- Existing anti-leakage sidecars already validate model artifact windows.
- The missing surface is an explicit dataset/root manifest contract and a simple
  train/validation/backtest overlap report that operators can inspect.

### ML Authority Contract

Best insertion:

- New module: `src/local_replay_runtime/ml_overlay_authority_contract.py`.
- Handoff or runner can emit an audit-only report declaring the current authority
  level.

Reason:

- Current code already keeps the ML model non-sovereign: it estimates edge and does
  not create candidates, change side, or bypass hard blockers.
- The doctrine needs a machine-readable proof surface for this, not an engine rewrite.

### Label Leakage Guard

Best insertion:

- Same grounding module, or a small `ml_label_leakage_guards.py` wrapper, because
  labels/outcomes are a feature-grounding classification.

Reason:

- `StrategyLadderB2LabelStoreRow` already separates `feature_values` from label fields
  such as `mfe_bps`, `mae_bps`, and forward-return labels.
- A guard should block those label/outcome names if an operator attempts to select
  them as ML runtime inputs.

## Implementation Boundaries

Allowed minimal patch scope:

- Add registry/contract modules.
- Write audit reports from the ML handoff path.
- Surface selected grounding/contract status in cockpit templates.
- Add focused tests under the existing `tests/test_local_replay_runtime` and
  `tests/cockpit` structure.

Forbidden patch scope:

- No engine A/B/C/D changes.
- No threshold changes.
- No `SignalCandidate` changes.
- No fake executed trades.
- No forced selected or executed counts.
- No proxy-to-truth promotion.
- No new runtime.

## Initial Verdict

The current system is already fail-closed on the most dangerous behavior: non-legacy
feature selection cannot silently train through the kline-only rail. The next work is
to make the doctrine explicit and auditable:

- feature grounding registry,
- label/outcome input guard,
- training source manifest/overlap contract,
- ML authority contract,
- reports and focused UI visibility.
