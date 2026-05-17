from __future__ import annotations

from datetime import date

from andoworldstate.smc import Particle, SequentialMonteCarlo
from run_live_engine import (
    LiveParticleState,
    LiveDayObservation,
    _apply_live_observation_to_swarm,
    build_backtest_dates,
    export_live_particle_to_neo4j,
    format_day_readout,
    initialize_live_swarm,
    leader_profile_for_country,
    run_live_engine,
)


def test_build_backtest_dates_returns_completed_days_oldest_first():
    dates = build_backtest_dates(end_date=date(2026, 5, 16), days=7)

    assert dates == [
        date(2026, 5, 10),
        date(2026, 5, 11),
        date(2026, 5, 12),
        date(2026, 5, 13),
        date(2026, 5, 14),
        date(2026, 5, 15),
        date(2026, 5, 16),
    ]


def test_initialize_live_swarm_uses_world_bank_baseline_across_particles():
    smc = initialize_live_swarm(
        "KEN",
        {"urbanization_rate": 0.31, "youth_bulge": 0.205, "debt_to_gdp": 0.714},
        particle_count=50,
        seed=3,
    )

    assert len(smc.particles) == 50
    state = smc.particles[0].state
    assert isinstance(state, LiveParticleState)
    assert state.country_iso3 == "KEN"
    assert state.macro_state.urbanization_ratio == 0.31
    assert state.macro_state.youth_bulge == 0.205
    assert state.macro_state.debt_to_gdp == 0.714
    assert state.graph.node_properties("capital_city")["role"] == "capital"
    assert state.graph.node_properties("regime")["role"] == "ruling_regime"


def test_initialize_live_swarm_injects_country_specific_leader_profiles():
    irn_state = initialize_live_swarm("IRN", macro_update_fixture(), particle_count=1, seed=3).particles[0].state
    usa_state = initialize_live_swarm("USA", macro_update_fixture(), particle_count=1, seed=3).particles[0].state
    fra_state = initialize_live_swarm("FRA", macro_update_fixture(), particle_count=1, seed=3).particles[0].state

    assert leader_profile_for_country("IRN").fusion_factor > 0.85
    assert irn_state.leader_profile.fusion_factor > 0.85
    assert usa_state.leader_profile.lta_complexity < 0.3
    assert usa_state.leader_profile.lta_distrust > 0.7
    assert fra_state.leader_profile.lta_complexity == 0.5
    assert fra_state.leader_profile.lta_distrust == 0.5
    assert fra_state.leader_profile.fusion_factor == 0.3


def test_format_day_readout_includes_event_volume_and_mobilization_consensus():
    readout = format_day_readout(
        day_number=4,
        observed_date=date(2026, 5, 13),
        event_count=12,
        threat_lambda=0.4,
        mobilization_consensus=0.4,
        effective_sample_size=16.8,
    )

    assert readout.startswith("Day 4 (2026-05-13): GDELT recorded 12 violent events.")
    assert "Swarm Consensus: 40% of particles triggered a mass mobilization cascade" in readout
    assert "lambda(t)=0.400" in readout
    assert "ESS: 16.8" in readout


def test_run_live_engine_queries_real_clients_by_iso3_and_backtests_seven_days():
    world_bank_client = FakeWorldBankClient()
    gdelt_client = FakeGdeltClient()

    result = run_live_engine(
        "KEN",
        world_bank_client=world_bank_client,
        gdelt_client=gdelt_client,
        particle_count=20,
        days=7,
        end_date=date(2026, 5, 16),
        emit=False,
        resample_start=0.5,
    )

    assert world_bank_client.requested_country_codes == ["KEN"]
    assert gdelt_client.calls == [
        ("KE", date(2026, 5, 10)),
        ("KE", date(2026, 5, 11)),
        ("KE", date(2026, 5, 12)),
        ("KE", date(2026, 5, 13)),
        ("KE", date(2026, 5, 14)),
        ("KE", date(2026, 5, 15)),
        ("KE", date(2026, 5, 16)),
    ]
    assert len(result.day_summaries) == 7
    assert len(result.readouts) == 7
    assert "Day 4" in result.readouts[3]
    assert "GDELT recorded 12 violent events" in result.readouts[3]
    assert result.day_summaries[0].mobilization_consensus == 0.0
    assert result.day_summaries[-1].mobilization_consensus > result.day_summaries[0].mobilization_consensus


def test_run_live_engine_applies_irn_fused_identity_logic_and_exports_highest_weighted_particle():
    neo4j_graph = FakeNeo4jGraph()

    result = run_live_engine(
        "IRN",
        world_bank_client=FakeWorldBankClient(),
        gdelt_client=FakeGdeltClient(),
        neo4j_graph=neo4j_graph,
        particle_count=20,
        days=7,
        end_date=date(2026, 5, 16),
        emit=False,
        export_neo4j=True,
        resample_start=0.5,
    )

    country_node = neo4j_graph.nodes["IRN"]
    assert result.neo4j_export.attempted
    assert result.neo4j_export.succeeded
    assert result.best_particle_state is not None
    assert result.best_particle_state.leader_decision == "mutually_destructive_conflict"
    assert country_node["fusion_factor"] > 0.85
    assert country_node["leader_decision"] == "mutually_destructive_conflict"
    assert "relative_wage" in country_node
    assert neo4j_graph.nodes["province_north"]["complex_behavior_adopted"]
    assert neo4j_graph.edges[("province_east", "province_north")]["omega"] == 0.2


def test_live_observation_does_not_let_watts_cross_weak_bridge_without_centola_width():
    smc = initialize_live_swarm(
        "KEN",
        {"urbanization_rate": 0.31, "youth_bulge": 0.205, "debt_to_gdp": 0.714},
        particle_count=10,
        seed=3,
    )
    weak_bridge_state = smc.particles[7].state

    _apply_live_observation_to_swarm(
        smc,
        LiveDayObservation(
            day_number=1,
            observed_date=date(2026, 5, 10),
            event_count=20,
            goldstein_salience=60.0,
            threat_lambda=1.0,
        ),
    )

    assert weak_bridge_state.watts_nodes["province_north"].active_state == 1
    assert weak_bridge_state.watts_nodes["province_east"].active_state == 0
    assert weak_bridge_state.watts_nodes["province_west"].active_state == 0
    assert not weak_bridge_state.complex_agents["province_east"].behavior_adopted
    assert not weak_bridge_state.complex_agents["province_west"].behavior_adopted


def test_export_live_particle_to_neo4j_serializes_macro_profile_agent_and_network_state():
    state = initialize_live_swarm("USA", macro_update_fixture(), particle_count=1, seed=3).particles[0].state
    _apply_live_observation_to_swarm(
        SequentialMonteCarlo([Particle(state=state, weight=1.0)]),
        LiveDayObservation(
            day_number=1,
            observed_date=date(2026, 5, 10),
            event_count=20,
            goldstein_salience=60.0,
            threat_lambda=1.0,
        ),
    )
    neo4j_graph = FakeNeo4jGraph()

    export_live_particle_to_neo4j(state, neo4j_graph, run_id="test-run")

    assert neo4j_graph.nodes["USA"]["run_id"] == "test-run"
    assert neo4j_graph.nodes["USA"]["lta_complexity"] < 0.3
    assert neo4j_graph.nodes["USA"]["debt_to_gdp"] == 0.714
    assert neo4j_graph.nodes["environment"]["environmental_threat_lambda"] == 1.0
    assert "affect_v" in neo4j_graph.nodes["province_north"]
    assert "watts_active_state" in neo4j_graph.nodes["province_north"]
    assert "complex_behavior_adopted" in neo4j_graph.nodes["province_north"]
    assert ("capital_city", "province_east") in neo4j_graph.edges


class FakeWorldBankClient:
    def __init__(self) -> None:
        self.requested_country_codes: list[str] = []

    def fetch_macro_state_update(self, iso_country_code: str) -> dict[str, float]:
        self.requested_country_codes.append(iso_country_code)
        return {"urbanization_rate": 0.31, "youth_bulge": 0.205, "debt_to_gdp": 0.714}


class FakeGdeltClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, date]] = []
        self.event_counts = [0, 1, 3, 12, 14, 18, 22]

    def fetch_daily_threat_index(self, *, country_code: str, day: date) -> dict[str, float | int]:
        self.calls.append((country_code, day))
        event_count = self.event_counts[len(self.calls) - 1]
        return {
            "event_count": event_count,
            "goldstein_salience": float(event_count * 3),
            "environmental_threat_lambda": min(1.0, event_count / 20.0),
        }


class FakeNeo4jGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, dict] = {}
        self.edges: dict[tuple[str, str], dict] = {}

    def add_node(self, node_id, **properties):
        self.nodes[str(node_id)] = dict(properties)

    def add_edge(self, source, target, **properties):
        self.edges[(str(source), str(target))] = dict(properties)


def macro_update_fixture() -> dict[str, float]:
    return {"urbanization_rate": 0.31, "youth_bulge": 0.205, "debt_to_gdp": 0.714}
