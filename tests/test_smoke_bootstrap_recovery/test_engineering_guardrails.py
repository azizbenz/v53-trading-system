"""Tests for executable engineering guardrails."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from smoke_bootstrap_recovery import run_build1_smoke
from smoke_bootstrap_recovery.engineering_guardrails import (
    EngineeringGuardrailsPolicy,
    format_engineering_guardrails_summary,
    run_engineering_guardrails,
    write_engineering_guardrails_baseline,
)
from smoke_bootstrap_recovery.state_sanity_checker import (
    check_engineering_guardrails,
)


def _write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_policy(path: Path, **overrides: object) -> None:
    payload = {
        "scan_roots": ["src", "scripts", "tests"],
        "max_file_lines": 40,
        "max_function_lines": 10,
        "allow_print_paths": [],
        "hotspot_limit": 5,
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


@pytest.mark.build1
class TestEngineeringGuardrails:
    def test_run_engineering_guardrails_passes_for_clean_sample(
        self,
        repo_tmp_path: Path,
    ) -> None:
        _write_file(
            repo_tmp_path / "src" / "sample.py",
            "from __future__ import annotations\n\n"
            "def add(left: int, right: int) -> int:\n"
            "    return left + right\n",
        )
        policy_path = repo_tmp_path / "policy.json"
        baseline_path = repo_tmp_path / "baseline.json"
        _write_policy(policy_path)
        report = run_engineering_guardrails(
            repo_root=repo_tmp_path,
            policy=EngineeringGuardrailsPolicy.model_validate_json(
                policy_path.read_text(encoding="utf-8")
            ),
            policy_path=policy_path,
            baseline_path=baseline_path,
            accepted_fingerprints=frozenset(),
        )
        assert report.passed
        assert report.total_violation_count == 0

    def test_run_engineering_guardrails_detects_core_rules(
        self,
        repo_tmp_path: Path,
    ) -> None:
        _write_file(
            repo_tmp_path / "src" / "bad.py",
            "def noisy(value):\n"
            "    print(value)\n"
            "    try:\n"
            "        return value\n"
            "    except Exception:\n"
            "        return None\n",
        )
        policy_path = repo_tmp_path / "policy.json"
        baseline_path = repo_tmp_path / "baseline.json"
        _write_policy(policy_path, max_function_lines=3)
        report = run_engineering_guardrails(
            repo_root=repo_tmp_path,
            policy=EngineeringGuardrailsPolicy.model_validate_json(
                policy_path.read_text(encoding="utf-8")
            ),
            policy_path=policy_path,
            baseline_path=baseline_path,
            accepted_fingerprints=frozenset(),
        )
        rule_ids = {violation.rule_id for violation in report.violations}
        assert "MISSING_FUTURE_ANNOTATIONS" in rule_ids
        assert "MISSING_PARAM_ANNOTATION" in rule_ids
        assert "MISSING_RETURN_ANNOTATION" in rule_ids
        assert "PRINT_CALL" in rule_ids
        assert "BARE_EXCEPT" in rule_ids
        assert "FUNCTION_TOO_LONG" in rule_ids

    def test_baseline_suppresses_existing_violations(
        self,
        repo_tmp_path: Path,
    ) -> None:
        _write_file(
            repo_tmp_path / "src" / "legacy.py",
            "def legacy(value):\n"
            "    print(value)\n"
            "    return value\n",
        )
        policy_path = repo_tmp_path / "policy.json"
        baseline_path = repo_tmp_path / "baseline.json"
        _write_policy(policy_path)
        policy = EngineeringGuardrailsPolicy.model_validate_json(
            policy_path.read_text(encoding="utf-8")
        )
        initial_report = run_engineering_guardrails(
            repo_root=repo_tmp_path,
            policy=policy,
            policy_path=policy_path,
            baseline_path=baseline_path,
            accepted_fingerprints=frozenset(),
        )
        write_engineering_guardrails_baseline(
            baseline_path,
            policy_path=policy_path,
            report=initial_report,
        )
        accepted = frozenset(
            json.loads(baseline_path.read_text(encoding="utf-8"))[
                "accepted_fingerprints"
            ]
        )
        rerun_report = run_engineering_guardrails(
            repo_root=repo_tmp_path,
            policy=policy,
            policy_path=policy_path,
            baseline_path=baseline_path,
            accepted_fingerprints=accepted,
        )
        assert rerun_report.passed
        assert rerun_report.new_violation_count == 0
        assert rerun_report.total_violation_count > 0

    def test_check_engineering_guardrails_reports_baseline_aware_status(
        self,
        repo_tmp_path: Path,
    ) -> None:
        _write_file(
            repo_tmp_path / "src" / "legacy.py",
            "def legacy(value):\n"
            "    print(value)\n"
            "    return value\n",
        )
        policy_path = repo_tmp_path / "policy.json"
        baseline_path = repo_tmp_path / "baseline.json"
        _write_policy(policy_path)
        policy = EngineeringGuardrailsPolicy.model_validate_json(
            policy_path.read_text(encoding="utf-8")
        )
        report = run_engineering_guardrails(
            repo_root=repo_tmp_path,
            policy=policy,
            policy_path=policy_path,
            baseline_path=baseline_path,
            accepted_fingerprints=frozenset(),
        )
        write_engineering_guardrails_baseline(
            baseline_path,
            policy_path=policy_path,
            report=report,
        )
        check = check_engineering_guardrails(
            repo_root=str(repo_tmp_path),
            policy_path=str(policy_path),
            baseline_path=str(baseline_path),
        )
        ok, detail = check()
        assert ok
        assert "engineering guardrails clean against baseline" in detail

    def test_build1_smoke_executes_engineering_guardrails_check(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import smoke_bootstrap_recovery as sbr

        calls: list[str] = []

        def _fake_engineering_guardrails():
            def _check() -> tuple[bool, str]:
                calls.append("called")
                return True, "ok"

            return _check

        def _pass_dag_clean():
            return lambda: (True, "DAG clean")

        def _fake_recovery(module_name, factory, config, **kwargs):
            from smoke_bootstrap_recovery.smoke_models import RecoveryResult, SmokeStatus

            return RecoveryResult(
                module_name=module_name,
                status=SmokeStatus.PASS,
                pre_state_valid=True,
                post_state_valid=True,
            )

        monkeypatch.setattr(sbr, "check_engineering_guardrails", _fake_engineering_guardrails)
        monkeypatch.setattr(sbr, "check_dag_clean", _pass_dag_clean)
        monkeypatch.setattr(sbr, "run_recovery_cycle", _fake_recovery)

        report = run_build1_smoke(fd_count_provider=lambda: 10)
        assert report.passed
        assert calls == ["called"]

    def test_summary_mentions_first_new_violation(
        self,
        repo_tmp_path: Path,
    ) -> None:
        _write_file(
            repo_tmp_path / "src" / "bad.py",
            "def legacy(value):\n"
            "    print(value)\n"
            "    return value\n",
        )
        policy_path = repo_tmp_path / "policy.json"
        baseline_path = repo_tmp_path / "baseline.json"
        _write_policy(policy_path)
        report = run_engineering_guardrails(
            repo_root=repo_tmp_path,
            policy=EngineeringGuardrailsPolicy.model_validate_json(
                policy_path.read_text(encoding="utf-8")
            ),
            policy_path=policy_path,
            baseline_path=baseline_path,
            accepted_fingerprints=frozenset(),
        )
        summary = format_engineering_guardrails_summary(report)
        assert "new_violations=" in summary
        assert "first_new_violation=" in summary
