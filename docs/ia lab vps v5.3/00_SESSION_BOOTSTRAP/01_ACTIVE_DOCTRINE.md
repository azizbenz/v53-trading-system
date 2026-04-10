# Active Doctrine

This file states the doctrine a new session must assume before starting work.

## Non-negotiable invariants

- one shared V5.3 codebase for local and VPS
- no parallel architecture
- no extra profiles beyond governed repo doctrine
- no bypass of Shadow, Micro-live, or Live gates
- no local or VPS fork presented as a second V5.3
- no implicit promotion from local replay or lab work to live runtime

## Canonical sources

Primary canon:
- `docs/specs/V5_3_MASTER_FINAL_UNIQUE.md`

Strict restart handoff:
- `docs/audit chatgpt buisness/2026-04-01_BUILD_HANDOFF_STATUS.md`

Session startup doctrine:
- `AGENTS.md`
- `docs/ia lab vps v5.3/2026-04-06_SESSION_DOCTRINE_HARD_CORE.md`

## Runtime doctrine that is real in code today

The codebase is no longer homogeneous on the profile doctrine.

What is real in governed runtime code:
- Build-11 Shadow opens in `COMPLETE` only
- Build-12 Micro-live opens in `COMPLETE` only
- Build-13 Live opens in `COMPLETE` only
- execution defaults also moved to `COMPLETE`

Key code anchors:
- `src/protocols/contracts.py`
- `src/protocols/micro_live_runtime.py`
- `src/protocols/live_light_runtime.py`
- `src/execution_backbone/execution_runtime.py`
- `src/execution_backbone/order_decider/intent_builder.py`

## Strategic doctrine tension

The repo still contains a major doctrine mismatch:

- many canonical docs still describe `LIGHT` and `COMPLETE` as the two active rollout profiles
- several registries, enums, tests, monitoring projections, and local replay surfaces still keep `LIGHT`
- but the governed runtime path for Shadow -> Micro-live -> Live is already `COMPLETE` only

This mismatch must be treated as a tracked convergence problem, not as an informal annoyance.

Working rule until convergence is finished:
- do not assume old `LIGHT` docs are still runtime-true
- verify profile behavior in code first
- when code and docs disagree, record the contradiction before editing

## Build-14 rule

The active master states:
- `SHADOW_ENABLED` means active at 100 percent in Shadow, not read-only

Therefore:
- if a secondary doc still describes Build-14 as read-only or limited influence in Shadow, the master wins

## Local AI Lab vs VPS doctrine

Local AI Lab:
- research
- replay
- diagnostics
- calibration
- proof
- distillation
- artifact packaging

VPS:
- governed runtime
- sovereignty
- observability
- artifact intake
- promotion gates

Control rule:
- Local AI Lab can prove and package
- VPS decides import, Shadow use, and promotion
- no direct local-to-live path

## Working assumption for new sessions

Until explicitly disproved by code:
- runtime modes stay `LOCAL_REPLAY`, `SHADOW`, `MICRO_LIVE`, `LIVE`
- the active critical rail is governed by runtime contracts, not by stale rollout wording
- any critical work must be bounded to a slice and validated against code + tests
