# Wave 4 Microstructure Consumer Map Evidence

This table classifies the traced consumer status for the main canonical microstructure features. Registry intent alone is not treated as runtime proof.

| Feature / family | Traced consumer status | Evidence | Notes |
| --- | --- | --- | --- |
| `kyle_lambda` | `DIRECT_ENGINE_INPUT`, `COST_GATE_INPUT` | Engine C continuation validator, Engine A cost-feasibility uplift | Registry also mentions execution; direct governed execution consumer not proven here. |
| `kyle_lambda_cost_uplift` | `COST_GATE_INPUT` | Engine A cost-feasibility | Provenance seam, not canonical raw estimator output field. |
| `ofi.cont_kukanov` | `DIRECT_ENGINE_INPUT`, `REGIME_CONTEXT_INPUT` | Engine C continuation input, Engine A `ofi_flow_score`, LOB regime `_ofi_short_window` | A uses caller-owned scalar mapping, not forced canonical-to-shared scoring mapping. |
| `vpin.easley_lopez_ohara` | `DIRECT_ENGINE_INPUT` | Engine B toxic-flow fade, Engine C toxic-flow veto | Runtime-consumed. |
| `pin.easley_kiefer_ohara_paperman` | `FUTURE_RESERVED` | Feature registry only | No governed runtime consumer proven. |
| `amihud_illiquidity.amihud` | `NOT_PROVEN_NEEDS_EXTERNAL_AUDIT` | Feature registry only | Direct runtime/scoring consumer not proven in this pass. |
| `roll_spread.roll` | `NOT_PROVEN_NEEDS_EXTERNAL_AUDIT` | Feature registry claims execution cost meter | Direct runtime consumer not proven in this pass. |
| `corwin_schultz_spread.corwin_schultz` | `FUTURE_RESERVED` | Interface/meta references only | Not proven in governed runtime. |
| `hawkes_intensity.bacry_mastromatteo_muzy` | `FUTURE_RESERVED` | Feature registry intent only | No direct runtime call found. |
| `realized_kernel_vol.barndorff_nielsen` | `DIRECT_ENGINE_INPUT` | Engines A/C/D via canonical provenance | Strongly runtime-consumed. |
| `queue_pressure.book_imbalance` | `DIRECT_ENGINE_INPUT` | Engine C continuation validator | Runtime-consumed. |
| `wall_strength_*` | `REGIME_CONTEXT_INPUT`, `CONSUMED_VIA_ARTIFACT` | LOB regime bundle, regime runtime, feature bridge | Not proven as direct engine inputs. |
| `wall_persistence_*` | `REGIME_CONTEXT_INPUT`, `CONSUMED_VIA_ARTIFACT` | LOB regime bundle | Runtime context only. |
| `wall_pullaway_*` | `REGIME_CONTEXT_INPUT`, `CONSUMED_VIA_ARTIFACT` | LOB regime bundle | Runtime context only. |
| `near_touch_cancel_ratio_*` | `REGIME_CONTEXT_INPUT`, `CONSUMED_VIA_ARTIFACT` | LOB regime bundle | Runtime context only. |
| `executed_vs_displayed_*` | `REGIME_CONTEXT_INPUT`, `CONSUMED_VIA_ARTIFACT` | LOB regime bundle | Runtime context only. |
| `real_wall_score_*` | `REGIME_CONTEXT_INPUT`, `CONSUMED_VIA_ARTIFACT` | LOB regime bundle | Runtime context only. |
| `spoof_like_suspicion_*` | `REGIME_CONTEXT_INPUT`, `CONSUMED_VIA_ARTIFACT` | LOB regime bundle | Runtime context only. |
| `deceptive_liquidity_score` | `REGIME_CONTEXT_INPUT`, `CONSUMED_VIA_ARTIFACT` | LOB regime bundle, regime dataset builder | Governed runtime use is via regime context, not direct side creation. |
| `spread_bps` | `REGIME_CONTEXT_INPUT`, `EXECUTION_GATE_INPUT`, `COCKPIT_ONLY` | LOB regime snapshot, hybrid router snapshots, data-quality cockpit | Multiple producers exist; external audit should distinguish live depth vs artifact seams. |
| `order_book_imbalance` | `REGIME_CONTEXT_INPUT`, `EXECUTION_GATE_INPUT` | LOB regime snapshot, hybrid router equations | Same-side routed, not directional side creator. |
| `microprice_pressure` | `REGIME_CONTEXT_INPUT`, `EXECUTION_GATE_INPUT` | LOB regime snapshot, hybrid router equations | Same-side routed. |
| `liquidity_thinning_score` | `REGIME_CONTEXT_INPUT`, `CONSUMED_VIA_ARTIFACT` | LOB regime snapshot, dataset-builder labels | No direct engine consumer proven. |
| `aggressive_trade_imbalance` | `REGIME_CONTEXT_INPUT`, `EXECUTION_GATE_INPUT` | LOB regime snapshot, hybrid router equations | Runtime-consumed through execution gate. |
| `short_window_volatility` | `REGIME_CONTEXT_INPUT`, `EXECUTION_GATE_INPUT` | LOB regime snapshot -> router sanitized `short_window_volatility_z` | Runtime-consumed through execution gate. |
| `regime_transition_risk` | `REGIME_CONTEXT_INPUT`, `EXECUTION_GATE_INPUT` | Regime detector runtime, hybrid router | Allowed non-directional runtime field. |
| `regime_stability_score` | `REGIME_CONTEXT_INPUT`, `EXECUTION_GATE_INPUT` | Regime detector runtime, hybrid router | Allowed non-directional runtime field. |
| `market_toxicity_score` | `REGIME_CONTEXT_INPUT`, `EXECUTION_GATE_INPUT` | Regime detector runtime, hybrid router | Allowed non-directional runtime field. |
| `expected_duration_bucket` | `REGIME_CONTEXT_INPUT`, `CONSUMED_VIA_ARTIFACT` | Regime detector runtime | No direct engine consumer proven here. |

## Engine C focus

Engine C is directly proven to consume:
- `cumulative_ofi`
- `queue_pressure`
- `vpin`
- `kyle_lambda`
- `realized_vol_current`
- `realized_vol_at_break`

## Engine D focus

Engine D is directly proven to consume:
- `realized_vol_current`
- `realized_vol_post_close`

No proof was found that Engine D should be force-mapped into A/B-style shared scoring physics fields.

## Classifications

- `CONSUMER_FOUND` where direct traced code path exists
- `CONSUMER_NOT_FOUND` / `NOT_PROVEN_NEEDS_EXTERNAL_AUDIT` where only registry or indirect intent exists
- `COCKPIT_ONLY` for feature-bridge visibility
- `FUTURE_RESERVED` where feature exists but governed runtime use was not proven
