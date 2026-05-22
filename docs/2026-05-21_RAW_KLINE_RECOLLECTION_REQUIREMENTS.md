# Raw Kline Recollection Requirements

## Purpose

This document captures the exact raw-data recollection needs discovered during the audit of:

- `L:\output backtest\runs\strategy_ladder_workflow-2f2ce881fb53f597`

Its purpose is to support a separate implementation conversation for a collection script that fetches the missing raw market data correctly.

This is a **data collection requirements doc**, not a patch report.

## Executive Summary

The canonical blocker is **not** in the backtest runner, `A2`, silverization, or orderbook extraction.

The dominant bronze gaps come from **incomplete raw Bybit kline files** already present under:

- `L:\klines\BTCUSDT\1\2025\BTCUSDT_1_2025-07-25.csv`
- `L:\klines\BTCUSDT\1\2025\BTCUSDT_1_2025-07-26.csv`
- `L:\klines\BTCUSDT\10\BTCUSDT_10_2025-07-25.csv`
- `L:\klines\BTCUSDT\10\BTCUSDT_10_2025-07-26.csv`

Observed pattern:

- `1m` files contain `1000` rows instead of `1440`
- `10m` files contain `100` rows instead of `144`
- both timeframes start at `07:20 UTC` instead of `00:00 UTC`

This creates the critical `26400000 ms` (`7h20`) inter-day bronze gap that correctly blocks canonical `A2 -> B1/B2`.

## Root Cause Proven by Audit

Run artifacts:

- `L:\output backtest\runs\strategy_ladder_workflow-2f2ce881fb53f597\phase_a2_data_factory\silver_quality_report.json`
- `L:\output backtest\runs\strategy_ladder_workflow-2f2ce881fb53f597\phase_a2_data_factory\bronze_market_index.json`

Key findings:

- `bronze_gap_count = 3`
- `bronze_largest_gap_ms = 26400000`
- `bronze_gap_severity_status = BRONZE_GAPS_BLOCKED`

Direct raw-file inspection proved:

### 1m raw klines

- `BTCUSDT_1_2025-07-25.csv`
  - rows: `1000`
  - first timestamp: `1753428000000` = `2025-07-25T07:20:00Z`
  - last timestamp: `1753487940000` = `2025-07-25T23:59:00Z`
- `BTCUSDT_1_2025-07-26.csv`
  - rows: `1000`
  - first timestamp: `1753514400000` = `2025-07-26T07:20:00Z`
  - last timestamp: `1753574340000` = `2025-07-26T23:59:00Z`

### 10m raw klines

- `BTCUSDT_10_2025-07-25.csv`
  - rows: `100`
  - first timestamp: `1753428000000` = `2025-07-25T07:20:00Z`
  - last timestamp: `1753487400000` = `2025-07-25T23:50:00Z`
- `BTCUSDT_10_2025-07-26.csv`
  - rows: `100`
  - first timestamp: `1753514400000` = `2025-07-26T07:20:00Z`
  - last timestamp: `1753573800000` = `2025-07-26T23:50:00Z`

### Trades

- `L:\trades\BTCUSDT\BTCUSDT_2025-07-25.csv.gz`
- `L:\trades\BTCUSDT\BTCUSDT_2025-07-26.csv.gz`

Observed gap:

- `2180 ms` between day boundary

This is minor and not the dominant blocker.

### Orderbook

- `L:\ordrebookpart1\BTCUSDT\2025-07-25_BTCUSDT_ob200.data.zip`
- `L:\ordrebookpart1\BTCUSDT\2025-07-26_BTCUSDT_ob200.data.zip`
- extracted `.data` files match ZIP contents on:
  - first event
  - last event
  - line count

Conclusion:

- orderbook extraction is **not** the source of the bronze gaps

## Immediate Data Recollection Scope

The next collection script must at minimum regenerate these raw files correctly:

- `L:\klines\BTCUSDT\1\2025\BTCUSDT_1_2025-07-25.csv`
- `L:\klines\BTCUSDT\1\2025\BTCUSDT_1_2025-07-26.csv`
- `L:\klines\BTCUSDT\10\BTCUSDT_10_2025-07-25.csv`
- `L:\klines\BTCUSDT\10\BTCUSDT_10_2025-07-26.csv`

The script should preferably support a more general repair mode for:

- symbol
- timeframe
- start date
- end date

so that future incomplete days can be re-fetched without writing one-off fixes.

## Required Output Contract

For **full-day canonical backtest usage**, recollected kline files must satisfy:

### 1m

- expected rows per UTC day: `1440`
- expected first candle timestamp: `00:00:00 UTC`
- expected last candle timestamp: `23:59:00 UTC`
- no missing minute inside the day

### 10m

- expected rows per UTC day: `144`
- expected first candle timestamp: `00:00:00 UTC`
- expected last candle timestamp: `23:50:00 UTC`
- no missing 10-minute bucket inside the day

### 5m

- expected rows per UTC day: `288`

### 15m

- expected rows per UTC day: `96`

The collector must treat any lower row count as incomplete unless there is an explicit exchange-level proof that fewer bars are valid for that day.

## Functional Requirements for the Collection Script

The collection script must:

1. Fetch Bybit klines with correct pagination until the full UTC day is covered.
2. Avoid silent truncation at exchange page limits such as `1000` rows.
3. Preserve canonical ordering by ascending timestamp.
4. Write deterministic CSV output compatible with the existing raw folder layout.
5. Overwrite or stage-replace corrupted/incomplete raw files only after the recollected result passes validation.
6. Support dry-run validation mode before replacing files.
7. Produce an audit report with:
   - symbol
   - timeframe
   - date
   - requested range
   - fetched page count
   - final row count
   - first timestamp
   - last timestamp
   - completeness verdict

## Recommended Validation Rules

Before a recollected file is accepted, validate:

1. `row_count` equals the exact expected count for the timeframe/day.
2. first timestamp matches `00:00 UTC`.
3. last timestamp matches the expected last bucket for the timeframe.
4. every consecutive timestamp delta matches the timeframe interval exactly.
5. no duplicates.
6. no out-of-order rows.

If any rule fails, the script must fail-close and not mark the file repaired.

## Output Layout Requirements

The script must preserve the current raw layout:

- `L:\klines\BTCUSDT\1\2025\BTCUSDT_1_YYYY-MM-DD.csv`
- `L:\klines\BTCUSDT\10\BTCUSDT_10_YYYY-MM-DD.csv`

Do not invent a new storage layout for this repair pass unless the migration is explicitly approved.

## Non-Goals

This repair pass does **not** need to recollect:

- orderbook ZIP files
- extracted orderbook `.data`
- raw trades files
- metadata cache

Those artifacts were not identified as the root cause of the critical bronze gap on this run.

## Acceptance Criteria for the Backtest Pipeline

After recollection and rerun of `A2`, the following must be true:

1. `silver_quality_report.json`
   - `bronze_gap_count = 0` or only non-critical residual gaps explicitly accepted by doctrine
   - `bronze_largest_gap_ms` no longer reflects the `7h20` kline hole
2. `data_factory_manifest.json`
   - no `BRONZE_GAP_LARGEST_EXCEEDS_RESEARCH_TOLERANCE`
3. `workflow_manifest.json`
   - `PHASE_A2` no longer blocked by bronze-gap severity
4. `1m` and `10m` silver outputs mirror full-day raw coverage
5. only then may canonical `B1/B2` proceed

## Suggested Next Conversation Prompt

Use this document to drive the next implementation conversation:

- build a Bybit kline recollection script
- repair incomplete `1m` and `10m` raw files
- enforce exact full-day validation
- emit an audit report before file replacement
- preserve the existing raw folder layout

## Bottom Line

The next script should solve a **raw kline completeness** problem, not a backtest-runner problem.

The required repair is:

- recollect complete `1m` and `10m` BTCUSDT day files
- prove full UTC-day coverage
- rerun `A2`
- only then resume canonical `B1/B2`
