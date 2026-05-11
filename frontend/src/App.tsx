import cytoscape, { Core, ElementDefinition } from "cytoscape";
import {
  AlertTriangle,
  BookOpen,
  ExternalLink,
  GitBranch,
  LineChart,
  Loader2,
  Network,
  RefreshCw,
  ShieldAlert,
  Sparkles
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";

import { fetchGraphView, fetchIranWarCase } from "./api";
import { buildCaseBriefMetrics, buildCausalBackbone, buildExtractionSummary, buildTimelineLanes, hasExtractedCausalClaims } from "./caseView";
import { causalSpineElements, highlightedNeighborhood } from "./graphView";
import {
  buildEventRug,
  buildMarketEventOverlays,
  chartWindowForMode,
  filterTensionSeriesForWindow,
  groupSeries,
  indexSeriesToBaseline,
  percentMove,
  type ChartWindowMode,
  type EventRugItem,
  type IndexedMarketSeriesPoint,
  type MarketEventOverlay
} from "./market";
import {
  groupPredictionMarkets,
  latestProbability,
  marketDateRange,
  splitPredictionMarkets,
  sortPredictionMarkets,
  type PredictionMarketSeries
} from "./predictionMarkets";
import { useSelectionStore } from "./store";
import type {
  GraphView,
  GraphNode,
  IranWarCase,
  MarketMarker,
  MarketSeriesPoint,
  PredictionMarketPricePoint,
  SourceDocument,
  SourceHealth,
  TensionSeriesPoint,
  TimelineEvent
} from "./types";

function App() {
  const [data, setData] = useState<IranWarCase | null>(null);
  const [graph, setGraph] = useState<GraphView | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setIsLoading(true);
    setError(null);
    try {
      const caseData = await fetchIranWarCase();
      setData(caseData);
      setGraph(caseData.graph_view);
      useSelectionStore.getState().clearSelection();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to load Iran-war case");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (isLoading) {
    return (
      <main className="loading-screen">
        <Loader2 className="spin" aria-hidden="true" />
        <span>Loading case evidence</span>
      </main>
    );
  }

  if (error || !data || !graph) {
    return (
      <main className="loading-screen error">
        <AlertTriangle aria-hidden="true" />
        <span>{error ?? "No case data available"}</span>
        <button type="button" onClick={load}>
          Retry
        </button>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <TopBar data={data} onRefresh={load} />
      <CaseBrief data={data} />
      <section className="workspace">
        <CausalBackbonePanel data={data} graph={graph} />
        <section className="graph-panel">
          <GraphToolbar graph={graph} setGraph={setGraph} />
          <CausalGraph graph={graph} />
        </section>
        <EvidenceInspector data={data} graph={graph} />
      </section>
      <MarketReactionPanel points={data.market_series} markers={data.market_markers} events={data.timeline_events} tension={data.tension_series} />
      <PredictionMarketPanel points={data.prediction_market_series} />
    </main>
  );
}

function TopBar({ data, onRefresh }: { data: IranWarCase; onRefresh: () => void }) {
  return (
    <header className="top-bar">
      <div className="title-block">
        <Network aria-hidden="true" />
        <div>
          <h1>{data.title}</h1>
          <p>
            Evidence window {data.evidence_window_start} to {data.evidence_window_end}
          </p>
        </div>
      </div>
      <div className="status-strip">
        {Object.entries(data.source_status).map(([name, status]) => (
          <SourceBadge key={name} name={name} status={status} />
        ))}
      </div>
      <button className="icon-button" type="button" onClick={onRefresh} aria-label="Refresh case data">
        <RefreshCw aria-hidden="true" />
      </button>
    </header>
  );
}

function SourceBadge({ name, status }: { name: string; status: SourceHealth }) {
  const className = status.available ? "source-badge available" : status.configured ? "source-badge configured" : "source-badge unavailable";
  return (
    <span className={className} title={status.note}>
      {name}
    </span>
  );
}

function CaseBrief({ data }: { data: IranWarCase }) {
  const metrics = buildCaseBriefMetrics(data);
  const extracted = hasExtractedCausalClaims(data);
  const extraction = buildExtractionSummary(data);

  return (
    <section className="case-brief">
      <div className="case-brief-copy">
        <span className="eyebrow">Case Brief</span>
        <h2>What caused the 2026 Iran war?</h2>
        <p>
          Wikipedia is the background corpus. The app extracts source-backed drivers and rationales into the graph, while GDELT,
          Polymarket, and FRED stay in supporting roles.
        </p>
        <div className={data.extraction_status.method === "openai" ? "extraction-status openai" : "extraction-status fallback"}>
          <strong>{extraction.label}</strong>
          <span>{extraction.detail}</span>
        </div>
      </div>
      <div className="brief-metrics">
        {metrics.map((metric) => (
          <article key={metric.label} className="brief-metric">
            <strong>{metric.value}</strong>
            <span>{metric.label}</span>
            <p>{metric.detail}</p>
          </article>
        ))}
      </div>
      {!extracted ? (
        <div className="extraction-banner">
          <AlertTriangle aria-hidden="true" />
          <span>Causal claims not extracted yet. The center panel is waiting for source-backed driver extraction.</span>
        </div>
      ) : null}
    </section>
  );
}

function CausalBackbonePanel({ data, graph }: { data: IranWarCase; graph: GraphView }) {
  const lanes = buildTimelineLanes(data);
  const backbone = buildCausalBackbone({ ...data, graph_view: graph });
  return (
    <aside className="timeline-panel">
      <PanelHeading icon={<BookOpen aria-hidden="true" />} title="Causal Backbone" />
      <LaneSection title="Drivers and rationales" count={backbone.length} note="LLM/rule-structured nodes from Wikipedia-backed evidence.">
        <DriverList nodes={backbone} />
      </LaneSection>
      <LaneSection title="News support" count={lanes.newsReports.length} note="GDELT/statement records support current-state timing.">
        <EventList events={lanes.newsReports.slice(0, 12)} graph={graph} />
      </LaneSection>
      <LaneSection title="Scenario probabilities" count={lanes.predictionMarkets.length} note="Polymarket expectations attached as context, not content.">
        <SourceSignalList sources={lanes.predictionMarkets.slice(0, 10)} />
      </LaneSection>
      <LaneSection title="Market reaction context" count={lanes.marketData.length} note="FRED series support the chart below.">
        <SourceSignalList sources={lanes.marketData.slice(0, 4)} />
      </LaneSection>
    </aside>
  );
}

function LaneSection({ title, count, note, children }: { title: string; count: number; note: string; children: ReactNode }) {
  return (
    <section className="lane-section">
      <div className="lane-heading">
        <div>
          <h3>{title}</h3>
          <p>{note}</p>
        </div>
        <span>{count}</span>
      </div>
      {children}
    </section>
  );
}

function EventList({ events, graph }: { events: TimelineEvent[]; graph: GraphView }) {
  const selectTimelineEvent = useSelectionStore((state) => state.selectTimelineEvent);
  const selectedTimelineEventId = useSelectionStore((state) => state.selectedTimelineEventId);

  function firstRelatedNode(event: TimelineEvent): string | null {
    return graph.nodes.find((node) => node.claim_cluster_ids.some((clusterId) => event.claim_cluster_ids.includes(clusterId)))?.id ?? null;
  }

  if (!events.length) {
    return <p className="empty-lane">No records in this lane.</p>;
  }

  return (
    <div className="lane-list">
      {events.map((event) => (
        <button
          key={event.id}
          type="button"
          className={event.id === selectedTimelineEventId ? "compact-card active" : "compact-card"}
          onClick={() => selectTimelineEvent(event.id, firstRelatedNode(event))}
        >
          <time>{event.occurred_at}</time>
          <strong>{event.title}</strong>
          <span>{event.source_ids.length} source{event.source_ids.length === 1 ? "" : "s"}</span>
        </button>
      ))}
    </div>
  );
}

function DriverList({ nodes }: { nodes: GraphNode[] }) {
  const selectedGraphNodeId = useSelectionStore((state) => state.selectedGraphNodeId);
  const selectGraphNode = useSelectionStore((state) => state.selectGraphNode);

  if (!nodes.length) {
    return <p className="empty-lane">No causal drivers extracted yet.</p>;
  }

  return (
    <div className="lane-list">
      {nodes.map((node) => (
        <button
          key={node.id}
          type="button"
          className={node.id === selectedGraphNodeId ? "driver-card active" : "driver-card"}
          onClick={() => selectGraphNode(node.id)}
        >
          <span>{node.node_type}</span>
          <strong>{node.label}</strong>
          <small>{node.source_count} source{node.source_count === 1 ? "" : "s"}</small>
        </button>
      ))}
    </div>
  );
}

function SourceSignalList({ sources }: { sources: SourceDocument[] }) {
  const selectedSourceId = useSelectionStore((state) => state.selectedSourceId);
  const selectSource = useSelectionStore((state) => state.selectSource);

  if (!sources.length) {
    return <p className="empty-lane">No supporting signals available.</p>;
  }

  return (
    <div className="lane-list">
      {sources.map((source) => (
        <button
          key={source.id}
          type="button"
          className={source.id === selectedSourceId ? "compact-card signal active" : "compact-card signal"}
          onClick={() => selectSource(source.id)}
        >
          <span>{source.source_type}</span>
          <strong>{source.title}</strong>
          <small>{source.published_at ? source.published_at.slice(0, 10) : source.retrieved_at}</small>
        </button>
      ))}
    </div>
  );
}

function GraphToolbar({
  graph,
  setGraph
}: {
  graph: GraphView;
  setGraph: (graph: GraphView) => void;
}) {
  const selectedGraphNodeId = useSelectionStore((state) => state.selectedGraphNodeId);
  async function loadView(view: string) {
    const next = await fetchGraphView(view, view === "neighborhood" ? selectedGraphNodeId ?? undefined : undefined);
    setGraph(next);
  }

  return (
    <div className="graph-toolbar">
      <PanelHeading icon={<GitBranch aria-hidden="true" />} title="Causal Graph" />
      <div className="toolbar-buttons">
        <button type="button" className={graph.view === "spine" ? "active" : ""} onClick={() => void loadView("spine")}>
          Spine
        </button>
        <button type="button" onClick={() => void loadView("neighborhood")} disabled={!selectedGraphNodeId}>
          1-hop
        </button>
        <button type="button" className={graph.view === "contradictions" ? "active" : ""} onClick={() => void loadView("contradictions")}>
          Contradictions
        </button>
      </div>
    </div>
  );
}

function CausalGraph({ graph }: { graph: GraphView }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);
  const selectedGraphNodeId = useSelectionStore((state) => state.selectedGraphNodeId);
  const selectGraphNode = useSelectionStore((state) => state.selectGraphNode);

  useEffect(() => {
    if (!containerRef.current || cyRef.current) {
      return;
    }
    cyRef.current = cytoscape({
      container: containerRef.current,
      elements: [],
      minZoom: 0.35,
      maxZoom: 2.2,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "#116a58",
            label: "data(label)",
            color: "#17201b",
            "font-size": "11px",
            "font-weight": 700,
            "text-wrap": "wrap",
            "text-max-width": "110px",
            "text-valign": "bottom",
            "text-margin-y": 9,
            width: "40px",
            height: "40px",
            "border-width": "2px",
            "border-color": "#ffffff"
          }
        },
        { selector: ".node-market_reaction", style: { "background-color": "#a35422" } },
        { selector: ".node-current_state", style: { "background-color": "#5d6580" } },
        { selector: ".node-supernode", style: { "background-color": "#5d6580" } },
        { selector: ".confidence-low", style: { "border-style": "dashed", opacity: 0.76 } },
        {
          selector: "edge",
          style: {
            width: "2px",
            "line-color": "#7f8f87",
            "target-arrow-color": "#7f8f87",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": "8px",
            color: "#465149"
          }
        },
        { selector: ".edge-disrupts", style: { "line-color": "#a35422", "target-arrow-color": "#a35422", width: "3px" } },
        { selector: ".faded", style: { opacity: 0.14 } },
        { selector: ".highlighted", style: { opacity: 1, "border-color": "#d39a35", "line-color": "#d39a35", "target-arrow-color": "#d39a35", width: "4px" } }
      ],
      layout: { name: "breadthfirst", directed: true, spacingFactor: 1.15 }
    });

    cyRef.current.on("tap", "node", (event) => {
      selectGraphNode(event.target.id());
    });
  }, [selectGraphNode]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) {
      return;
    }
    cy.elements().remove();
    cy.add(causalSpineElements(graph) as ElementDefinition[]);
    cy.layout({ name: "breadthfirst", directed: true, spacingFactor: 1.25 }).run();
    cy.fit(undefined, 42);
  }, [graph]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) {
      return;
    }
    cy.elements().removeClass("highlighted faded");
    const highlighted = highlightedNeighborhood(graph, selectedGraphNodeId);
    if (!highlighted.size) {
      return;
    }
    cy.elements().addClass("faded");
    for (const id of highlighted) {
      cy.getElementById(id).removeClass("faded").addClass("highlighted");
    }
    const selected = cy.getElementById(selectedGraphNodeId ?? "");
    if (selected.length) {
      cy.animate({ center: { eles: selected }, zoom: 1.05 }, { duration: 260 });
    }
  }, [graph, selectedGraphNodeId]);

  return <div className="cy-container" ref={containerRef} aria-label="Causal graph canvas" />;
}

function EvidenceInspector({ data, graph }: { data: IranWarCase; graph: GraphView }) {
  const selectedGraphNodeId = useSelectionStore((state) => state.selectedGraphNodeId);
  const selectedTimelineEventId = useSelectionStore((state) => state.selectedTimelineEventId);
  const selectedSourceId = useSelectionStore((state) => state.selectedSourceId);
  const selectedMarkerId = useSelectionStore((state) => state.selectedMarkerId);
  const sourceMap = useMemo(() => new Map(data.source_documents.map((source) => [source.id, source])), [data.source_documents]);
  const selectedNode = graph.nodes.find((node) => node.id === selectedGraphNodeId) ?? null;
  const selectedEvent = data.timeline_events.find((event) => event.id === selectedTimelineEventId) ?? null;
  const selectedSource = selectedSourceId ? sourceMap.get(selectedSourceId) ?? null : null;
  const selectedMarker = data.market_markers.find((marker) => marker.id === selectedMarkerId) ?? null;
  const sourceIds = selectedNode?.source_ids ?? selectedEvent?.source_ids ?? selectedMarker?.source_ids ?? [];

  return (
    <aside className="inspector-panel">
      <PanelHeading icon={<ShieldAlert aria-hidden="true" />} title="Evidence Inspector" />
      {selectedSource ? (
        <div className="inspector-content">
          <span className="eyebrow">{selectedSource.source_type}</span>
          <h2>{selectedSource.title}</h2>
          <p>{selectedSource.excerpt}</p>
          <SourceCard source={selectedSource} fallbackId={selectedSource.id} />
        </div>
      ) : selectedNode || selectedEvent || selectedMarker ? (
        <div className="inspector-content">
          <span className="eyebrow">{selectedNode ? selectedNode.node_type : selectedEvent?.category ?? selectedMarker?.marker_type}</span>
          <h2>{selectedNode?.label ?? selectedEvent?.title ?? selectedMarker?.title}</h2>
          <p>{selectedNode?.summary ?? selectedEvent?.summary ?? selectedMarker?.summary}</p>
          <div className="source-stack">
            {sourceIds.map((sourceId) => (
              <SourceCard key={sourceId} source={sourceMap.get(sourceId)} fallbackId={sourceId} />
            ))}
          </div>
        </div>
      ) : (
        <div className="empty-inspector">
          <Sparkles aria-hidden="true" />
          <p>Select a node/source to inspect evidence.</p>
        </div>
      )}
    </aside>
  );
}

function SourceCard({ source, fallbackId }: { source?: SourceDocument; fallbackId: string }) {
  if (!source) {
    return <div className="source-card">{fallbackId}</div>;
  }
  return (
    <article className="source-card">
      <div>
        <span>{source.source_type}</span>
        <strong>{source.title}</strong>
      </div>
      <p>{source.excerpt}</p>
      {source.url ? (
        <a href={source.url} target="_blank" rel="noreferrer">
          <ExternalLink aria-hidden="true" />
          Source
        </a>
      ) : null}
    </article>
  );
}

function MarketReactionPanel({ points, markers, events, tension }: { points: MarketSeriesPoint[]; markers: MarketMarker[]; events: TimelineEvent[]; tension: TensionSeriesPoint[] }) {
  const selectedMarkerId = useSelectionStore((state) => state.selectedMarkerId);
  const selectMarker = useSelectionStore((state) => state.selectMarker);
  const grouped = groupSeries(points);
  const brent = grouped.get("Brent") ?? [];
  const sp500 = grouped.get("S&P 500") ?? [];
  const brentMove = brent.length >= 2 ? percentMove(brent[0].value, brent[brent.length - 1].value) : "n/a";
  const spMove = sp500.length >= 2 ? percentMove(sp500[0].value, sp500[sp500.length - 1].value) : "n/a";

  return (
    <section className="market-panel">
      <div className="market-header">
        <div>
          <PanelHeading icon={<LineChart aria-hidden="true" />} title="Market Reaction Context" />
          <p className="market-note">Indexed daily closes with dated evidence overlays. Temporal alignment is not causal attribution.</p>
        </div>
        <div className="market-metrics">
          <span>Brent {brentMove}</span>
          <span>S&P 500 {spMove}</span>
        </div>
      </div>
      <MiniMarketChart points={points} markers={markers} events={events} tension={tension} />
      <div className="marker-list">
        {markers.map((marker) => (
          <button
            key={marker.id}
            type="button"
            className={marker.id === selectedMarkerId ? "marker active" : "marker"}
            onClick={() => selectMarker(marker.id)}
          >
            <strong>{marker.title}</strong>
            <span>{marker.occurred_at}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

function PredictionMarketPanel({ points }: { points: PredictionMarketPricePoint[] }) {
  const allMarkets = sortPredictionMarkets(groupPredictionMarkets(points));
  const sections = splitPredictionMarkets(allMarkets);
  const activeCount = allMarkets.filter((market) => market.status === "active").length;
  const resolvedCount = allMarkets.filter((market) => market.status !== "active").length;

  return (
    <section className="prediction-panel">
      <div className="market-header">
        <div>
          <PanelHeading icon={<LineChart aria-hidden="true" />} title="Prediction Market Expectations" />
          <p className="market-note">Polymarket daily closes for relevant Iran and oil scenarios. These are probabilities attached to scenarios, not evidence events.</p>
        </div>
        <div className="market-metrics">
          <span>{allMarkets.length} markets</span>
          <span>{activeCount} active</span>
          <span>{resolvedCount} resolved</span>
        </div>
      </div>
      {allMarkets.length ? (
        <div className="prediction-sections">
          <PredictionMarketSection title="Active markets" markets={sections.active} />
          <PredictionMarketSection title="Resolved markets" markets={sections.resolved} />
        </div>
      ) : (
        <div className="empty-chart prediction-empty">No Polymarket daily close history available yet.</div>
      )}
    </section>
  );
}

function PredictionMarketSection({ title, markets }: { title: string; markets: PredictionMarketSeries[] }) {
  if (!markets.length) {
    return null;
  }
  return (
    <section className="prediction-section">
      <div className="prediction-section-heading">
        <h3>{title}</h3>
        <span>{markets.length}</span>
      </div>
      <div className="prediction-list">
        {markets.map((market) => (
          <PredictionMarketRow key={market.marketId} market={market} />
        ))}
      </div>
    </section>
  );
}

function PredictionMarketRow({ market }: { market: PredictionMarketSeries }) {
  return (
    <article className="prediction-row">
      <div className="prediction-copy">
        <span>{predictionCategory(market.question)} · {market.status}</span>
        <strong>{market.question}</strong>
        <small>{marketDateRange(market)} · {market.points.length} daily close{market.points.length === 1 ? "" : "s"}</small>
      </div>
      <PredictionSparkline market={market} />
      <div className="prediction-latest">
        <strong>{latestProbability(market)}</strong>
        <span>{market.outcome}</span>
        {market.url ? (
          <a href={market.url} target="_blank" rel="noreferrer" aria-label={`Open Polymarket market: ${market.question}`}>
            <ExternalLink aria-hidden="true" />
          </a>
        ) : null}
      </div>
    </article>
  );
}

function PredictionSparkline({ market }: { market: PredictionMarketSeries }) {
  const width = 260;
  const height = 64;
  const padX = 10;
  const padY = 10;
  const points = market.points;
  const d = points
    .map((point, index) => {
      const x = predictionX(point.date, market, width, padX);
      const y = padY + (1 - point.probability) * (height - padY * 2);
      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");
  const first = points[0];
  const last = points[points.length - 1];

  return (
    <svg className="prediction-sparkline" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${market.question} probability history`}>
      <line x1={padX} x2={width - padX} y1={padY} y2={padY} className="prob-grid" />
      <line x1={padX} x2={width - padX} y1={height / 2} y2={height / 2} className="prob-grid" />
      <line x1={padX} x2={width - padX} y1={height - padY} y2={height - padY} className="prob-grid" />
      {d ? <path d={d} className={market.status === "active" ? "prob-line active" : "prob-line resolved"} /> : null}
      {first ? <circle cx={predictionX(first.date, market, width, padX)} cy={padY + (1 - first.probability) * (height - padY * 2)} r={3} className="prob-dot start" /> : null}
      {last ? <circle cx={predictionX(last.date, market, width, padX)} cy={padY + (1 - last.probability) * (height - padY * 2)} r={4} className="prob-dot end" /> : null}
      <text x={padX} y={height - 2}>{market.points[0]?.date}</text>
      <text x={width - 68} y={height - 2}>{market.points[market.points.length - 1]?.date}</text>
    </svg>
  );
}

function MiniMarketChart({ points, markers, events, tension }: { points: MarketSeriesPoint[]; markers: MarketMarker[]; events: TimelineEvent[]; tension: TensionSeriesPoint[] }) {
  const selectedTimelineEventId = useSelectionStore((state) => state.selectedTimelineEventId);
  const selectedEvent = useSelectionStore((state) => state.selectedTimelineEventId);
  const selectedMarkerId = useSelectionStore((state) => state.selectedMarkerId);
  const selectTimelineEvent = useSelectionStore((state) => state.selectTimelineEvent);
  const selectMarker = useSelectionStore((state) => state.selectMarker);
  const [eventMode, setEventMode] = useState<"major" | "all">("major");
  const [windowMode, setWindowMode] = useState<ChartWindowMode>("full");

  if (!points.length) {
    return <div className="market-chart empty-chart">No FRED market observations available.</div>;
  }

  const indexed = indexSeriesToBaseline(points);
  const overlays = buildMarketEventOverlays(events, markers);
  const selectedTimelineDate = events.find((event) => event.id === selectedEvent)?.occurred_at ?? null;
  const chartWindow = chartWindowForMode(windowMode, points, overlays, selectedTimelineDate);
  const rugItems = buildEventRug(
    overlays.filter((overlay) => withinWindow(overlay.date, chartWindow)),
    eventMode
  );
  const width = 900;

  function selectOverlay(overlays: MarketEventOverlay[]) {
    const event = overlays.find((overlay) => overlay.kind === "timeline");
    if (event) {
      selectTimelineEvent(event.id, null);
      return;
    }
    const marker = overlays.find((overlay) => overlay.kind === "marker");
    if (marker) {
      selectMarker(marker.id);
    }
  }

  return (
    <div className="event-study">
      <div className="chart-controls">
        <div className="segmented-control" aria-label="Market chart window">
          <button type="button" className={windowMode === "full" ? "active" : ""} onClick={() => setWindowMode("full")}>Full</button>
          <button type="button" className={windowMode === "war" ? "active" : ""} onClick={() => setWindowMode("war")}>War phase</button>
          <button type="button" className={windowMode === "selected" ? "active" : ""} onClick={() => setWindowMode("selected")} disabled={!selectedTimelineDate}>Selected</button>
        </div>
        <div className="segmented-control" aria-label="Event density">
          <button type="button" className={eventMode === "major" ? "active" : ""} onClick={() => setEventMode("major")}>Major events</button>
          <button type="button" className={eventMode === "all" ? "active" : ""} onClick={() => setEventMode("all")}>All news</button>
        </div>
      </div>
      <svg className="market-chart small-multiples" viewBox={`0 0 ${width} 382`} role="img" aria-label="Indexed Brent, WTI, S&P 500, and rule-based tension series with compact event rug">
        <IndexedSeriesRow seriesName="Brent" className="brent" points={indexed.get("Brent") ?? []} window={chartWindow} yOffset={14} width={width} />
        <IndexedSeriesRow seriesName="WTI" className="wti" points={indexed.get("WTI") ?? []} window={chartWindow} yOffset={96} width={width} />
        <IndexedSeriesRow seriesName="S&P 500" className="sp500" points={indexed.get("S&P 500") ?? []} window={chartWindow} yOffset={178} width={width} />
        <TensionSeriesRow points={filterTensionSeriesForWindow(tension, chartWindow)} window={chartWindow} yOffset={260} width={width} />
        <EventRug items={rugItems} window={chartWindow} width={width} selectedIds={[selectedTimelineEventId, selectedMarkerId]} onSelect={selectOverlay} />
        <g className="chart-legend">
          <text x={42} y={374}>Indexed to 100. Window {chartWindow.start} to {chartWindow.end}.</text>
          <text x={width - 184} y={374}>{rugItems.length} event date{rugItems.length === 1 ? "" : "s"}</text>
        </g>
      </svg>
    </div>
  );
}

function TensionSeriesRow({
  points,
  window,
  yOffset,
  width
}: {
  points: TensionSeriesPoint[];
  window: { start: string; end: string };
  yOffset: number;
  width: number;
}) {
  const rowHeight = 68;
  const padX = 58;
  const padTop = 8;
  const padBottom = 16;

  function x(date: string) {
    return marketX(date, window, width, padX);
  }

  function y(value: number) {
    return yOffset + rowHeight - padBottom - (value / 100) * (rowHeight - padTop - padBottom);
  }

  const d = points.map((point, index) => `${index === 0 ? "M" : "L"} ${x(point.date)} ${y(point.value)}`).join(" ");
  const last = points[points.length - 1];

  return (
    <g className="series-row tension-row">
      <text x={10} y={yOffset + 18} className="row-title">Tension</text>
      <line x1={padX} x2={width - padX} y1={y(50)} y2={y(50)} className="baseline" />
      <text x={width - 48} y={y(100) + 4} className="axis-label">100</text>
      <text x={width - 42} y={y(0) + 4} className="axis-label">0</text>
      <path d={d} className="line tension" />
      {last ? <circle cx={x(last.date)} cy={y(last.value)} r={3} className="series-end tension" /> : null}
    </g>
  );
}

function IndexedSeriesRow({
  seriesName,
  className,
  points,
  window,
  yOffset,
  width
}: {
  seriesName: string;
  className: string;
  points: IndexedMarketSeriesPoint[];
  window: { start: string; end: string };
  yOffset: number;
  width: number;
}) {
  const rowHeight = 68;
  const padX = 58;
  const padTop = 8;
  const padBottom = 16;
  const visible = points.filter((point) => withinWindow(point.date, window));
  const values = visible.map((point) => point.indexedValue);
  const minValue = Math.min(100, ...values);
  const maxValue = Math.max(100, ...values);
  const valueRange = Math.max(1, maxValue - minValue);
  const min = minValue - valueRange * 0.2;
  const max = maxValue + valueRange * 0.2;

  function x(date: string) {
    return marketX(date, window, width, padX);
  }

  function y(value: number) {
    return yOffset + rowHeight - padBottom - ((value - min) / Math.max(1, max - min)) * (rowHeight - padTop - padBottom);
  }

  const d = visible.map((point, index) => `${index === 0 ? "M" : "L"} ${x(point.date)} ${y(point.indexedValue)}`).join(" ");
  const last = visible[visible.length - 1];

  return (
    <g className="series-row">
      <text x={10} y={yOffset + 18} className="row-title">{seriesName}</text>
      <line x1={padX} x2={width - padX} y1={y(100)} y2={y(100)} className="baseline" />
      <text x={width - 48} y={y(maxValue) + 4} className="axis-label">+{(maxValue - 100).toFixed(0)}%</text>
      <text x={width - 42} y={y(minValue) + 4} className="axis-label">{(minValue - 100).toFixed(0)}%</text>
      <path d={d} className={`line ${className}`} />
      {last ? <circle cx={x(last.date)} cy={y(last.indexedValue)} r={3} className={`series-end ${className}`} /> : null}
    </g>
  );
}

function overlayCategory(overlays: MarketEventOverlay[]): string {
  const categories = overlays.map((overlay) => overlay.category);
  if (categories.includes("strike")) return "strike";
  if (categories.includes("statement")) return "statement";
  if (categories.includes("market") || categories.includes("market_move") || categories.includes("impact")) return "market";
  if (categories.includes("diplomacy")) return "diplomacy";
  return "prelude";
}

function overlayTitle(date: string, overlays: MarketEventOverlay[]): string {
  const titles = overlays.slice(0, 4).map((overlay) => `${overlay.title} (${overlay.sourceCount} source${overlay.sourceCount === 1 ? "" : "s"})`);
  const remaining = overlays.length > titles.length ? `\n+${overlays.length - titles.length} more` : "";
  return `${date}\n${titles.join("\n")}${remaining}`;
}

function EventRug({
  items,
  window,
  width,
  selectedIds,
  onSelect
}: {
  items: EventRugItem[];
  window: { start: string; end: string };
  width: number;
  selectedIds: (string | null)[];
  onSelect: (overlays: MarketEventOverlay[]) => void;
}) {
  const padX = 58;
  const axisY = 346;
  const dotY = 330;
  return (
    <g className="event-rug">
      <line x1={padX} x2={width - padX} y1={axisY} y2={axisY} className="rug-axis" />
      {items.map((item) => {
        const selected = item.overlays.some((overlay) => selectedIds.includes(overlay.id));
        const category = overlayCategory(item.overlays);
        return (
          <g key={item.date} className={selected ? "rug-item selected" : "rug-item"} onClick={() => onSelect(item.overlays)}>
            <title>{overlayTitle(item.date, item.overlays)}</title>
            <line x1={marketX(item.date, window, width, padX)} x2={marketX(item.date, window, width, padX)} y1={dotY} y2={axisY + 6} className={`rug-line overlay-${category}`} />
            <circle cx={marketX(item.date, window, width, padX)} cy={dotY} r={selected ? 5 : 4} className={`rug-dot overlay-${category}`} />
            {item.count > 1 ? <text x={marketX(item.date, window, width, padX) + 5} y={dotY - 3} className="rug-count">{item.count}</text> : null}
          </g>
        );
      })}
    </g>
  );
}

function withinWindow(date: string, window: { start: string; end: string }) {
  const normalized = date.slice(0, 10);
  return normalized >= window.start && normalized <= window.end;
}

function marketX(date: string, window: { start: string; end: string }, width: number, padX: number) {
  const startMs = Date.parse(window.start);
  const endMs = Date.parse(window.end);
  const time = Date.parse(date);
  const position = Number.isFinite(time) ? (time - startMs) / Math.max(1, endMs - startMs) : 0;
  return padX + Math.min(1, Math.max(0, position)) * (width - padX * 2);
}

function predictionX(date: string, market: PredictionMarketSeries, width: number, padX: number) {
  const start = market.marketStart ?? market.points[0]?.date ?? date;
  const end = market.marketEnd ?? market.points[market.points.length - 1]?.date ?? date;
  const startMs = Date.parse(start);
  const endMs = Date.parse(end);
  const time = Date.parse(date);
  const position = Number.isFinite(time) ? (time - startMs) / Math.max(1, endMs - startMs) : 0;
  return padX + Math.min(1, Math.max(0, position)) * (width - padX * 2);
}

function predictionCategory(question: string) {
  return /\b(oil|crude|wti|brent|hormuz)\b/i.test(question) ? "Oil" : "Iran";
}

function PanelHeading({ icon, title }: { icon: ReactNode; title: string }) {
  return (
    <div className="panel-heading">
      {icon}
      <h2>{title}</h2>
    </div>
  );
}

export default App;
