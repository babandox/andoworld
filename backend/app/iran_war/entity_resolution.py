from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ResolvedMention:
    raw_text: str
    normalized_text: str
    entity_id: str | None
    status: str
    resolver_method: str
    confidence: str


class EntityResolver:
    def __init__(self, aliases: dict[str, str], ambiguous: set[str] | None = None) -> None:
        self._aliases = {self._normalize(alias): entity_id for alias, entity_id in aliases.items()}
        self._ambiguous = {self._normalize(value) for value in (ambiguous or set())}

    @classmethod
    def with_default_seed(cls) -> "EntityResolver":
        aliases = {
            "IRGC": "entity:irgc",
            "Islamic Revolutionary Guard Corps": "entity:irgc",
            "Revolutionary Guards": "entity:irgc",
            "Iranian Revolutionary Guards": "entity:irgc",
            "Tehran's elite forces": "entity:irgc",
            "IDF": "entity:idf",
            "Israel Defense Forces": "entity:idf",
            "Strait of Hormuz": "entity:hormuz",
            "Hormuz": "entity:hormuz",
            "Donald Trump": "entity:trump",
            "Trump": "entity:trump",
            "Truth Social": "entity:truth-social",
            "S&P 500": "entity:sp500",
            "SP500": "entity:sp500",
            "Brent": "entity:brent",
            "Brent crude": "entity:brent",
            "IAEA": "entity:iaea",
            "International Atomic Energy Agency": "entity:iaea",
            "Iran": "entity:iran",
            "Israel": "entity:israel",
            "United States": "entity:united-states",
        }
        return cls(aliases=aliases, ambiguous={"Tehran"})

    def resolve(self, raw_text: str) -> ResolvedMention:
        normalized = self._normalize(raw_text)
        if normalized in self._aliases:
            return ResolvedMention(raw_text, normalized, self._aliases[normalized], "resolved", "alias_seed", "high")
        if normalized in self._ambiguous:
            return ResolvedMention(raw_text, normalized, None, "ambiguous", "ambiguous_seed", "low")
        return ResolvedMention(raw_text, normalized, None, "unresolved", "no_match", "low")

    def _normalize(self, value: str) -> str:
        return re.sub(r"\s+", " ", value.strip().casefold())
