import { describe, expect, it } from "vitest";

import { buildCaseBriefMetrics, buildCausalBackbone, buildExtractionSummary, buildTimelineLanes, hasExtractedCausalClaims } from "./caseView";
import type { IranWarCase } from "./types";

const baseCase: IranWarCase = {
  title: "2026 Iran War",
  evidence_window_start: "2025-12-01",
  evidence_window_end: "2026-05-10",
  summary: "Case summary",
  timeline_events: [
    {
      id: "background",
      occurred_at: "2025-12-01",
      title: "Background",
      summary: "Background summary",
      category: "background",
      source_ids: ["wiki:1"],
      claim_cluster_ids: [],
      confidence: "medium",
      claim_type: "actor_stated_rationale"
    },
    {
      id: "report",
      occurred_at: "2026-05-09",
      title: "GDELT report",
      summary: "News summary",
      category: "prelude",
      source_ids: ["gdelt:1"],
      claim_cluster_ids: [],
      confidence: "medium",
      claim_type: "reported_fact"
    }
  ],
  graph_view: {
    view: "spine",
    nodes: [
      {
        id: "node:nuclear",
        label: "Iran nuclear issue and JCPOA collapse",
        node_type: "strategic_driver",
        summary: "Nuclear driver",
        source_ids: ["wiki:1"],
        claim_cluster_ids: ["cluster:nuclear"],
        confidence: "medium",
        claim_type: "actor_stated_rationale",
        source_count: 1
      },
      {
        id: "node:polymarket",
        label: "Polymarket Iran markets",
        node_type: "current_state",
        summary: "Prediction signal",
        source_ids: ["poly:1"],
        claim_cluster_ids: [],
        confidence: "medium",
        claim_type: "market_expectation",
        source_count: 1
      }
    ],
    edges: []
  },
  source_documents: [
    { id: "wiki:1", source_type: "wikipedia", title: "Wiki", retrieved_at: "2026-05-10", excerpt: "Wiki excerpt" },
    { id: "wiki-ref:1", source_type: "wikipedia_reference", title: "CNN report", published_at: "2026-03-12", retrieved_at: "2026-05-10", excerpt: "Reference excerpt" },
    { id: "gdelt:1", source_type: "gdelt", title: "News", retrieved_at: "2026-05-10", excerpt: "News excerpt" },
    { id: "poly:1", source_type: "polymarket", title: "Peace deal market", retrieved_at: "2026-05-10", excerpt: "Market excerpt" },
    { id: "fred:1", source_type: "fred", title: "FRED Brent", retrieved_at: "2026-05-10", excerpt: "FRED excerpt" }
  ],
  claim_clusters: [{ id: "cluster:nuclear", claim_ids: ["claim:nuclear"], status: "accepted", summary: "Nuclear driver", canonical_entity_ids: [] }],
  claim_contradictions: [],
  market_series: [{ series: "Brent", date: "2026-05-01", value: 74.2, source: "FRED" }],
  tension_series: [{ date: "2026-05-01", value: 55, source: "rule_based", source_ids: ["wiki-ref:1"], summary: "Tension signal" }],
  prediction_market_series: [],
  market_markers: [],
  source_status: {
    wikipedia: { configured: true, available: true, note: "" },
    gdelt: { configured: true, available: true, note: "" },
    polymarket: { configured: true, available: true, note: "" },
    fred: { configured: true, available: true, note: "" },
    openai: { configured: true, available: true, note: "" },
    postgres: { configured: false, available: false, note: "" },
    qdrant: { configured: false, available: false, note: "" }
  },
  extraction_status: {
    method: "deterministic-wikipedia-fallback",
    note: "Wikipedia source sections were matched to the planned driver taxonomy.",
    source_scope: ["wikipedia", "gdelt"],
    extracted_claim_clusters: 1
  }
};

describe("buildTimelineLanes", () => {
  it("keeps prediction markets and FRED as supporting lanes, not chronology events", () => {
    const lanes = buildTimelineLanes(baseCase);

    expect(lanes.background.map((event) => event.id)).toEqual(["background"]);
    expect(lanes.newsReports.map((event) => event.id)).toEqual(["report"]);
    expect(lanes.predictionMarkets.map((source) => source.id)).toEqual(["poly:1"]);
    expect(lanes.marketData.map((source) => source.id)).toEqual(["fred:1"]);
  });
});

describe("buildCaseBriefMetrics", () => {
  it("summarizes source roles with counts", () => {
    const metrics = buildCaseBriefMetrics(baseCase);

    expect(metrics.map((metric) => `${metric.label}:${metric.value}`)).toContain("Causal Drivers:1");
    expect(metrics.map((metric) => `${metric.label}:${metric.value}`)).toContain("News Reporting:2");
    expect(metrics.map((metric) => `${metric.label}:${metric.value}`)).toContain("Expectation Signals:1");
  });
});

describe("hasExtractedCausalClaims", () => {
  it("is true when source-backed claim clusters exist", () => {
    expect(hasExtractedCausalClaims(baseCase)).toBe(true);
  });
});

describe("buildCausalBackbone", () => {
  it("returns causal nodes without prediction-market signal nodes", () => {
    expect(buildCausalBackbone(baseCase).map((node) => node.id)).toEqual(["node:nuclear"]);
  });
});

describe("buildExtractionSummary", () => {
  it("makes clear whether OpenAI or the deterministic fallback produced the graph", () => {
    const summary = buildExtractionSummary(baseCase);

    expect(summary.label).toBe("Extraction: deterministic-wikipedia-fallback");
    expect(summary.detail).toContain("Wikipedia source sections");
    expect(summary.detail).toContain("1 claim cluster");
  });
});
