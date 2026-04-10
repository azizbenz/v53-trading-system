"""
V5.3 - FEATURE LOCK CONTRACTS
=============================
Shared-core canonical vocabulary for the Build-L0 feature dictionary,
transform whitelist, and lineage lock.
"""

from __future__ import annotations

from enum import Enum, unique

from pydantic import BaseModel, Field, model_validator


CANONICAL_FEATURE_SET_VERSION = "1.0.0"
CANONICAL_TRANSFORM_SET_VERSION = "1.0.0"


@unique
class PhysicsFeatureFamily(str, Enum):
    """Canonical physics feature families unified by the P2 math patch."""

    DELTA_PROXY = "delta_proxy"
    CUMULATIVE_DELTA = "cumulative_delta"
    ORDER_FLOW_IMBALANCE = "order_flow_imbalance"
    BOOK_IMBALANCE = "book_imbalance"
    MICROPRICE_DEVIATION = "microprice_deviation"
    SPREAD_REGIME = "spread_regime"
    SLIPPAGE_FRICTION_PROXY = "slippage_friction_proxy"
    VOLUME_PROFILE = "volume_profile"
    POC_VAH_VAL = "poc_vah_val"
    HVN_LVN = "hvn_lvn"
    VOID_SCORE = "void_score"
    SWEEP_SCORE = "sweep_score"
    ABSORPTION_SCORE = "absorption_score"
    FALSE_BREAKOUT_SCORE = "false_breakout_score"
    TOXICITY_FRAGILITY_SURVIVABILITY = "toxcity_fragility_survivability"
    BOOK_RESILIENCY = "book_resiliency"
    REFILL_SPEED = "refill_speed"
    REGIME_HURST_CONTEXT_ENRICHMENT = "regime_hurst_context_enrichment"
    PORTFOLIO_OVERLAP_CROWDING_CLUSTER = "portfolio_overlap_crowding_cluster"


@unique
class DeltaProxyVariant(str, Enum):
    """Allowed delta proxy variants after the P2 patch."""

    SOFT = "delta_proxy_soft"
    SIGN = "delta_proxy_sign"


@unique
class TransformWhitelistId(str, Enum):
    """Minimal shared transform whitelist already canonized in code."""

    CLIP01 = "clip01"
    ZPLUS = "zplus"
    CAPRATIO = "capratio"
    DELTA_PROXY_SOFT = "delta_proxy_soft"
    DELTA_PROXY_SIGN = "delta_proxy_sign"
    DELTA_CONFIRMATION_V1 = "delta_confirmation_v1"
    PARTICIPATION_RATIO = "participation_ratio"
    VOID_SCORE_DISCRETE = "void_score_discrete"
    SWEEP_SCORE_V1 = "sweep_score_v1"
    FRAGILITY_SCORE_V1 = "fragility_score_v1"
    TOXICITY_SCORE_V1 = "toxicity_score_v1"
    EXECUTION_SURVIVABILITY_SCORE_V1 = "execution_survivability_score_v1"
    MICRO_FRICTION_SCORE_V1 = "micro_friction_score_v1"


PHYSICS_FEATURE_ALIASES: dict[str, PhysicsFeatureFamily] = {
    "OFI": PhysicsFeatureFamily.ORDER_FLOW_IMBALANCE,
    "OBI": PhysicsFeatureFamily.BOOK_IMBALANCE,
    "delta proxy": PhysicsFeatureFamily.DELTA_PROXY,
    "cumulative delta": PhysicsFeatureFamily.CUMULATIVE_DELTA,
    "book resiliency": PhysicsFeatureFamily.BOOK_RESILIENCY,
    "execution survivability score": PhysicsFeatureFamily.TOXICITY_FRAGILITY_SURVIVABILITY,
}


class FeatureDictionaryEntry(BaseModel, frozen=True):
    """Concrete dictionary entry for canonical shared-core features."""

    feature_id: str = Field(..., min_length=1)
    family: PhysicsFeatureFamily
    equation_id: str = Field(..., min_length=1)
    default_transform_ids: tuple[TransformWhitelistId, ...] = ()
    lineage_required: bool = True
    description: str = ""

    @model_validator(mode="after")
    def validate_defaults(self) -> "FeatureDictionaryEntry":
        if len(set(self.default_transform_ids)) != len(self.default_transform_ids):
            raise ValueError("FeatureDictionaryEntry default_transform_ids must stay unique")
        return self


class FeatureLineageRecord(BaseModel, frozen=True):
    """Audit-ready lineage record for one derived or exported feature."""

    feature_id: str = Field(..., min_length=1)
    family: PhysicsFeatureFamily
    source_inputs: tuple[str, ...] = ()
    upstream_feature_ids: tuple[str, ...] = ()
    transform_ids: tuple[TransformWhitelistId, ...] = ()
    equation_id: str = ""
    cap_refs: tuple[str, ...] = ()
    weight_refs: tuple[str, ...] = ()
    feature_set_version: str = Field(
        default=CANONICAL_FEATURE_SET_VERSION,
        min_length=1,
    )
    transform_set_version: str = Field(
        default=CANONICAL_TRANSFORM_SET_VERSION,
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_lineage(self) -> "FeatureLineageRecord":
        if not self.source_inputs and not self.upstream_feature_ids:
            raise ValueError(
                "FeatureLineageRecord requires source_inputs or upstream_feature_ids"
            )
        if not self.transform_ids:
            raise ValueError("FeatureLineageRecord requires at least one transform_id")
        if len(set(self.source_inputs)) != len(self.source_inputs):
            raise ValueError("FeatureLineageRecord source_inputs must stay unique")
        if len(set(self.upstream_feature_ids)) != len(self.upstream_feature_ids):
            raise ValueError("FeatureLineageRecord upstream_feature_ids must stay unique")
        if len(set(self.transform_ids)) != len(self.transform_ids):
            raise ValueError("FeatureLineageRecord transform_ids must stay unique")
        canonical_entry = CANONICAL_PHYSICS_FEATURE_DICTIONARY.get(self.feature_id)
        if canonical_entry is not None and self.family != canonical_entry.family:
            raise ValueError(
                "FeatureLineageRecord family must match the canonical feature dictionary"
            )
        return self


class FeatureLineageLock(BaseModel, frozen=True):
    """Canonical lock tying feature versions to explicit lineage records."""

    feature_set_version: str = Field(
        default=CANONICAL_FEATURE_SET_VERSION,
        min_length=1,
    )
    transform_set_version: str = Field(
        default=CANONICAL_TRANSFORM_SET_VERSION,
        min_length=1,
    )
    records: tuple[FeatureLineageRecord, ...] = ()

    @model_validator(mode="after")
    def validate_lock(self) -> "FeatureLineageLock":
        feature_ids = tuple(record.feature_id for record in self.records)
        if len(set(feature_ids)) != len(feature_ids):
            raise ValueError("FeatureLineageLock records must stay unique per feature_id")
        for record in self.records:
            if record.feature_set_version != self.feature_set_version:
                raise ValueError(
                    "FeatureLineageLock feature_set_version must match record feature_set_version"
                )
            if record.transform_set_version != self.transform_set_version:
                raise ValueError(
                    "FeatureLineageLock transform_set_version must match record transform_set_version"
                )
        return self


class TransformWhitelistLock(BaseModel, frozen=True):
    """Canonical lock tying a transform-set version to explicit allowed transforms."""

    transform_set_version: str = Field(
        default=CANONICAL_TRANSFORM_SET_VERSION,
        min_length=1,
    )
    allowed_transform_ids: tuple[TransformWhitelistId, ...] = ()

    @model_validator(mode="after")
    def validate_lock(self) -> "TransformWhitelistLock":
        if not self.allowed_transform_ids:
            raise ValueError("TransformWhitelistLock requires at least one allowed_transform_id")
        if len(set(self.allowed_transform_ids)) != len(self.allowed_transform_ids):
            raise ValueError(
                "TransformWhitelistLock allowed_transform_ids must stay unique"
            )
        return self


CANONICAL_PHYSICS_FEATURE_DICTIONARY: dict[str, FeatureDictionaryEntry] = {
    "delta_proxy_soft_1m": FeatureDictionaryEntry(
        feature_id="delta_proxy_soft_1m",
        family=PhysicsFeatureFamily.DELTA_PROXY,
        equation_id="P2.3.delta_proxy_soft",
        default_transform_ids=(TransformWhitelistId.DELTA_PROXY_SOFT,),
        description="Default canonical soft delta proxy",
    ),
    "delta_proxy_sign_1m": FeatureDictionaryEntry(
        feature_id="delta_proxy_sign_1m",
        family=PhysicsFeatureFamily.DELTA_PROXY,
        equation_id="P2.3.delta_proxy_sign",
        default_transform_ids=(TransformWhitelistId.DELTA_PROXY_SIGN,),
        description="Documented fallback delta proxy",
    ),
    "delta_confirmation": FeatureDictionaryEntry(
        feature_id="delta_confirmation",
        family=PhysicsFeatureFamily.DELTA_PROXY,
        equation_id="P2.3.delta_confirmation_v1",
        default_transform_ids=(TransformWhitelistId.DELTA_CONFIRMATION_V1,),
        description="Canonical normalized delta confirmation derived from a delta proxy",
    ),
    "participation_ratio_1m": FeatureDictionaryEntry(
        feature_id="participation_ratio_1m",
        family=PhysicsFeatureFamily.SLIPPAGE_FRICTION_PROXY,
        equation_id="P2.2.4.participation",
        default_transform_ids=(TransformWhitelistId.PARTICIPATION_RATIO,),
        description="Participation_t helper feature attached to slippage/fraction proxy",
    ),
    "void_score_discrete": FeatureDictionaryEntry(
        feature_id="void_score_discrete",
        family=PhysicsFeatureFamily.VOID_SCORE,
        equation_id="P2.2.3.void_score",
        default_transform_ids=(TransformWhitelistId.VOID_SCORE_DISCRETE,),
        description="Discrete canonical void score",
    ),
    "sweep_score": FeatureDictionaryEntry(
        feature_id="sweep_score",
        family=PhysicsFeatureFamily.SWEEP_SCORE,
        equation_id="P2.5.sweep_score",
        default_transform_ids=(TransformWhitelistId.SWEEP_SCORE_V1,),
        description="Canonical bounded sweep score",
    ),
    "fragility_score": FeatureDictionaryEntry(
        feature_id="fragility_score",
        family=PhysicsFeatureFamily.TOXICITY_FRAGILITY_SURVIVABILITY,
        equation_id="P2.6.fragility",
        default_transform_ids=(TransformWhitelistId.FRAGILITY_SCORE_V1,),
        description="Canonical bounded fragility score",
    ),
    "toxicity_score": FeatureDictionaryEntry(
        feature_id="toxicity_score",
        family=PhysicsFeatureFamily.TOXICITY_FRAGILITY_SURVIVABILITY,
        equation_id="P2.7.toxicity",
        default_transform_ids=(TransformWhitelistId.TOXICITY_SCORE_V1,),
        description="Canonical bounded toxicity score",
    ),
    "execution_survivability_score": FeatureDictionaryEntry(
        feature_id="execution_survivability_score",
        family=PhysicsFeatureFamily.TOXICITY_FRAGILITY_SURVIVABILITY,
        equation_id="P2.8.execution_survivability",
        default_transform_ids=(TransformWhitelistId.EXECUTION_SURVIVABILITY_SCORE_V1,),
        description="Canonical bounded execution survivability score",
    ),
    "micro_friction_score": FeatureDictionaryEntry(
        feature_id="micro_friction_score",
        family=PhysicsFeatureFamily.SLIPPAGE_FRICTION_PROXY,
        equation_id="P2.9.micro_friction",
        default_transform_ids=(TransformWhitelistId.MICRO_FRICTION_SCORE_V1,),
        description="Canonical bounded micro-friction score",
    ),
}

CANONICAL_TRANSFORM_WHITELIST: frozenset[TransformWhitelistId] = frozenset(
    TransformWhitelistId
)


def canonical_feature_ids() -> tuple[str, ...]:
    """Return the current concrete canonical feature ids in stable order."""

    return tuple(CANONICAL_PHYSICS_FEATURE_DICTIONARY.keys())


def canonical_transform_ids() -> tuple[TransformWhitelistId, ...]:
    """Return the current canonical transform ids in stable order."""

    return tuple(sorted(CANONICAL_TRANSFORM_WHITELIST, key=lambda item: item.value))


def validate_feature_lineage_lock(
    feature_ids: tuple[str, ...],
    lineage_lock: FeatureLineageLock | None,
) -> tuple[str, ...]:
    """Return deterministic lineage-lock rejection reasons for a feature set."""

    if not feature_ids:
        return ()
    if lineage_lock is None:
        return ("feature lineage lock is required",)

    reasons: list[str] = []
    seen = {record.feature_id for record in lineage_lock.records}
    for feature_id in feature_ids:
        if feature_id not in seen:
            reasons.append(f"missing lineage for feature_id={feature_id}")
    return tuple(reasons)


def validate_transform_whitelist_lock(
    transform_ids: tuple[TransformWhitelistId, ...],
    whitelist_lock: TransformWhitelistLock | None,
) -> tuple[str, ...]:
    """Return deterministic transform-whitelist rejection reasons."""

    if not transform_ids:
        return ()
    if whitelist_lock is None:
        return ("transform whitelist lock is required",)

    reasons: list[str] = []
    seen = set(whitelist_lock.allowed_transform_ids)
    for transform_id in transform_ids:
        if transform_id not in seen:
            reasons.append(f"missing whitelist for transform_id={transform_id.value}")
    return tuple(reasons)


__all__ = [
    "CANONICAL_FEATURE_SET_VERSION",
    "CANONICAL_TRANSFORM_SET_VERSION",
    "PhysicsFeatureFamily",
    "DeltaProxyVariant",
    "TransformWhitelistId",
    "PHYSICS_FEATURE_ALIASES",
    "FeatureDictionaryEntry",
    "FeatureLineageRecord",
    "FeatureLineageLock",
    "TransformWhitelistLock",
    "CANONICAL_PHYSICS_FEATURE_DICTIONARY",
    "CANONICAL_TRANSFORM_WHITELIST",
    "canonical_feature_ids",
    "canonical_transform_ids",
    "validate_feature_lineage_lock",
    "validate_transform_whitelist_lock",
]
