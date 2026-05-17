# Backtest Missing Items And Patch Recommendations

## Missing items

1. No explicit feature-store / gold-store runner input was found.
2. No canonical fast candidate-discovery backtest stage was found.
3. No candidate timestamp export was found on the canonical replay runner.
4. No candidate raw-window extractor was found.
5. No dedicated candidate-window depth20 replay loader was found.
6. No measured capital-bucket scenario generator was found in the replay runner.
7. No measured `allowed_pairs` / `blocked_pairs` / `max_active_pairs` production was found from real bucket scenarios.
8. No measured ladder artifacts were found for `400 / 500 / 1500 / 4000`.
9. Current replay/backtest still carries partial fee/impact/fill/parity states that correctly block promotion-grade claims.

## Recommended patch order

1. Add the actual Strategy Ladder runner:
   `feature/gold store -> candidate discovery -> candidate event export -> raw-window extraction -> detailed replay`.
2. Wire measured capital-bucket scenario generation into the runner and produce `capital_profiles/{bucket}.json` from real runs.
3. Keep true economics, cost/fill/depth, and sample-size rails fail closed while generating measured bucket/pair/strategy artifacts.
4. Only after that, refine Local IA Lab / cockpit ergonomics and any deeper ML research integrations.

## Before running Strategy Ladder

Required before the first serious ladder run:

- explicit backtest entrypoint for ladder stages
- candidate-event export with timestamp / pair / engine/source
- raw-window extraction
- detailed depth replay stage
- measured bucket scenario generation

Can wait until after the first measured backtest:

- broader cockpit polish
- additional Local IA Lab monitoring refinements
- further ML research tooling not required for core ladder proof
