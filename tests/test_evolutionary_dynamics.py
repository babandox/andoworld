from math import isclose

from andoworldstate.graph import InMemoryGraph
from andoworldstate.smc import Particle, SequentialMonteCarlo
from andoworldstate.theories.evolutionary_dynamics import (
    EvolutionaryDynamicsState,
    TerritorialShiftObservation,
    death_birth_probabilities_from_graph,
    mock_territorial_shift_observation,
    step_death_birth_moran_graph,
    update_territorial_shift_weights,
)


def test_death_birth_probability_distribution_uses_fitness_times_edge_weight_from_graph():
    graph = InMemoryGraph()
    graph.add_node("province_x", ideology="FactionA", fitness=1.0)
    graph.add_node("neighbor_a", ideology="FactionA", fitness=1.0)
    graph.add_node("neighbor_b", ideology="FactionB", fitness=4.0)
    graph.add_edge("neighbor_a", "province_x", logistical_weight=10.0)
    graph.add_edge("neighbor_b", "province_x", logistical_weight=2.0)

    probabilities = death_birth_probabilities_from_graph(graph, "province_x")

    assert isclose(probabilities["neighbor_a"], 10.0 / 18.0)
    assert isclose(probabilities["neighbor_b"], 8.0 / 18.0)


def test_death_birth_graph_step_updates_collapsed_node_to_victor_ideology_and_fitness():
    graph = InMemoryGraph()
    graph.add_node("province_x", ideology="FactionA", fitness=1.0)
    graph.add_node("frontier_b", ideology="FactionB", fitness=4.0)
    graph.add_node("capital_a", ideology="FactionA", fitness=1.0)
    graph.add_edge("frontier_b", "province_x", logistical_weight=3.0)
    graph.add_edge("capital_a", "province_x", logistical_weight=1.0)

    victor = step_death_birth_moran_graph(graph, "province_x", selection_value=0.8)

    assert victor == "frontier_b"
    assert graph.node_properties("province_x")["ideology"] == "FactionB"
    assert graph.node_properties("province_x")["fitness"] == 4.0


def test_territorial_shift_smc_weights_particles_that_predict_observed_faction_b_expansion():
    observation = TerritorialShiftObservation(
        collapsed_node_id="province_x",
        observed_ideology="FactionB",
        selection_value=0.8,
        mismatch_penalty=10.0,
    )
    correct_particle = Particle(state=EvolutionaryDynamicsState(graph=faction_b_advantaged_graph()), weight=1.0)
    flawed_particle = Particle(state=EvolutionaryDynamicsState(graph=faction_a_advantaged_graph()), weight=1.0)

    update_territorial_shift_weights([correct_particle, flawed_particle], observation)

    assert correct_particle.state.graph.node_properties("province_x")["ideology"] == "FactionB"
    assert flawed_particle.state.graph.node_properties("province_x")["ideology"] == "FactionA"
    assert correct_particle.weight > flawed_particle.weight


def test_territorial_shift_weights_feed_existing_smc_normalization():
    observation = mock_territorial_shift_observation()
    particles = [
        Particle(state=EvolutionaryDynamicsState(graph=faction_b_advantaged_graph()), weight=1.0),
        Particle(state=EvolutionaryDynamicsState(graph=faction_a_advantaged_graph()), weight=1.0),
    ]
    smc = SequentialMonteCarlo(particles)

    update_territorial_shift_weights(smc.particles, observation)
    smc.normalize_weights()

    assert smc.particles[0].weight > smc.particles[1].weight
    assert sum(particle.weight for particle in smc.particles) == 1.0


def test_mock_territorial_shift_observation_represents_province_falling_to_faction_b():
    observation = mock_territorial_shift_observation()

    assert observation.collapsed_node_id == "province_x"
    assert observation.observed_ideology == "FactionB"
    assert observation.mismatch_penalty > 0


def faction_b_advantaged_graph() -> InMemoryGraph:
    graph = InMemoryGraph()
    graph.add_node("province_x", ideology="FactionA", fitness=1.0)
    graph.add_node("frontier_b", ideology="FactionB", fitness=4.0)
    graph.add_node("capital_a", ideology="FactionA", fitness=1.0)
    graph.add_edge("frontier_b", "province_x", logistical_weight=3.0)
    graph.add_edge("capital_a", "province_x", logistical_weight=1.0)
    return graph


def faction_a_advantaged_graph() -> InMemoryGraph:
    graph = InMemoryGraph()
    graph.add_node("province_x", ideology="FactionA", fitness=1.0)
    graph.add_node("frontier_b", ideology="FactionB", fitness=1.0)
    graph.add_node("capital_a", ideology="FactionA", fitness=5.0)
    graph.add_edge("frontier_b", "province_x", logistical_weight=1.0)
    graph.add_edge("capital_a", "province_x", logistical_weight=3.0)
    return graph
