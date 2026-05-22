# Patch Docs Verification — Line-by-Line Reality Check

**Date:** 2026-05-21  
**Scope:** verification of patch docs against the current codebase and latest live artifacts  
**Method:** compare doc claims to:
- current code under `src/cockpit/` and `src/local_replay_runtime/`
- targeted tests run on 2026-05-21
- live run evidence already audited on `strategy_ladder_workflow-f9bb2bdc0c8ce1fd`

---

## 1. Executive verdict

The docs are **not uniformly wrong**, but they are **not uniformly current** either.

The current repo state splits into 3 buckets:

1. **Implemented and verified in code/tests**
- P1 OHLCV partial-day severity
- P2 metadata JSONL detection
- P3 ZIP/extracted dedup
- F2 bronze-gap severity classifier
- F16-B microstructure persistence
- `raw_source_manifest_path` propagation into runner manifests

2. **Still doc-only / not implemented in the actual launch path**
- **P6 fail-close `A2 -> B1/B2`**

3. **Docs now stale or over-strong**
- claims that `f9bb2bdc` would now be `DATA_FACTORY_READY`
- claims that 3 data-factory tests are still failing because of a pre-existing `TypeError`

---

## 2. Verified implemented in code

### 2.1 P1 — OHLCV partial-day severity

**Doc claim**
- `docs/2026-05-21_PATCHES_P1_P2_P3_IMPLEMENTATION_REPORT.md:4`
- `docs/2026-05-21_CODEX_HANDOFF_SPRINT_PATCHES.md:15`

**Code reality**
- `src/local_replay_runtime/strategy_ladder_data_factory.py:155-247`
- current code emits:
  - `OHLCV_<tf>_PARTIAL_DAY_ACCEPTED`
  - `OHLCV_TEMPORAL_COMPLETENESS_PARTIAL_DAY_ACCEPTED`

**Test reality**
- targeted pytest run passed for partial-day acceptance cases

**Verdict**
- **TRUE IN CODE**

---

### 2.2 P2 — metadata JSONL schema detection

**Doc claim**
- `docs/2026-05-21_PATCHES_P1_P2_P3_IMPLEMENTATION_REPORT.md`
- `docs/2026-05-21_CODEX_HANDOFF_SPRINT_PATCHES.md`

**Code reality**
- `src/local_replay_runtime/raw_market_data_indexer.py:457-497`
- metadata marker detection is present and suppresses false `RAW_FILE_SCHEMA_UNKNOWN`

**Verdict**
- **TRUE IN CODE**

---

### 2.3 P3 — ZIP/extracted dedup

**Doc claim**
- `docs/2026-05-21_PATCHES_P1_P2_P3_IMPLEMENTATION_REPORT.md`
- `docs/2026-05-21_CODEX_HANDOFF_SPRINT_PATCHES.md`

**Code reality**
- `src/local_replay_runtime/raw_market_data_indexer.py:562-625`
- dedup by content signature is present

**Verdict**
- **TRUE IN CODE**

---

### 2.4 F2 — bronze-gap severity classifier

**Doc claim**
- `docs/2026-05-21_F2_BRONZE_GAP_SEVERITY_IMPLEMENTATION_REPORT.md:4`

**Code reality**
- `src/local_replay_runtime/silver_market_synchronizer.py:18-80`
- `BRONZE_GAPS_TOLERATED_RESEARCH_GRADE` exists in code

**Test reality**
- targeted pytest run:
  - `tests/test_local_replay_runtime/test_f2_bronze_gap_severity_classifier.py`
  - `11 passed`

**Verdict**
- **TRUE IN CODE**

---

### 2.5 F16-B — VPIN / OFI / queue_pressure persistence

**Doc claim**
- `docs/2026-05-21_F16_B_IMPLEMENTATION_REPORT.md:4`

**Code reality**
- `src/local_replay_runtime/strategy_ladder_b2_label_store_builder.py:343-381`
- schema version `strategy_ladder.b2_label_store_row.v2` is present

**Test reality**
- targeted pytest run:
  - `tests/test_local_replay_runtime/test_f16_b_microstructure_persistence.py`
  - `12 passed`

**Verdict**
- **TRUE IN CODE**

---

### 2.6 `raw_source_manifest_path` propagation

**Doc / audit context**
- prior audits required `A2` provenance to reach `B1/B2`

**Code reality**
- `src/local_replay_runtime/strategy_ladder_runner.py:287-310`
- `_resolve_run_raw_source_manifest_path(...)` exists and falls back to A2 manifest

**Test reality**
- `tests/test_local_replay_runtime/test_strategy_ladder_runner.py:126`

**Verdict**
- **TRUE IN CODE**

---

## 3. Confirmed NOT implemented yet

### 3.1 P6 fail-close `A2 -> B1/B2`

This is the most important gap.

**Doc claim**
- `docs/2026-05-20_A2_FAILCLOSE_BUG_PATCH_PLAN.md:6`
  - explicitly says `PLAN — code pas modifié`
- `docs/2026-05-21_F16_B_IMPLEMENTATION_REPORT.md:192`
  - marks P6 as `Pending`
- `docs/2026-05-21_CODEX_HANDOFF_SPRINT_PATCHES.md:498`
  - still lists P6 in next steps

**Code reality**
- `src/cockpit/action_support.py:2052-2053`
  - `JOB_COMPLETED_WITH_BLOCKERS` still maps A2 to `PHASE_STATUS_DATA_FACTORY_READY`
- `src/cockpit/backtest_preflight.py:1628-1643`
  - `B1/B2` preflight checks only artifact presence
  - it does **not** reject a critical blocked upstream A2

**Operational consequence**
- a workflow can still run `B1/B2` on top of an `A2` that says `DATA_FACTORY_BLOCKED_*`

**Verdict**
- **NOT IMPLEMENTED**

---

## 4. Docs that are stale or overstate the current reality

### 4.1 “After patches, f9bb2bdc will be DATA_FACTORY_READY”

**Doc claim**
- `docs/2026-05-21_PATCHES_P1_P2_P3_IMPLEMENTATION_REPORT.md:181`
- `docs/2026-05-21_PATCHES_P1_P2_P3_IMPLEMENTATION_REPORT.md:191`

**Problem**
- this is not a verified artifact claim in the current tree
- it is a projection that still requires a fresh rerun
- later live audits still found blocked A2 runs in actual artifacts

**Verdict**
- **TOO STRONG / MUST BE TREATED AS HYPOTHESIS UNTIL RERUN**

---

### 4.2 “The 3 failing data-factory tests are still broken because of a pre-existing TypeError”

**Doc claim**
- `docs/2026-05-21_PATCHES_P1_P2_P3_IMPLEMENTATION_REPORT.md:159-166`
- `docs/2026-05-21_CODEX_HANDOFF_SPRINT_PATCHES.md:437-439`

**Current test reality**
- targeted pytest run on 2026-05-21:
  - `test_data_factory_normalizes_inputs_builds_gold_and_keeps_dynamic_pair_universe`
  - `test_data_factory_blocks_ambiguous_timestamp_units`
  - `test_data_factory_scans_flat_generic_root_without_year_directories`
- they now fail on **asserted status values**, not on `TypeError`

**Observed failures**
- expected `DATA_FACTORY_READY` or `DATA_FACTORY_BLOCKED_BY_SCHEMA`
- got `DATA_FACTORY_BLOCKED_BY_OHLCV_TEMPORAL_COMPLETENESS`

**Verdict**
- **STALE DOC CLAIM**
- the debt is now **fixture/assertion realignment**, not a lingering signature crash

---

### 4.3 “Remove 10m from critical list” as the next chosen fix

**Doc claim**
- `docs/2026-05-21_DATAFACTORY_BLOCKERS_ROOT_CAUSE_AND_FIX.md`
- recommends `B + C` with:
  - keep severity for 1m
  - remove `10m` from the critical list

**Code reality**
- current code does **not** remove `10m` from the critical set
- `10m` is still part of:
  - `_CRITICAL_OHLCV_EXPECTED_ROWS_PER_DAY`
  - `_CRITICAL_OHLCV_TIMEFRAME_INTERVALS_MS`

**Verdict**
- **DOC REFLECTS AN EARLIER DESIGN OPTION, NOT THE CURRENT IMPLEMENTATION**

---

## 5. Doctrine docs that remain valid

These docs are still useful as doctrine / sequencing references:

- `docs/2026-05-19_V53_BACKTEST_REALISM_RECAP.md`
- `docs/2026-05-20_V53_A2_REUSE_BACKTEST_MANY_DOCTRINE.md`
- `docs/2026-05-20_P0A_DECISIONS_LOCKED.md`
- `docs/2026-05-20_P0A_PHASES_DETAIL.md`
- `docs/2026-05-20_P0A_EXECUTION_PLAN.md`

But they should be read as:
- **policy / target architecture**
- not as proof that every downstream guard is already implemented

---

## 6. What to do next — exact order

### Step 1 — patch P6 for real

Current blocker hierarchy says this is the highest-value missing patch.

Required code areas:
- `src/cockpit/action_support.py`
  - A2 phase status must stop treating every `JOB_COMPLETED_WITH_BLOCKERS` as READY
- `src/cockpit/backtest_preflight.py`
  - `B1/B2` must read upstream `phase_a2_data_factory/data_factory_manifest.json`
  - critical blocked A2 must block downstream launch

### Step 2 — add/refresh targeted tests for P6

Must prove:
- blocked A2 => `PHASE_A2_DATA_FACTORY_BLOCKED`
- blocked A2 => `B1` preview blocked
- blocked A2 => `B2` preview blocked
- research-only A2 blockers only => downstream may proceed if doctrine allows it

### Step 3 — rerun A2 on a fresh workflow

Do **not** treat old run artifacts as proof of post-patch behavior.

### Step 4 — re-audit A2 artifacts first

Read again:
- `data_factory_manifest.json`
- `data_quality_report.json`
- `silver_quality_report.json`
- `workflow_manifest.json`

### Step 5 — only then allow `B1/B2`

If A2 is still critically blocked, downstream must stay blocked by doctrine.

### Step 6 — clean stale tests and stale docs

After P6 + rerun:
- update the 3 data-factory tests whose expected statuses are now stale
- update docs that still mention the old `TypeError` debt
- update docs that describe `f9bb2bdc` as ready before a verified rerun

---

## 7. Bottom line

If we want to understand “what to do” without noise:

1. **Trust the implementation reports for P1/P2/P3/F2/F16-B only insofar as code/tests confirm them.**
2. **Do not trust any doc that implicitly assumes P6 is already live.**
3. **The next real patch is P6 fail-close `A2 -> B1/B2`.**
4. **Only after P6 + rerun can we honestly decide whether A2 is stable enough for the `A2 reuse / backtest many` doctrine.**
