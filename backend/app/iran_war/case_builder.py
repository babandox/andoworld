from __future__ import annotations

from datetime import datetime, timezone
import os
import re

from backend.app.iran_war.fixtures import (
    ATOMIC_CLAIMS,
    CLAIM_CLUSTERS,
    CLAIM_CONTRADICTIONS,
    MARKET_MARKERS,
    MARKET_SERIES,
    SOURCE_DOCUMENTS,
    TIMELINE_EVENTS,
)
from backend.app.iran_war.causal_extraction import extract_causal_structure
from backend.app.iran_war.graph import build_graph_view
from backend.app.iran_war.ingestion import IngestedSourceBundle, ingest_live_sources
from backend.app.iran_war.persistence import load_cached_source_documents, persist_case_artifacts
from backend.app.iran_war.source_status import build_source_status
from backend.app.iran_war.tension import build_tension_series
from backend.app.models import (
    ExtractionStatus,
    GraphEdge,
    GraphNode,
    GraphView,
    IranWarCase,
    MarketMarker,
    MarketSeriesPoint,
    SourceDocument,
    SourceHealth,
    SourceStatus,
    TimelineEvent,
)


_CASE_CACHE: IranWarCase | None = None
TIMELINE_EVENT_LIMIT = 2000


def build_case(force_refresh: bool = False) -> IranWarCase:
    global _CASE_CACHE
    if _CASE_CACHE is not None and not force_refresh:
        return _CASE_CACHE

    if os.getenv("IRAN_WAR_DISABLE_LIVE", "").lower() in {"1", "true", "yes"}:
        _CASE_CACHE = build_fixture_case()
        return _CASE_CACHE

    bundle = ingest_live_sources()
    _CASE_CACHE = build_case_from_ingestion(bundle) if bundle.has_live_data else build_fixture_case()
    return _CASE_CACHE


def rebuild_case() -> IranWarCase:
    return build_case(force_refresh=True)


def build_fixture_case() -> IranWarCase:
    return IranWarCase(
        title="2026 Iran War",
        evidence_window_start="2025-12-01",
        evidence_window_end="2026-05-09",
        summary=(
            "A source-backed causal timeline for the 2026 Iran war, focused on background drivers, "
            "prelude events, opening strikes, public-statement reversals, Hormuz risk, and market reaction."
        ),
        timeline_events=TIMELINE_EVENTS,
        graph_view=build_graph_view("spine"),
        source_documents=SOURCE_DOCUMENTS,
        atomic_claims=ATOMIC_CLAIMS,
        claim_clusters=CLAIM_CLUSTERS,
        claim_contradictions=CLAIM_CONTRADICTIONS,
        market_series=MARKET_SERIES,
        tension_series=build_tension_series(TIMELINE_EVENTS, start="2025-12-01", end="2026-05-09"),
        prediction_market_series=[],
        market_markers=MARKET_MARKERS,
        source_status=build_source_status(),
        extraction_status=ExtractionStatus(
            method="fixture",
            note="Fixture claim clusters are loaded because live ingestion is disabled or unavailable.",
            source_scope=["fixture"],
            extracted_claim_clusters=len(CLAIM_CLUSTERS),
        ),
    )


def build_case_from_ingestion(bundle: IngestedSourceBundle) -> IranWarCase:
    bundle = _apply_cached_source_fallbacks(bundle)
    source_documents = bundle.source_documents or SOURCE_DOCUMENTS
    market_series = bundle.market_series if bundle.has_live_data else MARKET_SERIES
    prediction_market_series = bundle.prediction_market_series if bundle.has_live_data else []
    market_markers = _live_market_markers(bundle, source_documents)
    if not bundle.has_live_data:
        market_markers = MARKET_MARKERS
    timeline_events = _timeline_from_sources(source_documents) or TIMELINE_EVENTS
    evidence_end = datetime.now(timezone.utc).date().isoformat()
    summary_mode = "live source ingestion" if bundle.has_live_data else "fixture fallback"
    causal_extraction = extract_causal_structure(source_documents) if bundle.has_live_data else None
    graph_view = causal_extraction.graph_view if causal_extraction else build_graph_view("spine")
    atomic_claims = causal_extraction.atomic_claims if causal_extraction else ([] if bundle.has_live_data else ATOMIC_CLAIMS)
    claim_clusters = causal_extraction.claim_clusters if causal_extraction else ([] if bundle.has_live_data else CLAIM_CLUSTERS)
    claim_contradictions = [] if bundle.has_live_data else CLAIM_CONTRADICTIONS
    case = IranWarCase(
        title="2026 Iran War",
        evidence_window_start="2025-12-01",
        evidence_window_end=evidence_end,
        summary=(
            f"A source-backed causal graph for the 2026 Iran war using {summary_mode}"
            f"{f' and {causal_extraction.method}' if causal_extraction else ''}. "
            "Wikipedia provides the causal backbone; GDELT, Polymarket, and FRED are supporting evidence layers."
        ),
        timeline_events=timeline_events,
        graph_view=graph_view,
        source_documents=source_documents,
        atomic_claims=atomic_claims,
        claim_clusters=claim_clusters,
        claim_contradictions=claim_contradictions,
        market_series=market_series,
        tension_series=build_tension_series(timeline_events, start="2025-12-01", end=evidence_end),
        prediction_market_series=prediction_market_series,
        market_markers=market_markers,
        source_status=_status_from_bundle(bundle),
        extraction_status=_extraction_status(causal_extraction, source_documents),
    )
    return _apply_persistence_status(case) if bundle.has_live_data else case


def _timeline_from_sources(source_documents: list[SourceDocument]) -> list[TimelineEvent]:
    events: list[TimelineEvent] = []
    for source in source_documents:
        if source.source_type == "wikipedia":
            occurred_at = _wikipedia_event_date(source) or "2025-12-01"
            category = "background"
        elif source.source_type in {"gdelt", "wikipedia_reference", "statement_archive"} and source.published_at:
            occurred_at = _source_date(source.published_at)
            category = "statement" if "trump" in source.title.casefold() else "prelude"
        else:
            continue

        events.append(
            TimelineEvent(
                id=f"event:{source.id}",
                occurred_at=occurred_at,
                title=source.title,
                summary=source.excerpt,
                category=category,  # type: ignore[arg-type]
                source_ids=[source.id],
                claim_cluster_ids=[],
                confidence="medium",
                claim_type="reported_fact" if source.source_type != "wikipedia" else "actor_stated_rationale",
            )
        )
    events.sort(key=lambda event: event.occurred_at)
    return events[:TIMELINE_EVENT_LIMIT]


def _apply_cached_source_fallbacks(bundle: IngestedSourceBundle) -> IngestedSourceBundle:
    source_types = {source.source_type for source in bundle.source_documents}
    if "gdelt" in source_types:
        return bundle
    if not _source_errors(bundle, "GDELT"):
        return bundle
    cached = load_cached_source_documents("gdelt", limit=100)
    if not cached:
        return bundle
    return IngestedSourceBundle(
        source_documents=[*bundle.source_documents, *cached],
        market_series=bundle.market_series,
        prediction_market_series=bundle.prediction_market_series,
        market_markers=bundle.market_markers,
        errors=[*bundle.errors, f"GDELT cache fallback used {len(cached)} cached Postgres records."],
    )


def _wikipedia_event_date(source: SourceDocument) -> str | None:
    text = f"{source.section_title or ''} {source.excerpt}"
    if match := re.search(r"\b(\d{1,2})\s+([A-Z][a-z]+)\s+((?:19|20)\d{2})\b", text):
        day, month, year = match.groups()
        month_number = _month_number(month)
        if month_number:
            return f"{year}-{month_number}-{int(day):02d}"
    if match := re.search(r"\b([A-Z][a-z]+)\s+(\d{1,2}),\s*((?:19|20)\d{2})\b", text):
        month, day, year = match.groups()
        month_number = _month_number(month)
        if month_number:
            return f"{year}-{month_number}-{int(day):02d}"
    if match := re.search(r"\b([A-Z][a-z]+)\s+((?:19|20)\d{2})\b", text):
        month, year = match.groups()
        month_number = _month_number(month)
        if month_number:
            return f"{year}-{month_number}-01"
    if match := re.search(r"\b((?:19|20)\d{2})\b", text):
        return f"{match.group(1)}-01-01"
    return None


def _month_number(month: str) -> str | None:
    months = {
        "january": "01",
        "february": "02",
        "march": "03",
        "april": "04",
        "may": "05",
        "june": "06",
        "july": "07",
        "august": "08",
        "september": "09",
        "october": "10",
        "november": "11",
        "december": "12",
    }
    return months.get(month.casefold())


def _source_date(value: str) -> str:
    if len(value) >= 8 and value[:8].isdigit():
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}"
    return value[:10]


def _live_market_markers(bundle: IngestedSourceBundle, source_documents: list[SourceDocument]) -> list[MarketMarker]:
    markers: list[MarketMarker] = []
    fred_sources = [source for source in source_documents if source.source_type == "fred"]
    if bundle.market_series:
        markers.append(
            MarketMarker(
                id="marker:fred-live-series",
                occurred_at=bundle.market_series[-1].date,
                marker_type="market_move",
                title="Latest FRED market data",
                summary="Live FRED daily market series ingested for Brent, WTI, and/or S&P 500.",
                source_ids=[source.id for source in fred_sources] or ["fred:live"],
                related_node_ids=["node:market-reaction"],
            )
        )
    return markers


def _graph_from_sources(
    source_documents: list[SourceDocument],
    market_series: list[MarketSeriesPoint],
) -> GraphView | None:
    docs_by_type: dict[str, list[SourceDocument]] = {}
    for source in source_documents:
        docs_by_type.setdefault(source.source_type, []).append(source)

    nodes: list[GraphNode] = []
    if wikipedia_docs := docs_by_type.get("wikipedia", []):
        nodes.append(
            _source_node(
                id="node:live-wikipedia-background",
                label="Wikipedia background",
                node_type="structural_driver",
                claim_type="actor_stated_rationale",
                sources=wikipedia_docs,
            )
        )
    if gdelt_docs := docs_by_type.get("gdelt", []):
        nodes.append(
            _source_node(
                id="node:live-gdelt-reporting",
                label="GDELT reporting stream",
                node_type="proximate_trigger",
                claim_type="reported_fact",
                sources=gdelt_docs,
            )
        )
    if polymarket_docs := docs_by_type.get("polymarket", []):
        nodes.append(
            _source_node(
                id="node:live-polymarket-expectations",
                label="Polymarket Iran markets",
                node_type="current_state",
                claim_type="market_expectation",
                sources=polymarket_docs,
            )
        )
    if market_series:
        series_names = sorted({point.series for point in market_series})
        latest_date = max(point.date for point in market_series)
        fred_source_ids = [source.id for source in docs_by_type.get("fred", [])] or ["fred:live"]
        nodes.append(
            GraphNode(
                id="node:live-fred-market-data",
                label="FRED market series",
                node_type="market_reaction",
                summary=f"FRED returned {', '.join(series_names)} observations through {latest_date}.",
                source_ids=fred_source_ids,
                claim_cluster_ids=[],
                confidence="medium",
                claim_type="reported_fact",
                source_count=len(market_series),
            )
        )

    if not nodes:
        return None

    node_ids = {node.id for node in nodes}
    edges: list[GraphEdge] = []
    if {"node:live-wikipedia-background", "node:live-gdelt-reporting"}.issubset(node_ids):
        edges.append(
            _source_edge(
                id="edge:live-wiki-gdelt",
                source_node_id="node:live-wikipedia-background",
                target_node_id="node:live-gdelt-reporting",
                relation="justifies",
                summary="Wikipedia background sections provide the structured historical context for the current reporting stream.",
                source_ids=_node_source_ids(nodes, "node:live-wikipedia-background"),
                claim_type="actor_stated_rationale",
            )
        )
    if {"node:live-gdelt-reporting", "node:live-polymarket-expectations"}.issubset(node_ids):
        edges.append(
            _source_edge(
                id="edge:live-gdelt-polymarket",
                source_node_id="node:live-gdelt-reporting",
                target_node_id="node:live-polymarket-expectations",
                relation="correlates_with",
                summary="News-flow records and prediction-market records are shown together as contemporaneous evidence, not as settled causation.",
                source_ids=_node_source_ids(nodes, "node:live-polymarket-expectations"),
                claim_type="market_expectation",
            )
        )
    if {"node:live-gdelt-reporting", "node:live-fred-market-data"}.issubset(node_ids):
        edges.append(
            _source_edge(
                id="edge:live-gdelt-fred",
                source_node_id="node:live-gdelt-reporting",
                target_node_id="node:live-fred-market-data",
                relation="disrupts",
                summary="Iran-war reporting is overlaid with FRED market observations so oil and equity reactions can be inspected against dated events.",
                source_ids=_node_source_ids(nodes, "node:live-fred-market-data"),
                claim_type="reported_fact",
            )
        )

    return GraphView(view="spine", nodes=nodes[:60], edges=edges)


def _source_node(
    id: str,
    label: str,
    node_type: str,
    claim_type: str,
    sources: list[SourceDocument],
) -> GraphNode:
    source_ids = [source.id for source in sources[:12]]
    return GraphNode(
        id=id,
        label=label,
        node_type=node_type,  # type: ignore[arg-type]
        summary=_source_group_summary(sources),
        source_ids=source_ids,
        claim_cluster_ids=[],
        confidence="medium",
        claim_type=claim_type,  # type: ignore[arg-type]
        source_count=len(sources),
    )


def _source_edge(
    id: str,
    source_node_id: str,
    target_node_id: str,
    relation: str,
    summary: str,
    source_ids: list[str],
    claim_type: str,
) -> GraphEdge:
    return GraphEdge(
        id=id,
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        relation=relation,  # type: ignore[arg-type]
        summary=summary,
        source_ids=source_ids,
        claim_cluster_ids=[],
        confidence="medium",
        claim_type=claim_type,  # type: ignore[arg-type]
    )


def _source_group_summary(sources: list[SourceDocument]) -> str:
    first = sources[0]
    return f"{first.title}: {first.excerpt}"


def _node_source_ids(nodes: list[GraphNode], node_id: str) -> list[str]:
    for node in nodes:
        if node.id == node_id:
            return node.source_ids
    return []


def _status_from_bundle(bundle: IngestedSourceBundle) -> SourceStatus:
    base = build_source_status()
    source_types = {source.source_type for source in bundle.source_documents}
    series_available = bool(bundle.market_series)
    prediction_series_available = bool(bundle.prediction_market_series)
    return SourceStatus(
        wikipedia=_availability(base.wikipedia, "wikipedia" in source_types, "Wikipedia returned source sections.", _source_errors(bundle, "Wikipedia")),
        gdelt=_availability(
            base.gdelt,
            "gdelt" in source_types,
            "GDELT returned article records from windowed public DOC queries. Public DOC search covers the rolling recent horizon; older December/January reporting needs GDELT Cloud or BigQuery.",
            _source_errors(bundle, "GDELT"),
        ),
        polymarket=_availability(
            base.polymarket,
            "polymarket" in source_types or prediction_series_available,
            "Polymarket returned market records and daily probability history.",
            _source_errors(bundle, "Polymarket"),
        ),
        fred=_availability(base.fred, series_available, "FRED returned daily market observations.", _source_errors(bundle, "FRED")),
        openai=base.openai,
        postgres=base.postgres,
        qdrant=base.qdrant,
    )


def _apply_persistence_status(case: IranWarCase) -> IranWarCase:
    result = persist_case_artifacts(case)
    return case.model_copy(
        update={
            "source_status": case.source_status.model_copy(
                update={
                    "postgres": SourceHealth(
                        configured=case.source_status.postgres.configured,
                        available=result.postgres_available,
                        note=result.postgres_note,
                    ),
                    "qdrant": SourceHealth(
                        configured=case.source_status.qdrant.configured,
                        available=result.qdrant_available,
                        note=result.qdrant_note,
                    ),
                }
            )
        }
    )


def _extraction_status(causal_extraction: object | None, source_documents: list[SourceDocument]) -> ExtractionStatus:
    source_types = sorted({source.source_type for source in source_documents})
    if causal_extraction is None:
        return ExtractionStatus(
            method="none",
            note="No source-backed causal extraction ran because no Wikipedia background corpus was available.",
            source_scope=source_types,
            extracted_claim_clusters=0,
        )

    method = getattr(causal_extraction, "method", "unknown")
    model = getattr(causal_extraction, "model", None)
    clusters = getattr(causal_extraction, "claim_clusters", [])
    if method == "openai":
        model_note = f" using {model}" if model else ""
        note = f"OpenAI{model_note} structured causal drivers and edges from Wikipedia excerpts; records without valid source IDs were rejected."
    elif method == "deterministic-wikipedia-fallback":
        note = "Wikipedia source sections were matched to the planned driver taxonomy because OpenAI extraction was disabled, unavailable, or did not return a valid cited graph."
    else:
        note = "Causal drivers were extracted from the configured source corpus."
    return ExtractionStatus(
        method=method,
        note=note,
        source_scope=source_types,
        extracted_claim_clusters=len(clusters),
    )


def _availability(base: SourceHealth, available: bool, success_note: str, errors: list[str] | None = None) -> SourceHealth:
    if available:
        cached = next((error for error in errors or [] if "cache fallback" in error.casefold()), None)
        if cached:
            live_error = next((error for error in errors or [] if error != cached), None)
            warning = f"{cached}" + (f" Live query status: {live_error}." if live_error else "")
            return SourceHealth(configured=base.configured, available=True, note=warning)
        else:
            warning = f" Some query windows reported: {errors[0]}." if errors else ""
        return SourceHealth(configured=base.configured, available=True, note=f"{success_note}{warning}")
    if errors:
        return SourceHealth(
            configured=base.configured,
            available=False,
            note=f"{base.note} Last ingestion error: {errors[0]}",
        )
    return SourceHealth(
        configured=base.configured,
        available=False,
        note=f"{base.note} No live records were returned in the last ingestion attempt.",
    )


def _source_errors(bundle: IngestedSourceBundle, label: str) -> list[str]:
    prefix = label.casefold()
    return [error for error in bundle.errors if error.casefold().startswith(prefix)]
