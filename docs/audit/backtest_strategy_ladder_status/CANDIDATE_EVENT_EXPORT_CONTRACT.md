# Candidate Event Export Contract

Date: `2026-05-03`

## Canonical outputs

- `fast_candidates/candidate_events.jsonl`
- `fast_candidates/candidate_summary.json`

## Candidate event required fields

- `schema_version`
- `run_id`
- `candidate_id`
- `timestamp_ns` or `timestamp_ms`
- `pair`
- `timeframe`
- `engine_id`
- `strategy_id`
- `capital_bucket`
- `candidate_source`
- `feature_refs`
- `preliminary_score`
- `preliminary_reason_codes`
- `feature_version`
- `input_data_hash`
- `method_version_hash`

## Candidate export summary required fields

- `run_id`
- `candidate_count`
- `pairs_seen`
- `engines_seen`
- `strategies_seen`
- `timeframes_seen`
- `start_timestamp`
- `end_timestamp`
- `feature_store_status`
- `candidate_export_status`
- `artifact_hash`
- `input_data_hash`
- `created_at`

## Allowed statuses

- `CANDIDATE_DISCOVERY_READY`
- `CANDIDATE_DISCOVERY_EMPTY`
- `CANDIDATE_DISCOVERY_RESUMED`
- `CANDIDATE_DISCOVERY_NOT_PROVEN`
- `CANDIDATE_EXPORT_READY`
- `CANDIDATE_EXPORT_EMPTY`
- `CANDIDATE_EXPORT_NOT_PROVEN`
- `CANDIDATE_EXPORT_FAILED`

## Required rules

- Candidate timestamp is mandatory.
- Pair is mandatory.
- Engine/source identity is mandatory.
- Candidate ID must be deterministic from run context.
- Empty candidate export is valid and non-green.
- `candidate_source = COMPAT_FEATURE_DISCOVERY` is accepted for v1 only and must be read as compatibility mode, not live-engine parity.
- Candidate export can propose candidates; it cannot validate promotion readiness.
