# Capital Fragmentation And Min-Notional Doctrine

Purpose:
- define sizing-stage viability semantics before final execution normalization

## Planned notional doctrine

```text
planned_notional = planned_qty * planned_price

if planned_notional < min_notional * safety_buffer:
  candidate_status = NOT_VIABLE_MIN_NOTIONAL
  reason_code = SIZE_BELOW_MIN_NOTIONAL_BEFORE_EXECUTION
```

## Minimum viable capital per pair

```text
minimum_viable_capital_per_pair =
  max(min_notional * safety_multiplier, expected_trade_notional_min)
```

## Capital fragmentation doctrine

```text
max_viable_pairs =
  floor(usable_sizing_capital / minimum_viable_capital_per_pair)

if selected_pair_count > max_viable_pairs:
  capital_fragmentation_status = PAIR_UNIVERSE_TOO_WIDE_FOR_CAPITAL
```

## Rules

- do not auto-remove pairs unless configured by a governed capital-profile artifact
- emit warning or recommendation when fragmentation is detected
- VPS must respect `max_active_pairs` from the capital-profile artifact
- execution-stage min-notional fail-closed behavior remains the compatibility safety path
- sizing-stage min-notional awareness is a doctrine/spec layer until runtime integration exists

## Status doctrine

Allowed status examples:

- `NOT_VIABLE_MIN_NOTIONAL`
- `PAIR_UNIVERSE_TOO_WIDE_FOR_CAPITAL`
- `NEEDS_MORE_DATA`
- `NOT_PROVEN`

## Promotion note

Small capital must reduce the pair universe by measured viability, not by preference or static config.
