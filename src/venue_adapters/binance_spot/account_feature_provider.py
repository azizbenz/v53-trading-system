"""Bounded read-only Binance provider for weekly halal account-feature audits."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Awaitable, Callable, Mapping, Protocol

from sharia_compliance import (
    AccountFeaturesAuditConfig,
    AccountFeaturesAuditReport,
    audit_account_features,
)


class BinanceAccountFeaturePayloadClient(Protocol):
    async def get_account_feature_payload(
        self,
        *,
        path: str,
        recv_window_ms: int,
        params: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any] | list[Any]:
        ...


@dataclass(frozen=True)
class _Probe:
    path: str
    feature_key: str
    detector: Callable[[Mapping[str, Any] | list[Any]], Decimal]
    params: Mapping[str, str] | None = None


_PROBES: tuple[_Probe, ...] = (
    _Probe(
        path="/sapi/v1/margin/account",
        feature_key="margin_account",
        detector=lambda payload: _sum_nested_numeric(payload, ("borrowed", "interest")),
    ),
    _Probe(
        path="/sapi/v1/savings/account",
        feature_key="savings_account",
        detector=lambda payload: _sum_nested_numeric(payload, ("totalAmountInBTC", "totalInterest")),
    ),
    _Probe(
        path="/sapi/v1/lending/project/position/list",
        feature_key="lending_positions",
        params={"status": "HOLDING", "size": "100"},
        detector=lambda payload: _detect_list_payload(payload),
    ),
    _Probe(
        path="/sapi/v1/staking/position",
        feature_key="staking_positions",
        params={"product": "STAKING", "size": "100"},
        detector=lambda payload: _detect_list_payload(payload),
    ),
    _Probe(
        path="/sapi/v1/futures/transfer",
        feature_key="futures_transfer_history",
        params={"current": "1", "size": "100"},
        detector=lambda payload: _detect_list_payload(payload),
    ),
)


class BinanceAccountFeatureAuditProvider:
    """Collect bounded read-only Binance evidence and convert it to the halal audit report."""

    def __init__(
        self,
        client: BinanceAccountFeaturePayloadClient,
        *,
        recv_window_ms: int,
        audit_config: AccountFeaturesAuditConfig | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if recv_window_ms < 1:
            raise ValueError("recv_window_ms must be >= 1")
        self._client = client
        self._recv_window_ms = recv_window_ms
        self._audit_config = audit_config or AccountFeaturesAuditConfig()
        self._now = now or (lambda: datetime.now(timezone.utc))

    async def collect_feature_balances(self) -> dict[str, Decimal]:
        balances: dict[str, Decimal] = {}
        for probe in _PROBES:
            payload = await self._client.get_account_feature_payload(
                path=probe.path,
                recv_window_ms=self._recv_window_ms,
                params=probe.params,
            )
            amount = probe.detector(payload)
            if amount > 0:
                balances[probe.feature_key] = amount
        return balances

    async def run_audit(self, *, scanned_at: datetime | None = None) -> AccountFeaturesAuditReport:
        return audit_account_features(
            feature_balances=await self.collect_feature_balances(),
            config=self._audit_config,
            scanned_at=scanned_at or self._now(),
        )


def _detect_list_payload(payload: Mapping[str, Any] | list[Any]) -> Decimal:
    if isinstance(payload, list):
        return Decimal(len(payload))
    if isinstance(payload, Mapping):
        for key in ("rows", "positionAmountVos", "data", "assets", "items"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                return Decimal(len(candidate))
    return Decimal("0")


def _sum_nested_numeric(payload: Mapping[str, Any] | list[Any], keys: tuple[str, ...]) -> Decimal:
    total = Decimal("0")
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, Mapping):
                total += _sum_nested_numeric(item, keys)
        return total
    if not isinstance(payload, Mapping):
        return total
    for key in keys:
        if key in payload:
            total += _to_decimal(payload[key])
    for value in payload.values():
        if isinstance(value, Mapping | list):
            total += _sum_nested_numeric(value, keys)
    return total


def _to_decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


__all__ = ["BinanceAccountFeatureAuditProvider"]
