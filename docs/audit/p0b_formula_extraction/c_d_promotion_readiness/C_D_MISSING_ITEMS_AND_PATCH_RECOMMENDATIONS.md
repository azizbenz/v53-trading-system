# C/D Missing Items And Patch Recommendations

## Immediate Patch Candidates

- Add an engine-specific replay/shadow promotion artifact for C and D.
- Surface Engine C and Engine D role text plus `PARTIAL_BY_DESIGN` on cockpit engine explanation pages.
- Add explicit per-engine readiness states that remain non-green while:
  - cost completeness is partial or unknown
  - executed-only net return is missing
  - true net-equity drawdown is missing
  - shadow confirmation artifact is missing

## Backtest-Dependent Items

- Engine-specific execution-rate artifact
- Engine-specific partial-fill and no-fill artifact
- Engine-specific sample-size survival artifact
- Engine-specific small-capital viability and capital-bucket evidence
- Engine-specific cost-drift / replay-live parity evidence

## Shadow-Dependent Items

- Engine-specific shadow confirmation artifact
- Per-engine promotion status and artifact freshness/hash governance

## Recommended Register Updates

- keep `ADD2-OPEN-001` and `ADD2-OPEN-002` open; this pack strengthens, not closes, the partial-by-design doctrine
- keep `W5-OPEN-006` and `W5-OPEN-007` open; C/D still lack executed-only net return and true drawdown
- keep `DB-008` open; cockpit visibility for C/D doctrine is still partial
- add a C/D-specific promotion-evidence gap for missing engine-specific replay/shadow promotion artifacts

## Recommended New Gap

```text
Gap ID: CD-OPEN-001
Wave: C/D Audit
Area: Promotion readiness artifacts
Severity: P1_REQUIRED_BEFORE_SHADOW
Status: OPEN
Gap: Engine C and Engine D lack explicit engine-specific replay/shadow promotion artifacts and statuses.
Why it matters: architecture is viable, but per-engine promotion readiness cannot be proven from the current aggregates alone.
Dependency: replay/shadow export with engine-specific execution/refusal/sample metrics plus promotion-state artifact.
Proposed resolution: add engine-specific promotion artifact/export without force-mapping C/D into A/B shared physics.
Owner: engine_c_d_audit
Source doc: docs/audit/p0b_formula_extraction/c_d_promotion_readiness/C_D_PROMOTION_READINESS_SUMMARY.md
Last update: 2026-04-30
```

## Never-Patch-This-Way Warning

- Do not patch C/D by stuffing local fields into shared A/B physics fields without semantic proof.
- Do not treat absent cost or replay statuses as safe zero.
- Do not treat expected CE as realized profitability.
- Do not mark C or D shadow-ready just because `ENGINE_*_IMPLEMENTATION_STATUS == "shadow_capable"`.

