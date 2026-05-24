"""Governed registry for expected-edge feature promotion verdicts."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json


FEATURE_PROMOTION_REGISTRY_FILENAME = "feature_promotion_registry.json"
_logger = logging.getLogger(__name__)


def _now_ms() -> int:
    return int(datetime.now(tz=UTC).timestamp() * 1000.0)


class ExpectedEdgeFeatureVerdict(StrEnum):
    PROMOTED = "PROMOTED"
    NEUTRAL = "NEUTRAL"
    DEMOTED = "DEMOTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class FeaturePromotionEntry(BaseModel, frozen=True):
    schema_version: str = Field(
        default="expected_edge.feature_promotion_entry.v1",
        min_length=1,
    )
    pair: str = Field(..., min_length=1)
    timeframe: str = Field(..., min_length=1)
    feature_name: str = Field(..., min_length=1)
    verdict: ExpectedEdgeFeatureVerdict
    shap_rank: int | None = Field(default=None, ge=1)
    shap_mean_abs: float | None = Field(default=None, ge=0.0)
    ablation_delta_psr: float | None = None
    ablation_delta_sharpe: float | None = None
    ablation_delta_break_even_bps: float | None = None
    talab_quadruple_pass: bool | None = None
    min_btl_required: int = Field(default=0, ge=0)
    min_btl_satisfied: bool = False
    ablation_min_btl_satisfied: bool | None = None
    evidence_artifact_ref: str = ""
    evidence_class: str = Field(default="SHAP_AND_ABLATION_PNL", min_length=1)
    last_evaluated_at_ms: int = Field(default_factory=_now_ms, ge=0)
    detail: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class FeaturePromotionRegistry(BaseModel, frozen=True):
    schema_version: str = Field(
        default="expected_edge.feature_promotion_registry.v1",
        min_length=1,
    )
    generated_at_ms: int = Field(default_factory=_now_ms, ge=0)
    entries: tuple[FeaturePromotionEntry, ...] = ()

    def lookup(
        self,
        *,
        pair: str,
        timeframe: str,
        feature_name: str,
    ) -> FeaturePromotionEntry | None:
        target_pair = pair.strip().upper()
        target_timeframe = timeframe.strip()
        target_feature = feature_name.strip()
        for entry in self.entries:
            if (
                entry.pair.upper() == target_pair
                and entry.timeframe == target_timeframe
                and entry.feature_name == target_feature
            ):
                return entry
        return None

    def entries_for_pair_tf(
        self,
        pair: str,
        timeframe: str,
    ) -> tuple[FeaturePromotionEntry, ...]:
        target_pair = pair.strip().upper()
        target_timeframe = timeframe.strip()
        return tuple(
            entry
            for entry in self.entries
            if entry.pair.upper() == target_pair and entry.timeframe == target_timeframe
        )

    def upsert(self, entry: FeaturePromotionEntry) -> "FeaturePromotionRegistry":
        remaining = [
            existing
            for existing in self.entries
            if not (
                existing.pair.upper() == entry.pair.upper()
                and existing.timeframe == entry.timeframe
                and existing.feature_name == entry.feature_name
            )
        ]
        merged = tuple(
            sorted(
                (*remaining, entry),
                key=lambda item: (
                    item.pair.upper(),
                    item.timeframe,
                    item.feature_name,
                ),
            )
        )
        return self.model_copy(update={"entries": merged, "generated_at_ms": _now_ms()})


def load_feature_promotion_registry(path: Path) -> FeaturePromotionRegistry:
    try:
        if not path.is_file():
            return FeaturePromotionRegistry()
        return FeaturePromotionRegistry.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        _logger.warning(
            "FEATURE_PROMOTION_REGISTRY_LOAD_FAIL_CLOSED path=%s",
            path,
        )
        return FeaturePromotionRegistry()


def save_feature_promotion_registry(
    path: Path,
    registry: FeaturePromotionRegistry,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, registry.model_dump(mode="json"), indent=2)
    return path


__all__ = [
    "FEATURE_PROMOTION_REGISTRY_FILENAME",
    "ExpectedEdgeFeatureVerdict",
    "FeaturePromotionEntry",
    "FeaturePromotionRegistry",
    "load_feature_promotion_registry",
    "save_feature_promotion_registry",
]
