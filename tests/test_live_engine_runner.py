from __future__ import annotations

from datetime import date

from run_live_engine import (
    LiveParticleState,
    LiveDayObservation,
    _apply_live_observation_to_swarm,
    build_backtest_dates,
    format_day_readout,
    initialize_live_swarm,
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
