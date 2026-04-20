# Objective

Add a truthful, append-only persistence seam for Engine D consecutive-stop state so strategy beta state can survive restart without changing current runtime semantics.

# Docs Governants

- `docs/production_deployment_plan/22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md`

# Current Code Seam

Before this slice, `src/engines/engine_d/consecutive_stop_counter_d.py` only carried in-memory typed state plus inspectability. The spec explicitly requires restart-safe persistence for strategy beta state, but there was no append-only Engine D state snapshot store yet.

# Placement

The new seam lives in `src/engines/engine_d/engine_state_snapshot_d.py`. It stays local to Engine D, uses the same atomic JSONL + manifest persistence style already used by `RefusalJournal` and `ClosedEpisodeJournal`, and does not invent a second coordination rule engine.

# Files Changed

- `src/engines/engine_d/engine_state_snapshot_d.py`
- `src/engines/engine_d/__init__.py`
- `tests/test_engines/test_engine_d/test_engine_state_snapshot_d.py`

# Claims Implemented

- Added frozen `EngineDStateSnapshot` with canonical `(pair, side)` plus captured timestamp and `ConsecutiveStopStateD`.
- Added append-only `EngineDStateSnapshotStore` with:
  - `append(...)`
  - `append_state(...)`
  - `read()`
  - `latest_snapshot(...)`
  - `latest_state(...)`
  - `flush_to_disk(...)`
  - `load_from_disk(...)`
- Added `EngineDStateSnapshotManifest` with deterministic SHA-256 manifest validation.
- Kept the slice additive only:
  - no runtime behavior change
  - no broader caller creation
  - no silent D coordination change

# Tests and Proof

- `python -m py_compile src/engines/engine_d/engine_state_snapshot_d.py src/engines/engine_d/__init__.py tests/test_engines/test_engine_d/test_engine_state_snapshot_d.py`
  - pass
- `rtk pytest -q tests/test_engines/test_engine_d/test_engine_state_snapshot_d.py tests/test_engines/test_engine_d/test_consecutive_stop_counter_d.py tests/test_engines/test_engine_d/test_runtime_input_assembler_d.py --basetemp=.test_tmp/pytest`
  - `14 passed`
- `rtk pytest -q tests/test_engines/test_engine_d --basetemp=.test_tmp/pytest`
  - `113 passed`
- `python scripts/run_engineering_guardrails.py`
  - `new_violations=0`
- `python scripts/run_dag_check.py`
  - unchanged repo-global baseline fail with `9` violations outside this slice

# Deferred / Not Done

- No live caller persists `ConsecutiveStopStateD` yet.
- No automatic recovery path loads the store into a real runtime/orchestration caller yet.
- No broader Step 4 caller outside `src/engines/engine_d/` was created or adopted.
- No strategy-beta persistent state is wired into VPS lifecycle yet.

# Risks / Open Questions

- This slice only adds the persistence seam; restart continuity is not operational until a real caller flushes and reloads it.
- The spec text mentions persistence via `RefusalJournal` plus state snapshot. The refusal half already exists elsewhere, but this slice only closes the state snapshot half.
- Repo-global DAG/import-policy baseline remains red outside this slice.

# Completion Status

`PARTIAL`

Reason:

The additive persistence seam exists, is typed, tested, and audit-ready, but no real caller adopts it yet for live restart continuity.

# Next Safe Step

Adopt `EngineDStateSnapshotStore` in the first real Engine D state owner that already observes D stop outcomes and fresh-A resets, without inventing a new broader orchestration surface.
