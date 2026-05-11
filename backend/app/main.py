from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.app.iran_war.case_builder import build_case, rebuild_case
from backend.app.iran_war.source_status import build_source_status
from backend.app.models import (
    ClaimClusterRecord,
    ClaimContradictionRecord,
    GraphView,
    IranWarCase,
    MarketMarker,
    MarketSeriesPoint,
    PredictionMarketPricePoint,
    SourceDocument,
    SourceStatus,
    TensionSeriesPoint,
)


app = FastAPI(title="2026 Iran War Causal Timeline Graph")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/iran-war", response_model=IranWarCase)
def get_iran_war_case() -> IranWarCase:
    return build_case()


@app.post("/api/iran-war/rebuild", response_model=IranWarCase)
def rebuild_iran_war_case() -> IranWarCase:
    return rebuild_case()


@app.get("/api/iran-war/graph", response_model=GraphView)
def get_graph_view(
    view: str = Query(default="spine"),
    focus_node_id: str | None = Query(default=None),
) -> GraphView:
    return _select_graph_view(build_case().graph_view, view=view, focus_node_id=focus_node_id)


@app.get("/api/iran-war/claims", response_model=dict[str, list[ClaimClusterRecord] | list[ClaimContradictionRecord]])
def get_claims() -> dict[str, list[ClaimClusterRecord] | list[ClaimContradictionRecord]]:
    case = build_case()
    return {"clusters": case.claim_clusters, "contradictions": case.claim_contradictions}


@app.get("/api/iran-war/sources", response_model=list[SourceDocument])
def get_sources() -> list[SourceDocument]:
    return build_case().source_documents


@app.get("/api/iran-war/market-series", response_model=dict[str, list[MarketSeriesPoint] | list[MarketMarker] | list[TensionSeriesPoint]])
def get_market_series() -> dict[str, list[MarketSeriesPoint] | list[MarketMarker] | list[TensionSeriesPoint]]:
    case = build_case()
    return {"series": case.market_series, "markers": case.market_markers, "tension_series": case.tension_series}


@app.get("/api/iran-war/prediction-market-series", response_model=list[PredictionMarketPricePoint])
def get_prediction_market_series() -> list[PredictionMarketPricePoint]:
    return build_case().prediction_market_series


@app.get("/api/iran-war/source-status", response_model=SourceStatus)
def get_source_status() -> SourceStatus:
    return build_source_status()


def _select_graph_view(graph_view: GraphView, view: str, focus_node_id: str | None = None) -> GraphView:
    if view == "neighborhood" and focus_node_id:
        edges = [edge for edge in graph_view.edges if focus_node_id in {edge.source_node_id, edge.target_node_id}]
        node_ids = {focus_node_id} | {edge.source_node_id for edge in edges} | {edge.target_node_id for edge in edges}
        nodes = [node for node in graph_view.nodes if node.id in node_ids]
        return GraphView(view="neighborhood", nodes=nodes, edges=edges)

    if view == "timeline":
        return GraphView(view="timeline", nodes=graph_view.nodes, edges=graph_view.edges)

    if view == "contradictions":
        edges = [edge for edge in graph_view.edges if edge.relation == "contradicts"]
        node_ids = {edge.source_node_id for edge in edges} | {edge.target_node_id for edge in edges}
        nodes = [node for node in graph_view.nodes if node.id in node_ids]
        return GraphView(view="contradictions", nodes=nodes, edges=edges)

    if view == "full":
        return GraphView(view="full", nodes=graph_view.nodes, edges=graph_view.edges)

    return GraphView(view="spine", nodes=graph_view.nodes, edges=graph_view.edges)
