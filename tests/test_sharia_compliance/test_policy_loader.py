from pathlib import Path

from sharia_compliance import load_sharia_policy


def test_load_sharia_policy_reads_versioned_yaml():
    policy = load_sharia_policy(Path("config/sharia/policy_v1.yml"))

    assert policy.policy_version == "sharia_policy_v1"
    assert policy.stablecoin_policy.accepted_quote_assets == ("USDT",)
    assert "BTC" in policy.whitelisted_base_assets
    assert "AAVE" in policy.blacklisted_base_assets
