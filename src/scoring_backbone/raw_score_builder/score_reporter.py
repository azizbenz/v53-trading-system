"""
Build-5 / raw_score_builder / score_reporter
Audit-able score reporting with anomaly detection.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScorePayload(BaseModel, frozen=True):
    """Complete audit-able score payload."""

    engine_id: str
    pair: str
    raw_score: float
    block_scores: dict[str, float] = Field(default_factory=dict)
    features_used: tuple[str, ...] = ()
    scoring_version: str = ""
    is_anomaly: bool = False
    anomaly_reason: str = ""


class ScoreStats(BaseModel, frozen=True):
    total_scored: int = 0
    anomaly_count: int = 0
    mean_score: float = 0.0
    min_score: float = 0.0
    max_score: float = 0.0


class ScoreReporter:
    """Track and report scoring events."""

    def __init__(self, anomaly_low: float = -10.0, anomaly_high: float = 10.0) -> None:
        self._scores: list[float] = []
        self._anomaly_count: int = 0
        self._anomaly_low = anomaly_low
        self._anomaly_high = anomaly_high

    def evaluate(
        self,
        engine_id: str,
        pair: str,
        raw_score: float,
        block_scores: dict[str, float],
        features_used: tuple[str, ...],
        scoring_version: str,
    ) -> ScorePayload:
        """Build ScorePayload with anomaly detection."""
        normalized_scoring_version = _require_scoring_version(
            scoring_version,
            context="ScoreReporter.evaluate",
        )
        is_anomaly = raw_score < self._anomaly_low or raw_score > self._anomaly_high
        anomaly_reason = ""
        if is_anomaly:
            self._anomaly_count += 1
            anomaly_reason = f"score {raw_score:.4f} out of range [{self._anomaly_low}, {self._anomaly_high}]"

        self._scores.append(raw_score)

        return ScorePayload(
            engine_id=engine_id,
            pair=pair,
            raw_score=raw_score,
            block_scores=block_scores,
            features_used=features_used,
            scoring_version=normalized_scoring_version,
            is_anomaly=is_anomaly,
            anomaly_reason=anomaly_reason,
        )

    def get_stats(self) -> ScoreStats:
        n = len(self._scores)
        if n == 0:
            return ScoreStats()
        return ScoreStats(
            total_scored=n,
            anomaly_count=self._anomaly_count,
            mean_score=sum(self._scores) / n,
            min_score=min(self._scores),
            max_score=max(self._scores),
        )


def _require_scoring_version(scoring_version: str, *, context: str) -> str:
    """Reject blank score versions on the governed scoring rail."""

    normalized = scoring_version.strip()
    if not normalized:
        raise ValueError(f"{context} requires non-empty scoring_version")
    return normalized
