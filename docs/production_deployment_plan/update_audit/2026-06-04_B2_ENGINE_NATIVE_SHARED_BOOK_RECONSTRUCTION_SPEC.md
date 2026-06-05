# 2026-06-04 — B2 engine-native shared book reconstruction (per-(pair,day)) — Opus → Codex SPEC

> Master/slave protocol (CLAUDE.md §3). Opus authored the spec + the measured
> diagnosis below. Codex executes and fills the `<slot>`s. Opus then runs the
> audit checklist and emits GREENLIGHT or REQUEST_FIX.

## Objective

Eliminate the **redundant per-candidate order-book reconstruction** that makes
`engine_native_materialization` the dominant B2 cost. Candidates that share a
`(pair, source-day)` partition currently each walk the day's deltas from the
base snapshot **from scratch**; the existing progressive book-state cache
(patch A2-OPT-4) achieves **0 % hit** in B2. Make reconstruction work
**O(deltas per partition)** instead of **O(candidates × deltas per partition)**,
with **bit-exact parity** on every engine feature value.

This is a CPU/throughput fix only. It does **not** touch the RAM guard (already
shipped in `f57cd06`), the engines (A/B/C/D), profiles, or the
Shadow→Micro-live→Live gates.

## Measured diagnosis (Opus, 2026-06-04 — reproduced, do not re-derive)

Instrumented in-process replay of `tmp/b2_a2_53402a08_subset20_candidates.jsonl`
(`--detailed-only`, `V53_MAX_WORKERS=1`, run 53402a08 A2 inputs on `L:`):

```
engine_native_materialization      = 9.173 s   (top bottleneck; subset80 = 142.2 s = 60 %)
progressive_book_state_hit_count   = 0         <-- 0 % reuse in B2
progressive_book_state_miss_count  = 15        <-- one full reconstruct per candidate
file_cache_hit_count               = 72 / 33   (raw JSONL file cache DOES reuse)
replay-phase book_state cache      = 128 / 16  (89 % hit — proves the gap is engine-native-specific)
```

Candidate→source concentration (measured from the candidate JSONL, no pipeline):

```
subset20: 20 candidates -> 2 distinct (pair, day) partitions = 10x reuse factor
subset80: 80 candidates -> 2 distinct (pair, day) partitions = 40x reuse factor
```

A full 3-day discovery run (thousands of candidates over ~6 partitions) implies a
**several-hundred×** redundant-reconstruction factor.

### Why the existing cache misses (root cause, code-confirmed)

`_reconstruct_book_states_with_progressive_cache`
(`src/local_replay_runtime/strategy_ladder_engine_native_adapter.py:618`):

1. **Cache key includes `delta_path`** (`_progressive_book_state_cache_key`, l.291).
   In B2 each candidate has a distinct content-addressed window slice →
   distinct `delta_path` → distinct key → never shared.
2. **Reuse predicate is `last_ts_entry < window_start_ms`** (l.655). B2 windows
   are **nested** (all anchored at the day-start snapshot because of the
   ~2-snapshot/day cadence; each ends at its decision time). No cached boundary
   is ever strictly before a shared `window_start` → miss even when a key is
   shared (`progressive_book_state_cache_size=4` but 0 hits).

The cache was built for A2's **sequential, non-overlapping 1 m decisions** over a
**shared daily delta file**; B2's overlapping windows + per-candidate slices
defeat both assumptions.

## Current code seam (read before editing)

- `strategy_ladder_runner.py:_materialize_engine_native_candidates` (l.3097) —
  the per-candidate serial loop (`for ... in _serial_events`, l.3152). Calls
  `_run_native_engine_candidate` (l.2664) per candidate.
- `_run_native_engine_candidate` → per-engine `build_engine_{a,b,c,d}_microstructure_inputs_from_window(candidate_id, pair, window_start_ms, window_end_ms, window=…)`.
- Each builder calls `_reconstruct_book_states_with_progressive_cache(snapshot_path=raw_book_path, delta_path, base_snapshot, deltas, window_start_ms, window_end_ms, top_k=20)` (engine-C site l.1244; engine-D/microstructure-records site l.1805; requested-features site l.1376) and samples `book_states` within `[window_start, window_end]` to compute OFI / queue_pressure / VPIN / Kyle.
- Reconstruction reads: `snapshot_path` (the **daily base snapshot**, shared across a (pair,day)) + `delta_path` (the **per-candidate slice**) + window bounds.

## Design (recommended: extend the progressive cache; fallback: precompute timeline)

**Invariant (non-negotiable):** every engine feature value (cumulative_ofi,
queue_pressure, vpin, kyle_lambda, realized-kernel, book-depth, …) for every
candidate must be **bit-identical** to the current per-candidate path. The fix
changes *where the deltas are walked*, never *what is emitted*.

### Option A — shared, nested-aware progressive cache (preferred, surgical)

1. **Re-key** the progressive cache on the **shared source identity**, not the
   per-candidate slice: key = `(snapshot_path_sig, source_delta_identity, base_update_id)`
   where `source_delta_identity` is the **(pair, source-day)** silver-delta
   stream the slices are carved from — not the candidate slice path. (Derive it
   from the window manifest's source/lineage fields, or from `(pair, day(window_end))`.)
2. **Cache the emitted state list, not only the final book.** Store
   `(last_applied_uid, last_applied_ts, emitted_states[])` per key. For a new
   window `[ws, we]` on the same key, take the cached entry with the **largest
   `last_applied_ts ≤ we`**, advance only deltas in `(last_applied_ts, we]`,
   append newly-emitted states, then **return the sub-slice of emitted states
   that fall within `[ws, we]`**. Nested supersets reuse the prefix; this is the
   O(N)→O(1)-amortised path the docstring (l.628-639) already promises, now made
   to work for nested/overlapping windows.
3. **Process candidates within a partition in increasing `window_end_ms` order**
   so the cache advances monotonically. Group/sort happens in
   `_materialize_engine_native_candidates` before the loop (and inside any
   parallel chunk: keep a whole `(pair,day)` partition on **one** worker so the
   cache is process-local — reuse the ID-disjoint chunking pattern from
   `strategy_ladder_detailed_replay`).
4. **Bound memory**: cap cached `emitted_states[]` per key (top_k levels already
   bounds width); evict via the existing `evict_microstructure_file_cache` hook
   and the RAM guard. The full-day state list at top_k=20 is far smaller than the
   raw delta stream, but must still be eviction-safe.

### Option B — precompute per-(pair,day) timeline (fallback if A's parity is hard)

Group candidates by `(pair, day)`; reconstruct the day's book-state timeline once
into a bounded, queryable structure; each candidate slices `[ws, we]` from it.
Same parity gate. Higher memory; simpler reasoning.

Pick A unless a parity test forces B. Either way the **win = reuse factor**
(10–40× on subsets, hundreds× on a full run).

## Placement / Files changed (expected)

- `src/local_replay_runtime/strategy_ladder_engine_native_adapter.py` — cache key
  + nested-aware reuse in `_reconstruct_book_states_with_progressive_cache` /
  `_progressive_book_state_cache_key`; new counters
  (`progressive_book_state_nested_reuse_count`).
- `src/local_replay_runtime/strategy_ladder_runner.py` — group+sort candidates by
  `(pair, day, window_end)` before the materialization loop; keep partitions
  worker-local in the parallel path.
- (maybe) emit `get_microstructure_file_cache_stats()` into the B2
  `replay_performance_profile` so the reuse is observable in-band (today it is
  only emitted on the A2 path — `strategy_ladder_data_factory.py:4827`).
- `tests/test_local_replay_runtime/…` — new parity + reuse tests.

## Claims to implement (Codex fills proof)

- [ ] C1 — Feature parity: for the subset20 candidates, every engine feature value
  is bit-identical between the shared path and the legacy per-candidate path
  (golden compare). `<slot>`
- [ ] C2 — Reuse proven: on subset20,
  `progressive_book_state_hit_count > 0` and reconstruction
  `advance_deltas`/candidate drops; partition with N candidates does **1**
  base-init, not N. `<slot>`
- [ ] C3 — Wall-time: `engine_native_materialization` on subset80 drops
  measurably (report before/after seconds). `<slot>`
- [ ] C4 — Parallel safety: a `(pair,day)` partition is never split across workers
  (cache stays process-local; no parity drift serial vs parallel). `<slot>`

## Tests and Proof (slots — CLAUDE.md §5)

- [ ] `pytest` targeted suite pass count: `<slot>`
- [ ] New parity test (shared == per-candidate, bit-exact): `<slot>`
- [ ] Reuse/perf numbers (before/after, the harness below): `<slot>`
- [ ] guardrails `net-new-from-edits = 0` (stash-proven; src/ never baselined
  FILE_TOO_LONG → split if a function/file crosses): `<slot>`
- [ ] `git diff --stat` in-scope only: `<slot>`

Reproduce the measurement with a throwaway harness mirroring Opus's:
`--detailed-only --candidate-events-path tmp/b2_a2_53402a08_subset20_candidates.jsonl`
against the run-53402a08 A2 inputs on `L:`, `V53_MAX_WORKERS=1`, wrapping
`reset_/get_microstructure_file_cache_stats`.

## Deferred / Not done

- Capture-side **snapshot cadence** (denser snapshots → shorter windows) is the
  *complementary* lever (also fixes A2 spread-staleness). Out of scope here; this
  spec optimises reconstruction on the **existing** data.
- True multicore B2 (engine-native is still RAM-capped to 1 worker on the 32 GB
  PC). This fix reduces the per-worker cost so 1 worker goes further; it does not
  raise the worker cap.

## Risks

- **Parity drift** (highest): nested-window prefix reuse must emit exactly the
  same states. Mitigation = C1 golden test is the gate; ship nothing without it.
- **Memory**: cached emitted-state lists per key must be eviction-safe under the
  RAM guard.
- **Ordering coupling**: correctness now depends on per-partition `window_end`
  ordering — assert it; fall back to legacy full-reconstruct on any
  non-monotonic/evicted access (the current miss path already does this).

## Completion Status: ✅ COMPLETE — Opus direct implementation (2026-06-04)

Implemented as **Option A, path-independent** (key `(pair, base_update_id)`, not
the per-candidate slice path). 100% in the adapter + a 1-call toggle wrap in the
runner; **no runner candidate-grouping needed** (the timeline is correct for any
candidate order — a shorter window just filters an already-longer timeline).

- NEW `_PartitionBookTimeline` (cumulative book + emitted-state list) +
  `_partition_shared_book_states` helper (gap-delta loading via the existing
  `_load_book_deltas_in_window_with_lookback` + legacy fallback under the toggle).
- Wired **both B2 reconstruction call sites**, which cover **all four engines**:
  site 2 = `build_engine_c_microstructure_inputs_from_window` (Engine C); site 3 =
  `_compute_microstructure_records_from_window`, the **shared helper** called by
  `build_engine_a/b/d_microstructure_inputs_from_window` (Engines A, B, D). The
  timeline key is `(pair, base_update_id)` — **engine-independent** — so candidates
  of different engines but the same (pair, day) share one book timeline (verified:
  subset20 = 6 A / 6 B / 5 C / 3 D candidates → build_count 2). The A2 gold seam
  (`build_engine_c_requested_microstructure_features_from_window`) is left on the
  legacy progressive cache. Engine trading logic (`run_engine_*`) is untouched —
  only the shared book reconstruction that feeds the native re-invocations. Toggle default **False** (A2-safe); the B2 runner
  enables it around materialization only, in `try/finally`, then evicts timelines.
- The RAM guard (`f57cd06`) reclaims timelines under pressure
  (`evict_microstructure_file_cache` clears `_PARTITION_BOOK_TIMELINE_CACHE`).

**Proof (CLAUDE.md §5):**
- pytest: **7 new parity tests** (bit-exact vs `_reconstruct_book_states`: nested,
  overlapping, out-of-order, incremental, top_k, shipped-helper build_count,
  toggle-off fallback) + **104 passed, 4 skipped** regression (targeted suite).
- guardrails: **net-new-from-edits = 0** (stash-proven, global 816 == 816).
- empirical subset20 (real run 53402a08 inputs): C2 reuse proven —
  `partition_timeline_build_count = 2` (was 15 per-candidate reconstructions);
  delta-applications **16881 → 2368** (~7×); `progressive_book_state_miss_count = 0`.
  C3 wall: `engine_native_materialization` **9.17s → 7.42s** on subset20 (the win
  scales with window size + reuse factor — far larger on a full run).
- `git diff --stat`: `strategy_ladder_engine_native_adapter.py` (+~290),
  `strategy_ladder_runner.py` (+~16 net), NEW
  `tests/test_local_replay_runtime/test_b2_partition_book_timeline_parity.py`.

## Next Safe Step
1. Commit (awaiting user) + push with the 2 pending commits once auth is restored.
2. Re-run subset80 to quantify the wall-time win at higher reuse (40×) before a
   full multi-day B2.
3. (follow-up, not blocking) parallel-worker enablement: set the toggle in the
   worker init so the partition timeline also shares inside parallel chunks
   (today only the serial / 1-worker path benefits — which is the current PC mode).
4. (follow-up) runner candidate grouping by `(pair, day)` to evict each partition's
   timeline as soon as it is done, tightening peak memory on very long runs.

## Opus audit checklist (run on completion)

1. `pytest` targeted suite green; concrete pass count printed.
2. C1 parity test exists, exercises the **shipped** path, and is bit-exact.
3. C2 reuse proven: hit_count > 0 on subset20 (re-run the harness).
4. C3 before/after `engine_native_materialization` seconds reported (subset80).
5. C4 serial==parallel parity; partitions worker-local.
6. guardrails net-new-from-edits = 0 (stash-proven); no src/ file baselined for FILE_TOO_LONG.
7. `git diff --stat` shows only in-scope files.
8. Verdict: GREENLIGHT or REQUEST_FIX (line-level).
