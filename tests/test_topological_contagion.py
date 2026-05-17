from andoworldstate.graph import InMemoryGraph
from andoworldstate.smc import Particle, SequentialMonteCarlo
from andoworldstate.theories.complex_contagion import ComplexContagionAgent
from andoworldstate.theories.topological_contagion import (
    ProtestExpansionObservation,
    TopologicalContagionState,
    can_cross_complex_bridge,
    localized_protest_expansion_observation,
    run_bridge_constrained_complex_contagion,
    run_watts_cascade_until_stable,
    update_topological_contagion_weights,
)
from andoworldstate.theories.watts import WattsCascadeNode


def test_watts_cascade_ignites_vulnerable_cluster_until_stable():
    graph = InMemoryGraph()
    graph.add_edge("b", "a")
    graph.add_edge("c", "b")
    nodes = {
        "a": WattsCascadeNode("a", fractional_threshold=1.0, active_state=1),
        "b": WattsCascadeNode("b", fractional_threshold=1.0),
        "c": WattsCascadeNode("c", fractional_threshold=1.0),
    }

    steps = run_watts_cascade_until_stable(graph, nodes)

    assert steps == 2
    assert {node_id for node_id, node in nodes.items() if node.active_state == 1} == {"a", "b", "c"}


def test_complex_contagion_stalls_at_single_weak_tie_bottleneck_even_if_target_threshold_is_low():
    graph = InMemoryGraph()
    graph.add_edge("b1", "a1")
    agents = {
        "a1": ComplexContagionAgent("a1", complex_threshold=2, behavior_adopted=True),
        "b1": ComplexContagionAgent("b1", complex_threshold=1),
    }

    adopted = run_bridge_constrained_complex_contagion(
        graph,
        agents,
        source_community={"a1"},
        target_community={"b1"},
        complex_threshold=2,
    )

    assert can_cross_complex_bridge(graph, {"a1"}, {"b1"}, complex_threshold=2) is False
    assert adopted == set()
    assert agents["b1"].behavior_adopted is False


def test_complex_contagion_crosses_wide_bridge_when_width_meets_threshold():
    graph = InMemoryGraph()
    graph.add_edge("b1", "a1")
    graph.add_edge("b1", "a2")
    agents = {
        "a1": ComplexContagionAgent("a1", complex_threshold=2, behavior_adopted=True),
        "a2": ComplexContagionAgent("a2", complex_threshold=2, behavior_adopted=True),
        "b1": ComplexContagionAgent("b1", complex_threshold=2),
    }

    adopted = run_bridge_constrained_complex_contagion(
        graph,
        agents,
        source_community={"a1", "a2"},
        target_community={"b1"},
        complex_threshold=2,
    )

    assert can_cross_complex_bridge(graph, {"a1", "a2"}, {"b1"}, complex_threshold=2) is True
    assert adopted == {"b1"}
    assert agents["b1"].behavior_adopted is True


def test_topological_smc_penalizes_particles_that_jump_across_weak_ties():
    observation = ProtestExpansionObservation(
        observed_active_nodes={"a1", "a2"},
        source_community={"a1", "a2"},
        target_community={"b1"},
        complex_threshold=2,
        variance=1.0,
        weak_tie_penalty=10.0,
        missed_vulnerable_penalty=5.0,
    )
    valid_particle = Particle(state=weak_bridge_state(target_adopted=False), weight=1.0)
    jump_particle = Particle(state=weak_bridge_state(target_adopted=True), weight=1.0)

    update_topological_contagion_weights([valid_particle, jump_particle], observation)

    assert valid_particle.weight > jump_particle.weight


def test_topological_smc_penalizes_particles_that_fail_to_ignite_observed_vulnerable_cluster():
    observation = ProtestExpansionObservation(
        observed_active_nodes={"a", "b"},
        source_community={"a"},
        target_community={"b"},
        complex_threshold=2,
        variance=1.0,
        weak_tie_penalty=10.0,
        missed_vulnerable_penalty=5.0,
    )
    vulnerable_particle = Particle(state=vulnerable_cluster_state(fractional_threshold=1.0), weight=1.0)
    inert_particle = Particle(state=vulnerable_cluster_state(fractional_threshold=1.1), weight=1.0)

    update_topological_contagion_weights([vulnerable_particle, inert_particle], observation)

    assert vulnerable_particle.weight > inert_particle.weight


def test_topological_smc_weights_can_feed_existing_normalize_and_resample_loop():
    observation = ProtestExpansionObservation(
        observed_active_nodes={"a", "b"},
        source_community={"a"},
        target_community={"b"},
        complex_threshold=2,
        variance=1.0,
        weak_tie_penalty=10.0,
        missed_vulnerable_penalty=5.0,
    )
    particles = [
        Particle(state=vulnerable_cluster_state(fractional_threshold=1.0), weight=1.0),
        Particle(state=vulnerable_cluster_state(fractional_threshold=1.1), weight=1.0),
    ]
    smc = SequentialMonteCarlo(particles)

    update_topological_contagion_weights(smc.particles, observation)
    smc.normalize_weights()

    assert smc.particles[0].weight > smc.particles[1].weight
    assert sum(particle.weight for particle in smc.particles) == 1.0


def test_mock_localized_protest_expansion_observation_represents_bottleneck_scenario():
    observation = localized_protest_expansion_observation()

    assert observation.observed_active_nodes == {"district_a_1", "district_a_2", "district_a_3"}
    assert observation.source_community == {"district_a_1", "district_a_2", "district_a_3"}
    assert observation.target_community == {"district_b_1", "district_b_2"}
    assert observation.complex_threshold == 2


def weak_bridge_state(*, target_adopted: bool) -> TopologicalContagionState:
    graph = InMemoryGraph()
    graph.add_edge("b1", "a1")
    graph.add_node("a2")
    watts_nodes = {
        "a1": WattsCascadeNode("a1", fractional_threshold=1.0, active_state=1),
        "a2": WattsCascadeNode("a2", fractional_threshold=1.0, active_state=1),
        "b1": WattsCascadeNode("b1", fractional_threshold=1.0, active_state=0),
    }
    complex_agents = {
        "a1": ComplexContagionAgent("a1", complex_threshold=2, behavior_adopted=True),
        "a2": ComplexContagionAgent("a2", complex_threshold=2, behavior_adopted=True),
        "b1": ComplexContagionAgent("b1", complex_threshold=2, behavior_adopted=target_adopted),
    }
    return TopologicalContagionState(graph=graph, watts_nodes=watts_nodes, complex_agents=complex_agents)


def vulnerable_cluster_state(*, fractional_threshold: float) -> TopologicalContagionState:
    graph = InMemoryGraph()
    graph.add_edge("b", "a")
    watts_nodes = {
        "a": WattsCascadeNode("a", fractional_threshold=1.0, active_state=1),
        "b": WattsCascadeNode("b", fractional_threshold=fractional_threshold),
    }
    complex_agents = {
        "a": ComplexContagionAgent("a", complex_threshold=2, behavior_adopted=True),
        "b": ComplexContagionAgent("b", complex_threshold=2, behavior_adopted=False),
    }
    return TopologicalContagionState(graph=graph, watts_nodes=watts_nodes, complex_agents=complex_agents)
