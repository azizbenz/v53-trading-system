# Walls / Spoofing Calibration Note

## Current status

- `real_wall_score_method = HEURISTIC_WEIGHTED_SCORE`
- `spoof_suspicion_score_method = HEURISTIC_WEIGHTED_SCORE`
- `calibration_status = CALIBRATION_REQUIRED_FOR_STRONG_PRODUCTION_CLAIM`

These scores are bounded heuristics. They are admissible as context, not as empirically calibrated production claims.

## Current weights

### Real-wall proxy

`real_wall_score = clip(0.35 * wall_strength_z01 + 0.35 * persistence + 0.20 * executed_vs_displayed - 0.10 * wall_pullaway)`

Interpretation:
- higher wall strength increases real-wall confidence
- higher persistence increases real-wall confidence
- higher executed-vs-displayed increases real-wall confidence
- higher pullaway reduces real-wall confidence

### Spoof-like proxy

`spoof_suspicion_score = clip(0.25 * wall_strength_z01 + 0.25 * wall_pullaway + 0.20 * near_touch_cancel_ratio + 0.20 * (1 - executed_vs_displayed) + 0.10 * microprice_pressure_z01)`

Interpretation:
- strong displayed wall can still contribute to spoof suspicion
- pullaway near touch increases suspicion
- near-touch cancel ratio increases suspicion
- low executed-vs-displayed increases suspicion
- microprice pressure acts as a bounded context term

## Proxy definitions

### Real-wall proxy

The current real-wall score is a heuristic proxy for displayed liquidity that both persists and attracts actual executions rather than disappearing near touch.

### Spoof-like proxy

The current spoof-like score is a heuristic proxy for displayed liquidity that weakens or disappears near touch without a matching execution footprint.

## Pullaway interpretation

`wall_pullaway` is a bounded ratio of near-touch drops where displayed size falls sharply without matching executed volume. It is not a proven spoofing label by itself.

## Executed-vs-displayed interpretation

`executed_vs_displayed` is a bounded ratio of executed volume near the wall price relative to displayed size during the observed near-touch drop intervals. It is an execution-footprint proxy, not a venue-confirmed queue-fill measure.

## Limitations

- weights are hand-set
- no per-pair empirical calibration artifact is attached
- no OOS precision/false-positive study is attached
- no live venue-specific queue-position ground truth is attached
- no formal classifier training artifact is attached

## Calibration dataset requirements

Required future calibration datasets should include:
- per-pair depth20 event windows
- synchronized aggTrade windows
- near-touch wall episodes
- executed volume against wall proxy
- holdout splits by time and pair
- regime tags where available

## Required future metrics

- pullaway distribution
- persistence distribution
- executed_vs_displayed distribution
- false positive proxy
- precision proxy

## Why the status remains heuristic

The current scores are bounded and operationally useful as context, but they are not empirically calibrated enough to claim strong production detection quality. Until pair-level validation and OOS error characterization exist, the correct status remains `HEURISTIC_WEIGHTED_SCORE` plus `CALIBRATION_REQUIRED_FOR_STRONG_PRODUCTION_CLAIM`.
