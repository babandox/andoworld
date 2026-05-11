from __future__ import annotations

from backend.app.models import (
    AtomicClaimRecord,
    ClaimClusterRecord,
    ClaimContradictionRecord,
    Entity,
    GraphEdge,
    GraphNode,
    MarketMarker,
    MarketSeriesPoint,
    SourceDocument,
    TimelineEvent,
)


RETRIEVED_AT = "2026-05-09"


SOURCE_DOCUMENTS = [
    SourceDocument(
        id="wiki:2026-iran-war:background",
        source_type="wikipedia",
        title="2026 Iran war - Background",
        url="https://en.wikipedia.org/wiki/2026_Iran_war",
        published_at=None,
        retrieved_at=RETRIEVED_AT,
        revision_id="fixture-revision-1",
        section_title="Background",
        excerpt="Background material links the war to the Iran nuclear issue, sanctions, regional rivalry, and the Strait of Hormuz.",
    ),
    SourceDocument(
        id="wiki:rationale:iran-nuclear-issue",
        source_type="wikipedia",
        title="Rationale for the 2026 Iran war - Iran nuclear issue",
        url="https://en.wikipedia.org/wiki/Rationale_for_the_2026_Iran_war",
        published_at=None,
        retrieved_at=RETRIEVED_AT,
        revision_id="fixture-revision-2",
        section_title="Iran nuclear issue",
        excerpt="Rationale sections describe nuclear, missile, regional-proxy, and regime-change interpretations.",
    ),
    SourceDocument(
        id="gdelt:2025-12-protests",
        source_type="gdelt",
        title="December protests and sanctions pressure intensify",
        url="https://example.test/gdelt/iran-december-protests",
        published_at="2025-12-18T12:00:00Z",
        retrieved_at=RETRIEVED_AT,
        excerpt="News coverage connects protests, sanctions pressure, and worsening nuclear negotiations.",
    ),
    SourceDocument(
        id="gdelt:2026-02-opening-strikes",
        source_type="gdelt",
        title="Opening strikes begin the 2026 Iran war",
        url="https://example.test/gdelt/opening-strikes",
        published_at="2026-02-28T04:30:00Z",
        retrieved_at=RETRIEVED_AT,
        excerpt="Timestamped reports describe opening strikes and immediate escalation fears.",
    ),
    SourceDocument(
        id="statement:trump-2026-03-03",
        source_type="statement_archive",
        title="Trump statement supports ceasefire",
        url="https://trump-archive.com/archive",
        published_at="2026-03-03T10:00:00Z",
        retrieved_at=RETRIEVED_AT,
        excerpt="Trump signaled support for a ceasefire while warning Iran against closing Hormuz.",
    ),
    SourceDocument(
        id="statement:trump-2026-03-04",
        source_type="statement_archive",
        title="Trump statement reverses ceasefire tone",
        url="https://trump-archive.com/archive",
        published_at="2026-03-04T09:00:00Z",
        retrieved_at=RETRIEVED_AT,
        excerpt="Trump threatened renewed strikes if Iran resumed attacks, reversing the prior de-escalatory tone.",
    ),
    SourceDocument(
        id="fred:brent-sp500",
        source_type="fred",
        title="FRED Brent and S&P 500 daily series",
        url="https://fred.stlouisfed.org/",
        published_at=None,
        retrieved_at=RETRIEVED_AT,
        excerpt="Daily market data used to show oil and equity reaction windows.",
    ),
    SourceDocument(
        id="polymarket:iran-hormuz",
        source_type="polymarket",
        title="Iran/Hormuz prediction market expectation signal",
        url="https://polymarket.com/",
        published_at="2026-03-01T00:00:00Z",
        retrieved_at=RETRIEVED_AT,
        excerpt="Market expectations around Hormuz disruption and war escalation.",
    ),
]


ENTITIES = [
    Entity(id="entity:irgc", canonical_name="Islamic Revolutionary Guard Corps", entity_type="organization", wikidata_qid="Q207983", description="Iranian military-political organization.", confidence="high"),
    Entity(id="entity:trump", canonical_name="Donald Trump", entity_type="person", wikidata_qid="Q22686", description="US president and source of market-relevant public statements.", confidence="high"),
    Entity(id="entity:hormuz", canonical_name="Strait of Hormuz", entity_type="place", wikidata_qid="Q204457", description="Strategic maritime chokepoint for oil and LNG flows.", confidence="high"),
    Entity(id="entity:sp500", canonical_name="S&P 500", entity_type="market", description="US equity index used for market reaction charting.", confidence="high"),
]


ATOMIC_CLAIMS = [
    AtomicClaimRecord(id="claim:nuclear-pressure", subject="Iran nuclear issue", predicate="pressured", object="war rationale", occurred_at="2025-12-01", quote="The nuclear issue remained a central stated rationale.", source_ids=["wiki:rationale:iran-nuclear-issue"], canonical_entity_ids=["entity:iran"], claim_type="actor_stated_rationale"),
    AtomicClaimRecord(id="claim:protests-sanctions", subject="Sanctions and protests", predicate="pressured", object="Iranian decision space", occurred_at="2025-12-18", quote="Protests and sanctions pressure intensified in December.", source_ids=["gdelt:2025-12-protests"], canonical_entity_ids=["entity:iran"], claim_type="reported_fact"),
    AtomicClaimRecord(id="claim:opening-strikes", subject="Opening strikes", predicate="triggered", object="2026 Iran war", occurred_at="2026-02-28", quote="Opening strikes began the war.", source_ids=["gdelt:2026-02-opening-strikes"], canonical_entity_ids=["entity:iran", "entity:israel"], claim_type="reported_fact"),
    AtomicClaimRecord(id="claim:trump-supports-ceasefire", subject="Trump", predicate="supported", object="ceasefire", occurred_at="2026-03-03", quote="Trump signaled support for a ceasefire.", source_ids=["statement:trump-2026-03-03"], canonical_entity_ids=["entity:trump"], claim_type="reported_fact"),
    AtomicClaimRecord(id="claim:trump-rejects-ceasefire", subject="Trump", predicate="rejected", object="ceasefire", occurred_at="2026-03-04", quote="Trump threatened renewed strikes if attacks resumed.", source_ids=["statement:trump-2026-03-04"], canonical_entity_ids=["entity:trump"], claim_type="reported_fact"),
]


CLAIM_CLUSTERS = [
    ClaimClusterRecord(id="cluster:background-drivers", claim_ids=["claim:nuclear-pressure", "claim:protests-sanctions"], status="accepted", summary="Background drivers combine nuclear, sanctions, protest, and regional pressure.", canonical_entity_ids=["entity:iran"]),
    ClaimClusterRecord(id="cluster:opening-event", claim_ids=["claim:opening-strikes"], status="accepted", summary="Opening strikes triggered the war phase.", canonical_entity_ids=["entity:iran", "entity:israel"]),
    ClaimClusterRecord(id="cluster:trump-reversal", claim_ids=["claim:trump-supports-ceasefire", "claim:trump-rejects-ceasefire"], status="superseded", summary="Trump statements moved from de-escalatory to renewed-threat posture across consecutive days.", canonical_entity_ids=["entity:trump"]),
]


CLAIM_CONTRADICTIONS = [
    ClaimContradictionRecord(id="contradiction:trump-ceasefire", source_claim_id="claim:trump-supports-ceasefire", target_claim_id="claim:trump-rejects-ceasefire", relationship="reversal", confidence="medium", rationale="Same actor and proposition, different dates, opposing posture."),
]


TIMELINE_EVENTS = [
    TimelineEvent(id="event:background", occurred_at="2025-12-01", title="Long-running nuclear and sanctions dispute frames the war rationale", summary="Wikipedia background sections connect the war to nuclear negotiations, sanctions, missile concerns, and regional rivalry.", category="background", source_ids=["wiki:2026-iran-war:background", "wiki:rationale:iran-nuclear-issue"], claim_cluster_ids=["cluster:background-drivers"], confidence="medium", claim_type="actor_stated_rationale"),
    TimelineEvent(id="event:december-pressure", occurred_at="2025-12-18", title="December protests and sanctions pressure intensify", summary="Timestamped news evidence places domestic and sanctions pressure in the prelude window.", category="prelude", source_ids=["gdelt:2025-12-protests"], claim_cluster_ids=["cluster:background-drivers"], confidence="medium", claim_type="reported_fact"),
    TimelineEvent(id="event:opening-strikes", occurred_at="2026-02-28", title="Opening strikes begin the war phase", summary="GDELT-backed reports anchor the transition from prelude to active war.", category="strike", source_ids=["gdelt:2026-02-opening-strikes"], claim_cluster_ids=["cluster:opening-event"], confidence="high", claim_type="reported_fact"),
    TimelineEvent(id="event:trump-ceasefire-tone", occurred_at="2026-03-03", title="Trump signals support for ceasefire", summary="A de-escalatory statement coincides with a pullback in oil risk premium in daily data.", category="statement", source_ids=["statement:trump-2026-03-03", "fred:brent-sp500"], claim_cluster_ids=["cluster:trump-reversal"], confidence="medium", claim_type="reported_fact"),
    TimelineEvent(id="event:trump-renewed-threat", occurred_at="2026-03-04", title="Trump reverses tone and threatens renewed strikes", summary="A renewed-threat statement is preserved as a reversal rather than collapsed into one Trump position.", category="statement", source_ids=["statement:trump-2026-03-04", "fred:brent-sp500"], claim_cluster_ids=["cluster:trump-reversal"], confidence="medium", claim_type="reported_fact"),
    TimelineEvent(id="event:hormuz-market", occurred_at="2026-03-05", title="Hormuz disruption risk dominates market reaction", summary="Oil and equity movements are shown as temporal association unless source attribution supports causation.", category="market", source_ids=["fred:brent-sp500", "polymarket:iran-hormuz"], claim_cluster_ids=[], confidence="medium", claim_type="market_expectation"),
]


GRAPH_NODES = [
    GraphNode(id="node:nuclear-issue", label="Iran nuclear issue", node_type="strategic_driver", summary="Nuclear negotiations and weapons-risk claims structure actor-stated rationales.", source_ids=["wiki:rationale:iran-nuclear-issue"], claim_cluster_ids=["cluster:background-drivers"], confidence="medium", claim_type="actor_stated_rationale", source_count=1),
    GraphNode(id="node:sanctions-pressure", label="Sanctions and protests", node_type="proximate_trigger", summary="December pressure narrows decision space and escalates uncertainty.", source_ids=["gdelt:2025-12-protests"], claim_cluster_ids=["cluster:background-drivers"], confidence="medium", claim_type="reported_fact", source_count=1),
    GraphNode(id="node:opening-strikes", label="Opening strikes", node_type="opening_event", summary="Opening strikes mark the active war phase.", source_ids=["gdelt:2026-02-opening-strikes"], claim_cluster_ids=["cluster:opening-event"], confidence="high", claim_type="reported_fact", source_count=1),
    GraphNode(id="node:trump-reversals", label="Trump statement reversals", node_type="supernode", summary="Contradictory public posture is shown as ordered reversal events.", source_ids=["statement:trump-2026-03-03", "statement:trump-2026-03-04"], claim_cluster_ids=["cluster:trump-reversal"], confidence="medium", claim_type="reported_fact", source_count=2),
    GraphNode(id="node:hormuz-risk", label="Hormuz energy risk", node_type="impact", summary="Risk to the Strait of Hormuz transmits the war into oil-market expectations.", source_ids=["wiki:2026-iran-war:background", "polymarket:iran-hormuz"], claim_cluster_ids=[], confidence="medium", claim_type="market_expectation", source_count=2),
    GraphNode(id="node:market-reaction", label="Oil and S&P reaction", node_type="market_reaction", summary="Daily Brent and S&P 500 series show market reaction windows with event markers.", source_ids=["fred:brent-sp500"], claim_cluster_ids=[], confidence="medium", claim_type="market_expectation", source_count=1),
]


GRAPH_EDGES = [
    GraphEdge(id="edge:nuclear-sanctions", source_node_id="node:nuclear-issue", target_node_id="node:sanctions-pressure", relation="justifies", summary="Nuclear claims and sanctions pressure shape the stated rationale and prelude.", source_ids=["wiki:rationale:iran-nuclear-issue", "gdelt:2025-12-protests"], claim_cluster_ids=["cluster:background-drivers"], confidence="medium", claim_type="actor_stated_rationale"),
    GraphEdge(id="edge:sanctions-strikes", source_node_id="node:sanctions-pressure", target_node_id="node:opening-strikes", relation="triggers", summary="Prelude pressure feeds into the opening war phase in the causal spine.", source_ids=["gdelt:2025-12-protests", "gdelt:2026-02-opening-strikes"], claim_cluster_ids=["cluster:background-drivers", "cluster:opening-event"], confidence="medium", claim_type="model_inference"),
    GraphEdge(id="edge:strikes-hormuz", source_node_id="node:opening-strikes", target_node_id="node:hormuz-risk", relation="escalates", summary="Opening strikes escalate perceived chokepoint risk.", source_ids=["gdelt:2026-02-opening-strikes", "polymarket:iran-hormuz"], claim_cluster_ids=["cluster:opening-event"], confidence="medium", claim_type="market_expectation"),
    GraphEdge(id="edge:hormuz-market", source_node_id="node:hormuz-risk", target_node_id="node:market-reaction", relation="disrupts", summary="Hormuz risk is the main energy-market transmission channel.", source_ids=["fred:brent-sp500", "polymarket:iran-hormuz"], claim_cluster_ids=[], confidence="medium", claim_type="market_expectation"),
]


MARKET_SERIES = [
    MarketSeriesPoint(series="Brent", date="2025-12-01", value=73.4, source="fixture"),
    MarketSeriesPoint(series="Brent", date="2026-02-28", value=91.8, source="fixture"),
    MarketSeriesPoint(series="Brent", date="2026-03-03", value=84.2, source="fixture"),
    MarketSeriesPoint(series="Brent", date="2026-03-04", value=93.1, source="fixture"),
    MarketSeriesPoint(series="S&P 500", date="2025-12-01", value=6210.0, source="fixture"),
    MarketSeriesPoint(series="S&P 500", date="2026-02-28", value=5920.0, source="fixture"),
    MarketSeriesPoint(series="S&P 500", date="2026-03-03", value=6088.0, source="fixture"),
    MarketSeriesPoint(series="S&P 500", date="2026-03-04", value=5876.0, source="fixture"),
]


MARKET_MARKERS = [
    MarketMarker(id="marker:opening-strikes", occurred_at="2026-02-28", marker_type="strike", title="Opening strikes", summary="War phase begins; oil risk premium rises in daily data.", source_ids=["gdelt:2026-02-opening-strikes", "fred:brent-sp500"], related_node_ids=["node:opening-strikes", "node:market-reaction"]),
    MarketMarker(id="marker:trump-ceasefire", occurred_at="2026-03-03", marker_type="statement", title="Trump ceasefire tone", summary="De-escalatory statement marker overlaid on market chart.", source_ids=["statement:trump-2026-03-03"], related_node_ids=["node:trump-reversals"]),
    MarketMarker(id="marker:oil-spike", occurred_at="2026-03-04", marker_type="market_move", title="Oil spike and equity pullback", summary="Daily Brent rises and S&P 500 falls after renewed-threat messaging; shown as temporal association.", source_ids=["statement:trump-2026-03-04", "fred:brent-sp500"], related_node_ids=["node:market-reaction"]),
]
