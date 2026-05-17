# C/D Cost And Execution Realism Evidence

## Engine C

| Field / status | Classification | Evidence |
|---|---|---|
| `expected_cost` | `PROVEN_CONSUMED` | local cost feasibility, forecast, scoring candidate |
| `expected_total_cost` | `NOT_PROVEN` | not found on Engine C local seam |
| `cost_model_completeness_status` | `NOT_PROVEN` | scoring runtime supports it, Engine C builder does not populate it |
| `fee_source_status` | `NOT_PROVEN` | not populated by Engine C |
| `impact_source_status` | `NOT_PROVEN` | not populated by Engine C |
| `fill_realism_status` | `NOT_PROVEN` | not populated by Engine C |
| `realized_slippage_status` | `NOT_PROVEN` | not populated by Engine C |
| `execution_rate` | `NOT_PROVEN` | no per-engine execution rate export |
| `partial_fill_rate` | `NOT_PROVEN` | no per-engine export found |
| `no_fill_rate` | `NOT_PROVEN` | no per-engine export found |
| min-notional viability | `BLOCKED_BY_WAVE5` | only global small-capital doctrine exists |
| capital bucket status | `BLOCKED_BY_WAVE5` | no engine-specific bucket artifact found |

## Engine D

| Field / status | Classification | Evidence |
|---|---|---|
| `expected_cost` | `PROVEN_CONSUMED` | local cost feasibility, forecast, scoring candidate |
| `expected_total_cost` | `NOT_PROVEN` | not found on Engine D local seam |
| `cost_model_completeness_status` | `NOT_PROVEN` | scoring runtime supports it, Engine D builder does not populate it |
| `fee_source_status` | `NOT_PROVEN` | not populated by Engine D |
| `impact_source_status` | `NOT_PROVEN` | not populated by Engine D |
| `fill_realism_status` | `NOT_PROVEN` | not populated by Engine D |
| `realized_slippage_status` | `NOT_PROVEN` | not populated by Engine D |
| `execution_rate` | `NOT_PROVEN` | no per-engine execution rate export |
| `partial_fill_rate` | `NOT_PROVEN` | no per-engine export found |
| `no_fill_rate` | `NOT_PROVEN` | no per-engine export found |
| min-notional viability | `BLOCKED_BY_WAVE5` | only global small-capital doctrine exists |
| capital bucket status | `BLOCKED_BY_WAVE5` | no engine-specific bucket artifact found |

## Common Evidence

Support exists in shared scoring/risk backbones:

```text
src/scoring_backbone/scoring_runtime_support.py
  ScoringCandidateInput carries:
    cost_model_completeness_status
    fee_source_status
    impact_source_status
    fill_realism_status
    realized_slippage_status

src/risk_backbone/risk_runtime_models.py
  RiskCandidate carries the same statuses
```

But C/D local builders do not populate them:

```text
src/engines/engine_c/engine_c_runtime_support.py
src/engines/engine_d/engine_d_runtime_support.py
  build_scoring_candidate(...) passes expected_cost and expected_ce,
  but no explicit Wave 3/5 completeness statuses
```

## Conclusion

- Cost semantics are present for both engines at the expected-only level.
- Promotion-grade execution realism remains globally partial and engine-specific carriage is not proven.
- This blocks clean promotion claims even if local engine math is otherwise viable.

