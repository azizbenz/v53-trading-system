from pathlib import Path
from uuid import uuid4

import pytest

from sharia_compliance import FilePairScreeningProvider, load_pair_screening_registry


def _test_dir() -> Path:
    path = Path("build/test_pair_screening_registry") / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_load_pair_screening_registry_reads_versioned_yaml() -> None:
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
""".strip(),
        encoding="utf-8",
    )

    registry = load_pair_screening_registry(registry_path)

    assert registry.registry_version == "registry_v1"
    assert registry.snapshots[0].pair == "BTCUSDT"


def test_file_pair_screening_provider_returns_snapshot_by_pair() -> None:
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
""".strip(),
        encoding="utf-8",
    )

    provider = FilePairScreeningProvider(registry_path)

    assert provider.get_snapshot("btcusdt") is not None
    assert provider.get_snapshot("ETHUSDT") is None


def test_load_pair_screening_registry_rejects_duplicate_pairs() -> None:
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
  - pair: BTCUSDT
    screening_provider: fixture
    provider_version: v1
    reviewed_at: 2026-04-10T12:00:00Z
    debt_to_total_assets: "0.21"
    cash_and_interest_bearing_to_total_assets: "0.10"
    interest_income_to_total_revenue: "0.01"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="pairs must be unique"):
        load_pair_screening_registry(registry_path)
