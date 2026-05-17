# P0B ADD2 - Remaining Decisions

## Still open by design

## Decision 1
- Topic: `Engine C shared scoring physics mapping`
- Current state:
  - explicit partial only
  - no forced mapping of `execution_fragility`, `market_toxicity`, `spread_regime_penalty`, `participation_penalty`
- Why it remains open:
  - C already has local math and direct microstructure usage
  - equivalence to A/B-style shared physics fields was not proven
- Required label:
  - `HUMAN_DECISION_REQUIRED_FOR_C_D_SHARED_CARRIAGE`

## Decision 2
- Topic: `Engine D shared scoring physics mapping`
- Current state:
  - explicit partial only
  - realized-kernel seam is real, but no safe mapping for shared physics fields was proven
- Why it remains open:
  - D consumes volatility/regime context locally
  - a forced mapping would risk inventing semantics
- Required label:
  - `HUMAN_DECISION_REQUIRED_FOR_C_D_SHARED_CARRIAGE`

## Decision 3
- Topic: `participation_penalty`
- Current state:
  - not carried anywhere in this patch
- Why it remains open:
  - no governed runtime source was proven
  - zero would be a false active measurement

## Decision 4
- Topic: `risk info-stress carriage`
- Current state:
  - A/B now expose explicit missing reasons
  - C/D remain explicit partial
- Why it remains open:
  - the governed runtime rail did not prove sources for:
    - `reference_spread_bps`
    - `depth_ratio`
    - `order_cancellation_rate`
    - `taker_imbalance`
    - `micro_vol_divergence`

## Decision 5
- Topic: `live supplementary_refs source packaging`
- Current state:
  - transport and validation are patched
  - scoring/ML hook can consume refs when present
  - current production engine runtime inputs still default to empty refs unless an upstream governed source passes them
- Why it remains open:
  - the patch did not invent a new source of ML or regime artifact refs
  - transport is real, but current live source packaging remains neutral by default

## Decision 6
- Topic: `risk/scoring regime reinjection`
- Current state:
  - execution already consumes non-directional regime context
  - scoring/risk reinjection remains partial
- Why it remains open:
  - doctrine did not prove that the same regime state must be injected into scoring/risk carriers right now
- Required labels:
  - `REGIME_SCORING_REINJECTION_PARTIAL`
  - `REGIME_RISK_REINJECTION_PARTIAL`

## Decision 7
- Topic: `double-counting policy`
- Current state:
  - A/B keep derived raw features and now also carry explicit shared fields for audit/hook projection
- Why it remains open:
  - the patch intentionally avoided rewriting scoring math
  - if doctrine later requires shared fields to drive more runtime math, double-counting policy must be reviewed explicitly

## Current recommendation
- Accept the patch as the minimal safe A/B carriage fix
- Keep C/D partial until doctrine decides whether local math plus downstream execution context is sufficient
- Keep live ML supplementary refs neutral-by-default until an upstream governed source is explicitly wired
