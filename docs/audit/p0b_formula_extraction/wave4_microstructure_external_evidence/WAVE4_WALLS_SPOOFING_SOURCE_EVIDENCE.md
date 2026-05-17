# Wave 4 Walls / Spoofing Source Evidence

## Source

- Source file: `src/data_backbone/microstructure/walls_and_spoofing.py`
- Function/class:
  - `evaluate_walls_and_spoofing`
  - `_wall_strength_raw`
  - `_wall_persistence`
  - `_wall_pullaway`
  - `_near_touch_cancel_ratio`
  - `_executed_vs_displayed`
  - `_score_side_features`
  - `WallsAndSpoofingSnapshot`

## Exact code excerpts

```python
class _SideFeatures(NamedTuple):
    wall_strength: float
    wall_persistence: float
    wall_persistence_conditional: float
    wall_pullaway: float
    near_touch_cancel_ratio: float
    executed_vs_displayed: float
    real_wall_score: float
    spoof_suspicion_score: float
```

```python
return (
    _clip(
        (0.35 * wall_strength_z01)
        + (0.35 * persistence)
        + (0.20 * executed_vs_displayed)
        - (0.10 * wall_pullaway)
    ),
    _clip(
        (0.25 * wall_strength_z01)
        + (0.25 * wall_pullaway)
        + (0.20 * near_touch_cancel_ratio)
        + (0.20 * (1.0 - executed_vs_displayed))
        + (0.10 * microprice_pressure_z01)
    ),
)
```

```python
deceptive_liquidity_score = max(bid.spoof_suspicion_score, ask.spoof_suspicion_score)
```

```python
if len(window_depth) < 2 or not _has_full_top_n_depth(window_depth, top_n_levels=top_n_levels):
    return _insufficient_snapshot(...)
```

## Implemented formulas in plain text

- Wall strength:
  - dominant level size relative to mean visible size over top-N levels
- Persistence:
  - active wall span over observed span
- Conditional persistence:
  - persistence over intervals where wall observations exist
- Pullaway:
  - fraction of near-touch drops where displayed size falls by `cancel_drop_ratio` and executed volume stays below dropped size
- Near-touch cancel ratio:
  - cancelled displayed size / displayed size
- Executed vs displayed:
  - executed trade volume against the wall / displayed wall size
- Real wall score:
  - bounded weighted combination of wall strength, persistence, executed-vs-displayed, and inverse pullaway
- Spoof-like suspicion:
  - bounded weighted combination of wall strength, pullaway, near-touch cancel ratio, inverse executed-vs-displayed, and microprice-pressure term
- Deceptive liquidity:
  - `max(spoof_suspicion_bid, spoof_suspicion_ask)`

## Inputs / outputs / window / future handling

- Input variables:
  - ordered depth events
  - ordered agg trades
  - `window_seconds`
  - `top_n_levels`
  - `computed_at_ns`
- Output variable:
  - `WallsAndSpoofingSnapshot`
- Units:
  - most outputs are bounded scores `0..1`
  - `microprice_pressure` retains signed pressure scale
- Window:
  - rolling time window via `window_seconds`
- Future-event handling:
  - windowing helper filters to `timestamp_ns <= computed_at_ns`
- Insufficient-data behavior:
  - returns explicit insufficient snapshot with reason code `micro.snapshot.insufficient_data`

## Consumers

- `src/data_backbone/microstructure/lob_regime_features.py`
  - runtime LOB regime bundle carries:
    - `wall_strength_*`
    - `wall_persistence_*`
    - `wall_pullaway_*`
    - `near_touch_cancel_ratio_*`
    - `executed_vs_displayed_*`
    - `real_wall_score_*`
    - `spoof_like_suspicion_*`
    - `deceptive_liquidity_score`
- Feature registry claimed consumers:
  - `local_replay_runtime`
  - `meta_learning`
  - `complete_enablers.regime_detector_runtime`

## Tests

- `tests/test_data_backbone/microstructure/test_walls_and_spoofing.py`
  - `assert snapshot.insufficient_data is False`
  - `assert "micro.wall.bid.strong" in snapshot.reason_codes`
  - `assert "micro.spoof_like.ask" in snapshot.reason_codes`
  - `assert snapshot.reason_codes == ("micro.snapshot.insufficient_data",)`

## Classification / external questions

- Classifications:
  - `EVIDENCE_EXTRACTED`
  - `TEST_COVERED`
  - `REGIME_CONTEXT_INPUT`
  - `RUNTIME_CONSUMED`
- External-audit questions:
  - Should external audit treat `real_wall_score` and `spoof_suspicion_score` as runtime heuristics only, or require a separate calibration note because the weights are explicitly hand-set in `_score_side_features`?
