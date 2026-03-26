"""Tests Module 4 — compatibility_checker: detect breaking schema changes."""

import pytest

from pydantic import BaseModel, Field

from contract_test_suite.compatibility_checker import (
    FieldSnapshot,
    SchemaSnapshot,
    check_compatibility,
    snapshot_model,
)
from contract_test_suite.contract_models import ContractStatus


class ModelV1(BaseModel, frozen=True):
    name: str
    price: float


class ModelV2Compatible(BaseModel, frozen=True):
    """V2 adds a field with default — non-breaking."""
    name: str
    price: float
    quantity: int = 0


class ModelV2Breaking(BaseModel, frozen=True):
    """V2 removes price — breaking change."""
    name: str


class ModelV2NewRequired(BaseModel, frozen=True):
    """V2 adds a required field — breaking change."""
    name: str
    price: float
    category: str  # required, no default


class ModelV1Optional(BaseModel, frozen=True):
    name: str
    tag: str = "default"


class ModelV2BecameRequired(BaseModel, frozen=True):
    """tag was optional in V1, now required — breaking."""
    name: str
    tag: str  # no default anymore


MODULE = "test_module"


@pytest.mark.build1
class TestSnapshotModel:
    """Schema snapshot creation."""

    def test_snapshot_captures_fields(self):
        snap = snapshot_model(ModelV1)
        assert snap.model_name == "ModelV1"
        field_names = {f.name for f in snap.fields}
        assert "name" in field_names
        assert "price" in field_names

    def test_snapshot_captures_required(self):
        snap = snapshot_model(ModelV2Compatible)
        by_name = {f.name: f for f in snap.fields}
        assert by_name["name"].required is True
        assert by_name["quantity"].required is False

    def test_snapshot_is_frozen(self):
        snap = snapshot_model(ModelV1)
        with pytest.raises(Exception):
            snap.model_name = "hacked"  # type: ignore[misc]


@pytest.mark.build1
class TestCompatibleChange:
    """Non-breaking changes should pass."""

    def test_identical_schemas_pass(self):
        old = snapshot_model(ModelV1)
        new = snapshot_model(ModelV1)
        results = check_compatibility(old, new, MODULE)
        assert all(r.passed for r in results)

    def test_added_optional_field_no_breaking(self):
        """Adding a field WITH a default is non-breaking."""
        old = snapshot_model(ModelV1)
        new = snapshot_model(ModelV2Compatible)
        results = check_compatibility(old, new, MODULE)
        assert all(r.passed for r in results)


@pytest.mark.build1
class TestBreakingChange:
    """Breaking changes must be detected."""

    def test_removed_field_detected(self):
        old = snapshot_model(ModelV1)
        new = snapshot_model(ModelV2Breaking)
        results = check_compatibility(old, new, MODULE)
        failed = [r for r in results if r.failed]
        assert len(failed) >= 1
        assert any("price" in r.message for r in failed)

    def test_type_change_detected(self):
        old = SchemaSnapshot(
            model_name="Foo",
            fields=(FieldSnapshot(name="val", type_str="<class 'int'>", required=True),),
        )
        new = SchemaSnapshot(
            model_name="Foo",
            fields=(FieldSnapshot(name="val", type_str="<class 'str'>", required=True),),
        )
        results = check_compatibility(old, new, MODULE)
        type_fails = [r for r in results if r.failed and "type" in r.contract.contract_name]
        assert len(type_fails) == 1

    def test_new_required_field_is_breaking(self):
        """Adding a required field (no default) breaks existing consumers."""
        old = snapshot_model(ModelV1)
        new = snapshot_model(ModelV2NewRequired)
        results = check_compatibility(old, new, MODULE)
        failed = [r for r in results if r.failed]
        assert len(failed) >= 1
        assert any("category" in r.message for r in failed)
        assert any("required" in r.message.lower() for r in failed)

    def test_optional_became_required_is_breaking(self):
        """An optional field becoming required breaks existing consumers."""
        old = snapshot_model(ModelV1Optional)
        new = snapshot_model(ModelV2BecameRequired)
        results = check_compatibility(old, new, MODULE)
        failed = [r for r in results if r.failed]
        assert len(failed) >= 1
        assert any("tag" in r.message and "required" in r.message.lower() for r in failed)
