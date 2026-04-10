# Sonnet Audit BS Mapping

This file captures the usable `BS-* -> code` mappings recovered from:
- `docs/ia lab vps v5.3/angle mor audit calude sonets .docx`

Role of this file:
- preserve the remapping evidence in Markdown for future sessions
- prevent a new chat from treating these ids as "tracker-only / unmapped"
- distinguish stale audit snapshots from still-open code reality

This file is not canon.
It is a secondary audit bridge that must always be cross-checked against current code.

## Recovery result on 2026-04-08

The Sonnet audit remaps the previously orphan ids as follows:

- `BS-43`
  - audit mapping: `atomic_write_json : default=str sérialise silencieusement les types non-JSON`
  - audit code pointer: `atomic_io.py:45`
  - current repo path: `src/interface_contracts/atomic_io.py`
  - current code reality:
    - the audited `default=str` call is no longer present
    - `atomic_write_json()` now calls `json.dumps(data, indent=indent)` and therefore raises on unsupported types instead of silently stringifying them
  - status:
    - mapped
    - audit snapshot stale relative to current code
    - treat as closed by current repo state

- `BS-46`
  - audit mapping: `check_fd_leak : tolérance de 5 FDs s'accumule sans seuil absolu`
  - audit code pointer: `state_sanity_checker.py:193`
  - current repo path: `src/smoke_bootstrap_recovery/state_sanity_checker.py`
  - current code reality:
    - `check_fd_leak()` now supports an absolute FD ceiling in addition to the local delta tolerance
    - `run_build1_smoke()` now passes a suite-level FD ceiling derived from the initial process baseline, so slow cumulative leaks no longer hide behind repeated `+2/+3/+4` deltas
  - status:
    - mapped
    - closed in current code
    - outside the current `shadow/protocols` rail

- `BS-63`
  - audit mapping: `flush_to_disk : sérialise l'intégralité de l'historique à chaque appel`
  - audit code pointer: `trace_persistence_layer.py:110`
  - current repo path: `src/meta_minimal/dtr_core/trace_persistence_layer.py`
  - current code reality:
    - the old `data = [r.model_dump(mode="json") for r in self._records]` pattern is no longer present
    - current code caches `record.model_dump(mode="json")` at `persist()` time in `_serialized`
    - `flush_to_disk()` now writes `self._serialized`
  - status:
    - mapped
    - audit snapshot stale relative to current code
    - effectively closed by the already-landed `BS-62` fix set

- `BS-67`
  - audit mapping: `get_by_pair, get_by_engine, get_by_state : O(N) linear scan à chaque appel`
  - audit code pointer: `trace_persistence_layer.py:70-79`
  - current repo path: `src/meta_minimal/dtr_core/trace_persistence_layer.py`
  - current code reality:
    - the helper methods now read from append-only secondary indexes updated at `persist()` time
  - status:
    - mapped
    - closed in current code
    - outside the current `shadow/protocols` rail

## Cross-check proof

Code cross-check used on 2026-04-08:
- `src/interface_contracts/atomic_io.py`
- `src/meta_minimal/dtr_core/trace_persistence_layer.py`
- `src/smoke_bootstrap_recovery/state_sanity_checker.py`

Targeted proof run:
- `rtk pytest tests/test_interface_contracts/test_atomic_io.py tests/test_meta_minimal/test_bs62_dtr_crash_protection_regression.py tests/test_smoke_bootstrap_recovery/test_state_sanity.py -k "not test_dag_clean_passes" -q`
- `41 passed`
- `rtk pytest tests/test_meta_minimal/test_meta_minimal.py tests/test_meta_minimal/test_bs62_dtr_crash_protection_regression.py tests/test_meta_minimal/test_bs67_dtr_store_index_regression.py tests/test_regression_alignment.py -k "TestTracePersistenceLayer or TestDTRFlushToDisk or bs62 or bs67" -q`
- `21 passed`
- `rtk pytest tests/test_smoke_bootstrap_recovery/test_state_sanity.py tests/test_smoke_bootstrap_recovery/test_smoke_reporter.py -k "fd_leak or resource_release_checker" -q`
- `5 passed`

Known unrelated noise:
- the full test file `tests/test_smoke_bootstrap_recovery/test_state_sanity.py` still contains `test_dag_clean_passes`
- on the current broad worktree, that check fails because the repo is not DAG-clean end-to-end
- this is not evidence against the specific remapping above

## Operational rule

For future sessions:

1. do not call `BS-43`, `BS-46`, `BS-63`, or `BS-67` unmapped anymore
2. do not reopen `BS-43`, `BS-46`, `BS-63`, or `BS-67` unless current code regresses
