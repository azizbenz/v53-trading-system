# True Executed-Only Net Return Spec

Purpose:
- define a promotion-grade realized profitability rail distinct from expected CE

## Formula

```text
executed_only_net_return =
  sum(gross_return_i - realized_total_cost_i
      for records where execution_state in {EXECUTED, REDUCED})
```

## Required companion fields

- `executed_count`
- `reduced_count`
- `selected_count`
- `total_records`
- `missing_realized_cost_count`

## Rules

- `expected_ce_net` remains separate and expected-only
- blocked, rejected, phantom, and non-executed records are excluded
- if `realized_total_cost` is missing for any executed/reduced records, status becomes `EXECUTED_NET_RETURN_NOT_PROVEN`
- this rail must not silently fall back to expected cost

## Status doctrine

Allowed status examples:

- `MEASURED`
- `PARTIAL`
- `EXECUTED_NET_RETURN_NOT_PROVEN`
- `NOT_AVAILABLE`

## Promotion note

Without this rail:
- expected CE must not be presented as realized profitability
- promotion-grade performance remains incomplete
