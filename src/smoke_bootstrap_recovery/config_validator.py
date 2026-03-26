"""
7.5.2 — Config Validator: verify that necessary configs are present and coherent.

Checks:
- All required keys are present
- No required key has a None/empty value
- Types match expected schema (basic validation)

Spec 7.9: every startup error must be explicit.
"""

from __future__ import annotations

from typing import Any

from smoke_bootstrap_recovery.smoke_models import ConfigCheckResult, SmokeStatus


class ConfigSchema:
    """Declares the expected config keys for a module."""

    def __init__(
        self,
        required_keys: tuple[str, ...] = (),
        optional_keys: tuple[str, ...] = (),
        type_checks: dict[str, type] | None = None,
    ) -> None:
        self.required_keys = required_keys
        self.optional_keys = optional_keys
        self.type_checks = type_checks or {}

    @property
    def all_keys(self) -> frozenset[str]:
        return frozenset(self.required_keys) | frozenset(self.optional_keys)


def validate_config(
    module_name: str,
    config: dict[str, Any],
    schema: ConfigSchema,
) -> ConfigCheckResult:
    """Validate a config dict against a schema.

    Returns FAIL if any required key is missing or has None/empty value.
    Returns PASS if all required keys are present and valid.
    """
    missing: list[str] = []
    invalid: list[str] = []

    for key in schema.required_keys:
        if key not in config:
            missing.append(key)
        elif config[key] is None or config[key] == "":
            invalid.append(key)

    # Type checks for present keys
    for key, expected_type in schema.type_checks.items():
        if key in config and config[key] is not None:
            if not isinstance(config[key], expected_type):
                invalid.append(key)

    if missing or invalid:
        parts: list[str] = []
        if missing:
            parts.append(f"missing: {missing}")
        if invalid:
            parts.append(f"invalid (None/empty/wrong type): {invalid}")
        return ConfigCheckResult(
            module_name=module_name,
            status=SmokeStatus.FAIL,
            missing_keys=tuple(missing),
            invalid_keys=tuple(invalid),
            message=f"Config validation failed: {'; '.join(parts)}",
        )

    return ConfigCheckResult(
        module_name=module_name,
        status=SmokeStatus.PASS,
        message="Config validation passed",
    )


# ─── KNOWN SCHEMAS PER BUILD-1 MODULE ────────────────────────────────
# Minimal schemas. Stateless Build-1 modules have no required config.

BUILD1_SCHEMAS: dict[str, ConfigSchema] = {
    "interface_contracts": ConfigSchema(),
    "manifest_registry": ConfigSchema(),
    "dag_validator": ConfigSchema(),
    "contract_test_suite": ConfigSchema(),
    "smoke_bootstrap_recovery": ConfigSchema(),
}


def validate_build1_configs(
    configs: dict[str, dict[str, Any]] | None = None,
) -> tuple[ConfigCheckResult, ...]:
    """Validate configs for all Build-1 modules.

    If no configs dict is provided, uses empty configs (valid for stateless modules).
    """
    if configs is None:
        configs = {}

    results: list[ConfigCheckResult] = []
    for module_name, schema in BUILD1_SCHEMAS.items():
        config = configs.get(module_name, {})
        results.append(validate_config(module_name, config, schema))
    return tuple(results)
