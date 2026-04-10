"""BS-67 regression — DTRStore lookup helpers should not rescan the full record list."""

from __future__ import annotations

from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord
from meta_minimal.dtr_core.trace_persistence_layer import DTRStore


def _record(
    dtr_id: str,
    *,
    pair: str,
    engine_id: str,
    state: DecisionState,
) -> DTRRecord:
    return DTRRecord(
        dtr_id=dtr_id,
        timestamp=1700000000.0,
        pair=pair,
        engine_id=engine_id,
        decision_state=state,
    )


def test_persist_updates_lookup_indexes_in_insertion_order() -> None:
    store = DTRStore()
    first = _record("dtr_001", pair="BTCUSDT", engine_id="engine_a", state=DecisionState.SELECTED)
    second = _record("dtr_002", pair="ETHUSDT", engine_id="engine_b", state=DecisionState.HARD_BLOCKED)
    third = _record("dtr_003", pair="BTCUSDT", engine_id="engine_a", state=DecisionState.SELECTED)

    assert store.persist(first) is True
    assert store.persist(second) is True
    assert store.persist(third) is True

    assert store.get_by_pair("BTCUSDT") == (first, third)
    assert store.get_by_engine("engine_a") == (first, third)
    assert store.get_by_state(DecisionState.SELECTED) == (first, third)
    assert store.get_by_state("selected") == (first, third)


def test_persist_batch_keeps_secondary_indexes_coherent() -> None:
    store = DTRStore()
    records = (
        _record("dtr_001", pair="BTCUSDT", engine_id="engine_a", state=DecisionState.EVALUATED),
        _record("dtr_002", pair="BTCUSDT", engine_id="engine_b", state=DecisionState.SELECTED),
        _record("dtr_003", pair="ETHUSDT", engine_id="engine_a", state=DecisionState.SELECTED),
    )

    assert store.persist_batch(records) == 3

    assert store.get_by_pair("BTCUSDT") == records[:2]
    assert store.get_by_engine("engine_a") == (records[0], records[2])
    assert store.get_by_state(DecisionState.SELECTED) == records[1:]
    assert store.get_by_pair("SOLUSDT") == ()
