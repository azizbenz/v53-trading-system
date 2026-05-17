from __future__ import annotations

from datetime import UTC, datetime, timedelta
import backtest_artifact_import.capital_profile_builder as import_capital_profile_builder
import local_replay_runtime.capital_profile_builder as replay_capital_profile_builder
import shutil

from backtest_artifact_import import (
    CapitalProfileBuildInput,
    build_capital_bucket_profile,
    build_contract_validation_capital_profiles,
    enforce_capital_profile,
    select_lower_proven_capital_bucket,
    validate_capital_profile,
    write_capital_profile_artifacts,
)
from interface_contracts import RuntimeMode
from tests.support_paths import make_repo_scratch_dir


def _ready_profile_kwargs(capital_bucket: int) -> dict[str, object]:
    created_at = datetime(2026, 5, 1, tzinfo=UTC)
    return {
        "capital_bucket": capital_bucket,
        "pair_universe": ("BTCUSDT",),
        "allowed_pairs": ("BTCUSDT",),
        "max_active_pairs": 1,
        "record_count": 100,
        "executed_only_net_return": 0.01,
        "executed_only_net_return_status": "EXECUTED_NET_RETURN_PROVEN",
        "true_net_equity_max_drawdown": 0.04,
        "true_net_equity_drawdown_status": "TRUE_NET_EQUITY_DRAWDOWN_PROVEN",
        "fee_source_status": "FEE_SOURCE_PROVEN",
        "impact_source_status": "IMPACT_SOURCE_PROVEN",
        "cost_model_completeness_status": "COST_MODEL_COMPLETE",
        "fill_realism_status": "FILL_REALISM_PROVEN",
        "cost_parity_status": "REPLAY_LIVE_COST_PARITY_PROVEN",
        "book_depth_source_status": "BOOK_DEPTH20_AVAILABLE",
        "sample_size_survival_status": "MEASURED",
        "promotion_status": "CAPITAL_BUCKET_READY",
        "input_data_hash": "a" * 64,
        "method_version_hash": "capital.v1",
        "run_id": f"run-capital-{capital_bucket}",
        "strategy_ladder_manifest_ref": f"E:/audit/{capital_bucket}/run_manifest.json",
        "execution_fidelity_status": "FULL_CANONICAL_EXECUTION",
        "execution_fidelity_gap_codes": (),
        "created_at": created_at,
        "expires_at": created_at + timedelta(days=7),
    }


def test_contract_validation_profiles_cover_required_buckets_without_fake_pairs() -> None:
    profiles = build_contract_validation_capital_profiles()

    assert tuple(profile.capital_bucket for profile in profiles) == (400, 500, 1500, 4000)
    assert profiles[0].pair_universe == ()
    assert profiles[0].allowed_pairs == ()
    assert profiles[0].promotion_status == "CAPITAL_BUCKET_NOT_PROVEN"
    assert "BLOCKED_BY_BACKTEST" in profiles[0].promotion_blockers


def test_expected_ce_alone_cannot_allow_pairs_or_mark_bucket_ready() -> None:
    profile = build_capital_bucket_profile(
        CapitalProfileBuildInput(
            capital_bucket=400,
            pair_universe=("BTCUSDT", "ETHUSDT"),
            allowed_pairs=("BTCUSDT",),
            expected_ce_net=0.12,
        )
    )

    assert profile.promotion_status == "CAPITAL_BUCKET_NOT_PROVEN"
    assert profile.allowed_pairs == ()
    assert profile.blocked_pairs[0].pair == "BTCUSDT"
    assert profile.blocked_pairs[0].status == "PAIR_NOT_PROVEN"


def test_capital_profile_hash_is_deterministic() -> None:
    first = build_capital_bucket_profile(
        CapitalProfileBuildInput(
            capital_bucket=1500,
            quote_currency="USDT",
            method_version_hash="capital.v1",
        )
    )
    second = build_capital_bucket_profile(
        CapitalProfileBuildInput(
            capital_bucket=1500,
            quote_currency="USDT",
            method_version_hash="capital.v1",
        )
    )

    assert first.artifact_hash == second.artifact_hash


def test_validate_capital_profile_fails_closed_for_stale_and_hash_invalid() -> None:
    stale = build_capital_bucket_profile(
        CapitalProfileBuildInput(
            **(
                _ready_profile_kwargs(4000)
                | {
                    "executed_only_net_return": 0.02,
                    "true_net_equity_max_drawdown": 0.05,
                    "expires_at": datetime(2026, 5, 1, tzinfo=UTC),
                }
            ),
        )
    )
    stale_result = validate_capital_profile(
        stale,
        as_of=datetime(2026, 5, 2, tzinfo=UTC),
    )
    hash_result = validate_capital_profile(
        stale.model_copy(update={"artifact_hash": "broken"}),
        as_of=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
    )

    assert stale_result.status == "CAPITAL_PROFILE_STALE"
    assert stale_result.no_submit_status == "NO_SUBMIT_CAPITAL_PROFILE_INVALID"
    assert hash_result.status == "CAPITAL_PROFILE_HASH_INVALID"
    assert hash_result.no_submit_status == "NO_SUBMIT_CAPITAL_PROFILE_INVALID"


def test_select_lower_proven_capital_bucket_never_uses_higher_bucket() -> None:
    lower = build_capital_bucket_profile(
        CapitalProfileBuildInput(
            **_ready_profile_kwargs(500),
        )
    )
    higher = build_capital_bucket_profile(
        CapitalProfileBuildInput(
            **(
                _ready_profile_kwargs(1500)
                | {
                    "pair_universe": ("BTCUSDT", "ETHUSDT"),
                    "allowed_pairs": ("BTCUSDT", "ETHUSDT"),
                    "max_active_pairs": 2,
                    "executed_only_net_return": 0.02,
                    "true_net_equity_max_drawdown": 0.03,
                }
            ),
        )
    )

    selection = select_lower_proven_capital_bucket(
        live_capital=1200.0,
        profiles=(higher, lower),
        as_of=datetime(2026, 5, 2, tzinfo=UTC),
    )

    assert selection.status == "CAPITAL_PROFILE_VALID"
    assert selection.selected_bucket == 500
    assert selection.profile is not None
    assert selection.profile.capital_bucket == 500


def test_enforce_capital_profile_blocks_micro_live_on_missing_profile_and_static_config_override() -> None:
    missing = enforce_capital_profile(
        runtime_mode=RuntimeMode.MICRO_LIVE,
        profile=None,
        configured_pairs=("BTCUSDT",),
    )
    valid_profile = build_capital_bucket_profile(
        CapitalProfileBuildInput(
            **(
                _ready_profile_kwargs(400)
                | {
                    "pair_universe": ("BTCUSDT", "ETHUSDT"),
                    "allowed_pairs": ("BTCUSDT",),
                    "record_count": 120,
                }
            ),
        )
    )
    enforced = enforce_capital_profile(
        runtime_mode=RuntimeMode.MICRO_LIVE,
        profile=valid_profile,
        configured_pairs=("BTCUSDT", "ETHUSDT"),
        as_of=datetime(2026, 5, 2, tzinfo=UTC),
    )

    assert missing.validation_status == "CAPITAL_PROFILE_MISSING"
    assert missing.no_submit_status == "NO_SUBMIT_CAPITAL_PROFILE_INVALID"
    assert enforced.validation_status == "CAPITAL_PROFILE_VALID"
    assert enforced.allowed_pairs == ("BTCUSDT",)
    assert any(row.pair == "ETHUSDT" for row in enforced.blocked_pairs)


def test_capital_profile_ready_request_stays_fail_closed_without_manifest_and_fidelity() -> None:
    profile = build_capital_bucket_profile(
        CapitalProfileBuildInput(
            capital_bucket=400,
            pair_universe=("BTCUSDT",),
            allowed_pairs=("BTCUSDT",),
            max_active_pairs=1,
            record_count=100,
            executed_only_net_return=0.01,
            executed_only_net_return_status="EXECUTED_NET_RETURN_PROVEN",
            true_net_equity_max_drawdown=0.04,
            true_net_equity_drawdown_status="TRUE_NET_EQUITY_DRAWDOWN_PROVEN",
            fee_source_status="FEE_SOURCE_PROVEN",
            impact_source_status="IMPACT_SOURCE_PROVEN",
            cost_model_completeness_status="COST_MODEL_COMPLETE",
            fill_realism_status="FILL_REALISM_PROVEN",
            cost_parity_status="REPLAY_LIVE_COST_PARITY_PROVEN",
            book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
            sample_size_survival_status="MEASURED",
            promotion_status="CAPITAL_BUCKET_READY",
            input_data_hash="a" * 64,
            method_version_hash="capital.v1",
            expires_at=datetime(2026, 5, 8, tzinfo=UTC),
        )
    )

    assert profile.promotion_status == "CAPITAL_BUCKET_NOT_PROVEN"
    assert "BLOCKED_BY_RUN_ID" in profile.promotion_blockers
    assert "BLOCKED_BY_STRATEGY_LADDER_MANIFEST" in profile.promotion_blockers
    assert "BLOCKED_BY_EXECUTION_FIDELITY" in profile.promotion_blockers


def test_write_capital_profile_artifacts_materializes_bucket_json_files() -> None:
    scratch = make_repo_scratch_dir("capital_profile_builder_tests", "write_artifacts")
    try:
        written = write_capital_profile_artifacts(
            scratch,
            build_contract_validation_capital_profiles()[:2],
        )

        assert len(written) == 2
        assert written[0].name == "400.json"
        assert written[1].name == "500.json"
        assert written[0].exists()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_backtest_artifact_import_capital_profile_builder_is_owned_by_local_replay_runtime() -> None:
    assert (
        import_capital_profile_builder.CapitalProfileBuildInput
        is replay_capital_profile_builder.CapitalProfileBuildInput
    )
    assert (
        import_capital_profile_builder.build_capital_bucket_profile
        is replay_capital_profile_builder.build_capital_bucket_profile
    )
    assert (
        import_capital_profile_builder.write_capital_profile_artifacts
        is replay_capital_profile_builder.write_capital_profile_artifacts
    )
