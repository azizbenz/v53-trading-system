"""
manifest_registry — Module 2: Registre unique des modules V5.3.

Public API for querying the manifest: modules, dependencies, profiles, build order, versions.

Dependencies: interface_contracts, stdlib, pydantic
"""

from manifest_registry.module_inventory import (
    MODULES,
    ModuleEntry,
    Owner,
    Priority,
    ProfileScope,
    get_all_modules,
    get_module,
    get_module_names,
    get_modules_by_build,
    get_modules_by_layer,
    get_modules_by_profile,
    get_modules_by_status,
    validate_no_duplicates,
)
from manifest_registry.dependency_registry import (
    ALLOWED_DEPENDENCIES,
    get_allowed_dependencies,
    get_dependents,
    is_dependency_allowed,
    validate_all_modules_registered,
    validate_no_self_dependency,
    validate_no_unknown_targets,
)
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
from manifest_registry.build_order_registry import (
    BUILD_STAGES,
    BuildStage,
    get_all_stages,
    get_build_stage,
    get_modules_in_order,
    get_next_stage,
    get_prerequisite_modules,
    validate_build_order_coherent,
    validate_modules_have_stages,
)
from manifest_registry.version_registry import (
    MANIFEST_VERSION,
    ChangeType,
    ManifestChange,
    ManifestDiff,
    ManifestSnapshot,
    ModuleSnapshot,
    build_current_snapshot,
    diff_snapshots,
    get_changelog,
    get_changes_since,
    get_manifest_version,
)

__all__ = [
    # Module inventory
    "MODULES",
    "ModuleEntry",
    "Owner",
    "Priority",
    "ProfileScope",
    "get_all_modules",
    "get_module",
    "get_module_names",
    "get_modules_by_build",
    "get_modules_by_layer",
    "get_modules_by_profile",
    "get_modules_by_status",
    "validate_no_duplicates",
    # Dependencies
    "ALLOWED_DEPENDENCIES",
    "get_allowed_dependencies",
    "get_dependents",
    "is_dependency_allowed",
    "validate_all_modules_registered",
    "validate_no_self_dependency",
    "validate_no_unknown_targets",
    # Profiles
    "PROFILE_ENGINES",
    "PROFILE_PAIRS",
    "get_complete_only_modules",
    "get_complete_only_pairs",
    "get_engines_for_profile",
    "get_modules_for_profile",
    "get_pairs_for_profile",
    "is_engine_allowed",
    "is_module_active_in_profile",
    "is_pair_allowed",
    # Build order
    "BUILD_STAGES",
    "BuildStage",
    "get_all_stages",
    "get_build_stage",
    "get_modules_in_order",
    "get_next_stage",
    "get_prerequisite_modules",
    "validate_build_order_coherent",
    "validate_modules_have_stages",
    # Versioning & diff
    "MANIFEST_VERSION",
    "ChangeType",
    "ManifestChange",
    "ManifestDiff",
    "ManifestSnapshot",
    "ModuleSnapshot",
    "build_current_snapshot",
    "diff_snapshots",
    "get_changelog",
    "get_changes_since",
    "get_manifest_version",
]
