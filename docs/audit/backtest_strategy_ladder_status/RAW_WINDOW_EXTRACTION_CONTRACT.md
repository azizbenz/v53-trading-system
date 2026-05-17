# Raw Window Extraction Contract

Date: `2026-05-03`

## Canonical output

`raw_windows/{pair}/{candidate_id}/window_manifest.json`

## Required manifest fields

- `candidate_id`
- `pair`
- `engine_id`
- `timestamp_ms`
- `window_start_ms`
- `window_end_ms`
- `raw_trade_path`
- `raw_book_path`
- `raw_ohlcv_path`
- `book_depth_levels_available`
- `book_depth_source_status`
- `window_extraction_status`
- `input_data_hash`
- `artifact_hash`

## Allowed statuses

- `RAW_WINDOW_READY`
- `RAW_WINDOW_PARTIAL`
- `RAW_WINDOW_MISSING_TRADES`
- `RAW_WINDOW_MISSING_BOOK`
- `RAW_WINDOW_MISSING_OHLCV`
- `RAW_WINDOW_NOT_PROVEN`

## Required rules

- Missing book must remain explicit and must not become zero impact.
- Missing trades must remain explicit.
- Missing OHLCV must remain explicit.
- Limited depth must remain limited depth, not depth20.
- Window extraction must be deterministic and hash-backed.
