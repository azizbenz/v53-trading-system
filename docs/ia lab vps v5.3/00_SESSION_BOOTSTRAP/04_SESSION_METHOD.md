# Session Method

This file defines how a new session should recover context and work safely.

## Core rule

For critical work, a new session must rebuild context from:
- code
- tests
- canon
- explicit recovery docs

Never from memory alone.

## What "critical recovery" means

A new session must be able to answer all of the following before editing:
- what module is active right now
- what the system invariants are
- what other modules must connect to the active module
- what defaults are forbidden in that slice
- what counts as proof of closure for the slice

## Recovery workflow for every new session

1. Read `00_README_START_HERE.md`.
2. Read `01_ACTIVE_DOCTRINE.md`.
3. Read `06_DOC_USAGE_MATRIX.md`.
4. Read `03_CURRENT_STATUS.md`.
5. Read the relevant section in `02_CODEBASE_CARTOGRAPHY.md`.
6. Read `05_CODE_RUNTIME_ANALYSIS.md`.
7. If a `BS-*` id is unclear, read `07_SONNET_AUDIT_BS_MAPPING.md`.
8. Read `../2026-04-07_V53_MASTER_DEVELOPMENT_TRACKER.md`.
9. Read `../2026-04-05_V53_CORPUS_WORKING_MEMORY.md`.
10. Read the exact code slice line by line.
11. Read the matching tests line by line.
12. Compare code reality with canon and note any contradiction.
13. Start the session with the mandatory context brief.
14. Work only inside a bounded tranche.
15. Verify docs -> code -> tests -> runtime expectation before claiming closure.
16. Update `03_CURRENT_STATUS.md`, the tracker, and the working memory before ending the session.

## Line-by-line rule

Do not line-read the entire repo at the start of every chat.

Do line-read:
- the exact critical slice being worked on
- the direct contracts it depends on
- the direct tests that validate it

Do not skip:
- runtime entrypoints
- state stores / registries
- orchestration scripts if they are part of the active rail

## Bounded tranche rule

Each working tranche must declare:
- active rail
- in-scope files
- out-of-scope files
- targeted BS or gate
- required proof before closure

If the work starts crossing rails, stop and record the perimeter change.

## Closure rule

Do not say `closed`, `aligned`, or `green` unless all of these are true:
- docs match the intended behavior
- code implements the behavior
- tests cover the behavior
- runtime expectation is coherent and non-contradictory

If one of these is missing, use:
- `partial`
- `open`
- or `not ready`

## Anti-hallucination rules

- do not assume an old doc is still true without checking code
- do not assume a modified file is validated just because it exists
- do not assume a previous chat's memory survives a new session
- do not trust corrupted tracker files
- do not widen scope implicitly

## Minimum artifacts that must stay current

At minimum, keep these files usable:
- `00_README_START_HERE.md`
- `01_ACTIVE_DOCTRINE.md`
- `03_CURRENT_STATUS.md`

If those three stay current, a new session can usually recover safely.
