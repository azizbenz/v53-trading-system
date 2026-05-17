# V5.3 Publication Audit

Date: 2026-05-02
Repo state audited from branch: `codex/full-shadow-abcd-migration-20260403`

## Goal

Decide whether the current workspace can be uploaded as a "final solution" snapshot without silently publishing:

- stale patch artifacts,
- temporary office files,
- local secret material,
- or non-canonical convenience files.

## Current workspace reality

- Modified files: `147`
- Untracked files: `46`
- Modified scope is concentrated in:
  - `src/` (`81`)
  - `tests/` (`51`)
  - `scripts/` (`12`)
  - root/config metadata (`.env.example`, `config/engineering_guardrails_baseline.json`, `pyproject.toml`)
- Untracked scope is concentrated in:
  - `docs/` (`246` paths)
  - `src/` (`80` paths)
  - `tests/` (`32` paths)
  - `scripts/` (`11` paths)

## High-risk publication findings

### 1. Secret material was present in untracked scope

Observed:

- `secrets/binance-live-001.key`
- `secrets/binance-live-001.sealed.json`

Decision:

- `DO NOT PUBLISH`
- publication safety rule added to `.gitignore`: `secrets/`

### 2. Temporary office/editor debris was present in untracked scope

Observed:

- files matching `~$*`

Decision:

- `DO NOT PUBLISH`
- publication safety rule added to `.gitignore`: `**/~$*`

### 3. Convenience/exported reference HTML was present in untracked scope

Observed:

- `docs/production_deployment_plan/Claude Code Cheat Sheet.html`
- `docs/production_deployment_plan/Claude Code Cheat Sheet_files/`

Decision:

- `DO NOT PUBLISH` as part of a canonical final solution snapshot
- publication safety rules added to `.gitignore`

## Publish classification

### A publier

These paths look like canonical solution scope and should remain candidates for the final repo snapshot:

- `src/`
- `tests/`
- `scripts/`
- `config/calibration/`
- `config/engineering_guardrails_baseline.json`
- `pyproject.toml`
- `.env.example`
- `docs/audit/` markdown/csv/json/python evidence rails
- `docs/backtest/`
- `docs/cockpit/`

### A verifier avant push

These paths are not obviously wrong, but they are not automatically canonical just because they are present:

- `docs/production_deployment_plan/environement/`
- `docs/production_deployment_plan/update_audit/`
- standalone `.docx` files under `docs/audit/`
- standalone `.docx` files under `docs/production_deployment_plan/`

Reason:

- they may be working notes, exports, or user documents rather than governed final-source material

### A exclure

- `secrets/`
- office temp files matching `~$*`
- `docs/production_deployment_plan/Claude Code Cheat Sheet.html`
- `docs/production_deployment_plan/Claude Code Cheat Sheet_files/`

## Publication recommendation

Do not publish with blind `git add -A` yet.

Recommended pre-push sequence:

1. Keep canonical code and tests in scope:
   - `src/`
   - `tests/`
   - `scripts/`
   - governed config and audit docs
2. Exclude secret material and temporary office debris by ignore rules.
3. Decide intentionally whether `.docx` and ad hoc environment planning docs belong in the final repo.
4. Re-run a scope audit after that decision.
5. Only then create the new GitHub repository and push.

## User decision applied

User publication decision for the new GitHub repository:

- no `.docx`
- no `.md`

Operational interpretation used:

- exclude the full `docs/` tree from the publish snapshot
- exclude root/project markdown files from the publish snapshot
- keep code/config/tests/scripts only

## Prepared publish snapshot

A filtered local snapshot was prepared at:

- `publish_snapshot/repro_final_v53_mai26`

Current top-level content of that snapshot:

- `.github/`
- `config/`
- `schemas/`
- `scripts/`
- `src/`
- `tests/`
- `.env.example`
- `.gitignore`
- `Makefile`
- `pyproject.toml`

Verification result:

- no `secrets/`
- no `.md`
- no `.docx`
- no exported HTML cheat-sheet payload

## Practical push rule

Safe publication should be:

- `code + tests + scripts + governed docs + governed config`

Not:

- `everything on disk`

## Final verdict

Current workspace is **publishable only after scope filtering**.

The main risk was real:

- accidental secret publication,
- accidental temporary-file publication,
- and ambiguous inclusion of non-canonical document exports.

That risk is now reduced by ignore rules, but the `.docx` / planning-document subset still needs an explicit inclusion decision before final GitHub upload.
