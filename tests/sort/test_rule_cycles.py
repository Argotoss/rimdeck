"""Rule loops are found compactly and never stop the rest of the sort."""

import random
import time

from toposort import toposort

from app.sort.topo_sort import (
    find_rule_cycles,
    shortest_cycle,
    strongly_connected_components,
    topological_levels,
)


def test_acyclic_levels_match_toposort() -> None:
    rng = random.Random(7)
    for _ in range(200):
        nodes = [f"m{i}" for i in range(rng.randint(1, 30))]
        graph = {
            node: {dep for dep in nodes[:index] if rng.random() < 0.15}
            for index, node in enumerate(nodes)
        }
        assert topological_levels(graph) == list(toposort(graph))


def test_components_group_only_the_loop() -> None:
    graph = {"a": {"b"}, "b": {"a"}, "c": {"a"}, "d": set()}
    components = strongly_connected_components(graph)
    assert sorted(components) == [["a", "b"], ["c"], ["d"]]


def test_loop_lands_after_its_dependencies_and_before_dependents() -> None:
    graph = {"a": {"b", "base"}, "b": {"a"}, "top": {"a"}, "base": set()}
    assert topological_levels(graph) == [{"base"}, {"a", "b"}, {"top"}]


def test_self_dependency_is_not_a_loop() -> None:
    assert find_rule_cycles({"a": {"a"}, "b": {"a"}}) == []


def test_shortest_cycle_is_reported() -> None:
    graph = {"a": {"b"}, "b": {"c", "a"}, "c": {"a"}}
    assert shortest_cycle(graph, ["a", "b", "c"]) == ["a", "b"]


def test_dense_loop_reports_one_cycle_quickly() -> None:
    # Nine mods that all load after each other used to produce 125,664 cycles.
    nodes = [f"m{i}" for i in range(9)]
    graph = {node: set(nodes) - {node} for node in nodes}
    start = time.perf_counter()
    cycles = find_rule_cycles(graph)
    assert time.perf_counter() - start < 1
    assert len(cycles) == 1
    assert len(cycles[0]) == 2
