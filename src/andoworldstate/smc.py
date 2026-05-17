from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from random import Random
from typing import Any, Callable


@dataclass
class Particle:
    state: Any
    weight: float = 1.0

    def __post_init__(self) -> None:
        if self.weight < 0:
            raise ValueError("particle weight must be non-negative")


class SequentialMonteCarlo:
    def __init__(self, particles: list[Particle]) -> None:
        if not particles:
            raise ValueError("particles must not be empty")
        self.particles = particles

    def normalize_weights(self) -> None:
        total = sum(particle.weight for particle in self.particles)
        if total <= 0:
            raise ValueError("at least one particle must have positive weight")
        for particle in self.particles:
            particle.weight = particle.weight / total

    def effective_sample_size(self) -> float:
        weights = self._normalized_weights()
        return 1.0 / sum(weight * weight for weight in weights)

    def systematic_resample(
        self,
        *,
        start: float | None = None,
        rng: Random | None = None,
        mutation: Callable[[Any], Any] | None = None,
    ) -> list[Particle]:
        weights = self._normalized_weights()
        count = len(self.particles)
        if start is None:
            start = (rng or Random()).random()
        if not 0 <= start < 1:
            raise ValueError("start must be in the half-open interval [0, 1)")

        positions = [(start + index) / count for index in range(count)]
        cumulative = []
        running = 0.0
        for weight in weights:
            running += weight
            cumulative.append(running)

        selected: list[Particle] = []
        source_index = 0
        for position in positions:
            while position > cumulative[source_index]:
                source_index += 1
            state = deepcopy(self.particles[source_index].state)
            if mutation is not None:
                state = mutation(state)
            selected.append(Particle(state=state, weight=1.0 / count))

        self.particles = selected
        return selected

    def _normalized_weights(self) -> list[float]:
        total = sum(particle.weight for particle in self.particles)
        if total <= 0:
            raise ValueError("at least one particle must have positive weight")
        return [particle.weight / total for particle in self.particles]

