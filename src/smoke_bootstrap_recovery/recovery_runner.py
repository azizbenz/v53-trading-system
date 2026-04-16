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
from typing import Callable

from smoke_bootstrap_recovery.bootstrap_runner import Bootstrappable
from smoke_bootstrap_recovery.smoke_models import RecoveryResult, SmokeStatus

# GEM-04: backoff defaults
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BASE_DELAY_S = 1.0
_DEFAULT_MAX_DELAY_S = 30.0
_DEFAULT_BACKOFF_FACTOR = 2.0

RecoveryConfig = dict[str, object]
StateChecker = Callable[[], bool]
ResourceReleaseChecker = Callable[[], bool]


def _backoff_delay(attempt: int, base: float, factor: float, cap: float) -> float:
    """Compute exponential backoff delay capped at max."""
    return min(base * (factor ** attempt), cap)


def _elapsed_ms(start: float) -> float:
    """Return elapsed duration in milliseconds."""
    return (time.perf_counter() - start) * 1000


def _build_failure_result(
    module_name: str,
    *,
    pre_valid: bool,
    post_valid: bool,
    message: str,
    start: float,
) -> RecoveryResult:
    """Build a failure result with consistent timing."""
    return RecoveryResult(
        module_name=module_name,
        status=SmokeStatus.FAIL,
        pre_state_valid=pre_valid,
        post_state_valid=post_valid,
        message=message,
        duration_ms=_elapsed_ms(start),
    )


def _run_state_check(checker: StateChecker | None) -> bool:
    """Return checker state or True when no checker is configured."""
    return checker() if checker is not None else True


def _verify_resource_release(
    module_name: str,
    *,
    checker: ResourceReleaseChecker | None,
    pre_valid: bool,
    start: float,
) -> RecoveryResult | None:
    """Return a failure result when resources were not released."""
    if checker is None or checker():
        return None
    return _build_failure_result(
        module_name,
        pre_valid=pre_valid,
        post_valid=False,
        message="Resource release check failed after shutdown (FDs/sockets not freed)",
        start=start,
    )


def _retry_bootstrap(
    factory: Bootstrappable,
    config: RecoveryConfig,
    *,
    max_retries: int,
    base_delay_s: float,
    backoff_factor: float,
    max_delay_s: float,
) -> Exception | None:
    """Retry bootstrap with capped exponential backoff."""
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            factory.bootstrap(config)
            return None
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                delay = _backoff_delay(attempt, base_delay_s, backoff_factor, max_delay_s)
                time.sleep(delay)
    return last_error


def _validate_recovery_state(
    module_name: str,
    *,
    pre_valid: bool,
    post_valid: bool,
    start: float,
) -> RecoveryResult:
    """Map checker outcomes to the canonical recovery result."""
    if not pre_valid:
        return _build_failure_result(
            module_name,
            pre_valid=False,
            post_valid=post_valid,
            message="Pre-shutdown state check failed",
            start=start,
        )
    if not post_valid:
        return _build_failure_result(
            module_name,
            pre_valid=True,
            post_valid=False,
            message="Post-restart state check failed: state may be corrupted",
            start=start,
        )
    return RecoveryResult(
        module_name=module_name,
        status=SmokeStatus.PASS,
        pre_state_valid=True,
        post_state_valid=True,
        message="Recovery cycle completed successfully",
        duration_ms=_elapsed_ms(start),
    )


def run_recovery_cycle(
    module_name: str,
    factory: Bootstrappable,
    config: RecoveryConfig,
    pre_state_checker: StateChecker | None = None,
    post_state_checker: StateChecker | None = None,
    resource_release_checker: ResourceReleaseChecker | None = None,
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
        factory.bootstrap(config)
        pre_valid = _run_state_check(pre_state_checker)
        factory.shutdown()

        resource_failure = _verify_resource_release(
            module_name,
            checker=resource_release_checker,
            pre_valid=pre_valid,
            start=start,
        )
        if resource_failure is not None:
            return resource_failure

        last_error = _retry_bootstrap(
            factory,
            config,
            max_retries=max_retries,
            base_delay_s=base_delay_s,
            backoff_factor=backoff_factor,
            max_delay_s=max_delay_s,
        )
        if last_error is not None:
            return _build_failure_result(
                module_name,
                pre_valid=pre_valid,
                post_valid=False,
                message=f"Re-bootstrap failed after {max_retries + 1} attempts: {last_error}",
                start=start,
            )

        post_valid = _run_state_check(post_state_checker)
        factory.shutdown()
        return _validate_recovery_state(
            module_name,
            pre_valid=pre_valid,
            post_valid=post_valid,
            start=start,
        )
    except Exception as exc:
        return _build_failure_result(
            module_name,
            pre_valid=pre_valid,
            post_valid=post_valid,
            message=f"Recovery failed: {type(exc).__name__}: {exc}",
            start=start,
        )
