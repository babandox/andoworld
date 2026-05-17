from __future__ import annotations

import io
import zipfile

from andoworldstate.graph import InMemoryGraph
from andoworldstate.ingestion.gdelt import GdeltClient, apply_gdelt_threat_to_graph
from andoworldstate.ingestion.world_bank import WorldBankClient, apply_world_bank_update_to_graph


def test_world_bank_client_normalizes_macro_state_inputs_and_updates_graph_contract():
    requested_urls: list[str] = []

    def fetch_json(url: str):
        requested_urls.append(url)
        return [
            {"page": 1, "pages": 1, "per_page": 100, "total": 3},
            [
                {
                    "indicator": {"id": "SP.URB.TOTL.IN.ZS"},
                    "countryiso3code": "USA",
                    "date": "2024",
                    "value": 83.3,
                },
                {
                    "indicator": {"id": "SP.POP.1524.TO.ZS"},
                    "countryiso3code": "USA",
                    "date": "2024",
                    "value": 12.8,
                },
                {
                    "indicator": {"id": "GC.DOD.TOTL.GD.ZS"},
                    "countryiso3code": "USA",
                    "date": "2023",
                    "value": 97.4,
                },
            ],
        ]

    client = WorldBankClient(fetch_json=fetch_json)
    update = client.fetch_macro_state_update("USA")
    graph = InMemoryGraph()
    graph.add_node("USA")

    apply_world_bank_update_to_graph(graph, "USA", update)

    assert "country/USA/indicator/SP.URB.TOTL.IN.ZS;SP.POP.1524.TO.ZS;GC.DOD.TOTL.GD.ZS" in requested_urls[0]
    assert update == {
        "urbanization_rate": 0.833,
        "youth_bulge": 0.128,
        "debt_to_gdp": 0.974,
    }
    assert graph.node_properties("USA")["urbanization_ratio"] == 0.833
    assert graph.node_properties("USA")["youth_bulge"] == 0.128
    assert graph.node_properties("USA")["debt_to_gdp"] == 0.974


def test_gdelt_client_filters_events_and_computes_epstein_threat_index_from_goldstein_salience():
    latest_update = "123 abc http://data.gdeltproject.org/gdeltv2/20260517120000.export.CSV.zip\n"
    archive = zipped_csv(
        "\n".join(
            [
                gdelt_row(sql_date="20260517", root_code="14", goldstein="-5.0", country_code="US"),
                gdelt_row(sql_date="20260517", root_code="17", goldstein="-7.0", country_code="US"),
                gdelt_row(sql_date="20260517", root_code="04", goldstein="-10.0", country_code="US"),
                gdelt_row(sql_date="20260517", root_code="18", goldstein="-9.0", country_code="FR"),
            ]
        )
    )
    requested_text_urls: list[str] = []
    requested_binary_urls: list[str] = []

    def fetch_text(url: str) -> str:
        requested_text_urls.append(url)
        return latest_update

    def fetch_bytes(url: str) -> bytes:
        requested_binary_urls.append(url)
        return archive

    client = GdeltClient(fetch_text=fetch_text, fetch_bytes=fetch_bytes, threat_normalization=100.0)
    threat = client.fetch_latest_threat_index(country_code="US")
    graph = InMemoryGraph()
    graph.add_node("environment")

    apply_gdelt_threat_to_graph(graph, "environment", threat)

    assert requested_text_urls == ["http://data.gdeltproject.org/gdeltv2/lastupdate.txt"]
    assert requested_binary_urls == ["http://data.gdeltproject.org/gdeltv2/20260517120000.export.CSV.zip"]
    assert threat == {
        "event_count": 2,
        "goldstein_salience": 12.0,
        "environmental_threat_lambda": 0.14,
    }
    assert graph.node_properties("environment")["environmental_threat_lambda"] == 0.14


def test_gdelt_client_accepts_plain_csv_exports_for_easy_fixture_and_exporter_testing():
    client = GdeltClient(
        fetch_text=lambda url: "unused",
        fetch_bytes=lambda url: b"",
        threat_normalization=10.0,
    )

    events = client.parse_events_csv(
        gdelt_row(sql_date="20260517", root_code="20", goldstein="-4.5", country_code="US"),
        country_code="US",
    )
    threat = client.calculate_threat_index(events)

    assert len(events) == 1
    assert threat["environmental_threat_lambda"] == 0.55


def zipped_csv(csv_text: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("20260517120000.export.CSV", csv_text)
    return buffer.getvalue()


def gdelt_row(*, sql_date: str, root_code: str, goldstein: str, country_code: str) -> str:
    columns = [""] * 61
    columns[0] = "100"
    columns[1] = sql_date
    columns[26] = f"{root_code}1"
    columns[27] = f"{root_code}0"
    columns[28] = root_code
    columns[30] = goldstein
    columns[53] = country_code
    return "\t".join(columns)
