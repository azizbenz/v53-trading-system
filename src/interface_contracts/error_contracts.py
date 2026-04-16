"""
V5.3 — ERROR_CONTRACTS
Version contrat : 1.0.0
Erreurs métier standardisées.
"""
from __future__ import annotations


ErrorDetails = dict[str, object]


class V53BaseError(Exception):
    """Base de toutes les erreurs métier V5.3."""

    def __init__(
        self,
        message: str,
        code: str,
        module: str,
        pair: str | None = None,
        details: ErrorDetails | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.module = module
        self.pair = pair
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, object]:
        return {
            "error_type": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
            "module": self.module,
            "pair": self.pair,
            "details": self.details,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code!r}, pair={self.pair!r})"


class DataStaleError(V53BaseError):
    def __init__(
        self,
        pair: str,
        stale_ms: int,
        threshold_ms: int,
        module: str = "data",
        details: ErrorDetails | None = None,
    ) -> None:
        super().__init__(
            message=f"Données stale pour {pair}: âge={stale_ms}ms > seuil={threshold_ms}ms",
            code="ERR_DATA_STALE",
            module=module,
            pair=pair,
            details={
                "stale_ms": stale_ms,
                "threshold_ms": threshold_ms,
                **(details or {}),
            },
        )


class PairSuspendedError(V53BaseError):
    def __init__(
        self,
        pair: str,
        reason: str,
        module: str = "data",
        details: ErrorDetails | None = None,
    ) -> None:
        super().__init__(
            message=f"Paire {pair} suspendue: {reason}",
            code="ERR_PAIR_SUSPENDED",
            module=module,
            pair=pair,
            details={"suspension_reason": reason, **(details or {})},
        )


class DependencyViolationError(V53BaseError):
    def __init__(
        self,
        source_module: str,
        target_module: str,
        violation_type: str = "unauthorized_import",
        details: ErrorDetails | None = None,
    ) -> None:
        super().__init__(
            message=f"Dépendance interdite: {source_module} -> {target_module} ({violation_type})",
            code="ERR_DEPENDENCY_VIOLATION",
            module=source_module,
            pair=None,
            details={
                "source_module": source_module,
                "target_module": target_module,
                "violation_type": violation_type,
                **(details or {}),
            },
        )


class ContractViolationError(V53BaseError):
    def __init__(
        self,
        contract_name: str,
        field: str,
        expected: str,
        actual: str,
        module: str = "contracts",
        details: ErrorDetails | None = None,
    ) -> None:
        super().__init__(
            message=f"Contrat \'{contract_name}\' violé: champ \'{field}\' attendu={expected}, reçu={actual}",
            code="ERR_CONTRACT_VIOLATION",
            module=module,
            pair=None,
            details={
                "contract_name": contract_name,
                "field": field,
                "expected": expected,
                "actual": actual,
                **(details or {}),
            },
        )


class RiskBudgetExceededError(V53BaseError):
    def __init__(
        self,
        pair: str,
        budget_type: str,
        current_pct: float,
        limit_pct: float,
        module: str = "risk",
        details: ErrorDetails | None = None,
    ) -> None:
        super().__init__(
            message=f"Budget risque dépassé pour {pair}: {budget_type} à {current_pct:.1f}% (limite: {limit_pct:.1f}%)",
            code="ERR_RISK_BUDGET_EXCEEDED",
            module=module,
            pair=pair,
            details={
                "budget_type": budget_type,
                "current_pct": current_pct,
                "limit_pct": limit_pct,
                **(details or {}),
            },
        )


class InvalidProfileActivationError(V53BaseError):
    def __init__(
        self,
        requested_profile: str,
        current_profile: str,
        reason: str,
        module: str = "profile",
        details: ErrorDetails | None = None,
    ) -> None:
        super().__init__(
            message=f"Activation profil invalide: demandé={requested_profile}, courant={current_profile}. Raison: {reason}",
            code="ERR_INVALID_PROFILE_ACTIVATION",
            module=module,
            pair=None,
            details={
                "requested_profile": requested_profile,
                "current_profile": current_profile,
                "reason": reason,
                **(details or {}),
            },
        )


class EngineNotAllowedError(V53BaseError):
    def __init__(
        self,
        engine_id: str,
        profile: str,
        module: str = "engine",
        details: ErrorDetails | None = None,
    ) -> None:
        super().__init__(
            message=f"Moteur {engine_id} non autorisé en profil {profile}",
            code="ERR_ENGINE_NOT_ALLOWED",
            module=module,
            pair=None,
            details={"engine_id": engine_id, "profile": profile, **(details or {})},
        )


class ReconciliationError(V53BaseError):
    def __init__(
        self,
        pair: str,
        local_state: str,
        exchange_state: str,
        module: str = "execution",
        details: ErrorDetails | None = None,
    ) -> None:
        super().__init__(
            message=f"Réconciliation échouée pour {pair}: local={local_state}, exchange={exchange_state}",
            code="ERR_RECONCILIATION",
            module=module,
            pair=pair,
            details={
                "local_state": local_state,
                "exchange_state": exchange_state,
                **(details or {}),
            },
        )


class BootstrapError(V53BaseError):
    def __init__(
        self,
        module: str,
        phase: str,
        reason: str,
        details: ErrorDetails | None = None,
    ) -> None:
        super().__init__(
            message=f"Bootstrap échoué pour {module} (phase: {phase}): {reason}",
            code="ERR_BOOTSTRAP",
            module=module,
            pair=None,
            details={"phase": phase, "reason": reason, **(details or {})},
        )


__all__ = [
    "V53BaseError", "DataStaleError", "DependencyViolationError",
    "PairSuspendedError", "RiskBudgetExceededError",
    "InvalidProfileActivationError", "ContractViolationError",
    "EngineNotAllowedError", "ReconciliationError", "BootstrapError",
]
