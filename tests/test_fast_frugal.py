import pytest

from andoworldstate.theories.fast_frugal import FastFrugalAgent


def test_fast_frugal_tree_exits_immediately_on_first_triggered_non_final_cue():
    agent = FastFrugalAgent(unique_id="a", cue_hierarchy=["military_buildup", "food_shortage", "protests"])

    decision = agent.evaluate_threat_environment(
        {
            "military_buildup": True,
            "food_shortage": False,
            "protests": False,
        }
    )

    assert decision == 1


def test_fast_frugal_tree_final_cue_forces_binary_safe_decision():
    agent = FastFrugalAgent(unique_id="a", cue_hierarchy=["military_buildup", "food_shortage"])

    decision = agent.evaluate_threat_environment(
        {
            "military_buildup": False,
            "food_shortage": False,
        }
    )

    assert decision == 0


def test_fast_frugal_tree_requires_at_least_one_cue():
    with pytest.raises(ValueError, match="cue_hierarchy"):
        FastFrugalAgent(unique_id="a", cue_hierarchy=[])
