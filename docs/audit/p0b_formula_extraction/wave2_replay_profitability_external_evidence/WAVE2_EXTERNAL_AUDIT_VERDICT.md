# Wave 2 External Audit Verdict

## Status
- Applied as a semantic-safety patch, not a producer-formula rewrite.

## Final operator semantics
- `ce_net` remains the compatibility field in replay artifacts, but operator-facing surfaces now label it as `Expected CE net`.
- `ce_net` is explicitly caveated as expected CE over replay DTR records, not realized profitability.
- `exec_rate` remains `executed_count / total_records`.
- Operator-facing replay surfaces now label this explicitly as `Exec rate (executed / total records)`.
- `drawdown_proxy` remains a gross-return proxy and is explicitly labeled non-promotion-grade.
- Replay economics cannot render green when:
  - the source is missing or stale,
  - `total_records == 0`,
  - the replay sample is insufficient,
  - or the replay cost model is incomplete.

## Compatibility
- No producer field was destructively renamed.
- Existing `ce_net`, `expected_cost_mean`, `realized_cost_mean`, and `drawdown_proxy` remain intact.
- Additive metadata and labels now carry the semantic meaning needed by the cockpit and audit layer.

## Validation outcome
- Focused replay/cockpit semantic-safety tests passed after the patch.
- Broad replay/backtest/cockpit regression coverage was rerun; remaining nonzero exit was caused by filesystem permission failures and pre-existing unrelated build-root test issues, not by Wave 2 semantic regressions.
