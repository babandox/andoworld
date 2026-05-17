from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass
from math import exp
from random import Random

from andoworldstate.graph import InMemoryGraph
from andoworldstate.smc import Particle


@dataclass
class EvolutionaryDynamicsState:
    graph: InMemoryGraph


@dataclass(frozen=True)
class TerritorialShiftObservation:
    collapsed_node_id: Hashable
    observed_ideology: str
    selection_value: float
    mismatch_penalty: float

    def __post_init__(self) -> None:
        if not 0 <= self.selection_value < 1:
            raise ValueError("selection_value must be in the half-open interval [0, 1)")
        if self.mismatch_penalty < 0:
            raise ValueError("mismatch_penalty must be non-negative")


def mock_territorial_shift_observation() -> TerritorialShiftObservation:
    return TerritorialShiftObservation(
        collapsed_node_id="province_x",
        observed_ideology="FactionB",
        selection_value=0.8,
        mismatch_penalty=10.0,
    )


def death_birth_probabilities_from_graph(
    graph: InMemoryGraph,
    collapsed_node_id: Hashable,
    *,
    fitness_property: str = "fitness",
    edge_weight_property: str = "logistical_weight",
) -> dict[Hashable, float]:
    competitors = graph.predecessors(collapsed_node_id)
    if not competitors:
        raise ValueError("collapsed node must have competing neighbors")

    pressures = {}
    for competitor_id in competitors:
        properties = graph.node_properties(competitor_id)
        if fitness_property not in properties:
            raise ValueError(f"Competitor node lacks {fitness_property!r}: {competitor_id!r}")
        fitness = float(properties[fitness_property])
        edge_weight = float(graph.edge_property(competitor_id, collapsed_node_id, edge_weight_property, 1.0))
        pressures[competitor_id] = fitness * edge_weight

    denominator = sum(pressures.values())
    if denominator <= 0:
        raise ValueError("replacement denominator must be positive")
    return {node_id: pressure / denominator for node_id, pressure in pressures.items()}


def step_death_birth_moran_graph(
    graph: InMemoryGraph,
    collapsed_node_id: Hashable,
    *,
    selection_value: float | None = None,
    rng: Random | None = None,
) -> Hashable:
    if selection_value is None:
        selection_value = (rng or Random()).random()
    if not 0 <= selection_value < 1:
        raise ValueError("selection_value must be in the half-open interval [0, 1)")

    probabilities = death_birth_probabilities_from_graph(graph, collapsed_node_id)
    victor_id = _select_victor(probabilities, selection_value)
    victor_properties = graph.node_properties(victor_id)
    graph.set_node_property(collapsed_node_id, "ideology", victor_properties["ideology"])
    graph.set_node_property(collapsed_node_id, "fitness", victor_properties["fitness"])
    return victor_id


def update_territorial_shift_weights(
    particles: list[Particle],
    observation: TerritorialShiftObservation,
) -> None:
    for particle in particles:
        state = _evolutionary_state(particle)
        probabilities = death_birth_probabilities_from_graph(state.graph, observation.collapsed_node_id)
        victor_id = step_death_birth_moran_graph(
            state.graph,
            observation.collapsed_node_id,
            selection_value=observation.selection_value,
        )
        predicted_ideology = state.graph.node_properties(observation.collapsed_node_id)["ideology"]
        likelihood = max(probabilities[victor_id], 1e-12)
        if predicted_ideology != observation.observed_ideology:
            likelihood *= exp(-observation.mismatch_penalty)
        particle.weight *= likelihood


def _select_victor(probabilities: dict[Hashable, float], selection_value: float) -> Hashable:
    cumulative = 0.0
    victor_id = next(reversed(probabilities))
    for node_id, probability in probabilities.items():
        cumulative += probability
        if selection_value <= cumulative:
            return node_id
    return victor_id


def _evolutionary_state(particle: Particle) -> EvolutionaryDynamicsState:
    if isinstance(particle.state, EvolutionaryDynamicsState):
        return particle.state
    raise ValueError("particle state must be EvolutionaryDynamicsState")
