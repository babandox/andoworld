from fastapi.testclient import TestClient

from backend.app import main as main_module
from backend.app.iran_war.case_builder import build_case_from_ingestion
from backend.app.iran_war.ingestion import IngestedSourceBundle
from backend.app.models import PredictionMarketPricePoint, SourceDocument, SourceHealth, SourceStatus


app = main_module.app


def test_iran_war_api_returns_case_spine_and_sources():
    client = TestClient(app)

    response = client.get("/api/iran-war")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "2026 Iran War"
    assert body["graph_view"]["view"] == "spine"
    assert body["timeline_events"]
    assert body["source_documents"]


def test_graph_claims_market_and_source_status_endpoints():
    client = TestClient(app)

    graph = client.get("/api/iran-war/graph?view=spine")
    claims = client.get("/api/iran-war/claims")
    market = client.get("/api/iran-war/market-series")
    prediction_markets = client.get("/api/iran-war/prediction-market-series")
    status = client.get("/api/iran-war/source-status")

    assert graph.status_code == 200
    assert claims.status_code == 200
    assert market.status_code == 200
    assert "tension_series" in market.json()
    assert prediction_markets.status_code == 200
    assert status.status_code == 200
    assert "OPENAI_API_KEY" not in status.text
    assert "FRED_API_KEY" not in status.text
    assert status.json()["openai"]["configured"] is True


def test_graph_endpoint_returns_the_current_case_graph(monkeypatch):
    source = SourceDocument(
        id="wiki:live-test:background",
        source_type="wikipedia",
        title="Live test background",
        url="https://example.test/wiki",
        published_at=None,
        retrieved_at="2026-05-09",
        revision_id="rev-live",
        section_title="Background",
        excerpt="Live-only background evidence.",
    )
    case = build_case_from_ingestion(IngestedSourceBundle(source_documents=[source]))
    monkeypatch.setattr(main_module, "build_case", lambda: case)
    client = TestClient(app)

    response = client.get("/api/iran-war/graph?view=spine")

    assert response.status_code == 200
    labels = {node["label"] for node in response.json()["nodes"]}
    assert "Iran nuclear issue and JCPOA collapse" in labels
    assert "Opening strikes" not in labels


def test_prediction_market_series_endpoint_returns_current_case_points(monkeypatch):
    source = SourceDocument(
        id="wiki:live-test:background",
        source_type="wikipedia",
        title="Live test background",
        retrieved_at="2026-05-09",
        section_title="Background",
        excerpt="Live-only background evidence.",
    )
    point = PredictionMarketPricePoint(
        market_id="m1",
        question="Will Iran close the Strait of Hormuz in May?",
        token_id="yes-token",
        outcome="Yes",
        date="2026-04-08",
        probability=0.18,
        status="resolved",
        source="Polymarket",
        market_start="2026-04-08",
        market_end="2026-04-10",
        url="https://polymarket.com/event/iran-close-hormuz-may",
    )
    case = build_case_from_ingestion(IngestedSourceBundle(source_documents=[source], prediction_market_series=[point]))
    monkeypatch.setattr(main_module, "build_case", lambda: case)
    client = TestClient(app)

    response = client.get("/api/iran-war/prediction-market-series")

    assert response.status_code == 200
    assert response.json()[0]["market_id"] == "m1"
    assert response.json()[0]["probability"] == 0.18


def test_source_status_endpoint_does_not_build_the_full_case(monkeypatch):
    def fail_if_called():
        raise AssertionError("source-status should not trigger build_case")

    status = SourceStatus(
        wikipedia=SourceHealth(configured=True, available=True, note="Wikipedia available."),
        gdelt=SourceHealth(configured=True, available=True, note="GDELT available."),
        polymarket=SourceHealth(configured=True, available=True, note="Polymarket available."),
        fred=SourceHealth(configured=True, available=True, note="FRED configured."),
        openai=SourceHealth(configured=True, available=True, note="OpenAI configured."),
        postgres=SourceHealth(configured=False, available=True, note="Local Postgres reachable."),
        qdrant=SourceHealth(configured=False, available=True, note="Local Qdrant reachable."),
    )
    monkeypatch.setattr(main_module, "build_case", fail_if_called)
    monkeypatch.setattr(main_module, "build_source_status", lambda: status, raising=False)
    client = TestClient(app)

    response = client.get("/api/iran-war/source-status")

    assert response.status_code == 200
    assert response.json()["postgres"]["available"] is True
