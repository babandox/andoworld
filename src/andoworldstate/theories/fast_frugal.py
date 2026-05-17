from __future__ import annotations

from collections.abc import Callable, Hashable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from andoworldstate.theories.agent_zero import AgentZero
from andoworldstate.theories.structural_demographic import MacroState


LOW_COMPLEXITY_THRESHOLD = 0.3
LOW_COMPLEXITY_THRESHOLD_MULTIPLIER = 0.5
HIGH_DISTRUST_THRESHOLD = 0.7
THREAT_CUE_TERMS = ("threat", "military", "security", "fear", "crackdown", "violence", "war")


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


@dataclass(frozen=True)
class FFTDecision:
    choice: int
    triggered_cue: str | None
    evaluated_cues: tuple[str, ...]


@dataclass(frozen=True)
class FFTCue:
    name: str
    extractor: Callable[[MacroState, AgentZero], float]
    threshold: float
    decision_on_trigger: int = 1
    comparison: str = "greater_equal"

    @classmethod
    def macro_greater_equal(cls, name: str, macro_field: str, *, threshold: float) -> "FFTCue":
        return cls(
            name=name,
            extractor=lambda macro_state, agent_zero: float(getattr(macro_state, macro_field)),
            threshold=threshold,
        )

    @classmethod
    def wage_inverse_greater_equal(cls, *, threshold: float) -> "FFTCue":
        return cls(
            name="wage_inverse",
            extractor=lambda macro_state, agent_zero: 1.0 / macro_state.relative_wage,
            threshold=threshold,
        )

    @classmethod
    def epstein_fear_greater_equal(cls, *, threshold: float) -> "FFTCue":
        return cls(
            name="epstein_fear",
            extractor=lambda macro_state, agent_zero: agent_zero.affect_v,
            threshold=threshold,
        )

    def is_triggered(self, macro_state: MacroState, agent_zero: AgentZero) -> bool:
        value = self.extractor(macro_state, agent_zero)
        if self.comparison == "greater_equal":
            return value >= self.threshold
        if self.comparison == "less_equal":
            return value <= self.threshold
        raise ValueError(f"Unsupported FFT cue comparison: {self.comparison!r}")


@dataclass
class FFTAgent:
    unique_id: Hashable
    cue_hierarchy: Sequence[Any]

    def __post_init__(self) -> None:
        if not self.cue_hierarchy:
            raise ValueError("cue_hierarchy must contain at least one cue")

    def evaluate_from_state(
        self,
        macro_state: MacroState,
        agent_zero: AgentZero,
        *,
        leader_profile: Any | None = None,
    ) -> FFTDecision:
        evaluated: list[str] = []
        cue_hierarchy = _profile_adjusted_cues(self.cue_hierarchy, leader_profile)
        threshold_multiplier = _profile_threshold_multiplier(leader_profile)
        last_index = len(cue_hierarchy) - 1
        for index, cue in enumerate(cue_hierarchy):
            evaluated.append(cue.name)
            triggered = _cue_is_triggered(
                cue,
                macro_state,
                agent_zero,
                threshold_multiplier=threshold_multiplier,
            )
            if index < last_index:
                if triggered:
                    return FFTDecision(
                        choice=cue.decision_on_trigger,
                        triggered_cue=cue.name,
                        evaluated_cues=tuple(evaluated),
                    )
            else:
                return FFTDecision(
                    choice=cue.decision_on_trigger if triggered else 0,
                    triggered_cue=cue.name if triggered else None,
                    evaluated_cues=tuple(evaluated),
                )

        return FFTDecision(choice=0, triggered_cue=None, evaluated_cues=tuple(evaluated))


def _profile_threshold_multiplier(leader_profile: Any | None) -> float:
    if leader_profile is not None and getattr(leader_profile, "lta_complexity", 1.0) < LOW_COMPLEXITY_THRESHOLD:
        return LOW_COMPLEXITY_THRESHOLD_MULTIPLIER
    return 1.0


def _profile_adjusted_cues(cue_hierarchy: Sequence[Any], leader_profile: Any | None) -> list[Any]:
    cues = list(cue_hierarchy)
    if leader_profile is None or getattr(leader_profile, "lta_distrust", 0.0) <= HIGH_DISTRUST_THRESHOLD:
        return cues
    threat_cues = [cue for cue in cues if _is_threat_cue(cue)]
    other_cues = [cue for cue in cues if not _is_threat_cue(cue)]
    return threat_cues + other_cues


def _is_threat_cue(cue: Any) -> bool:
    cue_name = str(getattr(cue, "name", "")).lower()
    return any(term in cue_name for term in THREAT_CUE_TERMS)


def _cue_is_triggered(
    cue: Any,
    macro_state: MacroState,
    agent_zero: AgentZero,
    *,
    threshold_multiplier: float,
) -> bool:
    if threshold_multiplier == 1.0 or not all(
        hasattr(cue, attribute) for attribute in ("extractor", "threshold", "comparison")
    ):
        return bool(cue.is_triggered(macro_state, agent_zero))

    value = cue.extractor(macro_state, agent_zero)
    threshold = cue.threshold * threshold_multiplier
    if cue.comparison == "greater_equal":
        return value >= threshold
    if cue.comparison == "less_equal":
        return value <= threshold
    raise ValueError(f"Unsupported FFT cue comparison: {cue.comparison!r}")
