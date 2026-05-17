# V5.3 — CODEX ULTRA STRICT SPEC  
## Scripts CLI (argparse) + Logging + Pytest + Orchestration

**Purpose:** This document is a hard specification for Codex.  
Codex must implement exactly the described runnable pipeline layer for V5.3.

---

# 0) HARD RULES (NO EXCEPTIONS)

## R0.1 — No hallucination
Codex must not invent missing modules, APIs, or behavior.  
If an integration target is missing, Codex must:
- detect it
- fail closed
- write `NOT_IMPLEMENTED` in output logs/tests

## R0.2 — Minimal diffs only
No refactor of trading logic.  
Only add orchestration scripts, configs templates, and tests.

## R0.3 — No strategy semantic changes
No changes to:
- side logic
- execution logic
- risk rules
- promotion rules
- engine A/B/C/D semantics

## R0.4 — Quant anchors frozen
No edits to:
- PSR / DSR
- POT-GPD
- Energy distance anchors

## R0.5 — Determinism required
All artifacts/logging/hashes must be deterministic.

---

# 1) EXACT FILES TO CREATE

Codex MUST create exactly these folders/files if missing.

```
configs/
  backtest.yaml
  calibration.yaml
  promotion_rules.yaml
  runtime_prod.yaml
  runtime_paper.yaml
  kill_switch.yaml

scripts/
  setup_env.py
  smoke_check.py
  run_unit_tests.py
  run_replay.py
  run_backtest.py
  run_calibration.py
  run_export_artifacts.py
  run_promotion_gate.py
  run_local_lab_loop.py
  run_vps_runtime.py
  run_paper_trading.py
  run_live_trading.py
  run_prod_safe_check.py

tests/
  scripts/
    test_setup_env.py
    test_smoke_check.py
    test_run_unit_tests.py
    test_run_replay.py
    test_run_backtest.py
    test_run_calibration.py
    test_run_export_artifacts.py
    test_run_promotion_gate.py
    test_run_local_lab_loop.py
    test_run_vps_runtime.py
    test_run_paper_trading.py
    test_run_live_trading.py
    test_run_prod_safe_check.py
```

Codex MUST NOT rename these files.

---

# 2) LOGGING STANDARD (MANDATORY)

All scripts must write logs into:

```
logs/
  lab/
  runtime/
  daily/
  smoke/
  tests/
```

### Log file naming
Each run must generate:

```
logs/<slice>/<script_name>_<UTC_ISO_TIMESTAMP>.log
```

Example:
```
logs/smoke/smoke_check_2026-04-23T12-01-33Z.log
```

### Logging format (exact)
```
%(asctime)s %(levelname)s %(name)s %(message)s
```

### Required log lines
Every script must log:
- START + argv
- SUCCESS summary
- FAIL with stack trace

---

# 3) CLI STANDARD (argparse)

All scripts MUST use `argparse` only.

### Required CLI conventions
- `--config` points to YAML when applicable
- `--output-dir` must be supported when script generates outputs
- `--log-dir` optional override (default uses `logs/<slice>/`)
- `--dry-run` for any script that could place orders

### Exit codes
- 0 = success
- 1 = failure
- 2 = invalid CLI args
- 3 = missing config/data

---

# 4) COMMON UTILITIES (MUST CREATE)

Codex must create:

```
scripts/_script_utils.py
```

It must contain:

- `setup_logger(slice_name: str, script_name: str, log_dir_override: str | None) -> logging.Logger`
- `ensure_dir(path: Path) -> None`
- `load_yaml(path: Path) -> dict`
- `safe_write_json(path: Path, obj: dict) -> None` (atomic write)
- `utc_timestamp_slug() -> str`
- `fail_closed_exit(code: int, msg: str) -> NoReturn`

All scripts must reuse these helpers.

---

# 5) SCRIPT SPECIFICATIONS (STRICT)

## 5.1 scripts/setup_env.py

### Role
Bootstrap environment consistency.

### CLI
- `--venv-dir` default `.venv`
- `--requirements` default `requirements.txt`
- `--force` bool

### Behavior
- Verify python version >= 3.11 (or project configured version)
- Create venv if missing
- Install requirements
- Verify `.env` exists (warn only, do not fail)

### Output
Logs + console summary.

### Test
`tests/scripts/test_setup_env.py` must:
- run in temp dir
- validate that it fails closed if requirements missing

---

## 5.2 scripts/smoke_check.py

### Role
30-second proof the system can import and run minimal microstructure pipeline.

### CLI
- `--pair` default `BTCUSDT`
- `--touch-eps-bps` default `10.0`
- `--log-dir` optional

### Behavior (must do)
- import `evaluate_walls_and_spoofing`
- create 2 depth snapshots + 1 trade
- call evaluator
- assert deterministic output hash across 2 calls

### Output
- exit 0 if pass
- exit 1 if fail

### Test
Must verify:
- exit code = 0
- log file exists
- output includes SUCCESS

---

## 5.3 scripts/run_unit_tests.py

### Role
Run pytest suite.

### CLI
- `--k` optional filter
- `--maxfail` default 1

### Behavior
- calls `pytest` programmatically
- logs summary
- returns exit code pytest

### Test
Must confirm:
- can run with `-k smoke_check`
- produces log file

---

## 5.4 scripts/run_replay.py

### Role
Run replay pipeline from raw data to replay bundle.

### CLI
- `--pair` required
- `--start-ns` required
- `--end-ns` required
- `--data-source` required
- `--output-dir` required

### Behavior
If actual replay loader not implemented:
- fail closed with explicit message: `REPLAY_NOT_IMPLEMENTED`

### Output
If implemented:
- write replay bundle files:
  - `depth_events.jsonl`
  - `trades.jsonl`
  - `meta.json`

### Test
Must cover:
- missing output-dir fails closed
- NOT_IMPLEMENTED branch exits with code 1 and logs

---

## 5.5 scripts/run_backtest.py

### CLI
- `--config` required
- `--output-dir` required

### Behavior
- load config YAML
- call canonical backtest entrypoint if exists
- else fail closed `BACKTEST_NOT_IMPLEMENTED`

### Output (if implemented)
- `backtest_report.json`
- `equity_curve.csv`
- `trade_log.csv`
- `risk_report.json`

### Test
Same pattern: detect missing entrypoint and fail closed with deterministic logs.

---

## 5.6 scripts/run_calibration.py

### CLI
- `--export-dir` required
- `--calibration-config` required
- `--output-dir` required

### Behavior
- load export bundle
- call calibration loader
- output calibration artifact + hash file
- else fail closed `CALIBRATION_NOT_IMPLEMENTED`

### Output
- `calibration_artifact.json`
- `calibration_hash.txt`

### Test
Must verify atomic write + deterministic hash.

---

## 5.7 scripts/run_export_artifacts.py

### CLI
- `--pair` required
- `--start-ns` required
- `--end-ns` required
- `--output-dir` required

### Behavior
- run feature extraction pipeline
- export artifact dir
- else fail closed `EXPORT_NOT_IMPLEMENTED`

### Test
Must validate stable output dir layout.

---

## 5.8 scripts/run_promotion_gate.py

### CLI
- `--artifact` required
- `--rules` default `configs/promotion_rules.yaml`

### Behavior
- load artifact + rules
- apply gating checks
- output PASS/FAIL json

### Output
- `promotion_decision.json`

### Test
Must create dummy artifact violating rule → FAIL.

---

## 5.9 scripts/run_local_lab_loop.py

### CLI
- `--pair` required
- `--start-ns` required
- `--end-ns` required
- `--output-dir` required

### Behavior
Chain:
replay → export → calibration → promotion decision

If any stage missing:
fail closed and log which stage missing.

### Output
- `lab_loop_report.json`

### Test
Must confirm fail closed stage detection is deterministic.

---

## 5.10 scripts/run_vps_runtime.py

### CLI
- `--profile` default `configs/runtime_prod.yaml`
- `--artifact` required
- `--kill-switch` default `configs/kill_switch.yaml`
- `--dry-run` bool (default True)
- `--max-iterations` default 10

### Behavior
- must never place orders unless `--dry-run false`
- must log all decisions and refusal codes

### Output
- `runtime_decisions.jsonl`

### Test
Must confirm `--dry-run` prevents any order send call.

---

## 5.11 scripts/run_paper_trading.py

### CLI
Same as runtime.

### Behavior
- always dry-run enforced regardless of CLI

### Output
- `paper_trading_log.jsonl`

### Test
Must confirm enforcement.

---

## 5.12 scripts/run_live_trading.py

### CLI
- `--profile` required
- `--artifact` required
- `--kill-switch` required
- `--confirm-live` required (must be exact string `I_UNDERSTAND_LIVE_TRADING_RISK`)

### Behavior
- if confirm string missing → exit with code 3
- if confirm present → run runtime with real exchange adapter

### Test
Must confirm fails without confirm string.

---

## 5.13 scripts/run_prod_safe_check.py

### CLI
- `--artifact` required
- `--backtest-report` required
- `--runtime-logs` required

### Behavior
- verify hashes match
- verify promotion decision exists
- verify kill-switch exists
- output PASS/WARN/FAIL

### Output
- `prod_safe_report.json`

### Test
Must verify FAIL if artifact missing hash.

---

# 6) CONFIG TEMPLATES (MUST CREATE)

Codex must create YAML templates with minimal defaults:

## configs/backtest.yaml
Must include:
- fees
- slippage
- capital
- start/end
- pair list

## configs/calibration.yaml
Must include:
- window sizes
- threshold defaults
- top_n depth

## configs/promotion_rules.yaml
Must include:
- max_drawdown
- min_psr (but do not change PSR formula)
- max_trades_per_day

## configs/runtime_prod.yaml
Must include:
- polling frequency
- max order size
- exchange mode

## configs/runtime_paper.yaml
Same but paper mode enforced.

## configs/kill_switch.yaml
Must include:
- max_loss_day
- max_drawdown_intraday
- max_spread_bps
- max_toxicity_score
- data_stale_timeout_ms

---

# 7) PYTEST REQUIREMENTS (STRICT)

All tests must:
- use `tmp_path`
- never write to real project logs folder
- monkeypatch log dir to tmp
- validate exit codes

Codex must implement a helper:

```
tests/scripts/_run_script_helper.py
```

It must provide:
- `run_script(module_path: str, args: list[str]) -> (exit_code, stdout, stderr)`
- uses `subprocess.run([sys.executable, module_path, ...])`

---

# 8) ACCEPTANCE CRITERIA (PROOF)

Codex must run:

```bash
python -m pytest -q tests/scripts
python scripts/smoke_check.py
python scripts/run_unit_tests.py -k smoke_check
```

and paste the exact outputs.

---

# 9) FORBIDDEN ACTIONS

Codex must NOT:
- add torch/sklearn dependencies
- change engine A/B/C/D trading decisions
- modify existing quant anchors
- add any directional ML label into VPS runtime
- rewrite large modules for style only

---

# END OF SPEC
