# C/D Remaining Post-Patch Gaps

Date: `2026-05-01`

## Still Open

- `CD-OPEN-001`: engine-specific replay/shadow promotion artifacts are still missing
- `CD-OPEN-003`: engine-specific executed-only net return is still missing
- `CD-OPEN-004`: engine-specific true net-equity drawdown is still missing
- `CD-OPEN-006`: engine-specific sample-size survival artifacts are still missing

## Closed by This Patch

- explicit C/D cockpit role plus `PARTIAL_BY_DESIGN` visibility
- explicit C/D shared mapping status carriage
- explicit C/D non-proven cost/fill/slippage carriage on scoring and risk seams

## Still Blocked By Upstream Evidence

- replay/shadow export with engine-specific promotion artifacts
- true realized per-engine profitability rail
- true per-engine net-equity drawdown rail
- engine-specific shadow confirmation artifact
- engine-specific fill/no-fill evidence with measured semantics

## Patch Boundary

This patch closes doctrine and status-carriage gaps only.

It does not:

- invent measured replay/shadow artifacts
- invent executed-only returns
- invent true drawdown
- promote Engine C or Engine D to `SHADOW_READY`
