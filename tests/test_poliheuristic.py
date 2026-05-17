from andoworldstate.theories.poliheuristic import DecisionOption, PoliheuristicLeader


def test_poliheuristic_eliminates_options_below_political_survival_threshold_before_utility():
    leader = PoliheuristicLeader(political_survival_threshold=-3.0, weights={"military": 0.6, "economic": 0.4})
    options = [
        DecisionOption("invade", political=-5.0, military=10.0, economic=10.0),
        DecisionOption("sanction", political=-1.0, military=2.0, economic=-4.0),
        DecisionOption("do_nothing", political=-2.0, military=-1.0, economic=5.0),
    ]

    assert leader.evaluate_options(options) == "do_nothing"


def test_poliheuristic_fallback_selects_least_politically_damaging_option_when_all_are_eliminated():
    leader = PoliheuristicLeader(political_survival_threshold=1.0, weights={"military": 0.6, "economic": 0.4})
    options = [
        DecisionOption("war", political=-5.0, military=10.0, economic=10.0),
        DecisionOption("sanctions", political=-2.0, military=1.0, economic=1.0),
    ]

    assert leader.evaluate_options(options) == "sanctions"
