from andoworldstate.graph import InMemoryGraph
from andoworldstate.theories.moran import MoranGeopoliticalNode, death_birth_replacement_probabilities, step_death_birth_moran


def test_moran_death_birth_probabilities_use_fitness_times_logistical_weight():
    graph = InMemoryGraph()
    graph.add_edge("a", "dead", logistical_weight=2.0)
    graph.add_edge("b", "dead", logistical_weight=1.0)
    nodes = {
        "a": MoranGeopoliticalNode("a", ideology=1, fitness=3.0),
        "b": MoranGeopoliticalNode("b", ideology=0, fitness=2.0),
        "dead": MoranGeopoliticalNode("dead", ideology=0, fitness=1.0),
    }

    probabilities = death_birth_replacement_probabilities(graph, nodes, "dead")

    assert probabilities == {"a": 0.75, "b": 0.25}


def test_moran_death_birth_step_copies_victor_ideology_and_fitness_to_collapsed_node():
    graph = InMemoryGraph()
    graph.add_edge("a", "dead", logistical_weight=2.0)
    graph.add_edge("b", "dead", logistical_weight=1.0)
    nodes = {
        "a": MoranGeopoliticalNode("a", ideology=1, fitness=3.0),
        "b": MoranGeopoliticalNode("b", ideology=0, fitness=2.0),
        "dead": MoranGeopoliticalNode("dead", ideology=0, fitness=1.0),
    }

    victor = step_death_birth_moran(graph, nodes, dead_node_id="dead", selection_value=0.1)

    assert victor == "a"
    assert nodes["dead"].ideology == 1
    assert nodes["dead"].fitness == 3.0
