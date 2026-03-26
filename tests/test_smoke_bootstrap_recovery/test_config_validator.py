"""Tests Module 5 — config_validator: config present, missing, invalid."""

import pytest

from smoke_bootstrap_recovery.config_validator import (
    BUILD1_SCHEMAS,
    ConfigSchema,
    validate_build1_configs,
    validate_config,
)
from smoke_bootstrap_recovery.smoke_models import SmokeStatus


@pytest.mark.build1
class TestConfigValidationPass:
    """7.14: config validation passes when all required keys present."""

    def test_empty_schema_always_passes(self):
        schema = ConfigSchema()
        result = validate_config("test_mod", {}, schema)
        assert result.passed
        assert result.status == SmokeStatus.PASS

    def test_required_keys_present(self):
        schema = ConfigSchema(required_keys=("host", "port"))
        result = validate_config("test_mod", {"host": "localhost", "port": 8080}, schema)
        assert result.passed

    def test_extra_keys_ignored(self):
        schema = ConfigSchema(required_keys=("host",))
        result = validate_config("test_mod", {"host": "localhost", "extra": 42}, schema)
        assert result.passed


@pytest.mark.build1
class TestConfigValidationFail:
    """7.14: bootstrap FAIL if config missing."""

    def test_missing_required_key(self):
        schema = ConfigSchema(required_keys=("host", "port"))
        result = validate_config("test_mod", {"host": "localhost"}, schema)
        assert not result.passed
        assert result.status == SmokeStatus.FAIL
        assert "port" in result.missing_keys

    def test_all_keys_missing(self):
        schema = ConfigSchema(required_keys=("a", "b", "c"))
        result = validate_config("test_mod", {}, schema)
        assert not result.passed
        assert len(result.missing_keys) == 3

    def test_none_value_is_invalid(self):
        schema = ConfigSchema(required_keys=("host",))
        result = validate_config("test_mod", {"host": None}, schema)
        assert not result.passed
        assert "host" in result.invalid_keys

    def test_empty_string_is_invalid(self):
        schema = ConfigSchema(required_keys=("host",))
        result = validate_config("test_mod", {"host": ""}, schema)
        assert not result.passed
        assert "host" in result.invalid_keys

    def test_message_describes_problem(self):
        schema = ConfigSchema(required_keys=("missing_key",))
        result = validate_config("test_mod", {}, schema)
        assert "missing" in result.message.lower()

    def test_wrong_type_is_invalid(self):
        schema = ConfigSchema(
            required_keys=("port",),
            type_checks={"port": int},
        )
        result = validate_config("test_mod", {"port": "not_an_int"}, schema)
        assert not result.passed
        assert "port" in result.invalid_keys

    def test_correct_type_passes(self):
        schema = ConfigSchema(
            required_keys=("port",),
            type_checks={"port": int},
        )
        result = validate_config("test_mod", {"port": 8080}, schema)
        assert result.passed


@pytest.mark.build1
class TestBuild1Configs:
    """Build-1 modules are stateless — empty configs should pass."""

    def test_build1_schemas_defined(self):
        assert len(BUILD1_SCHEMAS) == 5
        assert "interface_contracts" in BUILD1_SCHEMAS
        assert "smoke_bootstrap_recovery" in BUILD1_SCHEMAS

    def test_build1_configs_all_pass(self):
        results = validate_build1_configs()
        assert len(results) == 5
        for r in results:
            assert r.passed, f"{r.module_name} config failed: {r.message}"

    def test_build1_with_no_args(self):
        results = validate_build1_configs(None)
        assert all(r.passed for r in results)
