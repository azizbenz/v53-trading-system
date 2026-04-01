"""
7.5.3 — Recovery Runner: trigger shutdown / relaunch / verify clean state.

Tests that a module can:
- Shut down cleanly
- Restart without corrupting state
- Recover after controlled interruption

Spec 7.4: no silent state repair. Spec 7.9: partial init is NOT ok.
GEM-04: exponential backoff on retry + resource release verification.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from smoke_bootstrap_recovery.bootstrap_runner import Bootstrappable
from smoke_bootstrap_recovery.smoke_models import RecoveryResult, SmokeStatus

# GEM-04: backoff defaults
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BASE_DELAY_S = 1.0
_DEFAULT_MAX_DELAY_S = 30.0
_DEFAULT_BACKOFF_FACTOR = 2.0


def _backoff_delay(attempt: int, base: float, factor: float, cap: float) -> float:
    """Compute exponential backoff delay capped at max."""
    return min(base * (factor ** attempt), cap)


def run_recovery_cycle(
    module_name: str,
    factory: Bootstrappable,
    config: dict[str, Any],
    pre_state_checker: Any | None = None,
    post_state_checker: Any | None = None,
    resource_release_checker: Callable[[], bool] | None = None,
    max_retries: int = _DEFAULT_MAX_RETRIES,
    base_delay_s: float = _DEFAULT_BASE_DELAY_S,
    backoff_factor: float = _DEFAULT_BACKOFF_FACTOR,
    max_delay_s: float = _DEFAULT_MAX_DELAY_S,
) -> RecoveryResult:
    """Run a full shutdown → restart → verify cycle with exponential backoff.

    Steps:
    1. Bootstrap the module
    2. Optionally check pre-shutdown state
    3. Shutdown
    4. GEM-04: verify resource release (FDs, sockets, etc.)
    5. Re-bootstrap (with exponential backoff on failure)
    6. Optionally check post-restart state
    7. Final shutdown

    Args:
        factory: Object implementing Bootstrappable protocol.
        config: Config dict for bootstrap.
        pre_state_checker: Optional callable() -> bool to verify state before shutdown.
        post_state_checker: Optional callable() -> bool to verify state after restart.
        resource_release_checker: GEM-04: optional callable() -> bool to verify
            resources (FDs, sockets) are released after shutdown.
        max_retries: Maximum bootstrap retry attempts (GEM-04).
        base_delay_s: Base delay between retries in seconds.
        backoff_factor: Multiplier for exponential backoff.
        max_delay_s: Maximum delay cap.
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

        # Step 4 (GEM-04): Verify resources released after shutdown
        if resource_release_checker is not None:
            if not resource_release_checker():
                elapsed = (time.perf_counter() - start) * 1000
                return RecoveryResult(
                    module_name=module_name,
                    status=SmokeStatus.FAIL,
                    pre_state_valid=pre_valid,
                    post_state_valid=False,
                    message="Resource release check failed after shutdown (FDs/sockets not freed)",
                    duration_ms=elapsed,
                )

        # Step 5 (GEM-04): Re-bootstrap with exponential backoff
        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                factory.bootstrap(config)
                last_error = None
                break
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    delay = _backoff_delay(attempt, base_delay_s, backoff_factor, max_delay_s)
                    time.sleep(delay)

        if last_error is not None:
            elapsed = (time.perf_counter() - start) * 1000
            return RecoveryResult(
                module_name=module_name,
                status=SmokeStatus.FAIL,
                pre_state_valid=pre_valid,
                post_state_valid=False,
                message=f"Re-bootstrap failed after {max_retries + 1} attempts: {last_error}",
                duration_ms=elapsed,
            )

        # Step 6: Check post-restart state
        if post_state_checker is not None:
            post_valid = post_state_checker()
        else:
            post_valid = True

        # Step 7: Final shutdown
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
