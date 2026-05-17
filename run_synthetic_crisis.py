from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from random import Random
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from andoworldstate.graph import InMemoryGraph
from andoworldstate.smc import Particle, SequentialMonteCarlo
from andoworldstate.theories.agent_zero import AgentZero
from andoworldstate.theories.cognitive_heuristics import (
    CognitiveHeuristicState,
    MacroShockObservation,
    update_leader_thresholds_from_macro_shock,
)
from andoworldstate.theories.complex_contagion import ComplexContagionAgent
from andoworldstate.theories.evolutionary_dynamics import (
    EvolutionaryDynamicsState,
    TerritorialShiftObservation,
    update_territorial_shift_weights,
)
from andoworldstate.theories.fast_frugal import FFTAgent, FFTCue
from andoworldstate.theories.poliheuristic import DecisionOption, PoliheuristicLeader
from andoworldstate.theories.structural_demographic import MacroState
from andoworldstate.theories.topological_contagion import (
    ProtestExpansionObservation,
    TopologicalContagionState,
    run_bridge_constrained_complex_contagion,
    update_topological_contagion_weights,
)
from andoworldstate.theories.watts import WattsCascadeNode


@dataclass(frozen=True)
class SyntheticObservation:
    week: int
    event: str
    debt_to_gdp: float
    polling_drop: float
    observed_protest_nodes: set[str]
    observed_capital_ideology: str
    source: str = "synthetic"


@dataclass
class SyntheticParticleState:
    graph: InMemoryGraph
    macro_state: MacroState
    agents: dict[str, AgentZero]
    fft_agents: dict[str, FFTAgent]
    watts_nodes: dict[str, WattsCascadeNode]
    complex_agents: dict[str, ComplexContagionAgent]
    leader: PoliheuristicLeader


@dataclass(frozen=True)
class TickSummary:
    week: int
    event: str
    capital_collapse_consensus: float
    effective_sample_size: float


@dataclass(frozen=True)
class CrisisRunResult:
    tick_summaries: list[TickSummary]
    readouts: list[str]


def build_synthetic_timeline() -> list[SyntheticObservation]:
    return [
        SyntheticObservation(1, "Debt pressure rises; isolated northern protests reported", 0.62, 0.00, {"province_north"}, "Regime"),
        SyntheticObservation(2, "Debt service worsens; protests remain localized", 0.68, 0.00, {"province_north"}, "Regime"),
        SyntheticObservation(3, "Structural debt strains the regime budget", 0.74, 0.00, {"province_north"}, "Regime"),
        SyntheticObservation(4, "Polling drops; protests find wide bridges into eastern districts", 0.82, 0.12, {"province_north", "province_east"}, "Regime"),
        SyntheticObservation(5, "Polling shock deepens; mobilization spreads through clustered ties", 0.88, 0.18, {"province_north", "province_east", "province_west"}, "Regime"),
        SyntheticObservation(6, "Capital-adjacent protest cluster ignites", 0.94, 0.24, {"province_north", "province_east", "province_west", "capital_city"}, "Regime"),
        SyntheticObservation(7, "Regime node collapses; insurgent frontier contests the capital", 0.98, 0.30, {"province_north", "province_east", "province_west", "capital_city"}, "Insurgent"),
        SyntheticObservation(8, "Province X reports administrative transfer to Faction B", 1.02, 0.32, {"province_north", "province_east", "province_west", "capital_city"}, "Insurgent"),
        SyntheticObservation(9, "Insurgent governance consolidates around the capital", 1.04, 0.34, {"province_north", "province_east", "province_west", "capital_city"}, "Insurgent"),
        SyntheticObservation(10, "Capital collapse confirmed by the synthetic ground truth feed", 1.06, 0.36, {"province_north", "province_east", "province_west", "capital_city"}, "Insurgent"),
    ]


def initialize_swarm(particle_count: int = 100, *, seed: int = 17) -> SequentialMonteCarlo:
    if particle_count <= 0:
        raise ValueError("particle_count must be positive")
    rng = Random(seed)
    particles = [
        Particle(state=_create_particle_state(index=index, rng=rng), weight=1.0)
        for index in range(particle_count)
    ]
    return SequentialMonteCarlo(particles)


def run_synthetic_crisis(
    *,
    particle_count: int = 100,
    seed: int = 17,
    emit: bool = True,
) -> CrisisRunResult:
    smc = initialize_swarm(particle_count=particle_count, seed=seed)
    summaries: list[TickSummary] = []
    readouts: list[str] = []
    for observation in build_synthetic_timeline():
        _apply_observation_to_swarm(smc, observation)
        effective_sample_size = smc.effective_sample_size()
        smc.normalize_weights()
        smc.systematic_resample(start=0.5)
        consensus = _capital_collapse_consensus(smc)
        summary = TickSummary(
            week=observation.week,
            event=observation.event,
            capital_collapse_consensus=consensus,
            effective_sample_size=effective_sample_size,
        )
        readout = format_tick_readout(
            week=summary.week,
            event=summary.event,
            capital_collapse_consensus=summary.capital_collapse_consensus,
            effective_sample_size=summary.effective_sample_size,
        )
        summaries.append(summary)
        readouts.append(readout)
        if emit:
            print(readout)
    return CrisisRunResult(tick_summaries=summaries, readouts=readouts)


def format_tick_readout(
    *,
    week: int,
    event: str,
    capital_collapse_consensus: float,
    effective_sample_size: float,
) -> str:
    consensus_pct = round(capital_collapse_consensus * 100)
    return (
        f"Week {week:02d} | Event: {event}\n"
        f"  Swarm Consensus: {consensus_pct}% of surviving particles predict Capital collapse | "
        f"ESS: {effective_sample_size:.1f}"
    )


def _create_particle_state(*, index: int, rng: Random) -> SyntheticParticleState:
    graph = InMemoryGraph()
    has_wide_bridge = index < 76
    has_insurgent_advantage = index < 88
    is_capital_vulnerable = index < 82

    insurgent_fitness = 4.0 + rng.random() * 0.2 if has_insurgent_advantage else 1.0
    regime_fitness = 1.0 if has_insurgent_advantage else 5.0
    insurgent_edge_weight = 3.0 if has_insurgent_advantage else 1.0
    regime_edge_weight = 1.0 if has_insurgent_advantage else 3.0

    graph.add_node("capital_city", role="capital", ideology="Regime", fitness=1.0)
    graph.add_node("regime", role="ruling_regime", ideology="Regime", fitness=regime_fitness)
    graph.add_node("province_north", role="province", ideology="Insurgent", fitness=insurgent_fitness)
    graph.add_node("province_east", role="province", ideology="Regime", fitness=1.0)
    graph.add_node("province_west", role="province", ideology="Regime", fitness=1.0)
    graph.add_node("province_south", role="province", ideology="Regime", fitness=1.0)

    graph.add_edge("province_east", "province_north", logistical_weight=1.0)
    if has_wide_bridge:
        graph.add_edge("province_west", "province_north", logistical_weight=1.0)
    graph.add_edge("capital_city", "province_east", logistical_weight=1.0)
    graph.add_edge("capital_city", "province_west", logistical_weight=1.0)
    graph.add_edge("province_north", "capital_city", logistical_weight=insurgent_edge_weight)
    graph.add_edge("regime", "capital_city", logistical_weight=regime_edge_weight)

    macro_state = MacroState(
        relative_wage=0.7,
        urbanization_ratio=0.8,
        youth_bulge=0.25,
        relative_elite_income=0.5,
        elite_ratio=0.12,
        debt_to_gdp=0.6,
        distrust=0.35,
    )
    agents = {
        node_id: AgentZero(
            unique_id=node_id,
            learning_rate_alpha=0.35,
            salience_beta=0.45,
            activation_threshold_tau=1.0,
        )
        for node_id in ("province_north", "province_east", "province_west", "capital_city")
    }
    fft_agents = {
        node_id: FFTAgent(
            unique_id=f"fft-{node_id}",
            cue_hierarchy=[
                FFTCue.macro_greater_equal("state_distrust", "distrust", threshold=0.55),
                FFTCue.wage_inverse_greater_equal(threshold=1.6),
                FFTCue.epstein_fear_greater_equal(threshold=0.45),
            ],
        )
        for node_id in agents
    }
    watts_nodes = {
        "province_north": WattsCascadeNode("province_north", fractional_threshold=1.0),
        "province_east": WattsCascadeNode("province_east", fractional_threshold=1.0),
        "province_west": WattsCascadeNode("province_west", fractional_threshold=1.0),
        "capital_city": WattsCascadeNode("capital_city", fractional_threshold=0.5 if is_capital_vulnerable else 1.1),
    }
    complex_agents = {
        "province_north": ComplexContagionAgent("province_north", complex_threshold=1),
        "province_east": ComplexContagionAgent("province_east", complex_threshold=1),
        "province_west": ComplexContagionAgent("province_west", complex_threshold=1),
        "capital_city": ComplexContagionAgent("capital_city", complex_threshold=2),
    }
    return SyntheticParticleState(
        graph=graph,
        macro_state=macro_state,
        agents=agents,
        fft_agents=fft_agents,
        watts_nodes=watts_nodes,
        complex_agents=complex_agents,
        leader=PoliheuristicLeader(political_survival_threshold=-3.0),
    )


def _apply_observation_to_swarm(smc: SequentialMonteCarlo, observation: SyntheticObservation) -> None:
    for particle in smc.particles:
        _apply_observation_to_particle(particle.state, observation)
    _weight_topology(smc, observation)
    if observation.observed_capital_ideology == "Insurgent":
        _weight_territorial_shift(smc)


def _apply_observation_to_particle(state: SyntheticParticleState, observation: SyntheticObservation) -> None:
    state.macro_state.debt_to_gdp = observation.debt_to_gdp
    state.macro_state.distrust = min(0.95, 0.35 + observation.polling_drop + max(0.0, observation.debt_to_gdp - 0.6))
    update_leader_thresholds_from_macro_shock(
        [Particle(state=CognitiveHeuristicState(state.macro_state, [state.leader]), weight=1.0)],
        MacroShockObservation(
            debt_to_gdp=observation.debt_to_gdp,
            polling_drop=observation.polling_drop,
            debt_baseline=0.6,
            debt_stress_weight=2.0,
            polling_drop_weight=5.0,
        ),
    )
    for node_id, agent in state.agents.items():
        agent.step_rescorla_wagner(observation.debt_to_gdp + observation.polling_drop)
        fft_decision = state.fft_agents[node_id].evaluate_from_state(state.macro_state, agent)
        if fft_decision.choice == 1 and node_id == "province_north":
            state.watts_nodes[node_id].active_state = 1
            state.complex_agents[node_id].behavior_adopted = True

    state.watts_nodes["province_north"].active_state = 1
    state.complex_agents["province_north"].behavior_adopted = True
    if observation.week >= 4:
        run_bridge_constrained_complex_contagion(
            state.graph,
            state.complex_agents,
            source_community={"province_north"},
            target_community={"province_east", "province_west"},
            complex_threshold=2,
        )
        for node_id in ("province_east", "province_west"):
            if state.complex_agents[node_id].behavior_adopted:
                state.watts_nodes[node_id].active_state = 1
    if observation.week >= 6:
        _evaluate_leader_decision(state)


def _evaluate_leader_decision(state: SyntheticParticleState) -> str:
    return state.leader.evaluate_options(
        [
            DecisionOption("hold_capital", political=-4.0, military=9.0, economic=4.0),
            DecisionOption("cede_ground", political=-1.0, military=1.0, economic=1.0),
        ]
    )


def _weight_topology(smc: SequentialMonteCarlo, observation: SyntheticObservation) -> None:
    wrapped_particles = [
        Particle(
            state=TopologicalContagionState(
                graph=particle.state.graph,
                watts_nodes=particle.state.watts_nodes,
                complex_agents=particle.state.complex_agents,
            ),
            weight=particle.weight,
        )
        for particle in smc.particles
    ]
    update_topological_contagion_weights(
        wrapped_particles,
        ProtestExpansionObservation(
            observed_active_nodes=set(observation.observed_protest_nodes),
            source_community={"province_north"},
            target_community={"province_east", "province_west"},
            complex_threshold=2,
            variance=1.0,
            weak_tie_penalty=8.0,
            missed_vulnerable_penalty=4.0,
        ),
    )
    for particle, wrapped in zip(smc.particles, wrapped_particles):
        particle.weight = wrapped.weight


def _weight_territorial_shift(smc: SequentialMonteCarlo) -> None:
    wrapped_particles = [
        Particle(state=EvolutionaryDynamicsState(graph=particle.state.graph), weight=particle.weight)
        for particle in smc.particles
    ]
    update_territorial_shift_weights(
        wrapped_particles,
        TerritorialShiftObservation(
            collapsed_node_id="capital_city",
            observed_ideology="Insurgent",
            selection_value=0.8,
            mismatch_penalty=10.0,
        ),
    )
    for particle, wrapped in zip(smc.particles, wrapped_particles):
        particle.weight = wrapped.weight


def _capital_collapse_consensus(smc: SequentialMonteCarlo) -> float:
    collapsed = sum(
        1
        for particle in smc.particles
        if particle.state.graph.node_properties("capital_city")["ideology"] == "Insurgent"
    )
    return collapsed / len(smc.particles)


def main() -> None:
    run_synthetic_crisis()


if __name__ == "__main__":
    main()
