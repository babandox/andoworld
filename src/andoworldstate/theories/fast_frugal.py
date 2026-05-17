from __future__ import annotations

from collections.abc import Hashable, Mapping
from dataclasses import dataclass


@dataclass
class FastFrugalAgent:
    unique_id: Hashable
    cue_hierarchy: list[str]

    def __post_init__(self) -> None:
        if not self.cue_hierarchy:
            raise ValueError("cue_hierarchy must contain at least one cue")

    def evaluate_threat_environment(self, environment_data: Mapping[str, bool]) -> int:
        last_index = len(self.cue_hierarchy) - 1
        for index, cue in enumerate(self.cue_hierarchy):
            cue_present = bool(environment_data.get(cue, False))
            if index < last_index:
                if cue_present:
                    return 1
            else:
                return 1 if cue_present else 0
        return 0

