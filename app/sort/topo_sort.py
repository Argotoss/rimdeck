from collections import deque
from collections.abc import Mapping

from loguru import logger

from app.models.metadata.metadata_structure import AboutXmlMod, ListedMod


def _without_self_edges(graph: Mapping[str, set[str]]) -> dict[str, set[str]]:
    """Return the graph with every node present and self-dependencies removed."""
    nodes = set(graph) | {dep for deps in graph.values() for dep in deps}
    return {node: set(graph.get(node, set())) - {node} for node in nodes}


def strongly_connected_components(graph: Mapping[str, set[str]]) -> list[list[str]]:
    """Find strongly connected components with an iterative Tarjan search.

    Nodes and edges are visited in sorted order so the result is the same on
    every run.

    :param graph: node -> set of nodes it depends on.
    :return: Components, each a sorted list of nodes.
    """
    index: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    components: list[list[str]] = []
    counter = 0

    for root in sorted(graph):
        if root in index:
            continue
        work: list[tuple[str, list[str], int]] = [(root, sorted(graph[root]), 0)]
        index[root] = lowlink[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)
        while work:
            node, neighbours, position = work[-1]
            if position < len(neighbours):
                work[-1] = (node, neighbours, position + 1)
                child = neighbours[position]
                if child not in index:
                    index[child] = lowlink[child] = counter
                    counter += 1
                    stack.append(child)
                    on_stack.add(child)
                    work.append((child, sorted(graph[child]), 0))
                elif child in on_stack:
                    lowlink[node] = min(lowlink[node], index[child])
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                lowlink[parent] = min(lowlink[parent], lowlink[node])
            if lowlink[node] == index[node]:
                component: list[str] = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    component.append(member)
                    if member == node:
                        break
                components.append(sorted(component))
    return components


def shortest_cycle(graph: Mapping[str, set[str]], members: list[str]) -> list[str]:
    """Return one shortest cycle through a strongly connected component.

    :param graph: node -> set of nodes it depends on (no self-edges).
    :param members: Nodes of one component with more than one node.
    :return: Nodes of the cycle in dependency order; each depends on the next,
        and the last depends on the first.
    """
    inside = set(members)
    best: list[str] = []
    for start in members:
        previous: dict[str, str] = {}
        queue = deque([start])
        found = False
        while queue and not found:
            node = queue.popleft()
            for child in sorted(graph[node] & inside):
                if child == start:
                    path = [node]
                    while path[-1] != start:
                        path.append(previous[path[-1]])
                    cycle = list(reversed(path))
                    if not best or len(cycle) < len(best):
                        best = cycle
                    found = True
                    break
                if child not in previous:
                    previous[child] = node
                    queue.append(child)
    return best


def find_rule_cycles(dependency_graph: Mapping[str, set[str]]) -> list[list[str]]:
    """Return one shortest cycle for every group of mods whose rules loop.

    :param dependency_graph: package_id -> set of dependency package_ids
    :return: Cycles as lists of package IDs; each loads after the next, and
        the last loads after the first.
    """
    graph = _without_self_edges(dependency_graph)
    return [
        shortest_cycle(graph, component)
        for component in strongly_connected_components(graph)
        if len(component) > 1
    ]


def topological_levels(dependency_graph: Mapping[str, set[str]]) -> list[set[str]]:
    """Group package IDs into levels where each depends only on earlier levels.

    Mods whose rules form a loop can't be ordered among themselves, so each
    loop is placed as one unit: every member lands in the same level, after
    everything the loop depends on and before everything that depends on it.

    :param dependency_graph: package_id -> set of dependency package_ids
    :return: Levels in load order.
    """
    graph = _without_self_edges(dependency_graph)
    components = strongly_connected_components(graph)
    component_of = {
        member: number
        for number, component in enumerate(components)
        for member in component
    }
    depends_on: dict[int, set[int]] = {
        number: {
            component_of[dep]
            for member in component
            for dep in graph[member]
            if component_of[dep] != number
        }
        for number, component in enumerate(components)
    }

    levels: list[set[str]] = []
    placed: set[int] = set()
    remaining = set(depends_on)
    while remaining:
        ready = {number for number in remaining if depends_on[number] <= placed}
        levels.append({member for number in ready for member in components[number]})
        placed |= ready
        remaining -= ready
    return levels


def do_topo_sort(
    dependency_graph: dict[str, set[str]],
    active_mod_paths: set[str],
    mods_metadata: Mapping[str, ListedMod],
) -> list[str]:
    """Sort mods using the topological sort algorithm.

    For each topological level, sort the mods alphabetically by name
    for consistency. Mods caught in a rule loop share one level and are
    ordered alphabetically like the rest; :func:`find_rule_cycles` reports
    the loops.

    :param dependency_graph: package_id -> set of dependency package_ids
    :param active_mod_paths: Set of mod paths (identifiers) to sort
    :param mods_metadata: path -> ListedMod mapping for name lookups
    :return: Sorted list of mod paths
    """
    logger.info(f"Initializing toposort for {len(dependency_graph)} mods")

    sorted_dependencies = topological_levels(dependency_graph)

    packageid_to_paths: dict[str, list[str]] = {}
    path_to_name: dict[str, str] = {}

    for path in active_mod_paths:
        mod = mods_metadata.get(path)
        if not isinstance(mod, AboutXmlMod):
            logger.warning(f"Missing or non-AboutXmlMod for path {path}, skipping")
            continue
        pid = str(mod.package_id)
        packageid_to_paths.setdefault(pid, []).append(path)
        name = mod.name if isinstance(mod.name, str) else "name error in mod about.xml"
        path_to_name[path] = name

    def safe_name(name: object) -> str:
        if isinstance(name, str):
            return name.lower()
        return "name error in mod about.xml"

    reordered: list[str] = []
    for level in sorted_dependencies:
        temp_mod_list = [
            path
            for package_id in level
            for path in packageid_to_paths.get(package_id, [])
        ]
        # Duplicate copies of one package ID share a name; the path keeps
        # their relative order stable.
        sorted_temp = sorted(
            temp_mod_list,
            key=lambda p: (safe_name(path_to_name.get(p)), p),
        )
        reordered.extend(sorted_temp)

    logger.info(f"Finished Toposort sort with {len(reordered)} mods")
    return reordered
