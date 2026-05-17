from __future__ import annotations

from collections.abc import Hashable, Iterable, MutableMapping
from dataclasses import dataclass
from math import exp

from andoworldstate.graph import InMemoryGraph
from andoworldstate.smc import Particle
from andoworldstate.theories.complex_contagion import ComplexContagionAgent, step_complex_contagion
from andoworldstate.theories.watts import WattsCascadeNode, step_watts_cascade


@dataclass
class TopologicalContagionState:
    graph: InMemoryGraph
    watts_nodes: MutableMapping[Hashable, WattsCascadeNode]
    complex_agents: MutableMapping[Hashable, ComplexContagionAgent]


@dataclass(frozen=True)
class ProtestExpansionObservation:
    observed_active_nodes: set[Hashable]
    source_community: set[Hashable]
    target_community: set[Hashable]
    complex_threshold: int
    variance: float
    weak_tie_penalty: float
    missed_vulnerable_penalty: float

    def __post_init__(self) -> None:
        if self.complex_threshold < 1:
            raise ValueError("complex_threshold must be at least 1")
        if self.variance <= 0:
            raise ValueError("variance must be positive")
        if self.weak_tie_penalty < 0:
            raise ValueError("weak_tie_penalty must be non-negative")
        if self.missed_vulnerable_penalty < 0:
            raise ValueError("missed_vulnerable_penalty must be non-negative")


def localized_protest_expansion_observation() -> ProtestExpansionObservation:
    return ProtestExpansionObservation(
        observed_active_nodes={"district_a_1", "district_a_2", "district_a_3"},
        source_community={"district_a_1", "district_a_2", "district_a_3"},
        target_community={"district_b_1", "district_b_2"},
        complex_threshold=2,
        variance=1.0,
        weak_tie_penalty=10.0,
        missed_vulnerable_penalty=5.0,
    )


def run_watts_cascade_until_stable(
    graph: InMemoryGraph,
    nodes: MutableMapping[Hashable, WattsCascadeNode],
    *,
    max_steps: int | None = None,
) -> int:
    steps = 0
    previous_active = _active_watts_nodes(nodes)
    limit = max_steps if max_steps is not None else max(len(nodes), 1)
    for _ in range(limit):
        step_watts_cascade(graph, nodes)
        current_active = _active_watts_nodes(nodes)
        if current_active == previous_active:
            break
        steps += 1
        previous_active = current_active
    return steps


def can_cross_complex_bridge(
    graph: InMemoryGraph,
    source_community: Iterable[Hashable],
    target_community: Iterable[Hashable],
    *,
    complex_threshold: int,
) -> bool:
    if complex_threshold < 1:
        raise ValueError("complex_threshold must be at least 1")
    return graph.edges_between(source_community, target_community) >= complex_threshold


def run_bridge_constrained_complex_contagion(
    graph: InMemoryGraph,
    agents: MutableMapping[Hashable, ComplexContagionAgent],
    *,
    source_community: Iterable[Hashable],
    target_community: Iterable[Hashable],
    complex_threshold: int,
) -> set[Hashable]:
    target_nodes = set(target_community)
    before = _adopted_agents(agents)
    if not can_cross_complex_bridge(
        graph,
        source_community,
        target_nodes,
        complex_threshold=complex_threshold,
    ):
        return set()

    step_complex_contagion(graph, agents)
    after = _adopted_agents(agents)
    return (after - before) & target_nodes


def update_topological_contagion_weights(
    particles: list[Particle],
    observation: ProtestExpansionObservation,
) -> None:
    for particle in particles:
        state = _particle_state(particle)
        run_watts_cascade_until_stable(state.graph, state.watts_nodes)
        simulated_active = _active_watts_nodes(state.watts_nodes)
        missed_observed = observation.observed_active_nodes - simulated_active
        symmetric_error = len(observation.observed_active_nodes.symmetric_difference(simulated_active))

        bridge_can_cross = can_cross_complex_bridge(
            state.graph,
            observation.source_community,
            observation.target_community,
            complex_threshold=observation.complex_threshold,
        )
        weak_tie_violations = 0
        if not bridge_can_cross:
            weak_tie_violations = sum(
                1
                for agent_id in observation.target_community
                if state.complex_agents.get(agent_id) is not None
                and state.complex_agents[agent_id].behavior_adopted
            )

        cascade_likelihood = exp(-0.5 * (symmetric_error**2) / observation.variance)
        weak_tie_likelihood = exp(-weak_tie_violations * observation.weak_tie_penalty)
        missed_vulnerable_likelihood = exp(-len(missed_observed) * observation.missed_vulnerable_penalty)
        particle.weight *= cascade_likelihood * weak_tie_likelihood * missed_vulnerable_likelihood


def _particle_state(particle: Particle) -> TopologicalContagionState:
    if isinstance(particle.state, TopologicalContagionState):
        return particle.state
    raise ValueError("particle state must be TopologicalContagionState")


def _active_watts_nodes(nodes: MutableMapping[Hashable, WattsCascadeNode]) -> set[Hashable]:
    return {node_id for node_id, node in nodes.items() if node.active_state == 1}


def _adopted_agents(agents: MutableMapping[Hashable, ComplexContagionAgent]) -> set[Hashable]:
    return {agent_id for agent_id, agent in agents.items() if agent.behavior_adopted}
