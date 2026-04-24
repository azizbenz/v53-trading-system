# V5.3 — Codex Spec Part 2
## Walls + Spoofing Features → ML Dataset / Labels / Promotion Gate / Proof Discipline

**Status**: IMPLEMENTATION SPEC — detailed, bounded, proof-oriented
**Target actor**: Codex
**Scope**: integrate the already-specified `walls_and_spoofing` microstructure outputs into the Local IA Lab ML pipeline, without changing the canonical runtime sovereignty of engines A/B/C/D
**Parent canon**:
- `19_MULTIPAIR_MODERNIZATION_PLAN.md`
- `20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `12_LOCAL_LAB_VS_VPS_SEPARATION.md`
- `13_CALIBRATION_METHODS.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`

---

## 0. One-line doctrine

This slice does **not** turn walls/spoofing into a live sovereign runtime decider.
It makes these signals usable as **Local-IA-Lab-only ML features**, then promotes them to VPS **only** through a governed model artifact if and when they survive walk-forward, drift checks, and promotion gates.

---

## 1. Non-negotiable invariants

### 1.1 System invariants

1. Engines **A/B/C/D remain sovereign** on trade direction and canonical emission.
2. The ML layer remains an **additive enabler**, not a fifth engine.
3. The VPS **never trains**, never runs feature search, never runs Optuna, never mutates thresholds silently.
4. Training, feature engineering, label building, walk-forward, SHAP, and model artifact production happen in the **Local IA Lab only**.
5. Runtime consumes **signed, versioned, immutable artifacts**.
6. No quant-anchor file may be touched in this slice:
   - `src/calibration_methods/psr.py`
   - `src/calibration_methods/dsr.py`
   - `src/calibration_methods/pot_gpd.py`
   - `src/calibration_methods/energy_distance.py`
7. No 1990s TA indicator may become a structural driver of the ML pipeline.
8. No direct runtime hard-block may be introduced from walls/spoofing features in this slice.
9. No feature may use data observed after timestamp `t` when constructing row `X_t`.
10. No target may use any data from `<= t` except the anchor price/value frozen at `t`.

### 1.2 Methodology invariants

Codex must follow the repository methodology hardening:
- first do **CODE CHECK**
- then **DOC CHECK**
- then **PLACEMENT CHECK**
- only then implement

The goal is to avoid inventing a new seam when a canonical seam already exists.

---

## 2. Objective of this slice

Take the walls/spoofing microstructure outputs defined in the Part 1 spec and integrate them into the ML research-and-promotion rail through:

1. a governed **feature set contract**,
2. a deterministic **dataset builder**,
3. an explicit **label definition**,
4. time-series-safe **walk-forward splits**,
5. feature-leakage prevention,
6. a typed **training artifact**,
7. a fail-closed **promotion gate**,
8. post-training **drift / parity / SHAP evidence**.

This slice must produce enough evidence that the user can audit whether walls/spoofing features are:
- useful,
- stable,
- not leaky,
- not fake edge,
- and not merely descriptive theatre.

---

## 3. What this slice is not allowed to do

Codex must **not**:

1. create a new engine,
2. create a runtime path where spoofing suspicion directly flips side,
3. block live trading directly from a spoofing score,
4. train on VPS,
5. use deep learning, RL, sequence transformers, or an opaque raw-book model,
6. consume the full raw book tensor directly as model input in this slice,
7. backfill missing future-aligned depth data,
8. use future highs/lows in target construction,
9. tune thresholds purely on in-sample PnL,
10. call the output “spoofing proof”,
11. invent a second feature registry,
12. mutate existing canonical engine/runtime contracts without an additive seam,
13. widen forecast caps of A/B/C/D,
14. introduce a hidden live-only fallback,
15. change any live gate or risk breaker in this slice.

---

## 4. Real placement in the repo

### 4.1 Files to create or extend

#### A. Feature contract / feature names
Preferred placement:
- `src/data_backbone/microstructure/feature_registry.py` (extend)
- `src/data_backbone/microstructure/walls_and_spoofing.py` (already specified in Part 1)

#### B. Dataset builder
Create:
- `src/calibration_methods/ml_dataset_builder.py`

#### C. Label contract
Create:
- `src/interface_contracts/ml_label_contracts.py`

#### D. Training artifact
Create or extend:
- `src/interface_contracts/ml_model_artifact.py`

#### E. Model promotion gate
Create or extend:
- `src/complete_enablers/ml_model_promotion_gate.py`

#### F. Drift / parity / model risk support
Create or extend:
- `src/meta_learning/model_risk_registry/`
- `src/meta_learning/strategy_drift_monitor/`

#### G. Optional local analysis exporter
Create if needed:
- `src/local_replay_runtime/ml_feature_evidence_exporter.py`

### 4.2 Files not to create

Do **not** create:
- `src/local_ai_lab/`
- `src/ml_runtime/`
- `src/engines/engine_e/`
- a second parallel artifact transport package

---

## 5. Feature usage contract

### 5.1 Features from the walls/spoofing slice

The following outputs from `WallsAndSpoofingSnapshot` are candidates for ML input:

1. `wall_strength_bid`
2. `wall_strength_ask`
3. `wall_persistence_bid`
4. `wall_persistence_ask`
5. `wall_pullaway_bid`
6. `wall_pullaway_ask`
7. `near_touch_cancel_ratio_bid`
8. `near_touch_cancel_ratio_ask`
9. `executed_vs_displayed_bid`
10. `executed_vs_displayed_ask`
11. `book_shape_skew`
12. `microprice_pressure`
13. `real_wall_score_bid`
14. `real_wall_score_ask`
15. `spoof_suspicion_score_bid`
16. `spoof_suspicion_score_ask`
17. `deceptive_liquidity_score`

### 5.2 First integration rule

The first ML integration must **not** necessarily use all 17 values.
Codex must implement a feature-switchable registry so the Local IA Lab can choose:
- **core_v1**,
- **extended_v2**,
- **ablation sets**.

Recommended initial core set:
1. `real_wall_score_bid`
2. `real_wall_score_ask`
3. `spoof_suspicion_score_bid`
4. `spoof_suspicion_score_ask`
5. `deceptive_liquidity_score`
6. `book_shape_skew`
7. `microprice_pressure`
8. `executed_vs_displayed_bid`
9. `executed_vs_displayed_ask`
10. `wall_pullaway_bid`
11. `wall_pullaway_ask`

Reason:
These are the most semantically compressed and least redundant V1 fields.

### 5.3 Existing feature coexistence

These walls/spoofing features must be allowed to coexist with already canonical microstructure features such as:
- OFI,
- VPIN,
- queue pressure,
- Kyle lambda,
- PIN,
- realized kernel volatility,
- spread dynamics.

But Codex must not blindly duplicate them under slightly different names.

---

## 6. Dataset row definition

### 6.1 Row timestamp

Each ML row is anchored at a single timestamp `t`.

The row contains:
- all admissible features computed from data `<= t`,
- metadata fields needed for audit,
- one target computed strictly from data `> t`.

### 6.2 Required row schema

Implement a frozen row contract:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class MlDatasetRow:
    pair: str
    timestamp_ns: int
    engine_context: str | None
    regime_bucket: str | None
    feature_values: Mapping[str, float]
    label_name: str
    label_value: float | int
    anchor_price: float
    input_data_hash: str
    feature_set_hash: str
```

### 6.3 Required metadata columns

Even if not fed into the model directly, the dataset builder must preserve for audit:
- `pair`
- `timestamp_ns`
- `anchor_price`
- `feature_set_hash`
- `input_data_hash`
- `label_name`
- `engine_context` if available
- `regime_bucket` if available

### 6.4 Columns the model must never see directly

Before training, remove from the ML matrix:
- raw timestamps,
- raw price columns,
- raw high/low/close columns used only for bookkeeping,
- any string identity field,
- any target-leaking audit fields,
- any post-hoc realized return column.

---

## 7. Label design — exact first choice

### 7.1 First label to implement

The first production-candidate label is:

```text
label_direction_t_h = 1 if mid_{t+h} > mid_t * (1 + fee_safe_buffer)
                        0 otherwise
```

Where:
- `mid_t` = anchor midprice at timestamp `t`
- `mid_{t+h}` = first valid midprice at timestamp `t + h`
- `h` = horizon in seconds or bars
- `fee_safe_buffer` = ex-ante minimum relative move required to remain meaningful after costs

### 7.2 Mandatory horizons

Implement at least these horizons in the dataset builder, even if only one is used in V1 training:
- `h = 60s`
- `h = 300s`
- `h = 900s`

Reason:
The system has engines with short and medium horizons. The Local IA Lab needs horizon experiments before locking a single label.

### 7.3 V1 training choice

For the first model artifact, use:
- horizon = `300s`
- label name = `direction_up_300s_fee_safe`

Reason:
- 60s is too noisy for a first bounded LightGBM model
- 900s risks mixing too many regime changes for the first pass
- 300s is a realistic bridge between microstructure and short-term continuation/mean-reversion context

### 7.4 Fee-safe buffer

Define:

```text
fee_safe_buffer = (expected_round_trip_fee_bps + expected_slippage_bps + delta_safe_bps) / 10000
```

This buffer is a **feature-engineering / labeling contract**, not a runtime live threshold.
It must come from a Local IA Lab evidence source, not a silent hardcode.

If no calibrated evidence exists yet, Codex may use a temporary clearly-named local constant in the dataset builder **only if**:
- it is marked `LOCAL_RESEARCH_DEFAULT_ONLY`,
- it is not exported to VPS,
- it is surfaced in the artifact metadata.

### 7.5 Prohibited labels

Do **not** implement as first label:
- profit directly net of future high/low,
- “did the bar hit TP first or SL first” if based on future intrabar path not truly observable,
- any label requiring future microstructure data that is not aligned and reconstructible,
- any label using trade outcomes from actual live fills as if they were clean targets,
- a label built from raw engine decision outputs.

---

## 8. Anti-leakage rules

### 8.1 Hard rule

For each dataset row at time `t`:
- Features `X_t` must use only observations at times `<= t`
- Target `Y_t` must use only observations at times `> t`

### 8.2 Forbidden leakage patterns

Codex must explicitly test against:
1. using candle high/low of the anchor bar when the anchor timestamp is inside the bar,
2. forward-filling post-`t` book data backward,
3. using future trade classification to clean present features,
4. normalization computed over the full dataset before split,
5. SHAP / selection using full-history trained model before walk-forward separation,
6. using global z-scores fit on all data before time split.

### 8.3 Required normalization discipline

Any normalization must be either:
- local-window feature engineering at row time using only past data, or
- train-fold-only transformation fit inside each walk-forward fold.

Never fit a global scaler on the full dataset before splitting.

---

## 9. Split policy

### 9.1 Mandatory split type

Use **time-ordered walk-forward** only.
No random K-fold.
No shuffled split.
No standard CV.

### 9.2 First mandated walk-forward scheme

Implement:
- `180 days train`
- `30 days test`
- step size `30 days`

That means:
- fold 1: train [T0, T0+180d), test [T0+180d, T0+210d)
- fold 2: train [T0+30d, T0+210d), test [T0+210d, T0+240d)
- etc.

### 9.3 Purge / embargo

For this first bounded implementation, use an **embargo gap** between train and test if target overlap could cause contamination.

Recommended default:
- embargo = max(target horizon, 300s)

Expose it explicitly in the split configuration.

### 9.4 Pair strategy

Codex must support both:
- **pooled multi-pair training**, and
- **pair-stratified evaluation**.

The first model may be trained pooled, but evaluation must report at least:
- global metrics
- per-pair metrics

Reason:
A model that looks fine globally may be carried by BTC/ETH only and fail on the rest.

---

## 10. Training model choice

### 10.1 Approved model for V1

Use **LightGBM classifier** only.

### 10.2 Explicitly forbidden in this slice

Do not implement:
- XGBoost
- CatBoost
- torch MLP
- LSTM
- Transformer
- RL
- imitation learning
- mixture-of-experts

### 10.3 Training hyperparameter envelope

Codex must expose a bounded search space, not an open-ended one.

Recommended V1 envelope:
- objective: `binary`
- boosting: `gbdt`
- learning_rate: `[0.01, 0.1]`
- num_leaves: `[15, 127]`
- max_depth: `[3, 6]`
- min_data_in_leaf: `[20, 200]`
- feature_fraction: `[0.5, 1.0]`
- bagging_fraction: `[0.5, 1.0]`
- bagging_freq: `[1, 10]`
- lambda_l1: `[0.0, 5.0]`
- lambda_l2: `[0.0, 10.0]`
- early_stopping_rounds: `50`
- optuna_trials_max: `100`

### 10.4 Determinism

The trainer must be deterministic given:
- dataset hash
- feature set hash
- training seed
- split configuration

Artifact metadata must record all four.

---

## 11. Outputs and artifacts

### 11.1 Required training artifact

Create a frozen artifact model carrying at least:
- `schema_version`
- `model_family = "lightgbm"`
- `label_name`
- `feature_names`
- `feature_set_hash`
- `dataset_hash`
- `pair_universe`
- `train_window`
- `validation_window`
- `walk_forward_spec`
- `training_seed`
- `backtest_sharpe`
- `oos_sharpe`
- `shadow_diff_pct` if available
- `ks_test_features_pvalue` if available
- `promotion_state`
- `artifact_hash`
- `created_at`
- optional `shap_summary_path`
- optional `per_pair_metrics`

### 11.2 Feature evidence export

Export a local evidence bundle with:
- feature importance rank
- SHAP summary per fold
- ablation summary
- per-pair stability
- class balance stats
- label prevalence
- missingness stats

This export is **Local IA Lab only**.

---

## 12. Promotion gate — exact fail-closed rule

### 12.1 V1 gate

A model artifact is promotable only if all are true:

```text
oos_sharpe >= 0.80 * backtest_sharpe
ks_test_features_pvalue > 0.05
shadow_diff_pct < 0.1%
required_fields_present == True
artifact_hash_valid == True
```

### 12.2 Missing evidence policy

If one mandatory metric is missing:
- gate returns `BLOCKED`
- not `PASS`
- not `WARN`

### 12.3 Per-pair degradation guard

Add one bounded extra rule:
- if more than 40% of the traded-pair universe has negative OOS expectancy or sharply degraded calibration quality, artifact cannot promote.

Codex must implement this as an explicit audited rule, not a hidden heuristic.

---

## 13. Drift monitoring requirements

### 13.1 Model risk registry

Store at least:
- feature set hash
- model artifact hash
- label name
- OOS metrics
- shadow/live parity metrics
- promotion state
- pause/block reason if drifted

### 13.2 Strategy drift monitor

The drift monitor must be able to flag:
- feature distribution drift,
- prediction distribution drift,
- WR/CE drift if connected to downstream evidence,
- pair concentration drift.

### 13.3 Walls/spoof-specific drift checks

Add explicit drift summaries for:
- `deceptive_liquidity_score`
- `spoof_suspicion_score_bid`
- `spoof_suspicion_score_ask`
- `real_wall_score_bid`
- `real_wall_score_ask`

Reason:
These features are especially vulnerable to venue-behavior change and market regime shifts.

---

## 14. SHAP and ablation requirements

### 14.1 Mandatory SHAP evidence

For each promoted candidate model, compute:
- global SHAP importance
- fold-level SHAP importance
- per-pair SHAP summary if computationally feasible

### 14.2 Mandatory ablation

Codex must implement at least three dataset runs:
1. **baseline_without_walls_spoofing**
2. **walls_spoofing_only_addition**
3. **core_microstructure_plus_walls_spoofing**

The purpose is to answer:
- do walls/spoofing features add information?
- or do they merely duplicate OFI/VPIN/queue pressure?

### 14.3 Acceptance logic for the feature family

Walls/spoofing features should only proceed beyond research if they show at least one of:
- measurable OOS uplift,
- better calibration stability,
- better per-pair robustness,
- lower false-positive rate in toxic conditions.

No single metric is enough; the evidence bundle must be reviewed holistically.

---

## 15. Integration with the bounded ML enabler

### 15.1 Runtime role

At runtime, if a promoted artifact exists, the ML layer may only produce:
- `ml_confidence ∈ [0,1]`
- optional debug `ml_direction`

### 15.2 Fusion formula

Use exactly:

```text
fused_score = base_score * (1 + alpha * (ml_confidence - 0.5))
```

Constraints:
- `alpha <= 0.5`
- preferred default `alpha ∈ [0.0, 0.3]`
- `ml_confidence = 0.5` means neutral
- side unchanged
- no fake blocked trade

### 15.3 Explicit non-role of walls/spoofing slice

This feature family is **not** allowed in this slice to:
- create side,
- change bet_structure,
- widen forecast caps,
- set stop-loss values,
- trigger direct engine refusal by itself,
- replace cost feasibility.

---

## 16. Tests to implement

### 16.1 Dataset builder tests

Create:
- `tests/test_calibration_methods/test_ml_dataset_builder.py`

Must prove:
1. rows use only data `<= t` for features
2. target uses only data `> t`
3. missing future anchor drops or marks target invalid explicitly
4. feature set hash is stable
5. dataset hash is stable
6. feature columns are deterministic
7. pair and timestamp metadata preserved

### 16.2 Label tests

Create:
- `tests/test_interface_contracts/test_ml_label_contracts.py`
- or fold into dataset-builder tests if appropriate

Must prove:
1. 60s / 300s / 900s labels computed correctly on synthetic price path
2. fee-safe buffer applied correctly
3. no future high/low leakage
4. exact boundary behavior when future mid equals threshold

### 16.3 Split tests

Create:
- `tests/test_calibration_methods/test_walk_forward_splits.py`

Must prove:
1. no shuffled ordering
2. embargo gap respected
3. no overlap contamination
4. fold count correct
5. per-fold time ranges deterministic

### 16.4 Trainer tests

Create:
- `tests/test_calibration_methods/test_ml_trainer.py`

Must prove:
1. deterministic model hash from same seed/data
2. training fails explicitly on empty feature matrix
3. training fails explicitly on all-NaN feature column
4. Optuna trial cap respected
5. artifact metadata populated

### 16.5 Promotion gate tests

Create:
- `tests/test_complete_enablers/test_ml_model_promotion_gate.py`

Must prove:
1. pass when all conditions green
2. fail closed on missing metric
3. fail on OOS Sharpe below threshold
4. fail on KS p-value <= 0.05
5. fail on shadow diff >= 0.1%
6. fail on too many bad pairs

### 16.6 Drift tests

Create:
- `tests/test_meta_learning/test_model_risk_registry.py`
- `tests/test_meta_learning/test_strategy_drift_monitor.py`

Must prove:
1. feature drift flagged on synthetic shift
2. spoof-like features drift summary available
3. no false pause on stable synthetic data

### 16.7 Walls/spoofing ML ablation evidence tests

Create a lightweight evidence test such as:
- `tests/test_local_replay_runtime/test_ml_feature_evidence_exporter.py`

Must prove:
1. ablation report writes deterministically
2. SHAP summary paths recorded
3. missing SHAP gracefully reported, not silently ignored

---

## 17. Proof commands Codex must run

Codex must run and report at minimum:

```bash
python -m py_compile \
  src/calibration_methods/ml_dataset_builder.py \
  src/interface_contracts/ml_label_contracts.py \
  src/interface_contracts/ml_model_artifact.py \
  src/complete_enablers/ml_model_promotion_gate.py

python -m pytest \
  tests/test_calibration_methods/test_ml_dataset_builder.py \
  tests/test_calibration_methods/test_walk_forward_splits.py \
  tests/test_calibration_methods/test_ml_trainer.py \
  tests/test_complete_enablers/test_ml_model_promotion_gate.py \
  tests/test_meta_learning/test_model_risk_registry.py \
  tests/test_meta_learning/test_strategy_drift_monitor.py -q

python scripts/run_engineering_guardrails.py
python scripts/run_dag_check.py
```

If the repo already has canonical wrappers (`rtk pytest`, etc.), use them consistently.

---

## 18. Acceptance criteria

### COMPLETE
This slice is `COMPLETE` only if:
1. dataset builder exists and is typed,
2. label contract exists and is tested,
3. walk-forward split logic exists and is tested,
4. training artifact exists and round-trips,
5. promotion gate exists and is fail-closed,
6. drift surfaces exist,
7. walls/spoofing features can be included in the ML matrix,
8. no forbidden runtime sovereignty is introduced,
9. tests are green,
10. guardrails add zero new violations.

### PARTIAL
This slice is `PARTIAL` if:
- the dataset/label/split/artefact rail exists,
- but one of promotion/drift/shap evidence remains deferred,
- and Codex states that honestly.

### BLOCKED
This slice is `BLOCKED` if:
- Codex cannot identify the canonical existing ML artifact seam,
- or walls/spoofing features cannot be time-aligned safely with the chosen label source,
- or a required dependency is missing and cannot be resolved without user arbitration.

---

## 19. Post-generation verification checklist

Codex must explicitly verify:

1. MemPalace check status if applicable
2. CODE CHECK performed
3. DOC CHECK performed
4. PLACEMENT CHECK performed
5. No new engine added
6. No VPS training introduced
7. No quant-anchor file modified
8. Dataset builder is anti-leakage safe
9. Label is strictly future-based
10. Walk-forward is time-ordered only
11. Promotion gate is fail-closed
12. Drift surfaces exist
13. No runtime hard-block from walls/spoofing introduced
14. Fusion role remains additive only
15. Tests and guardrails results reported honestly

---

## 20. Opening prompt block for Codex

```text
You are working on the V5.3 ML dataset / label / promotion slice for the walls+spoofing microstructure family.

Global invariants:
- engines A/B/C/D remain sovereign
- ML is additive only
- VPS never trains
- Local IA Lab builds dataset, labels, models, SHAP, drift evidence
- no quant-anchor file may be modified
- no direct runtime hard block from walls/spoofing in this slice
- no 1990s TA drift

Modules that must connect through real seams:
- src/data_backbone/microstructure/walls_and_spoofing.py
- src/data_backbone/microstructure/feature_registry.py
- src/calibration_methods/ml_dataset_builder.py
- src/interface_contracts/ml_label_contracts.py
- src/interface_contracts/ml_model_artifact.py
- src/complete_enablers/ml_model_promotion_gate.py
- src/meta_learning/model_risk_registry/
- src/meta_learning/strategy_drift_monitor/

Forbidden defaults:
- no new engine
- no VPS training
- no raw-book deep learning
- no shuffled CV
- no future leakage
- no silent hardcode exported to VPS
- no side override
- no direct live stop from spoof suspicion
- no edits to psr/dsr/pot_gpd/energy_distance

After generation, verify explicitly:
- dataset anti-leakage
- future-only labels
- deterministic hashes
- walk-forward only
- fail-closed promotion gate
- no runtime sovereignty drift
- tests green
- guardrails green
```

---

## 21. Final doctrine sentence

The walls/spoofing family is economically interesting only if it improves the Local-IA-Lab evidence stack in a measurable, stable, non-leaky way.
Until such proof exists, it remains a research feature family — not a live sovereign anti-adversary layer.
