from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class DecisionOption:
    option_id: str
    political: float
    military: float
    economic: float


@dataclass
class PoliheuristicLeader:
    political_survival_threshold: float
    weights: Mapping[str, float] = field(default_factory=lambda: {"military": 0.6, "economic": 0.4})

    def evaluate_options(self, options_matrix: list[DecisionOption]) -> str:
        if not options_matrix:
            raise ValueError("options_matrix must not be empty")

        surviving_options = [
            option for option in options_matrix if option.political >= self.political_survival_threshold
        ]
        if not surviving_options:
            return max(options_matrix, key=lambda option: option.political).option_id

        best_option = max(surviving_options, key=self._stage_two_utility)
        return best_option.option_id

    def assimilate_survival_threshold(self, political_survival_threshold: float) -> None:
        self.political_survival_threshold = political_survival_threshold

    def _stage_two_utility(self, option: DecisionOption) -> float:
        return (
            option.military * self.weights.get("military", 0.0)
            + option.economic * self.weights.get("economic", 0.0)
        )

