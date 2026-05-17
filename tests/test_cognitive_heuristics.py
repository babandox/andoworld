from andoworldstate.smc import Particle
from andoworldstate.theories.agent_zero import AgentZero
from andoworldstate.theories.cognitive_heuristics import (
    CognitiveHeuristicState,
    MacroShockObservation,
    mock_macro_shock_observation,
    update_leader_thresholds_from_macro_shock,
)
from andoworldstate.theories.fast_frugal import FFTAgent, FFTCue
from andoworldstate.theories.poliheuristic import DecisionOption, PoliheuristicLeader
from andoworldstate.theories.structural_demographic import MacroState


class ProbeCue:
    name = "lower_priority_probe"
    decision_on_trigger = 1

    def __init__(self):
        self.evaluations = 0

    def is_triggered(self, macro_state, agent_zero):
        self.evaluations += 1
        return True


def test_fft_agent_derives_distrust_cue_from_macro_state_and_halts_before_lower_cues():
    macro_state = macro_state_fixture(distrust=0.85, relative_wage=0.9)
    agent_zero = AgentZero("agent-1", 0.1, 0.1, 1.0, affect_v=0.1)
    lower_priority_probe = ProbeCue()
    agent = FFTAgent(
        unique_id="fft-1",
        cue_hierarchy=[
            FFTCue.macro_greater_equal("state_distrust", "distrust", threshold=0.8),
            lower_priority_probe,
        ],
    )

    decision = agent.evaluate_from_state(macro_state, agent_zero)

    assert decision.choice == 1
    assert decision.triggered_cue == "state_distrust"
    assert decision.evaluated_cues == ("state_distrust",)
    assert lower_priority_probe.evaluations == 0


def test_fft_agent_maps_inverse_wage_pressure_and_epstein_fear_into_boolean_cues():
    macro_state = macro_state_fixture(distrust=0.2, relative_wage=0.4)
    agent_zero = AgentZero("agent-1", 0.1, 0.1, 1.0, affect_v=0.7)
    agent = FFTAgent(
        unique_id="fft-1",
        cue_hierarchy=[
            FFTCue.wage_inverse_greater_equal(threshold=2.0),
            FFTCue.epstein_fear_greater_equal(threshold=0.6),
        ],
    )

    decision = agent.evaluate_from_state(macro_state, agent_zero)

    assert decision.choice == 1
    assert decision.triggered_cue == "wage_inverse"
    assert decision.evaluated_cues == ("wage_inverse",)


def test_fft_agent_final_cue_forces_binary_choice_when_no_prior_exit_triggers():
    macro_state = macro_state_fixture(distrust=0.2, relative_wage=0.9)
    agent_zero = AgentZero("agent-1", 0.1, 0.1, 1.0, affect_v=0.1)
    agent = FFTAgent(
        unique_id="fft-1",
        cue_hierarchy=[
            FFTCue.macro_greater_equal("state_distrust", "distrust", threshold=0.8),
            FFTCue.epstein_fear_greater_equal(threshold=0.6),
        ],
    )

    decision = agent.evaluate_from_state(macro_state, agent_zero)

    assert decision.choice == 0
    assert decision.triggered_cue is None
    assert decision.evaluated_cues == ("state_distrust", "epstein_fear")


def test_poliheuristic_rejects_high_utility_option_below_political_survival_threshold():
    leader = PoliheuristicLeader(political_survival_threshold=-2.0, weights={"military": 0.9, "economic": 0.1})
    options = [
        DecisionOption("reckless_war", political=-5.0, military=100.0, economic=100.0),
        DecisionOption("limited_sanctions", political=-1.0, military=1.0, economic=1.0),
    ]

    assert leader.evaluate_options(options) == "limited_sanctions"


def test_macro_shock_updates_smc_particle_leader_thresholds_from_turchin_stress_and_polling_drop():
    leader = PoliheuristicLeader(political_survival_threshold=-3.0)
    particle = Particle(
        state=CognitiveHeuristicState(
            macro_state=macro_state_fixture(debt_to_gdp=0.6),
            leaders=[leader],
        ),
        weight=1.0,
    )
    shock = MacroShockObservation(
        debt_to_gdp=0.9,
        polling_drop=0.2,
        debt_baseline=0.6,
        debt_stress_weight=2.0,
        polling_drop_weight=5.0,
    )

    update_leader_thresholds_from_macro_shock([particle], shock)

    assert particle.state.macro_state.debt_to_gdp == 0.9
    assert leader.political_survival_threshold == -3.0 + (0.3 * 2.0) + (0.2 * 5.0)


def test_mock_macro_shock_observation_models_debt_spike_and_polling_drop():
    shock = mock_macro_shock_observation()

    assert shock.debt_to_gdp > shock.debt_baseline
    assert shock.polling_drop > 0


def macro_state_fixture(
    *,
    distrust=0.5,
    relative_wage=0.5,
    debt_to_gdp=0.6,
) -> MacroState:
    return MacroState(
        relative_wage=relative_wage,
        urbanization_ratio=0.8,
        youth_bulge=0.25,
        relative_elite_income=0.4,
        elite_ratio=0.1,
        debt_to_gdp=debt_to_gdp,
        distrust=distrust,
    )
