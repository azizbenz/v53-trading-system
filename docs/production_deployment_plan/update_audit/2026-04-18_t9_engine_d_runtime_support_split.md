# T9 pilot — Surgical split of `engine_d_runtime_support.py`

**Date** : 2026-04-18
**Author (master)** : Opus
**Executor (slave)** : Codex
**Time budget** : 1 hour
**Governance** : doc 28 arbitration, doc 25 audit protocol, doc 26 template (this pack)

---

## Objective

Close the last residual guardrail violation on `src/engines/engine_d/engine_d_runtime_support.py` (851 lines, caps at 700) by splitting it into exactly two sibling modules along a doctrinally clean seam, while keeping 100% of the existing import surface and test suite green.

This is a **mechanical / surgical** split — no logic change, no contract change, no threshold change.

## Docs Governants

- `docs/production_deployment_plan/29_SPRINT_FINAL_CODEX_BEFORE_MONDAY.md` §T9 (new_violations=0 acceptance)
- `docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md` (no rank-1 formula impact; surgical mechanical change only)
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md` (proof discipline)
- `config/engineering_guardrails_policy.json` (FILE_TOO_LONG rule, `max_file_lines=700`)

## Current Code Seam

- Canonical file today: `src/engines/engine_d/engine_d_runtime_support.py` (851 lines)
- Imported by: `src/engines/engine_d/engine_d_runtime.py` and any test under `tests/test_engines/test_engine_d/` — **grep before splitting** to enumerate every importer.
- Why this seam is the right place: the file mixes three concerns — (1) core runtime helpers and logging, (2) scoring/forecast building, (3) runtime refusal / downstream annotation. Concern (3) is the largest block and cleanly isolable.
- Forbidden shortcut for this slice: **do NOT** change any public symbol signature, do NOT rename any symbol, do NOT move the scoring/forecast block (keep split at the cleanest boundary only).

## Placement (proposed split — 2 files, 1 new)

Keep `engine_d_runtime_support.py` as the authoritative surface.
Extract the runtime-refusal/downstream block to a sibling `engine_d_runtime_support_refusal.py`.

### File 1 (keep): `src/engines/engine_d/engine_d_runtime_support.py`

Target: ≤ 550 lines after extraction.
Keeps, in order:
- L1–L44 header + imports
- `resolve_runtime_now` (L46)
- `require_scoring_version` (L60)
- `resolve_scoring_audit` (L69)
- `build_signal_candidate` (L81)
- `to_regime_id` (L104)
- `validate_coordination_input` (L118)
- `build_runtime_refusal_record` (L136)
- `runtime_log_entry` (L166)
- `append_runtime_log` (L208)
- `_EngineDScoringState` + `build_scoring_candidate` + `build_scoring_state` (L231–L334)
- `build_forecast_signal_candidate` + `_build_conditioning_state` + `_build_forecast_reason_codes` + `_build_forecast_versions` + `_resolve_invalidation_ref` + `_resolve_forecast_horizon_class` + `_resolve_bet_structure` (L335–L519)
- `evaluate_risk` (L520)
- `run_reentry_validation_hook` (L551)
- `require_selection_entry` (L584)

At the bottom of File 1, add a compatibility re-export block so downstream importers are not broken:

```python
# Backward-compatible re-exports for callers that import refusal helpers
# from engine_d_runtime_support directly. Do not add new imports here.
from .engine_d_runtime_support_refusal import (  # noqa: E402,F401
    annotate_forecast_signal_candidate_for_runtime_status,
    resolve_hook_blocked_reason_codes,
)
```

### File 2 (new): `src/engines/engine_d/engine_d_runtime_support_refusal.py`

Target: ≤ 350 lines.
Hosts, in this order:
- Header docstring: "Runtime refusal / downstream annotation helpers extracted from `engine_d_runtime_support.py` on 2026-04-18."
- `from __future__ import annotations`
- All imports it actually needs (Codex computes this — do NOT duplicate unused imports)
- `_resolve_runtime_refusal_category` (was L591)
- `_resolve_runtime_refusal_reason_codes` (was L608)
- `resolve_hook_blocked_reason_codes` (was L657)
- `annotate_forecast_signal_candidate_for_runtime_status` (was L664)
- `_resolve_runtime_forecast_reason_codes` (was L699)
- `_resolve_runtime_risk_reason_codes` (was L741)
- `_build_runtime_downstream_conditioning_records` (was L754)
- `_extract_log_reason_codes` (was L823)

## Files Changed

- `src/engines/engine_d/engine_d_runtime_support.py` (shrunk, re-exports added)
- `src/engines/engine_d/engine_d_runtime_support_refusal.py` (new)
- No test file may be modified.
- No public import path in any `engine_d_runtime.py` call site may be modified.

## Claims Implemented

- Claim 1 — `engine_d_runtime_support.py` is ≤ 700 lines → `wc -l src/engines/engine_d/engine_d_runtime_support.py` shows ≤ 700.
- Claim 2 — `engine_d_runtime_support_refusal.py` exists and is ≤ 700 lines.
- Claim 3 — Every symbol moved is re-exported from the original module for backward compatibility (grep confirms).
- Claim 4 — Zero call site under `src/engines/engine_d/` had to be edited.
- Claim 5 — Zero test file was edited.
- Claim 6 — `rtk pytest -q tests/test_engines/test_engine_d/` → unchanged pass count (baseline = all green before this slice).
- Claim 7 — `rtk pytest -q tests/test_microstructure/test_paper_repro.py` → 18 passed (regression control).
- Claim 8 — `python scripts/run_engineering_guardrails.py` → `new_violations` decreases by exactly 1 (the file no longer triggers `FILE_TOO_LONG`), and no new rule_id appears.

## Tests and Proof (to be filled by Codex)

```
python -m py_compile src/engines/engine_d/engine_d_runtime_support.py src/engines/engine_d/engine_d_runtime_support_refusal.py
  -> pass (exit 0; no output)

rtk pytest -q tests/test_engines/test_engine_d/
  -> Pytest: 89 passed

rtk pytest -q tests/test_microstructure/test_paper_repro.py
  -> Pytest: 18 passed

rtk pytest -q tests/test_protocols/
  -> Pytest: 444 passed

python scripts/run_engineering_guardrails.py
  -> new_violations=2
  -> first_new_violation_file = tests/test_engines/test_engine_b/test_engine_b_runtime.py:1 FILE_TOO_LONG

wc -l src/engines/engine_d/engine_d_runtime_support.py
  -> 621

wc -l src/engines/engine_d/engine_d_runtime_support_refusal.py
  -> 257
```

## Deferred / Not Done

- Split of `tests/test_engines/test_engine_b/test_engine_b_runtime.py` (846 lines) — scheduled for next pilot pass.
- Split of `tests/test_engines/test_engine_d/test_engine_d_runtime.py` (791 lines) — scheduled for next pilot pass.

## Risks / Open Questions

- Risk R1 — a helper in the refusal block secretly imports from the scoring block via a closure or module-level constant. Mitigation: Codex MUST re-run the full `tests/test_engines/test_engine_d/` suite and report pass count unchanged.
- Risk R2 — circular import between the two files. Mitigation: the re-export block at the bottom of File 1 uses `from .engine_d_runtime_support_refusal import …` at module-bottom, not at top. If Codex hits a circular import, it means the refusal block imported from scoring — that is a doctrine violation to surface, not a silent workaround.
- Open question O1 — is there any `__all__` declaration in the original file? Codex must preserve it (extend it with the re-exports).

## Completion Status (to be filled by Codex)

`COMPLETE`

Reason:

`Mechanical split landed exactly on the requested seam; engine_d suite, paper_repro, and protocols are green, and the engine_d_runtime_support FILE_TOO_LONG guardrail is gone.`

## Next Safe Step (to be filled by Codex)

`Run the next pilot pass on tests/test_engines/test_engine_b/test_engine_b_runtime.py, which is now the first remaining FILE_TOO_LONG hotspot.`

---

## Opus audit checklist (post-Codex)

Opus will verify, in this order:
1. `git diff --stat` shows only the 2 target files touched (plus this md).
2. `git diff src/engines/engine_d/engine_d_runtime_support.py` shows only deletions of the moved block + addition of the re-export block.
3. Every moved symbol appears in the re-export list OR is documented as "intentionally private, no external import".
4. Line counts: both files ≤ 700.
5. Tests: engine_d suite + paper_repro + protocols all green.
6. Guardrails: `new_violations` dropped by exactly 1, and engine_d_runtime_support.py is no longer in the hotspots list for FILE_TOO_LONG.

If any of 1–6 fails → REQUEST_FIX with precise line-level feedback.
If all pass → GREENLIGHT and schedule pilot pass 2 (test_engine_b_runtime split).
