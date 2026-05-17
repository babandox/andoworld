from __future__ import annotations

import argparse
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from random import Random
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from andoworldstate.graph import InMemoryGraph
from andoworldstate.ingestion.gdelt import GdeltClient
from andoworldstate.ingestion.world_bank import WorldBankClient, apply_world_bank_update_to_graph
from andoworldstate.neo4j_graph import Neo4jGraph
from andoworldstate.smc import Particle, SequentialMonteCarlo
from andoworldstate.theories.agent_zero import AgentZero
from andoworldstate.theories.cognitive_heuristics import LeaderProfile
from andoworldstate.theories.complex_contagion import ComplexContagionAgent
from andoworldstate.theories.fast_frugal import FFTAgent, FFTCue
from andoworldstate.theories.poliheuristic import DecisionOption, PoliheuristicLeader
from andoworldstate.theories.structural_demographic import MacroState
from andoworldstate.theories.topological_contagion import (
    ProtestExpansionObservation,
    TopologicalContagionState,
    run_bridge_constrained_complex_contagion,
    run_watts_cascade_until_stable,
    update_topological_contagion_weights,
)
from andoworldstate.theories.watts import WattsCascadeNode


ISO3_TO_GDELT_COUNTRY_CODE = {
    "FRA": "FR",
    "IRN": "IR",
    "KEN": "KE",
    "USA": "US",
}

DEFAULT_LEADER_PROFILE = LeaderProfile(lta_complexity=0.5, lta_distrust=0.5, fusion_factor=0.3)
LEADER_PROFILE_MATRIX = {
    "IRN": LeaderProfile(lta_complexity=0.55, lta_distrust=0.65, fusion_factor=0.92),
    "USA": LeaderProfile(lta_complexity=0.2, lta_distrust=0.85, fusion_factor=0.2),
    "FRA": DEFAULT_LEADER_PROFILE,
}


@dataclass
class LiveParticleState:
    country_iso3: str
    graph: InMemoryGraph
    macro_state: MacroState
    leader_profile: LeaderProfile
    leader: PoliheuristicLeader
    fft_agent: FFTAgent
    agents: dict[str, AgentZero]
    watts_nodes: dict[str, WattsCascadeNode]
    complex_agents: dict[str, ComplexContagionAgent]
    seed_threshold: float
    leader_decision: str | None = None
    last_fft_decision: str | None = None


@dataclass(frozen=True)
class LiveDayObservation:
    day_number: int
    observed_date: date
    event_count: int
    goldstein_salience: float
    threat_lambda: float


@dataclass(frozen=True)
class LiveDaySummary:
    day_number: int
    observed_date: date
    event_count: int
    threat_lambda: float
    mobilization_consensus: float
    effective_sample_size: float


@dataclass(frozen=True)
class Neo4jExportSummary:
    attempted: bool = False
    succeeded: bool = False
    message: str = "not requested"
    run_id: str | None = None
    particle_weight: float | None = None


@dataclass(frozen=True)
class LiveRunResult:
    day_summaries: list[LiveDaySummary]
    readouts: list[str]
    best_particle_state: LiveParticleState | None
    best_particle_weight: float | None
    neo4j_export: Neo4jExportSummary


def build_backtest_dates(*, end_date: date | None = None, days: int = 7) -> list[date]:
    if days <= 0:
        raise ValueError("days must be positive")
    completed_end_date = end_date or (datetime.now(timezone.utc).date() - timedelta(days=1))
    first_day = completed_end_date - timedelta(days=days - 1)
    return [first_day + timedelta(days=offset) for offset in range(days)]


def initialize_live_swarm(
    country_iso3: str,
    macro_update: dict[str, float],
    *,
    particle_count: int = 50,
    seed: int = 29,
) -> SequentialMonteCarlo:
    if particle_count <= 0:
        raise ValueError("particle_count must be positive")
    country = country_iso3.upper()
    leader_profile = leader_profile_for_country(country)
    rng = Random(seed)
    particles = [
        Particle(
            state=_create_live_particle_state(
                country,
                macro_update,
                leader_profile=leader_profile,
                index=index,
                rng=rng,
            ),
            weight=1.0,
        )
        for index in range(particle_count)
    ]
    return SequentialMonteCarlo(particles)


def run_live_engine(
    country_iso3: str,
    *,
    world_bank_client: Any | None = None,
    gdelt_client: Any | None = None,
    particle_count: int = 50,
    days: int = 7,
    end_date: date | None = None,
    seed: int = 29,
    emit: bool = True,
    resample_start: float | None = None,
    gdelt_interval_minutes: int | None = None,
    neo4j_graph: Any | None = None,
    export_neo4j: bool = False,
    run_id: str | None = None,
) -> LiveRunResult:
    country = country_iso3.upper()
    world_bank = world_bank_client or WorldBankClient()
    gdelt = gdelt_client or GdeltClient()
    macro_update = world_bank.fetch_macro_state_update(country)
    smc = initialize_live_swarm(country, macro_update, particle_count=particle_count, seed=seed)
    gdelt_country_code = gdelt_country_code_for_iso3(country)
    rng = Random(seed)

    summaries: list[LiveDaySummary] = []
    readouts: list[str] = []
    best_particle: Particle | None = None
    best_particle_weight: float | None = None
    for day_number, observed_date in enumerate(build_backtest_dates(end_date=end_date, days=days), start=1):
        threat = _fetch_daily_threat(
            gdelt,
            gdelt_country_code=gdelt_country_code,
            observed_date=observed_date,
            gdelt_interval_minutes=gdelt_interval_minutes,
        )
        observation = LiveDayObservation(
            day_number=day_number,
            observed_date=observed_date,
            event_count=int(threat["event_count"]),
            goldstein_salience=float(threat["goldstein_salience"]),
            threat_lambda=float(threat["environmental_threat_lambda"]),
        )
        _apply_live_observation_to_swarm(smc, observation)
        day_best_particle = max(smc.particles, key=lambda particle: particle.weight)
        best_particle = day_best_particle
        best_particle_weight = day_best_particle.weight
        effective_sample_size = smc.effective_sample_size()
        smc.normalize_weights()
        smc.systematic_resample(start=resample_start, rng=rng)
        consensus = mobilization_consensus(smc)
        summary = LiveDaySummary(
            day_number=day_number,
            observed_date=observed_date,
            event_count=observation.event_count,
            threat_lambda=observation.threat_lambda,
            mobilization_consensus=consensus,
            effective_sample_size=effective_sample_size,
        )
        readout = format_day_readout(
            day_number=summary.day_number,
            observed_date=summary.observed_date,
            event_count=summary.event_count,
            threat_lambda=summary.threat_lambda,
            mobilization_consensus=summary.mobilization_consensus,
            effective_sample_size=summary.effective_sample_size,
        )
        summaries.append(summary)
        readouts.append(readout)
        if emit:
            print(readout)

    export_summary = _export_best_particle(
        best_particle,
        neo4j_graph=neo4j_graph,
        export_neo4j=export_neo4j,
        run_id=run_id or f"live-engine-{country}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        particle_weight=best_particle_weight,
    )
    if emit and export_summary.attempted:
        print(f"Neo4j Export: {export_summary.message}")

    return LiveRunResult(
        day_summaries=summaries,
        readouts=readouts,
        best_particle_state=best_particle.state if best_particle is not None else None,
        best_particle_weight=best_particle_weight,
        neo4j_export=export_summary,
    )


def format_day_readout(
    *,
    day_number: int,
    observed_date: date,
    event_count: int,
    threat_lambda: float,
    mobilization_consensus: float,
    effective_sample_size: float,
) -> str:
    consensus_pct = round(mobilization_consensus * 100)
    event_word = "event" if event_count == 1 else "events"
    return (
        f"Day {day_number} ({observed_date.isoformat()}): GDELT recorded {event_count} violent {event_word}.\n"
        f"  Swarm Consensus: {consensus_pct}% of particles triggered a mass mobilization cascade | "
        f"lambda(t)={threat_lambda:.3f} | ESS: {effective_sample_size:.1f}"
    )


def gdelt_country_code_for_iso3(country_iso3: str) -> str:
    country = country_iso3.upper()
    if len(country) != 3 or not country.isalpha():
        raise ValueError("country_iso3 must be a three-letter ISO-3 code")
    if country in ISO3_TO_GDELT_COUNTRY_CODE:
        return ISO3_TO_GDELT_COUNTRY_CODE[country]
    return country[:2]


def leader_profile_for_country(country_iso3: str) -> LeaderProfile:
    country = country_iso3.upper()
    return LEADER_PROFILE_MATRIX.get(country, DEFAULT_LEADER_PROFILE)


def mobilization_consensus(smc: SequentialMonteCarlo) -> float:
    mobilized = sum(1 for particle in smc.particles if _is_mass_mobilized(particle.state))
    return mobilized / len(smc.particles)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Andoworld live geopolitical SMC engine.")
    parser.add_argument("country_iso3", help="Target country ISO-3 code, such as KEN, FRA, or USA.")
    parser.add_argument("--particles", type=int, default=50, help="Number of SMC particles to initialize.")
    parser.add_argument("--days", type=int, default=7, help="Number of completed days to backtest.")
    parser.add_argument(
        "--gdelt-interval-minutes",
        type=int,
        default=15,
        help="GDELT v2 export interval size for each backtest day. The default uses every 15-minute export.",
    )
    parser.add_argument(
        "--no-neo4j-export",
        action="store_true",
        help="Run the SMC backtest without attempting to export the highest-weighted particle to Neo4j.",
    )
    parser.add_argument("--neo4j-run-id", default=None, help="Optional run id to attach to exported Neo4j nodes.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    run_live_engine(
        args.country_iso3,
        particle_count=args.particles,
        days=args.days,
        gdelt_interval_minutes=args.gdelt_interval_minutes,
        export_neo4j=not args.no_neo4j_export,
        run_id=args.neo4j_run_id,
    )


def _create_live_particle_state(
    country_iso3: str,
    macro_update: dict[str, float],
    *,
    leader_profile: LeaderProfile,
    index: int,
    rng: Random,
) -> LiveParticleState:
    graph = InMemoryGraph()
    has_wide_bridge = index % 10 < 7
    is_capital_vulnerable = index % 5 != 0
    seed_threshold = 0.2 + (index % 5) * 0.1 + rng.random() * 0.01

    graph.add_node(country_iso3, role="country")
    graph.add_node("environment", role="environmental_feed", environmental_threat_lambda=0.0)
    graph.add_node("capital_city", role="capital")
    graph.add_node("regime", role="ruling_regime")
    for province in ("province_north", "province_east", "province_west"):
        graph.add_node(province, role="province")

    graph.add_edge("province_east", "province_north", omega=0.2, logistical_weight=1.0)
    if has_wide_bridge:
        graph.add_edge("province_west", "province_north", omega=0.2, logistical_weight=1.0)
    graph.add_edge("capital_city", "province_east", omega=0.25, logistical_weight=1.0)
    graph.add_edge("capital_city", "province_west", omega=0.25, logistical_weight=1.0)

    macro_state = MacroState(
        relative_wage=macro_update.get("relative_wage", 0.7),
        urbanization_ratio=macro_update.get("urbanization_rate", 0.6),
        youth_bulge=macro_update.get("youth_bulge", 0.2),
        relative_elite_income=macro_update.get("relative_elite_income", 0.5),
        elite_ratio=macro_update.get("elite_ratio", 0.12),
        debt_to_gdp=macro_update.get("debt_to_gdp", 0.6),
        distrust=macro_update.get("distrust", min(0.9, 0.2 + macro_update.get("debt_to_gdp", 0.6) * 0.3)),
    )
    apply_world_bank_update_to_graph(graph, country_iso3, macro_update)

    agents = {
        node_id: AgentZero(
            unique_id=node_id,
            learning_rate_alpha=0.55,
            salience_beta=0.75,
            activation_threshold_tau=0.8,
        )
        for node_id in ("province_north", "province_east", "province_west", "capital_city")
    }
    leader = PoliheuristicLeader(
        political_survival_threshold=-2.0,
        lta_complexity=leader_profile.lta_complexity,
        lta_distrust=leader_profile.lta_distrust,
        fusion_factor=leader_profile.fusion_factor,
        ideological_preservation_threshold=0.8,
    )
    fft_agent = FFTAgent(
        unique_id=f"fft-{country_iso3}",
        cue_hierarchy=[
            FFTCue.macro_greater_equal("economic_pressure", "debt_to_gdp", threshold=0.85),
            FFTCue.epstein_fear_greater_equal(threshold=0.8),
        ],
    )
    watts_nodes = {
        "province_north": WattsCascadeNode("province_north", fractional_threshold=1.0),
        "province_east": WattsCascadeNode("province_east", fractional_threshold=1.1),
        "province_west": WattsCascadeNode("province_west", fractional_threshold=1.1),
        "capital_city": WattsCascadeNode("capital_city", fractional_threshold=0.5 if is_capital_vulnerable else 1.1),
    }
    complex_agents = {
        "province_north": ComplexContagionAgent("province_north", complex_threshold=1),
        "province_east": ComplexContagionAgent("province_east", complex_threshold=1),
        "province_west": ComplexContagionAgent("province_west", complex_threshold=1),
        "capital_city": ComplexContagionAgent("capital_city", complex_threshold=2),
    }
    return LiveParticleState(
        country_iso3=country_iso3,
        graph=graph,
        macro_state=macro_state,
        leader_profile=leader_profile,
        leader=leader,
        fft_agent=fft_agent,
        agents=agents,
        watts_nodes=watts_nodes,
        complex_agents=complex_agents,
        seed_threshold=seed_threshold,
    )


def _fetch_daily_threat(
    gdelt_client: Any,
    *,
    gdelt_country_code: str,
    observed_date: date,
    gdelt_interval_minutes: int | None,
) -> dict[str, float | int]:
    if gdelt_interval_minutes is None:
        return gdelt_client.fetch_daily_threat_index(country_code=gdelt_country_code, day=observed_date)
    return gdelt_client.fetch_daily_threat_index(
        country_code=gdelt_country_code,
        day=observed_date,
        interval_minutes=gdelt_interval_minutes,
    )


def _apply_live_observation_to_swarm(smc: SequentialMonteCarlo, observation: LiveDayObservation) -> None:
    for particle in smc.particles:
        _apply_live_observation_to_particle(particle.state, observation)
    _weight_live_topology(smc, observation)


def _apply_live_observation_to_particle(state: LiveParticleState, observation: LiveDayObservation) -> None:
    state.graph.set_node_property("environment", "environmental_threat_lambda", observation.threat_lambda)
    state.macro_state.distrust = min(
        0.95,
        state.macro_state.distrust + observation.threat_lambda * 0.15,
    )
    for agent in state.agents.values():
        agent.step_rescorla_wagner(observation.threat_lambda)

    state.leader_decision = state.leader.evaluate_options(_live_leader_options())
    fft_decision = state.fft_agent.evaluate_from_state(
        state.macro_state,
        state.agents["province_north"],
        leader_profile=state.leader_profile,
    )
    state.last_fft_decision = fft_decision.triggered_cue

    fused_conflict = state.leader_decision == "mutually_destructive_conflict"
    fft_high_risk_action = fft_decision.choice == 1
    if observation.event_count > 0 and (
        observation.threat_lambda >= state.seed_threshold or fused_conflict or fft_high_risk_action
    ):
        state.watts_nodes["province_north"].active_state = 1
        state.complex_agents["province_north"].behavior_adopted = True

    if state.complex_agents["province_north"].behavior_adopted:
        newly_adopted = run_bridge_constrained_complex_contagion(
            state.graph,
            state.complex_agents,
            source_community={"province_north"},
            target_community={"province_east", "province_west"},
            complex_threshold=2,
        )
        for node_id in newly_adopted:
            state.watts_nodes[node_id].active_state = 1

    run_watts_cascade_until_stable(state.graph, state.watts_nodes)


def _weight_live_topology(smc: SequentialMonteCarlo, observation: LiveDayObservation) -> None:
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
            observed_active_nodes=_observed_active_nodes_from_event_count(observation.event_count),
            source_community={"province_north"},
            target_community={"province_east", "province_west"},
            complex_threshold=2,
            variance=2.0,
            weak_tie_penalty=6.0,
            missed_vulnerable_penalty=3.0,
        ),
    )
    for particle, wrapped in zip(smc.particles, wrapped_particles):
        particle.weight = wrapped.weight


def _observed_active_nodes_from_event_count(event_count: int) -> set[str]:
    if event_count <= 0:
        return set()
    if event_count < 5:
        return {"province_north"}
    if event_count < 10:
        return {"province_north", "province_east"}
    if event_count < 15:
        return {"province_north", "province_east", "province_west"}
    return {"province_north", "province_east", "province_west", "capital_city"}


def _is_mass_mobilized(state: LiveParticleState) -> bool:
    active_count = sum(node.active_state for node in state.watts_nodes.values())
    return active_count >= 3


def _live_leader_options() -> list[DecisionOption]:
    return [
        DecisionOption(
            "ideological_capitulation",
            political=10.0,
            military=50.0,
            economic=50.0,
            ideological=0.1,
            violates_ideology=True,
        ),
        DecisionOption(
            "limited_security_response",
            political=-1.0,
            military=2.0,
            economic=-3.0,
            ideological=0.7,
        ),
        DecisionOption(
            "mutually_destructive_conflict",
            political=-10.0,
            military=-100.0,
            economic=-100.0,
            ideological=1.0,
        ),
    ]


def export_live_particle_to_neo4j(
    state: LiveParticleState,
    neo4j_graph: Any,
    *,
    run_id: str,
) -> None:
    for node_id, properties in state.graph.node_items():
        neo4j_graph.add_node(
            node_id,
            **_export_node_properties(state, node_id=str(node_id), properties=properties, run_id=run_id),
        )
    for source, target, properties in state.graph.edge_items():
        neo4j_graph.add_edge(source, target, **properties)


def _export_node_properties(
    state: LiveParticleState,
    *,
    node_id: str,
    properties: dict[str, Any],
    run_id: str,
) -> dict[str, Any]:
    exported = dict(properties)
    exported["run_id"] = run_id

    if node_id == state.country_iso3:
        exported.update(asdict(state.macro_state))
        exported.update(asdict(state.leader_profile))
        exported.update(
            {
                "political_survival_threshold": state.leader.political_survival_threshold,
                "ideological_preservation_threshold": state.leader.ideological_preservation_threshold,
                "leader_decision": state.leader_decision,
            }
        )

    if node_id in state.agents:
        agent_properties = asdict(state.agents[node_id])
        agent_properties.pop("unique_id", None)
        exported.update(agent_properties)

    if node_id in state.watts_nodes:
        watts_node = state.watts_nodes[node_id]
        exported.update(
            {
                "watts_active_state": watts_node.active_state,
                "watts_fractional_threshold": watts_node.fractional_threshold,
                "watts_degree": watts_node.degree,
            }
        )

    if node_id in state.complex_agents:
        complex_agent = state.complex_agents[node_id]
        exported.update(
            {
                "complex_threshold": complex_agent.complex_threshold,
                "complex_behavior_adopted": complex_agent.behavior_adopted,
            }
        )

    return exported


def _export_best_particle(
    best_particle: Particle | None,
    *,
    neo4j_graph: Any | None,
    export_neo4j: bool,
    run_id: str,
    particle_weight: float | None,
) -> Neo4jExportSummary:
    if not export_neo4j:
        return Neo4jExportSummary()
    if best_particle is None:
        return Neo4jExportSummary(
            attempted=True,
            succeeded=False,
            message="no particle available for export",
            run_id=run_id,
            particle_weight=particle_weight,
        )

    graph = neo4j_graph
    owns_graph = False
    try:
        if graph is None:
            graph = _neo4j_graph_from_environment()
            owns_graph = True
        export_live_particle_to_neo4j(best_particle.state, graph, run_id=run_id)
    except Exception as exc:
        return Neo4jExportSummary(
            attempted=True,
            succeeded=False,
            message=f"failed: {exc}",
            run_id=run_id,
            particle_weight=particle_weight,
        )
    finally:
        if owns_graph and graph is not None:
            graph.close()

    return Neo4jExportSummary(
        attempted=True,
        succeeded=True,
        message=f"succeeded for run_id={run_id}",
        run_id=run_id,
        particle_weight=particle_weight,
    )


def _neo4j_graph_from_environment() -> Neo4jGraph:
    return Neo4jGraph.from_uri(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password")),
        database=os.getenv("NEO4J_DATABASE") or None,
    )


if __name__ == "__main__":
    main()
