# Codex Task — V5.3 RewardAuditRecord MVP

**Status**: IMPLEMENTATION PROMPT / LOCAL_REPLAY_ONLY  
**Target system**: V5.3 trading system  
**Scope**: Add a governed economic reward-audit record for replay/backtest/shadow evidence.  
**Non-goal**: This is not a new engine, not RL live trading, not automatic calibration, and not a VPS learning loop.

---

## 0. Codex opening context

You are working on the V5.3 trading system, specifically the Local Replay / audit evidence rail.

Global invariants:

- Preserve canonical engines A/B/C/D only.
- Do not create Engine E.
- Do not replace `SignalCandidate` or `ForecastSignalCandidate`.
- Do not modify live trading behavior.
- Do not add any automatic threshold recalibration.
- Do not add a new VPS runtime.
- Do not create a new top-level `src/local_ai_lab` package.
- Keep implementation additive and surgical.
- Runtime VPS must only consume signed/calibrated artifacts; training, reward analysis, and calibration remain Local Lab / replay-side.
- Every no-trade, refusal, no-fill, phantom, rejected, and accepted-filled decision must be auditable without survivorship bias.

Modules that must connect to this work:

- `src/interface_contracts/decision_contracts.py` through existing signal references only.
- `src/interface_contracts/forecast_contracts.py` through existing forecast signal references only, if present.
- `src/interface_contracts/refusal_records.py` through `RefusalRecord` references only, if present.
- `src/meta_minimal/refusal_journal/` through existing refusal journal outputs only, if present.
- `src/local_replay_runtime/` as the correct rail for building and aggregating reward audit records.
- Existing execution/fill/cost records only through their current public contracts; do not invent a parallel execution schema.

Forbidden defaults:

- No `side="flat"` path.
- No fake blocked trade emitted as a real trade.
- No new canonical decision contract.
- No new engine.
- No broad repo rewrite.
- No RL/DQN live policy.
- No direct modification of live VPS gates.
- No hidden hardcoded production threshold.
- No mutation of existing frozen records.
- No `Any` unless justified with a local `# noqa: Any` comment and no better type exists.

After generation, verify explicitly:

- `python -m py_compile` on every touched file.
- Targeted pytest for new contracts and local replay reward audit tests.
- Existing interface contract tests remain green.
- Existing local replay tests remain green.
- Engineering guardrails report `new_violations=0`.
- No existing canonical contract was widened or replaced.

---

## 1. Objective

Add `RewardAuditRecord`, a frozen, audit-ready contract that converts every V5.3 decision outcome into an economic proof record:

```text
Signal / refusal / no-fill / phantom / filled trade
        ↓
Replay or shadow execution outcome
        ↓
Costs, slippage, drawdown, adverse selection
        ↓
RewardAuditRecord
        ↓
RewardAuditAggregator
        ↓
Evidence for calibration, promotion, and post-run diagnostics
```

The record answers:

```text
Was this decision economically good after fees, slippage, adverse selection, drawdown, turnover, and missed/refused opportunities?
```

This component must improve backtest/replay/shadow audit quality without changing live decision behavior.

---

## 2. Placement

### Files to add

```text
src/interface_contracts/reward_audit_contracts.py
src/local_replay_runtime/reward_audit_builder.py
src/local_replay_runtime/reward_audit_aggregator.py

tests/test_interface_contracts/test_reward_audit_contracts.py
tests/test_local_replay_runtime/test_reward_audit_builder.py
tests/test_local_replay_runtime/test_reward_audit_aggregator.py
```

### Files to modify, only if needed

```text
src/interface_contracts/__init__.py
src/local_replay_runtime/__init__.py
```

Modification policy:

- Export the new contract additively.
- Do not modify `decision_contracts.SignalCandidate`.
- Do not modify `forecast_contracts.ForecastSignalCandidate`.
- Do not modify existing refusal schema unless a current export pattern requires additive import exposure.

---

## 3. Contract design

### 3.1 Required enums

Create explicit enums in `reward_audit_contracts.py`.

```python
class RewardDecisionType(str, Enum):
    ACCEPTED_FILLED = "accepted_filled"
    ACCEPTED_NO_FILL = "accepted_no_fill"
    NO_TRADE = "no_trade"
    HARD_BLOCK = "hard_block"
    PORTFOLIO_REJECTED = "portfolio_rejected"
    RISK_REJECTED = "risk_rejected"
    PHANTOM = "phantom"
    MISSED_OPPORTUNITY = "missed_opportunity"
```

```python
class RewardAuditMode(str, Enum):
    LOCAL_REPLAY = "local_replay"
    SHADOW = "shadow"
    MICRO_LIVE_REVIEW = "micro_live_review"
    LIVE_REVIEW = "live_review"
```

```python
class RewardAuditQuality(str, Enum):
    CLEAN = "clean"
    PARTIAL_FILL = "partial_fill"
    NO_FILL = "no_fill"
    STALE_DATA = "stale_data"
    INCOMPLETE_COSTS = "incomplete_costs"
    INCOMPLETE_COUNTERFACTUAL = "incomplete_counterfactual"
```

Notes:

- `MICRO_LIVE_REVIEW` and `LIVE_REVIEW` are review labels only. They must not imply online learning or auto-calibration.
- Do not create a runtime mode enum if one already exists. These are audit-mode labels local to reward audit records.

---

### 3.2 Main contract: `RewardAuditRecord`

Use Pydantic v2 if the repo is already on Pydantic v2. Match the repo's current contract style.

Required behavior:

- Frozen model.
- `extra="forbid"`.
- Strict validation.
- Deterministic identity field.
- No mutable default values.
- Monetary values as `Decimal | None` where they represent actual notional or price.
- Bps/ratios as `float | None` with finite-value validation.
- Timestamps as `int` nanoseconds.

Proposed fields:

```python
class RewardAuditRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    # identity
    reward_audit_id: str
    audit_mode: RewardAuditMode
    timestamp_ns: int
    run_id: str
    replay_session_id: str | None = None

    # strategy identity
    strategy_id: str
    engine_id: str
    pair: str
    regime_bucket: str | None = None
    calibration_version: str | None = None
    feature_hash: str | None = None

    # decision linkage
    decision_type: RewardDecisionType
    signal_ref: str | None = None
    forecast_signal_ref: str | None = None
    refusal_ref: str | None = None
    order_ref: str | None = None
    fill_ref: str | None = None

    # signal economics expected before execution
    forecast_strength: float | None = None
    expected_gain_bps: float | None = None
    expected_cost_bps: float | None = None
    expected_ce_bps: float | None = None
    expected_break_even_bps: float | None = None

    # execution outcome
    intended_notional: Decimal | None = None
    filled_notional: Decimal | None = None
    entry_price: Decimal | None = None
    exit_price: Decimal | None = None
    holding_seconds: float | None = None

    # realized cost decomposition
    fee_bps: float = 0.0
    slippage_bps: float = 0.0
    spread_cost_bps: float = 0.0
    adverse_selection_bps: float = 0.0
    partial_fill_penalty_bps: float = 0.0

    # realized outcome
    gross_return_bps: float | None = None
    net_return_bps: float | None = None
    max_adverse_excursion_bps: float | None = None
    max_favorable_excursion_bps: float | None = None

    # counterfactual/refusal outcome
    counterfactual_return_bps: float | None = None
    refusal_opportunity_bps: float | None = None

    # reward decomposition
    cost_penalty_bps: float
    drawdown_penalty_bps: float
    turnover_penalty_bps: float
    reward_raw_bps: float
    reward_normalized: float | None = None

    # audit diagnostics
    quality: RewardAuditQuality
    reason_codes: tuple[str, ...]
    data_quality_flags: tuple[str, ...] = ()
    versions: Mapping[str, str] = Field(default_factory=dict)
```

If the repo forbids `Mapping` in Pydantic frozen records due to serialization issues, use `dict[str, str]` with a validator that copies and freezes semantics according to current repo practice.

---

## 4. Validation rules

Implement model validators or field validators consistent with current repo style.

Required validations:

1. `timestamp_ns > 0`.
2. `reward_audit_id`, `run_id`, `strategy_id`, `engine_id`, and `pair` must be non-empty after stripping.
3. `engine_id` must be one of `A`, `B`, `C`, `D` unless the current repo has a canonical engine enum. If an enum exists, use it.
4. `reason_codes` must contain at least one stable machine-readable code.
5. Bps values must be finite. No `NaN`, `inf`, or `-inf`.
6. Monetary `Decimal` values, when present, must be positive except where the repo has an existing zero-notional convention.
7. `filled_notional <= intended_notional` if both are present.
8. `exit_price` is required for `ACCEPTED_FILLED` unless the current replay model supports open-position interim audits. If open-position audits exist, add a separate decision type or quality flag instead of silently allowing missing exit.
9. `refusal_ref` is required for refusal-like decisions:
   - `NO_TRADE`
   - `HARD_BLOCK`
   - `PORTFOLIO_REJECTED`
   - `RISK_REJECTED`
10. `signal_ref` or `forecast_signal_ref` is required for accepted decision types:
   - `ACCEPTED_FILLED`
   - `ACCEPTED_NO_FILL`
   - `PHANTOM`
11. `counterfactual_return_bps` is optional in MVP, but if provided for a refusal, compute `refusal_opportunity_bps` deterministically.
12. `reward_normalized` may be `None` at record-build time. Normalization is aggregator-level unless the current run context already provides stable mean/std.

---

## 5. Reward formula

### 5.1 Base formulas

All reward values are in basis points.

```text
net_return_bps =
    gross_return_bps
    - fee_bps
    - slippage_bps
    - spread_cost_bps
```

```text
cost_penalty_bps =
    fee_bps
    + slippage_bps
    + spread_cost_bps
    + adverse_selection_bps
    + partial_fill_penalty_bps
```

```text
reward_raw_bps =
    net_return_bps
    - adverse_selection_bps
    - drawdown_penalty_bps
    - turnover_penalty_bps
    - partial_fill_penalty_bps
```

For no-trade/refusal records with counterfactual return available:

```text
refusal_opportunity_bps = counterfactual_return_bps
```

Then:

```text
reward_raw_bps = -refusal_opportunity_bps
```

Interpretation:

- If counterfactual return was negative, refusal reward is positive because the refusal avoided a loss.
- If counterfactual return was positive, refusal reward is negative because the system missed profit.

If counterfactual return is unavailable:

```text
reward_raw_bps = 0.0
quality = INCOMPLETE_COUNTERFACTUAL
reason_codes includes "reward.counterfactual_unavailable"
```

Do not invent fake counterfactual data.

---

### 5.2 Drawdown penalty

Use a simple explicit helper in the builder:

```text
drawdown_penalty_bps =
    max(0, abs(max_adverse_excursion_bps) - tolerated_mae_bps) * drawdown_weight
```

MVP defaults:

```python
DEFAULT_TOLERATED_MAE_BPS = 0.0
DEFAULT_DRAWDOWN_WEIGHT = 1.0
DEFAULT_TURNOVER_PENALTY_BPS = 0.0
```

Important:

- These defaults are audit/math defaults for record construction, not production trading thresholds.
- If a calibration loader already provides these values, thread them through a config object.
- Do not read calibration files directly inside the Pydantic contract.

---

### 5.3 Normalized reward

Aggregator-level normalization:

```text
reward_normalized = zscore(reward_raw_bps)
```

Optional clipping:

```text
reward_normalized_clipped = min(5.0, max(-5.0, reward_normalized))
```

MVP decision:

- Keep `reward_normalized=None` in individual builder output.
- Add normalization only in `reward_audit_aggregator.py`, where run-level distribution exists.
- Do not mutate existing records. Return new normalized summary objects or summary metrics.

---

## 6. Builder design

Create `src/local_replay_runtime/reward_audit_builder.py`.

### 6.1 Config contract

```python
class RewardAuditBuilderConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tolerated_mae_bps: float = 0.0
    drawdown_weight: float = 1.0
    turnover_penalty_bps: float = 0.0
    normalize_at_build_time: bool = False
```

If repo already has config style dataclasses instead of Pydantic for local replay configs, match repo style.

### 6.2 Public functions

Implement small public functions, each under 60 lines:

```python
def build_filled_reward_audit_record(...) -> RewardAuditRecord:
    """Build reward audit for an accepted and filled decision."""
```

```python
def build_no_fill_reward_audit_record(...) -> RewardAuditRecord:
    """Build reward audit for an accepted signal that did not fill."""
```

```python
def build_refusal_reward_audit_record(...) -> RewardAuditRecord:
    """Build reward audit for a refused/no-trade decision."""
```

```python
def build_phantom_reward_audit_record(...) -> RewardAuditRecord:
    """Build reward audit for a shadow/live divergence or phantom trade."""
```

If current repo has existing replay outcome contracts, accept those contracts. If not, create narrow local input models in `reward_audit_builder.py`, not in `interface_contracts`, to avoid creating broad canon too early.

Suggested narrow local input models:

```python
class RewardSignalSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    strategy_id: str
    engine_id: str
    pair: str
    signal_ref: str | None = None
    forecast_signal_ref: str | None = None
    forecast_strength: float | None = None
    expected_gain_bps: float | None = None
    expected_cost_bps: float | None = None
    expected_ce_bps: float | None = None
    expected_break_even_bps: float | None = None
    regime_bucket: str | None = None
    calibration_version: str | None = None
    feature_hash: str | None = None
```

```python
class RewardExecutionSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    intended_notional: Decimal | None = None
    filled_notional: Decimal | None = None
    entry_price: Decimal | None = None
    exit_price: Decimal | None = None
    holding_seconds: float | None = None
    gross_return_bps: float | None = None
    fee_bps: float = 0.0
    slippage_bps: float = 0.0
    spread_cost_bps: float = 0.0
    adverse_selection_bps: float = 0.0
    partial_fill_penalty_bps: float = 0.0
    max_adverse_excursion_bps: float | None = None
    max_favorable_excursion_bps: float | None = None
    order_ref: str | None = None
    fill_ref: str | None = None
```

```python
class RewardRefusalSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    refusal_ref: str
    category: str
    reason_codes: tuple[str, ...]
    counterfactual_return_bps: float | None = None
```

These local snapshots are adapters, not new canonical trading contracts.

---

## 7. Deterministic ID generation

Implement deterministic `reward_audit_id` generation.

Recommended format:

```text
reward_audit_id = sha256(
    run_id
    + timestamp_ns
    + strategy_id
    + engine_id
    + pair
    + decision_type
    + signal_ref/refusal_ref/order_ref/fill_ref
).hexdigest()
```

Rules:

- Use stable separators.
- Normalize `None` as empty string or explicit `<none>` consistently.
- Do not use random UUID for audit IDs.
- Do not include non-deterministic dictionary ordering.

---

## 8. Aggregator design

Create `src/local_replay_runtime/reward_audit_aggregator.py`.

### 8.1 Summary contract

Keep summary local to `local_replay_runtime` unless current repo has a summary contract pattern.

```python
class RewardAuditSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    n_records: int
    avg_reward_bps: float
    median_reward_bps: float
    tail_5pct_reward_bps: float
    avg_fee_bps: float
    avg_slippage_bps: float
    avg_adverse_selection_bps: float
    cost_drift_ratio: float | None
    refusal_regret_bps: float | None
    phantom_cost_bps: float | None
    reward_by_engine: dict[str, float]
    reward_by_pair: dict[str, float]
    reward_by_decision_type: dict[str, float]
    promotion_blockers: tuple[str, ...]
```

### 8.2 Required functions

```python
def summarize_reward_audit_records(records: Sequence[RewardAuditRecord]) -> RewardAuditSummary:
    """Aggregate reward audit records into run-level metrics."""
```

```python
def group_average_reward(records: Sequence[RewardAuditRecord], key: str) -> dict[str, float]:
    """Return average reward by supported key."""
```

Supported keys:

- `engine_id`
- `pair`
- `decision_type`
- `regime_bucket`

Do not implement arbitrary dynamic attribute lookup if the repo forbids it. Use explicit mapping.

### 8.3 Cost drift ratio

Compute when expected and realized costs are available:

```text
realized_cost_bps = fee_bps + slippage_bps + spread_cost_bps + adverse_selection_bps
cost_drift_ratio = average(realized_cost_bps) / average(expected_cost_bps)
```

If denominator unavailable or zero:

```text
cost_drift_ratio = None
promotion_blockers includes "reward.cost_drift_unavailable"
```

### 8.4 Promotion blockers

MVP blocker logic should be conservative and transparent:

```text
if avg_reward_bps <= 0:
    blocker = "reward.avg_non_positive"

if tail_5pct_reward_bps < -50:
    blocker = "reward.left_tail_too_negative"

if cost_drift_ratio is not None and cost_drift_ratio > 1.2:
    blocker = "reward.realized_cost_exceeds_expected"

if refusal_regret_bps is not None and refusal_regret_bps < -10:
    blocker = "reward.refusal_regret_too_negative"
```

Important:

- These are replay diagnostic blockers, not live trading hard blocks.
- If the repo has an existing promotion calibration register, output these as evidence only.
- Do not wire them directly into Shadow → Micro-live promotion without a separate governed slice.

---

## 9. Serialization

If current repo has JSONL artifact helpers, use them. Otherwise add only minimal pure functions inside `reward_audit_aggregator.py` or a small local helper:

```python
def reward_audit_record_to_json_line(record: RewardAuditRecord) -> str:
    """Serialize one reward audit record as deterministic JSON line."""
```

```python
def reward_audit_summary_to_json(summary: RewardAuditSummary) -> str:
    """Serialize reward summary as deterministic JSON."""
```

Rules:

- Use model serialization consistent with repo Pydantic version.
- Sort keys if repo artifact convention uses deterministic output.
- Decimal values must serialize as strings if that is existing repo convention; otherwise as JSON-compatible values via Pydantic serializer.
- Do not write files from the contract layer.
- Do not introduce a new artifact root path in this slice.

---

## 10. Tests

### 10.1 Contract tests

File:

```text
tests/test_interface_contracts/test_reward_audit_contracts.py
```

Required tests:

1. `RewardAuditRecord` accepts a minimal valid accepted-filled record.
2. `RewardAuditRecord` rejects empty `run_id`.
3. `RewardAuditRecord` rejects unknown engine id if no canonical engine enum exists.
4. `RewardAuditRecord` rejects `NaN` reward.
5. `RewardAuditRecord` rejects missing `refusal_ref` for `HARD_BLOCK`.
6. `RewardAuditRecord` rejects missing signal reference for `ACCEPTED_FILLED`.
7. `RewardAuditRecord` rejects `filled_notional > intended_notional`.
8. Frozen invariant: assignment to a field raises validation/type error.
9. `extra="forbid"` rejects unexpected fields.
10. Deterministic serialization round-trip if repo supports it.

### 10.2 Builder tests

File:

```text
tests/test_local_replay_runtime/test_reward_audit_builder.py
```

Required tests:

1. Filled trade computes `net_return_bps` correctly:

```text
gross=42, fee=8, slippage=5, spread=3
net = 26
```

2. Filled trade computes `cost_penalty_bps` correctly:

```text
fee=8, slippage=5, spread=3, adverse=6, partial=0
cost_penalty = 22
```

3. Filled trade computes `reward_raw_bps` correctly:

```text
net=26, adverse=6, drawdown=4, turnover=2, partial=0
reward = 14
```

4. Refusal with negative counterfactual return gives positive reward:

```text
counterfactual=-12
reward=+12
```

5. Refusal with positive counterfactual return gives negative reward:

```text
counterfactual=35
reward=-35
```

6. Refusal without counterfactual uses quality `INCOMPLETE_COUNTERFACTUAL` and reason code `reward.counterfactual_unavailable`.
7. No-fill record uses `ACCEPTED_NO_FILL`, quality `NO_FILL`, and no fake PnL.
8. Deterministic ID is stable for identical inputs.
9. Deterministic ID changes when `decision_type` or reference changes.
10. Builder does not mutate input snapshots.

### 10.3 Aggregator tests

File:

```text
tests/test_local_replay_runtime/test_reward_audit_aggregator.py
```

Required tests:

1. Empty record sequence is rejected explicitly.
2. Average reward by engine is correct.
3. Average reward by pair is correct.
4. Median reward is correct for odd and even record counts.
5. Tail 5% reward is deterministic.
6. Cost drift ratio is computed when expected costs are present.
7. Cost drift ratio is `None` when expected costs are unavailable.
8. Promotion blocker `reward.avg_non_positive` fires when average reward <= 0.
9. Promotion blocker `reward.realized_cost_exceeds_expected` fires when drift > 1.2.
10. Refusal regret metric handles only refusal-like records with available counterfactuals.

---

## 11. Acceptance criteria

This slice is accepted only if all conditions hold:

### Code acceptance

- New contract exists and is exported additively if project convention requires export.
- Builder exists under `local_replay_runtime`.
- Aggregator exists under `local_replay_runtime`.
- No canonical signal contract is modified.
- No existing engine logic is modified.
- No live runtime logic is modified.
- No new engine, profile, runtime, or package is created.
- No broad doc rewrite is performed.

### Math acceptance

- Net return, cost penalty, reward raw, refusal reward, and cost drift ratio are covered by deterministic tests.
- Missing counterfactual data is explicit and never fabricated.
- Reward normalization is not done at individual-record level unless run distribution is explicitly available.

### Audit acceptance

- Every record has a stable ID.
- Every record has reason codes.
- Refusal records can be represented without fake trades.
- No-fill records can be represented without fake fills.
- Phantom records can be represented without pretending live execution happened.

### Test acceptance

Run:

```bash
python -m py_compile \
  src/interface_contracts/reward_audit_contracts.py \
  src/local_replay_runtime/reward_audit_builder.py \
  src/local_replay_runtime/reward_audit_aggregator.py \
  tests/test_interface_contracts/test_reward_audit_contracts.py \
  tests/test_local_replay_runtime/test_reward_audit_builder.py \
  tests/test_local_replay_runtime/test_reward_audit_aggregator.py
```

Run targeted tests:

```bash
rtk pytest -q \
  tests/test_interface_contracts/test_reward_audit_contracts.py \
  tests/test_local_replay_runtime/test_reward_audit_builder.py \
  tests/test_local_replay_runtime/test_reward_audit_aggregator.py
```

Run nearby regression tests:

```bash
rtk pytest -q tests/test_interface_contracts/
rtk pytest -q tests/test_local_replay_runtime/
```

Run guardrails:

```bash
python scripts/run_engineering_guardrails.py
```

Expected:

```text
new_violations=0
```

---

## 12. Implementation order

### Step 1 — Inspect current repo

Before coding, inspect:

```bash
rtk read src/interface_contracts/decision_contracts.py
rtk read src/interface_contracts/forecast_contracts.py
rtk read src/interface_contracts/refusal_records.py
rtk grep "frozen=True" src/interface_contracts tests/test_interface_contracts
rtk grep "RefusalRecord" src tests
rtk grep "jsonl" src/local_replay_runtime tests/test_local_replay_runtime
```

Determine:

- Pydantic version and style.
- Existing enum style.
- Existing serialization style.
- Existing local replay artifact style.
- Existing reference field naming conventions.

### Step 2 — Add `reward_audit_contracts.py`

Implement enums and `RewardAuditRecord`.

Keep helper validators small:

```text
_validate_non_empty_text
_validate_finite_bps
_validate_positive_decimal
_validate_required_references
```

### Step 3 — Add contract tests

Write fail-first tests before finalizing implementation where practical.

### Step 4 — Add builder

Implement local snapshots only if existing replay outcome contracts are not suitable.

Use helpers:

```text
_resolve_reward_audit_id
_compute_net_return_bps
_compute_cost_penalty_bps
_compute_drawdown_penalty_bps
_compute_filled_reward_bps
_compute_refusal_reward_bps
_resolve_quality
_merge_reason_codes
```

### Step 5 — Add builder tests

Cover formulas and ID determinism.

### Step 6 — Add aggregator

Implement summary and grouping.

Use helpers:

```text
_mean
_median
_percentile_floor_or_nearest
_average_by_key
_compute_cost_drift_ratio
_compute_refusal_regret_bps
_compute_phantom_cost_bps
_resolve_promotion_blockers
```

Keep percentile deterministic and documented.

### Step 7 — Add aggregator tests

Cover summary outputs and blocker logic.

### Step 8 — Add exports only if needed

Modify `src/interface_contracts/__init__.py` only if that is the repo convention.

Do not export local builder functions globally unless local replay package convention already does so.

### Step 9 — Run verification commands

Run py_compile, targeted pytest, nearby regression, and guardrails.

### Step 10 — Write audit pack

If the repo has `docs/production_deployment_plan/update_audit/` convention, add a concise audit file:

```text
docs/production_deployment_plan/update_audit/YYYY-MM-DD_reward_audit_record_mvp.md
```

Audit pack content:

```text
Objective
Files changed
Claims implemented
Fail-first evidence
Tests and proof
Deferred / not done
Residual risks
Completion status
Next safe step
```

Do not rewrite broad docs in this slice.

---

## 13. Deferred work

Do not implement these in MVP:

- RL/DQN training.
- LSTM belief-state model.
- Live reward learning.
- Automatic calibration update.
- Shadow → Micro-live promotion wiring.
- Full counterfactual simulation engine.
- UI/Grafana dashboard.
- Cross-run model selection.
- Bayesian uncertainty.

These are future slices only after RewardAuditRecord MVP is stable.

---

## 14. Expected final Codex response

Return a concise implementation report:

```text
Summary:
- Added RewardAuditRecord contract and local replay builder/aggregator.

Files changed:
- ...

Key decisions:
- Reward remains audit-only.
- Missing counterfactual data is explicit.
- Normalization is aggregator-level, not record-level.

Tests:
- py_compile: pass
- targeted pytest: X passed
- interface contracts: X passed
- local replay runtime: X passed
- engineering guardrails: new_violations=0

Deferred:
- No RL/DQN, no LSTM, no live wiring, no auto-calibration.
```

---

## 15. Final reminder

This slice exists to make V5.3 backtest/replay/shadow evidence more truthful. It must not make the trading system more autonomous.

Canonical one-line intent:

```text
RewardAuditRecord transforms every V5.3 decision outcome — filled trade, no-fill, refusal, portfolio reject, risk reject, phantom, or missed opportunity — into a deterministic economic proof record for Local Replay and Shadow analysis, without changing live decision behavior.
```
