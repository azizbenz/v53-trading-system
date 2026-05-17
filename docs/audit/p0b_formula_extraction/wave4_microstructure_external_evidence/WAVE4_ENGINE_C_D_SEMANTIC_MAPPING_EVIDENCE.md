# Wave 4 Engine C / D Semantic Mapping Evidence

## Engine C doctrine evidence

Engine C is not a generic A/B-style shared-scoring carrier. The traced microstructure seam is continuation / breakout / fake-breakout protection.

### Exact code excerpts

```python
ENGINE_C_MICROSTRUCTURE_MISSING_REASON = "engine_internal.c.microstructure_missing"
ENGINE_C_OFI_PERSISTENCE_REASON = "engine_internal.c.ofi_persistence"
ENGINE_C_QUEUE_PRESSURE_REASON = "engine_internal.c.queue_pressure"
ENGINE_C_VPIN_TOXIC_REASON = "engine_internal.c.vpin_toxic"
ENGINE_C_KYLE_LAMBDA_REASON = "engine_internal.c.kyle_lambda_excessive"
```

```python
if inputs.cumulative_ofi is not None and inputs.cumulative_ofi < inputs.ofi_min:
    reason_codes.append(ENGINE_C_OFI_PERSISTENCE_REASON)
if inputs.queue_pressure is not None and inputs.queue_pressure < inputs.queue_min:
    reason_codes.append(ENGINE_C_QUEUE_PRESSURE_REASON)
if inputs.vpin is not None and inputs.vpin_max is not None and inputs.vpin > inputs.vpin_max:
    reason_codes.append(ENGINE_C_VPIN_TOXIC_REASON)
if (
    inputs.kyle_lambda is not None
    and inputs.kyle_lambda_max is not None
    and inputs.kyle_lambda > inputs.kyle_lambda_max
):
    reason_codes.append(ENGINE_C_KYLE_LAMBDA_REASON)
```

```python
if realized_vol_at_break is not None and realized_vol_at_break > 0.0:
    return realized_vol_at_break, "realized_vol_at_break"
if realized_vol_current is not None and realized_vol_current > 0.0:
    return realized_vol_current, "realized_vol_current_fallback"
```

## Engine C traced meaning

- `cumulative_ofi`:
  - continuation persistence
- `queue_pressure`:
  - continuation support / fake-breakout protection
- `vpin`:
  - toxic-flow veto
- `kyle_lambda`:
  - excessive impact veto
- `realized_vol_current` / `realized_vol_at_break`:
  - breakout invalidation and forecast volatility proxy

## Engine D doctrine evidence

Engine D is re-entry / first-episode / anti-revenge / reformation oriented, not an A/B shared-physics clone.

### Exact code excerpts

```python
side=Side.BUY,
```

```python
if engine_inputs.realized_vol_post_close is not None and engine_inputs.realized_vol_post_close > 0.0:
    return engine_inputs.realized_vol_post_close, ...
if engine_inputs.realized_vol_current is not None and engine_inputs.realized_vol_current > 0.0:
    return engine_inputs.realized_vol_current, ...
```

```python
return _clamp(
    0.45 * inputs.reformation_quality
    + 0.30 * inputs.pullback_quality
    + 0.25 * context_score
)
```

```python
if coordination_input is not None and coordination_input.first_episode_ref is not None:
    return coordination_input.first_episode_ref.bet_structure
return BetStructure.DIRECTIONAL_LONG
```

## Engine D traced meaning

- `realized_vol_post_close`:
  - preferred volatility seam for re-entry forecast
- `realized_vol_current`:
  - fallback volatility seam
- `first_episode_ref`:
  - historical linkage / coordination seam
- `anti_revenge_state`:
  - runtime conditioning seam
- `reformation_score`:
  - local re-entry quality score

## Should C/D map to shared scoring physics?

Evidence in this pass does **not** prove that Engine C or Engine D should be force-mapped into A/B-style shared scoring physics fields.

### Reasons

1. Engine C microstructure seam is semantic gating around continuation, contradiction, and toxic-flow veto, not generic fragility/toxicity carriage.
2. Engine D microstructure seam is realized-volatility context for re-entry / first-episode / anti-revenge conditioning.
3. Canonical provenance for C and D is explicit and narrow:
   - Engine C:
     - `cumulative_ofi`
     - `queue_pressure`
     - `vpin`
     - `kyle_lambda`
     - `realized_vol_current`
     - `realized_vol_at_break`
   - Engine D:
     - `realized_vol_current`
     - `realized_vol_post_close`

## Classification

- Engine C:
  - `DIRECT_ENGINE_INPUT`
  - `ENGINE_CONSUMED`
  - `HUMAN_OR_EXTERNAL_AUDIT_REQUIRED` for any forced shared-scoring equivalence
- Engine D:
  - `DIRECT_ENGINE_INPUT`
  - `ENGINE_CONSUMED`
  - `HUMAN_OR_EXTERNAL_AUDIT_REQUIRED` for any forced shared-scoring equivalence

## Tests

- `tests/test_engines/test_engine_c/test_engine_c_runtime.py`
  - `assert result.engine_output.microstructure_gate_applied is True`
  - `assert result.engine_output.cumulative_ofi == pytest.approx(24.0)`
  - `assert accepted_log.queue_pressure == pytest.approx(0.36)`
  - `assert result.signal_candidate.side == Side.BUY`
- `tests/test_engines/test_engine_d/test_runtime_input_assembler_d.py`
  - `assert assembly.runtime_input.engine_inputs.realized_vol_current == pytest.approx(0.018)`
  - `assert assembly.runtime_input.engine_inputs.realized_vol_post_close == pytest.approx(0.015)`
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py`
  - `assert result.signal_candidate.side == Side.BUY`
