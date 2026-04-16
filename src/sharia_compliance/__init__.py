"""Bounded halal compliance layer for P0-2."""

from __future__ import annotations

from sharia_compliance.account_features_audit import (
    AccountFeaturesAuditConfig,
    audit_account_features,
    resolve_account_features_audit_interval_s,
)
from sharia_compliance.asset_blacklist import is_blacklisted_asset_pair, is_blacklisted_pair, split_pair_assets
from sharia_compliance.asset_whitelist import get_base_asset_policy, is_whitelisted_pair
from sharia_compliance.contracts import (
    AaoifiPairScreeningAuditFinding,
    AaoifiPairScreeningAuditReport,
    AaoifiPairScreeningRegistry,
    AaoifiPairScreeningResult,
    AaoifiPairScreeningSnapshot,
    AccountFeatureAuditFinding,
    AccountFeaturesAuditReport,
    AssetPolicy,
    PurificationEstimate,
    PurificationSourceType,
    ShariaAuditEvent,
    ShariaPermit,
    ShariaPolicy,
    ShariaRejection,
    ShariaTradeRequest,
    StablecoinPolicy,
)
from sharia_compliance.pair_screening import (
    AAOIFI_MAX_CASH_AND_INTEREST_BEARING_TO_TOTAL_ASSETS,
    AAOIFI_MAX_DEBT_TO_TOTAL_ASSETS,
    AAOIFI_MAX_INTEREST_INCOME_TO_TOTAL_REVENUE,
    evaluate_pair_screening,
    load_pair_screening_snapshot,
)
from sharia_compliance.pair_screening_audit import audit_traded_pairs_against_screening
from sharia_compliance.pair_screening_registry import (
    FilePairScreeningProvider,
    load_pair_screening_registry,
)
from sharia_compliance.policy_audit_logger import PolicyAuditLogger
from sharia_compliance.policy_loader import load_sharia_policy
from sharia_compliance.purification_calculator import (
    StablecoinPurificationConfig,
    calculate_purification,
    estimate_stablecoin_purification,
)
from sharia_compliance.sharia_alerts import (
    build_account_feature_audit_alerts,
    build_pair_screening_audit_alerts,
)
from sharia_compliance.sharia_runtime import ShariaRuntime
from sharia_compliance.stablecoin_policy import is_quote_asset_permitted, resolve_quote_asset
from sharia_compliance.trade_type_guard import authorize_trade_type

__all__ = [
    "AAOIFI_MAX_CASH_AND_INTEREST_BEARING_TO_TOTAL_ASSETS",
    "AAOIFI_MAX_DEBT_TO_TOTAL_ASSETS",
    "AAOIFI_MAX_INTEREST_INCOME_TO_TOTAL_REVENUE",
    "AaoifiPairScreeningAuditFinding",
    "AaoifiPairScreeningAuditReport",
    "AaoifiPairScreeningRegistry",
    "AaoifiPairScreeningResult",
    "AaoifiPairScreeningSnapshot",
    "AccountFeatureAuditFinding",
    "AccountFeaturesAuditConfig",
    "AccountFeaturesAuditReport",
    "AssetPolicy",
    "FilePairScreeningProvider",
    "PolicyAuditLogger",
    "PurificationEstimate",
    "PurificationSourceType",
    "ShariaAuditEvent",
    "ShariaPermit",
    "ShariaPolicy",
    "ShariaRejection",
    "ShariaRuntime",
    "ShariaTradeRequest",
    "StablecoinPurificationConfig",
    "StablecoinPolicy",
    "audit_traded_pairs_against_screening",
    "audit_account_features",
    "authorize_trade_type",
    "build_account_feature_audit_alerts",
    "build_pair_screening_audit_alerts",
    "calculate_purification",
    "evaluate_pair_screening",
    "estimate_stablecoin_purification",
    "get_base_asset_policy",
    "is_blacklisted_asset_pair",
    "is_blacklisted_pair",
    "is_quote_asset_permitted",
    "is_whitelisted_pair",
    "load_pair_screening_registry",
    "load_sharia_policy",
    "load_pair_screening_snapshot",
    "resolve_account_features_audit_interval_s",
    "resolve_quote_asset",
    "split_pair_assets",
]
