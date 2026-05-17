# Wave 4 External Audit Questions

1. Kyle lambda uses an unscaled rolling OLS slope. Is the current unit acceptable for Engine C vetoes and Engine A cost uplift, or should a normalized bps/notional seam be required?
2. OFI is emitted as raw signed-size imbalance, not a normalized cross-pair score. Is that doctrinally acceptable under current engine-local thresholds?
3. PIN is only parameter-evaluation in the traced seam. Is raw-event fitting intentionally out of governed runtime scope?
4. `Amihud`, `Roll`, `Corwin-Schultz`, and `Hawkes` are implemented, but direct runtime consumers are not fully proven. Are these still intended for governed runtime or now primarily research/catalog seams?
5. `Roll` spread is registry-linked to execution cost metering, but the direct governed runtime consumer was not proven here. Is that registry entry still active?
6. `depth_skew` currently mirrors `order_book_imbalance` in the LOB regime bundle. Is that an intentional alias or only a compatibility seam?
7. `real_wall_score` and `spoof_suspicion_score` use bounded weighted heuristics. Does external audit require a formal calibration note before stronger production claims?
8. The governed runtime regime output is non-directional, but `src/local_replay_runtime/regime_detector_dataset_builder.py` contains directional label generation for local-lab training. Is the current separation sufficient, or should naming/module boundaries be hardened?
9. Should cockpit feature-bridge presence be explicitly segregated from governed runtime-consumption proof to avoid false-green inference?
10. Should route-hint spread fallback in `state_data_quality.py` be visually distinguished from live-depth-derived spread?
11. Engine C and Engine D have narrow canonical provenance seams. Should external audit treat their partial-by-design non-mapping to A/B shared scoring physics as the correct governed doctrine?
