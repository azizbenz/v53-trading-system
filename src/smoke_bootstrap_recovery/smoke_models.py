"""
7.5.0 — Smoke Models: shared types for bootstrap, recovery, and smoke testing.

All results are frozen, deterministic, and serializable.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SmokeStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIP = "skip"


class BootstrapResult(BaseModel, frozen=True):
    """Result of bootstrapping a single module."""

    module_name: str
    status: SmokeStatus
    message: str = ""
    duration_ms: float = Field(default=0.0, ge=0.0)

    @property
    def passed(self) -> bool:
        return self.status == SmokeStatus.PASS


class ConfigCheckResult(BaseModel, frozen=True):
    """Result of validating a module's configuration."""

    module_name: str
    status: SmokeStatus
    missing_keys: tuple[str, ...] = ()
    invalid_keys: tuple[str, ...] = ()
    message: str = ""

    @property
    def passed(self) -> bool:
        return self.status == SmokeStatus.PASS


class RecoveryResult(BaseModel, frozen=True):
    """Result of a shutdown/restart cycle."""

    module_name: str
    status: SmokeStatus
    pre_state_valid: bool = False
    post_state_valid: bool = False
    message: str = ""
    duration_ms: float = Field(default=0.0, ge=0.0)

    @property
    def passed(self) -> bool:
        return self.status == SmokeStatus.PASS


class StateSanityResult(BaseModel, frozen=True):
    """Result of post-recovery state validation."""

    module_name: str
    status: SmokeStatus
    checks_passed: int = 0
    checks_failed: int = 0
    anomalies: tuple[str, ...] = ()
    message: str = ""

    @property
    def passed(self) -> bool:
        return self.status == SmokeStatus.PASS


class ModuleSmokeReport(BaseModel, frozen=True):
    """Aggregate smoke results for a single module.

    Spec 7.9: a module that requires recovery MUST have recovery != None.
    A module that requires sanity MUST have state_sanity != None.
    Missing a required phase = automatic FAIL.
    """

    module_name: str
    bootstrap: BootstrapResult | None = None
    config_check: ConfigCheckResult | None = None
    recovery: RecoveryResult | None = None
    state_sanity: StateSanityResult | None = None
    requires_recovery: bool = False
    requires_sanity: bool = False

    @property
    def all_passed(self) -> bool:
        # A module with no results at all cannot pass
        results = [
            r for r in (self.bootstrap, self.config_check, self.recovery, self.state_sanity)
            if r is not None
        ]
        if not results:
            return False
        # If recovery is required but absent, FAIL
        if self.requires_recovery and self.recovery is None:
            return False
        # If sanity is required but absent, FAIL
        if self.requires_sanity and self.state_sanity is None:
            return False
        return all(r.passed for r in results)

    @property
    def has_failure(self) -> bool:
        # Missing required phase counts as failure
        if self.requires_recovery and self.recovery is None:
            return True
        if self.requires_sanity and self.state_sanity is None:
            return True
        results = [
            r for r in (self.bootstrap, self.config_check, self.recovery, self.state_sanity)
            if r is not None
        ]
        return any(not r.passed for r in results)


class SmokeReport(BaseModel, frozen=True):
    """Top-level smoke test report for all modules."""

    module_reports: tuple[ModuleSmokeReport, ...]
    passed: bool

    @property
    def total_modules(self) -> int:
        return len(self.module_reports)

    @property
    def modules_passed(self) -> int:
        return sum(1 for m in self.module_reports if m.all_passed)

    @property
    def modules_failed(self) -> int:
        return sum(1 for m in self.module_reports if m.has_failure)
