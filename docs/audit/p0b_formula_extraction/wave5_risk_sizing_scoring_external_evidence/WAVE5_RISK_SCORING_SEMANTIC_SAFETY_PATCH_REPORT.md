# Wave 5 Risk / Scoring Semantic Safety Patch Report

## Scope

This patch is semantic-safety, readiness-carriage, cockpit-status, and test work only.

It does not:
- rewrite scoring or risk math
- add Kelly sizing
- add a covariance model
- implement Backtest Strategy Ladder
- mutate side
- add shorting
- add leverage

## Files modified

Production/state files:
- `src/scoring_backbone/break_even_filter.py`
- `src/scoring_backbone/scoring_runtime_support.py`
- `src/risk_backbone/risk_runtime_models.py`
- `src/risk_backbone/risk_runtime_explainability.py`
- `src/local_replay_runtime/replay_metrics_collector.py`
- `src/cockpit/state_replay_metrics.py`
- `src/cockpit/state_economic_sterilization.py`
- `src/cockpit/state_system_flow.py`
- `src/cockpit/templates/partials/_replay_metrics.html`
- `src/cockpit/templates/partials/_economic_sterilization.html`
- `src/cockpit/templates/partials/_system_flow.html`

Tests:
- `tests/test_scoring_backbone/test_break_even_filter.py`
- `tests/test_scoring_backbone/test_scoring_runtime.py`
- `tests/test_risk_backbone/test_risk_runtime.py`
- `tests/cockpit/test_state_replay_metrics.py`
- `tests/cockpit/test_state_economic_sterilization.py`
- `tests/cockpit/test_state_system_flow.py`

Docs/register:
- `docs/audit/P0B_FINAL_GAP_REGISTER.md`
- `docs/audit/p0b_formula_extraction/wave5_risk_sizing_scoring_external_evidence/WAVE5_EXTERNAL_AUDIT_VERDICT.md`
- `docs/audit/p0b_formula_extraction/wave5_risk_sizing_scoring_external_evidence/WAVE5_RISK_SCORING_SEMANTIC_SAFETY_PATCH_REPORT.md`
- `docs/audit/p0b_formula_extraction/wave5_risk_sizing_scoring_external_evidence/WAVE5_REMAINING_RISK_SIZING_GAPS.md`
- `docs/audit/p0b_formula_extraction/wave5_risk_sizing_scoring_external_evidence/WAVE5_CAPITAL_ADAPTIVE_SIZING_EVIDENCE.md`
- `docs/audit/p0b_formula_extraction/wave5_risk_sizing_scoring_external_evidence/WAVE5_GAP_REGISTER_UPDATE_RECOMMENDATIONS.md`

## Compatibility notes

- Existing break-even math is preserved.
- Existing scoring math is preserved.
- Existing risk math is preserved.
- Existing portfolio cap behavior is preserved.
- New fields are additive and default-safe for compatibility.

## 1. Cost completeness carriage status

Added additive status carriage across scoring/risk-facing seams:
- `cost_model_completeness_status`
- `fee_source_status`
- `impact_source_status`
- `fill_realism_status`
- `realized_slippage_status`

Readiness behavior:
- incomplete or unknown cost completeness now downgrades readiness
- `execution_ready=false`
- `promotion_ready=false`
- readiness reason codes include `COST_MODEL_INCOMPLETE`

Compatibility doctrine:
- scoring still computes
- raw/adjusted score math is unchanged
- the patch hardens readiness semantics rather than replacing core formulas

## 2. Break-even strict completeness behavior

`break_even_filter.py` now supports:
- `require_complete_cost_model=False` by default for compatibility
- optional strict completeness rejection

Strict mode behavior:
- if completeness is not `COMPLETE`
- `allowed=false`
- `reason_code=COST_MODEL_INCOMPLETE`

Non-strict mode behavior:
- math still evaluates
- metadata carries `partial_cost_model=true`
- `cost_gate_status=PARTIAL_COST_MODEL`

## 3. Risk missing input semantics

`RiskCandidate` now carries additive semantic statuses for:
- `execution_fragility`
- `market_toxicity`
- `spread_regime_penalty`
- `participation_penalty`
- micro-friction provenance
- overall `risk_input_completeness_status`

Allowed semantics now distinguish:
- `MEASURED`
- `GOVERNED_SOURCE`
- `NEUTRAL_BY_DESIGN`
- `MISSING`
- `NOT_PROVEN`
- `PARTIAL`
- `UNKNOWN`

Result:
- `0.0` no longer has to imply measured zero
- unknown or missing micro-risk seams no longer read as safe measured inputs

## 4. Participation penalty status

`participation_penalty_status` is explicit.

Current doctrine in the governed rail:
- default `NOT_PROVEN`
- no fake measured `0.0`
- no forced C/D mapping
- no new participation formula introduced

## 5. Small-capital readiness status

Replay/cockpit-facing status carriage now includes:
- `small_capital_viability_status`
- `min_notional_viability_status`
- `capital_fragmentation_status`

Current defaults remain explicit:
- `small_capital_viability_status=BLOCKED_BY_BACKTEST`
- `min_notional_viability_status=BLOCKED_BY_BACKTEST`
- `capital_fragmentation_status=NOT_PROVEN`

Meaning:
- fail-closed min-notional normalization is safety only
- 400-500 EUR viability is still not measured

## 6. Sizing doctrine / no Kelly decision

Replay/cockpit surfaces now expose:
- `sizing_doctrine=FIXED_FRACTION_VOL_TARGET_CAPS`
- `kelly_status=NOT_IMPLEMENTED_BY_DESIGN_FOR_NOW`
- `kelly_reason=crypto spot small-capital / high cost / high uncertainty / future research`

No Kelly sizing route was added.

## 7. Portfolio baseline caps vs covariance gap

Replay/cockpit surfaces now expose:
- `multi_asset_risk_control_status=BASELINE_CAPS_ONLY`
- `covariance_model_status=NOT_IMPLEMENTED`

Meaning:
- pair/gross/cluster/beta caps remain active
- full covariance control is not claimed

## 8. Drawdown promotion status

Replay/cockpit surfaces now expose:
- `true_net_equity_drawdown_status=NOT_PROVEN`
- `drawdown_proxy_promotion_grade=false`

Meaning:
- replay `drawdown_proxy` remains diagnostic only
- promotion-grade drawdown readiness stays blocked without a true net-equity rail

## 9. Cockpit readiness updates

System-flow and replay-facing cockpit adapters now carry:
- scoring cost completeness status
- risk input completeness status
- small-capital viability status
- sizing doctrine status
- portfolio multi-asset status
- true drawdown status

Green readiness is blocked when:
- cost model is partial/unknown
- small-capital viability is not proven
- true drawdown is not proven
- portfolio control is baseline-only

Expected CE labeling remains expected-only and does not become realized profitability.

## 10. Capital-adaptive sizing evidence status

See `WAVE5_CAPITAL_ADAPTIVE_SIZING_EVIDENCE.md`.

Wave 5 patch result for capital doctrine:
- config/profile-driven capital adaptation is proven in `portfolio_minimal`
- live governed free-balance adaptation is not proven
- min-notional is fail-closed at execution stage
- sizing-stage viability awareness remains partial

## 11. Tests run

Syntax:
- `PYTHONPYCACHEPREFIX=.test_tmp\\pycache_wave5_semantic python -m py_compile ...`
- result: PASS

Targeted bands:
- scoring: `27 passed`
- risk full requested band after escalated rerun: `30 passed`
- portfolio minimal: `100 passed`
- cockpit: `69 passed`
- ML confidence: `10 passed`
- Engine C/D: `228 passed`

Separated environment note:
- the first sandboxed risk-band run hit `PermissionError [WinError 5]` under `build\\pytest-risk-runtime-daily-breaker`
- that issue was separated from logic and cleared by the escalated rerun

## 12. Remaining gaps

- runtime hard rejection outside strict break-even mode remains doctrine-dependent
- measured small-capital viability artifacts are still absent
- live balance adaptation is not proven
- true executed-only net return is still absent
- true net-equity max drawdown is still absent
- full covariance model is still future work
- Kelly sizing remains future research only
- capital-fragmentation guard is not proven
- min-notional is proven fail-closed, but not proven as sizing-stage viability awareness
