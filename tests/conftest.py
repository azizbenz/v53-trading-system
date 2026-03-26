"""Fixtures partagées pour tous les tests V5.3."""
import pytest

NOW_MS = 1_700_000_000_000  # Timestamp de référence (Nov 2023)

@pytest.fixture
def now_ms():
    return NOW_MS

@pytest.fixture
def valid_pairs():
    return ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "LINKUSDT"]
