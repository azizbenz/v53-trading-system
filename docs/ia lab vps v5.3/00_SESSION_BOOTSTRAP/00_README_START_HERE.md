# V5.3 Session Bootstrap

This folder is the stable entry point for any new Codex session on V5.3.

Goal:
- restore context from code + canon
- avoid hallucinated continuity
- avoid working from corrupted tracker files
- keep each new session inside the real active perimeter

## Read order for every new session

1. `00_README_START_HERE.md`
2. `01_ACTIVE_DOCTRINE.md`
3. `06_DOC_USAGE_MATRIX.md`
4. `03_CURRENT_STATUS.md`
5. `02_CODEBASE_CARTOGRAPHY.md`
6. `05_CODE_RUNTIME_ANALYSIS.md`
7. `07_SONNET_AUDIT_BS_MAPPING.md` when a `BS-*` id is mentioned but not yet understood
8. `../2026-04-07_V53_MASTER_DEVELOPMENT_TRACKER.md`
9. `../2026-04-05_V53_CORPUS_WORKING_MEMORY.md`
10. the exact code slice currently being worked on
11. the matching tests for that code slice

## Mandatory startup rule

Every session must begin with the context brief required by:
- `AGENTS.md`
- `docs/ia lab vps v5.3/2026-04-06_SESSION_DOCTRINE_HARD_CORE.md`

Required opening format:
- `You are working on module X.`
- `Global invariants: [...]`
- `Modules Y and Z must connect to X via [...]`
- `Forbidden defaults: [...]`
- `After generation, verify explicitly: [...]`

## Source of truth order

Use sources in this order:

1. code in `src/`
2. tests in `tests/`
3. canon in `docs/specs/V5_3_MASTER_FINAL_UNIQUE.md`
4. strict handoff in `docs/audit chatgpt buisness/2026-04-01_BUILD_HANDOFF_STATUS.md`
5. this bootstrap pack
6. tracker + working memory as execution memory only

Tracker and working memory are now readable again, but they are not superior canon.
Use them to restore session continuity, not to override `docs/specs` or code reality.

## What this pack contains

- `01_ACTIVE_DOCTRINE.md`
  - the doctrine that a new session must assume before editing anything
- `02_CODEBASE_CARTOGRAPHY.md`
  - the map of the repo by build, module, path, and test surface
- `03_CURRENT_STATUS.md`
  - what is known done, what remains open, and what is risky right now
- `04_SESSION_METHOD.md`
  - the exact workflow to recover context and work safely in a new chat
- `05_CODE_RUNTIME_ANALYSIS.md`
  - the code-based understanding of the real runtime paths
- `06_DOC_USAGE_MATRIX.md`
  - which MD files must be used, and with what authority level
- `07_SONNET_AUDIT_BS_MAPPING.md`
  - the recovered mapping of previously orphan `BS-*` ids from the Sonnet audit docx

## Current intent of this folder

This folder is not a new canon.
It is a recovery layer for new sessions.

If this pack and the code disagree:
- the code wins over this pack
- the master canon wins over secondary docs
- contradictions must be recorded explicitly before continuing
