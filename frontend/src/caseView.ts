import type { GraphNode, IranWarCase, SourceDocument, TimelineEvent } from "./types";

export interface CaseBriefMetric {
  label: string;
  value: string;
  detail: string;
}

export interface ExtractionSummary {
  label: string;
  detail: string;
}

export interface TimelineLanes {
  background: TimelineEvent[];
  newsReports: TimelineEvent[];
  predictionMarkets: SourceDocument[];
  marketData: SourceDocument[];
}

export function buildCaseBriefMetrics(data: IranWarCase): CaseBriefMetric[] {
  const sourceCounts = countSources(data.source_documents);
  return [
    {
      label: "Causal Drivers",
      value: String(data.graph_view.nodes.filter((node) => node.claim_type !== "market_expectation").length),
      detail: "Drivers and rationales extracted from the Wikipedia backbone."
    },
    {
      label: "Historical Backbone",
      value: String(sourceCounts.wikipedia ?? 0),
      detail: "Wikipedia sections are used as background evidence."
    },
    {
      label: "News Reporting",
      value: String((sourceCounts.gdelt ?? 0) + (sourceCounts.wikipedia_reference ?? 0)),
      detail: "GDELT records plus timestamped news citations extracted from Wikipedia references."
    },
    {
      label: "Expectation Signals",
      value: String(sourceCounts.polymarket ?? 0),
      detail: "Polymarket markets contextualize scenarios, not causes."
    }
  ];
}

export function buildCausalBackbone(data: IranWarCase): GraphNode[] {
  return data.graph_view.nodes.filter((node) => node.claim_type !== "market_expectation" && node.node_type !== "market_reaction");
}

export function buildTimelineLanes(data: IranWarCase): TimelineLanes {
  return {
    background: data.timeline_events.filter((event) => event.category === "background"),
    newsReports: data.timeline_events.filter((event) => event.category !== "background"),
    predictionMarkets: data.source_documents.filter((source) => source.source_type === "polymarket"),
    marketData: data.source_documents.filter((source) => source.source_type === "fred")
  };
}

export function hasExtractedCausalClaims(data: IranWarCase): boolean {
  return data.claim_clusters.length > 0;
}

export function buildExtractionSummary(data: IranWarCase): ExtractionSummary {
  const clusterCount = data.extraction_status.extracted_claim_clusters;
  return {
    label: `Extraction: ${data.extraction_status.method}`,
    detail: `${data.extraction_status.note} ${clusterCount} claim cluster${clusterCount === 1 ? "" : "s"} retained from ${data.extraction_status.source_scope.join(", ") || "no sources"}.`
  };
}

function countSources(sources: SourceDocument[]): Record<string, number> {
  return sources.reduce<Record<string, number>>((counts, source) => {
    counts[source.source_type] = (counts[source.source_type] ?? 0) + 1;
    return counts;
  }, {});
}
