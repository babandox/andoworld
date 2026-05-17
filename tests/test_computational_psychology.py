from andoworldstate.theories.agent_zero import AgentZero
from andoworldstate.theories.cognitive_heuristics import LeaderProfile
from andoworldstate.theories.fast_frugal import FFTAgent, FFTCue
from andoworldstate.theories.poliheuristic import DecisionOption, PoliheuristicLeader
from andoworldstate.theories.structural_demographic import MacroState


class EconomicCueProbe:
    name = "economic_relief"
    decision_on_trigger = 0

    def __init__(self) -> None:
        self.evaluations = 0

    def is_triggered(self, macro_state, agent_zero):
        self.evaluations += 1
        return True


def test_fused_leader_chooses_mutually_destructive_conflict_over_ideological_capitulation():
    leader = PoliheuristicLeader(
        political_survival_threshold=-20.0,
        weights={"military": 0.5, "economic": 0.5},
        fusion_factor=0.95,
        ideological_preservation_threshold=0.8,
    )
    options = [
        DecisionOption(
            "ideological_capitulation",
            political=10.0,
            military=50.0,
            economic=50.0,
            ideological=0.1,
            violates_ideology=True,
        ),
        DecisionOption(
            "mutually_destructive_conflict",
            political=-10.0,
            military=-100.0,
            economic=-100.0,
            ideological=1.0,
        ),
    ]

    assert leader.evaluate_options(options) == "mutually_destructive_conflict"


def test_impulsive_distrustful_leader_reorders_fft_to_threat_cue_and_exits_early():
    macro_state = MacroState(
        relative_wage=0.8,
        urbanization_ratio=0.6,
        youth_bulge=0.2,
        relative_elite_income=0.5,
        elite_ratio=0.1,
        debt_to_gdp=0.4,
        distrust=0.2,
    )
    agent_zero = AgentZero("leader-agent", 0.1, 0.1, 1.0, affect_v=0.45)
    economic_probe = EconomicCueProbe()
    profile = LeaderProfile(lta_complexity=0.2, lta_distrust=0.9, fusion_factor=0.2)
    fft_agent = FFTAgent(
        unique_id="fft-populist",
        cue_hierarchy=[
            economic_probe,
            FFTCue.epstein_fear_greater_equal(threshold=0.8),
        ],
    )

    decision = fft_agent.evaluate_from_state(macro_state, agent_zero, leader_profile=profile)

    assert decision.choice == 1
    assert decision.triggered_cue == "epstein_fear"
    assert decision.evaluated_cues == ("epstein_fear",)
    assert economic_probe.evaluations == 0
