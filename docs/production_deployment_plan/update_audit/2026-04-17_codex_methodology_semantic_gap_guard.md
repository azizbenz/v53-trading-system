## Objective

Hard-code a work-method correction in `CODEX_PROMPT.md` so Codex no longer:

- flattens Engine A/B into shared seams derived from Engine C/D
- starts ideating before a direct double-check of current code, active docs, and real module placement

## Docs Governants

- `docs/production_deployment_plan/20_CARVER_NARANG_TALEB_INTEGRATION.md`
- `docs/production_deployment_plan/23_MICROSTRUCTURE_FEATURE_DICTIONARY.md`
- `docs/production_deployment_plan/24_V53_UPDATE_SURGICAL_INTEGRATION_MAP.md`
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md`
- `docs/production_deployment_plan/29_SPRINT_FINAL_CODEX_BEFORE_MONDAY.md`

## Current Code Seam

`CODEX_PROMPT.md` already contained a session lesson noting the error, but it was still advisory. The failure mode was methodological:

- compare weaker engines to richer engines
- infer a shared seam too early
- risk copying trading semantics across engines with different intents
- start ideating from intuition before verifying the current repo and the governing docs

## Placement

- Root prompt: `CODEX_PROMPT.md`
- Audit pack: `docs/production_deployment_plan/update_audit/2026-04-17_codex_methodology_semantic_gap_guard.md`

## Files Changed

- `CODEX_PROMPT.md`
- `docs/production_deployment_plan/update_audit/2026-04-17_codex_methodology_semantic_gap_guard.md`

## Claims Implemented

1. The faulty methodology is now explicitly banned, not merely noted.
2. A repository-wide double-check method is now mandatory before any design direction:
   - `CODE CHECK`
   - `DOC CHECK`
   - `PLACEMENT CHECK`
3. A replacement classification method is now mandatory before enriching Engine A/B:
   - `ENGINE_LOCAL_SEMANTICS`
   - `TRANSVERSAL_SHARED_SEAM`
   - `OBSERVABILITY_ONLY`
   - `GOVERNANCE_ONLY`
   - `USER_DECISION_REQUIRED`
4. C/D are restricted to engineering-quality reference use, not semantic-template use.
5. A/B semantic patches now require an explicit pre-patch checklist.

## Tests and Proof

- Root prompt inspected before patch.
- Existing Engine B folder scanned before considering further code work.
- No new `.py` created in this slice.

## Deferred / Not Done

- No engine code changed in this slice.
- The next engine-level slice still requires a classified semantic gap before implementation.

## Risks / Open Questions

- This patch hardens method, not runtime behavior by itself.
- The next A/B semantic slice must still prove whether the missing richness is local or transversal.

## Completion Status

`COMPLETE`

## Next Safe Step

Run the next Engine A/B slice using the new classification method and stop for user arbitration if the gap is semantically ambiguous.
