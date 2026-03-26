"""
7.5.3 — Recovery Runner: trigger shutdown / relaunch / verify clean state.

Tests that a module can:
- Shut down cleanly
- Restart without corrupting state
- Recover after controlled interruption

Spec 7.4: no silent state repair. Spec 7.9: partial init is NOT ok.
"""

from __future__ import annotations

import time
from typing import Any

from smoke_bootstrap_recovery.bootstrap_runner import Bootstrappable
from smoke_bootstrap_recovery.smoke_models import RecoveryResult, SmokeStatus


def run_recovery_cycle(
    module_name: str,
    factory: Bootstrappable,
    config: dict[str, Any],
    pre_state_checker: Any | None = None,
    post_state_checker: Any | None = None,
) -> RecoveryResult:
    """Run a full shutdown → restart → verify cycle.

    Steps:
    1. Bootstrap the module
    2. Optionally check pre-shutdown state
    3. Shutdown
    4. Re-bootstrap
    5. Optionally check post-restart state
    6. Final shutdown

    Args:
        factory: Object implementing Bootstrappable protocol.
        config: Config dict for bootstrap.
        pre_state_checker: Optional callable() -> bool to verify state before shutdown.
        post_state_checker: Optional callable() -> bool to verify state after restart.
    """
    start = time.perf_counter()
    pre_valid = False
    post_valid = False

    try:
        # Step 1: Initial bootstrap
        factory.bootstrap(config)

        # Step 2: Check pre-shutdown state
        if pre_state_checker is not None:
            pre_valid = pre_state_checker()
        else:
            pre_valid = True

        # Step 3: Shutdown
        factory.shutdown()

        # Step 4: Re-bootstrap
        factory.bootstrap(config)

        # Step 5: Check post-restart state
        if post_state_checker is not None:
            post_valid = post_state_checker()
        else:
            post_valid = True

        # Step 6: Final shutdown
        factory.shutdown()

        elapsed = (time.perf_counter() - start) * 1000

        if not pre_valid:
            return RecoveryResult(
                module_name=module_name,
                status=SmokeStatus.FAIL,
                pre_state_valid=False,
                post_state_valid=post_valid,
                message="Pre-shutdown state check failed",
                duration_ms=elapsed,
            )

        if not post_valid:
            return RecoveryResult(
                module_name=module_name,
                status=SmokeStatus.FAIL,
                pre_state_valid=True,
                post_state_valid=False,
                message="Post-restart state check failed: state may be corrupted",
                duration_ms=elapsed,
            )

        return RecoveryResult(
            module_name=module_name,
            status=SmokeStatus.PASS,
            pre_state_valid=True,
            post_state_valid=True,
            message="Recovery cycle completed successfully",
            duration_ms=elapsed,
        )

    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return RecoveryResult(
            module_name=module_name,
            status=SmokeStatus.FAIL,
            pre_state_valid=pre_valid,
            post_state_valid=post_valid,
            message=f"Recovery failed: {type(exc).__name__}: {exc}",
            duration_ms=elapsed,
        )
