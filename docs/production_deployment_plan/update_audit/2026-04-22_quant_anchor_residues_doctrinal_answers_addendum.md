# 2026-04-22 - Quant Residues Doctrinal Answers Addendum

## Parent Document

- `docs/production_deployment_plan/update_audit/2026-04-21_quant_anchor_residues_doctrinal_disambiguation.md`

## Frozen User Answers

The user has frozen the doctrinal answers as:

| Anchor | User answer | Execution meaning |
|--------|-------------|-------------------|
| PSR 0.9505 | **B** | close via equivalence on the current `returns -> compute_probabilistic_sharpe_ratio(...)` seam |
| DSR Table 1 | **B** | close via equivalence on the current `returns + trial_count -> compute_deflated_sharpe_ratio(...)` seam |
| POT-GPD Denmark/Coles | **B** | close via deterministic Coles-compatible simulation, not via an external dataset |
| Energy same-dist < 0.05 | **B** | close on the current scaled statistic and its own null distribution |

## Consequences

- no public API widening is allowed for PSR / DSR / POT-GPD / Energy
- no external Denmark/Coles dataset is allowed
- no unscaled Energy seam is allowed
- no literal paper-table reproduction claim is allowed when the proof is only a current-API equivalence proof

## Active Execution Pack

- `docs/production_deployment_plan/update_audit/2026-04-22_quant_anchor_closure_b_repo_truth.md`

This addendum exists to freeze the doctrinal answers cleanly without rewriting
the older disambiguation pack in place.
