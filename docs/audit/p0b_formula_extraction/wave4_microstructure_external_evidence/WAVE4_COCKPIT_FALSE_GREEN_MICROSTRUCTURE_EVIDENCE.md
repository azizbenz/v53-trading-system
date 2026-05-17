# Wave 4 Cockpit False-Green Microstructure Evidence

## Source seams

- `src/cockpit/state_feature_bridge.py`
- `src/cockpit/templates/partials/_feature_bridge.html`
- `src/cockpit/state_data_quality.py`
- `tests/cockpit/test_state_feature_bridge.py`
- `tests/cockpit/test_state_data_quality.py`

## Feature-bridge artifact visibility

### Exact code excerpts

```python
SourceStatus = Literal["ok", "missing", "parse_error"]
```

```python
if latest is None:
    return FeatureBridgeSnapshot(source_status="missing")
...
if not path.is_file():
    return FeatureBridgeSnapshot(source_status="missing", source_path=str(path))
...
except (OSError, json.JSONDecodeError) as exc:
    return FeatureBridgeSnapshot(source_status="parse_error", source_path=str(path))
```

```html
{% if vm.feature_bridge.source_status != 'ok' %}
    <p class="muted">No feature bridge export for the latest day.</p>
{% else %}
```

```html
{% if vm.feature_bridge.lineage_lock_status == 'missing' %}
<p class="muted small value-down"><strong>Audit gap:</strong> feature lineage lock is still missing.</p>
{% endif %}
```

## Data-quality spread / stale seam

### Exact code excerpts

```python
if snapshot_path is None or not snapshot_path.is_file():
    return DataQualitySnapshot(
        source_status="missing",
        ...
        reason_codes=("live_snapshot_batch_missing",),
```

```python
spread_bps = _compute_spread_bps(bid, ask)
if spread_bps is None:
    spread_bps = _float(_nested(latest, "route_hint", "feature_values", "spread_bps"))
depth_available = bid is not None and ask is not None
stale_flag = bool(age_ms is not None and age_ms > stale_after_ms)
if stale_flag:
    status = "stale"
elif not depth_available:
    status = "missing_depth"
else:
    status = "ok"
```

## False-green risks extracted

1. Feature-bridge `ok` means artifact parse success, not proof of governed runtime consumption.
2. Recognized feature families in the cockpit are lineage/display signals, not direct execution/scoring proof.
3. Data-quality `spread_bps` can come from live batch depth or route-hint fallback; external audit should distinguish those sources.
4. `state_data_quality` uses `status = ok | stale | missing_depth | unknown`; that is safer than pure numeric zero defaults, but it is still a monitoring seam rather than a final execution-readiness verdict.

## Tests

- `tests/cockpit/test_state_feature_bridge.py`
  - `assert snapshot.feature_families == ("snapshot", "trade", "spread")`
  - `assert snapshot.recognized_feature_families == ("snapshot", "trade")`
  - `assert snapshot.unrecognized_feature_families == ("snapshot", "spread")`
- `tests/cockpit/test_state_data_quality.py`
  - `assert snapshot.pairs[0].status == "ok"`
  - `assert snapshot.pairs[0].status == "stale"`

## Classification

- `EVIDENCE_EXTRACTED`
- `TEST_COVERED`
- `COCKPIT_ONLY`
- `PLACEHOLDER_RISK`
- `COCKPIT_FALSE_GREEN_RISK`

## External-audit questions

1. Should the cockpit explicitly separate:
   - artifact-present
   - runtime-consumed
   - execution-gate-active
   instead of allowing feature-bridge presence to look operationally stronger than it is?
2. Should route-hint spread fallback be visually distinguished from live depth-derived spread?
