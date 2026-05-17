from __future__ import annotations

from collections.abc import Hashable, MutableMapping
from dataclasses import dataclass
from random import Random

from andoworldstate.graph import InMemoryGraph


@dataclass
class MoranGeopoliticalNode:
    unique_id: Hashable
    ideology: int
    fitness: float


def death_birth_replacement_probabilities(
    graph: InMemoryGraph,
    nodes: MutableMapping[Hashable, MoranGeopoliticalNode],
    dead_node_id: Hashable,
) -> dict[Hashable, float]:
    competitors = [node_id for node_id in graph.predecessors(dead_node_id) if node_id in nodes]
    if not competitors:
        raise ValueError("dead node must have competing neighbors")

    pressures = {
        node_id: nodes[node_id].fitness * graph.edge_property(node_id, dead_node_id, "logistical_weight", 1.0)
        for node_id in competitors
    }
    denominator = sum(pressures.values())
    if denominator <= 0:
        raise ValueError("replacement denominator must be positive")

    return {node_id: pressure / denominator for node_id, pressure in pressures.items()}


def step_death_birth_moran(
    graph: InMemoryGraph,
    nodes: MutableMapping[Hashable, MoranGeopoliticalNode],
    *,
    dead_node_id: Hashable | None = None,
    selection_value: float | None = None,
    rng: Random | None = None,
) -> Hashable:
    if not nodes:
        raise ValueError("nodes must not be empty")
    random_source = rng or Random()
    if dead_node_id is None:
        node_ids = list(nodes)
        dead_node_id = node_ids[random_source.randrange(len(node_ids))]
    if selection_value is None:
        selection_value = random_source.random()
    if not 0 <= selection_value < 1:
        raise ValueError("selection_value must be in the half-open interval [0, 1)")

    probabilities = death_birth_replacement_probabilities(graph, nodes, dead_node_id)
    cumulative = 0.0
    victor_id = next(reversed(probabilities))
    for node_id, probability in probabilities.items():
        cumulative += probability
        if selection_value <= cumulative:
            victor_id = node_id
            break

    dead_node = nodes[dead_node_id]
    victor = nodes[victor_id]
    dead_node.ideology = victor.ideology
    dead_node.fitness = victor.fitness
    return victor_id

