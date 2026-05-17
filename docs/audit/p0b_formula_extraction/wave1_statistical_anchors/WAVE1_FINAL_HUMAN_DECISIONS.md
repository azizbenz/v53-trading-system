# Wave 1 Final Human Decisions

## Scope lock
- This decision record applies only to `src/calibration_methods/*` Wave 1 statistical anchors.
- No engine, runtime, cockpit template, execution backbone, risk backbone, or portfolio logic changes are allowed under this decision set.
- Changes must remain additive unless a prior Wave 1 mismatch was already confirmed and closed.

## Final doctrinal decisions

## 1. PSR
- Decision:
  - choose the returns-API equivalence anchor
  - do not patch [psr.py](/E:/claude%20%20v5.3/v53_trading_system/src/calibration_methods/psr.py)
- Rationale:
  - the production seam accepts a return series, not a paper-table parameter set
  - no in-repo reference dataset proves a literal `PSR = 0.9505`
  - the correct audit anchor is therefore:
    - deterministic in-repo return fixture
    - stable fixture hash
    - independently recomputed Bailey-Lopez de Prado Eq. 3 value
    - equality with the production API result
- Required closure:
  - keep the deterministic fixture and fixture hash in tests
  - document that literal `0.9505` is not accepted without an in-repo fixture/hash

## 2. DSR
- Decision:
  - keep the existing returns-based API unchanged
  - add an additive reference seam accepting Table 1 / from-moments style inputs
  - allow the returns API to delegate internally if safe
- Rationale:
  - the existing production seam is returns-based and already internally coherent
  - the doctrinal gap was auditability against moments/Table 1 style anchors, not a contradiction in the current formula
  - an additive moments seam closes that audit gap without changing existing production callers
- Required closure:
  - keep `compute_deflated_sharpe_ratio(...)` as the production seam
  - add and test `compute_deflated_sharpe_ratio_from_moments(...)`
  - document `trial_count` semantics as the effective number of tested strategy candidates / promotion trials

## 3. POT-GPD
- Decision:
  - keep the existing Wave 1 correction
  - do not widen the POT-GPD refactor
- Rationale:
  - `_pot_var` was already confirmed as a true formula mismatch and corrected
  - the Denmark / Coles literal dataset anchor remains partial because the reference dataset is not present in-repo
  - that dataset residue is not blocking once the formula mismatch itself is closed
- Required closure:
  - preserve the corrected `_pot_var` seam
  - preserve simulation / recovery tests
  - keep the Denmark / Coles anchor classified partial rather than pretending it is numerically closed

## 4. Energy distance
- Decision:
  - keep the current scaled statistic seam unchanged
  - add an additive raw `E_n,m` seam for audit / scientific anchoring
  - do not force the raw same-distribution `< 0.05` threshold onto the scaled statistic
- Rationale:
  - the production seam intentionally uses the scaled statistic
  - the raw same-distribution threshold belongs to the raw statistic or to a separately calibrated null envelope
  - the correct closure is to expose both seams clearly and test them separately
- Required closure:
  - preserve `compute_energy_distance_test(...)`
  - add `compute_raw_energy_distance_statistic(...)`
  - test raw same-distribution magnitude and scaled-to-raw relation separately

## Wave 1 closure policy
- Closed anchors that were already passing must remain unchanged:
  - KS fixed-seed anchor
  - Energy strong-shift scaled anchor
  - Mann-Kendall `S = 4950`
  - Hansen SPA behavioral anchors
  - stationary bootstrap AR(1) anchor
- Reference datasets not present in-repo must not be invented.
- Scientific/doctrinal residues must be closed through additive seams, deterministic fixtures, or explicit partial status, not through silent formula rewrites.

## Final status per residue
| Residue | Final doctrinal status | Production formula patch allowed? | Final closure path |
|---|---|---:|---|
| `PSR 0.9505` | closed by returns-API equivalence anchor | `no` | deterministic hashed returns fixture |
| `DSR Table 1` | closed by additive from-moments seam | `yes`, additive only | new moments/reference seam |
| `POT-GPD Denmark/Coles` | formula closed, dataset anchor partial | already done | keep corrected `_pot_var`, keep simulation tests |
| `Energy same-dist < 0.05` | closed by additive raw seam | `yes`, additive only | raw `E_n,m` seam + scaled/raw distinction tests |

## Non-negotiable invariants after this decision
- no engine changes
- no runtime live changes
- no cockpit template changes
- no strategy changes
- no directional labels or synthetic datasets invented for anchor closure
