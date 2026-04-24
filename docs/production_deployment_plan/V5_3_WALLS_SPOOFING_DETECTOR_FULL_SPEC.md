# V5.3 — Walls + Spoofing Detector — Full Detailed Spec for Codex

**Status**: EXECUTION-READY SPEC (bounded V2 microstructure slice)  
**Parent canon**: V5.3  
**Companion docs**: 19, 20, 23, 24, 28, Local IA Lab / VPS separation  
**Primary role**: produce **audit-ready microstructure features** for the **Local IA Lab** and for the future `ml_confidence_enabler`  
**Not allowed to become**: a new engine, a sovereign live blocker, or an “anti-adversary platform”

---

## 0. One-line doctrine

> **Le système doit lire la profondeur réelle et la liquidité trompeuse, mais il ne doit pas se fantasmer en plateforme anti-adversaire avant d’avoir une preuve que ce risque est économiquement pertinent.**

This slice exists to measure:
- where the book shows **real, persistent liquidity**,
- where the book shows **fragile or deceptive displayed liquidity**,
- where a visible wall is likely **consumable**,
- where a visible wall is likely **pulling away before contact**.

It does **not** attempt to prove illegal spoofing in a legal/forensic sense. It only produces a **spoof-like suspicion score** and related wall-quality features.

---

## 1. Why this slice exists

The current V5.3 microstructure canon already formalizes OFI, VPIN, Kyle λ, PIN, queue pressure, realized kernel volatility, spread metrics, and book geometry. What is still missing as a bounded V2 layer is a **focused detector of displayed-vs-real liquidity quality**:

1. **Real wall**: a large, persistent, partially executable wall that genuinely matters.
2. **Decorative wall**: a large displayed wall that collapses when price approaches.
3. **Spoof-like pattern**: displayed liquidity that appears influential but is withdrawn before meaningful interaction.
4. **Book fragility context**: the book may look supportive but may not be trustworthy.

This slice is justified because:
- walls and near-touch liquidity matter economically,
- this information can improve the **ML confidence layer**,
- but the project explicitly rejected overbuilt anti-exploitation / anti-agent systems for the current capital scale.

---

## 2. Scope

### 2.1 Included

- A new bounded microstructure calculator under `src/data_backbone/microstructure/`
- Event-driven and short-window book/trade analysis using `depth20` + `aggTrades`
- Typed frozen output
- Registry integration into the canonical microstructure registry
- Unit tests with deterministic synthetic scenarios
- Local-Lab-first usage
- Future use as **feature input** to `ml_confidence_enabler`

### 2.2 Explicitly excluded

- No new engine
- No live-side autonomous anti-spoof execution logic
- No direct hard block in VPS runtime from this slice
- No training on VPS
- No deep learning over raw order book in this slice
- No legal/market-abuse claim of “spoofing proof”
- No rewrite of OFI / VPIN / Kyle λ / queue pressure modules already present

---

## 3. Strategic placement in V5.3

### 3.1 Correct place in the architecture

This slice belongs in the **microstructure data backbone**, not in an engine and not in a top-level anti-agent package.

### 3.2 Intended consumption order

1. **Compute features locally** from raw `depth20` + `aggTrades`
2. Store / replay / inspect them in the Local IA Lab
3. Use them in dataset building for ML
4. Let the ML enabler learn whether they improve signal quality
5. Only much later, if evidence is strong, consider a bounded runtime soft-penalty consumer

### 3.3 Not the intended use

Do **not** do this now:
- `if spoof_score > x: block live trade`
- `if wall_score > y: override engine side`
- `if deceptive_liquidity_score high: auto-exit position`

Those uses require a later doctrinal and shadow-backed decision.

---

## 4. Code placement

### 4.1 Main file to create

`src/data_backbone/microstructure/walls_and_spoofing.py`

### 4.2 Files to extend

- `src/data_backbone/microstructure/__init__.py`
- `src/data_backbone/__init__.py`
- `src/data_backbone/microstructure/feature_registry.py`
- optionally dataset builder files in the Local IA Lab / calibration side later, but **not in this slice**

### 4.3 Optional contract file

Only if the repo style clearly benefits from a separate typed contract:
- `src/interface_contracts/walls_and_spoofing_contracts.py`

Default preference:
- keep the frozen record directly inside `walls_and_spoofing.py`, matching the existing microstructure calculator style

---

## 5. Hard invariants

These are non-negotiable.

1. **No new engine** is created.
2. **No VPS training** is introduced.
3. This slice must remain **Local-Lab-first**.
4. It must produce **features**, not sovereign decisions.
5. It must reuse the **canonical microstructure registry**.
6. It must be computed using only data `<= t` for timestamp `t`.
7. It must not consume future book/trade information.
8. It must not be described as “spoofing proof”; only as **spoof-like suspicion**.
9. File size must remain compatible with repo engineering caps.
10. No god functions, no untyped outputs, no print, no silent fallbacks.

---

## 6. Data sources and alignment rules

### 6.1 Input sources

#### A. `depth20`
Book snapshots / book events containing the top 20 bid and ask levels.

Expected information per event:
- timestamp in ns
- bid prices and sizes for levels 1..20
- ask prices and sizes for levels 1..20

#### B. `aggTrades`
Aggressive trade flow:
- timestamp in ns
- price
- quantity
- aggressor side inference or available buy/sell flag

### 6.2 Allowed processing modes

- **event-driven** mode
- **short resampled mode**, default `1s`

### 6.3 Forbidden processing mode for this slice

- coarse candle-only computation
- 1-minute-only approximation

### 6.4 Time alignment rule

For every output computed at time `t`:
- use only depth and trade events with timestamp `<= t`
- if data is missing near `t`, degrade explicitly or return missing state
- never align with future events

### 6.5 Default short window

- default analysis window: `5s`
- hard cap: `30s`

Rationale:
spoof-like behavior is a short-lived event microstructure phenomenon; too wide a window blurs the effect.

---

## 7. Canonical typed output

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class WallsAndSpoofingSnapshot:
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
    reason_codes: tuple[str, ...]
    input_data_hash: str
    method_version_hash: str
```

### 7.1 Output constraints

- all scores must be finite floats
- bounded scores must be clipped explicitly
- `dominant_side` must be deterministic
- `reason_codes` must be machine-stable
- output must remain reproducible for same inputs

---

## 8. Mathematical definitions

### 8.1 Common constants

```text
eps = 1e-12
N_top = 5              # default top-N wall analysis depth
N_top_hard_cap = 10
touch_eps_bps = 2      # default near-touch distance
cancel_drop_ratio = 0.70
size_tolerance_ratio = 0.20
```

These defaults may later migrate into calibration seams, but **do not build a calibration loader dependency in this slice**.

---

### 8.2 Basic book variables

At time `t`:

- `best_bid_t` = highest bid price at level 1
- `best_ask_t` = lowest ask price at level 1
- `mid_t = (best_bid_t + best_ask_t) / 2`
- `spread_t = best_ask_t - best_bid_t`
- `depth_bid_k_t` = quantity displayed at bid level `k`
- `depth_ask_k_t` = quantity displayed at ask level `k`
- `price_bid_k_t` = price at bid level `k`
- `price_ask_k_t` = price at ask level `k`

The analysis window is `W = [t - Δ, t]`.

---

### 8.3 Dominant local wall level per side

For each side, define the dominant local wall as the level among top-N with the largest displayed depth at time `t`.

```text
k*_bid_t = argmax_{k in 1..N_top} depth_bid_k_t
k*_ask_t = argmax_{k in 1..N_top} depth_ask_k_t
```

Then:

```text
wall_level_price_bid_t = price_bid_k*_bid_t
wall_level_price_ask_t = price_ask_k*_ask_t
wall_level_size_bid_t  = depth_bid_k*_bid_t
wall_level_size_ask_t  = depth_ask_k*_ask_t
```

---

### 8.4 Wall strength

Measures how unusually large the dominant wall is relative to the surrounding top-N structure.

```text
mean_depth_bid_topN_t = mean(depth_bid_1_t, ..., depth_bid_N_t)
mean_depth_ask_topN_t = mean(depth_ask_1_t, ..., depth_ask_N_t)

wall_strength_bid_t = wall_level_size_bid_t / (mean_depth_bid_topN_t + eps)
wall_strength_ask_t = wall_level_size_ask_t / (mean_depth_ask_topN_t + eps)
```

Interpretation:
- around `1.0`: no strong wall
- clearly above `1.0`: local wall-like concentration

This is a raw ratio, not yet a probability.

---

### 8.5 Wall persistence

A real wall is not just large once; it must persist.

For the dominant wall level at time `t`, define persistence over `W` as the fraction of the window during which the wall remains at the same side and same price, with depth still positive and with acceptable relative size drift.

For the bid side:

```text
wall_persistence_bid_t =
    time_in_window_where(
        price_bid_k == wall_level_price_bid_t
        AND depth_bid_at_that_price > 0
        AND abs(depth_bid_at_that_price - wall_level_size_bid_reference)
            / (wall_level_size_bid_reference + eps)
            <= size_tolerance_ratio
    ) / window_seconds
```

Same for ask.

Range: `[0, 1]`

---

### 8.6 Near-touch event definition

A wall is “near-touch” if the mid price or best opposing price approaches the wall within a small bps distance.

For bid wall:

```text
near_touch_bid if
    abs(mid_t - wall_level_price_bid_t) / (mid_t + eps) * 10_000 <= touch_eps_bps
```

For ask wall:

```text
near_touch_ask if
    abs(wall_level_price_ask_t - mid_t) / (mid_t + eps) * 10_000 <= touch_eps_bps
```

Equivalent side-specific implementation using best ask / best bid is acceptable if applied consistently and documented.

---

### 8.7 Pull-away ratio

A deceptive wall often disappears when price gets too close.

Count near-touch episodes in `W`. A pull-away episode occurs when:
1. a near-touch condition is satisfied,
2. displayed wall size drops by more than `cancel_drop_ratio`,
3. this drop is not matched by meaningful aggressive execution against that wall.

For each side:

```text
wall_pullaway_side_t =
    near_touch_pullaway_episodes_side
    / (near_touch_episodes_side + eps)
```

Range: `[0, 1]`

Interpretation:
- high = the wall tends to retreat before actual interaction

---

### 8.8 Near-touch cancel ratio

Measures how much displayed liquidity disappears when price gets close.

```text
near_touch_cancel_ratio_side_t =
    cancelled_volume_near_touch_side
    / (displayed_volume_near_touch_side + eps)
```

Where:
- `cancelled_volume_near_touch_side` is the decrease in displayed wall-side volume that is not explained by executed aggressive flow against that side
- `displayed_volume_near_touch_side` is the total visible wall-side depth observed during near-touch episodes

Range: `[0, 1]`

---

### 8.9 Executed-vs-displayed ratio

A real wall should be at least partially executable.

For bid walls, use seller-aggressive trades that hit the bid side.  
For ask walls, use buyer-aggressive trades that hit the ask side.

```text
executed_vs_displayed_side_t =
    executed_volume_against_wall_side
    / (displayed_wall_volume_side + eps)
```

Range should be clipped to `[0, 1]` for scoring use:

```text
executed_vs_displayed_side_t = clip(executed_vs_displayed_side_t, 0.0, 1.0)
```

Interpretation:
- high = visible liquidity is genuinely hit / consumed
- low = visible liquidity is mostly decorative or never reachable

---

### 8.10 Book shape skew

We want a geometry signal indicating whether the local book is top-heavy, tilted, or asymmetrically distributed.

Define for each side the level price offsets from `mid_t`:

```text
x_k_bid = price_bid_k_t - mid_t
x_k_ask = price_ask_k_t - mid_t
```

Weights:

```text
w_k_bid = depth_bid_k_t / (sum_{j=1..N_top} depth_bid_j_t + eps)
w_k_ask = depth_ask_k_t / (sum_{j=1..N_top} depth_ask_j_t + eps)
```

Weighted mean and weighted standard deviation:

```text
mean_x_bid = sum_k(w_k_bid * x_k_bid)
mean_x_ask = sum_k(w_k_ask * x_k_ask)

std_x_bid = sqrt(sum_k(w_k_bid * (x_k_bid - mean_x_bid)^2) + eps)
std_x_ask = sqrt(sum_k(w_k_ask * (x_k_ask - mean_x_ask)^2) + eps)
```

Then define side skew proxies:

```text
obs_skew_bid = mean_x_bid / (std_x_bid + eps)
obs_skew_ask = mean_x_ask / (std_x_ask + eps)
```

Aggregate into one bounded geometry signal if needed:

```text
book_shape_skew = obs_skew_ask - obs_skew_bid
```

This keeps a directional notion of book asymmetry.

---

### 8.11 Microprice pressure

Microprice already fits the book-truth vs displayed-liquidity logic.

```text
microprice_t =
    (best_ask_t * depth_bid_1_t + best_bid_t * depth_ask_1_t)
    / (depth_bid_1_t + depth_ask_1_t + eps)

microprice_pressure_t =
    (microprice_t - mid_t) / (mid_t + eps)
```

Interpretation:
- positive = microprice biased upward
- negative = microprice biased downward

---

## 9. Score construction

### 9.1 Normalization note

When raw features like `wall_strength_side` need to enter a bounded score, use a stable local normalization.

Recommended helper:
- robust z-score over a larger rolling history using median / MAD,
- fallback to clipped centered ratio if insufficient history,
- no future leakage.

You may implement a small internal helper such as `_robust_rescale_feature(...)` if the repo does not already provide a canonical bounded rescaler in the microstructure layer.

---

### 9.2 Real wall score

A real wall should be:
- strong,
- persistent,
- not systematically pulling away,
- at least partially executable.

Recommended score:

```text
real_wall_score_side =
    0.35 * z(wall_strength_side)
  + 0.35 * wall_persistence_side
  + 0.20 * executed_vs_displayed_side
  - 0.10 * wall_pullaway_side
```

Then:

```text
real_wall_score_side = clip(real_wall_score_side, 0.0, 1.0)
```

If no robust z-normalization is safely available, use a monotone bounded transform on `wall_strength_side` that is deterministic and documented.

---

### 9.3 Spoof-like suspicion score

A spoof-like pattern should show:
- large visible size,
- low trusted persistence,
- high withdrawal near contact,
- high cancellation ratio near contact,
- weak actual execution,
- possibly abnormal microprice pressure relative to displayed shape.

Recommended score:

```text
spoof_suspicion_score_side =
    0.25 * z(wall_strength_side)
  + 0.25 * wall_pullaway_side
  + 0.20 * near_touch_cancel_ratio_side
  + 0.20 * (1.0 - executed_vs_displayed_side)
  + 0.10 * z(abs(microprice_pressure_t))
```

Then:

```text
spoof_suspicion_score_side = clip(spoof_suspicion_score_side, 0.0, 1.0)
```

### 9.4 Important naming rule

This score **must** be named and documented as:
- `spoof_suspicion_score_*`
- or `spoof_like_suspicion_score_*`

It must **not** be named:
- `spoofing_detected`
- `spoofing_proof`
- `is_spoofer`

---

### 9.5 Global deceptive liquidity score

The system only needs a side-agnostic summary for ML if desired.

```text
deceptive_liquidity_score =
    max(spoof_suspicion_score_bid, spoof_suspicion_score_ask)
```

Alternative weighted aggregation is allowed only if documented and deterministic.

---

### 9.6 Dominant side

```text
if real_wall_score_bid - real_wall_score_ask > 0.10:
    dominant_side = "bid"
elif real_wall_score_ask - real_wall_score_bid > 0.10:
    dominant_side = "ask"
else:
    dominant_side = "neutral"
```

The threshold `0.10` is a local bounded heuristic for this slice. Keep it module-local and explicit.

---

## 10. Reason code policy

Reason codes must be deterministic, short, and machine-oriented.

### 10.1 Allowed examples

- `micro.wall.bid.strong`
- `micro.wall.ask.strong`
- `micro.wall.bid.persistent`
- `micro.wall.ask.persistent`
- `micro.wall.bid.pullaway`
- `micro.wall.ask.pullaway`
- `micro.spoof_like.bid`
- `micro.spoof_like.ask`
- `micro.deceptive_liquidity.high`
- `micro.book.neutral`

### 10.2 Forbidden reason-code style

- natural-language sentences
- unstable free-form explanations
- logs masquerading as reason codes

### 10.3 Determinism rule

For identical inputs and identical thresholds, the reason-code tuple must be identical.

---

## 11. Registry integration

### 11.1 Add the following feature specs to the canonical microstructure registry

At minimum:
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

### 11.2 Promotion ladder position

These features should initially be registered as:
- research / candidate / local-only feature specs

They must not be marked as a direct runtime production dependency in this slice.

---

## 12. Intended ML usage

### 12.1 Primary intended use

These outputs are meant primarily as **inputs to the Local-Lab ML dataset** and later to the `ml_confidence_enabler`.

### 12.2 Correct ML role

The ML may learn patterns such as:
- continuation setups are weaker when visible liquidity is deceptive,
- mean-reversion setups are stronger when a real executable wall exists,
- wall persistence helps distinguish real support from decorative support,
- pull-away behavior correlates with failed continuation attempts.

### 12.3 Wrong ML role

Do **not** make the ML:
- decide side independently,
- replace engine A/B/C/D,
- consume this detector as a sovereign live blocker,
- retrain or adjust this logic on VPS.

---

## 13. Runtime usage policy for this slice

### 13.1 Allowed now

- Local IA Lab computation
- Dataset building
- Replay and research
- SHAP / feature-importance analysis
- Drift analysis
- Local dashboards / reports

### 13.2 Not allowed now

- hard live trade rejection on VPS
- direct runtime stop-loss trigger
- direct automatic reduction of exposure from this detector alone
- side mutation
- size mutation

If later evidence supports a live consumer, the correct first step is a **soft penalty** or **confidence modulation**, not a hard block.

---

## 14. Engineering guidance for implementation

### 14.1 File structure

Keep the module under the file cap.

Suggested shape:
- public frozen snapshot dataclass
- one public calculator entry point
- small private helpers:
  - `_validate_depth_snapshot(...)`
  - `_resolve_dominant_wall_levels(...)`
  - `_compute_wall_strength(...)`
  - `_compute_wall_persistence(...)`
  - `_compute_near_touch_metrics(...)`
  - `_compute_executed_vs_displayed(...)`
  - `_compute_book_shape_skew(...)`
  - `_compute_microprice_pressure(...)`
  - `_compute_real_wall_score(...)`
  - `_compute_spoof_suspicion_score(...)`
  - `_build_reason_codes(...)`

### 14.2 Keep functions short

No function should become a god function. Decompose aggressively.

### 14.3 Errors

Invalid input should fail explicitly:
- empty book
- unsorted prices
- negative depth
- impossible spread
- inconsistent timestamps

### 14.4 No fake precision

If trade-side attribution is ambiguous, the calculator must either:
- use the repo’s canonical trade-side convention,
- or fail explicitly,
- or accept a pre-attributed trade stream.

It must not invent certainty.

---

## 15. Tests to add

Create:

`tests/test_data_backbone/microstructure/test_walls_and_spoofing.py`

### 15.1 Required scenarios

#### Test 1 — Real persistent bid wall

Synthetic setup:
- large bid wall persists in top-5
- price approaches
- some seller-aggressive trades hit it
- wall remains partially present

Expected:
- `wall_strength_bid` high
- `wall_persistence_bid` high
- `executed_vs_displayed_bid` moderate to high
- `real_wall_score_bid` high
- `spoof_suspicion_score_bid` low

#### Test 2 — Pull-away ask wall (spoof-like)

Synthetic setup:
- large ask wall appears near price
- price approaches within near-touch threshold
- wall size collapses sharply
- little actual buyer-aggressive execution occurs

Expected:
- `wall_pullaway_ask` high
- `near_touch_cancel_ratio_ask` high
- `executed_vs_displayed_ask` low
- `spoof_suspicion_score_ask` high

#### Test 3 — Homogeneous book

Synthetic setup:
- balanced depth across levels
- no dominant level

Expected:
- low wall scores
- low spoof suspicion
- `dominant_side == "neutral"`

#### Test 4 — Real sweep, not spoof-like

Synthetic setup:
- large ask level exists
- large buyer-aggressive trade truly consumes visible depth

Expected:
- `executed_vs_displayed_ask` high
- pullaway low
- spoof suspicion not spuriously high

#### Test 5 — Invalid inputs

Cases:
- negative depth
- crossed book
- zero or negative prices
- empty levels

Expected:
- explicit validation error

#### Test 6 — Anti-leakage timestamp discipline

Construct events before and after `t`.

Expected:
- only events `<= t` contribute
- post-`t` events do not change output

#### Test 7 — Determinism

Run same inputs twice.

Expected:
- exact same output values
- exact same reason codes
- same hash fields if computed from same inputs

---

## 16. Acceptance criteria

This slice is `COMPLETE` only if all of the following are true:

1. `walls_and_spoofing.py` exists in canonical microstructure placement.
2. Frozen typed output exists.
3. All formulas described above are implemented or transparently documented if a minor bounded substitution is needed.
4. Full targeted tests are green.
5. Registry entries were added without creating a second registry.
6. No engines A/B/C/D were modified in this slice.
7. No live runtime hard block was introduced.
8. No future leakage exists.
9. Guardrails remain green.
10. The slice is auditable and bounded.

---

## 17. Explicit prohibitions for Codex

Codex must not:

1. invent a new engine
2. create a top-level anti-agent package
3. call this “spoofing proof”
4. introduce live hard-block logic based only on these scores
5. override side / bet structure / forecast contracts
6. retrain anything on VPS
7. use torch / deep learning in this slice
8. rewrite existing OFI / VPIN / Kyle λ / queue pressure modules
9. introduce RSI / MACD / Bollinger or any 1990s TA dependency
10. leave formulas half-defined
11. create giant files or giant functions
12. silently absorb invalid data

---

## 18. Order of implementation

### Step 1
Create the file and frozen output type.

### Step 2
Implement pure helper math on synthetic inputs.

### Step 3
Implement the public calculator entry point.

### Step 4
Add registry entries.

### Step 5
Write deterministic tests for the 7 scenarios.

### Step 6
Run py_compile + targeted pytest + guardrails.

### Step 7
Do **not** wire to runtime engines in this slice.

---

## 19. Suggested public API

```python
from __future__ import annotations


def compute_walls_and_spoofing_snapshot(
    *,
    pair: str,
    computed_at_ns: int,
    depth_events: list[DepthEvent],
    aggressive_trades: list[AggressiveTrade],
    window_seconds: float = 5.0,
    top_n_levels: int = 5,
) -> WallsAndSpoofingSnapshot:
    """Compute bounded wall-quality and spoof-like suspicion features.

    Args:
        pair: Symbol / pair id.
        computed_at_ns: Snapshot evaluation timestamp.
        depth_events: Depth20 events with timestamps <= computed_at_ns.
        aggressive_trades: Aggressive trades with timestamps <= computed_at_ns.
        window_seconds: Backward-looking analysis window.
        top_n_levels: Top-N levels to analyze.

    Returns:
        A frozen WallsAndSpoofingSnapshot.
    """
```

The exact input types may adapt to repo-native conventions, but the public behavior must remain explicit and typed.

---

## 20. Brief Codex opening message

Use this at the start of the Codex session:

```text
You are working on module src/data_backbone/microstructure/walls_and_spoofing.py.

Global invariants:
- no new engine
- no VPS training
- no runtime hard block from this slice
- no side override
- additive microstructure feature slice only
- must reuse canonical microstructure registry
- no future leakage
- outputs must be typed, frozen, deterministic, and audit-ready

Modules that must connect to this slice:
- src/data_backbone/microstructure/feature_registry.py via canonical feature registration
- src/data_backbone/microstructure/__init__.py and src/data_backbone/__init__.py via exports
- tests/test_data_backbone/microstructure/test_walls_and_spoofing.py via deterministic proofs

Forbidden defaults:
- do not create a new engine
- do not call the output spoofing proof
- do not add live runtime hard blocks
- do not modify engines A/B/C/D
- do not use deep learning
- do not rewrite OFI/VPIN/Kyle lambda modules
- do not leave formulas partially specified

After generation, verify explicitly:
- anti-leakage respected
- deterministic outputs
- registry updated
- no engine changes
- no runtime hard block introduced
- targeted tests green
- engineering guardrails green
```

---

## 21. Final strategic note

This slice is valuable because it measures **whether the book is telling the truth** about visible liquidity.

That is economically relevant.

What would be a mistake is to escalate that immediately into a theory that “the system must become an anti-agent platform.” The current capital scale, doctrine, and architecture do not justify that escalation. This detector should therefore stay where it belongs:

- in the **microstructure feature layer**,
- feeding the **Local-Lab ML and diagnostics**,
- and only later, if shadow evidence supports it, perhaps a bounded score penalty.

That is the correct V5.3 posture.
