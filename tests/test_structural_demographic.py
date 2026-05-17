from math import isclose

from andoworldstate.theories.structural_demographic import (
    MacroState,
    assimilate_world_bank_data,
    logistic_instability,
    particle_filter_sdt_update,
)


class Particle:
    def __init__(self, state):
        self.state = state
        self.weight = 1.0


def test_macro_state_computes_political_stress_indicator_multiplicatively():
    state = MacroState(
        relative_wage=0.5,
        urbanization_ratio=0.8,
        youth_bulge=0.25,
        relative_elite_income=0.4,
        elite_ratio=0.1,
        debt_to_gdp=0.6,
        distrust=0.5,
    )

    assert isclose(state.mass_mobilization_potential(), 2.0 * 0.8 * 0.25)
    assert isclose(state.elite_mobilization_potential(), 2.5 * 0.1)
    assert isclose(state.state_fiscal_distress(), 0.6 * 0.5)
    assert isclose(state.compute_psi(), (2.0 * 0.8 * 0.25) * (2.5 * 0.1) * (0.6 * 0.5))


def test_assimilate_world_bank_data_forces_hard_structural_observations_into_state():
    state = MacroState(1.0, 0.1, 0.1, 1.0, 0.1, 0.1, 0.1)

    assimilate_world_bank_data(
        state,
        {
            "relative_wage": 0.25,
            "debt_to_gdp": 0.75,
            "urbanization_rate": 0.65,
        },
    )

    assert isclose(state.relative_wage, 0.25)
    assert isclose(state.debt_to_gdp, 0.75)
    assert isclose(state.urbanization_ratio, 0.65)


def test_sdt_particle_update_penalizes_divergence_from_observed_instability():
    state = MacroState(0.5, 0.8, 0.25, 0.4, 0.1, 0.6, 0.5)
    particle = Particle(state)

    particle_filter_sdt_update(
        particle,
        world_bank_data={"relative_wage": 0.5, "debt_to_gdp": 0.6, "urbanization_rate": 0.8},
        gdelt_instability_index=0.4,
    )

    expected = logistic_instability(state.compute_psi())
    assert particle.weight < 1.0
    assert isclose(particle.weight, 2.718281828459045 ** (-abs(expected - 0.4) * 10), rel_tol=1e-9)
