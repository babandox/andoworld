from andoworldstate.graph import InMemoryGraph
from andoworldstate.theories.watts import WattsCascadeNode, is_vulnerable, particle_filter_cascade_culling, step_watts_cascade


class Particle:
    def __init__(self, agents):
        self.agents = agents
        self.variance = 4.0
        self.weight = 1.0


def test_watts_node_activates_when_active_neighbor_fraction_meets_threshold():
    graph = InMemoryGraph()
    graph.add_edge("a", "b")
    graph.add_edge("a", "c")
    nodes = {
        "a": WattsCascadeNode("a", fractional_threshold=0.5),
        "b": WattsCascadeNode("b", fractional_threshold=1.0, active_state=1),
        "c": WattsCascadeNode("c", fractional_threshold=1.0, active_state=0),
    }

    step_watts_cascade(graph, nodes)

    assert nodes["a"].active_state == 1


def test_watts_vulnerable_node_condition_matches_single_neighbor_activation_rule():
    assert is_vulnerable(degree=4, fractional_threshold=0.25)
    assert not is_vulnerable(degree=4, fractional_threshold=0.26)


def test_watts_particle_weight_uses_gaussian_kernel_over_cascade_size_error():
    particle = Particle([WattsCascadeNode("a", 0.5, 1), WattsCascadeNode("b", 0.5, 0)])

    particle_filter_cascade_culling([particle], real_time_protest_size=3)

    assert particle.weight == 2.718281828459045 ** (-0.5 * (2**2) / 4.0)
