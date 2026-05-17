from __future__ import annotations

import json
from collections.abc import Callable, Hashable, Mapping, Sequence
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen


URBANIZATION_INDICATOR = "SP.URB.TOTL.IN.ZS"
YOUTH_POPULATION_INDICATOR = "SP.POP.1524.TO.ZS"
DEBT_TO_GDP_INDICATOR = "GC.DOD.TOTL.GD.ZS"

INDICATOR_TO_MACRO_KEY = {
    URBANIZATION_INDICATOR: "urbanization_rate",
    YOUTH_POPULATION_INDICATOR: "youth_bulge",
    DEBT_TO_GDP_INDICATOR: "debt_to_gdp",
}

MACRO_UPDATE_TO_GRAPH_PROPERTY = {
    "urbanization_rate": "urbanization_ratio",
    "youth_bulge": "youth_bulge",
    "debt_to_gdp": "debt_to_gdp",
}

JsonFetcher = Callable[[str], Any]


class WorldBankClient:
    """Fetch and normalize World Bank indicators into Turchin macro-state inputs."""

    def __init__(
        self,
        *,
        fetch_json: JsonFetcher | None = None,
        base_url: str = "https://api.worldbank.org/v2",
    ) -> None:
        self._fetch_json = fetch_json or _default_fetch_json
        self._base_url = base_url.rstrip("/")

    def fetch_macro_state_update(self, iso_country_code: str) -> dict[str, float]:
        payload = self._fetch_json(self._macro_state_url(iso_country_code))
        return self.parse_macro_state_payload(payload)

    def parse_macro_state_payload(self, payload: Any) -> dict[str, float]:
        records = _extract_records(payload)
        latest_by_indicator: dict[str, Mapping[str, Any]] = {}

        for record in records:
            if not isinstance(record, Mapping):
                continue
            indicator_id = _indicator_id(record)
            if indicator_id not in INDICATOR_TO_MACRO_KEY or record.get("value") is None:
                continue
            previous = latest_by_indicator.get(indicator_id)
            if previous is None or _record_year(record) > _record_year(previous):
                latest_by_indicator[indicator_id] = record

        return {
            macro_key: _percent_to_ratio(latest_by_indicator[indicator_id]["value"])
            for indicator_id, macro_key in INDICATOR_TO_MACRO_KEY.items()
            if indicator_id in latest_by_indicator
        }

    def _macro_state_url(self, iso_country_code: str) -> str:
        country = iso_country_code.upper()
        indicators = ";".join(INDICATOR_TO_MACRO_KEY)
        query = urlencode({"format": "json", "per_page": "100", "mrnev": "1", "source": "2"})
        return f"{self._base_url}/country/{country}/indicator/{indicators}?{query}"


def apply_world_bank_update_to_graph(
    graph: Any,
    node_id: Hashable,
    update: Mapping[str, float],
) -> None:
    """Apply normalized World Bank values through the graph adapter contract."""

    for update_key, graph_property in MACRO_UPDATE_TO_GRAPH_PROPERTY.items():
        if update_key in update:
            graph.set_node_property(node_id, graph_property, update[update_key])


def _default_fetch_json(url: str) -> Any:
    with urlopen(url, timeout=30) as response:
        return json.load(response)


def _extract_records(payload: Any) -> Sequence[Any]:
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)) and len(payload) >= 2:
        records = payload[1]
        if isinstance(records, Sequence) and not isinstance(records, (str, bytes)):
            return records
    return ()


def _indicator_id(record: Mapping[str, Any]) -> str | None:
    indicator = record.get("indicator")
    if isinstance(indicator, Mapping):
        value = indicator.get("id")
        return str(value) if value is not None else None
    return None


def _record_year(record: Mapping[str, Any]) -> int:
    try:
        return int(str(record.get("date", "0"))[:4])
    except ValueError:
        return 0


def _percent_to_ratio(value: Any) -> float:
    return round(float(value) / 100.0, 6)

