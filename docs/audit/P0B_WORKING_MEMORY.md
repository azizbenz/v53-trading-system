# P0B Working Memory

Purpose:
- local markdown checkpoint for in-flight audit and patch work
- survive workspace copy, disk-access issues, or thread interruption
- resume work without depending only on chat history

Update rule:
- update this file after each meaningful correction, evidence-pack step, or register update
- date every checkpoint entry
- do not delete history; append newer entries above older ones

## Active checkpoint

Date:
- `2026-04-30`

Current workspace:
- `E:\claude  v5.3\v53_trading_system`

Current slice:
- Wave 5 Capital-Aware Strategy Ladder / Pair Universe Promotion Patch

Core invariants:
- no engine rewrite
- no signal logic rewrite
- no side mutation
- no shorting
- no leverage
- no Kelly implementation
- no covariance implementation
- no invented measured capital results
- expected CE remains expected-only
- live eligibility requires backtest + replay + shadow + fresh artifact

Completed immediately before this checkpoint:
- Wave 5 risk / sizing / scoring semantic-safety patch completed
- `docs/audit/P0B_FINAL_GAP_REGISTER.md` updated with dated Wave 5 and Wave 5 capital rows
- `docs/audit/p0b_formula_extraction/wave5_risk_sizing_scoring_external_evidence/WAVE5_CAPITAL_ADAPTIVE_SIZING_EVIDENCE.md` created
- capital-aware ladder/spec docs created for pair-universe promotion, VPS enforcement, executed-only return, true drawdown, live balance sizing, fragmentation, and post-cap cost recomputation doctrine

Work resumed from:
- maintain the register and working-memory files after each further correction
- keep measured capital artifacts, live balance integration, executed-only return implementation, and true drawdown implementation open until real evidence exists

Current canonical files for this slice:
- `docs/audit/p0b_formula_extraction/31_BACKTEST_STRATEGY_LADDER.md`
- `docs/audit/p0b_formula_extraction/wave5_risk_sizing_scoring_external_evidence/CAPITAL_PROFILE_ARTIFACT_CONTRACT.md`
- `docs/audit/p0b_formula_extraction/wave5_risk_sizing_scoring_external_evidence/VPS_CAPITAL_PROFILE_ENFORCEMENT_SPEC.md`
- `docs/audit/p0b_formula_extraction/wave5_risk_sizing_scoring_external_evidence/TRUE_EXECUTED_ONLY_NET_RETURN_SPEC.md`
- `docs/audit/p0b_formula_extraction/wave5_risk_sizing_scoring_external_evidence/TRUE_NET_EQUITY_DRAWDOWN_SPEC.md`
- `docs/audit/p0b_formula_extraction/wave5_risk_sizing_scoring_external_evidence/LIVE_BALANCE_SIZING_DOCTRINE.md`
- `docs/audit/p0b_formula_extraction/wave5_risk_sizing_scoring_external_evidence/CAPITAL_FRAGMENTATION_AND_MIN_NOTIONAL_DOCTRINE.md`
- `docs/audit/p0b_formula_extraction/wave5_risk_sizing_scoring_external_evidence/COST_RECOMPUTATION_AFTER_CAP_REDUCTION_SPEC.md`
- `docs/audit/p0b_formula_extraction/wave5_risk_sizing_scoring_external_evidence/WAVE5_CAPITAL_AWARE_STRATEGY_LADDER_PATCH_REPORT.md`
- `docs/audit/P0B_FINAL_GAP_REGISTER.md`

Capital doctrine to preserve:
- backtest proposes
- replay validates
- shadow confirms
- VPS enforces
- VPS must not choose pairs freely from a static global list
- bucket selection must use the lower proven capital bucket

If work must resume in a copied workspace:
1. verify the copied workspace contains the latest modified docs under `docs/audit/`
2. reopen from the copied root
3. read this file first
4. then read:
   - `docs/audit/P0B_FINAL_GAP_REGISTER.md`
   - `docs/audit/p0b_formula_extraction/wave5_risk_sizing_scoring_external_evidence/WAVE5_CAPITAL_ADAPTIVE_SIZING_EVIDENCE.md`
   - `docs/audit/p0b_formula_extraction/31_BACKTEST_STRATEGY_LADDER.md`

## History

- `2026-04-30` Wave 5 capital-aware ladder/spec patch completed at documentation/register level
- `2026-04-30` initial working-memory checkpoint created for Wave 5 capital-aware ladder continuation
