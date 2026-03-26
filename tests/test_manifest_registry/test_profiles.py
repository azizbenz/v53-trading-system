"""Tests Module 2 — profile_registry: profil Light/Complete valide."""

import pytest

from interface_contracts.domain_types import EngineId, ProfileId, LIGHT_PAIRS, ALL_PAIRS
from manifest_registry.module_inventory import ProfileScope
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
    """4.14: profil valide."""

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

    def test_light_engines_a_b_only(self):
        engines = get_engines_for_profile(ProfileId.LIGHT)
        assert engines == frozenset({EngineId.A, EngineId.B})

    def test_complete_engines_a_b_c_d(self):
        engines = get_engines_for_profile(ProfileId.COMPLETE)
        assert engines == frozenset({EngineId.A, EngineId.B, EngineId.C, EngineId.D})


@pytest.mark.build1
class TestEngineForbiddenInLight:
    """Engines C/D are FORBIDDEN in Light."""

    def test_engine_c_not_in_light(self):
        assert not is_engine_allowed(EngineId.C, ProfileId.LIGHT)

    def test_engine_d_not_in_light(self):
        assert not is_engine_allowed(EngineId.D, ProfileId.LIGHT)

    def test_engine_a_in_light(self):
        assert is_engine_allowed(EngineId.A, ProfileId.LIGHT)

    def test_engine_b_in_light(self):
        assert is_engine_allowed(EngineId.B, ProfileId.LIGHT)

    def test_all_engines_in_complete(self):
        for e in EngineId:
            assert is_engine_allowed(e, ProfileId.COMPLETE)


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


@pytest.mark.build1
class TestModuleProfileMapping:
    """Modules correctly mapped to profiles."""

    def test_common_modules_in_light(self):
        light_mods = get_modules_for_profile(ProfileId.LIGHT)
        light_names = {m.module_name for m in light_mods}
        assert "interface_contracts" in light_names
        assert "manifest_registry" in light_names

    def test_common_modules_in_complete(self):
        complete_mods = get_modules_for_profile(ProfileId.COMPLETE)
        complete_names = {m.module_name for m in complete_mods}
        assert "interface_contracts" in complete_names

    def test_complete_only_modules_not_in_light(self):
        complete_only = get_complete_only_modules()
        for m in complete_only:
            assert not is_module_active_in_profile(m.module_name, ProfileId.LIGHT), (
                f"{m.module_name} should not be active in Light"
            )

    def test_complete_only_modules_in_complete(self):
        complete_only = get_complete_only_modules()
        for m in complete_only:
            assert is_module_active_in_profile(m.module_name, ProfileId.COMPLETE)

    def test_light_modules_also_in_complete(self):
        """Light modules should be a subset of Complete modules."""
        light = {m.module_name for m in get_modules_for_profile(ProfileId.LIGHT)}
        complete = {m.module_name for m in get_modules_for_profile(ProfileId.COMPLETE)}
        assert light.issubset(complete)
