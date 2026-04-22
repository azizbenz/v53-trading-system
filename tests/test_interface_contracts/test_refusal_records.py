from __future__ import annotations

import pytest
from pydantic import ValidationError

from interface_contracts import EngineId, RefusalCategory, RefusalRecord


NOW_MS = 1_700_000_000_000


class TestRefusalCategory:
    def test_expected_values(self) -> None:
        assert {category.value for category in RefusalCategory} == {
            "no_trade",
            "no_fill",
            "phantom",
            "hard_block",
            "portfolio_rejected",
            "version_invalidated",
        }


class TestRefusalRecord:
    def test_valid_record(self) -> None:
        record = RefusalRecord(
            timestamp_ms=NOW_MS,
            pair="btcusdt",
            engine_id=EngineId.C,
            category=RefusalCategory.HARD_BLOCK,
            reason_codes=(" hard_block.ac_mutual_exclusion.a_holding ",),
            counterfactual_pnl=12.5,
        )
        assert record.pair == "BTCUSDT"
        assert record.reason_codes == ("hard_block.ac_mutual_exclusion.a_holding",)

    def test_engine_id_optional(self) -> None:
        record = RefusalRecord(
            timestamp_ms=NOW_MS,
            pair="ETHUSDT",
            category=RefusalCategory.VERSION_INVALIDATED,
            reason_codes=("reconciliation.mismatch",),
        )
        assert record.engine_id is None

    def test_counterfactual_pnl_accepts_none_and_negative_values(self) -> None:
        none_record = RefusalRecord(
            timestamp_ms=NOW_MS,
            pair="BTCUSDT",
            engine_id=EngineId.A,
            category=RefusalCategory.NO_TRADE,
            reason_codes=("economics.ev_net_below_floor",),
            counterfactual_pnl=None,
        )
        loss_record = RefusalRecord(
            timestamp_ms=NOW_MS,
            pair="ETHUSDT",
            engine_id=EngineId.B,
            category=RefusalCategory.NO_FILL,
            reason_codes=("execution.timeout",),
            counterfactual_pnl=-0.50,
        )

        assert none_record.counterfactual_pnl is None
        assert loss_record.counterfactual_pnl == pytest.approx(-0.50)

    def test_reason_codes_must_not_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            RefusalRecord(
                timestamp_ms=NOW_MS,
                pair="SOLUSDT",
                engine_id=EngineId.B,
                category=RefusalCategory.NO_TRADE,
                reason_codes=(),
            )

    def test_reason_codes_reject_blank_values(self) -> None:
        with pytest.raises(ValidationError):
            RefusalRecord(
                timestamp_ms=NOW_MS,
                pair="SOLUSDT",
                engine_id=EngineId.B,
                category=RefusalCategory.NO_TRADE,
                reason_codes=("  ",),
            )

    def test_record_is_frozen(self) -> None:
        record = RefusalRecord(
            timestamp_ms=NOW_MS,
            pair="ADAUSDT",
            engine_id=EngineId.D,
            category=RefusalCategory.NO_FILL,
            reason_codes=("execution.timeout",),
        )
        with pytest.raises(ValidationError):
            record.pair = "BTCUSDT"

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            RefusalRecord(
                timestamp_ms=NOW_MS,
                pair="LINKUSDT",
                engine_id=EngineId.A,
                category=RefusalCategory.PHANTOM,
                reason_codes=("shadow.fill_gap",),
                unexpected_field="boom",
            )
