from pathlib import Path
from uuid import uuid4

from sharia_compliance import (
    FilePairScreeningProvider,
    audit_traded_pairs_against_screening,
    load_sharia_policy,
)


def _test_dir() -> Path:
    path = Path("build/test_pair_screening_audit") / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def _provider() -> FilePairScreeningProvider:
    registry_path = _test_dir() / "pair_screening_registry.yml"
    registry_path.write_text(
        """
schema_version: sharia.pair_screening_registry.v1
registry_version: registry_v1
source_reference: manual_review
snapshots:
  - pair: BTCUSDT
    screening_provider: fixture
    provider_version: v1
    reviewed_at: 2026-04-10T12:00:00Z
    debt_to_total_assets: "0.20"
    cash_and_interest_bearing_to_total_assets: "0.10"
    interest_income_to_total_revenue: "0.01"
  - pair: ETHUSDT
    screening_provider: fixture
    provider_version: v1
    reviewed_at: 2026-04-10T12:00:00Z
    debt_to_total_assets: "0.34"
    cash_and_interest_bearing_to_total_assets: "0.10"
    interest_income_to_total_revenue: "0.01"
""".strip(),
        encoding="utf-8",
    )
    return FilePairScreeningProvider(registry_path)


def test_pair_screening_audit_is_clean_when_all_pairs_pass() -> None:
    report = audit_traded_pairs_against_screening(
        traded_pairs=("BTCUSDT",),
        provider=_provider(),
        policy=load_sharia_policy("config/sharia/policy_v1.yml"),
    )

    assert report.clean is True
    assert report.findings == ()


def test_pair_screening_audit_flags_missing_and_failed_pairs() -> None:
    report = audit_traded_pairs_against_screening(
        traded_pairs=("ETHUSDT", "SOLUSDT"),
        provider=_provider(),
        policy=load_sharia_policy("config/sharia/policy_v1.yml"),
    )

    assert report.clean is False
    assert tuple(finding.reason_code for finding in report.findings) == (
        "PAIR_SCREENING_FAILED",
        "PAIR_SCREENING_MISSING",
    )
