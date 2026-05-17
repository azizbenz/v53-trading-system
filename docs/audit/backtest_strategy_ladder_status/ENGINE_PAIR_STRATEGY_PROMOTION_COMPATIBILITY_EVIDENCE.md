# Engine / Pair / Strategy Promotion Compatibility Evidence

## Overall verdict

`READY`

This verdict is about rail compatibility plus measured-feed wiring.

It does **not** mean promotion readiness is measured or green across historical runs.

## Canonical paths found

- `engine_promotion/{engine_id}/{run_id}.json`
- `pair_promotion/{pair}/{run_id}.json`
- `strategy_promotion/{strategy_id}/{run_id}.json`
- `sample_size_survival/{scope}/{id}/{run_id}.json`

Primary source files:

- `src/interface_contracts/promotion_artifact_contracts.py`
- `src/local_replay_runtime/promotion_artifact_builder.py`
- `src/local_replay_runtime/strategy_ladder_runner.py`
- `src/local_replay_runtime/artifact_exporter.py`
- `src/local_replay_runtime/replay_executor.py`
- `tests/test_local_replay_runtime/test_strategy_ladder_runner.py`

## Required engines

`REQUIRED_PROMOTION_ENGINE_IDS = ("engine_a", "engine_b", "engine_c", "engine_d")`

This remains source-proven in `src/interface_contracts/promotion_artifact_contracts.py`.

## Compatibility table

| Artifact rail | Classification | Evidence | Reading |
|---|---|---|---|
| `engine_promotion/*` | `READY` | builder + runner feed + exporter + tests | The Strategy Ladder runner now feeds engine artifacts from detailed replay output. |
| `pair_promotion/*` | `READY` | same | Pair artifacts are now fed from detailed replay output. |
| `strategy_promotion/*` | `READY` | same | Strategy artifacts are now fed from detailed replay output. |
| `sample_size_survival/*` | `READY` | same | Sample-size artifacts are now fed from detailed replay output. |

## Strategy ID compatibility assumption

- The current strategy-level artifact builder still uses the current replay/ladder strategy identity.
- No separate governed strategy catalog was discovered in this patch slice.
- Therefore the current compatibility assumption remains:
  `strategy_id = current runner strategy identity`.

This is acceptable for current compatibility and should be revisited only if a separate strategy catalog is introduced later.

## Engine C/D doctrine safety

- Engine C and Engine D still carry local explainability/status fields under their own nested namespaces.
- `shared_physics_mapping_status` remains explicit and `PARTIAL_BY_DESIGN` where required.
- Nothing in the current Strategy Ladder feed force-maps C/D into A/B shared scoring physics.

## Conclusion

Promotion-rail compatibility is no longer just contract-only. The canonical Strategy Ladder runner can now feed the existing artifact rails from detailed replay output. What remains open is audited historical measured promotion evidence, not the feed path itself.
