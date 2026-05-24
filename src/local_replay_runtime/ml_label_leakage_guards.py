"""Guards that prevent post-decision labels from becoming ML runtime inputs."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.feature_grounding_registry import (
    LABEL_OR_OUTCOME_FEATURE_NAMES,
    feature_grounding_entry,
)


ML_FEATURE_INPUT_LABEL_LEAKAGE_REPORT_FILENAME = (
    "ml_feature_input_label_leakage_report.json"
)
NO_LABEL_LEAKAGE_DETECTED = "NO_LABEL_LEAKAGE_DETECTED"
LABEL_FEATURE_AS_INPUT_BLOCKED = "LABEL_FEATURE_AS_INPUT_BLOCKED"
ML_POST_DECISION_FEATURE_AS_INPUT_BLOCKED = "ML_POST_DECISION_FEATURE_AS_INPUT_BLOCKED"
ML_LABEL_FEATURE_AS_RUNTIME_INPUT_BLOCKED = "ML_LABEL_FEATURE_AS_RUNTIME_INPUT_BLOCKED"


class MlFeatureInputLabelLeakageReport(BaseModel, frozen=True):
    schema_version: str = "ml_feature_input_label_leakage.report.v1"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    status: str = NO_LABEL_LEAKAGE_DETECTED
    selected_feature_count: int = 0
    blocked_feature_names: tuple[str, ...] = ()
    blocker_reasons: tuple[str, ...] = ()


def build_ml_feature_input_label_leakage_report(
    selected_feature_names: tuple[str, ...],
) -> MlFeatureInputLabelLeakageReport:
    blocked: list[str] = []
    for feature_name in tuple(dict.fromkeys(name.strip() for name in selected_feature_names if name.strip())):
        entry = feature_grounding_entry(feature_name)
        if feature_name in LABEL_OR_OUTCOME_FEATURE_NAMES or (
            entry is not None and entry.is_label_or_outcome
        ):
            blocked.append(feature_name)
    reasons = tuple(
        f"{name}:{ML_LABEL_FEATURE_AS_RUNTIME_INPUT_BLOCKED}" for name in blocked
    )
    return MlFeatureInputLabelLeakageReport(
        status=LABEL_FEATURE_AS_INPUT_BLOCKED if blocked else NO_LABEL_LEAKAGE_DETECTED,
        selected_feature_count=len(
            tuple(name for name in selected_feature_names if name.strip())
        ),
        blocked_feature_names=tuple(blocked),
        blocker_reasons=reasons,
    )


def write_ml_feature_input_label_leakage_report(
    path: Path,
    report: MlFeatureInputLabelLeakageReport,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, report.model_dump(mode="json"), indent=2)
    return path


__all__ = [
    "LABEL_FEATURE_AS_INPUT_BLOCKED",
    "ML_FEATURE_INPUT_LABEL_LEAKAGE_REPORT_FILENAME",
    "ML_LABEL_FEATURE_AS_RUNTIME_INPUT_BLOCKED",
    "ML_POST_DECISION_FEATURE_AS_INPUT_BLOCKED",
    "MlFeatureInputLabelLeakageReport",
    "NO_LABEL_LEAKAGE_DETECTED",
    "build_ml_feature_input_label_leakage_report",
    "write_ml_feature_input_label_leakage_report",
]
