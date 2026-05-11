from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ClaimType = Literal[
    "reported_fact",
    "actor_stated_rationale",
    "contested_interpretation",
    "market_expectation",
    "model_inference",
]

Confidence = Literal["high", "medium", "low"]
ClaimClusterStatus = Literal["accepted", "disputed", "superseded", "unresolved"]


class SourceDocument(BaseModel):
    id: str
    source_type: Literal["wikipedia", "wikipedia_reference", "gdelt", "polymarket", "fred", "statement_archive", "fixture"]
    title: str
    url: str | None = None
    published_at: str | None = None
    retrieved_at: str
    revision_id: str | None = None
    section_title: str | None = None
    excerpt: str


class Entity(BaseModel):
    id: str
    canonical_name: str
    entity_type: Literal["person", "organization", "place", "state", "market", "concept"]
    wikidata_qid: str | None = None
    wikipedia_page_id: str | None = None
    description: str
    confidence: Confidence


class EntityMention(BaseModel):
    raw_text: str
    normalized_text: str
    entity_id: str | None = None
    status: Literal["resolved", "ambiguous", "unresolved"]
    resolver_method: str
    confidence: Confidence


class AtomicClaimRecord(BaseModel):
    id: str
    subject: str
    predicate: str
    object: str
    occurred_at: str
    quote: str
    source_ids: list[str]
    canonical_entity_ids: list[str] = Field(default_factory=list)
    claim_type: ClaimType = "reported_fact"


class ClaimClusterRecord(BaseModel):
    id: str
    claim_ids: list[str]
    status: ClaimClusterStatus
    summary: str
    canonical_entity_ids: list[str]


class ClaimContradictionRecord(BaseModel):
    id: str
    source_claim_id: str
    target_claim_id: str
    relationship: Literal["entails", "contradicts", "partially_overlaps", "reversal", "unrelated"]
    confidence: Confidence
    rationale: str


class TimelineEvent(BaseModel):
    id: str
    occurred_at: str
    title: str
    summary: str
    category: Literal[
        "background",
        "prelude",
        "statement",
        "strike",
        "diplomacy",
        "market",
        "impact",
        "current_state",
    ]
    source_ids: list[str]
    claim_cluster_ids: list[str] = Field(default_factory=list)
    confidence: Confidence
    claim_type: ClaimType


class GraphNode(BaseModel):
    id: str
    label: str
    node_type: Literal[
        "structural_driver",
        "strategic_driver",
        "proximate_trigger",
        "actor_rationale",
        "contested_interpretation",
        "opening_event",
        "impact",
        "current_state",
        "market_reaction",
        "supernode",
    ]
    summary: str
    source_ids: list[str]
    claim_cluster_ids: list[str] = Field(default_factory=list)
    confidence: Confidence
    claim_type: ClaimType
    source_count: int = 0


class GraphEdge(BaseModel):
    id: str
    source_node_id: str
    target_node_id: str
    relation: Literal[
        "enables",
        "pressures",
        "justifies",
        "triggers",
        "escalates",
        "constrains",
        "contradicts",
        "disrupts",
        "correlates_with",
    ]
    summary: str
    source_ids: list[str]
    claim_cluster_ids: list[str] = Field(default_factory=list)
    confidence: Confidence
    claim_type: ClaimType


class GraphView(BaseModel):
    view: Literal["spine", "neighborhood", "timeline", "contradictions", "full"]
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class MarketSeriesPoint(BaseModel):
    series: Literal["Brent", "WTI", "S&P 500"]
    date: str
    value: float
    source: Literal["FRED", "fixture"]


class TensionSeriesPoint(BaseModel):
    date: str
    value: float
    source: Literal["rule_based"] = "rule_based"
    source_ids: list[str] = Field(default_factory=list)
    summary: str


class PredictionMarketPricePoint(BaseModel):
    market_id: str
    question: str
    token_id: str
    outcome: str
    date: str
    probability: float
    status: Literal["active", "closed", "resolved"]
    source: Literal["Polymarket"] = "Polymarket"
    market_start: str | None = None
    market_end: str | None = None
    url: str | None = None


class MarketMarker(BaseModel):
    id: str
    occurred_at: str
    marker_type: Literal["statement", "strike", "market_move", "polymarket", "diplomacy"]
    title: str
    summary: str
    source_ids: list[str]
    related_node_ids: list[str] = Field(default_factory=list)


class SourceHealth(BaseModel):
    configured: bool
    available: bool
    note: str


class SourceStatus(BaseModel):
    wikipedia: SourceHealth
    gdelt: SourceHealth
    polymarket: SourceHealth
    fred: SourceHealth
    openai: SourceHealth
    postgres: SourceHealth
    qdrant: SourceHealth


class ExtractionStatus(BaseModel):
    method: str
    note: str
    source_scope: list[str]
    extracted_claim_clusters: int


class IranWarCase(BaseModel):
    title: str
    evidence_window_start: str
    evidence_window_end: str
    summary: str
    timeline_events: list[TimelineEvent]
    graph_view: GraphView
    source_documents: list[SourceDocument]
    atomic_claims: list[AtomicClaimRecord]
    claim_clusters: list[ClaimClusterRecord]
    claim_contradictions: list[ClaimContradictionRecord]
    market_series: list[MarketSeriesPoint]
    tension_series: list[TensionSeriesPoint] = Field(default_factory=list)
    prediction_market_series: list[PredictionMarketPricePoint] = Field(default_factory=list)
    market_markers: list[MarketMarker]
    source_status: SourceStatus
    extraction_status: ExtractionStatus
