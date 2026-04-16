# 26_UPDATE_AUDIT_PACK_TEMPLATE

Copy this template into:

`docs/production_deployment_plan/update_audit/YYYY-MM-DD_<slice_slug>.md`

---

# <SLICE TITLE>

## Objective

<One-paragraph description of the slice.>

## Docs Governants

- `<doc path>` `<section / line range>`
- `<doc path>` `<section / line range>`
- `<prompt / doctrine doc>` `<rule ids>`

## Current Code Seam

- Canonical file today: `<real file path>`
- Why this seam is the right place: `<short justification>`
- Forbidden shortcut for this slice: `<what was intentionally not done>`

## Placement

- Target file: `<real file path>`
- Doc target path: `<if different, state it>`
- Actual landing decision: `<why>`

## Files Changed

- `<file path>`
- `<file path>`
- `<file path>`

## Claims Implemented

- `<claim 1>` -> `<file path>`
- `<claim 2>` -> `<file path>`
- `<claim 3>` -> `<file path>`

## Tests and Proof

- `python -m py_compile ...` -> `<result>`
- `python -m pytest ... -q` -> `<result>`
- `python scripts/run_engineering_guardrails.py` -> `<result>`
- Optional artifact/log proof: `<path>`

## Deferred / Not Done

- `<deferred item 1>`
- `<deferred item 2>`

## Risks / Open Questions

- `<risk or explicit unknown>`
- `<risk or explicit unknown>`

## Completion Status

`COMPLETE | PARTIAL | BLOCKED`

Reason:

`<honest one-line status reason>`

## Next Safe Step

`<smallest next move that does not require inventing state>`
