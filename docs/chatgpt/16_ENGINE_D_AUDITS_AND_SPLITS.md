# 16_ENGINE_D_AUDITS_AND_SPLITS

## Included Source Docs
- docs/production_deployment_plan/update_audit/2026-04-18_t9_engine_d_runtime_support_split.md
- docs/production_deployment_plan/update_audit/2026-04-18_t9_engine_b_d_runtime_test_split.md

---

## Source: docs/production_deployment_plan/update_audit/2026-04-18_t9_engine_d_runtime_support_split.md

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


---

## Source: docs/production_deployment_plan/update_audit/2026-04-18_t9_engine_b_d_runtime_test_split.md

# T9 pilot pass 2 — Surgical split of engine_b & engine_d runtime test files

**Date** : 2026-04-18
**Author (master)** : Opus
**Executor (slave)** : Codex
**Time budget** : 1 hour
**Governance** : doc 28 arbitration, doc 25 audit protocol, doc 26 template (this pack)

---

## Objective

Close the last two FILE_TOO_LONG residuals (both test files explicitly deferred in the prior T9 pilot) by extracting the **risk-action** test cluster from each runtime test file into a sibling test module, identical seam in both engines.

This is a **mechanical / surgical** split — no test logic change, no assertion change, no fixture rename, no import-surface change for production code.

## Docs Governants

- `docs/production_deployment_plan/29_SPRINT_FINAL_CODEX_BEFORE_MONDAY.md` §T9 (`new_violations=0` acceptance)
- `docs/production_deployment_plan/28_ARBITRATION_PROTOCOL_OPUS_CODEX.md` (no rank-1 formula impact; surgical mechanical change only)
- `docs/production_deployment_plan/25_UPDATE_AUDIT_PROTOCOL.md` (proof discipline)
- `config/engineering_guardrails_policy.json` (`FILE_TOO_LONG` rule, `max_file_lines=700`)
- Pre-existing precedent for sibling-import pattern: `tests/test_engines/test_engine_b/test_engine_b_runtime_refusals.py` already imports helpers via `from .test_engine_b_runtime import (…)`.

## Current Code Seam

- `tests/test_engines/test_engine_b/test_engine_b_runtime.py` — **846 lines**, last passing FILE_TOO_LONG residual.
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py` — **791 lines**, last passing FILE_TOO_LONG residual.
- Both files share an identical structural pattern:
  1. shared module-level helpers (`_runtime`, `_runtime_input`, `_risk_runtime`, `_FixedRiskRuntime` / `_CapturingRiskRuntime`, `_base_risk_evaluation` / `_forced_risk_evaluation`, etc.)
  2. happy-path / canonical signal tests
  3. input-validation tests
  4. circuit-breaker / hook-block tests
  5. hard-block / ranking-rejection / portfolio-rejection tests
  6. **risk-action cluster** (cannot_bypass_risk_runtime → risk_rejected → risk_reduced → risk_observe_only) **← this is what we extract**
  7. trailing invariants (no-fake-flat, invalid_now)
- Why this seam: the risk-action cluster is the densest, most internally-coherent block in both files. It is also exactly the size needed to drop both files under 700 in a single move, with zero rebalancing.
- Forbidden shortcut for this slice:
  - **do NOT** rename or modify any test function.
  - **do NOT** rewrite any helper, fixture, or assertion.
  - **do NOT** move helpers — they stay in the original file and are imported by the sibling.
  - **do NOT** edit any `src/` file.
  - **do NOT** edit any other test file.

## Placement (proposed split — 2 new sibling test files)

### Engine B

#### File B1 (keep, shrink): `tests/test_engines/test_engine_b/test_engine_b_runtime.py`

Target: ≤ 690 lines after extraction.

Keeps everything from current line 1 through the end of the function `test_runtime_rejected_by_portfolio_annotates_forecast_truthfully` (currently ending around line 687). Then add ONE blank line and end of file.

Removes (moved to File B2): the contiguous block currently spanning the start of `test_runtime_cannot_bypass_risk_runtime` (line 689) through the **last line** of the file (line 846 inclusive — that is, all 7 risk-action tests **plus** `test_runtime_never_creates_fake_flat_side_or_fake_blocked_trade`).

Rationale for moving the trailing fake-flat test along with the risk cluster: it asserts on a `HARD_BLOCKED` runtime status path that exercises the same rejection-shape invariants as the risk tests, and keeping it together prevents File B1 from creeping back over 700 if a single new line is added later.

#### File B2 (new): `tests/test_engines/test_engine_b/test_engine_b_runtime_risk_actions.py`

Target: ≤ 250 lines.

Contents in this exact order:

1. Module docstring: `"""Risk-action and trailing invariant tests for Build-7 Engine B runtime, extracted from test_engine_b_runtime.py on 2026-04-18 to satisfy FILE_TOO_LONG."""`
2. `from __future__ import annotations`
3. Standard-library imports it actually uses (`from pathlib import Path` at minimum — Codex computes the exact set).
4. Direct project imports the moved tests already use (`EngineBRuntime`, `EngineBRuntimeStatus`, `RiskRuntime`, `RiskLimits`, `RiskRuntimeAction`, `Side`, `BlockerCondition`). Do NOT duplicate any import that the new file does not actually reference.
5. **Helper imports from the sibling** — relative import:
   ```python
   from .test_engine_b_runtime import (
       _FixedRiskRuntime,
       _base_risk_evaluation,
       _runtime,
       _runtime_input,
   )
   ```
   Add or remove names from this list according to what the moved tests actually call. Helpers stay defined in `test_engine_b_runtime.py`.
6. The 8 moved test functions, **byte-for-byte identical** (no whitespace reflow, no docstring rewrite, no parameter rename) to their current bodies in lines 689–846.

### Engine D

#### File D1 (keep, shrink): `tests/test_engines/test_engine_d/test_engine_d_runtime.py`

Target: ≤ 690 lines.

Keeps everything from current line 1 through the end of `test_runtime_rejected_by_portfolio_annotates_forecast_truthfully` (currently ending around line 668). Then one blank line, end of file.

Removes (moved to File D2): the contiguous block from `test_runtime_cannot_bypass_risk_runtime` (line 670) through the **last line** of the file (line 791 inclusive — that is, the 7 risk-action tests **plus** `test_runtime_never_creates_fake_flat_side_or_fake_blocked_trade` **plus** `test_invalid_now_rejected`).

#### File D2 (new): `tests/test_engines/test_engine_d/test_engine_d_runtime_risk_actions.py`

Target: ≤ 250 lines.

Contents in this exact order:

1. Module docstring: `"""Risk-action and trailing invariant tests for Build-9 Engine D runtime, extracted from test_engine_d_runtime.py on 2026-04-18 to satisfy FILE_TOO_LONG."""`
2. `from __future__ import annotations`
3. Standard-library imports actually used.
4. Direct project imports the moved tests already use (`EngineDRuntime`, `EngineDRuntimeStatus`, `RiskRuntime`, `RiskLimits`, `RiskRuntimeAction`, `BlockerCondition`, `Side`, plus any others the moved tests reference). Codex computes the exact set; do NOT duplicate unused imports.
5. **Helper imports from the sibling** — relative import:
   ```python
   from .test_engine_d_runtime import (
       _CapturingRiskRuntime,
       _accepted_risk_evaluation,
       _forced_risk_evaluation,
       _runtime,
       _runtime_input,
   )
   ```
   Adjust the name list to exactly what the moved tests call.
6. The 9 moved test functions, **byte-for-byte identical** to their current bodies in lines 670–791.

## Files Changed

- `tests/test_engines/test_engine_b/test_engine_b_runtime.py` (shrunk to ≤ 690 lines)
- `tests/test_engines/test_engine_b/test_engine_b_runtime_risk_actions.py` (new, ≤ 250 lines)
- `tests/test_engines/test_engine_d/test_engine_d_runtime.py` (shrunk to ≤ 690 lines)
- `tests/test_engines/test_engine_d/test_engine_d_runtime_risk_actions.py` (new, ≤ 250 lines)
- No `src/` file may be edited.
- No other test file may be edited.
- No `conftest.py` may be created or edited.

## Claims Implemented

- Claim 1 — `tests/test_engines/test_engine_b/test_engine_b_runtime.py` is ≤ 700 lines.
- Claim 2 — `tests/test_engines/test_engine_b/test_engine_b_runtime_risk_actions.py` exists, is ≤ 700 lines, and contains exactly the 8 moved test functions.
- Claim 3 — `tests/test_engines/test_engine_d/test_engine_d_runtime.py` is ≤ 700 lines.
- Claim 4 — `tests/test_engines/test_engine_d/test_engine_d_runtime_risk_actions.py` exists, is ≤ 700 lines, and contains exactly the 9 moved test functions.
- Claim 5 — Pytest collection + run for the engine_b and engine_d test directories shows the **same** total pass count (engine_d = 89, engine_b = unchanged baseline). No skip, no xfail, no ERROR introduced.
- Claim 6 — The full repo guardrail report shows `new_violations=0` (the two known residuals are resolved and no new rule_id appears).
- Claim 7 — `git diff --stat` shows exactly the four file paths above modified/created (plus this audit md).
- Claim 8 — Zero `src/` file appears in `git diff --name-only`.

## Tests and Proof (to be filled by Codex)

```
python -m py_compile tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime_risk_actions.py tests/test_engines/test_engine_d/test_engine_d_runtime.py tests/test_engines/test_engine_d/test_engine_d_runtime_risk_actions.py
  -> <fill: pass / fail>

rtk pytest -q tests/test_engines/test_engine_b/
  -> <fill: pass count>

rtk pytest -q tests/test_engines/test_engine_d/
  -> <fill: pass count>

rtk pytest -q tests/test_microstructure/test_paper_repro.py
  -> <fill: pass count>

PYTHONPATH=src python scripts/run_engineering_guardrails.py
  -> <fill: new_violations=…, first_new_violation_file=…>

wc -l tests/test_engines/test_engine_b/test_engine_b_runtime.py tests/test_engines/test_engine_b/test_engine_b_runtime_risk_actions.py
  -> <fill: line counts>

wc -l tests/test_engines/test_engine_d/test_engine_d_runtime.py tests/test_engines/test_engine_d/test_engine_d_runtime_risk_actions.py
  -> <fill: line counts>
```

## Deferred / Not Done

- `src/ui/technical_dashboard_view.py` (1940 lines) and `src/ui/technical_dashboard_html.py` (1271 lines) remain on the baseline whitelist — they are an HTML-generation surface and out of scope for this slice.
- All other historic baseline violations (annotation hygiene, etc.) remain on the baseline whitelist; this slice only targets the two NEW FILE_TOO_LONG entries.

## Risks / Open Questions

- Risk R1 — a moved test secretly references a helper not listed in the relative-import block. Mitigation: pytest collection failure is the loud detector; Codex MUST run both engine test suites and report the exact pass counts.
- Risk R2 — pytest discovery order changes alter a fixture-cached state. Mitigation: there are no module-level mutable state fixtures in either file; both helper sets are pure functions or fresh-instance factories. If a discovery-order regression appears, that is a doctrine violation to surface, not a silent workaround.
- Risk R3 — the byte-for-byte requirement is violated by an editor auto-formatter. Mitigation: Codex MUST diff the moved block against the original lines (`git diff` over the deletion + creation should net to zero on the moved bodies, modulo indentation only at the outermost def level — there is none here, all moved tests are module-level).
- Open question O1 — none. Both files have no `__all__`, no parametrize-shared marker, no module-level fixture.

## Completion Status (to be filled by Codex)

`<fill: COMPLETE / PARTIAL / BLOCKED>`

Reason:

`<fill: one-sentence justification>`

## Next Safe Step (to be filled by Codex)

`<fill: e.g., Hand back to Opus for full-suite green-run (rtk pytest -q tests/) and Sprint 29 T9 closure update in the sprint doc.>`

---

## Opus audit checklist (post-Codex)

Opus will verify, in this order:
1. `git diff --stat` shows only the 4 target files touched (plus this md).
2. `git diff tests/test_engines/test_engine_b/test_engine_b_runtime.py` shows only deletions of the moved block (no edits to any retained test).
3. `git diff tests/test_engines/test_engine_d/test_engine_d_runtime.py` shows only deletions of the moved block (no edits to any retained test).
4. The two new sibling files contain only: header, imports, sibling-helper imports, and the moved test functions (no helpers re-defined, no logic added).
5. Line counts: all four files ≤ 700.
6. Tests: engine_b suite pass count unchanged, engine_d suite = 89, paper_repro = 18.
7. Guardrails: `new_violations=0`. The two prior FILE_TOO_LONG entries on `test_engine_b_runtime.py` and `test_engine_d_runtime.py` are gone, and no new entry appears for the 4 target files.

If any of 1–7 fails → REQUEST_FIX with precise line-level feedback.
If all pass → GREENLIGHT and update memory + Sprint 29 T9 status to `COMPLETE`.


