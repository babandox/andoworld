from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from andoworldstate.smc import Particle
from andoworldstate.theories.poliheuristic import PoliheuristicLeader
from andoworldstate.theories.structural_demographic import MacroState


@dataclass(frozen=True)
class LeaderProfile:
    lta_complexity: float = 0.5
    lta_distrust: float = 0.5
    fusion_factor: float = 0.0

    def __post_init__(self) -> None:
        _validate_unit_interval(self.lta_complexity, "lta_complexity")
        _validate_unit_interval(self.lta_distrust, "lta_distrust")
        _validate_unit_interval(self.fusion_factor, "fusion_factor")


@dataclass
class CognitiveHeuristicState:
    macro_state: MacroState
    leaders: Sequence[PoliheuristicLeader]


@dataclass(frozen=True)
class MacroShockObservation:
    debt_to_gdp: float
    polling_drop: float
    debt_baseline: float
    debt_stress_weight: float
    polling_drop_weight: float

    def __post_init__(self) -> None:
        if self.debt_to_gdp < 0:
            raise ValueError("debt_to_gdp must be non-negative")
        if self.polling_drop < 0:
            raise ValueError("polling_drop must be non-negative")
        if self.debt_baseline < 0:
            raise ValueError("debt_baseline must be non-negative")
        if self.debt_stress_weight < 0:
            raise ValueError("debt_stress_weight must be non-negative")
        if self.polling_drop_weight < 0:
            raise ValueError("polling_drop_weight must be non-negative")


def mock_macro_shock_observation() -> MacroShockObservation:
    return MacroShockObservation(
        debt_to_gdp=0.92,
        polling_drop=0.18,
        debt_baseline=0.6,
        debt_stress_weight=2.0,
        polling_drop_weight=5.0,
    )


def update_leader_thresholds_from_macro_shock(
    particles: list[Particle],
    shock: MacroShockObservation,
) -> None:
    debt_spike = max(0.0, shock.debt_to_gdp - shock.debt_baseline)
    threshold_delta = (debt_spike * shock.debt_stress_weight) + (
        shock.polling_drop * shock.polling_drop_weight
    )
    for particle in particles:
        state = _cognitive_state(particle)
        state.macro_state.debt_to_gdp = shock.debt_to_gdp
        for leader in state.leaders:
            leader.assimilate_survival_threshold(
                leader.political_survival_threshold + threshold_delta
            )


def _cognitive_state(particle: Particle) -> CognitiveHeuristicState:
    if isinstance(particle.state, CognitiveHeuristicState):
        return particle.state
    raise ValueError("particle state must be CognitiveHeuristicState")


def _validate_unit_interval(value: float, name: str) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in the closed interval [0, 1]")
