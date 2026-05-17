# Wave 5 Gap Register Update Recommendations

Do not update the master register from this evidence pack automatically. These are recommended additions or follow-up moves only.

## Recommended new Wave 5 open gaps

| Proposed Gap ID | Area | Severity | Recommended status | Gap / Problem | Why it matters | Evidence |
|---|---|---|---|---|---|---|
| W5-OPEN-001 | Scoring / risk coherence | P1_REQUIRED_BEFORE_SHADOW | OPEN | Governed scoring/risk rails do not consume Wave 3 `cost_model_completeness_status`, `fee_source_status`, `impact_source_status`, or `fill_realism_status`. | Runtime score/risk acceptance can remain disconnected from replay cost-completeness safety doctrine. | Search across `src/scoring_backbone`, `src/risk_backbone`, `src/portfolio_minimal`, `src/engines`, `src/execution_backbone`, and `src/interface_contracts` returned `NO_MATCH` for those statuses. |
| W5-OPEN-002 | Small-capital viability | P1_REQUIRED_BEFORE_SHADOW | BLOCKED_BY_BACKTEST | Replay/cockpit small-capital exclusion exists only as `NOT_PROVEN` status, not a measured exclusion study. | 400-500 EUR viability cannot be claimed without measured exclusion rates, pair fragmentation, and min-notional survival evidence. | `src/local_replay_runtime/replay_metrics_collector.py`; `src/cockpit/state_replay_metrics.py`; `src/cockpit/state_economic_sterilization.py` |
| W5-OPEN-003 | Position sizing doctrine | P3_RESEARCH | NOT_PROVEN_NEEDS_EXTERNAL_AUDIT | Kelly / fractional Kelly sizing was not found in the inspected rails. | Future capital-ladder and scientific sizing review need explicit doctrine: intentionally absent vs missing seam. | repo-wide `Kelly|kelly|fractional_kelly` search returned `NO_MATCH` |
| W5-OPEN-004 | Portfolio multi-asset control | P2_REQUIRED_BEFORE_MICRO_LIVE | NOT_PROVEN_NEEDS_EXTERNAL_AUDIT | 12-pair multi-asset control is proven only through pair/gross/cluster/beta caps, not a richer cross-pair covariance rail. | Multi-pair production claims may overstate diversification control if cluster/beta is insufficient. | `gross_exposure_calculator.py`, `gross_cap_guard.py`, `projected_beta_checker.py`, `cluster_cap_guard.py` |
| W5-OPEN-005 | Cockpit readiness semantics | P2_REQUIRED_BEFORE_MICRO_LIVE | IN_PROGRESS | Feature/runtime and replay false-green protections are strong, but portfolio and small-capital readiness states are still sparse. | A green operator verdict could still under-communicate missing small-capital or runtime cost-completeness governance. | `state_system_flow.py`, `state_feature_bridge.py`, `state_replay_metrics.py`, `state_economic_sterilization.py` |

## Recommended capital-aware follow-up gaps

| Proposed Gap ID | Area | Severity | Recommended status | Gap / Problem | Why it matters | Evidence |
|---|---|---|---|---|---|---|
| W5-CAPITAL-001 | Live balance adaptation | P1_REQUIRED_BEFORE_SHADOW | NOT_PROVEN_NEEDS_EXTERNAL_AUDIT | Governed live/shadow free-quote-balance adaptation into sizing was not proven. | Capital should be account-state driven on live/shadow rails, not only config-profiled. | `src/portfolio_minimal/portfolio_orchestrator.py`; `WAVE5_CAPITAL_ADAPTIVE_SIZING_EVIDENCE.md` |
| W5-CAPITAL-002 | Adaptive sizing doctrine | P1_REQUIRED_BEFORE_SHADOW | IN_PROGRESS | Config/profile-driven adaptive sizing is proven, but governed live account-state doctrine is still incomplete. | Capital changes must not require code rewrites and should remain data/config driven. | `src/portfolio_minimal/allocation_router/base_size_builder.py`; `src/portfolio_minimal/allocation_router/vol_target_sizer.py`; `WAVE5_CAPITAL_ADAPTIVE_SIZING_EVIDENCE.md` |
| W5-CAPITAL-003 | Small-capital fragmentation | P2_REQUIRED_BEFORE_MICRO_LIVE | BLOCKED_BY_BACKTEST | 12-pair capital fragmentation risk is not measured. | 400-500 EUR may be structurally too fragmented even when single-order normalization is safe. | `WAVE5_CAPITAL_ADAPTIVE_SIZING_EVIDENCE.md`; `31_BACKTEST_STRATEGY_LADDER.md` |
| W5-CAPITAL-004 | Min-notional feasibility before execution | P2_REQUIRED_BEFORE_MICRO_LIVE | OPEN | Min-notional blocking is proven fail-closed at execution stage, but sizing-stage feasibility awareness is not proven. | Small-capital users need earlier viability signaling than late-stage execution refusal alone. | `tests/test_execution_backbone/test_execution_runtime.py`; `WAVE5_CAPITAL_ADAPTIVE_SIZING_EVIDENCE.md` |
| W5-CAPITAL-005 | Cost recomputation after cap reduction | P2_REQUIRED_BEFORE_MICRO_LIVE | NOT_PROVEN_NEEDS_EXTERNAL_AUDIT | Phantom guard rescales expected cost and edge, but full fee/impact/slippage recomputation after cap reduction is not proven. | Capital changes can alter execution realism and should not be inferred from a single expected-cost seam. | `src/portfolio_minimal/allocation_router/phantom_trade_guard.py`; `WAVE5_CAPITAL_ADAPTIVE_SIZING_EVIDENCE.md` |
| W5-CAPITAL-006 | Capital ladder dependency | P1_REQUIRED_BEFORE_SHADOW | BLOCKED_BY_BACKTEST | 400 / 500 / 1500 / 4000 capital viability still depends on Backtest Strategy Ladder scenario artifacts. | Promotion claims on small or changing capital remain incomplete without scenario evidence. | `docs/audit/p0b_formula_extraction/31_BACKTEST_STRATEGY_LADDER.md`; `WAVE5_CAPITAL_ADAPTIVE_SIZING_EVIDENCE.md` |

## Recommended possible future resolved moves after a later patch

These are not resolved by this evidence pack:
- move `W3-OPEN-007` only after a measured small-capital exclusion artifact exists
- move `W23-OPEN-001` only after executed-only realized net-return rail exists
- move `W23-OPEN-002` only after true net-equity max drawdown exists
- move `W3-OPEN-001` and `W3-OPEN-002` only after replay fee/impact provenance is explicit or doctrinally closed with evidence
- move `W5-OPEN-001` only if runtime score/risk explicitly consumes cost-completeness safety or an external doctrine declares cockpit-only gating sufficient

## Recommended future calibration dependencies

- pair-level small-capital viability report by capital bucket
- fee / impact / slippage parity mapping before promotion-grade profitability claims
- if sizing doctrine changes later, OOS comparison of current fixed-fraction / vol-target / cap rail versus any alternative sizing doctrine

## Recommended dashboard follow-ups

- add explicit portfolio-readiness state for small-capital viability
- add explicit runtime/cockpit display note where score/risk acceptance is present but replay economics is still partial
- keep `Expected CE net` labeling and never collapse it into realized profitability language
- keep artifact/config capital flexibility separate from measured capital viability

## Recommended shadow/live blockers

- executed-only realized net-return rail
- true net-equity max drawdown rail
- measured small-capital exclusion report
- explicit runtime doctrine for how cost-completeness partiality should affect shadow/live promotion
- governed live balance source for capital-aware sizing if live/shadow readiness is claimed
