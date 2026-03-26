"""
4.5.3 — Profile Registry: mapping of modules to Light / Complete / Common profiles.

Rules:
- COMMON modules are active in both profiles.
- LIGHT modules are active in Light and Complete.
- COMPLETE modules are active only in Complete.
- Engines C/D and paires 7-12 are FORBIDDEN in Light.
"""

from __future__ import annotations

from interface_contracts.domain_types import (
    ALL_PAIRS,
    COMPLETE_ADDITIONAL_PAIRS,
    ENGINE_PAIR_MAP,
    EngineId,
    LIGHT_PAIRS,
    ProfileId,
)
from manifest_registry.module_inventory import (
    MODULES,
    ModuleEntry,
    ProfileScope,
)


# ─── PROFILE → ALLOWED ENGINES ───────────────────────────────────────

PROFILE_ENGINES: dict[ProfileId, frozenset[EngineId]] = {
    ProfileId.LIGHT: frozenset({EngineId.A, EngineId.B}),
    ProfileId.COMPLETE: frozenset({EngineId.A, EngineId.B, EngineId.C, EngineId.D}),
}

# ─── PROFILE → ALLOWED PAIRS ─────────────────────────────────────────

PROFILE_PAIRS: dict[ProfileId, frozenset[str]] = {
    ProfileId.LIGHT: LIGHT_PAIRS,
    ProfileId.COMPLETE: ALL_PAIRS,
}


# ─── QUERY HELPERS ────────────────────────────────────────────────────


def get_modules_for_profile(profile: ProfileId) -> tuple[ModuleEntry, ...]:
    """Return all modules active in a given profile.

    - COMMON → active in both profiles
    - LIGHT → active in LIGHT and COMPLETE
    - COMPLETE → active in COMPLETE only
    """
    if profile == ProfileId.LIGHT:
        return tuple(
            m for m in MODULES
            if m.profile_scope in (ProfileScope.COMMON, ProfileScope.LIGHT)
        )
    else:  # COMPLETE
        return tuple(MODULES)  # all modules


def get_engines_for_profile(profile: ProfileId) -> frozenset[EngineId]:
    """Return allowed engines for a profile."""
    return PROFILE_ENGINES[profile]


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
    """Check if a module should be active for the given profile."""
    active = get_modules_for_profile(profile)
    return any(m.module_name == module_name for m in active)


def get_complete_only_modules() -> tuple[ModuleEntry, ...]:
    """Return modules that exist only in Complete profile."""
    return tuple(m for m in MODULES if m.profile_scope == ProfileScope.COMPLETE)


def get_complete_only_pairs() -> frozenset[str]:
    """Return pairs that only exist in Complete."""
    return COMPLETE_ADDITIONAL_PAIRS
