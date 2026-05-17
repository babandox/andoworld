from __future__ import annotations

import csv
import io
import re
import zipfile
from collections.abc import Callable, Hashable, Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any
from urllib.request import urlopen


DEFAULT_CIVIL_UNREST_ROOT_CODES = frozenset({"14", "17", "18", "19", "20"})
GDELT_LAST_UPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
GDELT_V2_ARCHIVE_BASE_URL = "http://data.gdeltproject.org/gdeltv2"

TextFetcher = Callable[[str], str]
BytesFetcher = Callable[[str], bytes]


@dataclass(frozen=True)
class GdeltEvent:
    sql_date: str
    event_root_code: str
    goldstein_scale: float
    action_geo_country_code: str


class GdeltClient:
    """Fetch GDELT event exports and normalize unrest signals for Epstein threat."""

    def __init__(
        self,
        *,
        fetch_text: TextFetcher | None = None,
        fetch_bytes: BytesFetcher | None = None,
        latest_update_url: str = GDELT_LAST_UPDATE_URL,
        archive_base_url: str = GDELT_V2_ARCHIVE_BASE_URL,
        root_event_codes: Iterable[str] | None = None,
        threat_normalization: float = 100.0,
    ) -> None:
        self._fetch_text = fetch_text or _default_fetch_text
        self._fetch_bytes = fetch_bytes or _default_fetch_bytes
        self._latest_update_url = latest_update_url
        self._archive_base_url = archive_base_url.rstrip("/")
        self._root_event_codes = frozenset(root_event_codes or DEFAULT_CIVIL_UNREST_ROOT_CODES)
        self._threat_normalization = float(threat_normalization)

    def fetch_latest_threat_index(self, *, country_code: str) -> dict[str, float | int]:
        latest_update = self._fetch_text(self._latest_update_url)
        export_url = self._extract_latest_export_url(latest_update)
        export_bytes = self._fetch_bytes(export_url)
        events = self.parse_events_csv(_decode_export(export_url, export_bytes), country_code=country_code)
        return self.calculate_threat_index(events)

    def fetch_daily_threat_index(
        self,
        *,
        country_code: str,
        day: date,
        interval_minutes: int = 15,
    ) -> dict[str, float | int]:
        events: list[GdeltEvent] = []
        for export_url in self.daily_export_urls(day=day, interval_minutes=interval_minutes):
            export_bytes = self._fetch_bytes(export_url)
            events.extend(self.parse_events_csv(_decode_export(export_url, export_bytes), country_code=country_code))
        return self.calculate_threat_index(events)

    def daily_export_urls(self, *, day: date, interval_minutes: int = 15) -> list[str]:
        if interval_minutes <= 0:
            raise ValueError("interval_minutes must be positive")
        minutes_per_day = 24 * 60
        if minutes_per_day % interval_minutes != 0:
            raise ValueError("interval_minutes must divide evenly into one day")

        current = datetime.combine(day, time.min)
        return [
            f"{self._archive_base_url}/{(current + timedelta(minutes=offset)).strftime('%Y%m%d%H%M%S')}.export.CSV.zip"
            for offset in range(0, minutes_per_day, interval_minutes)
        ]

    def parse_events_csv(
        self,
        csv_text: str,
        *,
        country_code: str,
        root_event_codes: Iterable[str] | None = None,
    ) -> list[GdeltEvent]:
        accepted_root_codes = frozenset(root_event_codes or self._root_event_codes)
        accepted_country = country_code.upper()
        events: list[GdeltEvent] = []

        for row in csv.reader(io.StringIO(csv_text), delimiter="\t"):
            event = _parse_event_row(row)
            if event is None:
                continue
            if event.action_geo_country_code.upper() != accepted_country:
                continue
            if event.event_root_code not in accepted_root_codes:
                continue
            events.append(event)

        return events

    def calculate_threat_index(self, events: Iterable[GdeltEvent]) -> dict[str, float | int]:
        event_list = list(events)
        goldstein_salience = round(sum(max(0.0, -event.goldstein_scale) for event in event_list), 6)
        raw_lambda = (len(event_list) + goldstein_salience) / self._threat_normalization

        return {
            "event_count": len(event_list),
            "goldstein_salience": goldstein_salience,
            "environmental_threat_lambda": round(min(1.0, raw_lambda), 6),
        }

    def _extract_latest_export_url(self, latest_update: str) -> str:
        match = re.search(r"https?://\S+?\.export\.CSV(?:\.zip)?", latest_update)
        if match is None:
            raise ValueError("GDELT lastupdate.txt did not include an event export CSV URL")
        return match.group(0)


def apply_gdelt_threat_to_graph(
    graph: Any,
    node_id: Hashable,
    threat_index: Mapping[str, float | int],
) -> None:
    """Apply normalized GDELT threat through the graph adapter contract."""

    graph.set_node_property(
        node_id,
        "environmental_threat_lambda",
        float(threat_index["environmental_threat_lambda"]),
    )


def _default_fetch_text(url: str) -> str:
    with urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8")


def _default_fetch_bytes(url: str) -> bytes:
    with urlopen(url, timeout=30) as response:
        return response.read()


def _decode_export(export_url: str, export_bytes: bytes) -> str:
    if export_url.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(export_bytes)) as archive:
            names = archive.namelist()
            if not names:
                raise ValueError("GDELT export archive is empty")
            with archive.open(names[0]) as csv_file:
                return csv_file.read().decode("utf-8")
    return export_bytes.decode("utf-8")


def _parse_event_row(row: list[str]) -> GdeltEvent | None:
    try:
        return GdeltEvent(
            sql_date=row[1],
            event_root_code=row[28],
            goldstein_scale=float(row[30]),
            action_geo_country_code=row[53],
        )
    except (IndexError, ValueError):
        return None

