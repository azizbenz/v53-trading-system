# Backtest Test Coverage Evidence

## Requested bands and actual paths

Requested path discovery note:

- `tests/test_portfolio_backbone` does not exist in this repo.
- The actual equivalent testable path in the current tree is `tests/test_portfolio_minimal`.

## Test commands

### Band 1

Command used:

```text
python -m pytest -q tests/test_local_replay_runtime tests/test_backtest_artifact_import tests/test_portfolio_minimal --tb=short --disable-warnings --basetemp=.test_tmp\pytest_backtest_audit_band1_escalated
```

Result:

```text
411 passed
```

### Band 2

Command used:

```text
python -m pytest -q tests/test_execution_backbone tests/test_risk_backbone tests/test_scoring_backbone tests/cockpit --tb=short --disable-warnings --basetemp=.test_tmp\pytest_backtest_audit_band2_escalated
```

Result:

```text
662 passed
```

## Environment failures separated

Initial sandboxed runs produced Windows temp-dir cleanup failures:

- `PermissionError: [WinError 5]` under `.test_tmp\pytest_backtest_audit_band1`
- `PermissionError: [WinError 5]` under `.test_tmp\pytest_backtest_audit_band2`

Those failures were environment/sandbox cleanup issues.

Unrestricted reruns passed cleanly and were used as the final logic status.

## Coverage reading

- Replay/export/import/portfolio-minimal rails are well-covered.
- Execution/risk/scoring/cockpit regression bands pass against the current workspace.
- Passing tests do **not** prove Strategy Ladder readiness by themselves; they only prove the current replay/export rails are stable enough to audit.
