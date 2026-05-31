# A — Split `/backtest` → `/backtest` + `/backtest/replay` Sub-page

**Date** : 2026-05-30
**Status** : OPUS SPEC READY FOR CODEX EXECUTION
**Effort estimate** : 1-2 days Codex
**Master spec parent** : `2026-05-29_A2_GOLD_PROD_SAFE_CLEANUP_SPEC.md`

## Objective

Décharger la page `/backtest` (actuellement **4212 lignes** dans `src/cockpit/templates/pages/backtest.html`) en extrayant les composants de drill-down vers une sous-page dédiée `/backtest/replay`. La sous-page sert à zoomer sur un run spécifique (épinglé via "▶ Load this run" depuis Recent Jobs) avec tous les détails forensiques.

## Docs governants

- `CLAUDE.md` (continuity protocol Opus → Codex)
- `project_backbone_parity_post_codex_audit_2026-05-27` (memory : 6 sections BACKBONE-METRICS card actuelle + BACKTEST-RUN-PIN flow)
- `project_b_dashboard_runtime_parity_card_2026-05-30` (memory : backend wire runtime_feature_parity_card livré, attend template HTML)
- `project_run_31bdfa55_deep_audit_2026-05-30` (memory : 6 questions audit → split UI = question 5 réponse)

## Current code seam (audit ce qui existe)

### Template `src/cockpit/templates/pages/backtest.html` — 4212 lignes

Cards principales détectées via `grep -n "<section\|class=\"card"` :

| Line | Card id | Card sub-title | Recommended split |
|------|---------|---------------|-------------------|
| 19 | `welcome-banner` | "Backtest / Replay" | KEEP /backtest (header) |
| 34 | `stat-row` | (stat tiles) | KEEP /backtest |
| 57 | (canonical local runner header) | "Audited local runner only" | KEEP /backtest |
| 98 | `run-backtest-card` | "Patch 6 Controls for phases A1/A2/B1/B_ML/B2" | KEEP /backtest |
| 590 | `backtest-progress-card` | "Observe the active run here first" | KEEP /backtest |
| 640 | `backtest-a2-performance-card` | "Data Factory cache, streaming, equivalence" | KEEP /backtest (summary only) |
| 672 | `backtest-decision-report-card` | "Operator ranking and readiness artifacts" | **MOVE /backtest/replay** |
| 711 | `backtest-backbone-parity-card` | "Canonical backbone vs local_replay fallback" | **MOVE /backtest/replay (detail)** ; KEEP summary badge on /backtest |
| 834 | `backtest-backbone-metrics-card` | "6 sections KPIs Execution/Edge/Risk/Portfolio/Regime/Hard_block" | **MOVE /backtest/replay** |
| 1037 | `backtest-runner-coverage-card` | "What the cockpit can prove during execution" | **MOVE /backtest/replay** |
| 1057 | `backtest-ml-check-card` | "Green if handoff run is ready" | KEEP /backtest |
| 1339 | `backtest-recent-jobs-card` | (Recent Backtest Jobs with pin) | KEEP /backtest |

### Server `src/cockpit/server.py` — 3233 lignes

Existing route :
```python
@app.get("/backtest")
def backtest_page(...): -> templates.TemplateResponse("pages/backtest.html", ...)
```

Need to add :
```python
@app.get("/backtest/replay")
def backtest_replay_page(request: Request, pinned_run_id: str = "") -> ...:
    -> templates.TemplateResponse("pages/backtest_replay.html", ...)
```

### View model `_build_vm` (`src/cockpit/server.py`)

Currently builds a single `vm` dict consumed by `backtest.html`. Sub-page reuses 80% of the same VM but with a narrower focus (pinned run only, no recent jobs panel duplication).

### Existing pin mechanism

Per memory `project_backbone_parity_post_codex_audit_2026-05-27` :
- Click `▶ Load this run` on Recent Backtest Jobs → recompute dashboard for that run (5 signatures touched)
- Currently the pin REPLACES the main /backtest dashboard view

Post-split intent : click `▶ Load this run` → **opens** `/backtest/replay?pinned_run_id=<id>` (new tab or in-page), main `/backtest` stays at current/live state.

## Placement (proposed file layout)

```
src/cockpit/
├── templates/pages/
│   ├── backtest.html              ← reduced to ~1800-2000L (control center)
│   └── backtest_replay.html       ← NEW ~1800-2200L (drill-down)
├── templates/partials/            ← NEW shared partials extracted from current file
│   ├── _decision_report_card.html
│   ├── _backbone_parity_detail_card.html
│   ├── _backbone_metrics_6_sections_card.html
│   ├── _runner_coverage_card.html
│   ├── _runtime_feature_parity_card.html   ← consumes vm.runtime.runtime_feature_parity_card (backend B wired 2026-05-30)
│   ├── _prod_safety_contract_card.html     ← NEW, reads a2_gold_prod_safety_contract.json
│   └── _loss_analysis_ledger_card.html     ← NEW, reads loss_analysis_ledger.jsonl
├── server.py                      ← add /backtest/replay route + view-model split
└── backtest_replay_state_support.py  ← NEW, helpers specific to replay sub-page
```

## Files Changed (slot — Codex fills)

### Templates
- [ ] `src/cockpit/templates/pages/backtest.html` (M) — extract cards 672, 711-detail, 834, 1037 to partials
- [ ] `src/cockpit/templates/pages/backtest_replay.html` (NEW) — include partials + drill-down focus
- [ ] `src/cockpit/templates/partials/_decision_report_card.html` (NEW)
- [ ] `src/cockpit/templates/partials/_backbone_parity_detail_card.html` (NEW)
- [ ] `src/cockpit/templates/partials/_backbone_metrics_6_sections_card.html` (NEW)
- [ ] `src/cockpit/templates/partials/_runner_coverage_card.html` (NEW)
- [ ] `src/cockpit/templates/partials/_runtime_feature_parity_card.html` (NEW — Codex spec for B template, scope from project_b)
- [ ] `src/cockpit/templates/partials/_prod_safety_contract_card.html` (NEW)
- [ ] `src/cockpit/templates/partials/_loss_analysis_ledger_card.html` (NEW)

### Server
- [ ] `src/cockpit/server.py` (M) — add `/backtest/replay` route, factor `_build_vm` if needed for sub-page narrower scope
- [ ] `src/cockpit/backtest_replay_state_support.py` (NEW) — replay sub-page-specific reader helpers (loss_analysis_ledger, prod_safety_contract aggregator)

### CSS
- [ ] `src/cockpit/static/cockpit.css` (M) — ensure partial card styles work standalone, add `.card--blocked` red banner for `is_blocked=True`

## Claims implemented (slot — Codex fills)

- [ ] Main `/backtest` reduced from 4212L to ≤ 2200L
- [ ] `/backtest/replay?pinned_run_id=<id>` renders pinned run drill-down
- [ ] `▶ Load this run` button on Recent Jobs now navigates to `/backtest/replay` (target=`_blank` or hx-get inline)
- [ ] `_runtime_feature_parity_card.html` renders `vm.runtime.runtime_feature_parity_card` with :
  - status badge (FRESH=green / STALE=yellow / BLOCKED=red)
  - training vs runtime feature counts
  - missing/extra feature names tables
- [ ] `_prod_safety_contract_card.html` renders prod_safety contract (12 blockers max) with traffic-light per category
- [ ] `_loss_analysis_ledger_card.html` renders top N loss records with classification + primary_cause + secondary_causes

## Tests and Proof (slot — Codex fills)

```
pytest count   :    PASS /    FAIL
guardrails     : new_violations =
git diff --stat : <only files listed in Files Changed above>

Smoke test     :
  - GET /backtest (no pin) → 200, renders reduced page
  - GET /backtest/replay?pinned_run_id=strategy_ladder_workflow-31bdfa55210c47e9 → 200, renders drill-down
  - Click "▶ Load this run" → navigates to /backtest/replay?pinned_run_id=<id>
  - runtime_feature_parity_card visible with status badge
```

## Deferred / Not Done

- Sub-page `/backtest/replay/<id>` URL-path syntax (alternative to query-string) — POST CODEX optional refactor
- Streaming live updates on /backtest/replay (currently snapshot at page load) — POST CODEX
- Sub-tabs inside /backtest/replay (e.g. Replay vs Promotion vs Costs) — POST CODEX

## Risks

| Risk | Mitigation |
|------|-----------|
| Template extraction breaks Jinja contexts | Run all cockpit pytest after each partial extraction |
| `_build_vm` regression breaks /backtest existing fields | Add per-section snapshot test BEFORE refactoring |
| Pin button regression | Keep current pin behavior on /backtest as fallback ; only ADD navigation on Recent Jobs button |
| Card CSS standalone rendering issues | Add visual smoke test in browser locally before commit |

## Completion Status (slot)

**Final status** : COMPLETE / PARTIAL / BLOCKED (Codex fills)
**Main page reduced from 4212L to** :  (Codex fills)
**Sub-page rendered drill-down working** : YES / NO

## Next Safe Step

After Codex completes A : ship Phase ML (short training run with all W0+W1+W2+W3 fixes + B+A UI visibility) → long institutional run multi-pair.

## Opus audit checklist (à valider à la fin)

- [ ] backtest.html reduced ≤ 2200L
- [ ] backtest_replay.html created + rendered with pinned_run_id
- [ ] All extracted partials referenced from BOTH pages where needed (no duplication)
- [ ] Pin button on Recent Jobs navigates correctly
- [ ] runtime_feature_parity_card visible on /backtest/replay (B wire backend déjà OK)
- [ ] prod_safety_contract_card visible avec 12 blockers max
- [ ] loss_analysis_ledger_card visible avec top N losses + classification
- [ ] CSS standalone for each partial OK
- [ ] pytest cockpit suite green (~330+ tests)
- [ ] No regression on main /backtest existing cards (run cards 19/34/57/98/590/640/1057/1339 still render correctly)
- [ ] Memory entry saved : `project_a_backtest_replay_subpage_split_complete_2026-05-XX.md`
