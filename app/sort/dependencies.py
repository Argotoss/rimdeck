from collections.abc import Iterable

from app.utils.constants import KNOWN_MOD_REPLACEMENTS


def dependency_satisfied(
    dependency: str,
    alternatives: Iterable[str],
    present: set[str],
    use_alternatives: bool,
) -> bool:
    """Decide whether a mod's dependency is met by the mods in ``present``.

    This is the single rule used by the mod list, the Sort dependency check
    and the dependency dialog, so they can't disagree.

    :param dependency: Package ID the mod depends on.
    :param alternatives: The dependency's ``alternativePackageIds``.
    :param present: Package IDs that count as available.
    :param use_alternatives: Whether alternative package IDs satisfy it.
    :return: True if the dependency, an allowed alternative, or a known
        replacement (e.g. Prepatcher for Harmony) is present.
    """
    if dependency in present:
        return True
    if use_alternatives and any(alt in present for alt in alternatives):
        return True
    return any(
        replacement in present
        for replacement in KNOWN_MOD_REPLACEMENTS.get(dependency, set())
    )


def extract_tier_subgraph(
    full_graph: dict[str, set[str]],
    tier_mods: set[str],
) -> dict[str, set[str]]:
    """Extract a subgraph containing only edges between mods in ``tier_mods``.

    Every mod in ``tier_mods`` gets an entry in the result, even if it has
    no edges in ``full_graph``.
    """
    return {mod_id: full_graph.get(mod_id, set()) & tier_mods for mod_id in tier_mods}


def get_dependencies_recursive(
    package_id: str,
    active_mods_dependencies: dict[str, set[str]],
    processed_ids: set[str],
) -> set[str]:
    dependencies_set: set[str] = set()
    if package_id in active_mods_dependencies:
        for dependency_id in active_mods_dependencies[package_id]:
            if dependency_id not in processed_ids:
                processed_ids.add(dependency_id)
                dependencies_set.add(dependency_id)
                dependencies_set.update(
                    get_dependencies_recursive(
                        dependency_id, active_mods_dependencies, processed_ids
                    )
                )
    return dependencies_set


def get_reverse_dependencies_recursive(
    package_id: str,
    active_mods_rev_dependencies: dict[str, set[str]],
    processed_ids: set[str],
) -> set[str]:
    reverse_dependencies_set: set[str] = set()
    if package_id in active_mods_rev_dependencies:
        for dependent_id in active_mods_rev_dependencies[package_id]:
            if dependent_id not in processed_ids:
                processed_ids.add(dependent_id)
                reverse_dependencies_set.add(dependent_id)
                reverse_dependencies_set.update(
                    get_reverse_dependencies_recursive(
                        dependent_id, active_mods_rev_dependencies, processed_ids
                    )
                )
    return reverse_dependencies_set
