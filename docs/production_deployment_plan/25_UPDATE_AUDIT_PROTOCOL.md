# 25_UPDATE_AUDIT_PROTOCOL

## 1. Why this exists

Raw update docs are not enough for a safe audit.

They usually mix:
- doctrine
- proposed landing paths
- partial truths about the current code
- future work that does not exist yet

For V5.3, an update is auditable only if a second reader can answer four questions fast:
1. Which doc clauses governed this slice?
2. Which real files changed?
3. Which proof was executed?
4. What is still not done?

This protocol makes Claude/Codex audits cheaper and less hallucinatory for the current update set and for future updates.

## 2. Mandatory artifact: the Update Audit Pack

Every non-trivial slice must create or update one audit pack under:

`docs/production_deployment_plan/update_audit/YYYY-MM-DD_<slice_slug>.md`

Optional runtime evidence may live under:

`build/update_audit/<slice_slug>/`

The markdown pack is the canonical human audit surface.
The `build/` evidence is optional supporting material, never the only proof.

## 3. Required content of every audit pack

Each pack must contain these sections, in this order:

1. `Objective`
2. `Docs Governants`
3. `Current Code Seam`
4. `Placement`
5. `Files Changed`
6. `Claims Implemented`
7. `Tests and Proof`
8. `Deferred / Not Done`
9. `Risks / Open Questions`
10. `Completion Status`
11. `Next Safe Step`

## 4. Hard rules

For every pack:

- Every claim must point to a real file path.
- Every claim must be backed by one of:
  - code existence
  - test result
  - runtime artifact
  - guardrails output
- A green unit test alone is not enough.
- A doc claim alone is never enough.
- If a slice is partial, the pack must say so explicitly.
- If a field/value is derived by mapping rather than copied verbatim from a doc, that mapping must be stated.
- If a seam was intentionally not wired, the reason must be explicit.

## 5. How Claude should audit an update

Claude should follow this order:

1. Read this protocol.
2. Open the relevant pack in `docs/production_deployment_plan/update_audit/`.
3. Read the governing docs cited by the pack.
4. Open the changed files listed by the pack.
5. Re-run the proof commands listed in the pack when needed.
6. Reject any claim that lacks:
   - a real file
   - a real proof command or artifact
   - an honest completion status

## 6. Requirements for future update docs

Any future update MD proposed by Claude/Opus/Sonnet should include:

- source doc section and line range
- recommended landing path
- current real code seam
- acceptance test expectation
- explicit non-goals
- migration order

If an update doc does not contain those fields, it must be normalized into an audit pack before implementation starts.

## 7. Anti-hallucination value

This protocol prevents five common failures:

- auditing from prose without checking code
- marking work done because tests are green but no consumer exists
- confusing target path with existing path
- forgetting deferred work
- losing context across chats or agents

## 8. Minimum bar for “done”

A slice is `COMPLETE` only if:

- code exists in the stated target files
- the stated tests were executed
- guardrails did not introduce new violations
- the pack records what was done and what remains

If one of these is missing, the slice is `PARTIAL` or `BLOCKED`.
