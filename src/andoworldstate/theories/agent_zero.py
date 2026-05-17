from __future__ import annotations

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from math import exp, pi, sqrt
from typing import Any

from andoworldstate.graph import InMemoryGraph


@dataclass
class AgentZero:
    unique_id: Hashable
    learning_rate_alpha: float
    salience_beta: float
    activation_threshold_tau: float
    affect_v: float = 0.0
    cognition_p: float = 0.0
    action: int = 0

    def step_rescorla_wagner(self, environmental_threat_lambda: float) -> None:
        self.affect_v = self.affect_v + (
            self.learning_rate_alpha * self.salience_beta * (environmental_threat_lambda - self.affect_v)
        )

    def calculate_social_contagion(self, graph: InMemoryGraph, agents: Mapping[Hashable, "AgentZero"]) -> float:
        social_s = 0.0
        for neighbor_id in graph.neighbors(self.unique_id):
            neighbor = agents[neighbor_id]
            omega = graph.edge_property(self.unique_id, neighbor_id, "omega", 0.0)
            social_s += omega * (neighbor.affect_v + neighbor.cognition_p)
        return social_s

    def step(
        self,
        graph: InMemoryGraph,
        agents: Mapping[Hashable, "AgentZero"],
        *,
        environmental_threat_lambda: float,
        local_risk: float,
    ) -> None:
        self.step_rescorla_wagner(environmental_threat_lambda)
        self.cognition_p = local_risk
        disposition = self.affect_v + self.cognition_p + self.calculate_social_contagion(graph, agents)
        self.action = 1 if disposition > self.activation_threshold_tau else 0


def gaussian_likelihood(*, observed: float, mean: float, standard_deviation: float) -> float:
    if standard_deviation <= 0:
        raise ValueError("standard_deviation must be positive")
    z_score = (observed - mean) / standard_deviation
    return (1.0 / (standard_deviation * sqrt(2.0 * pi))) * exp(-0.5 * z_score * z_score)


def update_particle_weight(particle_model: Any, real_world_protest_volume: float) -> None:
    agents = _particle_agents(particle_model)
    simulated_volume = sum(agent.action for agent in agents)
    likelihood = gaussian_likelihood(
        observed=real_world_protest_volume,
        mean=simulated_volume,
        standard_deviation=particle_model.variance_param,
    )
    particle_model.weight *= likelihood


def _particle_agents(particle_model: Any) -> Sequence[AgentZero]:
    if hasattr(particle_model, "agents"):
        return particle_model.agents
    if hasattr(particle_model, "schedule") and hasattr(particle_model.schedule, "agents"):
        return particle_model.schedule.agents
    raise ValueError("particle_model must expose agents or schedule.agents")

