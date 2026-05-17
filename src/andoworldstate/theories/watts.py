from __future__ import annotations

from collections.abc import Hashable, MutableMapping
from dataclasses import dataclass
from typing import Any

from andoworldstate.graph import InMemoryGraph

E = 2.718281828459045


@dataclass
class WattsCascadeNode:
    unique_id: Hashable
    fractional_threshold: float
    active_state: int = 0
    degree: int = 0


def step_watts_cascade(graph: InMemoryGraph, nodes: MutableMapping[Hashable, WattsCascadeNode]) -> None:
    active_snapshot = {node_id: node.active_state for node_id, node in nodes.items()}
    for node_id, node in nodes.items():
        node.degree = graph.degree(node_id)
        if node.active_state == 1 or node.degree == 0:
            continue
        active_neighbors = sum(1 for neighbor_id in graph.neighbors(node_id) if active_snapshot.get(neighbor_id) == 1)
        fraction_active = active_neighbors / node.degree
        if fraction_active >= node.fractional_threshold:
            node.active_state = 1


def is_vulnerable(*, degree: int, fractional_threshold: float) -> bool:
    if degree <= 0:
        return False
    return fractional_threshold <= 1.0 / degree


def particle_filter_cascade_culling(particles: list[Any], real_time_protest_size: int) -> None:
    for particle in particles:
        if particle.variance <= 0:
            raise ValueError("particle variance must be positive")
        simulated_size = sum(agent.active_state for agent in particle.agents)
        error = abs(simulated_size - real_time_protest_size)
        particle.weight *= E ** (-0.5 * (error**2) / particle.variance)

