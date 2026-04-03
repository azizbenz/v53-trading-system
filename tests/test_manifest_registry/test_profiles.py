"""Tests Module 2 - profile_registry: runtime profile activation is coherent."""

import pytest

from interface_contracts.domain_types import EngineId, ModuleStatus, ProfileId
from manifest_registry.profile_registry import (
    PROFILE_ENGINES,
    PROFILE_PAIRS,
    get_complete_only_modules,
    get_complete_only_pairs,
    get_engines_for_profile,
    get_modules_for_profile,
    get_pairs_for_profile,
    is_engine_allowed,
    is_module_active_in_profile,
    is_pair_allowed,
)


@pytest.mark.build1
class TestProfilValide:
    """Profile pair/engine exposure should match the current runtime surface."""

    def test_light_has_6_pairs(self):
        pairs = get_pairs_for_profile(ProfileId.LIGHT)
        assert len(pairs) == 6

    def test_complete_has_12_pairs(self):
        pairs = get_pairs_for_profile(ProfileId.COMPLETE)
        assert len(pairs) == 12

    def test_light_pairs_subset_of_complete(self):
        light = get_pairs_for_profile(ProfileId.LIGHT)
        complete = get_pairs_for_profile(ProfileId.COMPLETE)
        assert light.issubset(complete)

    def test_light_engines_match_full_shadow_runtime_surface(self):
        engines = get_engines_for_profile(ProfileId.LIGHT)
        assert engines == frozenset({EngineId.A, EngineId.B, EngineId.C, EngineId.D})

    def test_complete_runtime_engines_match_active_manifest(self):
        engines = get_engines_for_profile(ProfileId.COMPLETE)
        assert engines == frozenset({EngineId.A, EngineId.B, EngineId.C, EngineId.D})


@pytest.mark.build1
class TestEngineVisibility:
    """Full Shadow migration exposes all four engines on the runtime surface."""

    def test_engine_c_in_light(self):
        assert is_engine_allowed(EngineId.C, ProfileId.LIGHT)

    def test_engine_d_in_light(self):
        assert is_engine_allowed(EngineId.D, ProfileId.LIGHT)

    def test_engine_a_in_light(self):
        assert is_engine_allowed(EngineId.A, ProfileId.LIGHT)

    def test_engine_b_in_light(self):
        assert is_engine_allowed(EngineId.B, ProfileId.LIGHT)

    def test_engine_c_in_complete(self):
        assert is_engine_allowed(EngineId.C, ProfileId.COMPLETE)

    def test_engine_d_in_complete(self):
        assert is_engine_allowed(EngineId.D, ProfileId.COMPLETE)


@pytest.mark.build1
class TestPairsForbiddenInLight:
    """Complete-only pairs are not in Light."""

    def test_complete_only_pairs_not_in_light(self):
        complete_only = get_complete_only_pairs()
        light_pairs = get_pairs_for_profile(ProfileId.LIGHT)
        for pair in complete_only:
            assert pair not in light_pairs, f"{pair} should not be in Light"

    def test_complete_only_pairs_count(self):
        complete_only = get_complete_only_pairs()
        assert len(complete_only) == 6

    def test_pair_helper_uses_profile_pairs(self):
        for pair in PROFILE_PAIRS[ProfileId.LIGHT]:
            assert is_pair_allowed(pair, ProfileId.LIGHT)


@pytest.mark.build1
class TestModuleProfileMapping:
    """Only ACTIVE modules should be runtime-visible."""

    def test_common_modules_in_light(self):
        light_mods = get_modules_for_profile(ProfileId.LIGHT)
        light_names = {m.module_name for m in light_mods}
        assert "interface_contracts" in light_names
        assert "manifest_registry" in light_names

    def test_light_runtime_includes_build10_observability_only(self):
        light_names = {m.module_name for m in get_modules_for_profile(ProfileId.LIGHT)}
        assert "portfolio" in light_names
        assert "meta" in light_names
        assert "meta_learning" in light_names
        assert "protocols" in light_names
        assert "monitoring" in light_names
        assert "ui" in light_names
        assert "local_replay_runtime" in light_names
        assert "backtest_artifact_import" in light_names

    def test_complete_runtime_includes_active_complete_only_modules(self):
        complete_names = {m.module_name for m in get_modules_for_profile(ProfileId.COMPLETE)}
        assert "meta_learning" in complete_names
        assert "protocols" in complete_names
        assert "monitoring" in complete_names
        assert "ui" in complete_names
        assert "local_replay_runtime" in complete_names
        assert "backtest_artifact_import" in complete_names
        assert "complete_enablers" in complete_names
        assert "engine_c" in complete_names
        assert "engine_d" in complete_names

    def test_complete_only_modules_are_declared_and_runtime_active_when_implemented(self):
        complete_only = get_complete_only_modules()
        assert {m.module_name for m in complete_only} == {
            "complete_enablers",
            "engine_c",
            "engine_d",
        }
        for m in complete_only:
            assert m.status == ModuleStatus.ACTIVE
            assert is_module_active_in_profile(m.module_name, ProfileId.LIGHT)
            assert is_module_active_in_profile(m.module_name, ProfileId.COMPLETE)

    def test_light_modules_also_in_complete(self):
        light = {m.module_name for m in get_modules_for_profile(ProfileId.LIGHT)}
        complete = {m.module_name for m in get_modules_for_profile(ProfileId.COMPLETE)}
        assert light.issubset(complete)

    def test_profile_engines_constant_matches_helper(self):
        for profile in ProfileId:
            assert PROFILE_ENGINES[profile] == get_engines_for_profile(profile)
