# 2026-04-20 - Rate Limiter Warn / Block Alignment

## Docs Governants

- `docs/production_deployment_plan/18_CODE_VS_PLAN_AUDIT_AND_WORK_PLAN.md`
- `docs/production_deployment_plan/update_audit/2026-04-20_codex_critical_path_micro_live_verify_and_close.md`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/26_UPDATE_AUDIT_PACK_TEMPLATE.md`

## Objective

Close the remaining `section 2.3` rate-limiter wording gap without widening the bounded Binance REST client seam:

- preserve the current preemptive local quota tracker
- add explicit official-quota warning/block semantics from venue headers
- prove the behavior through the existing limiter and `rest_client.py` hooks

## Current Code Seam

- limiter: `src/venue_adapters/binance_spot/rate_limiter.py`
- REST consumer: `src/venue_adapters/binance_spot/rest_client.py`
- focused proofs:
  - `tests/test_venue_adapters/test_binance_spot/test_rate_limiter.py`
  - `tests/test_venue_adapters/test_binance_spot/test_rest_client.py`

## Files Changed

- `src/venue_adapters/binance_spot/rate_limiter.py`
- `tests/test_venue_adapters/test_binance_spot/test_rate_limiter.py`
- `tests/test_venue_adapters/test_binance_spot/test_rest_client.py`
- `docs/production_deployment_plan/update_audit/2026-04-20_codex_critical_path_micro_live_verify_and_close.md`

## Claims Implemented

- `BinanceApiRateLimiterConfig` now owns explicit official-quota thresholds:
  - `official_request_weight_warn_ratio = 0.80`
  - `official_request_weight_block_ratio = 0.95`
  - `official_request_weight_block_window_s = 60.0`
- `BinanceApiRateLimiterSnapshot` now exposes:
  - `official_request_weight_used_1m`
  - `official_request_weight_quota_ratio`
  - `official_request_weight_warn_active`
  - `official_request_weight_block_until_ms`
  - `official_request_weight_block_active`
- Header sync from `X-MBX-USED-WEIGHT-1M` now does two things explicitly:
  - raises warning state once the official quota ratio reaches `0.80`
  - installs a `60s` local block window once the official quota ratio reaches `0.95`
- The existing preemptive local ceiling is preserved. This slice adds an explicit official-quota overlay; it does not relax the bounded pre-request guard.
- `BinanceRestClient` still uses the same reserve/observe seam; no new client-side orchestration path was introduced.

## Tests and Proof

- `PYTHONPYCACHEPREFIX=.test_tmp/pycache_rate_limiter python -m py_compile src/venue_adapters/binance_spot/rate_limiter.py tests/test_venue_adapters/test_binance_spot/test_rate_limiter.py tests/test_venue_adapters/test_binance_spot/test_rest_client.py` -> pass
- `python -m pytest -q tests/test_venue_adapters/test_binance_spot/test_rate_limiter.py tests/test_venue_adapters/test_binance_spot/test_rest_client.py --basetemp=.test_tmp/pytest_rate_limiter` -> `25 passed`
- Focused limiter proofs now cover:
  - `WARN` at `80%` official quota
  - `BLOCK 60s` at `95%` official quota
  - reserve unblock once the `60s` window expires
  - REST-client landing via injected limiter config

## Deferred / Not Done

- no change to the preemptive local request-weight ceiling defaults
- no change to broader Binance execution adapter behavior
- no attempt to close `section 2.1` quant-anchor verification
- no attempt to close the repo-global guardrail or DAG baselines

## Guardrails

- `python scripts/run_engineering_guardrails.py` -> repo-global `new_violations=5`, unchanged and outside this slice
- `python scripts/run_dag_check.py` -> unchanged repo-global baseline `9 violations`

## Completion Status

`COMPLETE` for the narrowed `section 2.3` rate-limiter warn/block alignment slice.

## Next Safe Step

Keep the critical-path pilot honest:

- audit `section 2.1` quant anchors separately
- or clean the repo-global guardrails / DAG baseline if full `GREENLIGHT` proof is required
