"""Tests Module 2 — build_order_registry: build order coherent."""

import pytest

from manifest_registry.build_order_registry import (
    BUILD_STAGES,
    get_all_stages,
    get_build_stage,
    get_modules_in_order,
    get_next_stage,
    get_prerequisite_modules,
    validate_build_order_coherent,
    validate_modules_have_stages,
)
from manifest_registry.dependency_registry import ALLOWED_DEPENDENCIES
from manifest_registry.module_inventory import MODULES


@pytest.mark.build1
class TestBuildOrderCoherent:
    """4.14: build order coherent."""

    def test_all_stage_modules_exist_in_inventory(self):
        errors = validate_build_order_coherent()
        assert errors == [], f"Unknown modules in build stages: {errors}"

    def test_all_inventory_modules_have_stage(self):
        missing = validate_modules_have_stages()
        assert missing == [], f"Modules not in any build stage: {missing}"

    def test_stages_are_ordered(self):
        stages = get_all_stages()
        stage_numbers = [s.stage for s in stages]
        assert stage_numbers == sorted(stage_numbers), "Stages must be in order"

    def test_build1_has_6_modules(self):
        stage1 = get_build_stage(1)
        assert stage1 is not None
        assert len(stage1.modules) == 6

    def test_build1_first_module_is_interface_contracts(self):
        stage1 = get_build_stage(1)
        assert stage1 is not None
        assert stage1.modules[0] == "interface_contracts"

    def test_build1_contains_calibration_loader(self):
        stage1 = get_build_stage(1)
        assert stage1 is not None
        assert "calibration_loader" in stage1.modules

    def test_build12_exists(self):
        """Build-12 Micro-live Light must exist per V5.3 plan."""
        stage12 = get_build_stage(12)
        assert stage12 is not None
        assert stage12.name == "Micro-live Light"

    def test_build10_contains_replay_and_learning_scaffolding(self):
        stage10 = get_build_stage(10)
        assert stage10 is not None
        assert "local_replay_runtime" in stage10.modules
        assert "backtest_artifact_import" in stage10.modules
        assert "meta_learning" in stage10.modules

    def test_build2_contains_regime_classifier(self):
        stage2 = get_build_stage(2)
        assert stage2 is not None
        assert "regime_classifier" in stage2.modules

    def test_build13_exists(self):
        """Build-13 Live-Light must exist per V5.3 plan."""
        stage13 = get_build_stage(13)
        assert stage13 is not None
        assert stage13.name == "Live-Light"

    def test_build11_contains_alerting(self):
        stage11 = get_build_stage(11)
        assert stage11 is not None
        assert "alerting" in stage11.modules

    def test_build17_exists(self):
        """Build-17 UI Complete + Live-Complete must exist per V5.3 plan."""
        stage17 = get_build_stage(17)
        assert stage17 is not None
        assert stage17.name == "UI Complete + Live-Complete"

    def test_all_18_stages_present(self):
        """V5.3 plan defines 18 stages: 0-17."""
        expected = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17}
        actual = {s.stage for s in BUILD_STAGES}
        assert actual == expected, f"Missing stages: {expected - actual}"

    def test_build_11_12_13_sequential(self):
        """Shadow -> Micro-live -> Live-Light must be sequential."""
        s11 = get_build_stage(11)
        s12 = get_build_stage(12)
        s13 = get_build_stage(13)
        assert s11 is not None and s12 is not None and s13 is not None
        assert s11.stage < s12.stage < s13.stage


@pytest.mark.build1
class TestDependencyBuildOrderConsistency:
    """Dependencies must not point to a later build stage."""

    def test_deps_come_from_same_or_earlier_build(self):
        module_build = {m.module_name: m.build_stage for m in MODULES}
        violations: list[str] = []
        for src, deps in ALLOWED_DEPENDENCIES.items():
            src_stage = module_build.get(src, 99)
            for dep in deps:
                dep_stage = module_build.get(dep, 99)
                if dep_stage > src_stage:
                    violations.append(
                        f"{src}(B{src_stage}) depends on {dep}(B{dep_stage})"
                    )
        assert violations == [], f"Forward dependencies: {violations}"


@pytest.mark.build1
class TestBuildOrderQueries:
    """Test query helpers."""

    def test_get_next_stage(self):
        next_after_1 = get_next_stage(1)
        assert next_after_1 is not None
        assert next_after_1.stage > 1

    def test_get_next_stage_from_last(self):
        assert get_next_stage(17) is None

    def test_get_modules_in_order(self):
        ordered = get_modules_in_order()
        stages = [m.build_stage for m in ordered]
        assert stages == sorted(stages)

    def test_get_prerequisite_modules(self):
        prereqs = get_prerequisite_modules("data_backbone")
        assert "interface_contracts" in prereqs
        assert "manifest_registry" in prereqs
        assert "data_backbone" not in prereqs

    def test_prereqs_for_root_module(self):
        prereqs = get_prerequisite_modules("interface_contracts")
        # Build-0 has no modules, so interface_contracts has no prereqs
        assert len(prereqs) == 0

    def test_nonexistent_module_returns_empty(self):
        prereqs = get_prerequisite_modules("nonexistent")
        assert prereqs == ()

    def test_each_stage_has_name_and_description(self):
        for stage in BUILD_STAGES:
            assert len(stage.name) > 0
            assert len(stage.description) > 0
