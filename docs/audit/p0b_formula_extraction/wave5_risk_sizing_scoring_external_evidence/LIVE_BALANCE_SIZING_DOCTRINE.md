# Live Balance Sizing Doctrine

Purpose:
- define the governed capital base for shadow/live bucket selection and sizing readiness

## AccountBalanceSnapshot

Required fields:

- `free_quote_balance`
- `reserved_quote_balance`
- `pending_order_reserve`
- `open_order_reserved`
- `spot_inventory_value`
- `usable_sizing_capital`
- `balance_timestamp`
- `balance_source`
- `stale_balance_status`

## Formula

```text
usable_sizing_capital =
  free_quote_balance
  - reserve_buffer
  - pending_order_reserve
```

## Rules

- backtest may use config capital
- shadow/live must use governed account-state or explicit `CONFIG_CAPITAL_ONLY` status
- stale balance cannot green live sizing readiness
- missing balance cannot select a higher bucket
- missing balance must not default to safe zero or infinite capital
- spot inventory value may be reported separately but must not silently replace free quote balance in bucket selection

## Readiness doctrine

Allowed status examples:

- `GOVERNED_ACCOUNT_STATE`
- `CONFIG_CAPITAL_ONLY`
- `STALE_BALANCE`
- `BALANCE_SOURCE_NOT_PROVEN`

## Promotion note

Live/shadow capital-bucket enforcement is incomplete until governed account-state balance sourcing is proven.
