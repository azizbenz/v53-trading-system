"""
V5.3 — INTERFACE_CONTRACTS
===========================
Module Build-1 / Étape 1 — P0 absolue

Mission : Fournir le langage officiel de communication entre modules.
- Types métier stables et versionnés
- Structures d'événements, signaux, décisions, ordres, métriques
- Erreurs métier standardisées
- Invariants contractuels testables

Ce module NE DOIT PAS :
- Contenir de logique métier
- Importer des implémentations concrètes
- Gérer le runtime
- Effectuer des calculs d'edge
"""

from __future__ import annotations

__contract_version__ = "1.0.0"

from .domain_types import *
from .feature_lock_contracts import *
from .artifact_contracts import *
from .binance_contracts import *
from .market_event_contracts import *
from .decision_contracts import *
from .forecast_contracts import *
from .strategy_identity import *
from .refusal_records import *
from .meta_contracts import *
from .numeric_contracts import *
from .error_contracts import *
from .closed_episode_contracts import *
from .engine_coordination_contracts import *
from .venue_error_contracts import *
from .operator_contracts import *
from .build14_contracts import *
from .engine_validation_contracts import *
from .shadow_vps_service_contracts import *
from .dashboard_command_contracts import *
from .vps_recovery_contracts import *
from .pair_catalog import *
from .ml_model_artifact import *
from .ml_backtest_training_contracts import *
from .ml_model_transport_contracts import *
from .regime_detector_artifact import *
from .regime_detector_label_contracts import *
from .regime_detector_shadow_audit_contracts import *

__all__ = [
    # domain_types — Enums
    "EngineId", "RegimeId", "ProfileId", "RuntimeMode", "StrategyClassification",
    "PromotionState", "ReviewState", "Tier", "Timeframe", "Side",
    "ModuleLayer", "ModuleStatus", "SignalType", "PairHealthLevel",
    "ExecutionStatus", "RiskVerdict", "DeploymentState",
    # feature_lock_contracts
    "CANONICAL_FEATURE_SET_VERSION", "CANONICAL_TRANSFORM_SET_VERSION",
    "PhysicsFeatureFamily", "DeltaProxyVariant", "TransformWhitelistId",
    "PHYSICS_FEATURE_ALIASES", "FeatureDictionaryEntry",
    "FeatureLineageRecord", "FeatureLineageLock", "TransformWhitelistLock",
    "CANONICAL_PHYSICS_FEATURE_DICTIONARY", "CANONICAL_TRANSFORM_WHITELIST",
    "canonical_feature_ids", "canonical_transform_ids",
    "validate_feature_lineage_lock", "validate_transform_whitelist_lock",
    # artifact_contracts
    "ArtifactActivationStage", "ArtifactHealthState", "ArtifactLogicFormat",
    "HookId", "ArtifactActionKind", "ActionUnit",
    "ArtifactConflictResolutionMode", "ScoreConflictAggregationMode",
    "SizeReduceConflictMode", "RankAdjustConflictMode",
    "CompiledRegistryAtomicityMode", "CompiledRegistryConcurrencyModel",
    "ArtifactRuntimeFailureMode", "ArtifactRuntimeFailureStage",
    "DistilledRuleLogicalOp", "DistilledRuleOperator", "ArtifactClass",
    "ArtifactCompatibilityStatus", "ArtifactTrustKeyStatus", "ArtifactPolicyErrorCode",
    "ArtifactCompatibilityEntry", "ArtifactSignatureEnvelope", "ArtifactTrustStoreEntry",
    "ArtifactConflictPolicy", "CompiledArtifactRegistryPolicy",
    "DistilledRuleCondition", "DistilledRuleAction", "DistilledRule",
    "ArtifactProofSummary", "ArtifactProofFloorPolicy", "ArtifactRuntimeErrorPolicy",
    "ArtifactLifecyclePolicy", "ArtifactTtlStatus", "ArtifactDriftStatus",
    "ArtifactRuntimeGovernanceEvaluation", "ArtifactExportBundle",
    "HOOK_MODULE_BY_ID", "RUNTIME_OPEN_HOOK_IDS", "NON_ACTIVE_ARTIFACT_HEALTH_STATES",
    "CANONICAL_ARTIFACT_CONFLICT_POLICY", "CANONICAL_COMPILED_ARTIFACT_REGISTRY_POLICY",
    "CANONICAL_ARTIFACT_PROOF_FLOOR_POLICY", "CANONICAL_ARTIFACT_RUNTIME_ERROR_POLICY",
    "is_runtime_open_hook_id",
    "validate_artifact_proof_summary",
    "evaluate_artifact_runtime_governance",
    # binance_contracts
    "BinanceAccountSnapshot", "BinanceAssetBalance", "BinanceCredentials",
    "BinanceExchangeInfo", "BinanceRateLimit", "BinanceServerTime",
    "BinanceSymbolInfo", "BinanceTimeSyncResult",
    # domain_types — Pairs
    "LIGHT_PAIRS", "COMPLETE_ADDITIONAL_PAIRS", "ALL_PAIRS",
    "ENGINE_PAIR_MAP", "PAIR_TIER_MAP", "V53_MULTIPAIR_7",
    # domain_types — NewTypes & base
    "PairId", "OrderId", "TradeId", "RunId", "TimestampedModel",
    # market_event_contracts
    "KlineEvent", "TradeEvent", "DepthLevel", "DepthEvent",
    "SnapshotEvent", "HeartbeatEvent",
    # decision_contracts
    "ScorePayload", "SignalCandidate", "EdgeEstimate",
    "ExecutionIntent", "RiskDecision", "PortfolioAction", "PortfolioDecision",
    "PairHealthStatus", "BlockReason",
    # forecast_contracts
    "ForecastTargetClass", "ForecastHorizonClass", "BetStructure",
    "ConditioningFamily", "ConditioningRecord", "ForecastSignalCandidate",
    # strategy_identity
    "StrategyIdentity",
    # refusal_records
    "RefusalCategory", "RefusalRecord",
    # meta_contracts
    "DTROutcome", "DTRRecord", "CostRecord", "PenaltyDetail", "AlertSeverity",
    "AlertCategory", "AlertRecord",
    # numeric_contracts
    "EXECUTION_DECIMAL_CONTEXT_PRECISION", "EXECUTION_DECIMAL_ROUNDING",
    "execution_decimal", "decimal_to_canonical_str", "multiply_exact",
    "divide_exact_or_zero", "sum_exact", "quantize_down_to_step",
    "quantize_up_to_step", "decimal_to_float64_abs_loss", "decimal_to_float64",
    # error_contracts
    "V53BaseError", "ContractViolationError", "DependencyViolationError",
    "DataStaleError", "RiskBudgetExceededError", "PairSuspendedError",
    "EngineNotAllowedError", "InvalidProfileActivationError",
    "ReconciliationError", "BootstrapError",
    # closed_episode_contracts
    "EpisodeCloseReason", "EpisodeRef",
    # engine_coordination_contracts
    "EngineCoordinationAction", "EngineCoordinationInput",
    "EngineCoordinationOutcome", "EngineCoordinationThresholds",
    # venue_error_contracts
    "VenueRateLimitExceededError", "BinanceApiRateLimitExceededError",
    # operator_contracts
    "OperatorSafingAction", "OperatorSafingRequest",
    # build14_contracts
    "Build14InfluenceMode", "Build14InfluenceAction", "Build14Severity",
    "Build14SignalFamily", "Build14HardState", "Build14EnablerContract",
    "Build14ObservationInput", "Build14EnablerSnapshot",
    "Build14InfluenceSignal", "Build14InfluenceReport",
    # engine_validation_contracts
    "EngineCVoidValidationInput", "EngineCVoidValidationOutcome",
    "EngineDReentryValidationInput", "EngineDReentryValidationOutcome",
    # shadow_vps_service_contracts
    "ShadowVpsServiceStatus", "ShadowVpsServiceState",
    "ShadowVpsRuntimeEvidenceBundle", "ShadowVpsCampaignSummary",
    "ShadowVpsServiceEvent", "ShadowVpsExecutionRuntimeBootstrapSummary",
    # dashboard_command_contracts
    "DashboardArtifactKind", "DashboardSecretKind", "DashboardSecretEnvironment",
    "BinanceCredentialValidationStatus",
    "DashboardGovernedCommandKind",
    "DashboardGovernedCommandStatus", "DashboardCommandQueueStatus",
    "DashboardArtifactTransferManifest", "DashboardSecretTransferManifest",
    "BinanceCredentialProfileRef", "BinanceCredentialInventoryEntry",
    "BinanceCredentialInventorySnapshot", "binance_credential_entry_from_manifest",
    "DashboardGovernedCommandRequest",
    "DashboardGovernedCommandAck", "DashboardGovernedCommandResult",
    "DashboardCommandQueueSnapshot",
    # vps_recovery_contracts
    "VpsRecoveryCheckStatus", "VpsWarmupState", "VpsRecoveryCheck",
    "VpsRecoveryReadinessReport", "VpsWarmupRunSummary",
    # pair_catalog
    "PairEntry", "PairCatalog", "V53_PAIR_CATALOG",
    # ml_model_artifact
    "MlModelFamily", "MlModelWindow", "MlModelDriftBaseline", "MlModelArtifact",
    # regime_detector_artifact
    "RegimeDetectorModelFamily", "RegimeDetectorFeatureSetVersion", "RegimeDetectorOutputSemantics",
    "RegimeDurationBucket", "RegimeDetectorWindow", "RegimeDetectorArtifact",
    "RegimeDetectorArtifactSummary",
    # regime_detector_shadow_audit_contracts
    "RegimeDetectorShadowAuditSchemaMatchStatus", "RegimeDetectorShadowAuditMetricSummary",
    "RegimeDetectorShadowAuditReasonCodeCount", "RegimeDetectorShadowAuditStatusCount",
    "RegimeDetectorShadowAuditDurationCounts", "RegimeDetectorShadowAuditSample",
    "RegimeDetectorShadowAuditBundle", "RegimeDetectorShadowAuditFindingSeverity",
    "RegimeDetectorShadowAuditFindingCode", "RegimeDetectorShadowAuditFinding",
    "RegimeDetectorShadowAuditDiagnosisStatus", "RegimeDetectorShadowAuditDiagnosis",
    # regime_detector_label_contracts
    "REGIME_DETECTOR_LABEL_POLICY", "DEFAULT_REGIME_DETECTOR_WINDOW_SECONDS",
    "MAX_REGIME_DETECTOR_WINDOW_SECONDS", "DEFAULT_REGIME_DETECTOR_FUTURE_STEPS",
    "DEFAULT_REGIME_DETECTOR_TOP_N", "MAX_REGIME_DETECTOR_TOP_N",
    "RegimeToxicityBucket", "RegimeDetectorLabelConfig",
    "RegimeDetectorDatasetSample", "RegimeDetectorTrainingDataset",
    # ml_backtest_training_contracts
    "ML_BACKTEST_TARGET_POLICY", "ML_BACKTEST_REALIZED_TARGET_POLICY", "ML_BACKTEST_ROUTE_FEATURE_NAMES",
    "MlBacktestRouteFeatures", "MlBacktestOutcomeContext",
    "MlBacktestTrainingSample", "MlBacktestTrainingDataset",
    "MlModelSourceArtifactSummary",
]
