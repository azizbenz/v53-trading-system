# ML Forbidden Directional Keys

## Forbidden keys
- `direction_up_300s_fee_safe`
- `buy_probability`
- `sell_probability`
- `market_will_go_up`
- `side`
- `long`
- `short`
- `label`
- `direct_trade_decision`

## Enforcement
- ML supplementary refs:
  - `ML_DIRECTIONAL_REF_FORBIDDEN`
- Regime supplementary refs:
  - `REGIME_DIRECTIONAL_REF_FORBIDDEN`

## Reason
- these keys introduce or imply direction
- V5.3 ML on the governed VPS rail is non-sovereign
- side must remain owned by the canonical engine path
- indirect layers may modulate confidence/penalty only

## Explicit non-goals
- no buy/sell classifier transport
- no long/short classifier transport
- no hidden prediction target transport
- no future-return label transport
