from math import isclose

from andoworldstate.graph import InMemoryGraph
from andoworldstate.theories.agent_zero import AgentZero, gaussian_likelihood, update_particle_weight


class ParticleModel:
    def __init__(self, agents, variance_param=2.0):
        self.agents = agents
        self.variance_param = variance_param
        self.weight = 1.0


def test_agent_zero_updates_affect_with_rescorla_wagner_equation():
    agent = AgentZero(unique_id="a", learning_rate_alpha=0.5, salience_beta=0.25, activation_threshold_tau=1.0)

    agent.step_rescorla_wagner(environmental_threat_lambda=0.8)

    assert isclose(agent.affect_v, 0.1)


def test_agent_zero_social_contagion_uses_neighbor_affect_and_cognition_weighted_by_omega():
    graph = InMemoryGraph()
    graph.add_edge("a", "b", omega=0.2)
    graph.add_edge("a", "c", omega=0.5)
    agents = {
        "b": AgentZero("b", 0.1, 0.1, 1.0, affect_v=0.4, cognition_p=0.1),
        "c": AgentZero("c", 0.1, 0.1, 1.0, affect_v=0.2, cognition_p=0.6),
    }
    agent = AgentZero("a", 0.1, 0.1, 1.0)

    contagion = agent.calculate_social_contagion(graph, agents)

    assert isclose(contagion, 0.2 * 0.5 + 0.5 * 0.8)


def test_agent_zero_step_triggers_action_when_total_disposition_exceeds_threshold():
    graph = InMemoryGraph()
    graph.add_edge("a", "b", omega=1.0)
    agents = {
        "a": AgentZero("a", 1.0, 1.0, 0.75),
        "b": AgentZero("b", 0.1, 0.1, 1.0, affect_v=0.1, cognition_p=0.1),
    }

    agents["a"].step(graph, agents, environmental_threat_lambda=0.4, local_risk=0.2)

    assert agents["a"].action == 1


def test_agent_zero_particle_weight_uses_gaussian_likelihood_against_observed_protest_volume():
    particle = ParticleModel(
        [
            AgentZero("a", 0.1, 0.1, 1.0, action=1),
            AgentZero("b", 0.1, 0.1, 1.0, action=0),
            AgentZero("c", 0.1, 0.1, 1.0, action=1),
        ],
        variance_param=2.0,
    )

    update_particle_weight(particle, real_world_protest_volume=3)

    assert isclose(particle.weight, gaussian_likelihood(observed=3, mean=2, standard_deviation=2.0))
