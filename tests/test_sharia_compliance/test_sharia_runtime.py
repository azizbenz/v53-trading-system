import json
from datetime import datetime, timezone
from pathlib import Path

from sharia_compliance import PolicyAuditLogger, ShariaRuntime, ShariaTradeRequest, load_sharia_policy


def test_sharia_runtime_logs_rejection_to_append_only_jsonl(tmp_path: Path):
    policy = load_sharia_policy("config/sharia/policy_v1.yml")
    audit_path = tmp_path / "sharia_audit" / "audit.jsonl"
    runtime = ShariaRuntime(
        policy,
        audit_logger=PolicyAuditLogger(
            audit_path,
            now=lambda: datetime(2026, 4, 9, 12, 0, tzinfo=timezone.utc),
        ),
    )

    decision = runtime.authorize_trade(
        ShariaTradeRequest(
            intent_id="intent-1",
            pair="AAVEUSDT",
            engine_id="engine_a",
            side="buy",
        )
    )

    assert decision.allowed is False
    lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["decision"] == "reject"
    assert payload["reason_code"] == "ASSET_BLACKLISTED"
