from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Any, Mapping

E = 2.718281828459045


@dataclass
class MacroState:
    relative_wage: float
    urbanization_ratio: float
    youth_bulge: float
    relative_elite_income: float
    elite_ratio: float
    debt_to_gdp: float
    distrust: float

    def mass_mobilization_potential(self) -> float:
        return (1.0 / self._positive(self.relative_wage, "relative_wage")) * self.urbanization_ratio * self.youth_bulge

    def elite_mobilization_potential(self) -> float:
        return (1.0 / self._positive(self.relative_elite_income, "relative_elite_income")) * self.elite_ratio

    def state_fiscal_distress(self) -> float:
        return self.debt_to_gdp * self.distrust

    def compute_psi(self) -> float:
        return (
            self.mass_mobilization_potential()
            * self.elite_mobilization_potential()
            * self.state_fiscal_distress()
        )

    @staticmethod
    def _positive(value: float, name: str) -> float:
        if value <= 0:
            raise ValueError(f"{name} must be positive")
        return value


def assimilate_world_bank_data(state: MacroState, world_bank_data: Mapping[str, float]) -> None:
    if "relative_wage" in world_bank_data:
        state.relative_wage = world_bank_data["relative_wage"]
    if "debt_to_gdp" in world_bank_data:
        state.debt_to_gdp = world_bank_data["debt_to_gdp"]
    if "urbanization_rate" in world_bank_data:
        state.urbanization_ratio = world_bank_data["urbanization_rate"]


def logistic_instability(psi: float) -> float:
    if psi >= 0:
        return 1.0 / (1.0 + exp(-psi))
    exp_psi = exp(psi)
    return exp_psi / (1.0 + exp_psi)


def particle_filter_sdt_update(
    particle: Any,
    world_bank_data: Mapping[str, float],
    gdelt_instability_index: float,
    *,
    penalty_scale: float = 10.0,
) -> None:
    assimilate_world_bank_data(particle.state, world_bank_data)
    expected_instability = logistic_instability(particle.state.compute_psi())
    error = abs(expected_instability - gdelt_instability_index)
    particle.weight *= E ** (-error * penalty_scale)

