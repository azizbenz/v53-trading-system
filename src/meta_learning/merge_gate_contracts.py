"""Typed contracts for explicit Build-9X merge gates."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class Build9XMergeGateName(StrEnum):
    """Named merge gates frozen by the active Build-9X V2 spec."""

    NO_LIVE_MUTATION_PATH = "NO_LIVE_MUTATION_PATH"
    END_TO_END_ID_CORRELATION = "END_TO_END_ID_CORRELATION"
    STRUCTURED_LEARNING_LOGS_PRESENT = "STRUCTURED_LEARNING_LOGS_PRESENT"
    LEARNING_BACKPRESSURE_HANDLED = "LEARNING_BACKPRESSURE_HANDLED"
    RESOURCE_BUDGETS_RESPECTED = "RESOURCE_BUDGETS_RESPECTED"
    STATISTICAL_GOVERNANCE_PRESENT = "STATISTICAL_GOVERNANCE_PRESENT"


class Build9XMergeGateResult(BaseModel, frozen=True):
    """Single explicit pass/fail gate result."""

    gate_name: Build9XMergeGateName
    passed: bool
    summary: str = Field(..., min_length=1)
    blocking_reasons: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    structured_log_key: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_summary(self) -> "Build9XMergeGateResult":
        if self.passed and self.blocking_reasons:
            raise ValueError("Passing merge-gate results must not keep blocking_reasons")
        return self


class Build9XMergeGateReport(BaseModel, frozen=True):
    """Grouped Build-9X merge-gate report."""

    correlation_id: str = Field(..., min_length=1)
    all_passed: bool
    gates: tuple[Build9XMergeGateResult, ...]
    state_dir: str = ""

    @model_validator(mode="after")
    def validate_report(self) -> "Build9XMergeGateReport":
        if len({gate.gate_name for gate in self.gates}) != len(self.gates):
            raise ValueError("Build-9X merge-gate reports must not duplicate gate names")
        if self.all_passed != all(gate.passed for gate in self.gates):
            raise ValueError("all_passed must reflect the conjunction of gate results")
        return self

    def gate(self, gate_name: Build9XMergeGateName) -> Build9XMergeGateResult:
        for gate in self.gates:
            if gate.gate_name == gate_name:
                return gate
        raise KeyError(f"Unknown Build-9X merge gate {gate_name}")


__all__ = [
    "Build9XMergeGateName",
    "Build9XMergeGateResult",
    "Build9XMergeGateReport",
]
