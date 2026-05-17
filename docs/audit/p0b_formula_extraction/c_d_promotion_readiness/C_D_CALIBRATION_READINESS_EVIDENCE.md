# C/D Calibration Readiness Evidence

## Engine C Thresholds

| Threshold | Status | Evidence |
|---|---|---|
| VPIN threshold | `PROVEN_CONFIGURED`, `PROVEN_TESTED` | `THR-C_VPIN_MAX`; `test_engine_c_continuation_thresholds.py` |
| Kyle lambda threshold | `PROVEN_CONFIGURED`, `PROVEN_TESTED` | optional runtime artifact key `EC-KYLE-LAMBDA-MAX-01`; tested in `test_engine_c_continuation_thresholds.py` |
| OFI threshold | `PROVEN_CONFIGURED`, `PROVEN_TESTED` | `THR-C_OFI_MIN`; continuation threshold tests |
| queue pressure threshold | `PROVEN_CONFIGURED`, `PROVEN_TESTED` | `THR-C_QUEUE_MIN`; continuation threshold tests |
| false breakout threshold | `PROVEN_CONFIGURED` | local runner threshold `fake_breakout_risk_max`; no dedicated calibration artifact proved in this pack |
| continuation threshold | `PROVEN_CONFIGURED`, `PROVEN_TESTED` | local `score_min` / `extension_pct_max`; validator boundary tests |
| `ce_min_C` | `PROVEN_CONFIGURED`, `PROVEN_TESTED` | `THR-E03`; cost threshold tests |
| `delta_safe_C` | `PROVEN_CONFIGURED`, `PROVEN_TESTED` | `THR-E04`; cost threshold tests |
| cost feasibility threshold | `PROVEN_TESTED` | `test_cost_feasibility_c.py` |
| sample-size survival threshold | `MISSING`, `BLOCKED_BY_SHADOW` | no per-engine survival artifact found |

## Engine D Thresholds

| Threshold | Status | Evidence |
|---|---|---|
| `THR-X10` anti-revenge cooldown failsafe | `PROVEN_CONFIGURED`, `PROVEN_TESTED` | `test_engine_d_coordination_thresholds.py` |
| `THR-X11` max consecutive re-entries before reset | `PROVEN_CONFIGURED`, `PROVEN_TESTED` | `test_engine_d_coordination_thresholds.py` |
| re-entry age threshold | `PROVEN_CONFIGURED`, `PROVEN_TESTED` | `THR-D_MIN_GAP` in first-episode threshold tests |
| reformation score threshold | `MISSING` | no dedicated threshold artifact or local floor proved |
| history score threshold | `MISSING` | no dedicated threshold artifact or local floor proved |
| marginal value threshold | `PROVEN_CONFIGURED`, `PROVEN_TESTED` | `THR-D_MARGINAL_VALUE_SCORE_MIN`; marginal-value tests |
| `ce_min_D` | `PROVEN_CONFIGURED`, `PROVEN_TESTED` | Engine D cost threshold resolver tests |
| `delta_safe_D` | `PROVEN_CONFIGURED`, `PROVEN_TESTED` | Engine D cost threshold resolver tests |
| cost feasibility threshold | `PROVEN_TESTED` | `test_cost_feasibility_d.py` |
| stale signal threshold | `MISSING` | no explicit `stale_signal_score` or threshold proved |
| sample-size survival threshold | `MISSING`, `BLOCKED_BY_SHADOW` | no per-engine survival artifact found |

## Important Excerpts

```text
src/engines/engine_c/continuation_validator_c.py
  THR-C_OFI_MIN
  THR-C_QUEUE_MIN
  THR-C_VPIN_MAX

src/engines/engine_c/cost_feasibility_c.py
  THR-E03
  THR-E04

src/engines/engine_d/first_episode_resolver_d.py
  THR-D_LOOKBACK
  THR-D_MIN_GAP

src/engines/engine_d/marginal_value_estimator_d.py
  THR-D_MARGINAL_VALUE_SCORE_MIN

tests/test_scoring_backbone/test_engine_d_coordination_thresholds.py
  THR-X10
  THR-X11
```

## Conclusion

- Calibration ownership for C and D is real and typed.
- Engine C is stronger on directly named microstructure thresholds.
- Engine D is stronger on coordination / anti-revenge / first-episode threshold governance.
- Both engines still lack per-engine sample-size survival / promotion thresholds.

