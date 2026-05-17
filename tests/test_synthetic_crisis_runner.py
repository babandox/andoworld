from run_synthetic_crisis import (
    SyntheticParticleState,
    build_synthetic_timeline,
    format_tick_readout,
    initialize_swarm,
    run_synthetic_crisis,
)


def test_synthetic_timeline_has_ten_weeks_and_expected_crisis_phases():
    timeline = build_synthetic_timeline()

    assert [observation.week for observation in timeline] == list(range(1, 11))
    assert all(observation.source == "synthetic" for observation in timeline)
    assert timeline[0].debt_to_gdp < timeline[1].debt_to_gdp < timeline[2].debt_to_gdp
    assert timeline[0].polling_drop == 0.0
    assert timeline[3].polling_drop > 0.0
    assert timeline[5].observed_protest_nodes >= {"province_east", "province_west"}
    assert timeline[6].observed_capital_ideology == "Insurgent"
    assert timeline[9].observed_capital_ideology == "Insurgent"


def test_initialize_swarm_defaults_to_one_hundred_particles_with_required_graph_nodes():
    smc = initialize_swarm(seed=7)

    assert len(smc.particles) == 100
    state = smc.particles[0].state
    assert isinstance(state, SyntheticParticleState)
    assert state.graph.node_properties("capital_city")["role"] == "capital"
    assert state.graph.node_properties("regime")["role"] == "ruling_regime"
    for province in ("province_north", "province_east", "province_west", "province_south"):
        assert state.graph.node_properties(province)["role"] == "province"


def test_tick_readout_contains_week_event_and_swarm_consensus():
    observation = build_synthetic_timeline()[0]

    readout = format_tick_readout(
        week=observation.week,
        event=observation.event,
        capital_collapse_consensus=0.42,
        effective_sample_size=61.5,
    )

    assert "Week 01" in readout
    assert observation.event in readout
    assert "Swarm Consensus: 42% of surviving particles predict Capital collapse" in readout
    assert "ESS: 61.5" in readout


def test_run_synthetic_crisis_returns_ten_readouts_and_rising_collapse_consensus():
    result = run_synthetic_crisis(particle_count=100, seed=7, emit=False)

    assert len(result.tick_summaries) == 10
    assert len(result.readouts) == 10
    assert result.readouts[0].startswith("Week 01")
    assert "Swarm Consensus:" in result.readouts[-1]
    assert result.tick_summaries[0].capital_collapse_consensus == 0.0
    assert result.tick_summaries[-1].capital_collapse_consensus >= 0.8
