"""Minimal typed ML model risk registry for the bounded enabler layer."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from interface_contracts import MlModelArtifact
from interface_contracts.ml_model_artifact import MlModelWindow


class MlModelRuntimeStage(StrEnum):
    REPLAY = "replay"
    SHADOW = "shadow"
    LIVE = "live"


class MlModelRiskState(StrEnum):
    GREEN = "green"
    PAUSE = "pause"
    PROMOTION_BLOCK = "promotion_block"
    INSUFFICIENT_DATA = "insufficient_data"


class MlModelDriftSnapshot(BaseModel, frozen=True):
    stage: MlModelRuntimeStage
    created_at: datetime
    feature_ks_pvalue: float | None = Field(default=None, ge=0.0, le=1.0)
    shadow_diff_pct: float | None = Field(default=None, ge=0.0)
    live_diff_pct: float | None = Field(default=None, ge=0.0)
    win_rate_delta: float | None = None
    ce_delta: float | None = None


class MlModelRiskSignal(BaseModel, frozen=True):
    state: MlModelRiskState
    pause_signal: bool = False
    promotion_block: bool = False
    reasons: tuple[str, ...] = ()


class MlModelRiskRecord(BaseModel, frozen=True):
    artifact_id: str = Field(..., min_length=1)
    feature_hash: str = Field(..., min_length=1)
    train_window: MlModelWindow
    validation_window: MlModelWindow
    oos_sharpe: float
    drift_snapshots: tuple[MlModelDriftSnapshot, ...] = ()


def evaluate_model_risk_signal(record: MlModelRiskRecord) -> MlModelRiskSignal:
    """Evaluate pause/promotion-block signals from typed drift snapshots."""

    if not record.drift_snapshots:
        return MlModelRiskSignal(
            state=MlModelRiskState.INSUFFICIENT_DATA,
            promotion_block=True,
            reasons=("ML_DRIFT_EVIDENCE_REQUIRED",),
        )
    for snapshot in record.drift_snapshots:
        if snapshot.feature_ks_pvalue is not None and snapshot.feature_ks_pvalue <= 0.05:
            return MlModelRiskSignal(
                state=MlModelRiskState.PROMOTION_BLOCK,
                pause_signal=True,
                promotion_block=True,
                reasons=("ML_FEATURE_DRIFT_BLOCK",),
            )
        if snapshot.shadow_diff_pct is not None and snapshot.shadow_diff_pct >= 0.1:
            return MlModelRiskSignal(
                state=MlModelRiskState.PROMOTION_BLOCK,
                pause_signal=True,
                promotion_block=True,
                reasons=("ML_SHADOW_DIFF_BLOCK",),
            )
        if snapshot.live_diff_pct is not None and snapshot.live_diff_pct >= 0.1:
            return MlModelRiskSignal(
                state=MlModelRiskState.PAUSE,
                pause_signal=True,
                reasons=("ML_LIVE_DIFF_PAUSE",),
            )
        if snapshot.win_rate_delta is not None and snapshot.win_rate_delta <= -0.10:
            return MlModelRiskSignal(
                state=MlModelRiskState.PAUSE,
                pause_signal=True,
                reasons=("ML_WIN_RATE_DRIFT_PAUSE",),
            )
        if snapshot.ce_delta is not None and snapshot.ce_delta <= -0.05:
            return MlModelRiskSignal(
                state=MlModelRiskState.PAUSE,
                pause_signal=True,
                reasons=("ML_CE_DRIFT_PAUSE",),
            )
    return MlModelRiskSignal(state=MlModelRiskState.GREEN)


class MlModelRiskRegistry(BaseModel, frozen=True):
    """Immutable append-only style registry for model risk facts."""

    records: tuple[MlModelRiskRecord, ...] = ()

    def register_artifact(self, artifact: MlModelArtifact) -> "MlModelRiskRegistry":
        record = MlModelRiskRecord(
            artifact_id=artifact.artifact_hash,
            feature_hash=artifact.feature_hash,
            train_window=artifact.train_window,
            validation_window=artifact.validation_window,
            oos_sharpe=artifact.oos_sharpe,
        )
        return MlModelRiskRegistry(records=self.records + (record,))

    def append_drift_snapshot(
        self,
        *,
        artifact_id: str,
        snapshot: MlModelDriftSnapshot,
    ) -> "MlModelRiskRegistry":
        updated: list[MlModelRiskRecord] = []
        matched = False
        for record in self.records:
            if record.artifact_id == artifact_id:
                updated.append(
                    record.model_copy(
                        update={"drift_snapshots": record.drift_snapshots + (snapshot,)}
                    )
                )
                matched = True
            else:
                updated.append(record)
        if not matched:
            raise KeyError(f"Unknown ML model artifact {artifact_id}")
        return MlModelRiskRegistry(records=tuple(updated))

    def latest(self, artifact_id: str) -> MlModelRiskRecord:
        for record in reversed(self.records):
            if record.artifact_id == artifact_id:
                return record
        raise KeyError(f"Unknown ML model artifact {artifact_id}")


__all__ = [
    "MlModelRuntimeStage",
    "MlModelRiskState",
    "MlModelDriftSnapshot",
    "MlModelRiskSignal",
    "MlModelRiskRecord",
    "MlModelRiskRegistry",
    "evaluate_model_risk_signal",
]
