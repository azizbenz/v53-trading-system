## Objective

Replace the naked Engine D marginal-value gate constant with an explicit local governance seam, without inventing a false upstream `THR-W01` resolver while the MD corpus still uses `THR-W01` for conflicting meanings.

## Docs Governants

- `22_ENGINE_D_SPEC_REENTRY_SECOND_CHANCE.md`
- `24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `25_UPDATE_AUDIT_PROTOCOL.md`
- `26_UPDATE_AUDIT_PACK_TEMPLATE.md`
- `30_PROMOTION_CALIBRATION_REGISTER.md`

## Current Code Seam

- Local marginal gate in [engine_d_runner.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_d/engine_d_runner.py)
- Current score math in [signal_math_d.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_d/signal_math_d.py)
- New local governance seam in [marginal_value_estimator_d.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_d/marginal_value_estimator_d.py)

## Placement

This lands as a local Engine D ownership seam only.

It does not add a `scoring_backbone` or `risk_backbone` resolver because the current MD corpus is ambiguous:
- docs 11/13 bind `THR-W01` to risk drawdown warning
- docs 19/20/21/22 also reuse `THR-W01_floor` language for EV-net / marginal-EV floors

Per doc 24, current code remains source of truth when docs conflict.

## Files Changed

- [marginal_value_estimator_d.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_d/marginal_value_estimator_d.py)
- [engine_d_runner.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_d/engine_d_runner.py)
- [__init__.py](/E:/claude%20%20v5.3/v53_trading_system/src/engines/engine_d/__init__.py)
- [test_marginal_value_estimator_d.py](/E:/claude%20%20v5.3/v53_trading_system/tests/test_engines/test_engine_d/test_marginal_value_estimator_d.py)

## Claims Implemented

1. Engine D no longer carries a naked local `0.56` marginal gate constant in the runner.
2. The current marginal-value seam is explicitly centralized in a frozen typed object.
3. The seam records:
   - `THR-D_MARGINAL_EV_FLOOR`
   - inherited doc target `THR-W01`
   - local status `DOC_CONFLICT_BLOCKED`
4. The runner now consumes a testable helper seam instead of a magic number.

## Tests and Proof

- `python -m py_compile src/engines/engine_d/marginal_value_estimator_d.py src/engines/engine_d/engine_d_runner.py src/engines/engine_d/__init__.py tests/test_engines/test_engine_d/test_marginal_value_estimator_d.py tests/test_engines/test_engine_d/test_engine_d.py`
- `rtk pytest -q tests/test_engines/test_engine_d/test_marginal_value_estimator_d.py tests/test_engines/test_engine_d/test_engine_d.py --basetemp=.test_tmp/pytest`
- `rtk pytest -q tests/test_engines/test_engine_d --basetemp=.test_tmp/pytest`
- `python scripts/run_engineering_guardrails.py`
- `python scripts/run_dag_check.py`

## Deferred / Not Done

- No upstream signed resolver was added for `THR-D_MARGINAL_EV_FLOOR`.
- No direct mapping from `THR-W01` was implemented.
- No migration from `marginal_value_score` to a typed `marginal_EV` object was attempted.

## Risks / Open Questions

- The MD corpus currently conflicts on `THR-W01` semantics.
- Reusing the current `risk_runtime_drawdown_calibration.py` seam directly would likely be incorrect unless the threshold catalog is disambiguated first.
- A later slice should either:
  - split the EV-floor threshold family from drawdown warning explicitly, or
  - freeze one authoritative cross-doc meaning for `THR-W01`.

## Completion Status

`PARTIAL`

This slice closes local naked-constant ownership, but upstream governance remains blocked by doc conflict.

## Next Safe Step

Do not invent a false `THR-W01` resolver.

Next safe step is either:
1. disambiguate `THR-W01` meaning across docs 11/13/19/20/21/22, then add the upstream resolver, or
2. continue on another real local seam that does not depend on the conflicting `THR-W01` meaning.
