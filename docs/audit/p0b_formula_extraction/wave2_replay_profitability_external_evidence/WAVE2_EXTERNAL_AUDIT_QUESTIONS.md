# Wave 2 External Audit Questions

## CE semantics
1. Is all-record `ce_net = sum(ce_expected)` a deliberate doctrine choice, including hard-blocked, ranking-rejected, and phantom records?
2. Should replay output rename `ce_net` to `expected_ce_net` to prevent realized-PnL confusion?
3. Should row-level cockpit decision trace expose `ce_expected` explicitly instead of relabeling it as `ce_net`?

## Cost semantics
4. Are replay expected-cost components intentionally limited to spread, slippage, and latency penalty?
5. Are fees and impact folded into upstream fields, or absent from this replay seam?
6. Is realized replay cost intentionally `expected_cost * execution_factor`, with no separate partial-fill penalty term?
7. Should replay economics expose executed-only realized-cost views in addition to all-record means?

## Exec/block semantics
8. Is cockpit `exec_rate` intentionally `executed_count / total_records`, or should that be relabeled `exec_rate_total`?
9. Does doctrine also require a distinct `selected_execution_rate = executed_count / selected_count`?
10. Should ablation `_block_rate` be renamed to `non_execution_rate` or `block_rate_proxy`?

## Drawdown semantics
11. Is `drawdown_proxy` strictly informational, or can any downstream gate consume it?
12. Is a true net-equity drawdown seam required before any promotion or backtest-verdict reliance?

## Reconciliation and tests
13. Should pair and engine CE reconciliation be asserted with tolerance in tests?
14. Should tests explicitly prove `executed_count <= selected_count <= total_records`?
15. Should tests explicitly prove mutual exclusivity of hard-blocked, rejected-ranking, and phantom states?

## Cockpit safety
16. Should replay KPI state expose `PLACEHOLDER_DEFAULT`, `INSUFFICIENT_SAMPLE`, and `STALE_ARTIFACT` explicitly, not only numeric defaults?
17. Should `ce_net` be forbidden from rendering as green when `total_records == 0`?
18. Should `exec_rate` always display its denominator class in operator-facing UI?
