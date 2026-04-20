"""Runtime mapping of modules to the declared light / complete profiles."""

from __future__ import annotations

from interface_contracts.domain_types import (
    ALL_PAIRS,
    COMPLETE_ADDITIONAL_PAIRS as governed_additional_pairs,
    EngineId,
    LIGHT_PAIRS as legacy_pairs,
    ModuleStatus,
    ProfileId,
    V53_MULTIPAIR_7,
)
from manifest_registry.module_inventory import MODULES, ModuleEntry, ProfileScope


_legacy_profile = ProfileId("light")
_governed_profile = ProfileId("complete")

PROFILE_PAIRS: dict[ProfileId, frozenset[str]] = {
    _legacy_profile: legacy_pairs,
    _governed_profile: ALL_PAIRS,
}

_ENGINE_MODULE_MAP: dict[EngineId, str] = {
    EngineId.A: "engine_a",
    EngineId.B: "engine_b",
    EngineId.C: "engine_c",
    EngineId.D: "engine_d",
}


def get_modules_for_profile(profile: ProfileId) -> tuple[ModuleEntry, ...]:
    """Return runtime-active modules for a given profile."""

    active_modules = tuple(m for m in MODULES if m.status == ModuleStatus.ACTIVE)
    if profile == _legacy_profile:
        return tuple(
            m
            for m in active_modules
            if m.profile_scope in (ProfileScope.COMMON, ProfileScope.LEGACY)
        )
    return tuple(active_modules)


def get_engines_for_profile(profile: ProfileId) -> frozenset[EngineId]:
    """Return runtime-available engines for a profile."""

    active_names = {m.module_name for m in get_modules_for_profile(profile)}
    return frozenset(
        engine
        for engine, module_name in _ENGINE_MODULE_MAP.items()
        if module_name in active_names
    )


PROFILE_ENGINES: dict[ProfileId, frozenset[EngineId]] = {
    profile: get_engines_for_profile(profile)
    for profile in ProfileId
}


def get_pairs_for_profile(profile: ProfileId) -> frozenset[str]:
    """Return allowed pairs for a profile."""

    return PROFILE_PAIRS[profile]


def is_engine_allowed(engine: EngineId, profile: ProfileId) -> bool:
    """Check if an engine is allowed in a given profile."""

    return engine in PROFILE_ENGINES[profile]


def is_pair_allowed(pair: str, profile: ProfileId) -> bool:
    """Check if a pair is allowed in a given profile."""

    return pair in PROFILE_PAIRS[profile]


def is_module_active_in_profile(module_name: str, profile: ProfileId) -> bool:
    """Check if a module is runtime-active for the given profile."""

    active = get_modules_for_profile(profile)
    return any(m.module_name == module_name for m in active)


def get_complete_only_modules() -> tuple[ModuleEntry, ...]:
    """Return declared modules that are reserved to the governed profile."""

    return tuple(m for m in MODULES if m.profile_scope == ProfileScope.GOVERNED)


def get_complete_only_pairs() -> frozenset[str]:
    """Return pairs that only exist in the governed profile."""

    return governed_additional_pairs


def get_multipair7_universe() -> frozenset[str]:
    """Return the Phase-1 V5.3 multi-pair trading universe (7 canonical pairs)."""

    return V53_MULTIPAIR_7
