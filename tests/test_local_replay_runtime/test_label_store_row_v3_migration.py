from __future__ import annotations

import json
import math

import pytest
from pydantic import ValidationError

from local_replay_runtime.strategy_ladder_b2_label_store_builder import (
    StrategyLadderB2LabelStoreRow,
    _EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS,
)
from local_replay_runtime.strategy_ladder_expected_edge_training import (
    SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES,
)


def _row_payload() -> dict[str, object]:
    return {
        "candidate_id": "cand-1",
        "engine_id": "engine_b",
        "pair": "BTCUSDT",
        "timeframe": "1m",
        "capital_bucket": 1,
        "decision_timestamp_ms": 1_700_000_000_000,
        "feature_timestamp_ms": 1_700_000_000_000,
        "replay_record_id": "replay-1",
        "evidence_class": "REPLAY_EXECUTED_ONLY_NET_RETURN",
        "label_quality_status": "LABEL_QUALITY_PROMOTION_GRADE_CANDIDATE",
        "replay_grounded_status": "REPLAY_GROUNDED_PROMOTION_GRADE_CANDIDATE",
        "replay_quality_status": "REPLAY_READY",
        "execution_fidelity_status": "EXECUTION_FIDELITY_READY",
        "entry_reference_status": "ENTRY_REFERENCE_EXECUTED_FILL_MEASURED",
        "mfe_mae_status": "MFE_MAE_AVAILABLE",
        "feature_values": {
            "close_return": 0.01,
            "anti_revenge_state__active": 1.0,
            "anti_revenge_state__cooling": 0.0,
            "anti_revenge_state__idle": 0.0,
        },
    }


def test_schema_version_v3_default() -> None:
    row = StrategyLadderB2LabelStoreRow(**_row_payload())
    assert row.schema_version == "strategy_ladder.b2_label_store_row.v3"


def test_old_v2_payload_loads_with_none_defaults() -> None:
    payload = _row_payload()
    payload["schema_version"] = "strategy_ladder.b2_label_store_row.v2"
    row = StrategyLadderB2LabelStoreRow(**payload)
    assert row.kyle_lambda is None
    assert row.micro_edge_exit_governor_observed is None
    assert row.anti_revenge_state__active is None


def test_temporal_invariant_unchanged() -> None:
    payload = _row_payload()
    payload["feature_timestamp_ms"] = payload["decision_timestamp_ms"] + 1
    with pytest.raises(ValidationError, match="feature_timestamp_ms must be <= decision_timestamp_ms"):
        StrategyLadderB2LabelStoreRow(**payload)


def test_anti_revenge_one_hot_nullable_triplet() -> None:
    row = StrategyLadderB2LabelStoreRow(**_row_payload())
    assert row.anti_revenge_state__active is None
    assert row.anti_revenge_state__cooling is None
    assert row.anti_revenge_state__idle is None


def test_anti_revenge_one_hot_full_active() -> None:
    payload = _row_payload()
    payload.update(
        {
            "anti_revenge_state__active": True,
            "anti_revenge_state__cooling": False,
            "anti_revenge_state__idle": False,
        }
    )
    row = StrategyLadderB2LabelStoreRow(**payload)
    assert row.anti_revenge_state__active is True
    assert row.anti_revenge_state__cooling is False
    assert row.anti_revenge_state__idle is False


@pytest.mark.parametrize("invalid_value", [math.nan, math.inf, -math.inf])
def test_kyle_lambda_finite_only(invalid_value: float) -> None:
    payload = _row_payload()
    payload["kyle_lambda"] = invalid_value
    with pytest.raises(ValidationError, match="kyle_lambda must be finite when provided"):
        StrategyLadderB2LabelStoreRow(**payload)


def test_augmented_keys_aligned_with_validator() -> None:
    assert set(_EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS).issubset(
        set(SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES)
    )


def test_serialized_json_deterministic() -> None:
    payload = _row_payload()
    payload.update(
        {
            "kyle_lambda": 0.0023,
            "anti_revenge_state__active": True,
            "anti_revenge_state__cooling": False,
            "anti_revenge_state__idle": False,
        }
    )
    row = StrategyLadderB2LabelStoreRow(**payload)
    first = row.model_dump_json()
    second = StrategyLadderB2LabelStoreRow.model_validate_json(first).model_dump_json()
    assert json.loads(first) == json.loads(second)
