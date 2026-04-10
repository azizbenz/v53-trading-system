# Doc Usage Matrix

This file states which markdown files must be used by new sessions, and with what authority level.

## Authority levels

- `must_use`
  - mandatory for every critical new session
- `use_as_secondary`
  - useful continuity or planning context
- `context_only`
  - architecture or audit context, not startup truth
- `not_canon`
  - never allowed to override active canon or verified code

## Must Use

### Session doctrine

File:
- `docs/ia lab vps v5.3/2026-04-06_SESSION_DOCTRINE_HARD_CORE.md`

Status:
- `must_use`
- conforming

Why:
- it requires an explicit context brief at the start of every session
- it defines the mandatory startup format for critical work

### Bootstrap pack

Files:
- `docs/ia lab vps v5.3/00_SESSION_BOOTSTRAP/00_README_START_HERE.md`
- `docs/ia lab vps v5.3/00_SESSION_BOOTSTRAP/01_ACTIVE_DOCTRINE.md`
- `docs/ia lab vps v5.3/00_SESSION_BOOTSTRAP/02_CODEBASE_CARTOGRAPHY.md`
- `docs/ia lab vps v5.3/00_SESSION_BOOTSTRAP/03_CURRENT_STATUS.md`
- `docs/ia lab vps v5.3/00_SESSION_BOOTSTRAP/04_SESSION_METHOD.md`
- `docs/ia lab vps v5.3/00_SESSION_BOOTSTRAP/05_CODE_RUNTIME_ANALYSIS.md`
- `docs/ia lab vps v5.3/00_SESSION_BOOTSTRAP/06_DOC_USAGE_MATRIX.md`

Status:
- `must_use`
- conforming

Why:
- they define the restart workflow, code map, runtime understanding, and current operational status for new chats

### Master development tracker

File:
- `docs/ia lab vps v5.3/2026-04-07_V53_MASTER_DEVELOPMENT_TRACKER.md`

Status:
- `must_use`
- conforming as execution memory
- `not_canon`

Why:
- it is explicitly written as the multi-session tracker
- it contains status vocabulary, BS register, and current resume point

Caveat:
- its "Canon Hierarchy" section is not fully conforming to the repo active documentary canon because it gives primary status to Local AI Lab docs instead of `docs/specs/V5_3_MASTER_FINAL_UNIQUE.md`
- therefore it must be used for continuity, not as top-level canon

### Working memory

File:
- `docs/ia lab vps v5.3/2026-04-05_V53_CORPUS_WORKING_MEMORY.md`

Status:
- `must_use`
- conforming as execution memory
- `not_canon`

Why:
- it records the active rail, latest closures, remaining work, and multi-session rules
- it explicitly exists to prevent memory-only work

### Strict build handoff

File:
- `docs/audit chatgpt buisness/2026-04-01_BUILD_HANDOFF_STATUS.md`

Status:
- `must_use`
- conforming
- `not_canon`

Why:
- it is the strict restart baseline for validated vs non-validated builds
- it enforces the hardened verdict rule `docs -> code -> tests -> runtime expectation`
- it provides the safest build-order restart frame

## Use As Secondary

### Prod-safe orchestration plan

File:
- `docs/audit chatgpt buisness/2026-04-02_PROD_SAFE_ORCHESTRATION_PLAN_TARGET_DOCTRINE_AND_BUILD_AUDIT.md`

Status:
- `use_as_secondary`
- methodologically conforming
- partially stale on rollout doctrine

Why:
- it correctly enforces truth order, anti-hallucination, and bounded lots
- it is useful for orchestration discipline

Caveat:
- it still discusses the active correction frame in `LIGHT/COMPLETE` terms and target-doctrine migration terms that no longer perfectly match current runtime code

### Prod-safe code-vs-doc workplan

File:
- `docs/audit chatgpt buisness/2026-04-02_PROD_SAFE_CODE_VS_DOC_WORKPLAN.md`

Status:
- `use_as_secondary`
- methodologically conforming
- partially stale on some doctrine assumptions

Why:
- it gives a strong truth hierarchy and anti-hallucination rules
- it is useful to structure build-by-build audits

Caveat:
- some rollout/gate assumptions are historical and must be checked against current code

### Local VPS Shadow chain handoff

File:
- `docs/audit chatgpt buisness/2026-04-02_LOCAL_VPS_SHADOW_CHAIN_HANDOFF.md`

Status:
- `use_as_secondary`
- operationally conforming
- `not_canon`

Why:
- it explains the actual local replay -> export -> import VPS -> Shadow chain
- it is useful for operator and pipeline understanding

### Continuity handoff

File:
- `docs/audit chatgpt buisness/2026-04-02_CHATGPT_CONTINUITY_HANDOFF_5_DAYS.md`

Status:
- `use_as_secondary`
- partially conforming
- `not_canon`

Why:
- it contains valuable intersession continuity and operational state

Caveats:
- some build verdicts are older or more optimistic than the strict baseline
- it still speaks in older rollout doctrine terms

## Context Only

### Build worklog and status

File:
- `docs/audit chatgpt buisness/2026-04-02_BUILD_WORKLOG_AND_STATUS.md`

Status:
- `context_only`
- useful historical evidence
- not authoritative for current restart truth

Why:
- it records real work performed
- but its verdicts can conflict with the stricter build handoff baseline

### Local AI Lab / VPS architecture docs

Files:
- `docs/ia lab vps v5.3/2026-04-04_V53_LOCAL_AI_LAB_FINAL_UNIQUE_CANON.md`
- `docs/ia lab vps v5.3/2026-04-04_V53_NEW_TARGET_CANONICAL_VPS_LOCAL_AI_LAB.md`
- `docs/ia lab vps v5.3/2026-04-04_V53_LOCAL_AI_LAB_IMPLEMENTATION_BLUEPRINT.md`
- `docs/ia lab vps v5.3/2026-04-04_V53_LOCAL_AI_LAB_PROD_SAFE_BUILD_PLAN.md`
- `docs/ia lab vps v5.3/2026-04-04_V53_PROD_SAFE_VPS_MIGRATION_PLAN.md`
- `docs/ia lab vps v5.3/2026-04-04_V53_VPS_LAB_SYNC_MATRIX.md`

Status:
- `context_only`
- useful architecture and target-state context
- `not_canon` for repo runtime behavior when they conflict with `docs/specs` or verified code

Why:
- they help understand intended Local AI Lab / VPS convergence
- but they are not the repo active master canon

## Audit Archive

All other audit markdowns under:
- `docs/audit chatgpt buisness/`

Status:
- `context_only`
- `not_canon`

Why:
- they may contain proof, branch history, or useful local findings
- but they are not mandatory startup reads unless the active slice directly depends on them

## Bottom line

For a new critical session, the required doc chain is:

1. session doctrine
2. bootstrap pack
3. master development tracker
4. working memory
5. strict build handoff
6. exact code slice
7. matching tests

All other markdowns are subordinate to:
- active canon in `docs/specs`
- verified code
- verified tests
