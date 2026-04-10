"""
Regression tests — BS-125
emitted_at=0.0 (default) must NOT bypass expiry when
max_signal_age_s is explicitly set by the caller.
"""
from __future__ import annotations

import pytest

from portfolio_minimal.opportunity_selector.candidate_pool_builder import (
    CANDIDATE_POOL_FRESHNESS_DISABLED,
    CandidatePoolRejectReason,
    OpportunityCandidate,
    build_enforced_candidate_pool_freshness,
    build_candidate_pool,
)


def _cand(pair: str = "BTCUSDT", emitted_at: float = 0.0) -> OpportunityCandidate:
    return OpportunityCandidate(
        pair=pair,
        engine_id="engine_a",
        penalized_score=0.8,
        candidate_size=100.0,
        emitted_at=emitted_at,
    )


# ── BS-125 core fix ──

def test_emitted_at_zero_rejected_when_expiry_active():
    """BS-125: emitted_at=0.0 with expiry active must be rejected."""
    pool = build_candidate_pool(
        (_cand(emitted_at=0.0),),
        freshness_policy=build_enforced_candidate_pool_freshness(
            now_ts=1000.0,
            max_signal_age_s=60.0,
        ),
    )
    assert pool.pool_size == 0
    assert pool.rejected_count == 1
    assert pool.rejected_candidates[0].reason == CandidatePoolRejectReason.SIGNAL_EXPIRED
    assert "emitted_at not set" in pool.rejected_candidates[0].detail


def test_emitted_at_zero_accepted_when_expiry_inactive():
    """emitted_at=0.0 with NO expiry params must still be accepted (no regression)."""
    pool = build_candidate_pool(
        (_cand(emitted_at=0.0),),
        freshness_policy=CANDIDATE_POOL_FRESHNESS_DISABLED,
    )
    assert pool.pool_size == 1


def test_enforced_freshness_policy_requires_both_values():
    with pytest.raises(ValueError, match="requires now_ts and max_signal_age_s"):
        build_enforced_candidate_pool_freshness(
            now_ts=1000.0,
            max_signal_age_s=None,  # type: ignore[arg-type]
        )


def test_fresh_signal_with_valid_emitted_at_accepted():
    """A fresh signal (emitted 10s ago) with max_signal_age_s=60 must pass."""
    pool = build_candidate_pool(
        (_cand(emitted_at=990.0),),
        freshness_policy=build_enforced_candidate_pool_freshness(
            now_ts=1000.0,
            max_signal_age_s=60.0,
        ),
    )
    assert pool.pool_size == 1


def test_stale_signal_with_valid_emitted_at_rejected():
    """A stale signal (emitted 120s ago) with max_signal_age_s=60 must be rejected."""
    pool = build_candidate_pool(
        (_cand(emitted_at=880.0),),
        freshness_policy=build_enforced_candidate_pool_freshness(
            now_ts=1000.0,
            max_signal_age_s=60.0,
        ),
    )
    assert pool.pool_size == 0
    assert pool.rejected_candidates[0].reason == CandidatePoolRejectReason.SIGNAL_EXPIRED


def test_mixed_candidates_only_unknown_age_rejected():
    """Only the emitted_at=0.0 candidate must be rejected when expiry is active."""
    pool = build_candidate_pool(
        (
            _cand(pair="BTCUSDT", emitted_at=0.0),
            _cand(pair="ETHUSDT", emitted_at=990.0),
        ),
        freshness_policy=build_enforced_candidate_pool_freshness(
            now_ts=1000.0,
            max_signal_age_s=60.0,
        ),
    )
    assert pool.pool_size == 1
    assert pool.candidates[0].pair == "ETHUSDT"
    assert pool.rejected_count == 1
