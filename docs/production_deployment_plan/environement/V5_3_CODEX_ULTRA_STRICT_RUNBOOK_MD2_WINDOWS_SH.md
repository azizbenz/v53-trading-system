# V5.3 — MD2 CODEX ULTRA STRICT  
## Windows Orchestration (.bat) + Shell (.sh) + venv + requirements + RUN_ALL_SAFE

**Purpose:** Provide Codex a hard spec for operational scripts that allow the entire V5.3 system to be executed and audited end-to-end, locally on Windows (primary), with Linux shell support (secondary).

This MD2 complements MD1 (Python scripts CLI + pytest).  
MD2 focuses on **how to run** everything reliably and deterministically.

---

# 0) HARD RULES (NO EXCEPTIONS)

## R0.1 — No refactor of trading code
Only orchestration scripts, launchers, and env tooling.

## R0.2 — Must be reproducible on a clean machine
A new Windows machine must be able to:
- create venv
- install deps
- run smoke checks
- run tests
- run lab loop
- run paper runtime
with one command.

## R0.3 — Deterministic logs and output dirs
All run scripts must create:
- run_id
- timestamp
- structured output directories

## R0.4 — No admin rights required
No registry edits, no system installs.  
Everything runs from project folder.

## R0.5 — Fail closed always
If any step fails, orchestration stops immediately and returns non-zero exit code.

---

# 1) EXACT FILES TO CREATE

Codex MUST create exactly these files (no renaming):

```
tools/
  win/
    bootstrap_venv.bat
    run_smoke.bat
    run_tests.bat
    run_lab_loop.bat
    run_paper_runtime.bat
    run_prod_safe_check.bat
    run_all_safe.bat
    clean_outputs.bat
    show_last_logs.bat

  sh/
    bootstrap_venv.sh
    run_smoke.sh
    run_tests.sh
    run_lab_loop.sh
    run_paper_runtime.sh
    run_prod_safe_check.sh
    run_all_safe.sh
    clean_outputs.sh
    show_last_logs.sh

requirements/
  requirements_base.txt
  requirements_dev.txt

.env.example

Makefile   (optional but recommended)

README_RUNBOOK.md
```

Codex MUST NOT create additional random scripts.

---

# 2) REQUIRED DIRECTORY LAYOUT

Codex must enforce this runtime output layout:

```
outputs/
  runs/
    <RUN_ID>/
      meta.json
      smoke/
      tests/
      replay/
      export/
      calibration/
      promotion/
      runtime/
      prod_safe/
logs/
  daily/
  smoke/
  tests/
  lab/
  runtime/
```

RUN_ID format must be:

```
YYYYMMDD_HHMMSS_<random4>
```

Example:
```
20260423_223501_A7K2
```

---

# 3) ENV FILE STANDARD

Codex must create:

## 3.1 `.env.example`

Must contain placeholders:

```
# EXCHANGE
BINANCE_API_KEY=
BINANCE_API_SECRET=

# MODE
V53_ENV=LOCAL
V53_PROFILE=paper

# PATHS
V53_DATA_DIR=./data
V53_OUTPUTS_DIR=./outputs
V53_LOGS_DIR=./logs

# SAFETY
V53_LIVE_TRADING_ALLOWED=0
```

Rules:
- `.env` is not committed
- `.env.example` must exist
- scripts must warn if `.env` missing but should still run for smoke/tests

---

# 4) REQUIREMENTS LAYOUT

Codex must create:

## requirements/requirements_base.txt
Minimal runtime dependencies only:
- numpy
- pandas
- pydantic
- PyYAML
- python-dotenv
- scipy (if already used)
- requests (only if used)

## requirements/requirements_dev.txt
Dev-only:
- pytest
- pytest-cov
- ruff
- mypy
- types-PyYAML

**Rule:**  
Codex must NOT add torch/sklearn/xgboost unless explicitly requested in a separate ML spec.

---

# 5) WINDOWS SCRIPTS (.bat) SPEC

All `.bat` scripts must:
- use `@echo off`
- use `setlocal enabledelayedexpansion`
- fail on error with `if errorlevel 1 exit /b 1`
- call python scripts from `scripts/`

All `.bat` must assume project root is current directory.

---

## 5.1 tools/win/bootstrap_venv.bat

### Role
Create `.venv` and install dependencies.

### Steps (must follow exactly)
1. if `.venv` exists, skip unless `--force`
2. create venv
3. install base requirements
4. install dev requirements
5. verify python executable works

### Must run:
```
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements\requirements_base.txt
.venv\Scripts\python.exe -m pip install -r requirements\requirements_dev.txt
```

### Output
- prints python version
- prints pip freeze into `outputs/venv_freeze.txt`

---

## 5.2 tools/win/run_smoke.bat

### Role
Run smoke check with isolated output dir.

### Steps
1. ensure venv exists
2. create RUN_ID
3. create output folder
4. call `scripts/smoke_check.py`

Must call:
```
.venv\Scripts\python.exe scripts\smoke_check.py --pair BTCUSDT --touch-eps-bps 10.0
```

### Must write
`outputs/runs/<RUN_ID>/smoke/smoke_result.json`

---

## 5.3 tools/win/run_tests.bat

### Role
Run pytest with logs.

Must call:
```
.venv\Scripts\python.exe -m pytest -q
```

Must store:
- stdout/stderr into `outputs/runs/<RUN_ID>/tests/pytest_output.txt`
- exit code preserved

---

## 5.4 tools/win/run_lab_loop.bat

### Role
Run the governed Local Lab loop.

Must call:
```
.venv\Scripts\python.exe scripts\run_local_lab_loop.py --pair BTCUSDT --start-ns ... --end-ns ... --output-dir outputs\runs\<RUN_ID>\lab
```

If stage missing, script must fail closed.

---

## 5.5 tools/win/run_paper_runtime.bat

### Role
Run runtime in paper mode.

Must call:
```
.venv\Scripts\python.exe scripts\run_paper_trading.py --artifact <artifact_path> --profile configs\runtime_paper.yaml --max-iterations 50
```

---

## 5.6 tools/win/run_prod_safe_check.bat

### Role
Run prod safe gate script.

Must call:
```
.venv\Scripts\python.exe scripts\run_prod_safe_check.py --artifact ... --backtest-report ... --runtime-logs ...
```

---

## 5.7 tools/win/run_all_safe.bat  (MOST IMPORTANT)

### Role
Single command that runs everything safe.

### Must execute pipeline in this order:

1) bootstrap_venv  
2) run_smoke  
3) run_tests  
4) run_lab_loop  
5) run_paper_runtime  
6) run_prod_safe_check  

If any step fails → stop immediately.

### Output
At the end must print:

```
ALL_SAFE_COMPLETED RUN_ID=<RUN_ID>
```

---

## 5.8 tools/win/clean_outputs.bat

Deletes:
- outputs/runs/*
- logs/*

But must preserve:
- logs/.gitkeep if exists

---

## 5.9 tools/win/show_last_logs.bat

Shows last log file for each slice:
- smoke
- tests
- runtime

---

# 6) LINUX/MAC SCRIPTS (.sh) SPEC

Same logic as `.bat` but POSIX.

All `.sh` must:
- start with `#!/usr/bin/env bash`
- use `set -euo pipefail`
- assume project root

venv path:
```
.venv/bin/python
```

---

# 7) README_RUNBOOK.md (MANDATORY)

Codex must create a runbook with exact commands:

## Sections required

### 7.1 Setup Windows
```
tools\win\bootstrap_venv.bat
```

### 7.2 Run smoke
```
tools\win\run_smoke.bat
```

### 7.3 Run all safe
```
tools\win\run_all_safe.bat
```

### 7.4 Setup Linux
```
bash tools/sh/bootstrap_venv.sh
```

### 7.5 Logs interpretation
Explain where logs are and what "FAIL_CLOSED" means.

### 7.6 How to do a reproducible audit
Explain:
- rerun same RUN_ID not allowed
- compare artifacts by hash
- keep meta.json

---

# 8) META.JSON STANDARD (MANDATORY)

Each RUN_ID must create:

`outputs/runs/<RUN_ID>/meta.json`

It must contain:

```json
{
  "run_id": "...",
  "timestamp_utc": "...",
  "git_commit": "UNKNOWN_OR_HASH",
  "python_version": "...",
  "platform": "...",
  "user": "...",
  "profile": "paper|prod",
  "pipeline_steps": ["smoke","tests","lab_loop","paper_runtime","prod_safe_check"],
  "status": "SUCCESS|FAILED",
  "failure_step": null
}
```

If git commit cannot be detected, store `"UNKNOWN"`.

---

# 9) PYTESTS FOR WINDOWS/SH SCRIPTS (YES)

Codex must create:

```
tests/tools/
  test_win_scripts_exist.py
  test_sh_scripts_exist.py
  test_run_all_safe_contains_steps.py
```

Tests must verify:
- files exist
- scripts contain required commands
- ordering is correct
- no forbidden commands (like deleting root)

Example test must check run_all_safe.bat includes in correct order:
bootstrap_venv → run_smoke → run_tests → run_lab_loop → run_paper_runtime → run_prod_safe_check

---

# 10) FORBIDDEN ACTIONS

Codex must NOT:
- write live trading keys in any file
- set V53_LIVE_TRADING_ALLOWED=1 by default
- implement auto trading in bat/sh scripts
- run exchange API calls in smoke/tests

---

# 11) ACCEPTANCE CRITERIA

Codex must prove success by running:

Windows:
```
tools\win\run_all_safe.bat
```

Linux:
```
bash tools/sh/run_all_safe.sh
```

and show:
- RUN_ID created
- outputs/runs/<RUN_ID>/meta.json exists
- logs exist
- pytest passes

---

# END OF MD2
