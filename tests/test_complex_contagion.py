from andoworldstate.graph import InMemoryGraph
from andoworldstate.theories.complex_contagion import (
    ComplexContagionAgent,
    analyze_bridge_width_constraint,
    step_complex_contagion,
)


def test_complex_contagion_requires_redundant_active_signals_to_adopt_behavior():
    graph = InMemoryGraph()
    graph.add_edge("target", "a")
    graph.add_edge("target", "b")
    graph.add_edge("target", "c")
    agents = {
        "target": ComplexContagionAgent("target", complex_threshold=2),
        "a": ComplexContagionAgent("a", complex_threshold=2, behavior_adopted=True),
        "b": ComplexContagionAgent("b", complex_threshold=2, behavior_adopted=True),
        "c": ComplexContagionAgent("c", complex_threshold=2, behavior_adopted=False),
    }

    step_complex_contagion(graph, agents)

    assert agents["target"].behavior_adopted is True


def test_complex_contagion_single_weak_tie_fails_when_threshold_is_greater_than_one():
    graph = InMemoryGraph()
    graph.add_edge("target", "a")
    agents = {
        "target": ComplexContagionAgent("target", complex_threshold=2),
        "a": ComplexContagionAgent("a", complex_threshold=2, behavior_adopted=True),
    }

    step_complex_contagion(graph, agents)

    assert agents["target"].behavior_adopted is False


def test_bridge_width_constraint_counts_edges_between_communities():
    graph = InMemoryGraph()
    graph.add_edge("a1", "b1")
    graph.add_edge("a2", "b1")
    graph.add_edge("b2", "a1")

    width = analyze_bridge_width_constraint(graph, {"a1", "a2"}, {"b1", "b2"})

    assert width == 3
