from sharia_compliance import ShariaTradeRequest, authorize_trade_type, load_sharia_policy


def test_trade_type_guard_rejects_non_whitelisted_pair():
    policy = load_sharia_policy("config/sharia/policy_v1.yml")

    decision = authorize_trade_type(
        ShariaTradeRequest(
            intent_id="intent-1",
            pair="AAVEUSDT",
            engine_id="engine_a",
            side="buy",
        ),
        policy,
    )

    assert decision.allowed is False
    assert decision.reason_code == "ASSET_BLACKLISTED"


def test_trade_type_guard_rejects_non_spot_metadata():
    policy = load_sharia_policy("config/sharia/policy_v1.yml")

    decision = authorize_trade_type(
        ShariaTradeRequest(
            intent_id="intent-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            side="buy",
            metadata={"trade_mode": "FUTURES", "leverage": 2},
        ),
        policy,
    )

    assert decision.allowed is False
    assert decision.reason_code == "NON_SPOT_FORBIDDEN"


def test_trade_type_guard_permits_whitelisted_spot_trade():
    policy = load_sharia_policy("config/sharia/policy_v1.yml")

    decision = authorize_trade_type(
        ShariaTradeRequest(
            intent_id="intent-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            side="buy",
        ),
        policy,
    )

    assert decision.allowed is True
    assert decision.policy_version == "sharia_policy_v1"


def test_trade_type_guard_rejects_failed_pair_screening():
    policy = load_sharia_policy("config/sharia/policy_v1.yml")

    decision = authorize_trade_type(
        ShariaTradeRequest(
            intent_id="intent-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            side="buy",
            metadata={
                "pair_screening": {
                    "pair": "BTCUSDT",
                    "screening_provider": "fixture",
                    "provider_version": "v1",
                    "reviewed_at": "2026-04-10T12:00:00Z",
                    "debt_to_total_assets": "0.34",
                    "cash_and_interest_bearing_to_total_assets": "0.10",
                    "interest_income_to_total_revenue": "0.01",
                }
            },
        ),
        policy,
    )

    assert decision.allowed is False
    assert decision.reason_code == "PAIR_SCREENING_FAILED"


def test_trade_type_guard_rejects_missing_required_pair_screening():
    policy = load_sharia_policy("config/sharia/policy_v1.yml")

    decision = authorize_trade_type(
        ShariaTradeRequest(
            intent_id="intent-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            side="buy",
            metadata={"pair_screening_required": True},
        ),
        policy,
    )

    assert decision.allowed is False
    assert decision.reason_code == "PAIR_SCREENING_MISSING"


def test_trade_type_guard_rejects_pair_screening_pair_mismatch():
    policy = load_sharia_policy("config/sharia/policy_v1.yml")

    decision = authorize_trade_type(
        ShariaTradeRequest(
            intent_id="intent-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            side="buy",
            metadata={
                "pair_screening": {
                    "pair": "ETHUSDT",
                    "screening_provider": "fixture",
                    "provider_version": "v1",
                    "reviewed_at": "2026-04-10T12:00:00Z",
                    "debt_to_total_assets": "0.10",
                    "cash_and_interest_bearing_to_total_assets": "0.10",
                    "interest_income_to_total_revenue": "0.01",
                }
            },
        ),
        policy,
    )

    assert decision.allowed is False
    assert decision.reason_code == "PAIR_SCREENING_MISMATCH"


def test_trade_type_guard_rejects_invalid_pair_screening_payload():
    policy = load_sharia_policy("config/sharia/policy_v1.yml")

    decision = authorize_trade_type(
        ShariaTradeRequest(
            intent_id="intent-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            side="buy",
            metadata={"pair_screening": "bad-payload"},
        ),
        policy,
    )

    assert decision.allowed is False
    assert decision.reason_code == "PAIR_SCREENING_INVALID"
