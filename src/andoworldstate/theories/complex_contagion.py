from __future__ import annotations

from collections.abc import Hashable, Iterable, MutableMapping
from dataclasses import dataclass

from andoworldstate.graph import InMemoryGraph


@dataclass
class ComplexContagionAgent:
    unique_id: Hashable
    complex_threshold: int
    behavior_adopted: bool = False

    def __post_init__(self) -> None:
        if self.complex_threshold < 1:
            raise ValueError("complex_threshold must be at least 1")


def step_complex_contagion(
    graph: InMemoryGraph,
    agents: MutableMapping[Hashable, ComplexContagionAgent],
) -> None:
    adopted_snapshot = {agent_id: agent.behavior_adopted for agent_id, agent in agents.items()}
    for agent_id, agent in agents.items():
        if agent.behavior_adopted:
            continue
        active_signals = sum(
            1 for neighbor_id in graph.neighbors(agent_id) if adopted_snapshot.get(neighbor_id, False)
        )
        if active_signals >= agent.complex_threshold:
            agent.behavior_adopted = True


def analyze_bridge_width_constraint(
    graph: InMemoryGraph,
    community_a_nodes: Iterable[Hashable],
    community_b_nodes: Iterable[Hashable],
) -> int:
    return graph.edges_between(community_a_nodes, community_b_nodes)

