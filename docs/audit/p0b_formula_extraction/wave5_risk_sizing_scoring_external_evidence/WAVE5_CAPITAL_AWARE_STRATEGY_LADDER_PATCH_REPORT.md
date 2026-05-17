# Wave 5 Capital-Aware Strategy Ladder Patch Report

Role boundary:
- architecture/spec/status patch only
- no strategy rewrite
- no engine rewrite
- no measured capital results invented

## Files updated

- `docs/audit/p0b_formula_extraction/31_BACKTEST_STRATEGY_LADDER.md`
- `docs/audit/p0b_formula_extraction/wave5_risk_sizing_scoring_external_evidence/CAPITAL_PROFILE_ARTIFACT_CONTRACT.md`
- `docs/audit/p0b_formula_extraction/wave5_risk_sizing_scoring_external_evidence/VPS_CAPITAL_PROFILE_ENFORCEMENT_SPEC.md`
- `docs/audit/p0b_formula_extraction/wave5_risk_sizing_scoring_external_evidence/TRUE_EXECUTED_ONLY_NET_RETURN_SPEC.md`
- `docs/audit/p0b_formula_extraction/wave5_risk_sizing_scoring_external_evidence/TRUE_NET_EQUITY_DRAWDOWN_SPEC.md`
- `docs/audit/p0b_formula_extraction/wave5_risk_sizing_scoring_external_evidence/LIVE_BALANCE_SIZING_DOCTRINE.md`
- `docs/audit/p0b_formula_extraction/wave5_risk_sizing_scoring_external_evidence/CAPITAL_FRAGMENTATION_AND_MIN_NOTIONAL_DOCTRINE.md`
- `docs/audit/p0b_formula_extraction/wave5_risk_sizing_scoring_external_evidence/COST_RECOMPUTATION_AFTER_CAP_REDUCTION_SPEC.md`
- `docs/audit/P0B_FINAL_GAP_REGISTER.md`

## What this patch closes

- capital-aware pair-universe promotion doctrine is now explicit in the ladder spec
- capital-profile artifact contract is defined
- VPS enforcement behavior for capital buckets is defined
- executed-only net-return spec is defined
- true net-equity drawdown spec is defined
- live balance sizing doctrine is defined
- sizing-stage min-notional and fragmentation doctrine is defined
- post-cap cost recomputation doctrine is defined
- the capital-aware section is documented as additive to the existing backtest workflow, not a strategy-method replacement

## What this patch does not close

- measured capital artifacts
- runtime integration of capital profile enforcement
- live governed balance sourcing
- executed-only net-return implementation
- true net-equity drawdown implementation
- measured 400 / 500 / 1500 / 4000 viability

## Tests

- no code touched
- no tests required by this patch slice

## Remaining gaps

- capital profile artifacts remain absent as measured files
- live/shadow usable-capital sourcing remains not proven
- sizing-stage min-notional awareness remains a doctrine/spec until runtime integration exists
- capital fragmentation remains not measured
- post-cap explicit fee/impact/slippage recomputation remains not proven
