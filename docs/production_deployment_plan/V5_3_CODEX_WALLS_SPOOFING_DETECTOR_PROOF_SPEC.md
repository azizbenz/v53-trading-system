# V5.3 — Walls + Spoof-Like Deceptive Liquidity Detector
## Full Engineering Spec for Codex (proof-oriented, anti-hallucination)

**Status**: EXECUTION SPEC — bounded microstructure slice for Local IA Lab + future ML consumption  
**Date**: 2026-04-23  
**Role target**: Codex implementation spec  
**Parent canon**: V5.3, doc 19, doc 20, doc 23, Local IA Lab → signed artifact → VPS topology  
**Slice type**: additive, proof-oriented, no new engine, no new profile, no VPS training

---

## 0. Executive summary

This slice adds a **bounded microstructure detector** for:
- **real walls** (persistent, executable visible depth)
- **spoof-like deceptive liquidity** (displayed size that pulls away near touch and is not genuinely executable)

This slice is **not**:
- a new engine
- a legal proof-of-spoofing module
- an HFT anti-adversary platform
- a VPS-side autonomous blocker
- a deep-learning raw-book stack

The intended usage order is:
1. implement and test the calculator in `src/data_backbone/microstructure/`
2. register the resulting features in the canonical microstructure registry
3. expose them to Local IA Lab feature pipelines and the future `ml_confidence_enabler`
4. optionally consider a later bounded runtime soft-penalty only after Shadow proof

The detector must read **real depth geometry** and **deceptive liquidity patterns**, but V5.3 must **not** fantasize itself into an anti-adversary platform before economic relevance is proven.

---

## 1. Governing doctrine and non-negotiable invariants

### 1.1 Parent doctrine
This slice is governed by the following higher-order rules:

1. **V5.3 canonical engines remain A/B/C/D only**.
2. **ML is additive only**. It does not replace engines and does not set side autonomously.
3. **VPS never trains**. Local IA Lab trains, calibrates, signs, exports; VPS consumes.
4. **No critical threshold is hardcoded as a permanent truth**. Defaults are allowed locally if and only if they are clearly tagged as defaults and later migratable to calibration seams.
5. **Doc/code hierarchy**: current code is operational truth; this spec must land surgically onto real seams.
6. **No 1990s TA drift**. No RSI/MACD/Bollinger/Stochastic/Williams/Parabolic SAR contamination in this slice.
7. **No fake blocked trade**. No `side="flat"`, no invented canonical trade object for blocked paths.
8. **No runtime hard block from this slice in V1**.
9. **No quant-anchor formula edits** in:
   - `src/calibration_methods/psr.py`
   - `src/calibration_methods/dsr.py`
   - `src/calibration_methods/pot_gpd.py`
   - `src/calibration_methods/energy_distance.py`
10. **All outputs must be typed, audit-ready, and deterministic from their inputs**.

### 1.2 Specific doctrine for this slice

This slice must implement a **microstructure feature detector** that can later feed ML.
It must **not** decide trading direction and must **not** become a sovereign runtime policy.

The correct role is:
- **Local IA Lab**: research, replay, feature generation, SHAP, walk-forward, ML dataset construction.
- **VPS**: possibly compute these same features later for bounded inference only; not for training.

---

## 2. Objective

Implement a canonical calculator that detects:

1. **real wall presence**
2. **wall persistence**
3. **wall pull-away near touch**
4. **cancel-heavy near-touch behavior**
5. **executed-vs-displayed reality gap**
6. **deceptive liquidity suspicion**
7. **dominant pressure side**

The detector must operate from:
- `depth20`
- `aggTrades`

The detector must be designed so that:
- it is usable in Local IA Lab feature engineering,
- it can later feed a LightGBM tabular model,
- it remains independent from engine A/B/C/D semantics,
- it can be audited from logs and proofs without hidden rules.

---

## 3. Scope

### 3.1 Included
- one canonical calculator module in `src/data_backbone/microstructure/`
- one frozen output record
- feature-registry integration
- deterministic unit tests
- anti-leakage tests
- input-validation tests
- reason-code generation
- documented defaults and hard caps
- optional small helper functions if they remain local and typed

### 3.2 Excluded
- no ML trainer changes in this slice
- no `ml_confidence_enabler` modification in this slice
- no new runtime gating in this slice
- no direct engine A/B/C/D consumption in this slice
- no legal inference about manipulation
- no exchange enforcement or surveillance reporting layer
- no deep learning or sequence model

---

## 4. Placement and file map

### 4.1 Files to create

#### Primary module
- `src/data_backbone/microstructure/walls_and_spoofing.py`

#### Tests
- `tests/test_data_backbone/microstructure/test_walls_and_spoofing.py`

### 4.2 Files to modify
- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `src/data_backbone/microstructure/feature_registry.py`

### 4.3 Forbidden placement
Do **not**:
- create a new top-level package
- create `src/local_ai_lab/`
- create a second feature registry
- create a special-case engine-local copy of this logic
- create a runtime-only hidden version

This must land in the **canonical microstructure package**.

---

## 5. Input contract

### 5.1 Required inputs

The calculator must consume:

#### A. Depth events / snapshots
For each depth observation at time `t_i`:
- `timestamp_ns: int`
- `best_bid_price: float`
- `best_ask_price: float`
- `bid_prices: tuple[float, ...]`
- `ask_prices: tuple[float, ...]`
- `bid_sizes: tuple[float, ...]`
- `ask_sizes: tuple[float, ...]`

Constraints:
- top 20 depth levels max
- prices strictly ordered
- sizes non-negative
- best bid < best ask unless stale/corrupt, in which case raise explicit validation error

#### B. AggTrades / trade events
For each trade observation at time `u_j`:
- `timestamp_ns: int`
- `price: float`
- `quantity: float`
- `is_buyer_maker: bool` or equivalent side inference field

Constraints:
- quantity > 0
- price > 0
- timestamps non-decreasing

### 5.2 Time contract
All features at evaluation time `t` must use data with timestamps `<= t` only.
This slice must include an explicit anti-leakage validator.

### 5.3 Window contract
Supported local window:
- `window_seconds` default = `5.0`
- hard cap = `30.0`

The calculator may also internally use a short event-window fallback if clock-time density is low, but this behavior must be explicit and returned in metadata.

---

## 6. Common symbols and conventions

Let:
- `eps = 1e-12`
- `N = top_n_levels_for_wall_logic`, default `5`, hard cap `10`
- `W(t, Δ) = [t - Δ, t]`
- `mid_t = (best_bid_t + best_ask_t) / 2`
- `spread_t = best_ask_t - best_bid_t`

For side `s ∈ {bid, ask}`:
- `price_{s,k,t}` = price at level `k`
- `depth_{s,k,t}` = size at level `k`

For trades:
- `trade_price_j`
- `trade_qty_j`
- `trade_side_j ∈ {buy, sell}` inferred from aggressor convention

All divisions must use `+ eps` in denominator.

---

## 7. Output contract

Create a frozen record. Pydantic v2 frozen model is preferred for consistency with the repo, but a frozen dataclass is acceptable only if it matches existing microstructure style.

Preferred shape:

```python
class WallsAndSpoofingSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    pair: str
    computed_at_ns: int
    window_seconds: float
    n_depth_events: int
    n_trades: int

    wall_strength_bid: float
    wall_strength_ask: float
    wall_persistence_bid: float
    wall_persistence_ask: float
    wall_pullaway_bid: float
    wall_pullaway_ask: float
    near_touch_cancel_ratio_bid: float
    near_touch_cancel_ratio_ask: float
    executed_vs_displayed_bid: float
    executed_vs_displayed_ask: float
    book_shape_skew: float
    microprice_pressure: float

    real_wall_score_bid: float
    real_wall_score_ask: float
    spoof_suspicion_score_bid: float
    spoof_suspicion_score_ask: float
    deceptive_liquidity_score: float

    dominant_side: Literal["bid", "ask", "neutral"]
    insufficient_data: bool = False
    reason_codes: tuple[str, ...]

    input_data_hash: str
    method_version_hash: str
```

### 7.1 Output invariants
- all score fields must be finite floats
- bounded scores must be clipped into `[0, 1]`
- `dominant_side` must be deterministic from scores
- `reason_codes` must be deterministic and machine-stable
- if insufficient data, `insufficient_data=True` and bounded scores should still be valid numeric outputs, not NaNs

---

## 8. Mathematical definitions (closed, explicit)

## 8.1 Top-N local wall depth
For each time `t` and side `s`:

```text
TOPN_DEPTH_s(t) = {depth_{s,1,t}, depth_{s,2,t}, ..., depth_{s,N,t}}
```

with `N = 5` by default.

### 8.1.1 Local dominant displayed depth

```text
max_depth_s(t) = max_k depth_{s,k,t}
mean_depth_s(t) = mean_k depth_{s,k,t}
```

### 8.1.2 Wall strength

```text
wall_strength_s(t) = max_depth_s(t) / (mean_depth_s(t) + eps)
```

Interpretation:
- near 1.0 → homogeneous book
- > 1.0 → a level dominates local displayed depth

This raw measure is not yet bounded.

---

## 8.2 Dominant wall level selection
Define the dominant level index for side `s` at time `t`:

```text
dominant_level_index_s(t) = argmax_k depth_{s,k,t}
```

Let:
- `dominant_price_s(t) = price_{s, dominant_level_index_s(t), t}`
- `dominant_size_s(t) = depth_{s, dominant_level_index_s(t), t}`

If multiple levels tie, choose the one closest to the best price.

---

## 8.3 Wall persistence

We need persistence over the evaluation window `W(t, Δ)`.

A depth observation at time `τ` is considered to represent the **same wall** as the wall at time `t` on side `s` if:

1. it is on the same side,
2. its dominant price equals `dominant_price_s(t)`,
3. its dominant size is within tolerance of the terminal dominant size.

Size tolerance:

```text
same_size_if = abs(dominant_size_s(τ) - dominant_size_s(t)) / (dominant_size_s(t) + eps) <= size_tol
```

Default:
- `size_tol = 0.20`

Then:

```text
wall_persistence_s(t) =
    time_same_wall_s_within_window / window_seconds
```

Bound to `[0, 1]`.

---

## 8.4 Distance-to-touch
We define the relative distance between price and wall.

For bid-side wall:

```text
distance_to_wall_bid(τ) = (mid_τ - dominant_price_bid(τ)) / (mid_τ + eps)
```

For ask-side wall:

```text
distance_to_wall_ask(τ) = (dominant_price_ask(τ) - mid_τ) / (mid_τ + eps)
```

A wall is in **near-touch state** if:

```text
distance_to_wall_side(τ) <= touch_eps_bps / 10000
```

Default:
- `touch_eps_bps = 2.0`

---

## 8.5 Pull-away behavior

We detect a pull-away event when:
1. the wall was in near-touch state,
2. then dominant displayed size drops sharply,
3. without enough executed volume against that wall.

Let:

```text
size_drop_ratio_side =
    (size_before_touch_side - size_after_touch_side)
    / (size_before_touch_side + eps)
```

A near-touch pull-away episode is counted if:

```text
size_drop_ratio_side >= cancel_drop_ratio
```

with default:
- `cancel_drop_ratio = 0.70`

Then:

```text
wall_pullaway_side(t) =
    near_touch_pullaway_count_side
    / (near_touch_event_count_side + eps)
```

Bound to `[0, 1]`.

---

## 8.6 Near-touch cancel ratio
For all near-touch episodes inside the window:

```text
near_touch_cancel_ratio_side(t) =
    cancelled_displayed_volume_side
    / (displayed_volume_side + eps)
```

Where:
- `displayed_volume_side` = sum of dominant displayed volume over near-touch observations
- `cancelled_displayed_volume_side` = volume that disappeared from display without matching execution proxy

Bound to `[0, 1]` by clipping.

---

## 8.7 Executed-vs-displayed ratio

This estimates whether shown liquidity was actually executable.

For ask-side wall:
- use **aggressive buy** volume that trades into ask-side liquidity.

For bid-side wall:
- use **aggressive sell** volume that trades into bid-side liquidity.

Let:

```text
executed_vs_displayed_side(t) =
    executed_volume_against_wall_side
    / (displayed_wall_volume_side + eps)
```

Then clip:

```text
executed_vs_displayed_side(t) = clip(executed_vs_displayed_side(t), 0.0, 1.0)
```

Interpretation:
- near 1.0 → visible wall was materially executable
- near 0.0 → visible wall was not genuinely consumed

---

## 8.8 Book shape skew
This is an asymmetry measure of where depth is concentrated relative to the mid.

For each side, define relative price offsets:

```text
x_{s,k,t} = price_{s,k,t} - mid_t
```

Weight each offset by relative depth weight:

```text
w_{s,k,t} = depth_{s,k,t} / (Σ_k depth_{s,k,t} + eps)
```

Then weighted mean and std:

```text
mean_price_depth_s(t) = Σ_k w_{s,k,t} * x_{s,k,t}
std_price_depth_s(t) = sqrt(Σ_k w_{s,k,t} * (x_{s,k,t} - mean_price_depth_s(t))^2 + eps)
```

Define side skew:

```text
obs_skew_s(t) = mean_price_depth_s(t) / (std_price_depth_s(t) + eps)
```

Aggregate to one scalar:

```text
book_shape_skew(t) = obs_skew_ask(t) - obs_skew_bid(t)
```

No hard clipping required, but must remain finite.

---

## 8.9 Microprice pressure
Define:

```text
microprice_t =
    (best_ask_t * depth_bid_1_t + best_bid_t * depth_ask_1_t)
    / (depth_bid_1_t + depth_ask_1_t + eps)
```

Then:

```text
microprice_pressure_t = (microprice_t - mid_t) / (mid_t + eps)
```

This is not bounded by design but should be finite.

---

## 8.10 Robust normalization helper for local scores
Some raw measures need a robust local normalization before entering composite scores.

Use median/MAD normalization on the evaluation window or a larger local calibration window passed in explicitly.

Define:

```text
robust_z(x_t) = (x_t - median(x_window)) / (MAD(x_window) + eps)
```

Then squash for bounded contribution:

```text
z01(x_t) = 1 / (1 + exp(-robust_z(x_t)))
```

This maps raw outlier intensity into `(0, 1)`.

If there is insufficient local distribution support, fall back to a deterministic bounded transform:

```text
fallback_z01(x_t) = x_t / (1 + x_t)    for x_t >= 0
```

This fallback must be explicit and unit tested.

---

## 8.11 Real wall score
A **real wall** should be:
- locally large,
- persistent,
- not systematically pulled away,
- at least partially executable.

Define:

```text
real_wall_score_side(t) =
    0.35 * z01(wall_strength_side(t))
  + 0.35 * wall_persistence_side(t)
  + 0.20 * executed_vs_displayed_side(t)
  - 0.10 * wall_pullaway_side(t)
```

Then clip:

```text
real_wall_score_side(t) = clip(real_wall_score_side(t), 0.0, 1.0)
```

---

## 8.12 Spoof-like suspicion score
A **spoof-like** wall should look like:
- large when displayed,
- weakly persistent or unstable in a meaningful sense,
- strongly pulled away when approached,
- highly cancel-heavy near touch,
- weakly executable,
- optionally combined with microprice pressure distortion.

Define:

```text
spoof_suspicion_score_side(t) =
    0.25 * z01(wall_strength_side(t))
  + 0.25 * wall_pullaway_side(t)
  + 0.20 * near_touch_cancel_ratio_side(t)
  + 0.20 * (1.0 - executed_vs_displayed_side(t))
  + 0.10 * z01(abs(microprice_pressure_t))
```

Then clip:

```text
spoof_suspicion_score_side(t) = clip(spoof_suspicion_score_side(t), 0.0, 1.0)
```

### Critical language rule
This score must be named and documented as:
- **spoof-like suspicion**
- **deceptive liquidity suspicion**

It must **not** be presented as legal or conclusive spoofing detection.

---

## 8.13 Deceptive liquidity score
Define the total deceptive-liquidity score as:

```text
deceptive_liquidity_score(t) =
    max(spoof_suspicion_score_bid(t), spoof_suspicion_score_ask(t))
```

Bound already guaranteed by the per-side clip.

---

## 8.14 Dominant side

```text
dominant_side(t) =
    "bid"     if real_wall_score_bid(t) - real_wall_score_ask(t) > 0.10
    "ask"     if real_wall_score_ask(t) - real_wall_score_bid(t) > 0.10
    "neutral" otherwise
```

The 0.10 margin is a local deterministic default for this slice and must be documented as a default, not a permanent canonical threshold.

---

## 9. Reason-code policy

Reason codes must be deterministic tuples, not free prose.

Minimum supported codes:
- `micro.wall.bid.strong`
- `micro.wall.ask.strong`
- `micro.wall.bid.persistent`
- `micro.wall.ask.persistent`
- `micro.wall.bid.pullaway`
- `micro.wall.ask.pullaway`
- `micro.spoof_like.bid`
- `micro.spoof_like.ask`
- `micro.deceptive_liquidity.high`
- `micro.wall.neutral`
- `micro.snapshot.insufficient_data`
- `micro.snapshot.invalid_input`

Generation rule:
- emit only codes that correspond to actual conditions met
- output must be sorted in a deterministic stable order

---

## 10. Input validation rules

The module must reject or fail explicitly on:
- empty depth history
- negative quantities
- zero or negative prices
- best bid >= best ask without explicit stale/corrupt flag handling
- unordered timestamps
- `window_seconds <= 0`
- `window_seconds > 30`
- `top_n_levels <= 0`
- `top_n_levels > 10`

If depth/trade history is merely insufficient rather than corrupt, return a snapshot with:
- `insufficient_data=True`
- `reason_codes` containing `micro.snapshot.insufficient_data`

Do not raise on routine sparse-data cases unless the inputs are structurally invalid.

---

## 11. Feature-registry integration

Add a governed registration entry for each exposed feature in the canonical microstructure registry.
At minimum register:
- `wall_strength_bid`
- `wall_strength_ask`
- `wall_persistence_bid`
- `wall_persistence_ask`
- `wall_pullaway_bid`
- `wall_pullaway_ask`
- `near_touch_cancel_ratio_bid`
- `near_touch_cancel_ratio_ask`
- `executed_vs_displayed_bid`
- `executed_vs_displayed_ask`
- `book_shape_skew`
- `microprice_pressure`
- `real_wall_score_bid`
- `real_wall_score_ask`
- `spoof_suspicion_score_bid`
- `spoof_suspicion_score_ask`
- `deceptive_liquidity_score`

Do not create an alternate registry or a side-channel config file.

---

## 12. Intended consumers and forbidden consumers

### 12.1 Intended consumers now
- Local IA Lab feature engineering
- replay analytics
- future ML dataset builders
- SHAP analysis
- drift analysis

### 12.2 Intended consumer later
- bounded `ml_confidence_enabler`

### 12.3 Explicitly forbidden consumers in V1
- direct engine A/B/C/D hard block
- direct live kill switch
- direct live side mutation
- direct runtime sizing mutation
- direct exit trigger solely from `spoof_suspicion_score_*`

---

## 13. ML usage doctrine

This slice is designed **primarily for ML consumption**, but not as a sovereign signal.

Correct future usage:
- include the features in the Local IA Lab dataset
- allow LightGBM to learn whether real walls or deceptive liquidity improve or degrade trade survivability / continuation / mean-reversion quality
- let ML produce a bounded `ml_confidence`
- fuse that confidence additively with engine-derived score

Incorrect usage:
- `if spoof_score > x: block trade live`
- `if real_wall_score_bid > x: force long`
- hidden runtime policy outside governance

---

## 14. Test plan (mandatory, proof-oriented)

Create:
- `tests/test_data_backbone/microstructure/test_walls_and_spoofing.py`

### 14.1 Deterministic test cases

#### Case T1 — persistent real bid wall
Synthetic setup:
- repeated depth snapshots with a strong bid level at a stable price
- small changes in size within tolerance
- seller-initiated aggressive trades partially consume bid-side liquidity
- low pull-away behavior

Expected:
- `real_wall_score_bid` high
- `spoof_suspicion_score_bid` low
- `dominant_side == "bid"`

#### Case T2 — spoof-like ask wall
Synthetic setup:
- very large ask-side displayed size
- price approaches within near-touch threshold
- size disappears abruptly before meaningful buy execution
- repeated cancel-heavy episodes

Expected:
- `wall_pullaway_ask` high
- `near_touch_cancel_ratio_ask` high
- `executed_vs_displayed_ask` low
- `spoof_suspicion_score_ask` high

#### Case T3 — homogeneous book
Synthetic setup:
- evenly distributed depth across top N levels
- no dominant level
- balanced trade flow

Expected:
- wall strength near neutral
- low wall scores
- low spoof suspicion
- `dominant_side == "neutral"`

#### Case T4 — true sweep
Synthetic setup:
- aggressive trade flow consumes displayed liquidity near the wall
- no significant pull-away

Expected:
- `executed_vs_displayed_side` high
- no false spoof-like high score from pure aggression

#### Case T5 — insufficient data
Synthetic setup:
- too few depth events or too few timestamps in window

Expected:
- `insufficient_data=True`
- deterministic neutral-safe numeric outputs
- `reason_codes` contains `micro.snapshot.insufficient_data`

#### Case T6 — invalid structure
Synthetic setup:
- negative size
- best bid >= best ask
- unordered timestamps

Expected:
- explicit validation error

#### Case T7 — anti-leakage
Construct a case where future events would materially change the score if included.

Expected:
- evaluation at time `t` must ignore future events
- prove by assertion against manual calculation using only `<= t`

#### Case T8 — deterministic hash / reproducibility
Same inputs, same outputs.

Expected:
- identical score fields
- identical reason codes
- identical metadata hash behavior where applicable

### 14.2 Failure-first discipline
Where practical, structure tests so that the wrong implementation would fail for clear reasons:
- if pull-away logic ignores near-touch state, T2 should fail
- if executed-vs-displayed uses wrong side aggressor mapping, T1/T4 should fail
- if anti-leakage is broken, T7 should fail

---

## 15. Acceptance criteria

The slice is `COMPLETE` only if all of the following hold:

1. `walls_and_spoofing.py` exists in canonical microstructure package
2. all public functions are typed
3. all composite formulas match this spec
4. bounded scores are clipped into `[0, 1]`
5. anti-leakage is explicitly tested and green
6. invalid inputs are explicitly rejected
7. insufficient-data path is explicit and tested
8. registry entries are added
9. no engine file is modified
10. no runtime trade policy is changed
11. no quant-anchor files are edited
12. targeted tests are green
13. `python -m py_compile ...` passes
14. `python scripts/run_engineering_guardrails.py` reports `new_violations=0`
15. no file exceeds repo guardrail limits

If registry integration or tests are missing, status is at most `PARTIAL`.

---

## 16. Required public API sketch

Codex may refine naming slightly to match repo conventions, but the semantics must remain the same.

Preferred public function:

```python
def evaluate_walls_and_spoofing(
    *,
    pair: str,
    computed_at_ns: int,
    depth_events: Sequence[DepthEvent],
    trade_events: Sequence[AggTradeEvent],
    window_seconds: float = 5.0,
    top_n_levels: int = 5,
) -> WallsAndSpoofingSnapshot:
    ...
```

Private helpers should cover:
- input validation
- window slicing
- dominant wall extraction
- persistence computation
- near-touch episode extraction
- executed-vs-displayed mapping
- book skew computation
- microprice computation
- robust normalization helper
- reason-code builder

No god function.

---

## 17. Implementation guardrails for Codex

Codex must **not**:
- invent missing formulas
- silently change weights in composite scores
- rename outputs semantically
- turn suspicion into legal certainty
- wire this into engine runtime directly
- call this an anti-hedge-fund layer
- add deep learning
- add Optuna/trainer/runtime ML code in this slice
- use 1990s TA indicators in helper logic
- create a second feature registry
- create giant untyped dict outputs
- use `print()`
- catch broad exceptions and swallow them

Codex must:
- keep changes surgical
- reuse canonical microstructure patterns
- keep outputs frozen and audit-ready
- keep tests deterministic
- keep code reviewable and typed

---

## 18. Proof commands to run

At the end of the slice, Codex must run and report:

```bash
python -m py_compile \
  src/data_backbone/microstructure/walls_and_spoofing.py \
  tests/test_data_backbone/microstructure/test_walls_and_spoofing.py

python -m pytest \
  tests/test_data_backbone/microstructure/test_walls_and_spoofing.py -q

python scripts/run_engineering_guardrails.py
```

If registry was touched, also run:

```bash
python -m pytest \
  tests/test_data_backbone/microstructure/test_feature_registry.py -q
```

If package exports changed, run the nearest package import tests if they exist.

---

## 19. Output format required from Codex

Codex must answer with exactly these sections:

1. `Summary`
2. `Files created / modified`
3. `Mathematical formulas implemented`
4. `Validation and anti-leakage rules`
5. `Tests added`
6. `Proof results`
7. `Deferred / not done`
8. `Risks / open questions`
9. `Completion status`

The `Mathematical formulas implemented` section must explicitly restate the composite formulas for:
- `real_wall_score_side`
- `spoof_suspicion_score_side`
- `deceptive_liquidity_score`

---

## 20. Future-safe note

This slice is deliberately **bounded**.
Its real value is to create **audit-safe microstructure features** that later feed ML.

Only after replay + Shadow evidence shows economic value should the project consider any bounded runtime influence, and even then only as a **soft penalty**, never as a shadow anti-adversary fantasy layer.

---

## 21. Short Codex briefing block

Use this exact opener if helpful:

```text
You are working on module src/data_backbone/microstructure/walls_and_spoofing.py.

Global invariants:
- no new engine
- no new profile
- no VPS training
- no direct runtime hard block
- no side override
- no 1990s TA indicators
- no edits to protected quant-anchor modules
- additive feature slice only

Modules that must connect to this slice:
- src/data_backbone/microstructure/feature_registry.py via canonical registry entries
- tests/test_data_backbone/microstructure/ via deterministic unit tests
- package exports via src/data_backbone/microstructure/__init__.py and src/data_backbone/__init__.py

Forbidden defaults:
- do not invent formulas
- do not call suspicion proof-of-spoofing
- do not wire engines A/B/C/D directly
- do not create a second registry
- do not use print
- do not swallow exceptions

After generation, verify explicitly:
- anti-leakage
- bounded score clipping
- invalid-input rejection
- insufficient-data path
- deterministic outputs
- registry entries added
- tests green
- guardrails green
```

