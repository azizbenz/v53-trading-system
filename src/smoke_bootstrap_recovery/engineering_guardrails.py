"""Executable engineering guardrails derived from CODEX_PROMPT.md."""

from __future__ import annotations

import ast
import hashlib
import json
from collections import Counter, defaultdict
from enum import StrEnum
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, Field


RULE_ALLOW_ANY_COMMENT = "noqa: Any"


class GuardrailSeverity(StrEnum):
    ERROR = "error"


class EngineeringGuardrailsPolicy(BaseModel, frozen=True):
    """Typed policy for repo-wide engineering guardrail scans."""

    scan_roots: tuple[str, ...] = ("src", "scripts", "tests")
    max_file_lines: int = Field(default=700, ge=1)
    max_function_lines: int = Field(default=120, ge=1)
    allow_print_paths: tuple[str, ...] = ()
    hotspot_limit: int = Field(default=12, ge=1)


class GuardrailViolation(BaseModel, frozen=True):
    """One audit-ready engineering guardrail violation."""

    rule_id: str
    severity: GuardrailSeverity = GuardrailSeverity.ERROR
    file_path: str
    line: int = Field(default=0, ge=0)
    symbol: str = ""
    message: str
    fingerprint: str


class GuardrailHotspot(BaseModel, frozen=True):
    """Top offending file summary."""

    file_path: str
    violation_count: int = Field(default=0, ge=0)
    rule_counts: tuple[str, ...] = ()


class EngineeringGuardrailsReport(BaseModel, frozen=True):
    """Full baseline-aware engineering guardrail report."""

    policy_path: str
    baseline_path: str
    scanned_file_count: int = Field(default=0, ge=0)
    total_violation_count: int = Field(default=0, ge=0)
    baseline_violation_count: int = Field(default=0, ge=0)
    new_violation_count: int = Field(default=0, ge=0)
    passed: bool = False
    violations: tuple[GuardrailViolation, ...] = ()
    new_violations: tuple[GuardrailViolation, ...] = ()
    hotspots: tuple[GuardrailHotspot, ...] = ()


def load_engineering_guardrails_policy(
    path: Path | str,
) -> EngineeringGuardrailsPolicy:
    """Load guardrail policy from JSON."""

    policy_path = Path(path)
    payload = json.loads(policy_path.read_text(encoding="utf-8"))
    return EngineeringGuardrailsPolicy(**payload)


def load_engineering_guardrails_baseline(
    path: Path | str,
) -> frozenset[str]:
    """Load accepted violation fingerprints from JSON."""

    baseline_path = Path(path)
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    accepted = payload.get("accepted_fingerprints", ())
    if not isinstance(accepted, list):
        raise ValueError("engineering guardrails baseline must contain a list")
    return frozenset(str(value) for value in accepted)


def write_engineering_guardrails_baseline(
    path: Path | str,
    *,
    policy_path: Path | str,
    report: EngineeringGuardrailsReport,
) -> Path:
    """Persist a baseline from the current full violation set."""

    baseline_path = Path(path)
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "policy_path": str(Path(policy_path)),
        "accepted_fingerprints": sorted(
            {
                violation.fingerprint
                for violation in report.violations
            }
        ),
    }
    baseline_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return baseline_path


def run_engineering_guardrails(
    *,
    repo_root: Path,
    policy: EngineeringGuardrailsPolicy,
    policy_path: Path,
    baseline_path: Path,
    accepted_fingerprints: frozenset[str] | None = None,
) -> EngineeringGuardrailsReport:
    """Scan the repo against executable engineering guardrails."""

    baseline = accepted_fingerprints or frozenset()
    violations: list[GuardrailViolation] = []
    for file_path in _discover_python_files(repo_root=repo_root, policy=policy):
        violations.extend(
            _scan_python_file(
                repo_root=repo_root,
                file_path=file_path,
                policy=policy,
            )
        )

    ordered_violations = tuple(
        sorted(
            violations,
            key=lambda item: (item.file_path, item.line, item.rule_id, item.symbol),
        )
    )
    new_violations = tuple(
        violation
        for violation in ordered_violations
        if violation.fingerprint not in baseline
    )
    hotspots = _build_hotspots(
        ordered_violations,
        limit=policy.hotspot_limit,
    )
    return EngineeringGuardrailsReport(
        policy_path=str(policy_path),
        baseline_path=str(baseline_path),
        scanned_file_count=len(_discover_python_files(repo_root=repo_root, policy=policy)),
        total_violation_count=len(ordered_violations),
        baseline_violation_count=len(ordered_violations) - len(new_violations),
        new_violation_count=len(new_violations),
        passed=len(new_violations) == 0,
        violations=ordered_violations,
        new_violations=new_violations,
        hotspots=hotspots,
    )


def format_engineering_guardrails_summary(
    report: EngineeringGuardrailsReport,
) -> str:
    """Format a short audit-ready summary."""

    lines = [
        "ENGINEERING GUARDRAILS",
        f"scanned_files={report.scanned_file_count}",
        f"total_violations={report.total_violation_count}",
        f"baseline_violations={report.baseline_violation_count}",
        f"new_violations={report.new_violation_count}",
    ]
    if report.hotspots:
        lines.append("hotspots=")
        for hotspot in report.hotspots[:5]:
            lines.append(
                f"- {hotspot.file_path}: {hotspot.violation_count} "
                f"({' ; '.join(hotspot.rule_counts)})"
            )
    if report.new_violations:
        lines.append("first_new_violation=")
        first = report.new_violations[0]
        lines.append(
            f"- {first.file_path}:{first.line} {first.rule_id} {first.message}"
        )
    return "\n".join(lines)


def _discover_python_files(
    *,
    repo_root: Path,
    policy: EngineeringGuardrailsPolicy,
) -> tuple[Path, ...]:
    files: list[Path] = []
    for root_name in policy.scan_roots:
        root_path = repo_root / root_name
        if not root_path.exists():
            continue
        files.extend(
            path
            for path in root_path.rglob("*.py")
            if path.is_file()
        )
    return tuple(sorted(files))


def _scan_python_file(
    *,
    repo_root: Path,
    file_path: Path,
    policy: EngineeringGuardrailsPolicy,
) -> tuple[GuardrailViolation, ...]:
    source = file_path.read_text(encoding="utf-8-sig")
    lines = source.splitlines()
    relative_path = file_path.relative_to(repo_root).as_posix()
    violations: list[GuardrailViolation] = []

    if "from __future__ import annotations" not in source:
        violations.append(
            _violation(
                rule_id="MISSING_FUTURE_ANNOTATIONS",
                file_path=relative_path,
                line=1,
                message="missing 'from __future__ import annotations'",
                fingerprint=f"{relative_path}|MISSING_FUTURE_ANNOTATIONS",
            )
        )

    if len(lines) > policy.max_file_lines:
        violations.append(
            _violation(
                rule_id="FILE_TOO_LONG",
                file_path=relative_path,
                line=1,
                message=(
                    f"file has {len(lines)} lines, exceeds max_file_lines="
                    f"{policy.max_file_lines}"
                ),
                fingerprint=f"{relative_path}|FILE_TOO_LONG",
            )
        )

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as exc:
        violations.append(
            _violation(
                rule_id="PARSE_ERROR",
                file_path=relative_path,
                line=exc.lineno or 1,
                message=f"file could not be parsed: {exc.msg}",
                fingerprint=f"{relative_path}|PARSE_ERROR",
            )
        )
        return tuple(violations)
    visitor = _GuardrailVisitor(
        file_path=relative_path,
        lines=lines,
        policy=policy,
    )
    visitor.visit(tree)
    violations.extend(visitor.violations)
    return tuple(violations)


def _build_hotspots(
    violations: tuple[GuardrailViolation, ...],
    *,
    limit: int,
) -> tuple[GuardrailHotspot, ...]:
    by_file: dict[str, Counter[str]] = defaultdict(Counter)
    for violation in violations:
        by_file[violation.file_path][violation.rule_id] += 1

    hotspots = [
        GuardrailHotspot(
            file_path=file_path,
            violation_count=sum(counter.values()),
            rule_counts=tuple(
                f"{rule_id}={count}"
                for rule_id, count in sorted(
                    counter.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ),
        )
        for file_path, counter in by_file.items()
    ]
    return tuple(
        sorted(
            hotspots,
            key=lambda item: (-item.violation_count, item.file_path),
        )[:limit]
    )


def _violation(
    *,
    rule_id: str,
    file_path: str,
    line: int,
    message: str,
    fingerprint: str,
    symbol: str = "",
) -> GuardrailViolation:
    return GuardrailViolation(
        rule_id=rule_id,
        file_path=file_path,
        line=line,
        symbol=symbol,
        message=message,
        fingerprint=fingerprint,
    )


def _annotation_contains_any(annotation: ast.expr | None) -> bool:
    if annotation is None:
        return False
    for node in ast.walk(annotation):
        if isinstance(node, ast.Name) and node.id == "Any":
            return True
        if isinstance(node, ast.Attribute) and node.attr == "Any":
            return True
    return False


def _context_hash(lines: list[str], line_number: int) -> str:
    current_index = max(line_number - 1, 0)
    context = "\n".join(
        (
            lines[current_index - 1] if current_index > 0 else "",
            lines[current_index] if current_index < len(lines) else "",
            lines[current_index + 1] if current_index + 1 < len(lines) else "",
        )
    )
    return hashlib.sha1(context.encode("utf-8")).hexdigest()[:12]


class _GuardrailVisitor(ast.NodeVisitor):
    """AST visitor enforcing repo guardrails."""

    def __init__(
        self,
        *,
        file_path: str,
        lines: list[str],
        policy: EngineeringGuardrailsPolicy,
    ) -> None:
        self._file_path = file_path
        self._lines = lines
        self._policy = policy
        self._class_stack: list[str] = []
        self._function_stack: list[str] = []
        self.violations: list[GuardrailViolation] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            if not self._is_print_allowed():
                self.violations.append(
                    _violation(
                        rule_id="PRINT_CALL",
                        file_path=self._file_path,
                        line=node.lineno,
                        message="print() is forbidden by engineering guardrails",
                        fingerprint=(
                            f"{self._file_path}|PRINT_CALL|"
                            f"{_context_hash(self._lines, node.lineno)}"
                        ),
                    )
                )
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        bare_exception = node.type is None
        naked_exception = (
            isinstance(node.type, ast.Name)
            and node.type.id == "Exception"
            and node.name is None
        )
        if bare_exception or naked_exception:
            self.violations.append(
                _violation(
                    rule_id="BARE_EXCEPT",
                    file_path=self._file_path,
                    line=node.lineno,
                    message="bare except or 'except Exception:' without alias is forbidden",
                    fingerprint=(
                        f"{self._file_path}|BARE_EXCEPT|"
                        f"{_context_hash(self._lines, node.lineno)}"
                    ),
                )
            )
        self.generic_visit(node)

    def _visit_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        qualified_name = ".".join(
            (*self._class_stack, *self._function_stack, node.name)
        )
        self._function_stack.append(node.name)
        self._check_function_size(node, qualified_name)
        self._check_function_annotations(node, qualified_name)
        self.generic_visit(node)
        self._function_stack.pop()

    def _check_function_size(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        qualified_name: str,
    ) -> None:
        if node.end_lineno is None:
            return
        line_count = node.end_lineno - node.lineno + 1
        if line_count <= self._policy.max_function_lines:
            return
        self.violations.append(
            _violation(
                rule_id="FUNCTION_TOO_LONG",
                file_path=self._file_path,
                line=node.lineno,
                symbol=qualified_name,
                message=(
                    f"function has {line_count} lines, exceeds max_function_lines="
                    f"{self._policy.max_function_lines}"
                ),
                fingerprint=f"{self._file_path}|FUNCTION_TOO_LONG|{qualified_name}",
            )
        )

    def _check_function_annotations(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        qualified_name: str,
    ) -> None:
        if node.returns is None:
            self.violations.append(
                _violation(
                    rule_id="MISSING_RETURN_ANNOTATION",
                    file_path=self._file_path,
                    line=node.lineno,
                    symbol=qualified_name,
                    message="function return annotation is required",
                    fingerprint=(
                        f"{self._file_path}|MISSING_RETURN_ANNOTATION|{qualified_name}"
                    ),
                )
            )
        elif _annotation_contains_any(node.returns) and not self._line_allows_any(node.returns.lineno):
            self.violations.append(
                _violation(
                    rule_id="ANY_ANNOTATION",
                    file_path=self._file_path,
                    line=node.returns.lineno,
                    symbol=f"{qualified_name}:return",
                    message="Any is forbidden unless explicitly waived with '# noqa: Any'",
                    fingerprint=f"{self._file_path}|ANY_ANNOTATION|{qualified_name}|return",
                )
            )

        all_args = (
            list(node.args.posonlyargs)
            + list(node.args.args)
            + list(node.args.kwonlyargs)
        )
        if node.args.vararg is not None:
            all_args.append(node.args.vararg)
        if node.args.kwarg is not None:
            all_args.append(node.args.kwarg)

        for arg in all_args:
            if arg.arg in {"self", "cls"}:
                continue
            if arg.annotation is None:
                self.violations.append(
                    _violation(
                        rule_id="MISSING_PARAM_ANNOTATION",
                        file_path=self._file_path,
                        line=arg.lineno,
                        symbol=f"{qualified_name}:{arg.arg}",
                        message=f"parameter '{arg.arg}' annotation is required",
                        fingerprint=(
                            f"{self._file_path}|MISSING_PARAM_ANNOTATION|"
                            f"{qualified_name}|{arg.arg}"
                        ),
                    )
                )
                continue
            if _annotation_contains_any(arg.annotation) and not self._line_allows_any(arg.annotation.lineno):
                self.violations.append(
                    _violation(
                        rule_id="ANY_ANNOTATION",
                        file_path=self._file_path,
                        line=arg.annotation.lineno,
                        symbol=f"{qualified_name}:{arg.arg}",
                        message="Any is forbidden unless explicitly waived with '# noqa: Any'",
                        fingerprint=(
                            f"{self._file_path}|ANY_ANNOTATION|"
                            f"{qualified_name}|{arg.arg}"
                        ),
                    )
                )

    def _is_print_allowed(self) -> bool:
        relative_path = PurePosixPath(self._file_path)
        return any(relative_path.match(pattern) for pattern in self._policy.allow_print_paths)

    def _line_allows_any(self, line_number: int) -> bool:
        if line_number <= 0 or line_number > len(self._lines):
            return False
        return RULE_ALLOW_ANY_COMMENT in self._lines[line_number - 1]
